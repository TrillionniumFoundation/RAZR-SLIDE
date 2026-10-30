"""Separate STEP readback with reverse q=[12,0] construction; no producer import."""
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
from complete_surface_support import full_face_support

OUT=HERE/'reader-v2';OUT.mkdir(exist_ok=False)
report={'schema':'razr-r12-current-K1K3-independent-STEP-reverse-v2',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(__file__),'helper_sha256':sha(HERE/'current_key_common.py'),'complete_support_helper_sha256':sha(HERE/'complete_surface_support.py'),
        'input_manifest_sha256':sha(HERE/'INPUT_MANIFEST.json'),
        'completed':False,'failures':[],'sides':{},'all_15D_body_pairs_qualified':False}

def construct(shape,folder):
    move=cq.Vector(0,-12,0)
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
        ranges,complete=full_face_support(face,move.toTuple())
        entry['complete_face_support_certificate']=complete
        if kind=='PLANE':
            boxvol=F(complete['exact_carrier_volume_upper_mm3'])
            if boxvol<=F('1e-9'):
                parts.append(None)
                rows.append({'label':'planar_face_'+str(i),'source_face':i,
                    'representation':'exact_complete_face_q_box_certificate',
                    'complete_affine_UV_q_carrier':complete,
                    'conceptual_box_positive_or_zero_dimension':all(b>=a for a,b in ranges),
                    'native_near_degenerate_prism_not_used':True})
                entry['action']='exact_complete_surface_q_box_volume_bound'
                continue
            op=BRepPrimAPI_MakePrism(face.wrapped,gp_Vec(0,-12,0),True)
            assert op.IsDone();add('planar_face_'+str(i),cq.Shape.cast(op.Shape()),i)
            rows[-1]['complete_affine_UV_q_carrier']=complete
            entry['action']='complete_native_face_prism'
        elif kind=='CYLINDER':
            lows=[];highs=[]
            for lo,hi in ranges:
                fl=float(lo);fh=float(hi)
                if F(fl)>lo:fl=math.nextafter(fl,-math.inf)
                if F(fh)<hi:fh=math.nextafter(fh,math.inf)
                lows.append(math.nextafter(fl,-math.inf));highs.append(math.nextafter(fh,math.inf))
            for attempt in range(8):
                sizes=[math.nextafter(highs[j]-lows[j],math.inf) for j in range(3)]
                carrier=cq.Solid.makeBox(*sizes,cq.Vector(*lows))
                bb=bounds(carrier)
                good=all(F(bb[2*j])<=ranges[j][0] and F(bb[2*j+1])>=ranges[j][1] for j in range(3))
                if good:break
                for j in range(3):
                    lows[j]=math.nextafter(lows[j],-math.inf);highs[j]=math.nextafter(highs[j],math.inf)
            assert good,'native box does not enclose complete cylinder support'
            entry['action']='outward_complete_cylinder_trim_edge_vertex_full_q_support_box'
            entry['native_support_inclusion_checked']=True
            add('cylinder_'+str(i)+'_full_support_box',carrier,i)
        else:raise ValueError('unsupported complete boundary '+kind)
    return parts,rows,face_rows

try:
    verify_inputs()
    forward=HERE/'producer-v6/report.json'
    producer=json.loads(forward.read_text());assert producer['completed']
    report['forward_producer_report_sha256']=sha(forward)
    report['independence']={'separate_process':True,'source_geometry_format':'STEP',
        'construction_direction':'reverse 12 to 0','producer_builder_imported':False,
        'same_native_kernel':True,'same_general_enclosure_formulas':True,'independent_CAD_kernel':False}
    panel,pr=load_body('A_BACK_PANEL','reader');report['panel']=pr
    report['whole_source_BREP_STEP_directed_material_differences']={}
    for name in ['L_KEY','R_KEY','A_BACK_PANEL']:
        step,_=load_body(name,'reader');brep,_=load_body(name,'producer')
        item={}
        for label,a,b in [('STEP_minus_BREP',step,brep),('BREP_minus_STEP',brep,step)]:
            difference=serial(a,b,'cut');item[label]=save(difference,OUT/'source-material'/name/(label+'.brep'),empty=True)
            assert item[label]['signed_volume_mm3']<=strict.TOL
        report['whole_source_BREP_STEP_directed_material_differences'][name]=item
    keys={};originals={}
    for side in 'LR':
        key,kr=load_body(side+'_KEY','reader');keys[side]=key;originals[side]=kr
        row={'original':kr,'q_interval_mm':[0.,12.],'construction_q_start_end':[12.,0.],'complete_face_inventory':[],'region_results':[]}
        report['sides'][side]=row
        parts,regions,faces=construct(clone(key).translate((0,12,0)),OUT/side/'regions');row['complete_face_inventory']=faces
        row['regions']=regions
        for i,(part,rec) in enumerate(zip(parts,regions)):
            before=fingerprint(part) if part is not None else None
            certificate=rec.get('complete_affine_UV_q_carrier')
            exact_bound=F(certificate['exact_carrier_volume_upper_mm3']) if certificate else None
            if exact_bound is not None and exact_bound<=F('1e-9'):
                bound=float(exact_bound)
                if F(bound)<exact_bound:bound=math.nextafter(bound,math.inf)
                pair={'method':'complete_affine_UV_q_carrier_volume_bound','measured_common_mm3':bound,
                    'value_is_conservative_geometric_carrier_bound_not_Common':True,
                    'exact_volume_bound_mm3':str(exact_bound),
                    'exact_box_certificate_used_without_invalid_native_prism':True,
                    'original_gate_clear':exact_bound<=F(strict.TOL),
                    'all_native_evaluator_error_bound_available':False}
            else:
                pair=complete_pair(part,panel,OUT/side/'commons'/(rec['label']+'.brep'))
            row['region_results'].append({'region_index':i,'label':rec['label'],**pair})
            assert part is None or fingerprint(part)==before
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
    report['scope']={'motion_is_continuous_region_construction':True,'every_complete_source_face_included_without_normal_sign_selection':True,'near_tangent_faces_bound_exactly_without_native_tiny_prism':True,'finite_samples_used_as_domain_proof':False,
       'native_filling_and_all_compiled_geometry_errors_formally_bounded':False,
       'physical_allowed_domain_proved':False,'whole_15D_G2':False,'strength':False,'G3':False,'G4':False,'G5':False}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'completed':report['completed'],'seconds':report['seconds'],'peak_RSS_bytes':report['peak_RSS_bytes'],'failures':report['failures']}))
sys.exit(0 if report['completed'] else 1)
