#!/usr/bin/env python3
"""R7 bounded endpoint relocation, with uncut frozen R6 participants.

The historical A anchor is not a product constraint. Its actual obstruction
is retained before searching relocations. Connector boxes are only original
dimensional reservations; no supplier model is exported or reconstructed.
"""
from pathlib import Path
import hashlib,itertools,json,math,platform,sys,time,traceback
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN,TopAbs_OUT,TopAbs_ON
from OCP.gp import gp_Pnt

ROOT=Path(__file__).resolve().parent
R6=ROOT.parent/'fpc-g2-route-candidates-20261013-r6/recovered_x230/input'
sys.path[:0]=[str(R6),str(R6/'guards')]
from actual_obstacle_and_jacobian import obstacle_factory
from strict_intersections import participant,strict_common
POSES=[('STOW',0.,0.),('PREDOCK',79.75,0.),('OPEN_SEATED',79.75,8.2)]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def box(x0,x1,y0,y1,z0,z1):return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,cq.Vector(x0,y0,z0))
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def classify(point,body):
    c=BRepClass3d_SolidClassifier(body.wrapped);c.Perform(gp_Pnt(*point),1e-7)
    return {TopAbs_IN:'IN',TopAbs_OUT:'OUT',TopAbs_ON:'ON'}.get(c.State(),'UNKNOWN')
def full_payload(shape):
    leaves=[];counts={}
    def visit(s):
        counts[s.ShapeType()]=counts.get(s.ShapeType(),0)+1
        if s.ShapeType()=='Solid':participant(s);leaves.append(s)
        elif s.ShapeType()=='Compound':
            ch=list(s)
            if not ch:raise ValueError('empty complete payload')
            for c in ch:visit(c)
        else:raise ValueError('loose complete payload '+s.ShapeType())
    visit(shape)
    return {'positive_solid_leaves':len(leaves),'hierarchy_shape_counts':counts,
      'all_raw_children_validated':True,'signed_volume_sum_mm3':sum(s.Volume() for s in leaves)}
def export(parts,name):
    path=ROOT/'cad'/name;path.parent.mkdir(exist_ok=True)
    sh=cq.Compound.makeCompound(list(parts.values()));cert=full_payload(sh)
    cq.exporters.export(sh,str(path));loaded=cq.importers.importStep(str(path))
    if len(loaded.vals())!=1:raise ValueError('unexpected top level STEP payload count')
    re=full_payload(loaded.val())
    if re['positive_solid_leaves']!=len(parts):raise ValueError('STEP payload count differs')
    return {'path':str(path.relative_to(ROOT)),'sha256':sha(path),'part_names':list(parts),
      'source_full_payload':cert,'reimport_full_payload':re,'parts_may_intersect':True,
      'manufacturing_go':False}
def pairs(parts,obs):
    ret={}
    for name,part in parts.items():
        per={}
        for label,other in obs.items():
            try:per[label]=strict_common(part,other)
            except Exception as exc:per[label]={'rejected_boolean':True,'exception':str(exc),'traceback':traceback.format_exc()}
        ret[name]=per
    return ret
def failures(p):
    return {n:{k:(v.get('checked_volume_mm3') if 'checked_volume_mm3' in v else v) for k,v in rows.items()
               if v.get('rejected_boolean') or v.get('checked_volume_mm3',0)>1e-7} for n,rows in p.items()}
def free(p):return all(not f for f in failures(p).values())
def inside_budget(body,budget):
    bb=body.BoundingBox()
    return all(getattr(bb,a+'min')>=budget[a+'min']-1e-7 and getattr(bb,a+'max')<=budget[a+'max']+1e-7 for a in 'xyz')
