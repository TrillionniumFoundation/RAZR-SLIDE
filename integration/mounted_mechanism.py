"""Mount the fixed thin cartridges on a removable project-owned A back panel.

New ears, blind nominal tap bores, back-panel pads and four frame bosses are
research geometry, not vendor fasteners or qualified joints. Existing KEY,
PAWL, STOP, contact cores and other parts are not resized. Threads, preload,
strength, seal, actual components and the B-to-KEY transmission are NOT modeled.
The full B motion check is shell clearance, explicitly NOT coupled actuation.
"""
from pathlib import Path
from functools import lru_cache
import argparse
import hashlib
import json
import math
import tarfile
import tempfile
import cadquery as cq
import cam_contact_native as n
from verify_contact_motion import PARTS
from verify_thin_mechanism import placement

ROOT=Path(__file__).resolve().parents[1]
BASE='287d37d035cf2497b69bfe6af0866b4531274e71'
SOURCE=ROOT/'engineering/thin-mechanism-20261015'
LAYOUT=ROOT/'engineering/phone-layout-study-20261015/native'
SHIFT_Y=6.0
ROOT_ROLE='ROOT_INNER'
EAR_R=(-9.,0.)
FRAME_POINTS=((-34.8,50.),(34.8,50.),(-34.8,70.),(34.8,70.))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def volume(body): return n.whole_material(body,empty=True)[1]


def one(body): return n.single(body)


def block(x0,x1,y0,y1,z0,z1):
    if any(not math.isfinite(v) for v in (x0,x1,y0,y1,z0,z1)) or min(x1-x0,y1-y0,z1-z0)<=0:
        raise ValueError('invalid block')
    return one(cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,cq.Vector(x0,y0,z0)))


def cyl(radius,z0,z1,x,y):
    if radius<=0 or z1<=z0:raise ValueError('invalid cylinder')
    return one(cq.Solid.makeCylinder(radius,z1-z0,cq.Vector(x,y,z0),cq.Vector(0,0,1)))


def mounted(body,side):
    if side not in ('L','R'):raise ValueError('invalid side')
    return placement(body,side).translate((0,SHIFT_Y,0))


def ear_point(side,index):
    if side not in ('L','R') or type(index) is not int or index not in (0,1):raise ValueError('invalid ear')
    return ((-23.85-EAR_R[index]) if side=='L' else (23.85+EAR_R[index]),4.8)


@lru_cache(maxsize=1)
def source_entries():
    gm=json.loads((SOURCE/'geometry-manifest.json').read_text());arc=SOURCE/gm['archive']
    if sha(arc)!=gm['archive_sha256']:raise ValueError('parent native archive changed')
    return arc,{x['path']:x for x in gm['files']}


@lru_cache(maxsize=46)
def parent_part(side,name):
    if side not in ('L','R') or name not in PARTS:raise ValueError('unknown source part')
    arc,entries=source_entries();member=f'{side}_candidate_{name}.step'
    with tarfile.open(arc,'r:gz') as t:data=t.extractfile(member).read()
    entry=entries[member]
    if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('parent STEP differs')
    with tempfile.TemporaryDirectory(prefix='mount-source-') as td:
        path=Path(td)/'part.step';path.write_bytes(data);vals=cq.importers.importStep(str(path)).vals()
    if len(vals)!=1:raise ValueError('extra source root')
    return one(vals[0])


def layout(name):
    report=json.loads((LAYOUT/'report.json').read_text());rec=report['exports'][name];path=LAYOUT/rec['path']
    if sha(path)!=rec['sha256']:raise ValueError('shell input differs')
    vals=cq.importers.importStep(str(path)).vals()
    if len(vals)!=1:raise ValueError('extra shell root')
    return one(vals[0])


def nominal_m1x3(x,y):
    # Same nominal shank/head envelope as the preserved spring screws, head on -Z.
    return one(cyl(.5,.55,3.55,x,y).fuse(cyl(.9,.10,.55,x,y)).clean())


