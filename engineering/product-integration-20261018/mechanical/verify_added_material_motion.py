"""Continuous nominal relative-motion check for every added material region.

Cuts cannot create positive material intersection. This check therefore takes
the exact added material of each changed native part, all entirely new fixed
parts, and compares them with the full current mechanical/allocation scene.
It complements the dedicated OLED, installation and endpoint checks. It does
not requalify the inherited motion or nonnominal joint allocations.
"""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'integration'))
import product_assembly as p
from straight_envelope import whole_material
from translation_regions import regions

TOL = 1e-7


def displacement(a, b):
    aa, bb = p.bounds(a), p.bounds(b)
    move = tuple(bb[2*i] - aa[2*i] for i in range(3))
    if max(abs(bb[2*i+1] - aa[2*i+1] - move[i]) for i in range(3)) > TOL:
        raise ValueError('participant is not a rigid translation')
    moved = a.translate(move)
    if max(p.volume(moved.cut(b)), p.volume(b.cut(moved))) > TOL:
        raise ValueError('native endpoint identity differs')
    return move


def axis_gap(a, b, move=(0., 0., 0.)):
    return max(max(a[2*i] + min(0., move[i]) - b[2*i+1],
                   b[2*i] - a[2*i+1] - max(0., move[i])) for i in range(3))


