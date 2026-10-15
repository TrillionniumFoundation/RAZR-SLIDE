"""Fixed root clearance channels and connected overpassing support ribs.

This is a new stationary-root research candidate. PAWL, KEY, pins, manual
slot, catalogue screw and roof geometry remain exact. The bounded rigid
relative-error box is a design scenario, NOT measured process capability,
free-guide play, independent feature-size errors or a manufacturing release.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import cadquery as cq
from verify_catalogue_roof_joint import read, vol

BASE='a78a74998c79a6d8b51dca40873160d0187dd95d'
ROOT=Path(__file__).resolve().parents[1]
# Coordinates are right-hand installed coordinates in mm; the left is mirrored.
WINDOWS=(
    ('guide_block',(13.5,18.05,3.50),(16.7,22.25,7.40)),
    ('input_neck',(13.5,16.02,3.94),(14.25,18.25,5.60)),
    ('locking_tongue_corridor',(14.,15.95,4.),(30.07,16.75,5.42)),
    ('socket_corridor',(12.10,19.25,4.57),(13.85,20.75,7.15)),
)
BRIDGE_X=(22.55,27.70)
ERROR_MM=(.03,.05,.02)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def single(shape):
    if len(shape.Solids())!=1 or not shape.isValid() or vol(shape)<=0:
        raise ValueError('one complete connected positive root required')
    return shape


def block(lo,hi):
    if len(lo)!=3 or len(hi)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in (*lo,*hi)) or any(b<=a for a,b in zip(lo,hi)):
        raise ValueError('finite ordered box coordinates required')
    return cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo))


def handed(body,side):
    if side not in ('L','R'):raise ValueError('invalid side')
    return body.mirror('YZ') if side=='L' else body


def bridge_boxes():
    return [block(lo,hi) for x in BRIDGE_X for lo,hi in (
        ((x,15.35,4.95),(x+.4,15.70,5.82)),
        ((x,15.35,5.48),(x+.4,17.60,5.82)),
        ((x,17.15,4.95),(x+.4,17.60,5.82)),
    )]


def modify_root(old,side,*,outer):
    if type(outer) is not bool:raise ValueError('explicit root kind required')
    single(old);result=old
    for _,lo,hi in WINDOWS:result=result.cut(handed(block(lo,hi),side)).clean()
    cut_only=result;disconnected=len(result.Solids())
    if outer:
        for rib in bridge_boxes():result=result.fuse(handed(rib,side)).clean()
    result=single(result)
    # No detached cut fragment is dropped to achieve a single solid.
    retained=vol(cut_only.cut(result))
    if retained>1e-7:raise ValueError('support repair discarded cut fragments')
    loss=vol(old.cut(result));gain=vol(result.cut(old))
    if abs(vol(old)-loss+gain-vol(result))>1e-7:raise ValueError('material balance failure')
    return result,{'old_volume_mm3':vol(old),'removed_mm3':loss,'added_mm3':gain,
                   'new_volume_mm3':vol(result),'cut_only_components':disconnected,
                   'discarded_cut_material_mm3':retained}


def mounted_roots(manifest=None):
    if manifest is None:
        import cam_coupling
        return {s+'_ROOT_INNER':cam_coupling.parent(s+'_ROOT_INNER') for s in 'LR'},{}
    path=Path(manifest).resolve();m=json.loads(path.read_text());h={str(path):sha(path)};parts={}
    for s in 'LR':
        name=s+'_ROOT_INNER';rec=m['exports'][name];rel=Path(rec['path']);f=path.parent/rel
        if rel.parts!=(name+'.step',) or f.is_symlink() or sha(f)!=rec['sha256']:
            raise ValueError('invalid mounted root identity')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra mounted root')
        parts[name]=single(roots[0]);h[str(f)]=sha(f)
    return parts,h


def build(base,inner):
    parts=dict(base);details={}
    for side in 'LR':
        for name,old,is_outer in [(side+'_ROOT_OUTER',base[side+'_ROOT_OUTER'],True),(side+'_ROOT_INNER',inner[side+'_ROOT_INNER'],False)]:
            parts[name],details[name]=modify_root(old,side,outer=is_outer)
    return parts,details


def generate(baseline,output,mount_manifest=None):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    _,base,h=read(baseline);inners,h2=mounted_roots(mount_manifest);h.update(h2)
    parts,detail=build(base,inners);out.mkdir(parents=True,exist_ok=False);exports={}
    for name,body in parts.items():
        path=out/(name+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':sha(path),'volume_mm3':vol(body),
            'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(sha(p)!=v for p,v in h.items()):raise ValueError('input changed while building')
    report={'base_main':BASE,'source_sha256':sha(__file__),'baseline_manifest_sha256':sha(baseline),
        'input_sha256':h,'exports':exports,'material':detail,'fixed_windows_R':WINDOWS,
        'relative_rigid_error_halfwidth_xyz_mm':ERROR_MM,
        'scenario_not_process_capability_or_all_free_play':True,
        'PAWL_KEY_slots_pins_and_catalogue_fasteners_unchanged':True,
        'root_guidance_and_support_geometry_changed':True,'support_strength_and_new_guidance_not_qualified':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--mount-manifest',type=Path)
    a=p.parse_args();r=generate(a.baseline,a.output,a.mount_manifest)
    print(json.dumps({'templates':len(r['exports']),'material':r['material'],'manufacturing_go':False}))
