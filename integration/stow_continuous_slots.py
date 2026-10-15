"""Fixed STOW web slots for a declared assembly order and full straight motions.

Order: inner root (fixture boundary), parked pawl, STOP0, STOP1, outer root.
Only the added web is further slotted; original root material may be removed
only inside the two already-declared nominal pawl envelopes. No state-following
cutters, OEM cuts, or change to STOP/pawl/fastener geometry is permitted.
"""
from pathlib import Path
from functools import lru_cache
import hashlib
import stow_motion_slots as previous
from straight_envelope import envelope
ROOT=previous.ROOT; GROUP=previous.GROUP; parent=previous.parent; b=previous.b
ROOT_NAME=previous.ROOT_NAME; check=previous.check; pairs=previous.pairs
volume_leaves=previous.volume_leaves


@lru_cache(maxsize=2)
def fixed_design(side):
    reference, returned, inserted, _ = previous.canonical_envelopes(side)
    pieces, prior = previous.fixed_operation_slots(side)
    parked=reference['PAWL'].translate(b.identity.evec('STOW',side,1.1))
    direction=b.identity.evec('STOW',side,-10.)
    fixed={'ROOT_INNER':reference['ROOT_INNER'],'STOP_0':reference['STOP_0'],
           'STOP_1':reference['STOP_1'],'PARKED_PAWL':parked}
    envelopes={};methods={}
    for name,shape in fixed.items():
        swept,method=envelope(shape,direction);envelopes[name]=swept;methods[name]=method
    web=b.fuse(list(pieces))
    for swept in envelopes.values():web=web.cut(swept).clean()
    leaves=volume_leaves(web)
    if not leaves:raise ValueError('full motion slots remove the whole connecting web')
    components=web.Solids()
    if len(leaves)!=len(components):raise ValueError('non-solid web result')
    original=reference[ROOT_NAME]
    core=original.cut(returned).cut(inserted).clean()
    candidate=core
    for component in components:candidate=candidate.fuse(component)
    candidate=candidate.clean();b.participant(candidate)
    removed=sum(volume_leaves(original.cut(candidate)));added=sum(volume_leaves(candidate.cut(original)))
    outside=sum(volume_leaves(original.cut(candidate).cut(returned).cut(inserted)))
    if outside>1e-7:raise ValueError('original material removed outside declared pawl collisions')
    if abs(original.Volume()+added-removed-candidate.Volume())>1e-7:raise ValueError('material accounting differs')
    oldbb,newbb=original.BoundingBox(),candidate.BoundingBox()
    if any(abs(getattr(newbb,k)-getattr(oldbb,k))>1e-7 for k in ('xmin','xmax','ymin','ymax','zmin','zmax')):raise ValueError('original root envelope expanded')
    report={'candidate':'fixed_continuous_assembly_slots','side':side,
            'assembly_order':['ROOT_INNER','PARKED_PAWL','STOP_0','STOP_1',ROOT_NAME],
            'prior_sample_slots':prior,'full_relative_slot_methods':methods,
            'slotted_web_components_all_kept':len(components),'root_positive_solids':1,
            'old_root_volume_mm3':original.Volume(),'new_root_volume_mm3':candidate.Volume(),
            'removed_original_mm3':removed,'added_mm3':added,'removed_outside_pawl_envelopes_mm3':outside,
            'full_root_bounds_unchanged':True,'only_outer_root_changed':True,
            'root_fixed_across_runtime_states':True,'web_nominal_thickness_mm':.25,
            'material_connected_not_load_qualified':True,'intermediate_fixture_and_gripping_not_qualified':True,
            'manufacturing_go':False,'candidate_go':False}
    return reference,candidate,envelopes,report


def repair_parts(parts,port,side,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:raise ValueError('invalid scene identity')
    if not enabled or port=='OPEN':return dict(parts),{'repair_enabled':enabled,'changed_parts':[],'manufacturing_go':False}
    reference,candidate,_,report=fixed_design(side)
    actual=parts[ROOT_NAME];b.participant(actual)
    if sum(volume_leaves(actual.cut(reference[ROOT_NAME])))>1e-7 or sum(volume_leaves(reference[ROOT_NAME].cut(actual)))>1e-7:raise ValueError('runtime root differs from pinned original')
    out=dict(parts);out[ROOT_NAME]=candidate
    if any(not out[n].wrapped.IsSame(s.wrapped) for n,s in parts.items() if n!=ROOT_NAME):raise ValueError('unrelated part changed')
    return out,{**report,'changed_parts':[ROOT_NAME]}


def scene(port,side,lift=1.14,present=True,*,enabled=True):
    parts,raw=parent.scene(port,side,lift,present)
    out,report=repair_parts(parts,port,side,enabled=enabled)
    return out,{**raw,'continuous_assembly_slots':report}
