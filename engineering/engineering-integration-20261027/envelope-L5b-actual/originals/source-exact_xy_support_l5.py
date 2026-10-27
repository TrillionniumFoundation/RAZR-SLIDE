"""Exact rational support certificate for the rounded L5 capsule bridge.

The operands are the binary64 coordinates actually given to the native wire.
No assumption about hypot, normalization or rounded corner arithmetic enters
acceptance. This is a planar set proof, not an interval certificate for OCCT.
"""
from fractions import Fraction as F
import math


def require(value, message):
    if not value:
        raise ValueError(message)


def frac(value):
    require(type(value) in (float, int) and math.isfinite(value), 'nonfinite planar operand')
    return F(value)


def cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def minus(a, b):
    return (a[0]-b[0], a[1]-b[1])


def support_certificate(ends, radius, points):
    """Prove the entire segment-centered width-2R rectangle inside a CCW quad.

    With v=b-a and an edge e starting at p, the minimum of cross(e,x-p)
    over that continuous rectangle is c - R*abs(dot(e,v))/sqrt(dot(v,v)),
    c=min(cross(e,a-p), cross(e,b-p)). Squaring is equivalent only after c>=0.
    Every comparison here is exact integer/rational arithmetic.
    """
    require(len(ends)==2 and len(points)==4, 'wrong segment or bridge vertex count')
    a,b=[tuple(map(frac,p)) for p in ends]
    vertices=[tuple(map(frac,p)) for p in points]
    require(all(len(p)==2 for p in [a,b]+vertices), 'nonplanar coordinate')
    r=frac(radius);v=minus(b,a);v2=sum(x*x for x in v)
    require(r>0 and v2>0, 'bridge requires positive radius and nonzero segment')
    edges=[minus(vertices[(i+1)%4],vertices[i]) for i in range(4)]
    area2=sum(cross(vertices[i],vertices[(i+1)%4]) for i in range(4))
    turns=[cross(edges[i],edges[(i+1)%4]) for i in range(4)]
    rows=[]
    for p,e in zip(vertices,edges):
        c=min(cross(e,minus(a,p)),cross(e,minus(b,p)))
        dot=sum(x*y for x,y in zip(e,v))
        slack=c*c*v2-r*r*dot*dot
        rows.append({'edge_exact':list(map(str,e)), 'minimum_endpoint_cross_exact':str(c),
            'edge_dot_centerline_exact':str(dot), 'squared_support_slack_exact':str(slack),
            'nonnegative_before_squaring':c>=0,
            'continuous_rectangle_in_halfspace':c>=0 and slack>=0})
    passed=(area2>0 and all(x>0 for x in turns) and all(x['continuous_rectangle_in_halfspace'] for x in rows))
    return {'schema':'razr-L5-exact-rounded-bridge-support-v1',
        'centerline_endpoints_exact':[[str(x) for x in p] for p in (a,b)],
        'rounded_bridge_vertices_exact':[[str(x) for x in p] for p in vertices],
        'radius_exact':str(r),'centerline_length_squared_exact':str(v2),
        'signed_twice_area_exact':str(area2),'strict_convex_turns_exact':list(map(str,turns)),
        'edge_halfspace_checks':rows,'continuous_rectangle_contained':passed,
        'finite_point_sampling_used_for_acceptance':False,
        'native_Boolean_or_surface_interval_certificate':False}


def _certified_bridge(ends, radius, maximum_attempts, partial):
    """Choose a slightly extended bridge and certify its actual rounded corners.

    Any failed attempt is retained. XY widths/end extensions may grow; Z never
    changes here. The initial floating norm is merely a construction guess.
    """
    require(maximum_attempts==32, 'reviewed finite construction cap changed')
    a,b=[tuple(map(frac,p)) for p in ends]
    r=frac(radius);v=minus(b,a);v2=sum(x*x for x in v)
    require(r>0 and v2>0, 'bridge requires positive radius and nonzero segment')
    partial['phase']='normal_scale_guess'
    guess=radius/math.hypot(float(v[0]),float(v[1]))
    partial['initial_native_normal_guess']=guess if math.isfinite(guess) else None
    require(math.isfinite(guess) and guess>0,'unusable native normal-scale guess')
    initial_guess=guess;adjustments=0
    partial['phase']='outward_normal_scale'
    while F(guess)*F(guess)*v2<r*r:
        partial['normal_scale_nextafter_steps']=adjustments
        require(adjustments<32,'normal-scale rational outward bound not reached')
        guess=math.nextafter(guess,math.inf);adjustments+=1
    k=F(guess);attempts=partial['construction_attempts']
    partial.update(normal_scale_nextafter_steps=adjustments,outward_base_normal_scale_exact=str(k))
    for attempt in range(maximum_attempts):
        partial.update(phase='rounded_bridge_vertices',active_attempt=attempt)
        extension=F(1,2**(48-attempt))
        scale=k*(1+extension)
        normal=(-v[1]*scale,v[0]*scale)
        head=tuple(a[i]-extension*v[i] for i in range(2))
        tail=tuple(b[i]+extension*v[i] for i in range(2))
        exact_points=[tuple(point[i]+sign*normal[i] for i in range(2))
            for point,sign in ((head,1),(head,-1),(tail,-1),(tail,1))]
        rounded=[tuple(float(x) for x in p) for p in exact_points]
        require(all(math.isfinite(x) for p in rounded for x in p),'nonfinite constructed bridge vertex')
        errors=[[F(x)-y for x,y in zip(p,raw)] for p,raw in zip(rounded,exact_points)]
        partial['phase']='exact_continuous_support'
        proof=support_certificate(ends,radius,rounded)
        row={'attempt':attempt,'relative_XY_normal_inflation_exact':str(extension),
            'centerline_extension_parameter_exact':str(extension),
            'normal_scale_exact':str(scale),
            'normal_scale_squared_surplus_exact':str(scale*scale*v2-r*r),
            'native_corner_rounding_error_xy_exact':[[str(x) for x in p] for p in errors],
            'maximum_corner_rounding_L1_bound_exact':str(max(sum(abs(x) for x in p) for p in errors)),
            'support_certificate':proof}
        attempts.append(row)
        if proof['continuous_rectangle_contained']:
            return rounded,{'method':'exact_support_of_actual_rounded_XY_bridge',
                'initial_native_normal_guess':initial_guess,
                'nextafter_steps_for_rational_outward_normal_scale':adjustments,
                'outward_base_normal_scale_exact':str(k),
                'construction_attempts':attempts,'accepted_attempt':attempt,
                'maximum_attempts':maximum_attempts,
                'native_bridge_XY_vertices':list(map(list,rounded)),
                'continuous_planar_rectangle_inclusion_proved':True,
                'Z_padding_added_by_this_algorithm':False,
                'whole_OCCT_interval_certificate':False}
    error=ValueError('rounded XY bridge continuous inclusion remains unresolved')
    error.partial_bridge_audit={'construction_attempts':attempts,'maximum_attempts':maximum_attempts,
        'continuous_planar_rectangle_inclusion_proved':False,'whole_OCCT_interval_certificate':False}
    raise error


def certified_bridge(ends, radius, maximum_attempts=32):
    partial={'phase':'input_validation','construction_attempts':[],
        'normal_scale_nextafter_steps':0,'maximum_attempts':maximum_attempts,
        'continuous_planar_rectangle_inclusion_proved':False,'whole_OCCT_interval_certificate':False}
    try:
        return _certified_bridge(ends,radius,maximum_attempts,partial)
    except Exception as exc:
        partial.update(getattr(exc,'partial_bridge_audit',{}))
        exc.partial_bridge_audit=partial
        raise
