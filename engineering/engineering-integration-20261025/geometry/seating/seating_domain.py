"""Exact SEATING allocation domain and source-owned rigid Z laws.

Pure standard-library arithmetic: importing this module never imports CAD.
This is research preparation; no native clearance result is produced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache
import itertools
import math

SLIDE = F('79.75')
SEATING = F('8.2')
LOW = F('.1')
HIGH = F('2.9')
TOTAL_AT_ZERO = F('8.5')
REFERENCE_JOINT = TOTAL_AT_ZERO / 3
VARIABLES = ('d', 'j1L', 'j2L', 'j1R', 'j2R', 'flankL', 'flankR')
FLEXIBLE = frozenset(('OLED_GEOMETRIC_TRIAL', 'EP5_finite_material'))


def fraction(value):
    if isinstance(value, bool) or not isinstance(value, (F, int, float, str)):
        raise ValueError('finite non-boolean real parameter required')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('finite real parameter required')
    try:
        return value if isinstance(value, F) else F(str(value))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('finite exact decimal parameter required') from error


def interval(low=0, high=SEATING):
    low, high = fraction(low), fraction(high)
    if not 0 <= low <= high <= SEATING:
        raise ValueError('SEATING subinterval must lie in [0, 8.2]')
    return low, high


@lru_cache(maxsize=512)
def joints_at(descent):
    """All vertices of one bounded three-joint fixed-sum cross-section."""
    descent, _ = interval(descent, descent)
    total = TOTAL_AT_ZERO - descent
    result = set()
    for free in range(3):
        constrained = [i for i in range(3) if i != free]
        for values in itertools.product((LOW, HIGH), repeat=2):
            point = [F(0)] * 3
            for i, value in zip(constrained, values):
                point[i] = value
            point[free] = total - sum(values)
            if LOW <= point[free] <= HIGH:
                result.add(tuple(point))
    if not result:
        raise ValueError('empty captured telescope cross-section')
    return tuple(sorted(result))


def critical_descents(low=0, high=SEATING):
    """Cross-section vertices change affine branch at cube-corner sums."""
    low, high = interval(low, high)
    critical = [TOTAL_AT_ZERO - (k * HIGH + (3 - k) * LOW) for k in range(4)]
    return tuple(sorted({low, high, *(d for d in critical if low <= d <= high)}))


@lru_cache(maxsize=256)
def coupled_vertices(low=F(0), high=SEATING):
    """Exact generators of the joint *shared-d* five-dimensional polytope.

    On an interval between two cube-corner sums, every one-side vertex is
    affine in the same d. Every Cartesian product of those side vertices
    is therefore affine in d too. Cross-sections are their convex hulls,
    so the two endpoint product sets generate the entire interval. Adding
    all branch endpoints gives the exact full convex hull, not a box with
    independently selected left/right descents.
    """
    low, high = interval(low, high)
    result = set()
    for d in critical_descents(low, high):
        vertices = joints_at(d)
        for left, right in itertools.product(vertices, repeat=2):
            result.add((d, left[0], left[1], right[0], right[1]))
    return tuple(sorted(result))


def allocation(values):
    if len(values) != 7:
        raise ValueError('seven parameters required')
    d, l1, l2, r1, r2, fl, fr = map(fraction, values)
    interval(d, d)
    left = (l1, l2, TOTAL_AT_ZERO - d - l1 - l2)
    right = (r1, r2, TOTAL_AT_ZERO - d - r1 - r2)
    if any(not LOW <= v <= HIGH for v in left + right) or any(not -1 <= v <= 1 for v in (fl, fr)):
        raise ValueError('state is outside the coupled captured telescope/flank domain')
    return {'descent': d, 'joints': {'L': left, 'R': right}, 'flanks': (fl, fr)}


@dataclass(frozen=True)
class ZLaw:
    constant: F
    coefficients: tuple[F, ...]

    def __post_init__(self):
        if len(self.coefficients) != 7:
            raise ValueError('seven exact coefficients required')
        object.__setattr__(self, 'constant', fraction(self.constant))
        object.__setattr__(self, 'coefficients', tuple(map(fraction, self.coefficients)))

    def evaluate(self, values):
        if len(values) != 7:
            raise ValueError('seven state coordinates required')
        return self.constant + sum(c * fraction(v) for c, v in zip(self.coefficients, values))

    def relative_to(self, other):
        return ZLaw(self.constant - other.constant,
                    tuple(a - b for a, b in zip(self.coefficients, other.coefficients)))

    def in_frame(self, frame):
        """Frame B follows the original B translation -d from PREDOCK."""
        if frame not in ('A', 'B'):
            raise ValueError('only source-owned A and B relative frames are supported')
        values = list(self.coefficients)
        if frame == 'B':
            values[0] += 1
        return ZLaw(self.constant, tuple(values))

    @lru_cache(maxsize=2048)
    def projection(self, low=0, high=SEATING):
        vertices = coupled_vertices(*interval(low, high))
        first = self.coefficients[:5]
        values = [self.constant + sum(c * v for c, v in zip(first, point)) for point in vertices]
        flank_half = abs(self.coefficients[5]) + abs(self.coefficients[6])
        return min(values) - flank_half, max(values) + flank_half

    def record(self):
        return {'constant': str(self.constant), 'coefficients': [str(v) for v in self.coefficients],
                'parameter_order': list(VARIABLES), 'translation_axis': 'Z only'}


ZERO = ZLaw(F(0), (F(0),) * 7)
B_FOLLOWING = ZLaw(F(0), (F(-1),) + (F(0),) * 6)


def rigid_laws(names, slot_halfwidth_by_side, expected_names):
    """Fail closed on inventory changes; retain every original material body.

    The immutable expected list is taken from the previously complete native
    factory inventory. New runs must reconstruct the same exact name set.
    Geometry probes check these explicit source-derived laws against the
    complete factory; sampled agreement is not used to infer the laws.
    """
    names = tuple(names)
    if len(names) != len(set(names)) or set(names) != set(expected_names) or len(names) != 154:
        raise ValueError('the complete 154-part travel inventory is required')
    if not FLEXIBLE <= set(names) or set(slot_halfwidth_by_side) != {'L', 'R'}:
        raise ValueError('both flexible materials and both independent native slots are required')
    laws = {name: ZERO for name in names if name not in FLEXIBLE}
    # All B_* bodies in the travel inventory are the complete B shell,
    # two B allocations or one of the 20 native B endpoint parts. Cam
    # material is already integrated in its parent, not silently omitted.
    b_names = {name for name in laws if name.startswith('B_')}
    if len(b_names) != 23:
        raise ValueError('B shell/allocation/20-endpoint inventory changed')
    for name in b_names:
        laws[name] = B_FOLLOWING
    for side, first, flank in (('L', 1, 5), ('R', 3, 6)):
        half = fraction(slot_halfwidth_by_side[side])
        if not 0 < half < F('.1'):
            raise ValueError('invalid native slot halfwidth')
        values = [F(0)] * 7
        values[flank] = half
        for role in ('PAWL', 'SHOULDER_PIN_NOMINAL'):
            laws[side + '_' + role] = ZLaw(F(0), tuple(values))
        for stage in (1, 2):
            values = [F(0)] * 7
            values[first] = 1
            if stage == 2:
                values[first + 1] = 1
            law = ZLaw(-stage * REFERENCE_JOINT, tuple(values))
            for role in ('TELESCOPE_' + str(stage), 'TELESCOPE_' + str(stage) + '_BOTTOM_CAP'):
                laws[side + '_' + role] = law
        for suffix in ('', '_CORE_BOTTOM_SHOULDER', '_CAM_LOWER_FLANGE', '_CAM_UPPER_FLANGE'):
            laws[side + '_TELESCOPE_3' + suffix] = B_FOLLOWING
    if set(laws) != set(names) - FLEXIBLE:
        raise ValueError('rigid law classification inserted or lost material')
    return laws


def domain_record(low=0, high=SEATING):
    low, high = interval(low, high)
    vertices = coupled_vertices(low, high)
    return {'slide_mm': float(SLIDE), 'descent_mm': [float(low), float(high)],
            'tabs_mm': [3., 3.], 'slot_flanks': [[-1., 1.], [-1., 1.]],
            'KEY_offsets_mm': [0., 0.], 'crosshead_offsets_mm': [0., 0.],
            'joint_limits_mm': [float(LOW), float(HIGH)],
            'each_side_joint_sum': '8.5 - the same d',
            'independent_left_right_allocations_at_the_shared_descent': True,
            'OPEN_accessories_installed_during_travel': False,
            'polytope_parameter_order': list(VARIABLES[:5]),
            'critical_descents_exact': [str(d) for d in critical_descents(low, high)],
            'exact_vertex_generator_count': len(vertices),
            'exact_vertex_generators': [[str(v) for v in row] for row in vertices],
            'linear_relative_Z_projection_is_exact_convex_image': True,
            'physical_or_complete_G2_qualification': False}
