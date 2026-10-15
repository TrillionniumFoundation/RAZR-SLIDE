"""Builder-free native readback of manual PAWL actuation and geometric interlocks.

Same CAD kernel. Native slot flanks and nominal sequences do not establish
forces, automatic return, detents, load-bearing OPEN lock or full tolerances.
Wrong-order native collisions are retained rather than clamped into a pass.
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
import verify_cam_coupling as v

ROOT=Path(__file__).resolve().parents[1]
M=1.1/3.
PR=.4
GR=.425
TOL=1e-7


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_new(manifest):
    manifest=Path(manifest).resolve();meta=json.loads(manifest.read_text());p={};h={str(manifest):sha(manifest)}
    expected={s+'_'+k for s in 'LR' for k in ('PAWL','ORIGINAL_PAWL','PIN','TAB','GUIDE','ROOT_OUTER')}|{'A_BACK_PANEL'}
    if set(meta['exports'])!=expected:raise ValueError('missing or extra actuator part')
    for name,rec in meta['exports'].items():
        rel=Path(rec['path']);path=manifest.parent/rel
        if rel.is_absolute() or len(rel.parts)!=1 or rel.name!=name+'.step' or path.is_symlink():raise ValueError('unsafe STEP filename')
        if sha(path)!=rec['sha256']:raise ValueError('changed native bytes')
        values=[rec['volume_mm3'],*rec['bounds_mm']]
        if len(values)!=7 or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):raise ValueError('nonfinite certificate')
        roots=cq.importers.importStep(str(path)).vals()
        if len(roots)!=1:raise ValueError('extra native root')
        body=v.n.single(roots[0]);b=body.BoundingBox();bounds=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if abs(v.vol(body)-values[0])>TOL or any(abs(a-b)>TOL for a,b in zip(bounds,values[1:])):raise ValueError('native certificate differs')
        p[name]=body;h[str(path)]=sha(path)
    return meta,p,h


def prior_native(h):
    folder=ROOT/'engineering/cam-coupling-20261015'
    gm=folder/'geometry-v5-manifest.json';entries=json.loads(gm.read_text());arc=folder/entries['archive']
    if sha(arc)!=entries['archive_sha256']:raise ValueError('prior cam archive changed')
    h[str(gm)]=sha(gm);h[str(arc)]=sha(arc);manifest=folder/'V5_NATIVE_MANIFEST.json';h[str(manifest)]=sha(manifest)
    with tempfile.TemporaryDirectory(prefix='pawl-prior-') as td,tarfile.open(arc,'r:gz') as t:
        directory=Path(td)
        for rec in entries['files']:
            name=Path(rec['path'])
            if name.is_absolute() or len(name.parts)!=1:raise ValueError('unsafe prior member')
            data=t.extractfile(rec['path']).read()
            if len(data)!=rec['bytes'] or hashlib.sha256(data).hexdigest()!=rec['sha256']:raise ValueError('prior native member changed')
            (directory/name).write_bytes(data)
        (directory/'manifest.json').write_bytes(manifest.read_bytes());_,p,_=v.load(directory/'manifest.json')
    old=v.source_parts(h)
    f=ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz';h[str(f)]=sha(f)
    data=json.loads(gzip.decompress(f.read_bytes()));fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
    profiles={s:[v.ContactProfile(**{k:c['profile'][k] for k in fields}) for c in data['sides'][s]['contacts']] for s in 'LR'}
    return p,old,profiles


def scene(new,prior,old,profiles,s,d,tabs,*,key_offset=0.,actuator_flank=0.):
    if len(tabs)!=2 or any(type(u) not in (int,float) or not math.isfinite(u) or not 0<=u<=3 for u in tabs):raise ValueError('bad manual controls')
    parts=v.scene(prior,old,profiles,s,d)
    if key_offset:
        dx=(v.G-v.R)*math.hypot(1,v.K);pr=v.prototype(prior,s,d,dx=dx,dq=key_offset)
        for side in 'LR':
            parts[side+'_KEY']=pr[side+'_KEY_YOKE'];parts[side+'_CROSSHEAD']=pr[side+'_CROSSHEAD']
            for i in range(1,4):parts[f'{side}_TELESCOPE_{i}']=pr[f'{side}_TELESCOPE_{i}']
            for i in (0,1):
                profile=profiles[side][i];delta=profile.evaluate(v.K*s+key_offset)[0]-profile.evaluate(0)[0];sign=-1 if side=='L' else 1
                parts[f'{side}_STOP_{i}']=old[f'{side}_STOP_{i}'].translate((sign*delta,0,0))
                role=f'{side}_SPRING_{i}_OD_TOL_ENVELOPE';b=old[role].BoundingBox();lo=b.xmin+min(0,sign*delta);hi=b.xmax+max(0,sign*delta)
                parts[role]=v.n.single(cq.Solid.makeCylinder(.43,hi-lo,cq.Vector(lo,(b.ymin+b.ymax)/2,(b.zmin+b.zmax)/2),cq.Vector(1,0,0)))
    for side,u in zip('LR',tabs):
        parts[side+'_PAWL']=new[side+'_PAWL'].translate((0,0,M*u+actuator_flank))
        parts[side+'_TAB']=new[side+'_TAB'].translate((0,u,0))
        parts[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
    parts['A_BACK_PANEL']=new['A_BACK_PANEL']
    if len(parts)!=67:raise ValueError('incomplete native scene')
    return parts


def pairs(parts,selected=None):
    result=[]
    for a,b in itertools.combinations(sorted(parts),2):
        if selected is not None and a not in selected and b not in selected:continue
        value=v.common(parts[a],parts[b]);result.append({'a':a,'b':b,'common_mm3':value})
    return result


def slot_checks(new):
    half=(GR-PR)*math.hypot(1,M);rows=[];stops=[]
    for side in 'LR':
        for u in (0.,1.5,3.):
            body=new[side+'_TAB'].translate((0,u,0))
            for flank in (-1,1):
                z=5.3+M*u+flank*half
                pin=v.n.single(cq.Solid.makeCylinder(PR,.96,cq.Vector(11.12,20.,z),cq.Vector(1,0,0)))
                if side=='L':pin=pin.mirror('YZ')
                touch=pin.distance(body);hit=v.common(pin,body);over=v.common(pin.translate((0,0,flank*.01)),body)
                if touch>1e-6 or hit>TOL or over<=TOL:raise ValueError('native slot flank does not constrain the PAWL')
                rows.append({'side':side,'tab_mm':u,'flank':flank,'tangent_distance_mm':touch,'common_mm3':hit,'overtravel_common_mm3':over})
        for u,allowed in ((0.,True),(3.,True),(-.01,False),(3.01,False)):
            value=v.common(new[side+'_TAB'].translate((0,u,0)),new[side+'_GUIDE'])
            if (allowed and value>TOL) or (not allowed and value<=TOL):raise ValueError('guide travel stop not present')
            stops.append({'side':side,'tab_mm':u,'within_nominal_domain':allowed,'common_mm3':value})
    return {'flanks':rows,'travel_stops':stops,'slot_only_PAWL_halfwidth_mm':half}


def verify(manifest,output):
    output=Path(output)
    if output.exists():raise ValueError('new output required')
    meta,new,h=load_new(manifest);prior,old,profiles=prior_native(h);material=[]
    for side in 'LR':
        v.equal(new[side+'_ORIGINAL_PAWL'],old[side+'_PAWL']);lost=v.vol(old[side+'_PAWL'].cut(new[side+'_PAWL']))
        if lost>TOL:raise ValueError('old PAWL contact body was trimmed')
        root=old[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'];revised=new[side+'_ROOT_OUTER']
        if v.vol(revised.cut(root))>TOL:raise ValueError('unreported root addition')
        removed=root.cut(revised);leaves,_=v.n.whole_material(removed)
        for leaf in leaves:
            b=leaf.BoundingBox()
            if b.ymin<19.55-TOL or b.ymax>20.45+TOL or b.zmin<4.85-TOL or b.zmax>6.85+TOL:raise ValueError('root trimmed outside fixed pin window')
        material.append({'side':side,'original_PAWL_lost_mm3':lost,'pin_added_mm3':v.vol(new[side+'_PAWL'].cut(old[side+'_PAWL'])),'root_window_removed_mm3':v.vol(removed)})
    contacts=slot_checks(new);print('SLOT_FLANKS',len(contacts['flanks']),'TRAVEL_STOPS',len(contacts['travel_stops']),flush=True)
    changed={'L_PAWL','R_PAWL','L_TAB','R_TAB','L_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','R_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','A_BACK_PANEL'}
    traces=[('ENGAGED',0.,0.,(0.,0.)),('RELEASE_MID',0.,0.,(1.5,1.5)),('RELEASED',0.,0.,(3.,3.)),('ONE_SIDE_RELEASED',0.,0.,(3.,0.)),('SLIDING',40.,0.,(3.,3.)),('PREDOCK',79.75,0.,(3.,3.)),('SEATED',79.75,8.2,(3.,3.))]
    rows=[];failures=[]
    for name,s,d,tabs in traces:
        part=scene(new,prior,old,profiles,s,d,tabs);result=pairs(part);bad=[x for x in result if x['common_mm3']>TOL]
        rows.append({'name':name,'slide_mm':s,'descent_mm':d,'tabs_mm':tabs,'participants':67,'pairs':result,'positive_pairs':bad})
        failures.extend([{'state':name,**x} for x in bad]);print(name,'PAIRS',len(result),'BAD',bad,flush=True)
    negatives=[]
    for name,s,d,tabs in [('MOVE_WITHOUT_RELEASE',5.,0.,(0.,0.)),('MOVE_WITH_ONE_RELEASE',5.,0.,(3.,0.)),('RETURN_BEFORE_KEY',40.,0.,(0.,0.))]:
        result=pairs(scene(new,prior,old,profiles,s,d,tabs),changed);bad=[x for x in result if x['common_mm3']>TOL]
        if not bad:raise ValueError('wrong-order negative control did not produce a physical obstruction: '+name)
        negatives.append({'name':name,'slide_mm':s,'tabs_mm':tabs,'positive_pairs':bad});print('NEGATIVE',name,bad,flush=True)
    key_half=(v.G-v.R)*(math.hypot(1,v.K)+math.sqrt(2));half=contacts['slot_only_PAWL_halfwidth_mm'];backlash=[]
    for u in (0.,1.5,3.):
        for flank in (-1,1):
            parts=scene(new,prior,old,profiles,0.,0.,(u,u),key_offset=key_half,actuator_flank=flank*half)
            result=pairs(parts,changed);bad=[x for x in result if x['common_mm3']>TOL]
            backlash.append({'tab_mm':u,'KEY_positive_return_offset_mm':key_half,'PAWL_flank_offset_mm':flank*half,'positive_pairs':bad})
            print('CLEARANCE_BRANCH',u,flank,'BAD',bad,flush=True)
    whole=scene(new,prior,old,profiles,0.,0.,(0.,0.));contained={k:v.vol(whole[k].cut(old['A_OUTER'])) for k in changed}
    if any(value>TOL for value in contained.values()):raise ValueError('new control exceeds assumed A outer')
    if any(sha(f)!=value for f,value in h.items()):raise ValueError('native inputs changed during readback')
    if 'pawl_actuator' in sys.modules or 'cam_coupling' in sys.modules:raise ValueError('candidate builder imported')
    result={'base_main':meta['base_main'],'source_sha256':meta['source_sha256'],'reader_sha256':sha(__file__),'input_sha256':h,'native_exports':len(new),'contacts':contacts,'material':material,'nominal_sequence':rows,'wrong_order_obstructions':negatives,'combined_clearance_probes':backlash,'all_clearance_branches_clear':not any(x['positive_pairs'] for x in backlash),'new_control_outside_A_mm3':contained,'failure_pairs':failures,'passed':not failures,
            'pass_scope':'nominal manual control geometry and detected bad-order contact, not complete clearance or force qualification',
            'same_CAD_kernel':True,'candidate_builder_imported':False,'manual_inputs_required':2,'automatic_return_detent_or_preload':False,'OPEN_load_lock_implemented':False,'STOP_restoring_force_still_a_boundary_condition':True,'negative_KEY_clearance_branch_outside_inherited_profile_not_qualified':True,'full_continuous_assembly_or_installation_proved':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('ACTUATOR_RESULT',result['passed'],'ALL_CLEARANCE_BRANCHES_CLEAR',result['all_clearance_branches_clear'],flush=True);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=verify(args.manifest,args.output);raise SystemExit(0 if r['passed'] else 1)
