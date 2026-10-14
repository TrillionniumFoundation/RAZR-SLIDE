"""Bound a local sampled contact transition without assuming global monotonicity.

A clear sample is not a continuous collision-free path, force solution or
certificate. The threshold is a caller's fixed numerical diagnostic threshold.
"""
import math


class NoClearSample(ValueError):
    def __init__(self, samples):
        super().__init__('No clear point on the specified bounded sample grid')
        self.samples = samples


def sampled_clearance_bracket(volume, positions, *, threshold=1e-10, iterations=27):
    points = tuple(float(p) for p in positions)
    if not points or any(not math.isfinite(p) for p in points) or any(b <= a for a,b in zip(points,points[1:])):
        raise ValueError('positions must be finite and strictly increasing')
    if not math.isfinite(threshold) or threshold < 0 or type(iterations) is not int or not 0 <= iterations <= 60:
        raise ValueError('invalid fixed diagnostic threshold or iteration count')
    samples = []
    def measure(p):
        v = float(volume(p))
        if not math.isfinite(v) or v < 0:
            raise ValueError('invalid signed common volume, never clearance')
        samples.append({'position':p,'checked_common_mm3':v})
        return v
    lo = None
    for hi in points:
        if measure(hi) <= threshold:
            break
        lo = hi
    else:
        raise NoClearSample(samples)
    if lo is not None:
        # Local bracketing only: never require the far end of the global domain
        # to be clear. No assertion that unsampled clear intervals are absent.
        for _ in range(iterations):
            middle = (lo+hi)/2
            if measure(middle) > threshold:
                lo = middle
            else:
                hi = middle
    if measure(hi) > threshold:
        raise ValueError('clear endpoint failed final actual recheck')
    return {'clear_position':hi,'colliding_bracket_position':lo,
            'samples':samples,'threshold_mm3':threshold,
            'global_monotonicity_assumed':False,'continuous_path_qualified':False,
            'first_global_contact_proven':False,'manufacturing_go':False}
