"""R20: STEP solids for LOCAL gated contact-carriage kinematics.
All local dogs/carrier/housing are unverified machining envelopes. TE geometry is a
WORKING-HEIGHT RECTANGULAR PROXY (not TE's real STEP). Six authored scenarios
include intended contact/release collisions, not a complete mechanically driven cam.
"""
import json,hashlib,sys
from pathlib import Path
import cadquery as cq
from r20_model import p,ROOT
ROOT_CAD=ROOT/'cad';ROOT_CAD.mkdir(exist_ok=True)
def box(x0,x1,y0,y1,z0,z1):
    assert x1>x0 and y1>y0 and z1>z0
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0,centered=False).translate((x0,y0,z0)).val()
def vol(a,b):return float(a.intersect(b).Volume())
def local_assembly(retract=True,left_open=False,right_open=False):
    shift= -p.retract if retract else 0.
    # A conductive pads are generic flat copper sheets, matching documented footprint but NOT OEM PCB
    parts={}
    for i,x in enumerate(p.x_pins):
        parts[f'A_PAD_{i}']=box(x-p.pad_width/2,x+p.pad_width/2,-p.pad_length/2,p.pad_length/2,0,p.pad_t)
        h=p.free_height if retract else p.nominal_h
        base=-p.nominal_h+shift
        parts[f'B_TE_CONTACT_RECT_PROXY_{i}']=box(x-p.te_width/2,x+p.te_width/2,-p.te_length/2,p.te_length/2,base,base+h)
    # Carrier lugs with a purposely separate, valid, physical interference when the corresponding shutter is CLOSED.
    for side in (-1,1):
        xa,xb=p.tongue_left if side==-1 else (-p.tongue_left[1],-p.tongue_left[0])
        parts[f'B_CARRIER_LUG_{"L" if side==-1 else "R"}']=box(xa,xb,-.5,.5,
             p.tongue_zmin+shift,p.tongue_zmax+shift)
        da,db=p.dog_closed_left if side==-1 else (-p.dog_closed_left[1],-p.dog_closed_left[0])
        is_open=left_open if side==-1 else right_open
        dshift=(-p.dog_retract_x if side==-1 else p.dog_retract_x) if is_open else 0
        name='L' if side==-1 else 'R'
        parts[f'B_DOG_{name}']=box(da+dshift,db+dshift,-.65,.65,p.dog_zmin,p.dog_zmax)
        # Side capture ribs with a pocket; ribs deliberately NOT contacting moving dog or lug.
        # Physical end-stop actuator is not modeled; do not interpret as assembled real cam.
        if side==-1:
            parts[f'B_GUIDE_RIB_{name}']=box(-23.5,-20.9,-3,3,-2.85,-.35)
        else:
            parts[f'B_GUIDE_RIB_{name}']=box(20.9,23.5,-3,3,-2.85,-.35)
    parts['B_BOTTOM_CARRIER_BACKBONE_PROXY']=box(-15,15,-2.8,-2.45,-2.85+shift,-2.58+shift)
    return parts

SCENES=[
 ('01_SLIDE_RETRACTED_DOGS_CLOSED',True,False,False,False),
 ('02_ONE_SIDE_SEATED_RETRACTED',True,True,False,False),
 ('03_BOTH_DOGS_OPEN_RETRACTED',True,True,True,False),
 ('04_BOTH_DOGS_OPEN_ENGAGED',False,True,True,False),
 ('05_FAULT_FORCE_WITH_LEFT_CLOSED',False,False,True,True),
 ('06_FAULT_FORCE_WITH_RIGHT_CLOSED',False,True,False,True),
 ('07_FAULT_FORCE_BOTH_CLOSED',False,False,False,True),
 ('08_FAULT_FALSE_BOTH_OPEN_EARLY',False,True,True,False),
 ('09_REVERSE_AFTER_RETRACT',True,False,False,False)]

def collision_metrics(parts):
    return {'L_block_mm3':vol(parts['B_CARRIER_LUG_L'],parts['B_DOG_L']),
            'R_block_mm3':vol(parts['B_CARRIER_LUG_R'],parts['B_DOG_R']),
            'pad_contact_overlap_mm3':sum(vol(parts[f'A_PAD_{i}'],parts[f'B_TE_CONTACT_RECT_PROXY_{i}']) for i in range(4)),
            'dog_L_rib_overlap_mm3':vol(parts['B_DOG_L'],parts['B_GUIDE_RIB_L']),
            'dog_R_rib_overlap_mm3':vol(parts['B_DOG_R'],parts['B_GUIDE_RIB_R'])}

def run(write=True):
    rows=[]
    for tag,retract,L,R,should_block in SCENES:
        parts=local_assembly(retract,L,R)
        cm=collision_metrics(parts)
        assert cm['dog_L_rib_overlap_mm3']<1e-8 and cm['dog_R_rib_overlap_mm3']<1e-8
        assert cm['pad_contact_overlap_mm3']<1e-8
        if should_block:assert cm['L_block_mm3']>0 or cm['R_block_mm3']>0,(tag,cm)
        else:assert cm['L_block_mm3']<1e-8 and cm['R_block_mm3']<1e-8,(tag,cm)
        fp=ROOT_CAD/(tag+'.step')
        if write:
            a=cq.Assembly(name='R20_'+tag)
            for name,solid in parts.items():
                if name.startswith('A_PAD'):color=cq.Color(.30,.70,.80)
                elif name.startswith('B_DOG'):color=cq.Color(.90,.23,.28)
                elif name.startswith('B_CARRIER_LUG'):color=cq.Color(.95,.65,.12)
                else:color=cq.Color(.42,.48,.58)
                a.add(solid,name=name,color=color)
            a.save(str(fp),exportType='STEP')
            imported=cq.importers.importStep(str(fp)).solids().vals()
            assert len(imported)==len(parts) and all(v.isValid() for v in imported),(tag,len(imported),len(parts))
            sha=hashlib.sha256(fp.read_bytes()).hexdigest()
        else:sha=None
        rows.append(dict(tag=tag,retracted=retract,gate_L_open=L,gate_R_open=R,
             should_block=should_block,parts=len(parts),collisions=cm,step_sha256=sha,
             failsafe_outcome=('blocked_by_lug' if should_block else ('NO_REAL_SEATING_PROOF' if not retract else 'parked'))))
    # Verify local packaging envelopes vs R19's OEM-proxy placeholder for OPEN and STOW, no falsely clean bill.
    xspan=2*p.station_halfwidth
    yspan=2*p.y_station_halfextent
    module_volume=xspan*yspan*2.50/1000
    summary=dict(revision='R20 compact local-dog docking demonstrator, not OEM fit',rows=rows,
        envelope=dict(x_span_mm=xspan,y_span_mm=yspan,proxy_h_mm=2.5,
                      upper_bound_cartridge_envelope_cm3_per_port=module_volume,
                      two_station_envelope_cm3=2*module_volume),
        vendor_REAL_STEP_imported=False,
        unmodeled=['dog/cam seating actuation','elastic force-displacement','blind-mate alignment / vibration',
          'side-wall strength and full R17/19 assembly packaging','current and PCB thermal'],
        unsafe_fault=['08_FAULT_FALSE_BOTH_OPEN_EARLY has NO geometry blockade; hard-stop actuation unproven'],
        assembly_manufacturing_release=False)
    if write:(ROOT/'verification'/'R20_local_cad_results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    return summary
if __name__=='__main__':
    out=run();print('R20 CAD',len(out['rows']),'poses',out['rows'][4]['collisions'])
