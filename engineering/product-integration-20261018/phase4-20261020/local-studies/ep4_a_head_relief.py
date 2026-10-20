#!/usr/bin/env python3
"""Bounded A-web head relief on the identified EP4 endpoint; no shell edits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root, out = args.repository_root.resolve(), args.output.resolve()
    sys.path.insert(0, str(root/'integration'))
    import cadquery as cq
    import product_assembly as p
    import product_routing_ep4 as ep
    import product_fpc as f
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert sha(root/'integration/product_routing_ep4.py') == 'f8286416e8d4f835b5a280f3c76e7dd69aaebda25ac2217f40f33e19e92251b8'
    assert not out.exists() and out != root and root not in out.parents
    before = ep.source_identity()
    out.mkdir(parents=True)
    c = ep.load_config()
    original = ep.ep4_local_parts('A', c)
    parent = original['inner_carrier_jaw']
    # A factory mirrors material Y into negative endpoint-local Y. The first
    # actual head is R1.75, local (0,-15), Z .85..1.45. This R1.95 relief starts
    # exactly above the bearing face; it does not remove that face or thread.
    tool = cq.Solid.makeCylinder(1.95, .8, cq.Vector(0., -15., .85))
    modified = p.single(parent.cut(tool).clean())
    revised = {**original, 'inner_carrier_jaw': modified}
    removed = parent.cut(modified)
    added = modified.cut(parent)
    removed_volume, added_volume = p.volume(removed), p.volume(added)
    old_common = p.strict_common(original['M2_clamp_head_1'], parent)['common_mm3']
    new_common = p.strict_common(original['M2_clamp_head_1'], modified)['common_mm3']
    probes = {}
    for side, x0, x1 in [('L', -5.7, -5.5), ('R', 5.5, 5.7)]:
        probe = p.box((x0, -13.6, .82), (x1, -13.4, 3.2))
        probes[side] = {'probe_mm3': p.volume(probe),
                       'contained_mm3': p.strict_common(probe, modified)['common_mm3'],
                       'role': 'finite side web bridge across the retained transfer window height'}
    bearing = cq.Solid.makeCylinder(1.75, .05, cq.Vector(0., -15., .8)).cut(
        cq.Solid.makeCylinder(1.1, .05, cq.Vector(0., -15., .8)))
    bearing_volume = p.volume(bearing)
    bearing_retained = p.strict_common(bearing, modified)['common_mm3']
    named = {'A_'+name: body for name, body in revised.items()}
    self_pairs = ep.native_pairs(named, out/'A-local-self', c, coordinate_frame='A endpoint local, same proper material frame as EP4')
    endpoint = ep.export_shape(cq.Compound.makeCompound(list(revised.values())), out/'A-complete-head-relief.step')
    endpoint['parts'] = {name: ep.native_metrics(body) for name, body in sorted(revised.items())}
    artifacts = {'complete_endpoint': endpoint,
        'removed_material': ep.export_shape(removed, out/'A-web-removed-material.step'),
        'explicit_head_clearance_tool': ep.export_shape(tool, out/'A-head-relief-tool.step')}
    # Changed material is a subset of the old carrier. This monotonic argument
    # prevents new material intersections under the same proper rigid motion;
    # it does not preserve strength, retention, support or sealing capability.
    fields = {'unchanged_other_endpoint_parts': all(revised[k] is original[k] for k in original if k != 'inner_carrier_jaw'),
        'one_valid_connected_carrier': ep.native_metrics(modified)['positive_valid_solids'] == 1,
        'old_actual_head_web_common_preserved_as_counterexample': abs(old_common-.18081185628459612) < 1e-8,
        'new_head_web_Common_zero_within_native_tolerance': new_common <= ep.TOL,
        'new_material_added': added_volume > 0.0,
        'both_finite_side_web_connections_retained': all(abs(q['probe_mm3']-q['contained_mm3']) <= ep.TOL for q in probes.values()),
        'complete_nominal_bearing_annulus_retained': abs(bearing_volume-bearing_retained) <= ep.TOL,
        'all_190_self_pairs_clear_without_error': self_pairs['no_Common_above_tolerance_or_evaluation_error']}
    qualified = (fields['unchanged_other_endpoint_parts'] and fields['one_valid_connected_carrier'] and
        fields['old_actual_head_web_common_preserved_as_counterexample'] and
        fields['new_head_web_Common_zero_within_native_tolerance'] and not fields['new_material_added'] and
        fields['both_finite_side_web_connections_retained'] and fields['complete_nominal_bearing_annulus_retained'] and
        fields['all_190_self_pairs_clear_without_error'])
    after = ep.source_identity()
    assert before == after
    report = {'schema': 'razr-ep4-A-head-local-relief-v1', 'runtime': ep.runtime_identity(),
        'script': {'path': str(Path(__file__).resolve()), 'sha256': sha(__file__)},
        'basis_native_source_commit': '9a8307fe4bd4163b53515698fb12cfc0a8cc27e7',
        'basis_source_sha256': before, 'basis_source_bytes_unchanged': True,
        'coordinate_frame': 'A endpoint local; A material tail is negative Y',
        'actual_head': {'center_XY_mm': [0.,-15.], 'radius_mm': 1.75, 'Z_mm': [.85,1.45]},
        'relief': {'center_XY_mm': [0.,-15.], 'radius_mm': 1.95, 'Z_mm': [.85,1.65],
                   'nominal_radial_clearance_mm': .2, 'bearing_plane_Z_mm': .85},
        'material_accounting': {'original_mm3': p.volume(parent), 'removed_mm3': removed_volume,
                               'added_mm3': added_volume, 'new_mm3': p.volume(modified)},
        'head_Common_mm3': {'original': old_common, 'revised': new_common},
        'side_web_volume_probes': probes,
        'bearing_annulus_mm3': {'specified': bearing_volume, 'retained': bearing_retained},
        'self_pairs': self_pairs, 'artifacts': artifacts, 'checks': fields,
        'local_declared_geometry_checks_passed': qualified,
        'baseline_EP4_source_or_assemblies_modified': False,
        'new_external_intersections_precluded_by_material_subset_only': added_volume == 0.0,
        'subset_claim_scope': 'same obstacle geometry and same rigid placement; no statement that old external pairs are clear',
        'thread_or_fastener_retention_defined': False, 'strength_or_manufacturing_qualified': False,
        'whole_phone_candidate_accepted': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False}
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'local_declared_geometry_checks_passed': qualified, 'head_Common_mm3': report['head_Common_mm3'],
                      'material_accounting': report['material_accounting'], 'checks': fields},indent=2))
    return 0 if qualified else 1


if __name__ == '__main__':
    raise SystemExit(main())
