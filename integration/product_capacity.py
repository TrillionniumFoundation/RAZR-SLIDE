"""Turn the actual candidate's cell allocations into a conditional capacity budget.

An allocation is the outside envelope available to a complete protected cell,
not electrochemically active volume. No cell chemistry, nominal voltage, energy
density or supplier performance is inferred from CAD. Hypothetical densities
are a sensitivity axis, never a claim that such a product is available.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / 'design/product_geometry.json'


def capacity_budget(geometry, hypothetical_densities=(100, 150, 200, 250, 300, 350)):
    rows = []
    for component in geometry['components']:
        if component['name'] not in ('A_BATTERY_ALLOCATION', 'B_BATTERY_ALLOCATION'):
            continue
        if len(component['lo_mm']) != 3 or len(component['hi_mm']) != 3:
            raise ValueError('three coordinates per cell-allocation bound required')
        dimensions = [b-a for a, b in zip(component['lo_mm'], component['hi_mm'])]
        if len(dimensions) != 3 or any(not math.isfinite(x) or x <= 0 for x in dimensions):
            raise ValueError('positive finite cell-allocation dimensions required')
        rows.append({
            'name': component['name'], 'cabin': component['cabin'],
            'outside_dimensions_mm': dimensions,
            'available_outside_volume_mm3': math.prod(dimensions),
            'source_kind': component['source_kind'],
            'selected_part': component.get('selected_part'),
            'capacity_mAh': component.get('capacity_mAh'),
            'swelling_included': component.get('swelling_included', False),
        })
    if len(rows) != 2 or {row['cabin'] for row in rows} != {'A', 'B'}:
        raise ValueError('one independent A and one B cell allocation required')
    total = sum(row['available_outside_volume_mm3'] for row in rows) / 1000
    target = geometry['constraints']['total_system_capacity_target_mAh']
    if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(target) or target <= 0:
        raise ValueError('positive finite total capacity target required')
    volume = {row['cabin']: row['available_outside_volume_mm3'] for row in rows}
    sensitivity = []
    for density in hypothetical_densities:
        if isinstance(density, bool) or not isinstance(density, (int, float)) or not math.isfinite(density) or density <= 0:
            raise ValueError('positive finite hypothetical density required')
        sensitivity.append({
            'hypothetical_complete_pack_mAh_per_cm3': density,
            'capacity_if_entire_allocation_usable_mAh': density * total,
            'outside_volume_needed_for_target_cm3': target / density,
            'extra_outside_volume_needed_cm3': max(0, target / density-total),
            'source_kind': 'conditional_arithmetic_not_a_supplier_claim',
        })
    return {
        'scope': 'conditional capacity versus current outside allocation volume',
        'cell_allocations': rows,
        'A_has_larger_allocation_volume': volume['A'] > volume['B'],
        'A_larger_actual_capacity_verified': False,
        'total_outside_allocation_cm3': total,
        'total_target_mAh': target,
        'capacity_target_convention': 'sum of cell-label mAh at a common nominal reference voltage; not terminal Ah for an unidentified series/parallel topology',
        'actual_system_terminal_capacity_verified': False,
        'reference_voltage_and_pack_topology_selected': False,
        'minimum_required_complete_pack_mAh_per_cm3': target / total,
        'required_density_is_lower_bound_before_unmodeled_allowances': True,
        'hypothetical_density_sensitivity': sensitivity,
        'selected_cell_pair_capacity_or_Wh_verified': False,
        'true_cell_shapes_tabs_protection_and_swelling_verified': False,
        'interpretation': 'A donor cell pair must satisfy both native geometric fit and its actual rated capacity. A lower-density pair requires more allocation volume or a revised target; unmodeled allowances increase the density requirement.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', type=Path, default=GEOMETRY)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.geometry.read_bytes()
    result = capacity_budget(json.loads(raw))
    result['geometry_sha256'] = hashlib.sha256(raw).hexdigest()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('total_outside_allocation_cm3', 'minimum_required_complete_pack_mAh_per_cm3', 'A_has_larger_allocation_volume')}))


if __name__ == '__main__':
    main()
