"""Place the separable follower construction back in the common phone scene.

Only component partition changes. Every replacement must reproduce its actual
native parent material in both directions, including nonnominal permitted
telescope allocations. This does not establish joint strength, joining-tool
access or the assembly order of the complete phone.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess

import cadquery as cq
import product_assembly as p

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SOURCE = ROOT / 'engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py'
TOL = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def construction():
    spec = importlib.util.spec_from_file_location('razr_captured_construction', LOCAL_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if sha(ROOT / 'integration/cam_coupling.py') != module.SOURCE_SHA:
        raise ValueError('captured follower source identity changed')
    _, _, sections = module.source_geometry()
    return {name: p.single(module.body(intervals)) for name, intervals in sections.items()}


def partition(parent_name, parent, removed):
    """Require each actual removable body to be wholly within its native parent."""
    checks = []
    for name, body in removed.items():
        outside = p.volume(body.cut(parent))
        inside = p.strict_common(body, parent)['common_mm3']
        if outside > TOL or inside <= TOL:
            raise ValueError('removable body is not contained in current parent: ' + name)
        checks.append({'part': name, 'outside_parent_mm3': outside, 'contained_mm3': inside})
    remaining = parent
    for body in removed.values():
        remaining = p.single(remaining.cut(body).clean())
    pieces = {parent_name: remaining, **removed}
    joined = p.fuse(list(pieces.values()))
    lost, added = p.volume(parent.cut(joined)), p.volume(joined.cut(parent))
    sibling_pairs = []
    for (a, first), (b, second) in itertools.combinations(sorted(pieces.items()), 2):
        result = p.strict_common(first, second)
        sibling_pairs.append({'a': a, 'b': b, **result})
        if result['common_mm3'] > TOL:
            raise ValueError('replacement sibling material overlaps')
    if max(lost, added) > TOL:
        raise ValueError('partition changed native material')
    return pieces, {'parent': parent_name, 'replacement_parts': list(pieces),
                    'removed_material_not_restored_mm3': lost,
                    'new_material_outside_parent_mm3': added,
                    'containment': checks, 'sibling_pair_checks': sibling_pairs,
                    'joint_strength_or_manufacturing_qualified': False}


def split_scene(slide_mm=0., descent_mm=0., left_tab_mm=0., right_tab_mm=0., **kwargs):
    scene, meta = p.product_scene(slide_mm, descent_mm, left_tab_mm, right_tab_mm, **kwargs)
    original = dict(scene)
    local = construction()
    records = []
    for side in 'LR':
        t1_bounds = p.bounds(scene[side + '_TELESCOPE_1'])
        x, y = (t1_bounds[0]+t1_bounds[1])/2, (t1_bounds[2]+t1_bounds[3])/2
        # The actual native scene supplies X/Y and every telescopic base Z.
        # The crosshead outer floor is the frozen construction's Z=.7 datum.
        removals = {
            side + '_CROSSHEAD_TUBE_BOTTOM_CAP': local['TUBE_0_BOTTOM_CAP'].translate((x, y, .7)),
            side + '_KEY_FOLLOWER_LOWER_FLANGE': local['KEY_LOWER_FLANGE'].translate((x, y-4., 0.)),
        }
        names = side + '_CROSSHEAD'
        parts, record = partition(names, scene[names], removals)
        scene.update(parts); records.append(record)
        for stage in (1, 2, 3):
            name = f'{side}_TELESCOPE_{stage}'
            box = p.bounds(scene[name])
            origin = ((box[0]+box[1])/2, (box[2]+box[3])/2, box[4])
            if stage < 3:
                removals = {name + '_BOTTOM_CAP': local[f'TUBE_{stage}_BOTTOM_CAP'].translate(origin)}
            else:
                removals = {name + '_' + role: local[role].translate(origin)
                            for role in ('CORE_BOTTOM_SHOULDER', 'CAM_LOWER_FLANGE', 'CAM_UPPER_FLANGE')}
            parts, record = partition(name, scene[name], removals)
            scene.update(parts); records.append(record)
    if len(scene) != len(original)+14 or len(records) != 8:
        raise ValueError('incomplete two-sided component partition')
    changed = {r['parent'] for r in records}
    unchanged = sorted(set(original)-changed)
    return scene, {**meta,
        'factory': 'integration/product_split_assembly.py:split_scene',
        'parent_factory': 'integration/product_assembly.py:product_scene',
        'parent_mechanical_participants': len(original),
        'installed_mechanical_parts': len(scene), 'expected_scene_participants': len(scene),
        'new_parts_from_partition': 14, 'changed_parent_parts': 8,
        'unchanged_parent_parts': unchanged, 'partition_checks': records,
        'whole_material_preserved_against_this_pose_native_parents': True,
        'whole_phone_installation_order_verified': False,
        'joining_tool_access_with_whole_housing_verified': False,
        'physical_joint_retention_qualified': False, 'physical_prototype_exists': False,
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}


def generate(output):
    import oled_storage
    import product_fpc
    import product_interfaces
    import product_routing_diagnostic
    output = Path(output).resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('use a new output outside source')
    sources = [Path(__file__), LOCAL_SOURCE, ROOT/'integration/product_assembly.py',
               ROOT/'integration/cam_coupling.py', ROOT/'integration/oled_storage.py',
               ROOT/'design/product_geometry.json', ROOT/'integration/product_fpc.py',
               ROOT/'integration/product_interfaces.py', ROOT/'design/product_interfaces.json',
               ROOT/'integration/product_routing_diagnostic.py', ROOT/'design/product_routing_followup.json']
    before = {str(f.relative_to(ROOT)): sha(f) for f in sources}
    output.mkdir(parents=True)
    electrical = product_interfaces.load_config()
    product_routing_diagnostic.load_config()
    endpoints = {end: product_routing_diagnostic.ep2_local_parts(electrical, end) for end in ('A','B')}
    poses = {}
    for label, s, d, tab, accessories in [('STOW', 0., 0., 0., False),
                                          ('PREDOCK', 79.75, 0., 3., False),
                                          ('OPEN', 79.75, 8.2, 3., True)]:
        parts, meta = split_scene(s, d, tab, tab, open_hold=accessories, open_support=accessories)
        mechanical_count = len(parts)
        parts.update(p.registered_components(p.load_config(), s, d))
        parts['OLED_GEOMETRIC_TRIAL'], oled_meta = oled_storage.geometry(s, d)
        sections, route_meta = product_fpc.route_pose(electrical, s, d)
        ribbon, ribbon_meta = product_fpc.finite_material_solid(sections['corners'])
        parts['REJECTED_EP2_FINITE_FPC'] = ribbon
        for end in ('A','B'):
            placed = product_fpc.place_endpoint(endpoints[end], sections, end)
            parts.update({'REJECTED_EP2_'+end+'_'+name: shape for name,shape in placed.items()})
        if len(parts) != mechanical_count+46:
            raise ValueError('complete EP2, OLED or component allocation omitted')
        records = {name: {'bounds_mm': p.bounds(body), 'volume_mm3': p.volume(body)}
                   for name, body in sorted(parts.items())}
        assembly = cq.Assembly(name='RAZR_SEPARABLE_FOLLOWER_' + label)
        for name, body in sorted(parts.items()):
            assembly.add(body, name=name)
        step = output / (label + '-complete-rejected-EP2-assembly.step')
        assembly.export(str(step))
        poses[label] = {'mechanical_participants': mechanical_count,
                        'total_participants': len(parts), 'mechanical': meta,
                        'OLED': oled_meta, 'FPC_route': route_meta, 'finite_FPC': ribbon_meta,
                        'EP2_endpoint_participants': 40,
                        'whole_phone_clearance_passed': False,
                        'collisions_recomputed_by_this_exporter': False,
                        'scope': 'all declared design allocations, nominal OLED, complete rejected EP2 and partitioned mechanism in one coordinate system',
                        'parts': records,
                        'combined': {'file': step.name, 'sha256': sha(step), 'expected_solids': len(parts)}}
    # Rebuild one admissible unequal telescope allocation, without duplicating
    # its STEP output. Each partition remains tied to actual native component Z.
    _, unequal = split_scene(79.75, 0., 3., 3., telescope_offsets=[2.9, 2.8, 2.8])
    after = {str(f.relative_to(ROOT)): sha(f) for f in sources}
    if before != after or any(not p.source_unchanged(pose['mechanical']) for pose in poses.values()) or not p.source_unchanged(unequal):
        raise ValueError('construction source changed during export')
    result = {'schema': 'razr-common-split-assembly-v1',
              'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_sha256': before, 'source_bytes_unchanged': True,
              'native_archive_identity': {k: poses['STOW']['mechanical'][k]
                                          for k in ('archive', 'archive_sha256', 'source_inputs')},
              'poses': poses, 'unequal_telescope_allocation': unequal,
              'same_geometry_does_not_qualify_new_joints': True,
              'whole_phone_installation_order_verified': False,
              'real_donor_components_included': False,
              'full_finite_FPC_and_EP2_endpoints_included': True,
              'included_EP2_is_a_rejected_research_route': True,
              'whole_phone_clearance_passed': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps({'poses': {k: v['total_participants'] for k,v in result['poses'].items()},
                      'source_bytes_unchanged': result['source_bytes_unchanged'],
                      'whole_phone_installation_order_verified': False}))
