#!/usr/bin/env python3
"""Fresh whole-payload STEP verification; does not import the R7 builder."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'fpc-g2-route-candidates-20261013-r6/recovered_x230/input/guards'))
from strict_intersections import participant,strict_common
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads((ROOT/p).read_text())
def leaves(roots):
    out=[];types={}
    def visit(s):
        name=s.ShapeType();types[name]=types.get(name,0)+1
        if name=='Compound':
            children=list(s)
            if not children:raise ValueError('empty compound')
            for c in children:visit(c)
        elif name=='Solid':participant(s);out.append(s)
        else:raise ValueError('extra raw topology '+name)
    for s in roots:visit(s)
    return out,types
def match(parts,certificate):
    matches=[]
    for shape in parts:
        c=participant(shape)
        if abs(c['signed_volume_mm3']-certificate['signed_volume_mm3'])<1e-5 and all(abs(c['bounds_mm'][k]-v)<1e-6 for k,v in certificate['bounds_mm'].items()):matches.append(shape)
    if len(matches)!=1:raise ValueError('ambiguous/missing complete participant: '+str(len(matches)))
    return matches[0]
def compare(a,b,expected):
    r=strict_common(a,b)
    if abs(r['checked_volume_mm3']-expected['checked_volume_mm3'])>1e-6:raise ValueError('independent actual common changed')
    return {'actual_volume_mm3':r['checked_volume_mm3'],'original_checked_volume_mm3':expected['checked_volume_mm3'],'absolute_difference_mm3':abs(r['checked_volume_mm3']-expected['checked_volume_mm3']),
      'OCC_boolean_was_run':r['OCC_boolean_was_run']}
def run():
    start=time.monotonic();native=load('native_receipt.json');old=load('old_endpoint_counterexample.json');cert=load('obstacle_certificates.json')
    before={x['path']:sha(ROOT/x['path']) for x in native['exports']};out=[];checks=[];interior=[]
    for entry in native['exports']:
        name=entry['path'];wp=cq.importers.importStep(str(ROOT/name));raw=wp.vals()
        if len(raw)!=1:raise ValueError('multiple top-level payloads')
        parts,types=leaves(raw)
        if len(parts)!=entry['source_full_payload']['positive_solid_leaves']:raise ValueError('incomplete native payload')
        out.append({'path':name,'sha256':sha(ROOT/name),'complete_raw_hierarchy':types,'all_positive_solid_leaves':len(parts),'non_solid_leaves':0,
          'signed_volume_sum_mm3':sum(s.Volume() for s in parts),'parts_may_intersect':True})
        if 'OLD_ANCHOR_' in name:
            pose=name.removeprefix('cad/REJECTED_OLD_ANCHOR_').removesuffix('.step');bridge=match(parts,cert[pose]['A_MOVING_BRIDGE_DEPLOY_0.0_PROXY'])
            cl=BRepClass3d_SolidClassifier(bridge.wrapped);cl.Perform(gp_Pnt(32.7,70.,6.05),1e-7)
            if cl.State()!=TopAbs_IN:raise ValueError('A point did not remain strictly inside parked bridge after STEP')
            distance=cq.Compound.makeCompound(bridge.Faces()).distance(cq.Vertex.makeVertex(32.7,70.,6.05))
            if abs(distance-.35)>1e-6:raise ValueError('actual interior margin changed')
            interior.append({'pose':pose,'A_point_strictly_inside_imported_parked_bridge':True,'distance_to_actual_faces_mm':distance})
            for row in old['finite_stubs']:
                if row['pose']!=pose:continue
                expected=row['pairs'][row['case']]['A_MOVING_BRIDGE_DEPLOY_0.0_PROXY'];stub=match(parts,expected['a'])
                checks.append({'path':name,'case':row['case'],'versus':'A_MOVING_BRIDGE_DEPLOY_0.0_PROXY',**compare(stub,bridge,expected)})
        elif 'STATIC_CARRIER_' in name:
            index=int(name.split('_')[-1].split('.')[0]);row=load('actual_carrier_relocations.json')['rows'][index]['finite_rows'][0]
            body=match(parts,cert['STOW']['A_R38_CORE'])
            for case,pairs in row['pairs'].items():
                expected=pairs['A_R38_CORE']
                if 'checked_volume_mm3' not in expected:raise ValueError('builder rejection needs separate original diagnostic, not hidden')
                own=match(parts,expected['a']);checks.append({'path':name,'case':case,'versus':'A_R38_CORE',**compare(own,body,expected)})
        elif 'MIGRATED_RESERVATION_' in name:
            index=int(name.split('_')[-1].split('.')[0]);row=load('finite_endpoint_relocations.json')['rows'][index]['finite_rows'][0]
            for case,pairs in row['pairs'].items():
                for obstacle in ['A_R38_CORE','A_MOVING_BRIDGE_DEPLOY_0.0_PROXY']:
                    expected=pairs[obstacle]
                    if 'checked_volume_mm3' not in expected:raise ValueError('builder rejected common retained')
                    own=match(parts,expected['a']);body=match(parts,expected['b'])
                    checks.append({'path':name,'case':case,'versus':obstacle,**compare(own,body,expected)})
    after={x['path']:sha(ROOT/x['path']) for x in native['exports']}
    if before!=after:raise ValueError('actual STEP bytes changed')
    report={'host':platform.node(),'CadQuery':cq.__version__,'script_sha256':sha(Path(__file__)),'exports':out,'native_recomputed_common_pairs':checks,
      'independent_A_interior_margin':interior,'whole_positive_solid_leaf_count':sum(x['all_positive_solid_leaves'] for x in out),'STEP_hashes_before':before,'STEP_hashes_after':after,
      'builder_imported':False,'same_host_fresh_independent_process':True,'actual_phone_assembly_or_material_qualification':False,'candidate_route_accepted':False,
      'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (ROOT/'independent_STEP_verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'STEPs':len(out),'positive_solid_leaves':report['whole_positive_solid_leaf_count'],'native_common_pairs':len(checks),'manufacturing_go':False}))
if __name__=='__main__':run()
