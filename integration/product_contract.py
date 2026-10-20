"""Bind product, mechanical and electrical declarations to one candidate.

This checks configuration identity, not solid clearance or physical operation.
It exists because independent current-state documents and FPC scene choices
previously drifted. Native CAD and motion reports retain their own scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('design/current_product.json', 'design/product_geometry.json',
          'design/product_interfaces.json')


def agree(name, *values):
    first = values[0]
    if any(type(value) is not type(first) or value != first for value in values[1:]):
        raise ValueError(name + ': product declarations disagree')


def agree_number(name, *values):
    if any(isinstance(x, bool) or not isinstance(x, (float, int)) or
           not math.isfinite(x) or x <= 0 for x in values):
        raise ValueError(name + ': finite positive dimensions required')
    if any(not math.isclose(values[0], x, rel_tol=0, abs_tol=1e-10) for x in values[1:]):
        raise ValueError(name + ': product declarations disagree')


def bind(product, geometry, electrical):
    baseline = product['implementation_baseline']['commit']
    if not re.fullmatch(r'[0-9a-f]{40}', baseline):
        raise ValueError('full implementation baseline commit required')
    agree('implementation baseline', baseline, geometry['base_commit'], electrical['basis_commit'])
    p, g, e = product['product_constraints'], geometry['constraints'], electrical['constraints']
    dimensions = geometry['dimensions']
    agree('equal cabin constraint', p['same_finished_A_B_envelope'],
          g['equal_finished_cabin_envelopes'], e['equal_finished_cabins'], True)
    agree('rear display constraint', p['independent_rear_display'],
          g['independent_rear_display'], e['independent_rear_display'], False)
    agree('one display constraint', g['one_flexible_display'], e['single_flexible_display'], True)
    agree('flat storage', p['storage_mode'], 'flat_in_' + g['planar_storage_cabin'], 'flat_in_B')
    agree('electrical flat storage', e['planar_display_storage'], True)
    agree('A battery priority', p['larger_cell_priority'], g['larger_battery_priority'], 'A')
    agree('electrical A priority', e['A_larger_battery_priority'], True)
    agree_number('total capacity target', p['total_capacity_target_mAh'],
                 g['total_system_capacity_target_mAh'], e['system_capacity_target_mAh'])
    agree_number('slide', p['B_upward_travel_mm'], dimensions['slide_mm'], e['B_slide_mm'])
    agree_number('normal seating', p['normal_seating_mm'], dimensions['normal_seating_mm'], e['B_descent_mm'])
    route, coupon = electrical['route_study'], electrical['coupon']
    agree_number('FPC width', route['width_mm'], coupon['width_mm'])
    agree_number('FPC thickness', route['thickness_mm'], coupon['finished_flex_thickness_assumption_mm'])
    agree_number('FPC free length', route['fixed_free_material_length_mm'], coupon['free_length_mm'])
    agree_number('coupon material partition', coupon['length_mm'],
                 coupon['free_length_mm'] + 2 * coupon['end_stiffener_length_mm'])
    factory = geometry['current_product_candidate']['factory']
    agree('FPC shared current scene', route['common_scene_api'],
          'integration/' + factory.replace('.', '.py:', 1))
    return {
        'scope': 'cross-configuration identity and declared dimensions only',
        'implementation_baseline': baseline,
        'declarations_consistent': True,
        'current_scene_factory': factory,
        'slide_mm': dimensions['slide_mm'],
        'normal_seating_mm': dimensions['normal_seating_mm'],
        'single_display_flat_storage_in_B': True,
        'A_larger_battery_priority': True,
        'capacity_is_a_target_not_a_selected_pair': True,
        'same_coupon_and_route_material_dimensions': True,
        'solid_packing_or_full_motion_evaluated_here': False,
        'actual_donor_or_hardware_qualified_here': False,
    }


def from_root(root=ROOT):
    paths = [Path(root) / p for p in INPUTS]
    raw = [path.read_bytes() for path in paths]
    result = bind(*(json.loads(data) for data in raw))
    result['input_sha256'] = {p: hashlib.sha256(data).hexdigest() for p, data in zip(INPUTS, raw)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = from_root()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
