"""Research side-entry opening for the inner-root square locator.
Only a declared part of the cover is removed; this changes the locator from a
closed hole to an open-sided slot. Capture/load/tolerance are NOT qualified.
"""
from functools import lru_cache
import keycover_bypass as base
import cam_contact_native as n
from straight_envelope import whole_material
ROOT=base.ROOT;GROUP=base.GROUP;b=base.b;parent=base.parent;baseline=base.baseline;previous=base.previous
ROOT_NAME=base.ROOT_NAME;check=base.check;pairs=base.pairs

@lru_cache(maxsize=2)
def design(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    original,root,cover,relative,prior,sweep,free=base.design(side)
    window=n.box(side,-3.16,-2.68,2.98,3.22,-7.25,-6.43)
    candidate=cover.cut(window).clean();n.single(candidate)
    removed=whole_material(cover.cut(candidate),empty=True)[1]
    if abs(removed-.04416)>1e-7 or whole_material(candidate.cut(cover),empty=True)[1]>1e-7:raise ValueError('locator removal differs from declared window')
    before=n.bounds(side,cover);after=n.bounds(side,candidate)
    if any(abs(a-b)>1e-7 for v,w in zip(before,after) for a,b in zip(v,w)):raise ValueError('cover outer bounds changed')
    return original,root,candidate,relative,{'candidate':'cover_inner_locator_side_entry','parent_keycover_receipt':prior,
        'notch_eqr_mm':[-3.16,-2.68,2.98,3.22,-7.25,-6.43],'original_closed_locator_becomes_side_open_slot':True,
        'cover_removed_this_revision_mm3':removed,'cover_prior_volume_mm3':cover.Volume(),'cover_new_volume_mm3':candidate.Volume(),
        'single_positive_solid':True,'outer_bounds_unchanged':True,'other_parts_changed':False,
        'original_locator_retention_boundary_changed':True,'locator_closing_keeper_not_designed':True,
        'load_capture_tolerance_or_phone_qualification':False,'candidate_go':False,'manufacturing_go':False},sweep,free

def scene(port,side,lift=1.14,present=True,*,enabled=True):
    if type(enabled) is not bool:raise ValueError('explicit switch required')
    parts,raw=base.scene(port,side,lift,present)
    if port=='OPEN' or not enabled:return parts,{**raw,'cover_locator_side_entry':{'changed':False}}
    new=dict(parts);new['OLD_COVER']=design(side)[2]
    return new,{**raw,'cover_locator_side_entry':design(side)[4]}
