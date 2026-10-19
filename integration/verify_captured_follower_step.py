"""Read captured-follower STEP independently of every geometry builder.

Checks file identities, complete solid counts, validity, positive finite
volumes and declared volume/bounds signatures. Combined placements derive
from the report's subassembly members and action offsets, with the outer tube
and already-positioned CAM strip as explicit zero datums. This is not Boolean
shape equivalence, an independent CAD kernel, or a physical joining proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


HEX = re.compile(r'^[0-9a-f]{64}$')
EXPECTED_PARTS = {
    'TUBE_0_OPEN_BOTTOM', 'TUBE_0_BOTTOM_CAP',
    'TUBE_1_OPEN_BOTTOM', 'TUBE_1_BOTTOM_CAP',
    'TUBE_2_OPEN_BOTTOM', 'TUBE_2_BOTTOM_CAP',
    'CORE_STEM', 'CORE_BOTTOM_SHOULDER',
    'CAM_LOWER_FLANGE', 'CAM_UPPER_FLANGE',
    'KEY_FOLLOWER_WITHOUT_LOWER_FLANGE', 'KEY_LOWER_FLANGE',
    'CAM_SLOT_REFERENCE', 'KEY_SLOT_REFERENCE',
}
FORBIDDEN_BUILDERS = {
    'cam_coupling', 'captured_follower_assembly',
    'product_assembly', 'product_split_assembly',
}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def finite(value, label):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(label+': finite real number required')
    return float(value)


def verified_file(directory, rec):
    filename, digest = rec['file'], rec['sha256']
    if not isinstance(filename, str) or not isinstance(digest, str) or not HEX.fullmatch(digest):
        raise ValueError('invalid file identity')
    rel = Path(filename)
    if rel.name != str(rel):
        raise ValueError('STEP must be a direct file member')
    path = directory/rel
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or nonregular STEP')
    if sha_bytes(path.read_bytes()) != digest:
        raise ValueError('STEP SHA256 differs: '+filename)
    return path


def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    result = [x0, x1, y0, y1, z0, z1]
    if not all(math.isfinite(x) for x in result):
        raise ValueError('nonfinite STEP bounds')
    return result


def solids_from(path):
    roots = cq.importers.importStep(str(path)).vals()
    solids = [solid for root in roots for solid in root.Solids()]
    for solid in solids:
        v = solid.Volume()
        if not solid.isValid() or not math.isfinite(v) or v <= 0:
            raise ValueError('invalid or nonpositive STEP solid')
    return solids


def checked_signature(expected):
    ev = finite(expected['volume_mm3'], 'declared volume')
    eb = expected['bounds_mm']
    if ev <= 0 or not isinstance(eb, list) or len(eb) != 6:
        raise ValueError('invalid declared geometry signature')
    eb = [finite(x, 'declared bound') for x in eb]
    if any(eb[2*i+1] <= eb[2*i] for i in range(3)):
        raise ValueError('empty or reversed declared bounds')
    return ev, eb


def signature_matches(solid, expected):
    ev, eb = checked_signature(expected)
    return (abs(solid.Volume()-ev) <= max(1e-7, abs(ev)*1e-8)
            and max(abs(a-b) for a, b in zip(bounds(solid), eb)) <= 1e-6)


def verify(directory, output):
    directory, output = Path(directory).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('use a new readback output; existing output cannot be overwritten')
    source_bytes = Path(__file__).read_bytes()
    report_path = directory/'report.json'
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError('report must be a regular file')
    report_bytes = report_path.read_bytes()
    r = json.loads(report_bytes)
    if r.get('schema') != 'razr-captured-follower-assembly-study-v1':
        raise ValueError('unrecognized captured-follower report')
    if not isinstance(r.get('parts'), list) or len(r['parts']) != 14:
        raise ValueError('fourteen individual parts required')
    if type(r['combined'].get('expected_solids')) is not int or r['combined']['expected_solids'] != 11:
        raise ValueError('combined report must declare eleven solids')
    if r['subassembly_members'].get('placement_values_are_axial_translation_mm') is not True:
        raise ValueError('explicit axial subassembly placements required')
    for field in ('study_source_sha256', 'construction_source_sha256'):
        if not isinstance(r.get(field), str) or not HEX.fullmatch(r[field]):
            raise ValueError('invalid source identity: '+field)
    parts = {row['part']: row for row in r['parts']}
    if set(parts) != EXPECTED_PARTS or len({x['file'] for x in r['parts']}) != 14:
        raise ValueError('missing, unexpected or duplicate part name/file')
    single_results = []
    for name, rec in sorted(parts.items()):
        path = verified_file(directory, rec)
        solids = solids_from(path)
        if type(rec.get('valid_solids')) is not int or len(solids) != rec['valid_solids'] or len(solids) != 1:
            raise ValueError('wrong individual solid count: '+name)
        if not signature_matches(solids[0], rec):
            raise ValueError('individual signature differs: '+name)
        single_results.append({'part': name, 'file': path.name, 'sha256': rec['sha256'],
            'valid_positive_solids': 1, 'observed_volume_mm3': solids[0].Volume(),
            'observed_bounds_mm': bounds(solids[0]), 'declared_volume_and_bounds_match': True})

    def action(number):
        matches = [a for a in r['assembly_actions']
                   if a['action'].startswith(str(number)+' ')]
        if len(matches) != 1:
            raise ValueError('missing or duplicate assembly action')
        return matches[0]

    # The outer tube remains at its exported origin. The CAM strip file already
    # contains its assembled coordinates. Other placements come from the report.
    placements = {'TUBE_0_OPEN_BOTTOM': 0.,
        'TUBE_0_BOTTOM_CAP': finite(action(7)['moving_final_shift_z_mm'], 'outer cap shift'),
        'CAM_SLOT_REFERENCE': 0.}
    outer_shift = finite(action(6)['moving_final_shift_z_mm'], 'middle subassembly shift')
    members = r['subassembly_members']['MIDDLE_AND_INNER_UNIT_relative_to_tube_1']
    expected_members = {'TUBE_1_OPEN_BOTTOM', 'TUBE_1_BOTTOM_CAP',
        'TUBE_2_OPEN_BOTTOM', 'TUBE_2_BOTTOM_CAP', 'CORE_STEM', 'CORE_BOTTOM_SHOULDER'}
    if not isinstance(members, dict) or set(members) != expected_members:
        raise ValueError('incomplete middle/inner subassembly membership')
    for name, inner_shift in members.items():
        placements[name] = outer_shift+finite(inner_shift, 'nested subassembly shift')
    placements['CAM_LOWER_FLANGE'] = finite(action(8)['moving_final_shift_z_mm'], 'lower flange shift')
    placements['CAM_UPPER_FLANGE'] = finite(action(10)['moving_final_shift_z_mm'], 'upper flange shift')
    if len(placements) != 11:
        raise ValueError('incomplete assembled placement map')
    expected = {}
    for name, dz in placements.items():
        ev, bb = checked_signature(parts[name])
        bb[4] += dz; bb[5] += dz
        expected[name] = {'volume_mm3': ev, 'bounds_mm': bb}

    combined_path = verified_file(directory, r['combined'])
    combined_solids = solids_from(combined_path)
    if len(combined_solids) != 11:
        raise ValueError('combined STEP must contain eleven solids')
    unmatched, combined_matches = dict(expected), []
    for solid in combined_solids:
        names = [name for name, rec in unmatched.items() if signature_matches(solid, rec)]
        if len(names) != 1:
            raise ValueError('missing or ambiguous combined geometry signature')
        name = names[0]; unmatched.pop(name); combined_matches.append(name)
    if unmatched:
        raise ValueError('declared assembled participant missing')
    builder_names = sorted(name for name in sys.modules if name.rsplit('.', 1)[-1] in FORBIDDEN_BUILDERS)
    if builder_names:
        raise ValueError('builder imported by independent reader: '+', '.join(builder_names))
    # Verify that the report, this reader, and all actual STEP bytes retained
    # their identities during the readback operation.
    if report_path.read_bytes() != report_bytes or Path(__file__).read_bytes() != source_bytes:
        raise ValueError('report or reader changed during readback')
    for rec in [*r['parts'], r['combined']]:
        verified_file(directory, rec)
    result = {'schema': 'razr-captured-follower-step-readback-v1',
        'reader_sha256': sha_bytes(source_bytes), 'report_sha256': sha_bytes(report_bytes),
        'study_source_sha256': r['study_source_sha256'],
        'construction_source_sha256': r['construction_source_sha256'],
        'runtime_cadquery': cq.__version__, 'individual_parts': single_results,
        'combined': {'file': combined_path.name, 'sha256': r['combined']['sha256'],
            'valid_positive_solids': len(combined_solids),
            'matched_participants': sorted(combined_matches),
            'derived_expected_z_placements_mm': placements,
            'placement_basis': 'report subassembly members and action offsets; outer tube and already-positioned CAM strip use exported zero datum',
            'sum_observed_solid_volumes_mm3': sum(s.Volume() for s in combined_solids),
            'sum_expected_solid_volumes_mm3': sum(x['volume_mm3'] for x in expected.values()),
            'all_volume_and_bounds_signatures_match': True},
        'builder_modules_imported': False, 'independent_CAD_kernel': False,
        'boolean_shape_equivalence_checked': False,
        'joint_strength_or_full_phone_assembly_checked': False,
        'passed': True, 'manufacturing_go': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.directory, args.output)
    print(json.dumps({'passed': result['passed'],
        'individual_parts': len(result['individual_parts']),
        'combined_solids': result['combined']['valid_positive_solids'],
        'boolean_shape_equivalence_checked': False}))
