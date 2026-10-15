"""Balanced PAWL lands reusing the existing outboard cover as a guide.

V1's added outboard spine collided with the actual OLD_COVER, which already
limited outward motion. V2 removes that proposal, adds only two inboard lands,
and recesses a fixed 0.04mm-deep region of the cover to form the opposite face.
The moving PAWL, slot, pins and screws stay exact. No load/preload qualification.
"""
from pathlib import Path
import argparse
import json
import cadquery as cq
import verify_root_clearance as v

ROOT=Path(__file__).resolve().parents[1]
BASE='63ba045ce388ddb89316a385d6391e7ea7cf2fa0'
LANDS=(('inboard_front',(13.4,18.3,4.5),(13.55,19.,7.3)),
       ('inboard_rear',(13.4,21.3,4.5),(13.55,22.,7.3)))
COVER_CUT=((16.5,18.05,3.5),(16.65,22.25,7.4))


def additions(side):
    return [(name,v.hand(v.box(lo,hi),side)) for name,lo,hi in LANDS]


def load_covers(manifest=None):
    if manifest is None:
        import cam_coupling
        return {s+'_OLD_COVER':cam_coupling.parent(s+'_OLD_COVER') for s in 'LR'},{}
    path=Path(manifest).resolve();data=json.loads(path.read_text());parts={};h={str(path):v.sha(path)}
    for side in 'LR':
        key=side+'_OLD_COVER';rec=data['exports'][key];rel=Path(rec['path']);f=path.parent/rel
        if rel.parts!=(key+'.step',) or f.is_symlink() or v.sha(f)!=rec['sha256']:
            raise ValueError('existing cover identity differs')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra cover root')
        parts[key]=v.single(roots[0]);h[str(f)]=v.sha(f)
    return parts,h


def build(base,covers):
    roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL',
           'SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL',
           'ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER')
    if set(base)!={s+'_'+r for s in 'LR' for r in roles}|{'A_BACK_PANEL'}:
        raise ValueError('complete frozen root-clearance templates required')
    if set(covers)!={'L_OLD_COVER','R_OLD_COVER'}:
        raise ValueError('both actual existing covers are required')
    result=dict(base);receipts={}
    for side in 'LR':
        key=side+'_ROOT_OUTER';old=v.single(base[key]);body=old
        for _,part in additions(side):
            if v.common(part,old)<=v.TOL:raise ValueError('inboard land detached from root')
            body=body.fuse(part).clean()
        body=v.single(body);loss=v.vol(old.cut(body));gain=v.vol(body.cut(old))
        if loss>v.TOL or abs(v.vol(old)+gain-v.vol(body))>v.TOL:raise ValueError('root material lost')
        result[key]=body;receipts[key]={'removed_mm3':loss,'added_mm3':gain,'connected_solids':1}
        key=side+'_OLD_COVER';old=v.single(covers[key]);body=v.single(old.cut(v.hand(v.box(*COVER_CUT),side)).clean())
        loss=v.vol(old.cut(body));gain=v.vol(body.cut(old))
        if gain>v.TOL or abs(v.vol(old)-loss-v.vol(body))>v.TOL:raise ValueError('cover material accounting differs')
        result[key]=body;receipts[key]={'removed_mm3':loss,'added_mm3':gain,'connected_solids':1}
    return result,receipts


def generate(baseline,output,mount_manifest=None):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('use a new external output directory')
    _,base,h=v.load_new(baseline);covers,h2=load_covers(mount_manifest);h.update(h2)
    parts,receipts=build(base,covers);out.mkdir(parents=True,exist_ok=False);exports={}
    for key,body in parts.items():
        path=out/(key+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[key]={'path':path.name,'sha256':v.sha(path),'volume_mm3':v.vol(body),
            'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(v.sha(p)!=x for p,x in h.items()):raise ValueError('baseline changed')
    r={'base_main':BASE,'source_sha256':v.sha(__file__),'baseline_manifest_sha256':v.sha(baseline),
       'baseline_input_sha256':h,'exports':exports,'material':receipts,
       'fixed_inboard_lands_R':LANDS,'fixed_cover_cut_R':COVER_CUT,
       'existing_cover_is_active_part_not_discarded':True,'V1_outboard_spine_rejected':True,
       'nominal_pure_X_contact_mm':[-.05,.05],
       'stop_scope':'original orientation and finite guide-face overlap; not all coupled degrees of freedom',
       'prior_root_error_envelope_new_minimum_gap_mm':.02,
       'prior_root_error_envelope_previous_minimum_gap_mm':.05,
       'tradeoff':'defined inboard stop consumes root clearance; cover outward clearance increases from .01 to .05mm',
       'load_preload_stiffness_wear_process_qualified':False,
       'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--mount-manifest',type=Path)
    a=p.parse_args();r=generate(a.baseline,a.output,a.mount_manifest)
    print(json.dumps({'templates':len(r['exports']),'material':r['material']}))
