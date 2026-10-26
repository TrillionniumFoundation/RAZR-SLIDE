"""Source-derived nominal SLIDE laws; no CAD is imported by this module.

The single q parameter drives B/KEY/crosshead motion. Independent telescope
allocation and slot flanks remain free. Four STOP height functions and four
growing spring envelopes are separate complete materials, never fixed rigid
translations inferred from finite samples.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import itertools
import math

QMAX = F(12)
SLIDE_PER_Q = F('79.75') / QMAX
JOINT_NOMINAL = F('8.5') / 3
JOINT_LOW, JOINT_HIGH = F('.1'), F('2.9')
FLEX = frozenset(('OLED_GEOMETRIC_TRIAL', 'EP5_finite_material'))
SPRINGS = frozenset(f'{s}_SPRING_{i}_OD_TOL_ENVELOPE' for s in 'LR' for i in (0, 1))
STOP_ROLES = tuple(f'{s}_STOP_{i}' for s in 'LR' for i in (0, 1))


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, F)):
        raise ValueError('finite non-boolean numeric value required')
    if not math.isfinite(float(value)):
        raise ValueError('finite value required')
    return value if isinstance(value, F) else F(str(value))


def q_interval(low=0, high=12):
    low, high = finite(low), finite(high)
    if not 0 <= low <= high <= QMAX:
        raise ValueError('nominal contact coordinate must remain in [0,12]')
    return low, high


def joint_vertices():
    return tuple(sorted(set(itertools.permutations((F('2.7'), F('2.9'), F('2.9'))))))


@dataclass(frozen=True)
class Law:
    q_xyz: tuple[F, F, F]
    # Relative Z from the STOW equal-allocation reference in j1L,j2L,j1R,j2R.
    joint_z: tuple[F, F, F, F] = (F(0),) * 4
    flank_z: tuple[F, F] = (F(0),) * 2
    # Coefficients of each complete STOP's h_i(q)-h_i(0), in its X axis.
    height_x: tuple[F, F, F, F] = (F(0),) * 4

    def __post_init__(self):
        for field, length in (('q_xyz', 3), ('joint_z', 4), ('flank_z', 2), ('height_x', 4)):
            raw = getattr(self, field)
            if len(raw) != length:
                raise ValueError('incorrect law dimension: ' + field)
            object.__setattr__(self, field, tuple(map(finite, raw)))

    def relative_to(self, other):
        def subtract(field):
            return tuple(a-b for a,b in zip(getattr(self,field),getattr(other,field)))
        return Law(*(subtract(field) for field in ('q_xyz','joint_z','flank_z','height_x')))

    def z_interval(self):
        extrema = []
        for start in (0, 2):
            first, second = self.joint_z[start:start+2]
            values = [first*(j[0]-JOINT_NOMINAL)+second*(j[1]-JOINT_NOMINAL) for j in joint_vertices()]
            extrema.append((min(values), max(values)))
        flank_half = sum(map(abs,self.flank_z))
        return sum(row[0] for row in extrema)-flank_half, sum(row[1] for row in extrema)+flank_half

    def coordinates(self, q, joints_left, joints_right, flanks, profiles):
        q_interval(q,q)
        if len(flanks)!=2 or any(not -1<=finite(v)<=1 for v in flanks):
            raise ValueError('independent finite flank inputs required')
        for joints in (joints_left,joints_right):
            if len(joints)!=3 or sum(map(finite,joints))!=F('8.5') or any(not JOINT_LOW<=finite(v)<=JOINT_HIGH for v in joints):
                raise ValueError('complete fixed-sum telescope allocation required')
        if len(profiles)!=4:
            raise ValueError('four original native profiles required')
        xyz = [float(c*finite(q)) for c in self.q_xyz]
        xyz[0] += math.fsum(float(c)*(p.evaluate(float(q))[0]-p.evaluate(0.)[0]) for c,p in zip(self.height_x,profiles))
        values = [finite(v)-JOINT_NOMINAL for j in (joints_left,joints_right) for v in j[:2]]
        xyz[2] += float(sum(c*v for c,v in zip(self.joint_z,values))+sum(c*finite(v) for c,v in zip(self.flank_z,flanks)))
        return tuple(xyz)

    def enclosure_parameters(self, profiles, low=0, high=12):
        """Conservative full image; height/q correlation is explicitly retained as unresolved if needed.

        The q vector is one shared parameter, and telescope/flank Z is its
        exact independent convex projection. STOP heights are bounded by their
        proven monotonic branch law; treating each as independent enlarges the
        image. An overlapping cage cannot be accepted as an actual collision.
        """
        low, high = q_interval(low,high)
        if len(profiles)!=4:
            raise ValueError('four original native profiles required')
        vectors, intervals = [tuple(map(float,self.q_xyz))], [(float(low),float(high))]
        for coefficient, profile in zip(self.height_x,profiles):
            if coefficient:
                hmin,hmax=profile.height_bounds(float(low),float(high)); home=profile.evaluate(0.)[0]
                vectors.append((float(coefficient),0.,0.)); intervals.append((hmin-home,hmax-home))
        zlow,zhigh=self.z_interval()
        if zlow or zhigh:
            vectors.append((0.,0.,1.)); intervals.append((float(zlow),float(zhigh)))
        return vectors,tuple(intervals)

    def record(self):
        return {field:[str(v) for v in getattr(self,field)] for field in ('q_xyz','joint_z','flank_z','height_x')}


ZERO=Law((F(0),)*3)


def rigid_laws(names, halfwidth, expected_names):
    names=tuple(names)
    if len(names)!=154 or len(set(names))!=154 or set(names)!=set(expected_names):
        raise ValueError('complete immutable travel participant inventory required')
    if not FLEX|SPRINGS|set(STOP_ROLES)<=set(names) or set(halfwidth)!={'L','R'}:
        raise ValueError('complete flexible, spring, STOP and slot material required')
    laws={name:ZERO for name in names if name not in FLEX|SPRINGS}
    b_names={name for name in laws if name.startswith('B_')}
    if len(b_names)!=23:
        raise ValueError('all 23 B shell/allocation/endpoint materials required')
    for name in b_names: laws[name]=Law((F(0),SLIDE_PER_Q,F(0)))
    for side,side_index in (('L',0),('R',1)):
        sign=F(-1 if side=='L' else 1)
        laws[side+'_KEY']=Law((F(0),F(1),F(0)))
        for suffix in ('CROSSHEAD','CROSSHEAD_TUBE_BOTTOM_CAP','KEY_FOLLOWER_LOWER_FLANGE'):
            laws[side+'_'+suffix]=Law((sign,F(0),F(0)))
        half=finite(halfwidth[side])
        if not 0<half<F('.1'):
            raise ValueError('native slot halfwidth out of range')
        f=[F(0),F(0)]; f[side_index]=half
        for suffix in ('PAWL','SHOULDER_PIN_NOMINAL'): laws[side+'_'+suffix]=Law((F(0),)*3,flank_z=tuple(f))
        for stage in (1,2,3):
            j=[F(0)]*4
            if stage<3:
                j[2*side_index]=F(1)
                if stage==2:j[2*side_index+1]=F(1)
            suffixes=('', '_BOTTOM_CAP') if stage<3 else ('','_CORE_BOTTOM_SHOULDER','_CAM_LOWER_FLANGE','_CAM_UPPER_FLANGE')
            for suffix in suffixes: laws[f'{side}_TELESCOPE_{stage}{suffix}']=Law((sign,F(0),F(0)),joint_z=tuple(j))
        for i in (0,1):
            coefficients=[F(0)]*4;coefficients[2*side_index+i]=sign
            laws[f'{side}_STOP_{i}']=Law((F(0),)*3,height_x=tuple(coefficients))
    if len(laws)!=148 or set(laws)!=set(names)-(FLEX|SPRINGS):
        raise ValueError('rigid material classification changed')
    return laws


def profile_intervals(profiles):
    if len(profiles)!=4 or any(p.q_max!=12. for p in profiles):
        raise ValueError('four complete source profiles with original finite travel required')
    # Preserve distinct floating-source breakpoints, even when very close.
    points=sorted({0.,12.,*(q for p in profiles for q in p.breakpoints)})
    if any(not 0.<=q<=12. for q in points):raise ValueError('invalid profile breakpoint')
    return tuple(zip(points[:-1],points[1:]))


def domain_record(profiles=None):
    return {'slide_mm':[0.,79.75],'descent_mm':0.,'q_mm':[0.,12.],
            'q_to_slide_exact':str(SLIDE_PER_Q),'tabs_mm':[3.,3.],
            'independent_slot_flanks':[[-1.,1.],[-1.,1.]],
            'KEY_offsets_mm':[0.,0.],'crosshead_offsets_mm':[0.,0.],
            'independent_joint_vertices_each':[[str(v) for v in j] for j in joint_vertices()],
            'joint_sum_each_exact':'17/2','all_four_growing_spring_materials_retained':True,
            'all_four_complete_STOP_materials_retained':True,
            'selected_contact_branch_requires_lower_restoring_force':True,
            'profile_subintervals_q_mm':list(profile_intervals(profiles)) if profiles is not None else None,
            'reverse_uses_same_quasistatic_material_sets_not_a_dynamic_relock_proof':True,
            'all_nonzero_KEY_crosshead_clearance_states_included':False,
            'complete_G2_or_physical_qualification':False}
