"""Verify execution identities and seal the finite R12 panel-fill investigation."""
from pathlib import Path
from fractions import Fraction as F
import datetime,gzip,hashlib,json

ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_text())
def ref(name):
    path=ROOT/name;return {'path':name,'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
    scopepath=ROOT/'R12_PANEL_FILL_SCOPE.json';manifestpath=ROOT/'R12_PANEL_FILL_DELIVERY_MANIFEST.json'
    assert not scopepath.exists() and not manifestpath.exists(),'sealed outputs already exist'
    native=read('native-boundaries-attempt4/report.json');coarse=read('fibre-intersection-attempt1/report.json')
    refine=read('exterior-refinement-attempt1/report.json');trim=read('trim-frontier-attempt1/report.json')
    for value in (native,coarse,refine,trim):assert value['completed']
    for report,source in ((native,'extract_complete_boundaries_r12_v4.py'),(coarse,'compute_fibre_intersection_r12.py'),
                          (refine,'refine_exterior_channels_r12.py'),(trim,'inspect_trim_frontier_r12.py')):
        assert sha(ROOT/source)==report['source']['sha256']
    assert sha(ROOT/'projected_boundary_r12.py')==refine['projection_source']['sha256']
    assert sha(ROOT/'inputs/complete_surface_support_v3.py')==native['support_source']['sha256']
    assert sha(ROOT/'native-boundaries-attempt4/report.json')==coarse['native_boundary_report']['sha256']==refine['native_report']['sha256']
    assert [native['bodies'][name]['native_face_count'] for name in ('A_BACK_PANEL','L_KEY','R_KEY')]==[298,92,92]
    for name,body in native['bodies'].items():assert sha(ROOT/'inputs'/f'{name}.brep')==body['input']['sha256']
    assert not trim['all_ordered_wires_exactly_closed'] and not trim['exact_trim_hole_refinement_admitted']
    assert trim['complete_ordered_edge_occurrences']==48
    reviews={name:read('independent-review/'+name) for name in
        ('FIBRE_COMPLETE_GRID_INDEPENDENT_REVIEW.json','EXTERIOR_LEDGER_INDEPENDENT_REVIEW.json','PCURVE_AND_TRIM_INDEPENDENT_REVIEW.json')}
    assert all(r['completed'] for r in reviews.values())
    gridreview=reviews['FIBRE_COMPLETE_GRID_INDEPENDENT_REVIEW.json']
    extreview=reviews['EXTERIOR_LEDGER_INDEPENDENT_REVIEW.json']
    trimreview=reviews['PCURVE_AND_TRIM_INDEPENDENT_REVIEW.json']
    assert gridreview['source']['sha256']==sha(ROOT/'independent-review/audit_fibre_covers_independently.py')
    assert extreview['source_sha256']==sha(ROOT/'independent-review/audit_exterior_ledger_independently.py')
    assert trimreview['source_sha256']==sha(ROOT/'independent-review/audit_pcurves_and_trim_frontier.py')
    assert extreview['projection_formula_source_sha256']==trimreview['projection_formula_source_sha256']==sha(ROOT/'independent-review/certify_key_bent_channels.py')
    assert extreview['sqrt_source_sha256']==trimreview['sqrt_source_sha256']==sha(ROOT/'inputs/complete_surface_support_v3.py')
    assert trimreview['trim_report_sha256']==sha(ROOT/'trim-frontier-attempt1/report.json')
    assert trimreview['pcurve_occurrences']==2544 and trimreview['nonzero_exact_joins']==44
    assert len(extreview['negative_controls'])==5 and all(c['rejected'] for c in extreview['negative_controls'])
    pairs=[]
    for index,key in enumerate(('L_KEY','R_KEY')):
        prior=coarse['pairs'][index];latest=refine['pairs'][index];independent=extreview['pairs'][index]
        assert latest['key']==independent['key']==key
        assert latest['remaining_upper_exact']==independent['exact_remaining_sum']
        assert F(latest['remaining_upper_exact'])>F(1e-7)
        assert not latest['original_1e_minus7_gate_passes_under_stated_model']
        assert prior['results']['XYZ_intersection']['exact_upper_mm3']==independent['exact_original_sum']
        assert latest['original_positive_boxes']==independent['complete_positive_boxes']
        assert latest['counts']['KEY_bent_negative_Y_then_outside_X']==independent['excluded_full_boxes']==2
        pairs.append({'key':key,'full_q_interval_exact':['0','12'],'whole_panel_fixed':True,
            'Z_fibre_upper_approx_mm3':prior['results']['Z_only']['upper_mm3_approx'],
            'XYZ_fibre_upper_approx_mm3':prior['results']['XYZ_intersection']['upper_mm3_approx'],
            'final_upper_exact_mm3':latest['remaining_upper_exact'],'final_upper_approx_mm3':latest['remaining_upper_mm3_approx'],
            'all_positive_RLE_boxes':latest['original_positive_boxes'],'exterior_channel_excluded_boxes':2,
            'original_1e_minus7_gate_passes_under_stated_model':False})
    scope={'schema':'razr-r12-current-panel-whole-key-filling-closeout-v1','sealed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'classification':'complete conditional conservative bound; residual inconclusive; no native/full-G2 qualification',
        'complete_boundary_face_count':482,'complete_pcurve_occurrences':2544,'pairs':pairs,
        'all_positive_cells_and_tiny_contributions_retained':True,'independent_full_grid_and_projection_review_complete':True,
        'independent_tamper_controls_rejected':5,'original_float64_threshold_exact':str(F(1e-7)),
        'original_spatial_split_limit':4096,'original_depth_limit':24,'additional_spatial_splits':0,'additional_depth':0,
        'trim_frontier':{'faces':[104,109,110,115,118,121],'native_closed_wires':12,'complete_ordered_edges':48,
            'nonzero_exact_endpoint_joins':44,'maximum_exact_UV_gap':trimreview['maximum_exact_UV_join_gap'],
            'hole_subtraction_admitted':False,'native_tolerance_or_endpoint_snapping_substituted_for_proof':False},
        'actual_collision_proved':False,'native_material_set_identity_proved':False,'uniform_compiled_error_proved':False,
        'continuous_G2':False,'whole_15D_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False,
        'retained_failed_native_attempts':['native-boundaries-attempt1','native-diagnostic-attempt2','native-boundaries-attempt3'],
        'reports':[ref(n) for n in ['native-boundaries-attempt4/report.json','fibre-intersection-attempt1/report.json',
            'exterior-refinement-attempt1/report.json','trim-frontier-attempt1/report.json',
            *['independent-review/'+n for n in reviews]]],
        'seal_source':ref('seal_panel_fill_r12.py')}
    scopepath.write_text(json.dumps(scope,indent=2)+'\n')
    entries=[]
    for path in sorted(ROOT.rglob('*')):
        assert not path.is_symlink(),'archive must not contain symlinks'
        if path.is_file() and path!=manifestpath:
            assert '__pycache__' not in path.parts,'bytecode cache is not source evidence'
            entries.append(ref(path.relative_to(ROOT).as_posix()))
    manifest={'schema':'razr-r12-panel-fill-complete-delivery-manifest-v1','file_count_excluding_self':len(entries),
        'bytes_excluding_self':sum(r['bytes'] for r in entries),'scope_sha256':sha(scopepath),'files':entries,
        'physical_qualification_or_manufacturing_release':False}
    manifestpath.write_text(json.dumps(manifest,indent=2)+'\n')
    # Re-read every file after serialization: the manifest describes this sealed snapshot.
    assert all((ROOT/r['path']).stat().st_size==r['bytes'] and sha(ROOT/r['path'])==r['sha256'] for r in entries)
    print(json.dumps({'file_count_excluding_self':len(entries),'bytes_excluding_self':manifest['bytes_excluding_self'],
                      'scope_sha256':sha(scopepath),'manifest_sha256':sha(manifestpath),'final_upper_approx_mm3':[r['final_upper_approx_mm3'] for r in pairs]}))

if __name__=='__main__':main()
