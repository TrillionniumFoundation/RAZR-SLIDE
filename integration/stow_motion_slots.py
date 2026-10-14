"""Fixed design-time slots in a narrow STOW side web, followed by fresh replay.

All slot positions are frozen by the original 564-row native operation report.
No root geometry follows the simulated KEY/STOP state. This is a sampled
motion-compatible research design, not continuous KEY/STOP or force proof.
"""
from pathlib import Path
from functools import lru_cache
import gzip
import hashlib
import json
import stow_web_repair as prior

ROOT=prior.ROOT
GROUP=prior.GROUP
parent=prior.parent
b=prior.b
check=prior.check
pairs=prior.pairs
ROOT_NAME=prior.ROOT_NAME
volume_leaves=prior.volume_leaves
planar_translation_sweep=prior.planar_translation_sweep
canonical_envelopes=prior.canonical_envelopes
modification_geometry=prior.modification_geometry
HISTORY_SHA256='0136db902bf133291e6e2fc1118b1ac6a10110f3e0659b9d097744ff3e060132'


@lru_cache(maxsize=2)
def fixed_operation_slots(side):
    path=ROOT/'engineering/workplan-execution-20261014/integration/sequence-native-report.json.gz'
    payload=gzip.decompress(path.read_bytes())
    digest=hashlib.sha256(payload).hexdigest()
    if digest!=HISTORY_SHA256:raise ValueError('frozen original native operation changed')
    history=json.loads(payload)
    if history['row_count']!=564 or history['unexpected_positive_rows']!=18:raise ValueError('original failed operation replaced')
    reference,returned,insertion,method=canonical_envelopes(side)
    cutters=[shape for name,shape in reference.items() if name not in (ROOT_NAME,'PAWL')]
    cam_rows=[row for row in history['cam_brackets'] if row['port']=='STOW' and row['side']==side]
    if len(cam_rows)!=14:raise ValueError('original cam pose coverage changed')
    for row in cam_rows:
        cutters.append(reference['KEY'].translate(b.identity.qvec('STOW',row['q_mm'])))
        for i,lift in enumerate(row['actual_cam_collision_free_lifts_mm']):
            cutters.append(reference['STOP_'+str(i)].translate(b.rvec('STOW',lift-1.14)))
    for d in (10.,6.,3.,1.,.5,.1,0.):
        for name in ('STOP_0','STOP_1','ROOT_INNER'):
            cutters.append(reference[name].translate(b.identity.evec('STOW',side,-d)))
    if len(cutters)!=84:raise ValueError('fixed cutter count changed')
    plate=b.world(b.box(.05,.30,1.10,2.15,-9.60,9.35),'STOW',side)
    for cutter in cutters:plate=plate.cut(cutter).clean()
    leaves=volume_leaves(plate);components=plate.Solids()
    if not leaves or len(leaves)!=len(components):raise ValueError('slotted web has missing or extra topology')
    return tuple(components),{'fixed_cutter_count':84,'original_operation_sha256':digest,
                              'all_web_components_retained':len(components),
                              'runtime_state_changes_do_not_recut_root':True}


def repair_parts(parts,port,side,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:
        raise ValueError('invalid scene identity or repair switch')
    original=parts[ROOT_NAME];b.participant(original);out=dict(parts)
    report={'port':port,'side':side,'repair_enabled':enabled,'changed_parts':[],
            'mechanical_strength_qualified':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    if not enabled or port=='OPEN':return out,report
    _,returned,insertion,_=canonical_envelopes(side)
    components,slot_receipt=fixed_operation_slots(side)
    candidate=original
    for component in components:candidate=candidate.fuse(component)
    candidate=candidate.clean().cut(returned).cut(insertion).clean()
    b.participant(candidate)
    removed=original.cut(candidate);added=candidate.cut(original)
    removed_total=sum(volume_leaves(removed));added_total=sum(volume_leaves(added))
    outside=sum(volume_leaves(removed.cut(returned).cut(insertion)))
    if outside>1e-7:raise ValueError('material loss outside declared two motion conflicts')
    if abs(original.Volume()+added_total-removed_total-candidate.Volume())>1e-7:raise ValueError('material balance mismatch')
    aa,bb=original.BoundingBox(),candidate.BoundingBox()
    delta={k:float(getattr(bb,k)-getattr(aa,k)) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}
    if any(abs(v)>1e-7 for v in delta.values()):raise ValueError('outer-root envelope expanded')
    out[ROOT_NAME]=candidate
    if any(not out[k].wrapped.IsSame(v.wrapped) for k,v in parts.items() if k!=ROOT_NAME):raise ValueError('unrelated part modified')
    report.update({'changed_parts':[ROOT_NAME],'candidate':'fixed_operation_slotted_side_web',
                   'side_web_parameters_local_mm':[.05,.30,1.10,2.15,-9.60,9.35],
                   'nominal_web_thickness_mm':.25,'fixed_design_slots':slot_receipt,
                   'old_volume_mm3':original.Volume(),'new_volume_mm3':candidate.Volume(),
                   'removed_material_mm3':removed_total,'added_material_mm3':added_total,
                   'removed_outside_declared_motion_envelopes_mm3':outside,'bounds_delta_mm':delta,
                   'all_other_parts_same_shape_identity':True,'final_root_solids':1,
                   'all_material_outside_declared_motion_envelopes_retained':True,
                   'canonical_cut_state':{'lift_mm':1.14,'key_present':True},
                   'root_not_recut_for_actual_lift_or_key_state':True,
                   'load_path_material_connected_not_strength_qualified':True})
    return out,report


def scene(port,side,lift=1.14,present=True,*,enabled=True):
    parts,raw=parent.scene(port,side,lift,present)
    repaired,receipt=repair_parts(parts,port,side,enabled=enabled)
    return repaired,{**raw,'fixed_slot_repair':receipt}
