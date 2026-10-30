"""Choose a radial midpoint using exact local quadratic sensitivity."""
from fractions import Fraction as F


def choose_cut(B, observation, models, sources):
    radial = []
    for channel in observation['observations']:
        failure = channel['failure']
        if failure is None:
            continue
        side = channel['material_side']
        piece = sources[side]['pieces'][failure['piece_index']]
        model = models[side].get((piece['kind'],piece['index']))
        if model and model['type'] in ('GeomAbs_Cylinder','GeomAbs_Circle'):
            radial.append(model['basis'])
    width = [hi-lo for lo,hi in B]
    center = [(hi+lo)/2 for lo,hi in B]
    if radial:
        scores = [F(0),F(0),F(0)]
        for basis in radial:
            p = [center[k]-basis['origin'][k] for k in range(3)]
            a,b = basis['a'],basis['b']
            u = sum((a[k]*p[k] for k in range(3)),F(0))
            v = sum((b[k]*p[k] for k in range(3)),F(0))
            for k in range(3):
                # This score only selects a cut; it is not used as a bound.
                # Every exclusion still uses full_D and the independently
                # checked original exact quadric predicate.
                score = (abs(2*(u*a[k]+v*b[k]))*width[k]
                         +(a[k]*a[k]+b[k]*b[k])*width[k]*width[k])/(basis['radius']**2)
                scores[k] = max(scores[k],score)
        rule = 'maximum_local_quadric_variation'
    else:
        scores = width
        rule = 'longest_axis'
    axis = max(range(3),key=lambda k:(scores[k],-k))
    return axis,(B[axis][0]+B[axis][1])/2,{'rule':rule,'scores_exact':list(map(str,scores))}
