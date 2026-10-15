"""Two independent manual closed-slot PAWL actuators in the existing study shell.

A rear-access translating tab moves 3 mm in Y. The actual inclined slot moves
an attached PAWL pin nominally 1.1 mm in Z, in both directions. Groove/guide
play remains real; no automatic return force, detent, load or ergonomics is
claimed. Original PAWL, KEY and interlock contact material is retained.
"""
from pathlib import Path
from functools import lru_cache
import argparse
import json
import math
import cadquery as cq
import cam_coupling as c
from verify_cam_coupling import common

ROOT=Path(__file__).resolve().parents[1]
BASE='27abd4d77f83cf4ad6dcf25acdad7e34a8206a8a'
TRAVEL=3.0
PAWL_TRAVEL=1.1
SLOPE=PAWL_TRAVEL/TRAVEL
PIN_RADIUS=.4
SLOT_RADIUS=.425
PIN_Y=20.0
PIN_Z=5.3


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('finite real value required')
    return float(value)


def displacement(tab_mm):
    tab_mm=number(tab_mm)
    if not 0<=tab_mm<=TRAVEL:raise ValueError('manual tab outside designed stroke')
    return SLOPE*tab_mm


def output_interval(tab_mm):
    center=displacement(tab_mm)
    half=(SLOT_RADIUS-PIN_RADIUS)*math.hypot(1.,SLOPE)
    return {'center_mm':center,'lower_mm':center-half,'upper_mm':center+half,
            'slot_only_halfwidth_mm':half,'unique_without_load_or_preload':False}


def pin(radius,x0,x1,y,z):
    return c.one(cq.Solid.makeCylinder(radius,x1-x0,cq.Vector(x0,y,z),cq.Vector(1,0,0)))


def slot_yz(a,b,radius,x0,x1):
    return c.one(c.capsule(a,b,radius,x0,x1).rotate((0,0,0),(1,1,1),120))


