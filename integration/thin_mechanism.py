"""Fixed 6.6-mm-depth STOW research mechanism, not a scaled or qualified phone.

Preserves the KEY, PAWL, contact-pin/core geometry and nominal screw sizes.
Moves the two spring stations in the q/r plane, redraws their seats/supports,
and replaces the wide outer stock and cover edge. All modifications are
project-owned study geometry. No OEM material, original STEP or old failure
is edited. Force, tolerances, PCB/OLED and phone kinematic integration remain
unknown. A study-cavity placement is not a measured product registration.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import tarfile
import tempfile

import cam_contact_native as n
from verify_contact_motion import PARTS
from translation_regions import regions, checks

ROOT=Path(__file__).resolve().parents[1]
BASE_COMMIT='69170884da4fdf1f3563171a967ea7bb043fcc85'
ROOT_NAMES=('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
BINDINGS={
    'bench':('engineering/cover-assembly-order-20261014','bench-geometry.tar.gz'),
    'capture':('engineering/cover-retention-and-space-20261015','capture-geometry.tar.gz'),
}
STATIONS=((16.5,19.0),(10.5,22.0))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_side(side):
    if side not in ('L','R'):
        raise ValueError('invalid side')


@lru_cache(maxsize=200)
def native_input(group,member):
    if group not in BINDINGS:
        raise ValueError('unknown native source')
    folder,archive=BINDINGS[group];folder=ROOT/folder
    manifest=json.loads((folder/'geometry-manifest.json').read_text())
    archive=folder/archive
    if sha(archive)!=manifest['archive_sha256']:
        raise ValueError('native source archive changed')
    matches=[x for x in manifest['files'] if x['path']==member]
    if len(matches)!=1 or not member.endswith('.step'):
        raise ValueError('missing or ambiguous STEP member')
    entry=matches[0]
    with tarfile.open(archive,'r:gz') as stream:
        data=stream.extractfile(member).read()
    if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
        raise ValueError('native STEP member changed')
    with tempfile.TemporaryDirectory(prefix='thin-native-') as td:
        f=Path(td)/'native.step';f.write_bytes(data)
        roots=n.cq.importers.importStep(str(f)).vals()
    if len(roots)!=1:
        raise ValueError('extra native root')
    return n.single(roots[0])


def original(side):
    require_side(side)
    return {name:native_input('capture','candidate/'+side+'_'+name+'.step') if name in ROOT_NAMES
            else native_input('bench','cover-first/'+side+'_'+name+'.step') for name in sorted(PARTS)}


def box(side,*bounds):
    return n.box(side,*bounds)


def cylinder(side,radius,length,e,q,r):
    return n.single(n.cq.Solid.makeCylinder(radius,length,n.world(side,e,q,r),n.cq.Vector(0,0,1)))


def cropped(side,body,low,high):
    # Declared fixed stock planes, never a shape cut by the current pose.
    return body.intersect(box(side,low,high,-40,40,-40,40)).clean()


def material_delta(old,new):
    lost=n.whole_material(old.cut(new),empty=True)[1]
    added=n.whole_material(new.cut(old),empty=True)[1]
    if abs(old.Volume()-lost+added-new.Volume())>1e-7:
        raise ValueError('whole material balance changed')
    return {'old_mm3':old.Volume(),'removed_mm3':lost,'added_mm3':added,'new_mm3':new.Volume()}


@lru_cache(maxsize=2)
def design(side):
    require_side(side);old=original(side);new=dict(old);joins=[]
    for name in ROOT_NAMES:
        stock=native_input('bench','cover-first/'+side+'_'+name+'.step')
        new[name]=cropped(side,stock,-3.5,3.1)
        n.single(new[name])
    for i in (0,1):
        new['CAP_'+str(i)]=n.single(cropped(side,old['CAP_'+str(i)],-3.5,3.1))
    new['OLD_COVER']=n.single(cropped(side,old['OLD_COVER'],-3.5,2.77))
    for i,(qc,sc) in enumerate(STATIONS):
        off=5*i;ec=2.2
        seat=n.fuse([box(side,.25,2.5,1.26,1.38,2.64+off,2.94+off),
                     box(side,2.2,2.5,1.3,qc+.15,2.64+off,2.94+off),
                     cylinder(side,.55,.3,ec,qc,2.64+off)])
        core=cropped(side,old['STOP_'+str(i)],-1.,.4)
        new['STOP_'+str(i)]=n.fuse([core,seat])
        guide=cylinder(side,.8,3.,ec,qc,1.4+off).cut(cylinder(side,.6,3.1,ec,qc,1.35+off))
        guide=guide.cut(box(side,ec-.31,ec+.31,qc-1.,qc,1.35+off,3.21+off)).clean()
        new['SPRING_GUIDE_'+str(i)]=n.single(guide)
        new[f'SPRING_{i}_OD_TOL_ENVELOPE']=cylinder(side,.43,1.46,ec,qc,2.94+off)
        cap=box(side,1.3,3.1,qc-.8,sc+.9,4.4+off,4.7+off)
        new['SPRING_CAP_'+str(i)]=n.single(cap.cut(cylinder(side,.55,.7,ec,sc,4.3+off)).clean())
        new[f'SPRING_SCREW_{i}_M1x3_NOMINAL']=n.fuse([
            cylinder(side,.5,3.,ec,sc,1.7+off),cylinder(side,.9,.45,ec,sc,4.7+off)])
        post=box(side,1.7,2.7,sc-.5,sc+.5,-11.06,4.4+off)
        post=post.cut(cylinder(side,.5,3.,ec,sc,1.7+off)).clean()
        tie=box(side,.7,3.05,2.98,sc+.5,-11.06,-10.76)
        support=box(side,2.8,3.05,qc-.8,qc+.8,-11.06,1.4+off)
        bed=box(side,1.3,3.1,qc-.8,qc+.8,1.1+off,1.4+off)
        new[ROOT_NAMES[1]]=n.fuse([new[ROOT_NAMES[1]],post,tie,support,bed])
    # Move only the lower cap screws into a separate q lane: their old axial
    # insertion path crosses the upper cap bosses. Nominal screw bodies are
    # rigidly translated, not resized. Original unused bores remain explicit.
    bridge=box(side,-3.3,-2.,-7.4,-1.4,-1.,-.8)
    bosses=[cylinder(side,.7,4.02,-2.6,q,-1.) for q in (-4.5,-6.7)]
    new[ROOT_NAMES[0]]=n.fuse([new[ROOT_NAMES[0]],bridge,*bosses])
    cap=n.fuse([new['CAP_0'],box(side,-3.5,-1.6,-7.7,2.2,3.02,3.32)])
    for j,(old_q,new_q) in enumerate(zip((-1.15,1.2),(-4.5,-6.7))):
        new[ROOT_NAMES[0]]=n.single(new[ROOT_NAMES[0]].cut(cylinder(side,.5,2.7,-2.6,new_q,1.)).clean())
        cap=n.single(cap.cut(cylinder(side,.55,.7,-2.6,new_q,2.9)).clean())
        new['SCREW_0_'+str(j)]=old['SCREW_0_'+str(j)].translate((0,old_q-new_q,0))
    new['CAP_0']=cap
    # Fixed, declared upper-seat admission relief, independent of run pose.
    # The outer q-spine remains joined by the new bottom web.
    relief=box(side,.04,2.77,1.24,17.07,2.62,2.96)
    opened=new[ROOT_NAMES[1]].cut(relief).clean()
    # Fixed side bypass reconnects every retained spine fragment above the slot.
    bypass=[box(side,2.8,3.05,3.,3.2,-.98,3.3),
            box(side,.7,3.05,3.,3.2,3.1,3.3),
            box(side,.7,3.05,3.,3.2,-.98,-.82)]
    new[ROOT_NAMES[1]]=n.fuse([opened,*bypass])
    for name,(ea,eb,pa,pb) in {ROOT_NAMES[0]:(-3.5,-2.2,-3.5,-3.25),
                              ROOT_NAMES[1]:(2.2,3.1,2.87,3.1)}.items():
        pieces=[box(side,ea,eb,6.5,7.,-6.34,-6.04),
                box(side,pa,pb,6.5,7.,-7.64,-6.04),
                box(side,ea,eb,6.5,7.,-7.64,-7.26)]
        if name==ROOT_NAMES[1]:
            # Shift the right capture support beyond the pawl's full q range.
            pieces=[box(side,2.2,3.1,8.,8.5,-2.4,-2.1),
                    box(side,2.87,3.1,8.,8.5,-11.06,-2.1),
                    box(side,2.2,3.1,8.,8.5,-3.3,-2.92)]
        channel=n.fuse(pieces);overlap=n.common(new[name],channel)
        if overlap<=1e-7:
            raise ValueError('floating retention channel')
        new[name]=n.fuse([new[name],channel])
        joins.append({'root':name,'positive_channel_joint_mm3':overlap})
    changes={}
    for name in sorted(PARTS):
        n.single(new[name])
        if not new[name].isSame(old[name]):changes[name]=material_delta(old[name],new[name])
    return old,new,{'changes':changes,'channel_joins':joins,'no_uniform_or_anisotropic_scaling':True,
                    'nominal_retention_top_gap_mm':.10,'nominal_retention_post_widths_mm':[.25,.23],
                    'spring_force_and_changed_stop_arm_stiffness_qualified':False,
                    'screw_edge_distance_threads_and_preload_qualified':False}


def scene(side,*,enabled=True):
    require_side(side)
    if type(enabled) is not bool:
        raise ValueError('enabled must be boolean')
    old,new,report=design(side)
    return dict(new if enabled else old)


def parked(side,pawl):
    require_side(side)
    return pawl.translate((-1.1 if side=='L' else 1.1,0,0))


def placed(body,side):
    """One proposed whole-component rigid placement in the empty A study cavity.
    KEY withdrawal is aligned with +Y. Not a selected OEM/B-module interface.
    """
    require_side(side)
    rotated=body.rotate((0,0,0),(0,1,0),90 if side=='L' else -90)
    rotated=rotated.rotate((0,0,0),(0,0,1),180)
    return rotated.translate((-13.85 if side=='L' else 13.85,10.,-30.55))


def certificate(body):
    b=body.BoundingBox()
    return {'volume_mm3':n.whole_material(body)[1],
            'bounds_xyz_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:
        raise ValueError('new external output directory required')
    out.mkdir(parents=True,exist_ok=False);exports={};sides={}
    for side in 'LR':
        old,new,report=design(side);report['static_bounds_eqr_mm']=n.bounds(side,n.cq.Compound.makeCompound(list(new.values())))
        sides[side]=report
        for state,parts in [('old',old),('candidate',new)]:
            for name,body in sorted(parts.items()):
                role=side+'_'+state+'_'+name;f=out/(role+'.step');n.cq.exporters.export(body,str(f))
                exports[role]={'path':f.name,'sha256':sha(f),**certificate(body)}
        for state,parts in [('candidate',new),('old',old)]:
            whole=n.cq.Compound.makeCompound([placed(s,side) for s in parts.values()])
            f=out/(side+'_'+state+'_PLACED_ASSEMBLY.step');n.cq.exporters.export(whole,str(f))
            exports[side+'_'+state+'_PLACED_ASSEMBLY']={'path':f.name,'sha256':sha(f),**certificate(whole),'expected_solids':23}
    report={'base_commit':BASE_COMMIT,'source_sha256':sha(__file__),'parts_per_side':23,
            'native_source_bindings':{k:{'folder':v[0],'archive':v[1],
                'sha256':sha(ROOT/v[0]/v[1])} for k,v in BINDINGS.items()},
            'exports':exports,'sides':sides,'same_23_roles_not_dropped_parts':True,
            'nominal_width_target_mm':6.6,'study_cavity_depth_mm':6.7,
            'placement_kind':'proposed rigid study placement in A, not product kinematic registration',
            'placement_input':'engineering/phone-layout-study-20261015/native/stepped_A_cavity.step',
            'actual_phone_fit':'unknown','candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=generate(a.output);print(json.dumps({'native_exports':len(r['exports']),'parts_per_side':r['parts_per_side'],'actual_phone_fit':r['actual_phone_fit']}))