@lru_cache(maxsize=1)
def build():
    refs={f'{s}_{k}':mounted(parent_part(s,k),s) for s in 'LR' for k in sorted(PARTS)}
    parts=dict(refs);ear_reports=[]
    for side in 'LR':
        root=refs[side+'_'+ROOT_ROLE];adds=[]
        for i,rr in enumerate(EAR_R):
            qend=2. if i==0 else -2.
            tab=mounted(n.box(side,-3.,-2.2,-10.,qend,rr-.6,rr+.6),side)
            x,y=ear_point(side,i)
            ear=one(cyl(1.8,1.2,4.2,x,y).fuse(tab).clean())
            # Exact nominal shank clearance, not a represented helical thread.
            ear=one(ear.cut(cyl(.5,1.1,3.60,x,y)).clean())
            overlap=n.common(root,ear)
            if overlap<=1e-7:raise ValueError('ear is not attached to source root')
            adds.append(ear)
            ear_reports.append({'side':side,'index':i,'center_xy_mm':[x,y],
                                'native_joint_overlap_mm3':overlap,'blind_tip_clearance_mm':.05})
        joined=root
        for ear in adds:joined=one(joined.fuse(ear).clean())
        if volume(root.cut(joined))>1e-7:raise ValueError('source root material removed')
        parts[side+'_'+ROOT_ROLE]=joined
    shell=layout('stepped_A_shell');outer=layout('stepped_A_outer');cavity=layout('stepped_A_cavity')
    original_panel=one(shell.intersect(block(-40,40,-1,96,0,.65)).clean())
    frame=one(shell.cut(original_panel).clean());panel=original_panel
    ears=[ear_point(s,i) for s in 'LR' for i in (0,1)]
    mounts=[('CARTRIDGE_'+str(i),xy) for i,xy in enumerate(ears)]+[('FRAME_'+str(i),xy) for i,xy in enumerate(FRAME_POINTS)]
    frame_overlaps=[]
    for i,(x,y) in enumerate(FRAME_POINTS):
        boss=one(cyl(1.8,1.2,4.2,x,y).cut(cyl(.5,1.1,3.60,x,y)).clean())
        overlap=n.common(frame,boss)
        if overlap<=1e-7:raise ValueError('frame boss disconnected')
        frame_overlaps.append(overlap);frame=one(frame.fuse(boss).clean())
        # Fixed recess for the back-panel pad, including 0.05 mm radial study clearance.
        frame=one(frame.cut(cyl(1.85,.60,1.20,x,y)).clean())
    screws={}
    for name,(x,y) in mounts:
        panel=one(panel.fuse(cyl(1.8,.60,1.2,x,y)).clean())
        panel=one(panel.cut(cyl(.55,-.1,1.3,x,y)).clean())
        panel=one(panel.cut(cyl(.95,-.1,.55,x,y)).clean())
        screws[name+'_M1x3_NOMINAL']=nominal_m1x3(x,y)
    results={'ears':ear_reports,'frame_boss_joint_overlaps_mm3':frame_overlaps,
             'mechanism_parts':46,'new_fasteners':8,'mounts_xy':{name:xy for name,xy in mounts},
             'root_new_material_mm3':{s:volume(parts[s+'_'+ROOT_ROLE].cut(refs[s+'_'+ROOT_ROLE])) for s in 'LR'},
             'original_A_shell':shell,'original_A_outer':outer,'original_A_cavity':cavity,
             'unchanged_B_shell':layout('stepped_B_shell'),'B_outer':layout('stepped_B_outer')}
    return refs,parts,frame,panel,screws,results


def direct_coupling_residual(slide_mm,normal_descent_mm,key_withdrawal_mm):
    vals=(slide_mm,normal_descent_mm,key_withdrawal_mm)
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vals):raise ValueError('nonfinite travel')
    if not 0<=slide_mm<=79.75 or not 0<=normal_descent_mm<=8.2 or not 0<=key_withdrawal_mm<=12:
        raise ValueError('outside current movement domains')
    if normal_descent_mm>0 and slide_mm!=79.75:raise ValueError('normal phase cannot precede full slide')
    # A rigid connection fixes B-to-KEY relative pose. KEY stays in its guide Z.
    return {'relative_Y_drift_mm':slide_mm-key_withdrawal_mm,'relative_Z_drift_mm':-normal_descent_mm,
            'direct_rigid_connection_compatible':abs(slide_mm-key_withdrawal_mm)<=1e-9 and normal_descent_mm<=1e-9}


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output path required')
    out.mkdir(parents=True,exist_ok=False)
    refs,parts,frame,panel,screws,detail=build();exports={}
    def export(role,body):
        p=out/(role+'.step');cq.exporters.export(body,str(p));bb=body.BoundingBox()
        leaves,vol=n.whole_material(body)
        exports[role]={'path':p.name,'sha256':sha(p),'solid_count':len(leaves),'volume_mm3':vol,
                       'bounds_xyz_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]}
    for role,body in parts.items():export(role,body)
    for s in 'LR':export(s+'_PARENT_ROOT_INNER',refs[s+'_ROOT_INNER'])
    for role,body in screws.items():export(role,body)
    for role,body in [('A_FRAME',frame),('A_BACK_PANEL',panel),('A_PARENT_SHELL',detail['original_A_shell']),
                      ('A_OUTER',detail['original_A_outer']),('A_PARENT_CAVITY',detail['original_A_cavity']),
                      ('B_SHELL',detail['unchanged_B_shell']),('B_OUTER',detail['B_outer'])]:export(role,body)
    complete=cq.Compound.makeCompound([frame,panel,*parts.values(),*screws.values()]);export('A_COMPLETE_MOUNTED',complete)
    report={'base_main':BASE,'source_sha256':sha(__file__),'parent_native_archive_sha256':sha(source_entries()[0]),
            'exports':exports,'parts_unchanged_except_two_ROOT_INNER':True,'whole_cartridge_translation_Y_mm':SHIFT_Y,
            'ears':detail['ears'],'frame_boss_joint_overlaps_mm3':detail['frame_boss_joint_overlaps_mm3'],
            'mounts_xy':detail['mounts_xy'],'source_root_material_removed_mm3':0.,
            'root_new_material_mm3':detail['root_new_material_mm3'],
            'motion_scope':'mounted A assembly versus complete B shell through sequential 79.75mm slide/8.2mm seating; not B-to-KEY actuation',
            'direct_rigid_coupling_rejected':direct_coupling_residual(79.75,8.2,12.),
            'complete_coupling_implemented':False,'thread_preload_force_tolerance_and_seal_qualified':False,
            'actual_components_installed':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=generate(a.output);print(json.dumps({'exports':len(r['exports']),'direct_coupling':r['direct_rigid_coupling_rejected'],'manufacturing_go':False}))