@lru_cache(maxsize=1)
def build():
    shapes={};joints=[];panels=c.housing_study()[0];panel=panels['A_BACK_PANEL']
    slot=slot_yz((20.2,PIN_Z-.2*SLOPE),(16.8,PIN_Z+3.2*SLOPE),SLOT_RADIUS,11.0,12.2)
    plate=c.box((11.1,16.,4.6),(12.1,25.,7.15))
    plate=c.one(plate.cut(slot).clean())
    stem=c.box((11.3,24.0,.35),(11.9,24.6,4.8))
    pad=c.box((9.,23.2,.1),(12.45,25.4,.45))
    slider=c.one(plate.fuse(stem).fuse(pad).clean())
    shaft=pin(PIN_RADIUS,10.8,14.2,PIN_Y,PIN_Z)
    shaft=c.one(shaft.fuse(pin(.65,10.8,11.,PIN_Y,PIN_Z)).fuse(pin(.65,12.2,12.4,PIN_Y,PIN_Z)).clean())
    floor=c.box((10.75,15.7,4.4),(12.45,28.3,4.55))
    floor=c.one(floor.cut(c.box((11.2,23.9,4.3),(12.,27.7,4.7))).clean())
    rear=c.box((10.75,15.7,4.5),(11.05,28.3,7.3))
    front=c.box((12.15,15.7,4.5),(12.45,28.3,7.3))
    relief=slot_yz((PIN_Y,PIN_Z),(PIN_Y,PIN_Z+PAWL_TRAVEL),.68,10.5,12.6)
    rear=c.one(rear.cut(relief).clean());front=c.one(front.cut(relief).clean())
    top=c.box((10.75,15.7,7.2),(12.45,28.3,7.3))
    guide=c.one(floor.fuse(rear).fuse(front).fuse(top).clean())
    for y0,y1 in ((15.7,16.),(28.,28.3)):
        guide=c.one(guide.fuse(c.box((10.75,y0,.60),(12.45,y1,7.3))).clean())
    material=[]
    for side in 'LR':
        old=c.parent(side+'_PAWL');extension=c.handed(shaft,side)
        overlap=common(old,extension)
        if overlap<=1e-7:raise ValueError('actuating pin does not join native PAWL')
        pawl=c.one(old.fuse(extension).clean())
        if c.vol(old.cut(pawl))>1e-7:raise ValueError('original PAWL was cut')
        this_guide=c.handed(guide,side);joint=common(panel,this_guide)
        if joint<=1e-7:raise ValueError('guide has no material connection to panel')
        panel=c.one(panel.fuse(this_guide).clean())
        opening=c.handed(c.box((8.9,23.1,-.1),(12.55,28.5,.75)),side)
        panel=c.one(panel.cut(opening).clean())
        root=c.parent(side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
        passage=c.handed(slot_yz((PIN_Y,PIN_Z),(PIN_Y,PIN_Z+PAWL_TRAVEL),.45,12.6,13.8),side)
        revised=c.one(root.cut(passage).clean())
        removed=c.vol(root.cut(revised))
        if removed<=1e-7 or c.vol(revised.cut(root))>1e-7:
            raise ValueError('declared pin-passage material accounting failed')
        shapes[side+'_ROOT_OUTER']=revised
        joints.append({'side':side,'outer_root_fixed_pin_passage_removed_mm3':removed})
        shapes[side+'_PAWL']=pawl;shapes[side+'_ORIGINAL_PAWL']=old
        shapes[side+'_TAB']=c.one(c.handed(slider,side));shapes[side+'_GUIDE']=c.one(this_guide)
        shapes[side+'_PIN']=c.one(extension)
        joints.append({'side':side,'pin_to_PAWL_overlap_mm3':overlap,'guide_to_panel_overlap_mm3':joint})
    original=panels['A_BACK_PANEL'];lost=c.vol(original.cut(panel));added=c.vol(panel.cut(original))
    if abs(c.vol(original)-lost+added-c.vol(panel))>1e-7:raise ValueError('panel material accounting differs')
    shapes['A_BACK_PANEL']=panel
    return shapes,{'joints':joints,'panel_material':{'removed_mm3':lost,'added_mm3':added},
                   'original_PAWL_material_removed_mm3':0.,'manual_tabs_independent':True,
                   'no_automatic_return_or_detent_implemented':True,'guide_and_tab_assembly_access_unqualified':True}


def scene(slide,descent=0.,*,left_tab=3.,right_tab=3.):
    # This replaces the inherited parked PAWL, rather than counting it as a driven state.
    parts,pose,detail=c.phone_scene(slide,descent);b,report=build()
    for side,u in (('L',left_tab),('R',right_tab)):
        z=displacement(u)
        parts[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=b[side+'_ROOT_OUTER']
        parts[side+'_PAWL']=b[side+'_PAWL'].translate((0,0,z))
        parts[side+'_TAB']=b[side+'_TAB'].translate((0,u,0))
    parts['A_BACK_PANEL']=b['A_BACK_PANEL']
    return parts,{'slide_mm':slide,'descent_mm':descent,'left_tab_mm':left_tab,'right_tab_mm':right_tab,
                  'PAWL_position_kind':'slot centerline representative, not unique clearance-free output'}


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    out.mkdir(parents=True,exist_ok=False);b,detail=build();exports={}
    for name,body in b.items():
        path=out/(name+'.step');cq.exporters.export(body,str(path));bb=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':c.sha(path),'volume_mm3':c.vol(body),
                       'bounds_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]}
    report={'base_main':BASE,'source_sha256':c.sha(__file__),'exports':exports,'construction':detail,
            'tab_travel_mm':TRAVEL,'nominal_PAWL_travel_mm':PAWL_TRAVEL,'groove_radius_mm':SLOT_RADIUS,
            'pin_radius_mm':PIN_RADIUS,'output_interval_at_released':output_interval(TRAVEL),
            'manual_input_not_automatic_B_release':True,'full_endpoint_lock_load_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=generate(args.output)
    print(json.dumps({'native_exports':len(report['exports']),'released_interval':report['output_interval_at_released']}))
