"""Top-entry manual control with removable roof, thumb pad and shoulder pin.

Project-owned nominal assembly study. Original PAWL/KEY contacts remain intact;
only the declared pin corridor in the project root is widened. The detachable
pin, roof screws and pad screw have nominal thread envelopes and simple drive
slots, NOT verified threads, preload, forces, sealing or production tolerance.
Assembly is on a detached back-panel/cartridge subassembly; frame/B are absent.
"""
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import json
import tarfile
import tempfile
import cadquery as cq
import cam_coupling as c
import pawl_actuator as a
import verify_pawl_actuator as w

ROOT=Path(__file__).resolve().parents[1]
BASE='2fc753ddcd545dfe95854b0becc8d4063d1e0479'
SOURCE=ROOT/'engineering/pawl-actuation-20261015'
MOUNT_Y=(14.5,29.6)
MOUNT_X=11.6
ROOF_SPLIT_Z=6.7


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def parent():
    gm=SOURCE/'geometry-manifest.json';meta=json.loads(gm.read_text());arc=SOURCE/meta['archive']
    if sha(arc)!=meta['archive_sha256']:raise ValueError('parent archive identity changed')
    with tarfile.open(arc,'r:gz') as stream,tempfile.TemporaryDirectory(prefix='serviceable-parent-') as td:
        folder=Path(td)
        for rec in meta['files']:
            name=Path(rec['path'])
            if name.is_absolute() or len(name.parts)!=1:raise ValueError('unsafe frozen member')
            raw=stream.extractfile(str(name)).read()
            if len(raw)!=rec['bytes'] or hashlib.sha256(raw).hexdigest()!=rec['sha256']:raise ValueError('frozen member changed')
            (folder/name).write_bytes(raw)
        (folder/'manifest.json').write_bytes((SOURCE/'NATIVE_MANIFEST.json').read_bytes())
        _,b,_=w.load_new(folder/'manifest.json')
    return b


def z_screw(x,y,radius,head_radius,z0,head_top,tip):
    screw=c.one(c.cylinder(radius,head_top,tip,x,y).fuse(c.cylinder(head_radius,z0,head_top,x,y)).clean())
    # Rear face drive slot; finite shaft engagement can be checked independently.
    slit=c.box((x-head_radius-.05,y-.10,z0-.01),(x+head_radius+.05,y+.10,z0+.10))
    return c.one(screw.cut(slit).clean())


def shoulder_pin():
    body=c.one(a.pin(.4,11.,13.30,20.,5.3).fuse(a.pin(.65,10.8,11.,20.,5.3)).clean())
    slit=c.box((10.79,19.90,4.60),(10.90,20.10,6.00))
    return c.one(body.cut(slit).clean())


def material(old,new):
    loss=c.vol(old.cut(new));gain=c.vol(new.cut(old))
    if abs(c.vol(old)-loss+gain-c.vol(new))>1e-7:raise ValueError('complete material accounting mismatch')
    return {'old_mm3':c.vol(old),'removed_mm3':loss,'added_mm3':gain,'new_mm3':c.vol(new)}


