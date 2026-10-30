"""Full current K1 KEY forward [0,12] q regions against whole current K3 panel."""
import os,resource,signal,time,json,traceback,datetime,sys
resource.setrlimit(resource.RLIMIT_AS,(3<<29,3<<29))
resource.setrlimit(resource.RLIMIT_CPU,(240,240))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
signal.alarm(300);started=time.monotonic()
from current_key_common import *
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec
from OCP.BRepLib import BRepLib
from OCP.TopoDS import TopoDS
from fractions import Fraction as F

OUT=HERE/'producer-v2';OUT.mkdir(exist_ok=False)
report={'schema':'razr-r12-current-K1K3-forward-whole-key-v2',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(__file__),'helper_sha256':sha(HERE/'current_key_common.py'),
        'input_manifest_sha256':sha(HERE/'INPUT_MANIFEST.json'),
        'completed':False,'failures':[],'sides':{},'all_15D_body_pairs_qualified':False}

def construct(shape,folder):
    move=cq.Vector(0,12,0)
    parts=[];rows=[];face_rows=[]
    def add(label,part,source=None):
        before_volume=float(part.Volume())
        before_bounds=bounds(part)
        orientation={'unmodified_signed_volume_mm3':before_volume,'repair_applied':False}
        if before_volume<=0:
            orientation['raw_unoriented_file']=save_raw(part,folder/(label+'.unoriented.brep'))
            assert part.ShapeType()=='Solid' and part.isValid()
            part=clone(part)
            accepted=BRepLib.OrientClosedSolid_s(TopoDS.Solid_s(part.wrapped))
            orientation.update(repair_applied=True,native_OrientClosedSolid_returned=accepted)
            assert accepted
            orientation['oriented_signed_volume_mm3']=float(part.Volume())
            orientation['signed_volume_sum_mm3']=before_volume+float(part.Volume())
            orientation['bounds_unchanged']=bounds(part)==before_bounds
            assert orientation['bounds_unchanged'] and abs(orientation['signed_volume_sum_mm3'])<=strict.TOL
        raw=save_raw(part,folder/(label+'.brep'))
        sig=signature(part)
        strict.single(part)
        parts.append(part);rows.append({'label':label,'source_face':source,'file':raw,'orientation':orientation,**sig})
    add('whole_start',clone(shape));add('whole_end',clone(shape).translate(move))
    for i,face0 in enumerate(shape.Faces()):
        face=cq.Face(clone(face0).wrapped)
        kind=face.geomType();entry={'index':i,'kind':kind,'normal':list(face.normalAt().toTuple())}
        face_rows.append(entry)
        if kind=='PLANE':
            dot=face.normalAt().dot(move);entry['normal_dot_motion']=dot
            if dot>0:
                op=BRepPrimAPI_MakePrism(face.wrapped,gp_Vec(0,12,0),True)
                assert op.IsDone();add('planar_face_'+str(i),cq.Shape.cast(op.Shape()),i)
                entry['action']='complete_native_face_prism'
            else:entry['action']='nonadvancing_planar_face'
        elif kind=='CYLINDER':
            ad=BRepAdaptor_Surface(face.wrapped);cy=ad.Cylinder();d=cy.Axis().Direction()
            axis=cq.Vector(d.X(),d.Y(),d.Z());p=cy.Location();v0=ad.FirstVParameter();v1=ad.LastVParameter()
            assert v1>v0
            base=cq.Vector(p.X(),p.Y(),p.Z()).add(axis.multiply(v0));h=v1-v0;r=cy.Radius()
            entry['cylinder']={'axis':list(axis.toTuple()),'base':list(base.toTuple()),'radius':r,'v_interval':[v0,v1]}
            # Even axial cylinders are included as full filled carriers. This
            # is deliberately conservative; no boundary patch is discarded.
            dot=axis.dot(move);cross=axis.cross(move)
            if cross.Length==0:
                add('cylinder_'+str(i)+'_axial',cq.Solid.makeCylinder(r,h+abs(dot),base.add(axis.multiply(min(0.,dot))),axis),i)
                entry['action']='full_axial_cylinder'
            else:
                assert dot==0,'oblique cylinder refused'
                first=cq.Solid.makeCylinder(r,h,base,axis)
                add('cylinder_'+str(i)+'_start',first,i)
                add('cylinder_'+str(i)+'_end',clone(first).translate(move),i)
                tangent=axis.cross(move.normalized()).normalized().multiply(r)
                pts=[base.add(tangent),base.sub(tangent),base.add(move).sub(tangent),base.add(move).add(tangent)]
                wire=cq.Wire.makePolygon(pts,close=True)
                profile=cq.Face.makeFromWires(wire)
                op=BRepPrimAPI_MakePrism(profile.wrapped,gp_Vec(*(axis.multiply(h).toTuple())),True)
                assert op.IsDone();add('cylinder_'+str(i)+'_bridge',cq.Shape.cast(op.Shape()),i)
                entry['action']='whole_cylinder_capsule_three_regions'
        else:raise ValueError('unsupported complete boundary '+kind)
    return parts,rows,face_rows

try:
    verify_inputs();panel,pr=load_body('A_BACK_PANEL','producer');report['panel']=pr
    keys={};originals={}
    for side in 'LR':
        key,kr=load_body(side+'_KEY','producer');keys[side]=key;originals[side]=kr
        row={'original':kr,'q_interval_mm':[0.,12.],'complete_face_inventory':[],'region_results':[]}
        report['sides'][side]=row
        parts,regions,faces=construct(key,OUT/side/'regions');row['complete_face_inventory']=faces
        row['regions']=regions
        for i,(part,rec) in enumerate(zip(parts,regions)):
            before=fingerprint(part)
            pair=complete_pair(part,panel,OUT/side/'commons'/(rec['label']+'.brep'))
            row['region_results'].append({'region_index':i,'label':rec['label'],**pair})
            assert fingerprint(part)==before
        row['sum']=exact_sum_nonnegative([x['measured_common_mm3'] for x in row['region_results']])
        row['positive_regions']=[x for x in row['region_results'] if x['measured_common_mm3']>strict.TOL]
        row['whole_original_unchanged']=fingerprint(key)==kr['fingerprint_before'];assert row['whole_original_unchanged']
    l,r=map(lambda s:originals[s]['signature']['bounds_mm'],'LR')
    gap=F(r[0])-F(l[1]);assert gap>0
    report['independent_q_L_q_R_KEY_KEY_separation']={'q_L_mm':[0,12],'q_R_mm':[0,12],
         'exact_read_native_X_support_gap_mm':str(gap),'gap_mm':float(gap),
         'reason':'Independent Y translations do not change either complete X support.',
         'native_support_bound_formal_error_proof':False}
    assert fingerprint(panel)==pr['fingerprint_before'];verify_inputs()
    report['completed']=True
    report['all_current_KEY_panel_region_sums_clear']=all(x['sum']['measured_sum_passes_original_1e_7_gate'] for x in report['sides'].values())
except BaseException as exc:
    report['failures'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
finally:
    report['seconds']=time.monotonic()-started
    report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    report['scope']={'motion_is_continuous_region_construction':True,'finite_samples_used_as_domain_proof':False,
       'native_filling_and_all_compiled_geometry_errors_formally_bounded':False,
       'physical_allowed_domain_proved':False,'whole_15D_G2':False,'strength':False,'G3':False,'G4':False,'G5':False}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'completed':report['completed'],'seconds':report['seconds'],'peak_RSS_bytes':report['peak_RSS_bytes'],'failures':report['failures']}))
sys.exit(0 if report['completed'] else 1)
