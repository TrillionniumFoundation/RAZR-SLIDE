"""Do the two declared finite groove caps enforce the ContactProfile q limits?

Exact longitudinal projection on the source capsule centerlines only. This is
not a whole-assembly feasibility, force or native CAD qualification.
"""
from __future__ import annotations
import argparse
import ast
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import subprocess


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository',type=Path,required=True)
    ap.add_argument('--slot-domain',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();domain=json.loads(args.slot_domain.read_text());S4=domain['functional_source_commit']
    raw=subprocess.check_output(['git','-C',str(args.repository),'show',S4+':integration/cam_coupling.py'])
    require_hash=domain['source_identities']['integration/cam_coupling.py']['sha256']
    assert hashlib.sha256(raw).hexdigest()==require_hash
    tree=ast.parse(raw);values={}
    def evaluate(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.Name):return values[node.id]
        if isinstance(node,ast.Tuple):return tuple(evaluate(x) for x in node.elts)
        if isinstance(node,ast.BinOp):
            a,b=evaluate(node.left),evaluate(node.right)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
            if isinstance(node.op,ast.Div):return a/b
        raise ValueError('not an approved source arithmetic expression')
    wanted={'STROKE','KEY_STROKE','RATIO','X0','Y_CAM','Y_OUTPUT','PIN_RADIUS','SLOT_RADIUS'}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in wanted:
            values[n.targets[0].id]=evaluate(n.value)
    assert wanted<=set(values)
    templates=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='templates')
    for n in templates.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('a','b','c','d'):
            values[n.targets[0].id]=evaluate(n.value)
    grooves={'B_CAM':(values['a'],values['b']),'KEY_YOKE':(values['c'],values['d'])}
    rows=[]
    for index,vertex in enumerate(domain['exact_slot_only_vertices']):
        s,dxL,dqL,dxR,dqR=map(F,vertex['coordinates_exact']);q=F(values['RATIO'])*s
        for side,dx,dq in (('L',dxL,dqL),('R',dxR,dqR)):
            points={'B_CAM':(F(values['X0'])+q+dx,F(values['Y_CAM'])-s),
                    'KEY_YOKE':(F(values['X0'])+q+dx,F(values['Y_OUTPUT'])-q-dq)}
            for name,(a,b) in grooves.items():
                a,b=tuple(map(F,a)),tuple(map(F,b));d=tuple(y-x for x,y in zip(a,b));den=sum(x*x for x in d)
                t=sum((v-u)*dv for u,v,dv in zip(a,points[name],d))/den
                distance2=min(t,1-t)**2*den
                radius2=F(values['PIN_RADIUS'])**2
                rows.append({'source_vertex_index':index,'side':side,'groove':name,
                    'line_projection_parameter_exact':str(t),'nearest_cap_transition_plane_distance_squared_mm2':str(distance2),
                    'pin_radius_squared_mm2':str(radius2),'complete_pin_disk_longitudinally_inside_straight_region':0<t<1 and distance2>radius2,
                    'distance_to_transition_plane_approx_mm':math.sqrt(float(distance2)),
                    'q_exact_mm':str(q+dq),'q_outside_profile':q+dq<0 or q+dq>12})
    assert len(rows)==128 and all(x['complete_pin_disk_longitudinally_inside_straight_region'] for x in rows)
    result={'schema':'razr-S4-finite-groove-endcap-source-projection-v1','functional_source_commit':S4,
        'cam_coupling_source_sha256':require_hash,'slot_domain_sha256':hashlib.sha256(args.slot_domain.read_bytes()).hexdigest(),
        'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_constants':{k:values[k] for k in wanted},'source_capsule_centerline_endpoints_mm':grooves,
        'all_exact_vertex_projections':rows,'projection_count':len(rows),
        'minimum_transition_plane_distance_by_groove_approx_mm':{name:min(x['distance_to_transition_plane_approx_mm'] for x in rows if x['groove']==name) for name in grooves},
        'exact_squared_distance_checks_exceed_pin_radius_squared_for_all_vertices':True,
        'whole_source_polytope_longitudinal_scope':'Projection is affine in each source coordinate, so its min/max occur at the saved 32 vertices; the complete declared radius-0.4 disk remains in the central straight region of both capsules.',
        'endcaps_of_these_two_source_grooves_enforce_q_0_or_12':False,
        'normal_sidewall_or_3D_clearance_qualified':False,'other_actual_hard_stops_excluded':False,
        'out_of_profile_states_proved_physically_reachable':False,
        'new_CAD_executed':False,'physical_allowed_domain_proved':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('projection_count','minimum_transition_plane_distance_by_groove_approx_mm','endcaps_of_these_two_source_grooves_enforce_q_0_or_12')}))


if __name__=='__main__':main()