@lru_cache(maxsize=1)
def build():
    old=parent();parts={};panel=c.housing_study()[0]['A_BACK_PANEL'];details={'sides':{}}
    for side in 'LR':
        mirror=lambda body:c.one(c.handed(body,side))
        pawl=old[side+'_ORIGINAL_PAWL']
        boss=c.one(a.pin(.65,12.2,13.8,20.,5.3).cut(a.pin(.4,12.0,13.35,20.,5.3)).clean())
        boss=mirror(boss)
        joint=w.v.common(pawl,boss)
        if joint<=1e-7:raise ValueError('socket boss is not connected to original PAWL')
        newpawl=c.one(pawl.fuse(boss).clean())
        if c.vol(pawl.cut(newpawl))>1e-7:raise ValueError('original PAWL material removed')
        root=c.parent(side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
        passage=mirror(a.slot_yz((20.,5.3),(20.,6.4),.70,12.05,13.85))
        root=c.one(root.cut(passage).clean())
        # Open-top guide body, preserving the original side guide geometry.
        original_guide=old[side+'_GUIDE']
        guide=c.one(original_guide.intersect(c.box((-40,13.,.5),(40,32.,ROOF_SPLIT_Z))).clean())
        roof=c.one(original_guide.cut(c.box((-40,13.,-.1),(40,32.,ROOF_SPLIT_Z))).clean())
        # Widen a fixed stem corridor for a one-mm square stem and pad fastener.
        stem_window=mirror(c.box((11.0,23.9,4.3),(12.2,28.1,4.7)))
        guide=c.one(guide.cut(stem_window).clean())
        for j,y in enumerate(MOUNT_Y):
            y0,y1=(13.4,16.) if j==0 else (28.2,30.7)
            foot=mirror(c.box((10.65,y0,.60),(12.55,y1,ROOF_SPLIT_Z)))
            roofpad=mirror(c.box((10.65,y0,ROOF_SPLIT_Z),(12.55,y1,7.3)))
            guide=c.one(guide.fuse(foot).clean());roof=c.one(roof.fuse(roofpad).clean())
            x=-MOUNT_X if side=='L' else MOUNT_X
            guide=c.one(guide.cut(c.cylinder(.55,.5,6.8,x,y)).clean())
            roof=c.one(roof.cut(c.cylinder(.5,6.6,7.0,x,y)).clean())
            parts[f'{side}_ROOF_SCREW_{j}_M1_NOMINAL']=z_screw(x,y,.5,.9,.1,.55,6.95)
        # The bottom pad is separate, so it no longer obstructs top entry.
        tabbase=old[side+'_TAB'].cut(c.box((-40,0,-.1),(40,40,4.6))).clean()
        stem=mirror(c.box((11.1,24.,.60),(12.1,25.,4.8)))
        tab=c.one(tabbase.fuse(stem).clean())
        x=-11.6 if side=='L' else 11.6
        tab=c.one(tab.cut(c.cylinder(.3,.5,1.30,x,24.5)).clean())
        pad=mirror(c.box((9.,23.2,.1),(12.45,25.4,.6)))
        pad=c.one(pad.cut(c.cylinder(.325,0.,.7,x,24.5)).cut(c.cylinder(.575,0.,.25,x,24.5)).clean())
        padscrew=z_screw(x,24.5,.3,.55,.1,.25,1.25)
        # Build the panel's fixed guide, retaining explicit rear access cutouts.
        overlap=w.v.common(panel,guide)
        if overlap<=1e-7:raise ValueError('new guide not joined to panel')
        panel=c.one(panel.fuse(guide).clean())
        panel=c.one(panel.cut(mirror(c.box((8.9,23.1,-.1),(12.55,28.5,.75)))).clean())
        for y in MOUNT_Y:
            x=-MOUNT_X if side=='L' else MOUNT_X
            panel=c.one(panel.cut(c.cylinder(.55,-.1,1.3,x,y)).clean())
            panel=c.one(panel.cut(c.cylinder(.95,-.1,.55,x,y)).clean())
        parts[side+'_PAWL']=newpawl
        parts[side+'_SHOULDER_PIN_NOMINAL']=mirror(shoulder_pin())
        parts[side+'_TAB']=tab;parts[side+'_THUMB_PAD']=pad;parts[side+'_PAD_SCREW_M06_NOMINAL']=padscrew
        parts[side+'_ROOF']=roof;parts[side+'_GUIDE_REFERENCE']=guide;parts[side+'_ROOT_OUTER']=root
        details['sides'][side]={'socket_to_original_PAWL_joint_mm3':joint,'panel_guide_joint_mm3':overlap,
            'PAWL_material':material(pawl,newpawl),'root_from_prior_pawl_candidate':material(old[side+'_ROOT_OUTER'],root),
            'roof_blind_tip_gap_mm':.05,'pad_blind_tip_gap_mm':.05,'pin_blind_tip_gap_mm':.05}
    parts['A_BACK_PANEL']=panel
    details['panel_material']=material(old['A_BACK_PANEL'],panel)
    details['manual_nominal_motion_unchanged']={'tab_mm':3.,'PAWL_mm':1.1,'slot_radius_mm':.425,'pin_radius_mm':.4}
    details['assembly_scope']='detached backpanel with original cartridges held in home pose, no A frame or B shell during top entry'
    details['fasteners']='nominal cylindrical thread envelopes and drive slots only; no preload/strength/fit certificate'
    details['endpoint_clearance_failures_from_prior_design_not_repaired']=True
    return parts,details


def scene(slide=0.,descent=0.,left=0.,right=0.):
    p,_=a.scene(slide,descent,left_tab=left,right_tab=right);new,_=build()
    for side,u in (('L',left),('R',right)):
        z=a.displacement(u);p[side+'_PAWL']=new[side+'_PAWL'].translate((0,0,z))
        p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
        for role in ('TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL'):p[side+'_'+role]=new[side+'_'+role].translate((0,u,0))
        p[side+'_SHOULDER_PIN_NOMINAL']=new[side+'_SHOULDER_PIN_NOMINAL'].translate((0,0,z))
        for role in ('ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL'):p[side+'_'+role]=new[side+'_'+role]
    p['A_BACK_PANEL']=new['A_BACK_PANEL'];return p


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output directory required')
    out.mkdir(parents=True,exist_ok=False);parts,details=build();exports={}
    for role,body in parts.items():
        p=out/(role+'.step');cq.exporters.export(body,str(p));b=body.BoundingBox()
        exports[role]={'path':p.name,'sha256':sha(p),'volume_mm3':c.vol(body),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    manifest={'base_main':BASE,'source_sha256':sha(__file__),'parent_archive_sha256':sha(SOURCE/'native-geometry.tar.gz'),
              'exports':exports,'construction':details,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    r=generate(parser.parse_args().output);print(json.dumps({'exports':len(r['exports']),'candidate_go':False}))
