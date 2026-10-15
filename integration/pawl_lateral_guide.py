"""Connected opposed PAWL lands: a lateral-guidance design, not a load release.

Four finite lands on each original guide block limit pure X translation before
shoulder collars bear on the thin manual slot. A spine connects both otherwise
floating outer lands to the root. No moving part, root fragment or fastener is
cut. The X bound is conditional on unchanged orientation and overlapping lands;
it does not claim all five parasitic freedoms, preload or holding stiffness.
"""
from pathlib import Path
import argparse
import json
import cadquery as cq
import verify_root_clearance as v

ROOT = Path(__file__).resolve().parents[1]
BASE = '63ba045ce388ddb89316a385d6391e7ea7cf2fa0'
LANDS = (
    ('inboard_front', (13.4,18.3,4.5), (13.55,19.0,7.3)),
    ('inboard_rear', (13.4,21.3,4.5), (13.55,22.0,7.3)),
    ('outboard_front', (16.65,18.3,4.5), (16.85,19.0,7.3)),
    ('outboard_rear', (16.65,21.3,4.5), (16.85,22.0,7.3)),
    ('outboard_spine', (16.8,17.8,4.5), (17.0,23.2,7.3)),
)


def additions(side):
    return [(name, v.hand(v.box(lo,hi),side)) for name,lo,hi in LANDS]


def build(base):
    expected = {s+'_'+r for s in 'LR' for r in (
        'ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL',
        'SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL',
        'ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER')} | {'A_BACK_PANEL'}
    if set(base)!=expected:
        raise ValueError('complete frozen root-clearance templates required')
    result=dict(base);receipts={}
    for side in 'LR':
        name=side+'_ROOT_OUTER';old=v.single(base[name]);body=old;joins=[]
        for role,part in additions(side):
            joins.append({'component':role,'overlap_with_original_root_mm3':v.common(part,old)})
            body=body.fuse(part).clean()
        body=v.single(body)
        removed=v.vol(old.cut(body));added=v.vol(body.cut(old))
        if removed>v.TOL or abs(v.vol(old)+added-v.vol(body))>v.TOL:
            raise ValueError('root material lost or inconsistent whole material')
        result[name]=body
        receipts[name]={'original_removed_mm3':removed,'added_mm3':added,
                        'final_connected_solids':len(body.Solids()),'component_joins':joins}
    return result,receipts


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:
        raise ValueError('use a new external output directory')
    _,base,hashes=v.load_new(baseline);parts,receipts=build(base)
    out.mkdir(parents=True,exist_ok=False);exports={}
    for name,body in parts.items():
        path=out/(name+'.step');cq.exporters.export(body,str(path));bb=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':v.sha(path),'volume_mm3':v.vol(body),
            'bounds_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]}
    if any(v.sha(p)!=x for p,x in hashes.items()):
        raise ValueError('baseline changed while generating')
    report={'base_main':BASE,'source_sha256':v.sha(__file__),
        'baseline_manifest_sha256':v.sha(baseline),'baseline_input_sha256':hashes,
        'exports':exports,'material':receipts,'fixed_components_R':LANDS,
        'nominal_pure_X_stop_mm':[-.05,.05],
        'stop_scope':'native orientation held; finite guide lands overlap; no full six-DOF reachable-set claim',
        'intentional_new_bearing_margin_under_prior_error_box_mm':.02,
        'previous_nonbearing_minimum_margin_mm':.05,
        'tradeoff':'new intentional bearing lands reduce X travel and the gap to the existing rigid error envelope',
        'preload_load_stiffness_wear_and_process_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=generate(args.baseline,args.output)
    print(json.dumps({'templates':len(r['exports']),'material':r['material']}))