def verify():
    started = time.monotonic()
    hashes = {path: p.sha(ROOT / path) for path in (
        'integration/product_assembly.py', 'design/product_geometry.json',
        'integration/translation_regions.py', 'integration/straight_envelope.py',
        str(Path(__file__).relative_to(ROOT)))}
    poses = ((0., 0., 0.), (0., 0., 3.), (79.75, 0., 3.), (79.75, 8.2, 3.))
    scenes = []
    for s, d, u in poses:
        scene, _ = p.product_scene(s, d, u, u)
        scene.update(p.registered_components(slide_mm=s, descent_mm=d))
        scenes.append(scene)
    native, _ = p.native_scene()
    changed = set(p.load_config()['current_product_candidate']['changed_native_parts'])
    entirely_new = set(scenes[0]) - set(native) - set(p.registered_components())
    added = {}
    accounting = {}
    for name in sorted(changed | entirely_new):
        current = scenes[0][name]
        gain = current.cut(native[name]) if name in changed else current
        leaves, total = whole_material(gain, empty=True)
        if not leaves:
            raise ValueError('declared addition has no positive material')
        accounting[name] = {'material_regions': len(leaves), 'added_mm3': total,
                            'entirely_new_part': name in entirely_new}
        for i, body in enumerate(leaves):
            added[name + ':' + str(i)] = (name, body)
    print('ADDED_MATERIAL_INITIALIZED', len(added), 'REGIONS', flush=True)
    non_affine = {name for name in scenes[0] if '_STOP_' in name or '_SPRING_' in name}
    profiles = p.native_inputs()[4]
    profile_receipts = {side: [profile.receipt() for profile in side_profiles]
                        for side, side_profiles in profiles.items()}
    # ContactProfile has an ordered constant / descending rounded corner /
    # descending ramp / constant branch. Its extrema therefore lie at q=0,12.
    # The spring reservation's X length grows monotonically from that height.
    # These eight participants use their full endpoint AABB UNION, not a false
    # assumption that their position/shape varies affinely with slide time.
    translations = []
    for first, last in zip(scenes, scenes[1:]):
        moves = {name: ((0., 0., 0.) if name in non_affine else displacement(first[name], last[name]))
                 for name in first}
        translations.append(moves)
    offsets = {name: (0., 0., 0.) for name in scenes[0]}
    checks = []
    failures = []
    for index, phase in enumerate(('UNLOCK', 'SLIDE', 'SEAT')):
        current = dict(scenes[index])
        for name in non_affine:
            aa, bb = p.bounds(scenes[index][name]), p.bounds(scenes[index+1][name])
            current[name] = p.box([min(aa[2*i], bb[2*i]) for i in range(3)],
                                 [max(aa[2*i+1], bb[2*i+1]) for i in range(3)])
        bboxes = {name: p.bounds(body) for name, body in current.items()}
        counts = {'complete_axis_box_clear': 0, 'native_region_clear': 0,
                  'rejected': 0, 'self_owner_excluded': 0}
        for label, (owner, gain) in added.items():
            moving = gain.translate(offsets[owner])
            moving_bounds = p.bounds(moving)
            cache = {}
            for name, obstacle in current.items():
                if name == owner:
                    counts['self_owner_excluded'] += 1
                    continue
                vector = tuple(translations[index][owner][i] - translations[index][name][i] for i in range(3))
                if axis_gap(moving_bounds, bboxes[name], vector) > 0:
                    counts['complete_axis_box_clear'] += 1
                    continue
                if vector not in cache:
                    if max(abs(v) for v in vector) < 1e-12:
                        cache[vector] = ([moving], {'complete_translation_not_pose_samples': True,
                                                  'method': 'actual fixed relative material'})
                    else:
                        try:
                            cache[vector] = regions(moving, vector)
                        except ValueError as error:
                            cache[vector] = (None, {'unsupported': str(error)})
                enclosure, method = cache[vector]
                row = {'phase': phase, 'added_region': label, 'owner': owner,
                       'obstacle': name, 'relative_translation_mm': list(vector),
                       'method': method}
                if name in non_affine:
                    row['obstacle_is_complete_monotone_profile_box_superset'] = True
                if enclosure is None:
                    values = None
                    rejected = True
                else:
                    values = []
                    for piece in enclosure:
                        values.append(0. if axis_gap(p.bounds(piece), bboxes[name]) > 0
                                      else p.volume(piece.intersect(obstacle)))
                    rejected = any(v > TOL for v in values)
                row['region_common_mm3'] = values
                row['clear'] = not rejected
                if rejected:
                    # A positive conservative region is retained as rejection.
                    # An actual interpolated material intersection, if found,
                    # is separately identified as a physical geometry witness.
                    witnesses = []
                    for k in range(0 if name in non_affine else 41):
                        fraction = k / 40.
                        moved = moving.translate(tuple(fraction*x for x in vector))
                        if axis_gap(p.bounds(moved), bboxes[name]) > 0:
                            continue
                        value = p.volume(moved.intersect(obstacle))
                        if value > TOL:
                            witnesses.append({'phase_fraction': fraction, 'actual_common_mm3': value})
                            break
                    row['actual_material_witnesses'] = witnesses
                    row['no_sample_witness_does_not_clear_conservative_rejection'] = True
                    failures.append(row)
                    counts['rejected'] += 1
                else:
                    counts['native_region_clear'] += 1
                checks.append(row)
        print('ADDED_MATERIAL_PHASE', phase, counts, flush=True)
        for name in offsets:
            offsets[name] = tuple(offsets[name][i] + translations[index][name][i] for i in range(3))
    if any(p.sha(ROOT / path) != expected for path, expected in hashes.items()):
        raise ValueError('frozen source/configuration changed during verification')
    return {'schema': 'razr-added-material-motion-v1', 'source_sha256': hashes,
            'added_material_accounting': accounting, 'positive_material_regions': len(added),
            'full_scene_participants_excluding_separately_verified_OLED': len(scenes[0]),
            'phase_relative_translations': translations,
            'native_endpoint_translation_identity_checked_for_affine_participants': True,
            'non_affine_participants_use_complete_monotone_profile_bounds': sorted(non_affine),
            'source_contact_profile_receipts': profile_receipts,
            'nontrivial_region_checks': checks, 'rejections': failures,
            'all_added_material_nominal_motion_enclosures_clear': not failures,
            'positive_common_superset_not_automatically_an_actual_collision': True,
            'zero_common_not_a_positive_clearance_measurement': True,
            'same_reverse_path_sets': True,
            'scope': 'all exact additions and new installed parts against current complete mechanics and four allocations; affine slot centerline and equal telescope allocation; monotone full-profile boxes for STOPs and spring reservations',
            'inherited_non_nominal_joint_allocations_and_physical_strength_reverified': False,
            'OLED_full_path_is_separate_report': True,
            'OPEN_accessories_only_at_static_OPEN_and_separate_insertion_report': True,
            'elapsed_seconds': time.monotonic() - started,
            'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'clear': result['all_added_material_nominal_motion_enclosures_clear'],
                      'rejections': len(result['rejections']),
                      'elapsed_seconds': result['elapsed_seconds']}), flush=True)
