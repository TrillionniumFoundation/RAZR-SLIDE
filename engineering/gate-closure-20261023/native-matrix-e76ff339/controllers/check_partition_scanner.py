"""Focused positive/negative checks for the independent retained-byte scanner."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import audit_native_matrix as audit

BASE = Path(__file__).resolve().parent
checks = []


def check(name, value, expected):
    rows = list(audit.region_groups(value))
    assert len(rows) == 1 and rows[0]['old_per_region_clear'] is True
    assert rows[0]['summed_upper_bound_clear'] is expected
    checks.append({'name': name, 'passed': True, 'record': rows[0]})


check('individual_region_values_below_tolerance_do_not_hide_sum', {'region_common_mm3': [9e-8, 9e-8]}, False)
check('mounted_screw_plural_field_is_not_omitted', {'commons_mm3': [9e-8, 9e-8]}, False)
check('thin_pin_and_remainder_share_budget', {'stop': 0, 'pin_complete_relative_path_common_mm3': 9e-8,
                                            'core_remainder_cage_common_mm3': [9e-8, 0., 0.]}, False)
box = [{'side': 'R', 'fixed': 'R_ROOF', 'piece': name, 'common_mm3': value}
       for name, value in [('body', 9e-8), ('neck', 9e-8), ('tongue', 0.), ('round_carrier', 0.)]]
check('box_guide_simultaneous_material_pieces_share_budget', box, False)
root = [{'side': 'R', 'root': 'ROOT_OUTER', 'cover': name, 'common_mm3': 0., 'distance_mm': .05}
        for name in ('body', 'neck', 'tongue', 'socket', 'pin')]
check('root_cover_preserves_positive_distance_guard', root, True)
assert not list(audit.region_groups({'bare_frame_three_segment_common_mm3': [9e-8, 9e-8, 9e-8]}))
checks.append({'name': 'sequential_nut_motion_segments_not_summed_as_material', 'passed': True})
try:
    list(audit.region_groups(box[:-1]))
    raise AssertionError('incomplete material accepted')
except ValueError:
    checks.append({'name': 'incomplete_material_partition_rejected', 'passed': True})
for value in (float('nan'), float('inf'), -1e-9):
    try:
        list(audit.region_groups({'common_mm3': [value]}))
        raise AssertionError('invalid Common accepted')
    except ValueError:
        pass
checks.append({'name': 'negative_and_nonfinite_common_rejected', 'passed': True})
result = {'schema': 'razr-raw-partition-scanner-check-v2',
          'checked_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
          'audit_tool_sha256': hashlib.sha256((BASE/'audit_native_matrix.py').read_bytes()).hexdigest(),
          'check_tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'checks': checks, 'passed': True}
with (BASE/'partition-scanner-contract-v2.json').open('x') as stream:
    json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
print(json.dumps({'checks': len(checks), 'passed': True}))
