"""Conservative overlap checks for the complete STOP/KEY material partition.

The pin and three remainder cages cover one physical STOP. Their overlaps
with the same KEY must share one tolerance budget. The sum is an upper bound
because cages may overlap; it is not a measured union or a collision witness.
Different sides, STOPs and obstacle pairs retain separate tolerance budgets.
"""
import math

from translation_regions import sum_common_upper_bound


def stop_key_partition_checks(partitions, tolerance=1e-7):
    """Require exactly the four L/R, STOP 0/1 complete material partitions."""
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('positive finite Common tolerance required')
    partitions = list(partitions)
    if len(partitions) != 4:
        raise ValueError('four complete STOP/KEY material partitions required')
    expected = {(side, stop) for side in 'LR' for stop in range(2)}
    seen = set()
    checks = []
    for item in partitions:
        if not isinstance(item, dict):
            raise ValueError('material partition record required')
        side, stop = item.get('side'), item.get('stop')
        if type(side) is not str or side not in ('L', 'R') or type(stop) is not int or stop not in (0, 1):
            raise ValueError('invalid STOP/KEY material partition identity')
        identity = (side, stop)
        if identity in seen:
            raise ValueError('duplicate STOP/KEY material partition')
        seen.add(identity)
        remainder = item.get('remainder_common_mm3')
        if not isinstance(remainder, (list, tuple)) or len(remainder) != 3:
            raise ValueError('all three STOP remainder cage overlaps required')
        values = [item.get('pin_common_mm3'), *remainder]
        upper = sum_common_upper_bound(values)
        checks.append({
            'side': side,
            'stop': stop,
            'member_common_mm3': values,
            'common_upper_bound_mm3': upper,
            'common_upper_bound_is_sum_not_union_volume': True,
            'whole_STOP_KEY_proved_clear': upper <= tolerance,
        })
    if seen != expected:
        raise ValueError('complete L/R STOP 0/1 material coverage required')
    return checks
