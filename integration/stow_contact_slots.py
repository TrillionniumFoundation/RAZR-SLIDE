"""Remove only V2 added-web material intersected by the complete STOP stroke.

The design is fixed at construction time. It does not follow the current cam
pose. Original R4/v9 material, all non-root parts, and OPEN geometry stay intact.
"""
from functools import lru_cache
import stow_continuous_slots_v2 as baseline
from straight_envelope import envelope, whole_material
ROOT=baseline.ROOT; GROUP=baseline.GROUP; b=baseline.b; parent=baseline.parent
previous=baseline.previous
ROOT_NAME=baseline.ROOT_NAME; check=baseline.check; pairs=baseline.pairs
volume_leaves=baseline.volume_leaves

@lru_cache(maxsize=2)
def build(side):
    if side not in ('L','R'):raise ValueError('invalid STOW side')
    original,v2,relative,receipt=baseline.fixed_design(side)
    swept={};methods={};new=v2
    for i in range(2):
        source=original[f'STOP_{i}'].translate((0,0,-1.16))
        path,method=envelope(source,(0,0,1.16));swept[f'STOP_{i}']=path;methods[f'STOP_{i}']=method
        new=new.cut(path).clean()
    b.participant(new)
    removed=whole_material(v2.cut(new),empty=True)[1]
    old_material_removed=whole_material(original[ROOT_NAME].intersect(v2.cut(new)),empty=True)[1]
    if old_material_removed>1e-7:raise ValueError('new contact repair removes protected original material')
    if abs(v2.Volume()-removed-new.Volume())>1e-7:raise ValueError('V2-to-contact material balance changed')
    bb,nb=v2.BoundingBox(),new.BoundingBox()
    if any(abs(getattr(bb,k)-getattr(nb,k))>1e-7 for k in ('xmin','xmax','ymin','ymax','zmin','zmax')):raise ValueError('root external bounds changed')
    for sh in swept.values():
        if b.strict_common(new,sh)['checked_volume_mm3']>1e-7:raise ValueError('complete STOP stroke still collides')
    new_receipt={**receipt,'candidate':'fixed_full_STOP_stroke_slots','prior_candidate':'fixed_continuous_assembly_slots_v2',
        'V2_root_volume_mm3':v2.Volume(),'new_root_volume_mm3':new.Volume(),
        'additional_V2_web_removed_mm3':removed,'additional_original_material_removed_mm3':old_material_removed,
        'full_STOP_stroke_mm':1.16,'full_STOP_stroke_methods':methods,
        'new_root_single_positive_solid':True,'root_fixed_across_runtime_states':True,
        'dynamic_contact_friction_tolerance_or_strength_qualified':False,'manufacturing_go':False}
    return original,new,relative,new_receipt,swept

def fixed_design(side):return build(side)[:4]
def full_stop_envelopes(side):return build(side)[4]

def repair_parts(parts,port,side,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:raise ValueError('invalid identity or switch')
    if not enabled or port=='OPEN':return dict(parts),{'changed_parts':[],'manufacturing_go':False}
    original,new,relative,receipt,_=build(side)
    source=parts[ROOT_NAME];expected=original[ROOT_NAME]
    if whole_material(source.cut(expected),empty=True)[1]>1e-7 or whole_material(expected.cut(source),empty=True)[1]>1e-7:raise ValueError('unexpected original root')
    out=dict(parts);out[ROOT_NAME]=new
    if any(not out[n].wrapped.IsSame(sh.wrapped) for n,sh in parts.items() if n!=ROOT_NAME):raise ValueError('non-root part changed')
    return out,{**receipt,'changed_parts':[ROOT_NAME]}

def scene(port,side,lift=1.14,present=True,*,enabled=True):
    parts,raw=parent.scene(port,side,lift,present)
    repaired,report=repair_parts(parts,port,side,enabled=enabled)
    return repaired,{**raw,'full_stop_contact_repair':report}
