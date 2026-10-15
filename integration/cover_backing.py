"""One-piece back-panel posts giving the active guide cover an outward stop.

Four fixed rectangular posts join the existing panel with positive material
intersection. No cover, contact tongue, root, pin, screw or manual slot is
cut. Each cover has nominal 0.02 mm take-up before the new panel surface is
reached. This does not certify panel anchorage, stiffness, preload, fatigue,
manufacturing tolerance, or retention in every coupled direction.
"""
from pathlib import Path
import argparse
import json
import math
import cadquery as cq
from verify_pawl_lateral_guide import load_new
from verify_root_clearance import box, hand, single, vol, common, sha

ROOT=Path(__file__).resolve().parents[1]
BASE='21ce4c6bb81b531576d546a945a2708fed8010c5'
POSTS=(('front',(17.43,18.30,.50),(18.43,19.50,7.00)),
       ('rear',(17.43,22.35,.50),(18.43,23.80,7.00)))
TAKEUP_MM=.02


def posts(side):
    if side not in ('L','R'):raise ValueError('explicit side L or R required')
    return {side+'_BACKING_'+name:single(hand(box(lo,hi),side)) for name,lo,hi in POSTS}


def build(base):
    roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL',
           'TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')
    if set(base)!={s+'_'+r for s in 'LR' for r in roles}|{'A_BACK_PANEL'}:
        raise ValueError('complete current 25-template body-guide baseline required')
    original=single(base['A_BACK_PANEL']);panel=original;joins=[]
    for side in 'LR':
        for name,post in posts(side).items():
            overlap=common(post,original)
            if overlap<=1e-7:raise ValueError('backing post is not connected to original panel')
            panel=single(panel.fuse(post).clean())
            joins.append({'post':name,'overlap_with_original_panel_mm3':overlap})
    removed=vol(original.cut(panel));added=vol(panel.cut(original))
    if removed>1e-7 or abs(vol(original)+added-vol(panel))>1e-7:
        raise ValueError('original panel lost material or balance differs')
    result=dict(base);result['A_BACK_PANEL']=panel
    return result,{'only_changed_template':'A_BACK_PANEL','original_panel_removed_mm3':removed,
                   'new_panel_material_mm3':added,'joins':joins,'one_connected_panel_solid':True}


def nominal_lateral_interval(cover_outward_mm):
    if type(cover_outward_mm) not in (int,float) or not math.isfinite(cover_outward_mm):
        raise ValueError('finite real cover shift required')
    if not 0<=cover_outward_mm<=TAKEUP_MM:raise ValueError('cover shift outside nominal take-up domain')
    return {'inboard_mm':-.05,'outboard_mm':.05+cover_outward_mm,
            'original_orientation_and_guiding_overlap_required':True,
            'not_whole_freeplay_or_process_qualification':True}


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('use new external output directory')
    _,old,h=load_new(baseline);new,material=build(old)
    out.mkdir(parents=True,exist_ok=False);exports={}
    for name,body in new.items():
        path=out/(name+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':sha(path),'volume_mm3':vol(body),
            'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(sha(p)!=v for p,v in h.items()):raise ValueError('baseline changed during generation')
    data={'base_main':BASE,'source_sha256':sha(__file__),'baseline_manifest_sha256':sha(baseline),
          'baseline_input_sha256':h,'exports':exports,'material':material,'fixed_posts_R':POSTS,
          'nominal_cover_outward_takeup_mm':TAKEUP_MM,'lateral_interval_at_cover_stop':nominal_lateral_interval(TAKEUP_MM),
          'unchanged_physical_part_count':79,'unchanged_templates':24,
          'panel_is_geometric_anchor_not_certified_ground':True,
          'post_and_panel_stiffness_preload_threads_forces_qualified':False,
          'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(data,indent=2)+'\n');return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=generate(a.baseline,a.output);print(json.dumps({'templates':len(r['exports']),'material':r['material'],'cover_takeup_mm':TAKEUP_MM}))
