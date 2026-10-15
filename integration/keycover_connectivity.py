"""Bounded-cover separation witness from material contained in the actual KEY.

Three overlapping rectangular solids form a bottom-to-top material barrier
in the old cover box. Their exact straight translations, not any conservative
cylindrical carrier, separate the two retained cover sides. This does not
assert impossibility after enlarging the cover bounds or changing the KEY.
"""
import cam_contact_native as n
from straight_envelope import whole_material

def prove(key,cover,side):
    source_specs=[(-.17,.17,-.70,.60,-7.25,-3.01),(-1.49,-.16,-.29,.39,-3.19,-3.01),(-1.49,-1.11,-.049,.049,-3.18,-2.49)]
    sources=[n.box(side,*v) for v in source_specs]
    proofs=[]
    for box in sources:
        outside=whole_material(box.cut(key),empty=True)[1]
        if outside>1e-7:raise ValueError('separation witness is not a subset of actual native KEY')
        proofs.append({'volume_mm3':box.Volume(),'outside_native_KEY_mm3':outside})
    expanded=[n.box(side,e0,e1,q0,q1+12,r0,r1) for e0,e1,q0,q1,r0,r1 in source_specs]
    obstacle=n.fuse(expanded)
    bounds=n.bounds(side,cover);domain=n.box(side,*bounds[0],*bounds[1],*bounds[2])
    free=domain.cut(obstacle).clean();leaves,volume=whole_material(free)
    if len(leaves)!=2:raise ValueError('native-subset obstacle does not split original cover box in two')
    separation=leaves[0].distance(leaves[1])
    if separation<=1e-7:raise ValueError('free regions are not separated by positive thickness')
    # Witness points in each original fastening plate have positive volume.
    anchors=[n.box(side,-2.6,-2.5,6.,6.1,-7.,-6.9),n.box(side,2.5,2.6,6.,6.1,-7.,-6.9)]
    membership=[]
    for a in anchors:
        if whole_material(a.cut(cover),empty=True)[1]>1e-7:raise ValueError('anchor not in original retained plate')
        row=[n.common(a,g) for g in leaves]
        if sum(v>1e-7 for v in row)!=1:raise ValueError('plate anchor not uniquely assigned to a free region')
        membership.append(row)
    if sum(row[0]>1e-7 for row in membership)!=1:raise ValueError('anchors not separated')
    return obstacle,free,{'source_rectangles_eqr_mm':source_specs,'source_subset_checks':proofs,
        'exact_straight_sweeps_q_mm':[0.,12.],'free_components':2,'free_region_min_distance_mm':separation,
        'retained_plate_anchor_membership_mm3':membership,'native_KEY_subset_not_conservative_carrier':True,
        'impossibility_scope':'connected retained cover plates inside original cover bounding box, unchanged KEY q=0..12',
        'no_claim_for_larger_cover_or_changed_KEY':True,'manufacturing_go':False}
