"""Body-first Y bearing guide and fixed collar relief, not load qualification.

Two finite Y lands per outer root transfer the *geometric* first-contact path
from the shoulder/socket to the original PAWL guide block. Existing opposed
X lands/cover remain exact. Unchanged moving contacts still need actual
preload, stiffness, friction, process and coupled-mobility qualification.
"""
from pathlib import Path
import argparse
import json
import cadquery as cq
import verify_pawl_lateral_guide as v

ROOT=Path(__file__).resolve().parents[1]
BASE='4c5aaa838e3bcdd0c6f52b0501593690d061cb89'
# Fixed right-hand manufacturing geometry, left mirrored. No pose-dependent cuts.
LANDS=(('front',(14.4,17.85,4.50),(16.3,18.07,7.30)),
       ('rear',(14.4,22.23,4.50),(16.3,22.45,7.30)))
COLLAR_RADIUS=.78
CHEEKS=((10.70,11.055),(12.145,12.50))


def cylinder_x(radius,x0,x1,y,z):
    return v.v.single(cq.Solid.makeCylinder(radius,x1-x0,cq.Vector(x0,y,z),cq.Vector(1,0,0)))


def reliefs(side):
    result=[]
    for x0,x1 in CHEEKS:
        a=cylinder_x(COLLAR_RADIUS,x0,x1,20.,5.3)
        b=cylinder_x(COLLAR_RADIUS,x0,x1,20.,6.4)
        mid=v.v.box((x0,20.-COLLAR_RADIUS,5.3),(x1,20.+COLLAR_RADIUS,6.4))
        result.append(v.v.hand(v.v.single(a.fuse(b).fuse(mid).clean()),side))
    return result


def additions(side):
    if side not in ('L','R'):raise ValueError('explicit side required')
    return [(name,v.v.hand(v.v.box(lo,hi),side)) for name,lo,hi in LANDS]


def build(base):
    expected={s+'_'+k for s in 'LR' for k in ('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL',
        'PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE',
        'ROOT_OUTER','ROOT_INNER','OLD_COVER')}|{'A_BACK_PANEL'}
    if set(base)!=expected:raise ValueError('complete current 25-template baseline required')
    parts=dict(base);details={};panel=base['A_BACK_PANEL']
    for side in 'LR':
        key=side+'_ROOT_OUTER';old=base[key];root=old
        for _,land in additions(side):
            if v.v.common(old,land)<=v.TOL:raise ValueError('body land disconnected')
            root=v.v.single(root.fuse(land).clean())
        parts[key]=root
        for role in ('GUIDE_REFERENCE','ROOF'):
            key=side+'_'+role;body=base[key]
            for tool in reliefs(side):body=body.cut(tool).clean()
            parts[key]=v.v.single(body)
        for tool in reliefs(side):panel=panel.cut(tool).clean()
    parts['A_BACK_PANEL']=v.v.single(panel)
    changed={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('ROOT_OUTER','GUIDE_REFERENCE','ROOF')}
    for key in sorted(changed):
        old,new=base[key],parts[key];loss=v.v.vol(old.cut(new));gain=v.v.vol(new.cut(old))
        if abs(v.v.vol(old)-loss+gain-v.v.vol(new))>v.TOL:raise ValueError('material accounting mismatch: '+key)
        if key.endswith('ROOT_OUTER') and loss>v.TOL:raise ValueError('original root removed')
        if not key.endswith('ROOT_OUTER') and gain>v.TOL:raise ValueError('unexpected collar-region addition')
        details[key]={'removed_mm3':loss,'added_mm3':gain,'connected_solids':1}
    return parts,details


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external directory required')
    _,base,h=v.load_new(baseline);new,details=build(base);out.mkdir(parents=True,exist_ok=False);exports={}
    for key,body in new.items():
        f=out/(key+'.step');cq.exporters.export(body,str(f));bb=body.BoundingBox()
        exports[key]={'path':f.name,'sha256':v.v.sha(f),'volume_mm3':v.v.vol(body),
                     'bounds_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]}
    if any(v.v.sha(p)!=x for p,x in h.items()):raise ValueError('baseline changed')
    r={'base_main':BASE,'source_sha256':v.v.sha(__file__),'baseline_manifest_sha256':v.v.sha(baseline),
       'exports':exports,'material':details,'fixed_body_Y_lands_R':LANDS,'collar_relief_radius_mm':COLLAR_RADIUS,
       'collar_relief_cheeks_R':CHEEKS,'PAWL_KEY_slot_pins_fasteners_and_active_outer_cover_unchanged':True,
       'nominal_Y_body_contact_mm':[-.08,.08],
       'claim_scope':'body-first fixed-orientation coupled-Y/Z guide; finite rotation, force and process separately unqualified',
       'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=generate(a.baseline,a.output);print(json.dumps({'templates':len(r['exports']),'material':r['material']}))
