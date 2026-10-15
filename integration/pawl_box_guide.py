"""Body-bearing Y lands and relieved follower-carrier edges.

Add two joined stationary Y-bearing lands per side. Widen only stationary
pin-head clearance in panel/guide reference/roof, so the intended body lands
precede fragile pin-carrier edge contact for the specified coupled slot path.
No preload, actual material strength, contact stress or free-play rating is
inferred. All existing moving/locking/fastener geometry remains exact.
"""
from pathlib import Path
import argparse,json,math
import cadquery as cq
from verify_pawl_lateral_guide import load_new
from verify_root_clearance import single,vol,common,box,hand,sha

ROOT=Path(__file__).resolve().parents[1]
BASE='4c5aaa838e3bcdd0c6f52b0501593690d061cb89'
Y_LANDS=(('front',(14.6,17.9,4.5),(15.6,18.075,7.3)),
         ('rear',(14.6,22.225,4.5),(15.6,22.4,7.3)))
RELIEF_RADIUS=.80
RELIEF_Y=20.
RELIEF_Z=(5.3,6.4)
RELIEF_X=(10.5,12.6)


def carrier_relief():
    # Exact union of complete X cylinders plus their YZ rectangular bridge.
    cylinders=[cq.Solid.makeCylinder(RELIEF_RADIUS,RELIEF_X[1]-RELIEF_X[0],
         cq.Vector(RELIEF_X[0],RELIEF_Y,z),cq.Vector(1,0,0)) for z in RELIEF_Z]
    bridge=box((RELIEF_X[0],RELIEF_Y-RELIEF_RADIUS,RELIEF_Z[0]),
               (RELIEF_X[1],RELIEF_Y+RELIEF_RADIUS,RELIEF_Z[1]))
    return single(cylinders[0].fuse(cylinders[1]).fuse(bridge).clean())


def build(base):
    expected={s+'_'+r for s in 'LR' for r in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')}|{'A_BACK_PANEL'}
    if set(base)!=expected:raise ValueError('complete lateral-guide baseline required')
    parts=dict(base);changes={};panel=base['A_BACK_PANEL']
    for side in 'LR':
        root=base[side+'_ROOT_OUTER'];joints=[]
        for name,lo,hi in Y_LANDS:
            land=hand(box(lo,hi),side);joint=common(land,root)
            if joint<=1e-7:raise ValueError('Y land lacks real attachment')
            joints.append({'land':name,'native_joint_overlap_mm3':joint})
            root=single(root.fuse(land).clean())
        parts[side+'_ROOT_OUTER']=root
        cutter=hand(carrier_relief(),side)
        for role in ('ROOF','GUIDE_REFERENCE'):
            parts[side+'_'+role]=single(base[side+'_'+role].cut(cutter).clean())
        panel=single(panel.cut(cutter).clean())
        changes[side+'_land_connections']=joints
    parts['A_BACK_PANEL']=panel
    for name,body in parts.items():
        if body.isSame(base[name]):continue
        before=base[name];removed=vol(before.cut(body));added=vol(body.cut(before))
        if abs(vol(before)-removed+added-vol(body))>1e-7:raise ValueError('material balance differs')
        if name.endswith('ROOT_OUTER') and removed>1e-7:raise ValueError('old root material removed')
        if not name.endswith('ROOT_OUTER') and added>1e-7:raise ValueError('undeclared stationary addition')
        changes[name]={'removed_mm3':removed,'added_mm3':added,'new_volume_mm3':vol(body),'connected_solids':1}
    return parts,changes


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    _,base,h=load_new(baseline);parts,changes=build(base)
    out.mkdir(parents=True,exist_ok=False);exports={}
    for name,body in parts.items():
        f=out/(name+'.step');cq.exporters.export(body,str(f));b=body.BoundingBox()
        exports[name]={'path':f.name,'sha256':sha(f),'volume_mm3':vol(body),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(sha(f)!=v for f,v in h.items()):raise ValueError('baseline changed during generation')
    data={'base_main':BASE,'source_sha256':sha(__file__),'baseline_manifest_sha256':sha(baseline),'baseline_input_sha256':h,
          'exports':exports,'material':changes,'new_Y_lands_R_mm':Y_LANDS,'stationary_pin_carrier_radius_mm':RELIEF_RADIUS,
          'pure_Y_body_contact_mm':[-.075,.075],'relief_is_not_free_play_or_load_qualification':True,
          'moving_PAWL_KEY_pins_slot_and_all_fasteners_unchanged':True,
          'selected_material_forces_preload_and_stiffness_qualified':False,
          'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(data,indent=2)+'\n');return data

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();r=generate(args.baseline,args.output);print(json.dumps({'templates':len(r['exports']),'material':r['material']}))
