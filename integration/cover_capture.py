"""Integral lateral-entry anti-lift channels on the two bench roots.
No cover or motion part is trimmed. Keeps the existing bench envelope, not a
claim that the 3.5 mm-expanded bench fits finished A/B phone cavities.
"""
from pathlib import Path
from functools import lru_cache
import json,hashlib,tarfile,tempfile
import cam_contact_native as n
from verify_contact_motion import PARTS
ROOT=Path(__file__).resolve().parents[1]
PHASE=ROOT/'engineering/cover-assembly-order-20261014'
ROOT_NAMES=('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
BOXES={ROOT_NAMES[0]:(-3.3,-2.2,-3.3,-3.17),ROOT_NAMES[1]:(3.5,4.4,4.27,4.4)}
FIELDS=('xmin','xmax','ymin','ymax','zmin','zmax')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

@lru_cache(maxsize=1)
def sources():
    manifest=json.loads((PHASE/'geometry-manifest.json').read_text())
    arc=PHASE/'bench-geometry.tar.gz'
    if sha(arc)!=manifest['archive_sha256']:raise ValueError('baseline archive differs')
    return arc,{x['path']:x for x in manifest['files']}

@lru_cache(maxsize=200)
def read_shape(member):
    arc,entries=sources()
    if member not in entries or not member.endswith('.step'):raise ValueError('unknown native STEP')
    with tarfile.open(arc,'r:gz') as t:b=t.extractfile(member).read()
    if len(b)!=entries[member]['bytes'] or hashlib.sha256(b).hexdigest()!=entries[member]['sha256']:raise ValueError('native STEP content differs')
    with tempfile.TemporaryDirectory(prefix='razr-capture-read-') as td:
        p=Path(td)/'part.step';p.write_bytes(b);vals=n.cq.importers.importStep(str(p)).vals()
    if len(vals)!=1:raise ValueError('extra native root')
    return n.single(vals[0])

def baseline(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    return {k:read_shape('cover-first/'+side+'_'+k+'.step') for k in PARTS}

@lru_cache(maxsize=4)
def channel(side,name):
    if side not in ('L','R') or name not in BOXES:raise ValueError('invalid side or root')
    ea,eb,pa,pb=BOXES[name]
    return n.fuse([n.box(side,ea,eb,6.5,7.,-6.42,-6.22),
                   n.box(side,pa,pb,6.5,7.,-7.64,-6.22),
                   n.box(side,ea,eb,6.5,7.,-7.64,-7.26)])

@lru_cache(maxsize=2)
def build(side):
    old=baseline(side);new=dict(old);reports=[]
    for name in ROOT_NAMES:
        keep=channel(side,name);joint=n.common(old[name],keep)
        if joint<=1e-7:raise ValueError('floating retainer, not attached to root')
        target=n.single(old[name].fuse(keep).clean())
        lost=n.whole_material(old[name].cut(target),empty=True)[1]
        extra=n.whole_material(target.cut(old[name]),empty=True)[1]
        if lost>1e-7 or n.whole_material(target.cut(old[name]).cut(keep),empty=True)[1]>1e-7:raise ValueError('unaccounted material')
        bb,nb=old[name].BoundingBox(),target.BoundingBox()
        delta={k:getattr(nb,k)-getattr(bb,k) for k in FIELDS}
        if any(abs(x)>1e-7 for x in delta.values()):raise ValueError('root bounding envelope grew')
        new[name]=target
        reports.append({'root':name,'old_volume_mm3':old[name].Volume(),'new_volume_mm3':target.Volume(),
                        'added_mm3':extra,'old_material_removed_mm3':lost,'joint_overlap_mm3':joint,'bounds_delta_mm':delta})
    return old,new,reports

def components(side,name):
    old=baseline(side)
    if name in ROOT_NAMES:return [old[name],channel(side,name)]
    return [read_shape('cover-first/'+side+'_'+name+'.step')]

def positive_uplift(side,distance_mm,enabled=True):
    if type(enabled) is not bool or not isinstance(distance_mm,(float,int)) or isinstance(distance_mm,bool) or not 0<=distance_mm<=1:raise ValueError('invalid trial')
    old,new,_=build(side);parts=new if enabled else old;moving=parts['OLD_COVER'].translate((0,0,distance_mm))
    return {name:n.common(moving,parts[name]) for name in ROOT_NAMES}


def export_candidate(out):
    out=Path(out).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output directory required')
    out.mkdir(parents=True,exist_ok=False);exports={};material=[]
    for side in 'LR':
        old,new,reports=build(side);material.extend([{'side':side,**r} for r in reports])
        for name in ROOT_NAMES:
            for suffix,body in [('',new[name]),('_CHANNEL',channel(side,name))]:
                role=side+'_'+name+suffix;f=out/(role+'.step');n.cq.exporters.export(body,str(f))
                b=body.BoundingBox();exports[role]={'path':f.name,'sha256':sha(f),'volume_mm3':body.Volume(),'bounds_mm':{k:getattr(b,k) for k in FIELDS}}
    result={'base_commit':'8f4a7edd01e8db77105d28ab30d3b679c3e6835e','source_sha256':sha(__file__),
            'archive_sha256':sha(sources()[0]),'exports':exports,'material':material,
            'integral_channels_not_loose_clips':True,'nominal_upper_gap_mm':.02,'nominal_wall_mm':.13,
            'root_envelope_and_prior_3p5mm_bench_growth_unchanged':True,
            'rigid_straight_uplift_only_not_6DOF_capture':True,'strength_and_process_tolerance_unknown':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
    export_candidate(a.output);print('EXPORTED: four joined roots and four channel proofs; no hardware qualification')
