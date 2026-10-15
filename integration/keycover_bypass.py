"""Fixed near-end cover reconnection and outer-root KEY channel.

The original cover box cannot connect its two retained plates around the
full KEY stroke. The new U connection extends that part's q-min by 2.1 mm,
explicitly, while staying in the existing 23-part bench bounding envelope.
This does NOT establish clearance in actual finished phone cavities.
"""
from functools import lru_cache
import stow_contact_slots as base
import cam_contact_native as n
from keycover_connectivity import prove
from straight_envelope import envelope, whole_material
ROOT=base.ROOT;GROUP=base.GROUP;b=base.b;parent=base.parent
baseline=base.baseline;previous=base.previous
ROOT_NAME=base.ROOT_NAME;check=base.check;pairs=base.pairs
volume_leaves=base.volume_leaves
BOUNDS=('xmin','xmax','ymin','ymax','zmin','zmax')

@lru_cache(maxsize=2)
def design(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    original,old_root,relative,old_receipt,_=base.build(side)
    key=original['KEY'];cover=original['OLD_COVER']
    barrier,exact_free,separation_proof=prove(key,cover,side)
    sweep,method=envelope(key.translate((0,-12.,0)),(0,12.,0))
    eb,qb,rb=n.bounds(side,cover)
    free=n.box(side,*eb,*qb,*rb).cut(sweep).clean()
    regions,free_volume=whole_material(free)
    split=cover.cut(sweep).clean();fragments,split_volume=whole_material(split)
    if len(regions)!=2 or len(fragments)!=2:raise ValueError('original bounded-connectivity counterexample changed')
    map_rows=[[n.common(fragment,region) for region in regions] for fragment in fragments]
    if not all(sum(v>1e-7 for v in row)==1 for row in map_rows) or sum(map_rows[i][0]>1e-7 for i in range(2))!=1:raise ValueError('cover fragments do not lie in separate free-space components')
    # Fixed stock, not a state-following intersection. Section matches old rib
    # 0.3 mm in q by 0.4 mm in r; finite joining overlap at both old posts.
    rail_left=n.box(side,-2.7,-2.4,-.4,5.2,-2.9,-2.5)
    rail_right=n.box(side,2.4,2.7,-.4,5.2,-2.9,-2.5)
    tie=n.box(side,-2.7,2.7,-.4,-.1,-2.9,-2.5)
    bridge=n.fuse([rail_left,rail_right,tie])
    repaired_cover=cover.fuse(bridge).cut(sweep).clean();n.single(repaired_cover)
    repaired_root=old_root.cut(sweep).clean();n.single(repaired_root)
    removed_cover=whole_material(cover.cut(repaired_cover),empty=True)[1]
    added_cover=whole_material(repaired_cover.cut(cover),empty=True)[1]
    removed_root=whole_material(old_root.cut(repaired_root),empty=True)[1]
    root_original_loss=whole_material(original[ROOT_NAME].intersect(old_root.cut(repaired_root)),empty=True)[1]
    if root_original_loss>1e-7:raise ValueError('KEY channel removes protected v9 root material')
    for old,new,label in [(cover,repaired_cover,'cover'),(old_root,repaired_root,'root')]:
        if whole_material(old.cut(new).cut(sweep),empty=True)[1]>1e-7:raise ValueError('material removed outside declared KEY stroke: '+label)
        if n.common(new,sweep)>1e-7:raise ValueError('KEY full stroke still intersects '+label)
    if abs(cover.Volume()+added_cover-removed_cover-repaired_cover.Volume())>1e-7:raise ValueError('cover material balance changed')
    if abs(old_root.Volume()-removed_root-repaired_root.Volume())>1e-7:raise ValueError('root material balance changed')
    # Complete lower plates, old holes and fastener interfaces are untouched.
    protected=n.box(side,eb[0]-.01,eb[1]+.01,qb[0]-.01,qb[1]+.01,rb[0]-.01,-6.4)
    delta_old=cover.cut(repaired_cover).intersect(protected)
    delta_new=repaired_cover.cut(cover).intersect(protected)
    if max(whole_material(delta_old,empty=True)[1],whole_material(delta_new,empty=True)[1])>1e-7:raise ValueError('cover plate or original fastening zone changed')
    prior_parts=dict(original);prior_parts[ROOT_NAME]=old_root
    new_parts=dict(prior_parts);new_parts[ROOT_NAME]=repaired_root;new_parts['OLD_COVER']=repaired_cover
    bb=n.cq.Compound.makeCompound(list(prior_parts.values())).BoundingBox();nb=n.cq.Compound.makeCompound(list(new_parts.values())).BoundingBox()
    assembly_delta={k:getattr(nb,k)-getattr(bb,k) for k in BOUNDS}
    if any(abs(v)>1e-7 for v in assembly_delta.values()):raise ValueError('whole bench envelope expanded')
    report={'candidate':'fixed_near_end_cover_bypass_and_KEY_root_channel','side':side,
        'parent_contact_receipt':old_receipt,'KEY_full_q_mm':[0.,12.],'KEY_envelope_method':method,
        'native_subset_separation_proof':separation_proof,'original_cover_allowed_space_components':2,'original_cut_cover_components':2,'component_membership_mm3':map_rows,
        'cover_part_bounds_before_eqr_mm':[eb,qb,rb],'cover_part_bounds_after_eqr_mm':n.bounds(side,repaired_cover),
        'cover_local_q_min_extension_mm':2.1,'whole_bench_bounds_delta_mm':assembly_delta,
        'cover_old_volume_mm3':cover.Volume(),'cover_new_volume_mm3':repaired_cover.Volume(),
        'cover_original_removed_mm3':removed_cover,'cover_added_mm3':added_cover,
        'contact_root_old_volume_mm3':old_root.Volume(),'root_new_volume_mm3':repaired_root.Volume(),
        'root_KEY_channel_removed_mm3':removed_root,'extra_original_v9_root_removed_mm3':root_original_loss,
        'old_cover_lower_plates_and_holes_preserved':True,'retained_material_fragments_reconnected_not_discarded':True,
        'two_changed_parts':[ROOT_NAME,'OLD_COVER'],'fixed_geometry_independent_of_runtime_pose':True,
        'actual_finished_phone_cavity_clearance_unknown':True,'fastener_thread_preload_and_load_strength_qualified':False,
        'fixture_fabrication_go':False,'candidate_go':False,'manufacturing_go':False}
    return original,repaired_root,repaired_cover,relative,report,sweep,free

def fixed_design(side):
    original,root,cover,relative,report,sweep,free=design(side)
    # Keep full prior fields for unmodified replay drivers, with explicit
    # current fields; old record is also retained under parent_contact_receipt.
    return original,root,relative,{**report['parent_contact_receipt'],**report}

def full_stop_envelopes(side):return base.full_stop_envelopes(side)

def repair_parts(parts,port,side,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:raise ValueError('invalid scene identity or switch')
    if not enabled or port=='OPEN':return dict(parts),{'changed_parts':[],'manufacturing_go':False}
    original,root,cover,relative,report,_,_=design(side)
    for name in (ROOT_NAME,'OLD_COVER'):
        for x,y in ((parts[name],original[name]),(original[name],parts[name])):
            if whole_material(x.cut(y),empty=True)[1]>1e-7:raise ValueError('runtime original identity differs: '+name)
    out=dict(parts);out[ROOT_NAME]=root;out['OLD_COVER']=cover
    if any(not out[k].wrapped.IsSame(v.wrapped) for k,v in parts.items() if k not in (ROOT_NAME,'OLD_COVER')):raise ValueError('unrelated component changed')
    return out,{**report,'changed_parts':[ROOT_NAME,'OLD_COVER']}

def scene(port,side,lift=1.14,present=True,*,enabled=True):
    parts,raw=parent.scene(port,side,lift,present)
    fixed,report=repair_parts(parts,port,side,enabled=enabled)
    return fixed,{**raw,'keycover_bypass':report}
