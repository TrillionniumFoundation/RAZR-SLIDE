"""Cover-first admission with a finite research support and hold-down fixture.

Only the initial prefix is tested here. Root closure, screws, downstream parts
and fixture gripping forces are not inferred from a successful prefix.
"""
from admission_cells import Stage
import cam_contact_native as n


def fixture(side):
    base=n.box(side,-4.,5.,-5.,.1,-24.,-22.)
    supports=[n.box(side,e-.11,e+.11,-.36,-.14,-22.,-2.9) for e in (-2.55,2.55)]
    lower=n.fuse([base,*supports])
    # Hold-down fingers approach from the rear q<0, below the transverse
    # root-join screw envelope; long vertical posts stay behind q=-3.7.
    upper=n.fuse([n.box(side,-3.,3.,-4.1,-3.7,12.,12.5),
        *[n.box(side,e-.08,e+.08,-3.98,-3.82,-2.5,12.05) for e in (-2.55,2.55)],
        *[n.box(side,e-.08,e+.08,-3.98,-.17,-2.5,-2.34) for e in (-2.55,2.55)]])
    return {'JIG_BASE_SUPPORTS':lower,'JIG_HOLD_DOWN':upper}


def stages(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    outward=-20. if side=='L' else 20.;inward=-outward;park=-1.1 if side=='L' else 1.1
    return [Stage('COVER_ON_SUPPORTS','OLD_COVER',(0,0,20.),(0,0,0)),
        Stage('HOLD_DOWN','JIG_HOLD_DOWN',(0,0,20.),(0,0,0)),
        Stage('UNPARKED_PAWL_FROM_BELOW','PAWL',(0,0,-20.),(0,0,0)),
        Stage('PARK_PAWL','PAWL',(0,0,0),(park,0,0)),
        Stage('INNER_ROOT_SIDE_ENTRY','ROOT_INNER',(inward,0,0),(0,0,0)),
        Stage('STOP_0_SIDE_ENTRY','STOP_0',(outward,0,0),(0,0,0)),
        Stage('STOP_1_SIDE_ENTRY','STOP_1',(outward,0,0),(0,0,0)),
        Stage('OUTER_ROOT_CLOSE','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',(outward,0,0),(0,0,0))]
