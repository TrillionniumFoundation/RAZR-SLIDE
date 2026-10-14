"""Candidate shoulder bypass and FIXED motion grooves in project-owned STOW roots.
No original R4 STOP material is cut. No enclosure/OLED/battery shape is changed.
Continuous nominal swept space is not a force, fatigue or toleranced clearance proof.
"""
from pathlib import Path
from functools import lru_cache
import math
import stow_motion_slots as previous
parent=previous.parent
b=previous.b
ROOT=previous.ROOT
GROUP=previous.GROUP
ROOT_NAME=previous.ROOT_NAME
check=previous.check
pairs=previous.pairs
volume_leaves=previous.volume_leaves
planar_translation_sweep=previous.planar_translation_sweep
canonical_envelopes=previous.canonical_envelopes

def material_volume(shape):return sum(volume_leaves(shape))

def shoulder_recipe(side,index):
    z=2.64+5*index
    # Fixed lower-Q U bypass, replacing only the added R6 shoulder bridge.
    parts=[b.box(.74,1.36,1.08,1.20,z,z+.30),
           b.box(.74,.94,1.08,1.38,z,z+.30),
           b.box(1.16,1.36,1.08,1.38,z,z+.30)]
    u=b.world(b.fuse(parts),'STOW',side)
    cut=b.world(b.box(.94,1.16,1.24,1.40,z-.01,z+.31),'STOW',side)
    return cut,u

@lru_cache(maxsize=2)
def fixed_geometry(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    original,audit=previous.scene('STOW',side,1.14,True)
    old_r4,_=b.source('STOW');parts=dict(original);grooves=[];stop_audits=[]
    for i in (0,1):
        name='STOP_'+str(i);cut,u=shoulder_recipe(side,i)
        new=original[name].cut(cut).fuse(u).clean();b.participant(new)
        inherited=old_r4[side][name].translate(b.rvec('STOW',-.06))
        lost=material_volume(inherited.cut(new))
        if lost>1e-7:raise ValueError('inherited R4 stop material lost')
        removed=material_volume(original[name].cut(new));added=material_volume(new.cut(original[name]))
        if abs(original[name].Volume()+added-removed-new.Volume())>1e-7:raise ValueError('STOP material accounting')
        parts[name]=new
        moving_start=u.translate(b.rvec('STOW',-1.16))
        dynamic,dm=planar_translation_sweep(moving_start,b.rvec('STOW',1.22))
        # Relative sweep for outer-root E+10 approach to the settled STOP.
        access,am=planar_translation_sweep(u,b.identity.evec('STOW',side,-10.))
        grooves.extend([dynamic,access])
        stop_audits.append({'part':name,'old_volume_mm3':original[name].Volume(),'new_volume_mm3':new.Volume(),
            'original_R4_material_lost_mm3':lost,'removed_added_shoulder_mm3':removed,'new_bypass_material_mm3':added,
            'local_bypass_Q_mm':[1.08,1.20],'nominal_bridge_thickness_mm':.30,
            'dynamic_lift_range_mm':[-.02,1.20],'outer_root_approach_mm':10.,
            'dynamic_envelope':dm,'assembly_relative_envelope':am})
    old=original[ROOT_NAME];new=old
    for groove in grooves:new=new.cut(groove).clean()
    b.participant(new)
    removed=old.cut(new);outside=removed
    for groove in grooves:outside=outside.cut(groove)
    if material_volume(outside)>1e-7:raise ValueError('root cut outside declared fixed groove envelopes')
    added=material_volume(new.cut(old))
    if added>1e-7:raise ValueError('unexpected material added to root')
    parts[ROOT_NAME]=new
    for name,shape in original.items():
        if name not in ['STOP_0','STOP_1',ROOT_NAME] and not shape.wrapped.IsSame(parts[name].wrapped):raise ValueError('unrelated part changed')
    receipt={'side':side,'base_repair':'fixed operation slots','stop_changes':stop_audits,
        'root_old_volume_mm3':old.Volume(),'root_new_volume_mm3':new.Volume(),'root_removed_mm3':material_volume(removed),
        'root_removed_outside_declared_grooves_mm3':material_volume(outside),'root_positive_solids':1,
        'root_is_fixed_across_all_lift_key_states':True,'changed_parts':['STOP_0','STOP_1',ROOT_NAME],
        'new_root_cut_beyond_previous_two_pawl_envelopes':True,
        'enclosure_or_OLED_or_battery_shapes_changed':False,
        'mechanical_load_path_strength_qualified':False,'manufacturing_go':False}
    return parts,receipt

def scene(port,side,lift=1.14,present=True,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool or not math.isfinite(lift) or not -.02<=lift<=1.20:raise ValueError('unsupported scene state')
    original,raw=previous.scene(port,side,lift,present)
    if not enabled or port=='OPEN':return original,raw
    fixed,audit=fixed_geometry(side);parts=dict(original)
    parts[ROOT_NAME]=fixed[ROOT_NAME]
    for i in (0,1):parts['STOP_'+str(i)]=fixed['STOP_'+str(i)].translate(b.rvec(port,lift-1.14))
    return parts,{**raw,'shoulder_clearance_repair':audit}
