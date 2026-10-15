"""Integrate the retained low panel/frame shear-key candidate.

Only A_BACK_PANEL gains two connected rectangular keys. Frame, screws,
control/locking/contact solids stay unchanged. The 0.02 mm panel/frame
clearance is nominal pure translation, not a tolerance or loaded rating.
"""
from pathlib import Path
import argparse
import json
import math
import cadquery as cq
from verify_pawl_lateral_guide import load_new
from verify_root_clearance import box, hand, single, vol, common, sha

ROOT=Path(__file__).resolve().parents[1]
BASE='5f37e90ecfdecd94ec95b5f4e09217a9be452a87'
KEY_RIGHT=((35.70,16.50,.50),(36.325,24.00,2.00))
PANEL_TAKEUP_MM=.02
ROLES=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL',
       'SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL',
       'ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')


def key_material(side):
    if side not in ('L','R'):raise ValueError('explicit L or R side required')
    return single(hand(box(*KEY_RIGHT),side))


def add_keys(original):
    original=single(original);panel=original;joins=[]
    for side in 'LR':
        key=key_material(side);overlap=common(key,original)
        if overlap<=1e-7:raise ValueError('shear key has no native panel connection')
        panel=single(panel.fuse(key).clean())
        joins.append({'side':side,'original_panel_overlap_mm3':overlap})
    loss=vol(original.cut(panel));gain=vol(panel.cut(original))
    if loss>1e-7 or abs(gain-12.65625)>1e-6 or abs(vol(original)+gain-vol(panel))>1e-7:
        raise ValueError('unexpected panel/key material accounting')
    return panel,{'removed_mm3':loss,'added_mm3':gain,'joins':joins,'connected_solids':1}


def build(base):
    if set(base)!={s+'_'+r for s in 'LR' for r in ROLES}|{'A_BACK_PANEL'}:
        raise ValueError('complete 25-template backing baseline required')
    new=dict(base);new['A_BACK_PANEL'],material=add_keys(base['A_BACK_PANEL'])
    return new,material


def original_orientation_offsets(panel_dx,cover_outward):
    """Coordinate bookkeeping only; not an assertion that every combination is reachable."""
    for x in (panel_dx,cover_outward):
        if type(x) not in (int,float) or not math.isfinite(x):raise ValueError('finite real displacement required')
    if abs(panel_dx)>.02 or not 0<=cover_outward<=.02:raise ValueError('outside declared nominal displacement family')
    return {side:{'body_inboard_global_X_mm':panel_dx+sign*(-.05),
                  'body_outboard_global_X_mm':panel_dx+sign*(.05+cover_outward)}
            for side,sign in (('L',-1),('R',1))}


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    _,base,h=load_new(baseline);new,material=build(base)
    out.mkdir(parents=True,exist_ok=False);exports={}
    for key,body in new.items():
        path=out/(key+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[key]={'path':path.name,'sha256':sha(path),'volume_mm3':vol(body),
                      'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(sha(p)!=x for p,x in h.items()):raise ValueError('baseline changed during generation')
    report={'base_main':BASE,'source_sha256':sha(__file__),'baseline_manifest_sha256':sha(baseline),
            'baseline_input_sha256':h,'exports':exports,'material':material,'fixed_key_R':KEY_RIGHT,
            'only_changed_template':'A_BACK_PANEL','unchanged_templates':24,'physical_participants':79,
            'panel_pure_X_takeup_mm':.02,'cover_outward_takeup_relative_panel_mm':.02,
            'coordinate_composition_not_complete_reachable_set':True,
            'frame_screw_axial_retention_preload_stiffness_or_strength_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=generate(a.baseline,a.output);print(json.dumps({'templates':25,'material':r['material'],'panel_takeup_mm':.02}))
