"""Endpoint-margin and deeper roof-joint study; not a hardware release.

Only the new manual TAB slot and roof joint pockets/bosses change. The native
PAWL, KEY, pins, root stops, screw sizes and prior thin transmission are not
scaled or trimmed. Slot-only bounds are a subset of a real tolerance budget.
The roof has a longer nominal female-thread region, NOT modeled helical
threads or measured pull-out strength. No automatic return/detent is added.
"""
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass, asdict
import argparse
import json
import math
import serviceable_pawl as s

ROOT=Path(__file__).resolve().parents[1]
BASE='6ac042a14b976e549e27631530e8464ede0bfcc9'


@dataclass(frozen=True)
class Slot:
    input_travel_mm: float=3.0
    output_origin_mm: float=.020
    output_span_mm: float=1.060
    pin_radius_mm: float=.400
    slot_radius_mm: float=.425

    def __post_init__(self):
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in asdict(self).values()):
            raise ValueError('finite real geometry required')
        if self.input_travel_mm<=0 or self.output_span_mm<=0 or self.pin_radius_mm<=0 or self.slot_radius_mm<=self.pin_radius_mm:
            raise ValueError('positive travel and real clearance required')

    @property
    def slope(self):return self.output_span_mm/self.input_travel_mm

    @property
    def halfwidth(self):return (self.slot_radius_mm-self.pin_radius_mm)*math.hypot(1.,self.slope)

    def interval(self,u):
        if type(u) not in (int,float) or not math.isfinite(u) or not 0<=u<=self.input_travel_mm:
            raise ValueError('manual input outside physical travel')
        center=self.output_origin_mm+self.slope*u
        return {'center_mm':center,'lower_mm':center-self.halfwidth,'upper_mm':center+self.halfwidth,
                'scope':'two ideal native slot flanks only, no guide/pin play, process or force budget'}


SLOT=Slot()
BOSS_BOTTOM=5.70
BOSS_RADIUS=.80
POCKET_BOTTOM=5.65
POCKET_RADIUS=.85


@lru_cache(maxsize=1)
def build():
    old,_=s.build();parts=dict(old);changes={};panel=old['A_BACK_PANEL']
    for side in 'LR':
        mirror=lambda b:s.c.one(s.c.handed(b,side))
        # Restore ONLY the original project's slotted plate, then cut the new
        # fixed slot. Original PAWL/KEY/root geometry is never modified here.
        plate=mirror(s.c.box((11.1,16.,4.6),(12.1,25.,7.15)))
        filled=s.c.one(old[side+'_TAB'].fuse(plate).clean())
        z=s.a.PIN_Z+SLOT.output_origin_mm
        tool=mirror(s.a.slot_yz((20.2,z-.2*SLOT.slope),(16.8,z+3.2*SLOT.slope),SLOT.slot_radius_mm,11.,12.2))
        parts[side+'_TAB']=s.c.one(filled.cut(tool).clean())
        roof=old[side+'_ROOF'];guide=old[side+'_GUIDE_REFERENCE']
        x=-s.MOUNT_X if side=='L' else s.MOUNT_X
        for y in s.MOUNT_Y:
            ring=s.c.one(s.c.cylinder(BOSS_RADIUS,BOSS_BOTTOM,6.80,x,y).cut(s.c.cylinder(.5,5.60,7.10,x,y)).clean())
            if s.w.v.common(roof,ring)<=1e-7:raise ValueError('new joint boss detached from roof')
            roof=s.c.one(roof.fuse(ring).clean())
            pocket=s.c.cylinder(POCKET_RADIUS,POCKET_BOTTOM,6.80,x,y)
            panel=s.c.one(panel.cut(pocket).clean());guide=s.c.one(guide.cut(pocket).clean())
        parts[side+'_ROOF']=roof;parts[side+'_GUIDE_REFERENCE']=guide
        for role in ('TAB','ROOF','GUIDE_REFERENCE'):
            changes[side+'_'+role]=s.material(old[side+'_'+role],parts[side+'_'+role])
    parts['A_BACK_PANEL']=panel;changes['A_BACK_PANEL']=s.material(old['A_BACK_PANEL'],panel)
    return parts,{'changed_material':changes,'slot':asdict(SLOT),'nominal_female_region_from_mm':BOSS_BOTTOM,
                  'screw_tip_mm':6.95,'nominal_axial_overlap_mm':6.95-BOSS_BOTTOM,'blind_tip_gap_mm':.05,
                  'radial_boss_pocket_gap_mm':POCKET_RADIUS-BOSS_RADIUS,'original_PAWL_KEY_roots_pins_screws_unchanged':True,
                  'threads_preload_torque_pullout_not_qualified':True}


def scene(slide=0.,descent=0.,left=0.,right=0.,flanks=(0.,0.)):
    if not isinstance(flanks,(tuple,list)) or len(flanks)!=2 or any(x not in (-1,0,1) or type(x) is bool for x in flanks):
        raise ValueError('two explicit slot flank selectors required')
    parts=s.scene(slide,descent,left,right);new,_=build()
    for side,u,flank in zip('LR',(left,right),flanks):
        center=SLOT.interval(u)['center_mm'];z=center+flank*SLOT.halfwidth
        for role in ('PAWL','SHOULDER_PIN_NOMINAL'):
            parts[side+'_'+role]=new[side+'_'+role].translate((0,0,z))
        parts[side+'_TAB']=new[side+'_TAB'].translate((0,u,0))
        parts[side+'_ROOF']=new[side+'_ROOF']
    parts['A_BACK_PANEL']=new['A_BACK_PANEL']
    return parts


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    out.mkdir(parents=True,exist_ok=False);parts,detail=build();exports={}
    for name,body in parts.items():
        path=out/(name+'.step');s.c.cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':s.sha(path),'volume_mm3':s.c.vol(body),
                       'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    report={'base_main':BASE,'source_sha256':s.sha(__file__),'exports':exports,'construction':detail,
            'slot_only_closed_interval_mm':SLOT.interval(0.),'slot_only_open_interval_mm':SLOT.interval(3.),
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    r=generate(p.parse_args().output)
    print(json.dumps({k:r[k] for k in ('slot_only_closed_interval_mm','slot_only_open_interval_mm')}))
