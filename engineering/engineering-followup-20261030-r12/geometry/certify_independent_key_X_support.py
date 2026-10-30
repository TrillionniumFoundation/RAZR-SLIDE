"""Exact interval separation of complete current KEY boundary representations.

This certificate intentionally distinguishes its mathematical compact-filling
premise from a completed proof of actual native BREP filling semantics.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,datetime

ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

rows={}
for role,path in [('producer',ROOT/'producer-v6/report.json'),('reader',ROOT/'reader-v2/report.json')]:
    d=json.loads(path.read_text());assert d['completed']
    intervals={};counts={}
    for side in 'LR':
        faces=d['sides'][side]['complete_face_inventory'];assert len(faces)==92
        boxes=[];edge_count=0
        for face in faces:
            c=face['complete_face_support_certificate']
            assert c['all_complete_trim_curves_edges_vertices_included']
            assert c['edge_occurrences_including_opposite_cylinder_seams_enumerated']
            box=[tuple(map(F,p)) for p in c['complete_swept_support']]
            assert all(a<=b for a,b in box)
            assert list(map(F,c['motion_exact'])) in ([F(0),F(12),F(0)],[F(0),F(-12),F(0)])
            boxes.append(box);edge_count+=len(c['edges'])
        intervals[side]=(min(b[0][0] for b in boxes),max(b[0][1] for b in boxes))
        counts[side]={'complete_faces':len(faces),'complete_edge_occurrences':edge_count}
    gap=intervals['R'][0]-intervals['L'][1]
    assert gap>0
    rows[role]={'input_report':str(path.relative_to(ROOT)),'input_sha256':sha(path),
        'complete_X_carriers_exact_mm':{s:list(map(str,v)) for s,v in intervals.items()},
        'counts':counts,'positive_exact_X_gap_mm':str(gap),'positive_gap_approx_mm':float(gap),
        'independent_q_L_q_R_box_mm':[[0,12],[0,12]],
        'exact_represented_boundary_halfspace_separation':True,
        'actual_native_compact_fill_bridge_fully_proved':False}

result={'schema':'razr-r12-whole-current-KEY-independent-q-X-separation-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),
    'roles':rows,
    'mathematical_proof':[
        'Every serialized analytic face, full trim pcurve, 3-D edge and vertex over every q in its admitted interval is enclosed in the recorded boxes.',
        'The union of those boxes is enclosed in the recorded X halfspaces.',
        'For any compact material K, if its complete boundary is inside x<=a then K is inside x<=a: a point with x>a would have a boundary point at least as far in +X along its finite exit ray. The analogous lower halfspace follows using -X.',
        'Under that complete-boundary/material premise, each independent KEY stays in its halfspace for all q. The positive rational gap makes the two whole materials disjoint for every independent q_L,q_R in [0,12].'],
    'scope':{'uses_native_Common_zero_as_upper_bound':False,
        'uses_AddOptimal_numeric_bounds_as_exact_support':False,
        'full_source_analytic_representations_used':True,
        'formal_native_BREP_filling_or_uniform_compiled_error_bridge_complete':False,
        'physical_allowed_domain_proved':False,'all_15D_G2_qualified':False,
        'G3':False,'G4':False,'G5':False,'manufacturing_go':False}}
(ROOT/'INDEPENDENT_KEY_X_SUPPORT_CERTIFICATE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({role:r['positive_gap_approx_mm'] for role,r in rows.items()}))