def carrier():
    # Exact R3 original carrier dimensions and DS-oriented PCB holes. The
    # R3 bodies omit copper, solder, components and flex; this stays explicit.
    holes=[(-15.,-12.),(15.,-12.),(-12.,12.)]
    def cyl(x,y,r,z0,z1):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0))
    base=box(-23,23,-21,21,-2,-1.1)
    for x,y in holes:base=base.fuse(cyl(x,y,.9,-2,2.4))
    for x in (-19,17):
        for y in (-17,15):base=base.fuse(box(x,x+2,y,y+2,-1.1,-.8))
    def board(z0,z1):
        b=box(-20,20,-18,18,z0,z1)
        for x,y in holes:b=b.cut(cyl(x,y,1,z0-.1,z1+.1))
        return b.clean()
    return {'R3_CARRIER_PROXY':base.clean(),'R3_DS_BOARD_ONLY':board(-.8,0),
      'R3_DP_RX180_BOARD_ONLY':board(.6,1.4),
      'BM28_24_MATED_DIMENSION_RESERVATION_NOT_VENDOR':box(-3.4,3.4,-.85,.85,0,.6),
      'CONDITIONAL_56UM_EXIT_GUIDE':box(20,23,-.6,.6,1.1-.028,1.1+.028)}

def run():
    start=time.monotonic();factory,frozen=obstacle_factory()
    before={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    source_before=sha(__file__);obs_cache={p:factory(s,q) for p,s,q in POSES}
    certs={p:{n:participant(b) for n,b in ob.items()} for p,ob in obs_cache.items()}
    write(ROOT/'obstacle_certificates.json',certs)
    anchors=[];old_stubs=[];exports=[]
    for pose,s,q in POSES:
        ob=obs_cache[pose];parts={}
        for end,point,direction in [('A',[32.7,70.,6.05],-1),('B',[32.7,15+s,-3.4+q],1)]:
            per={n:classify(point,b) for n,b in ob.items()}
            interior=[]
            for n,b in ob.items():
                if per[n]=='IN':
                    # Distance to all actual native faces, not distance to
                    # the volume (which would always be zero inside).
                    d=cq.Compound.makeCompound(b.Faces()).distance(cq.Vertex.makeVertex(*point))
                    interior.append({'obstacle':n,'nearest_actual_face_distance_mm':d})
            anchors.append({'pose':pose,'end':end,'point_xyz_mm':point,'native_states_all_23':per,'strict_interior':interior})
            for width in ['Y','Z']:
                x0,x1=sorted((point[0],point[0]+direction*.5));wy,wz=(1.2,.056) if width=='Y' else (.056,1.2)
                stub=box(x0,x1,point[1]-wy/2,point[1]+wy/2,point[2]-wz/2,point[2]+wz/2)
                tag=end+'_OLD_ANCHOR_WIDTH_'+width;parts[tag]=stub
                p=pairs({tag:stub},ob)
                old_stubs.append({'pose':pose,'case':tag,'length_mm':.5,'nominal_volume_mm3':stub.Volume(),'pairs':p,'positive_or_rejected':failures(p),
                  'no_supplier_dynamic_FPC_selected':True})
        exports.append(export({**ob,**parts},'REJECTED_OLD_ANCHOR_'+pose+'.step'))
    write(ROOT/'old_endpoint_counterexample.json',{'anchors':anchors,'finite_stubs':old_stubs,'bridge_deployment_zero_during_slide_and_normal_dock':True,
      'deployment_mapping_source':'r17_cad.py:a_moving_leaf docstring and run scenes; deployed after both axes seated',
      'fixed_historical_A_anchor_continuous_path_obstructed':True,'A_anchor_is_product_constraint':False,'manufacturing_go':False})
    # 48 explicitly bounded candidate points, not an exhaustive cavity search.
    point_rows=[]
    for x,y,z in itertools.product([31.5,32.7,33.625,34.5],[63.,70.,76.,85.],[5.5,6.05,6.75]):
        p=[x,y,z];states={pose:{n:classify(p,b) for n,b in ob.items()} for pose,ob in obs_cache.items()}
        point_rows.append({'point_xyz_mm':p,'pose_states_all_23':states,'outside_all_23_in_three_sampled_poses':all(v=='OUT' for row in states.values() for v in row.values())})
    write(ROOT/'bounded_point_relocations.json',{'requested_points':48,'rows':point_rows,'empty_point_is_mount_or_route_proof':False,'manufacturing_go':False})
    # Actual finite endpoint/short-guide reservations. The mating gap is not
    # the complete board/FPC/stiffener/clamp stack and is not called one.
    migration=[]
    for i,(x,y,z) in enumerate(itertools.product([32.,33.625],[60.,70.,80.],[5.4,6.05])):
        base={'BM28_24_DIMENSION_ONLY':box(x-.85,x+.85,y-3.4,y+3.4,z-.3,z+.3),
          'CONDITIONAL_W1P2_T56UM_L3_GUIDE':box(x-3,x,y-.6,y+.6,z-.028,z+.028)}
        rows=[]
        for pose,s,q in POSES:
            pr=pairs(base,obs_cache[pose]);rows.append({'pose':pose,'pairs':pr,'positive_or_rejected':failures(pr),'sampled_obstacle_clear':free(pr),
              'all_parts_within_original_A_research_proxy_bbox':all(inside_budget(b,certs[pose]['A_R38_CORE']['bounds_mm']) for b in base.values())})
        migration.append({'candidate':i,'hypothetical_static_A_anchor_xyz_mm':[x,y,z],'finite_rows':rows,
          'complete_installed_stack_known':False,'actual_full_PCB_or_clamp_installed':False,
          'manufacturing_go':False})
        if i in (0,7):exports.append(export({**obs_cache['STOW'],**base},'REJECTED_MIGRATED_RESERVATION_%02d.step'%i))
        print('migration',i,'clear',sum(r['sampled_obstacle_clear'] for r in rows),flush=True)
    write(ROOT/'finite_endpoint_relocations.json',{'bounded_candidate_count':12,'sampled_pose_count':3,'rows':migration,'manufacturing_go':False})
    # Move the actually built R3 research carrier, rather than pretending a
    # 0.6 mm connector box represents the complete static endpoint assembly.
    original=carrier();carrier_rows=[]
    for i,(y,z) in enumerate(itertools.product([25.,45.],[1.,3.])):
        placed={n:b.translate((0,y,z)) for n,b in original.items()};rows=[]
        for pose,s,q in POSES:
            pr=pairs(placed,obs_cache[pose]);rows.append({'pose':pose,'pairs':pr,'positive_or_rejected':failures(pr),'sampled_obstacle_clear':free(pr),
              'all_parts_within_original_A_research_proxy_bbox':all(inside_budget(b,certs[pose]['A_R38_CORE']['bounds_mm']) for b in placed.values())})
        carrier_rows.append({'candidate':i,'R3_carrier_relocation_xyz_mm':[0,y,z],'finite_rows':rows,'not_complete_phone_PCB':True,'manufacturing_go':False})
        if i in (0,3):exports.append(export({**obs_cache['STOW'],**placed},'REJECTED_STATIC_CARRIER_%02d.step'%i))
        print('actual R3 carrier relocation',i,'clear',sum(r['sampled_obstacle_clear'] for r in rows),flush=True)
    write(ROOT/'actual_carrier_relocations.json',{'bounded_candidate_count':4,'rows':carrier_rows,'not_exhaustive_proof_no_other_endpoint_architecture_exists':True,'manufacturing_go':False})
    after={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    if before!=after or source_before!=sha(__file__):raise ValueError('frozen inputs or running source changed')
    write(ROOT/'native_receipt.json',{'schema':'R7_BOUNDED_ENDPOINT_RELOCATION','host':platform.node(),'Python':platform.python_version(),'CadQuery':cq.__version__,
      'source_sha256_before':source_before,'source_sha256_after':sha(__file__),'frozen_R6_input_hashes_before':before,'frozen_R6_input_hashes_after':after,
      'frozen_inputs_unchanged':True,'fixed_anchor_cases':6,'old_finite_stub_cases':12,'bounded_point_candidates':48,
      'outside_all_23_point_candidates':sum(r['outside_all_23_in_three_sampled_poses'] for r in point_rows),
      'finite_migrated_reservation_candidates':12,'clear_all_three_pose_reservation_candidates':sum(all(r['sampled_obstacle_clear'] for r in c['finite_rows']) for c in migration),
      'actual_R3_carrier_candidates':4,'clear_all_three_pose_carrier_candidates':sum(all(r['sampled_obstacle_clear'] for r in c['finite_rows']) for c in carrier_rows),
      'exports':exports,'continuous_motion_or_actual_manufacturing_qualification':False,'real_equal_finished_housings_and_internal_cavities_known':False,
      'A_battery_capacity_allocation_verified':False,'candidate_route_accepted':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start})
    print(json.dumps({'exports':len(exports),'clear_points':sum(r['outside_all_23_in_three_sampled_poses'] for r in point_rows),'route_accepted':False,'manufacturing_go':False}),flush=True)
if __name__=='__main__':run()
