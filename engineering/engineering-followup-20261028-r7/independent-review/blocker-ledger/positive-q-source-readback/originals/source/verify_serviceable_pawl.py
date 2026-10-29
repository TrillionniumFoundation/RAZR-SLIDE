"""Builder-free verification of detachable manual controls on a bare back panel.

Checks complete native participants, insertion order, finite tool shafts,
nominal control motion and retained clearance limitations. Same CAD kernel.
Thread envelopes do not certify torque/holding; reverse assembly reuses the
same swept sets, not a load/friction simulation. Frame and B are absent during
control assembly. Prior cartridge construction still needs temporary holding.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import itertools
import json
import math
import sys
import tarfile
import tempfile
import cadquery as cq
import verify_pawl_actuator as w
from translation_regions import regions,checks,sum_common_upper_bound

ROOT=Path(__file__).resolve().parents[1]
TOL=1e-7
ROLES=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER')
INSERT_ROLES=('TAB','SHOULDER_PIN_NOMINAL','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def vol(shape):return w.v.vol(shape)
def common(a,b):return w.v.common(a,b)


def box(lo,hi):
    return w.v.n.single(cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo)))


def load(manifest):
    path=Path(manifest).resolve();r=json.loads(path.read_text());p={};h={str(path):sha(path)}
    expected={s+'_'+k for s in 'LR' for k in ROLES}|{'A_BACK_PANEL'}
    if set(r['exports'])!=expected:raise ValueError('missing or extra serviceable participant')
    for role,rec in r['exports'].items():
        name=Path(rec['path']);f=path.parent/name
        if name.is_absolute() or len(name.parts)!=1 or name.name!=role+'.step' or f.is_symlink():raise ValueError('invalid STEP path')
        if sha(f)!=rec['sha256']:raise ValueError('native bytes changed')
        values=[rec['volume_mm3'],*rec['bounds_mm']]
        if len(values)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('invalid finite certificate')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra native root')
        b=w.v.n.single(roots[0]);bb=b.BoundingBox();actual=[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]
        if abs(vol(b)-values[0])>TOL or any(abs(a-b)>TOL for a,b in zip(actual,values[1:])):raise ValueError('native shape certificate differs')
        p[role]=b;h[str(f)]=sha(f)
    return r,p,h


def parent_native(h, *, verified_mounted_members=None):
    folder=ROOT/'engineering/pawl-actuation-20261015';gm=folder/'geometry-manifest.json';g=json.loads(gm.read_text());arc=folder/g['archive']
    if sha(arc)!=g['archive_sha256']:raise ValueError('parent native archive differs')
    h[str(gm)]=sha(gm);h[str(arc)]=sha(arc);mp=folder/'NATIVE_MANIFEST.json';h[str(mp)]=sha(mp)
    with tempfile.TemporaryDirectory(prefix='serviceable-independent-') as td,tarfile.open(arc,'r:gz') as stream:
        d=Path(td)
        for rec in g['files']:
            name=Path(rec['path'])
            if name.is_absolute() or len(name.parts)!=1:raise ValueError('unsafe parent member')
            raw=stream.extractfile(str(name)).read()
            if len(raw)!=rec['bytes'] or hashlib.sha256(raw).hexdigest()!=rec['sha256']:raise ValueError('parent member differs')
            (d/name).write_bytes(raw)
        (d/'manifest.json').write_bytes(mp.read_bytes());_,parent,_=w.load_new(d/'manifest.json')
    prior,old,profiles=w.prior_native(h, verified_mounted_members=verified_mounted_members)
    return parent,prior,old,profiles


def scene(new,parent,prior,old,profiles,s,d,tabs):
    parts=w.scene(parent,prior,old,profiles,s,d,tabs)
    for side,u in zip('LR',tabs):
        z=1.1*u/3.;parts[side+'_PAWL']=new[side+'_PAWL'].translate((0,0,z))
        parts[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
        for role in ('TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL'):parts[side+'_'+role]=new[side+'_'+role].translate((0,u,0))
        parts[side+'_SHOULDER_PIN_NOMINAL']=new[side+'_SHOULDER_PIN_NOMINAL'].translate((0,0,z))
        for role in ('ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL'):parts[side+'_'+role]=new[side+'_'+role]
    parts['A_BACK_PANEL']=new['A_BACK_PANEL']
    if len(parts)!=79:raise ValueError('incomplete scene participants')
    return parts


def broad_sweep(body,vector):
    b=body.BoundingBox();lo=[b.xmin,b.ymin,b.zmin];hi=[b.xmax,b.ymax,b.zmax]
    return box([v+min(0,d) for v,d in zip(lo,vector)],[v+max(0,d) for v,d in zip(hi,vector)])


def motion(label,body,vector,fixed):
    cage=broad_sweep(body,vector);enclosure=None;rows=[]
    for name,obstacle in sorted(fixed.items()):
        if common(cage,obstacle)<=TOL:
            values=[0.];method='complete_axis_box_superset'
        else:
            if enclosure is None:enclosure=regions(body,vector)[0]
            c=checks(enclosure,obstacle);values=c['region_common_mm3'];method='complete_native_translation_regions'
        upper=sum_common_upper_bound(values)
        rows.append({'fixed':name,'method':method,'common_mm3':values,'common_upper_bound_mm3':upper,
                     'common_upper_bound_is_sum_not_union_volume':True,'clear':upper<=TOL})
    return {'label':label,'translation_mm':vector,'checks':rows,'failed':[r for r in rows if not r['clear']]}


def plan(side):
    sign=-1 if side=='L' else 1
    return [(side+'_TAB',(0,0,12.)),(side+'_SHOULDER_PIN_NOMINAL',(-sign*10.,0,0)),
            (side+'_THUMB_PAD',(0,0,-8.)),(side+'_PAD_SCREW_M06_NOMINAL',(0,0,-8.)),
            (side+'_ROOF',(0,0,12.)),(side+'_ROOF_SCREW_0_M1_NOMINAL',(0,0,-10.)),(side+'_ROOF_SCREW_1_M1_NOMINAL',(0,0,-10.))]


def tools(new,installed):
    result=[]
    for side in 'LR':
        # Flat finite tool blade within the actual slot, not a whole screwdriver handle.
        blade=box((.8,19.92,4.85),(10.89,20.08,5.75))
        if side=='L':blade=blade.mirror('YZ')
        targets=[(side+'_SHOULDER_PIN_NOMINAL',blade)]
        x=-11.6 if side=='L' else 11.6
        for role,y,length in [('PAD_SCREW_M06_NOMINAL',24.5,.40),('ROOF_SCREW_0_M1_NOMINAL',14.5,.65),('ROOF_SCREW_1_M1_NOMINAL',29.6,.65)]:
            targets.append((side+'_'+role,box((x-length,y-.08,-10.),(x+length,y+.08,.19))))
        for name,body in targets:
            values=[{'fixed':key,'common_mm3':common(body,part)} for key,part in sorted(installed.items())]
            result.append({'fastener':name,'checks':values,'failed':[r for r in values if r['common_mm3']>TOL]})
    return result


def root_closure_check(new,side):
    if side not in ('L','R'):raise ValueError('invalid side')
    parked=new[side+'_PAWL'].translate((0,0,1.1))
    enclosure,receipt=regions(parked,(0,0,-10.))
    result=checks(enclosure,new[side+'_ROOT_OUTER'])
    return {'side':side,'scope':'earlier outer-root closure over parked PAWL socket',
            'relative_full_translation_mm':[0.,0.,-10.],'enclosure':receipt,'result':result}


def verify(manifest,output):
    output=Path(output)
    if output.exists():raise ValueError('new result path required')
    sources={str(Path(f).resolve()):sha(f) for f in (__file__,sum_common_upper_bound.__code__.co_filename)}
    meta,new,h=load(manifest);h.update(sources);parent,prior,old,profiles=parent_native(h)
    accounting={}
    for side in 'LR':
        original=parent[side+'_ORIGINAL_PAWL'];modified=new[side+'_PAWL']
        if vol(original.cut(modified))>TOL:raise ValueError('original PAWL contact body lost')
        rootold=parent[side+'_ROOT_OUTER'];rootnew=new[side+'_ROOT_OUTER']
        if vol(rootnew.cut(rootold))>TOL:raise ValueError('unexpected root addition')
        lost=rootold.cut(rootnew);leaves,_=w.v.n.whole_material(lost)
        for b in leaves:
            bb=b.BoundingBox()
            if bb.ymin<19.3-TOL or bb.ymax>20.7+TOL or bb.zmin<3.9-TOL or bb.zmax>7.1+TOL:raise ValueError('root cut outside declared pin corridor')
        accounting[side]={'original_PAWL_removed_mm3':vol(original.cut(modified)),'boss_added_mm3':vol(modified.cut(original)),'root_removed_mm3':vol(lost)}
        # Complete active slotted plate is identical; changes below it serve pad installation.
        region=box((-40,0,4.6),(40,40,10))
        w.v.equal(new[side+'_TAB'].intersect(region),parent[side+'_TAB'].intersect(region))
    root_closure=[root_closure_check(new,side) for side in 'LR']
    if any(not r['result']['all_regions_clear'] for r in root_closure):
        raise ValueError('socket boss obstructs earlier outer-root assembly')
    print('EARLIER_ROOT_CLOSURE',root_closure,flush=True)
    # Every pair is rechecked at home. Additional states check all new/modified participants.
    changed={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('PAWL','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',*INSERT_ROLES)}
    static=[];static_failed=[]
    for index,(slide,descent,tabs) in enumerate([(0.,0.,(0.,0.)),(0.,0.,(1.5,1.5)),(0.,0.,(3.,3.)),(40.,0.,(3.,3.)),(79.75,8.2,(3.,3.))]):
        p=scene(new,parent,prior,old,profiles,slide,descent,tabs)
        rows=w.pairs(p,None if index==0 else changed);bad=[r for r in rows if r['common_mm3']>TOL]
        static.append({'slide_mm':slide,'descent_mm':descent,'tabs_mm':tabs,'participants':79,'all_pairs':index==0,'pairs':rows,'failed':bad})
        static_failed.extend(bad);print('POSE',slide,descent,tabs,'PAIRS',len(rows),'FAIL',bad,flush=True)
    home=scene(new,parent,prior,old,profiles,0.,0.,(0.,0.))
    detachable={s+'_'+k for s in 'LR' for k in INSERT_ROLES}
    # The outer frame/B are deliberately absent; other final-pose parts are conservative obstacles.
    installed={k:v for k,v in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}}
    stages=[]
    for side in 'LR':
        for role,withdrawal in plan(side):
            row=motion(role,home[role],withdrawal,installed);row['installed_before']=sorted(installed)
            stages.append(row);installed[role]=home[role]
            print('ASSEMBLY',role,'PAIRS',len(row['checks']),'FAIL',row['failed'],flush=True)
    tool_rows=tools(new,installed)
    # Genuine old exclusions: closed guide prevents top loading; captured shoulders prevent axial tab loading.
    negatives=[]
    for side in 'LR':
        oldtab=parent[side+'_TAB'];oldguide=parent[side+'_GUIDE'];oldpawl=parent[side+'_PAWL']
        for name,body,move,obstacle in [('OLD_CLOSED_GUIDE',oldtab,(0,0,1.),oldguide),('OLD_INTEGRAL_COLLAR',oldtab,(-.3 if side=='R' else .3,0,0),oldpawl)]:
            volume=common(body.translate(move),obstacle)
            negatives.append({'side':side,'case':name,'translation_mm':move,'common_mm3':volume,'limited_witness_not_global_assembly_impossibility':True})
            if volume<=TOL:raise ValueError('old nonserviceable counterexample lost')
    # Actual new slot flanks and travel stops, with the assembled roof as a participant.
    contact_input={side+'_TAB':new[side+'_TAB'] for side in 'LR'}
    for side in 'LR':contact_input[side+'_GUIDE']=cq.Compound.makeCompound([new['A_BACK_PANEL'],new[side+'_ROOF']])
    contacts=w.slot_checks(contact_input)
    motions=[]
    for side in 'LR':
        fixed={k:b for k,b in home.items() if k not in {side+'_TAB',side+'_THUMB_PAD',side+'_PAD_SCREW_M06_NOMINAL',side+'_PAWL',side+'_SHOULDER_PIN_NOMINAL','A_FRAME','B_SHELL'}}
        for role,vector in [('TAB',(0,3.,0)),('THUMB_PAD',(0,3.,0)),('PAD_SCREW_M06_NOMINAL',(0,3.,0)),('PAWL',(0,0,1.1)),('SHOULDER_PIN_NOMINAL',(0,0,1.1))]:
            motions.append(motion(side+'_'+role,home[side+'_'+role],vector,fixed))
        motions.append(motion(side+'_PIN_RELATIVE_TAB',home[side+'_SHOULDER_PIN_NOMINAL'],(0,-3.,1.1),{side+'_TAB':home[side+'_TAB']}))
    # Frame closure must be checked against actual controls; no global old-shell proof is reused.
    closure=[]
    closure_names={'A_BACK_PANEL'}|changed
    for name in sorted(closure_names):
        closure.append(motion('FRAME_CLOSE_'+name,home[name],(0,0,-20.),{'A_FRAME':home['A_FRAME']}))
    outside={k:vol(b.cut(old['A_OUTER'])) for k,b in home.items() if k in changed}
    failed={'static':static_failed,'assembly':[r for r in stages if r['failed']],'tools':[r for r in tool_rows if r['failed']],
            'nominal_control_motion':[r for r in motions if r['failed']],'control_frame_closure':[r for r in closure if r['failed']],
            'outside_A':{k:v for k,v in outside.items() if v>TOL}}
    if any(sha(p)!=v for p,v in h.items()):raise ValueError('native input changed during check')
    if any(k in sys.modules for k in ('serviceable_pawl','pawl_actuator','cam_coupling')):raise ValueError('candidate generator imported')
    result={'base_main':meta['base_main'],'source_sha256':meta['source_sha256'],'reader_sha256':sha(__file__),'input_sha256':h,
            'native_templates':len(new),'earlier_root_closure':root_closure,'material':accounting,'nominal_states':static,'assembly_stages':stages,'finite_tool_checks':tool_rows,
            'old_assembly_counterexamples':negatives,'slot_contacts':contacts,'nominal_control_motion':motions,'control_frame_closure':closure,
            'failures':failed,'passed':not any(failed.values()),'same_CAD_kernel':True,'candidate_builder_imported':False,
            'assembly_stage_frame_and_B_absent':True,'parent_cartridge_and_transmission_preassembly_not_recertified':True,
            'thread_preload_holding_force_qualified':False,'endpoint_allowance_problem_not_repaired':True,'full_phone_allocation_and_continuous_motion_qualified':False,
            'two_manual_inputs_not_automatic_release':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',result['passed'],{k:len(v) for k,v in failed.items()},flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.manifest,a.output);raise SystemExit(0 if r['passed'] else 1)
