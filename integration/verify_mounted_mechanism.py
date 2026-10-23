"""Builder-free reimport of mounted research cartridges and removable back panel.

Native material, added mounting paths and complete two-stage B shell clearance
are verified. This is NOT B-driven KEY motion, helical threads/preload, load,
tolerance, PCB/OLED/battery integration, tool-handle or fixture qualification.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import sys
import tarfile
import tempfile
import cadquery as cq
import cam_contact_native as n
from verify_contact_motion import PARTS
from verify_thin_mechanism import placement
from translation_regions import regions, checks, sum_common_upper_bound

ROOT=Path(__file__).resolve().parents[1]
TOL=1e-7


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vol(body):return n.whole_material(body,empty=True)[1]


def equal(a,b):
    v=[vol(a.cut(b)),vol(b.cut(a))]
    if max(v)>TOL:raise ValueError('whole native shape differs')
    return v


def box(lo,hi):
    if min(b-a for a,b in zip(lo,hi))<=0:raise ValueError('invalid proof box')
    return n.single(cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo)))


def bb(body):
    b=body.BoundingBox()
    return [b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]


def common(a,b):
    # Inputs have already passed complete-payload validation; strict positive gap only.
    amin,amax=bb(a);bmin,bmax=bb(b)
    if any(x>y+TOL or z>w+TOL for x,y,z,w in zip(amin,bmax,bmin,amax)):
        return 0.,'validated_positive_axis_gap'
    v=vol(a.intersect(b))
    if v>min(vol(a),vol(b))+TOL:raise ValueError('invalid signed common bound')
    return v,'native_common'


def sweep_box(body,move):
    lo,hi=bb(body)
    return box([a+min(0,d) for a,d in zip(lo,move)],[a+max(0,d) for a,d in zip(hi,move)])


def read_all(manifest):
    manifest=Path(manifest).resolve();r=json.loads(manifest.read_text());parts={};hashes={str(manifest):sha(manifest)}
    expected={s+'_'+k for s in 'LR' for k in PARTS}|{s+'_PARENT_ROOT_INNER' for s in 'LR'}
    expected|={family+'_'+str(i)+'_M1x3_NOMINAL' for family in ('CARTRIDGE','FRAME') for i in range(4)}
    expected|={'A_FRAME','A_BACK_PANEL','A_PARENT_SHELL','A_OUTER','A_PARENT_CAVITY','B_SHELL','B_OUTER','A_COMPLETE_MOUNTED'}
    if set(r['exports'])!=expected:raise ValueError('missing/extra mounted participant')
    for role,rec in r['exports'].items():
        rel=Path(rec['path'])
        if rel.is_absolute() or len(rel.parts)!=1 or rel.name!=role+'.step':raise ValueError('wrong STEP name')
        p=manifest.parent/rel
        if p.is_symlink() or sha(p)!=rec['sha256']:raise ValueError('changed STEP bytes')
        values=[rec['volume_mm3'],*rec['bounds_xyz_mm']]
        if len(values)!=7 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('nonfinite certificate')
        roots=cq.importers.importStep(str(p)).vals()
        if len(roots)!=1:raise ValueError('extra STEP root')
        body=roots[0];leaves,total=n.whole_material(body);count=56 if role=='A_COMPLETE_MOUNTED' else 1
        if len(leaves)!=count or type(rec['solid_count']) is not int or rec['solid_count']!=count:raise ValueError('complete solid count differs')
        lo,hi=bb(body);actual=[lo[0],hi[0],lo[1],hi[1],lo[2],hi[2]]
        if abs(total-rec['volume_mm3'])>TOL or any(abs(x-y)>TOL for x,y in zip(actual,rec['bounds_xyz_mm'])):raise ValueError('native certificate mismatch')
        if any(leaves[i].isSame(leaves[j]) for i in range(len(leaves)) for j in range(i)):raise ValueError('duplicate solid')
        parts[role]=body;hashes[str(p)]=sha(p)
    return r,parts,hashes


def parent_checks(parts,hashes):
    source=ROOT/'engineering/thin-mechanism-20261015';gm=json.loads((source/'geometry-manifest.json').read_text());arc=source/gm['archive']
    if sha(arc)!=gm['archive_sha256']:raise ValueError('parent archive identity differs')
    hashes[str(source/'geometry-manifest.json')]=sha(source/'geometry-manifest.json');hashes[str(arc)]=sha(arc)
    records=[];original={}
    with tarfile.open(arc,'r:gz') as t,tempfile.TemporaryDirectory(prefix='mount-independent-') as td:
        for side in 'LR':
            for name in sorted(PARTS):
                member=f'{side}_candidate_{name}.step';raw=t.extractfile(member).read();entry=next(x for x in gm['files'] if x['path']==member)
                if len(raw)!=entry['bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('parent member bytes differ')
                p=Path(td)/member;p.write_bytes(raw);roots=cq.importers.importStep(str(p)).vals()
                if len(roots)!=1:raise ValueError('extra source root')
                old=placement(n.single(roots[0]),side).translate((0,6.,0));original[side+'_'+name]=old
                new=parts[side+'_'+name]
                if name!='ROOT_INNER':equal(old,new)
                else:
                    equal(old,parts[side+'_PARENT_ROOT_INNER'])
                    if vol(old.cut(new))>TOL:raise ValueError('source root was trimmed')
                    if vol(new.cut(old))<=TOL:raise ValueError('missing mount ears')
                records.append({'side':side,'name':name,'source_removed_mm3':vol(old.cut(new)),
                                'source_added_mm3':vol(new.cut(old))})
    return records,original


def verify(manifest,output):
    output=Path(output)
    if output.exists():raise ValueError('new report path required')
    sources={str(Path(f).resolve()):sha(f) for f in (__file__,sum_common_upper_bound.__code__.co_filename)}
    r,p,hashes=read_all(manifest);hashes.update(sources);parent,old=parent_checks(p,hashes)
    screws={k:v for k,v in p.items() if k.startswith(('CARTRIDGE_','FRAME_'))}
    mechanism={s+'_'+k:p[s+'_'+k] for s in 'LR' for k in PARTS}
    installed={'A_FRAME':p['A_FRAME'],'A_BACK_PANEL':p['A_BACK_PANEL'],**mechanism,**screws}
    # Check every pair, not only the changed geometry. No expected overlap is waived.
    static=[]
    for a,b in itertools.combinations(sorted(installed),2):
        v,method=common(installed[a],installed[b]);static.append({'a':a,'b':b,'volume_mm3':v,'method':method})
    bad=[x for x in static if x['volume_mm3']>TOL]
    print('STATIC',len(static),'BAD',bad,flush=True)
    # Complete assembly contains every declared leaf exactly once.
    leaves=n.whole_material(p['A_COMPLETE_MOUNTED'])[0];used=set()
    for name,body in installed.items():
        matches=[i for i,b in enumerate(leaves) if i not in used and abs(vol(b)-vol(body))<=TOL and max(vol(b.cut(body)),vol(body.cut(b)))<=TOL]
        if len(matches)!=1:raise ValueError('assembled leaf not uniquely matched: '+name)
        used.add(matches[0])
    if len(used)!=56:raise ValueError('assembly is incomplete')
    contained={k:vol(b.cut(p['A_OUTER'])) for k,b in installed.items()}
    # Actual native originals and two full B movement enclosure shapes are bound here.
    layout=ROOT/'engineering/phone-layout-study-20261015/native';lr=json.loads((layout/'report.json').read_text())
    for key,ours in [('stepped_A_outer','A_OUTER'),('stepped_A_shell','A_PARENT_SHELL'),('stepped_A_cavity','A_PARENT_CAVITY'),('stepped_B_shell','B_SHELL'),('stepped_B_outer','B_OUTER')]:
        rec=lr['exports'][key];f=layout/rec['path']
        if sha(f)!=rec['sha256']:raise ValueError('changed shell reference')
        equal(p[ours],n.single(cq.importers.importStep(str(f)).val()));hashes[str(f)]=sha(f)
    phases=[]
    for name in ('slide_outer_superset','seat_lap_superset','seat_body_superset'):
        rec=lr['exports'][name];f=layout/rec['path']
        if sha(f)!=rec['sha256']:raise ValueError('changed B phase proof')
        cage=n.single(cq.importers.importStep(str(f)).val());hashes[str(f)]=sha(f)
        v,_=common(p['A_OUTER'],cage);phases.append({'full_phase':name,'A_outer_common_mm3':v})
    # Rigid cassette/backpanel insertion from below; no detached or omitted KEY.
    # Bounding boxes suffice for every cartridge and fastener and conservatively
    # cover the entire 20 mm translation. Panel itself needs its actual faces.
    insertion=[]
    for k,b in installed.items():
        if k in ('A_FRAME','A_BACK_PANEL') or k.startswith('FRAME_'):continue
        cage=sweep_box(b,(0,0,-20.));v,_=common(cage,p['A_FRAME'])
        insertion.append({'part':k,'sweep_common_mm3':v,'method':'complete_translated_AABB_superset'})
    native_regions,_=regions(p['A_BACK_PANEL'],(0,0,-20.))
    panel_check=checks(native_regions,p['A_FRAME']);insertion.append({'part':'A_BACK_PANEL',
        'sweep_common_mm3':sum_common_upper_bound(panel_check['region_common_mm3']),
        'common_field_is_sum_upper_bound_not_union_volume':True,'native_regions':panel_check})
    print('INSERTION',len(insertion),'BAD',[x for x in insertion if x['sweep_common_mm3']>TOL],flush=True)
    # Insert mounting screws from the actual back side; modeled tool is only
    # a finite straight shaft, not a chosen drive/socket or complete handle.
    screw_paths=[];tool_paths=[]
    for k,screw in screws.items():
        regs,_=regions(screw,(0,0,-8.));others={a:b for a,b in installed.items() if a!=k}
        for name,b in others.items():
            v,_=common(sweep_box(screw,(0,0,-8.)),b)
            check=checks(regs,b) if v>TOL else {'all_regions_clear':True,'region_common_mm3':[0.]}
            screw_paths.append({'screw':k,'fixed':name,'all_clear':check['all_regions_clear'],'commons_mm3':check['region_common_mm3']})
        center=screw.Center();x,y=center.x,center.y
        tool=n.single(cq.Solid.makeCylinder(.7,15.1,cq.Vector(x,y,-15.),cq.Vector(0,0,1)))
        for name,b in others.items():
            v,_=common(tool,b);tool_paths.append({'tool_for':k,'fixed':name,'common_mm3':v})
    # Unchanged thin contact geometry retains its original qualification scope.
    # Only new material/interfaces require new local-moving-part comparisons.
    extras={'A_FRAME':p['A_FRAME'],'A_BACK_PANEL':p['A_BACK_PANEL'],**screws}
    for s in 'LR':
        added=p[s+'_ROOT_INNER'].cut(old[s+'_ROOT_INNER']);leaves,_=n.whole_material(added)
        for i,b in enumerate(leaves):extras[s+'_MOUNT_ADDITION_'+str(i)]=b
    moves=[]
    for s in 'LR':
        for role,vector in [('KEY',(0,12.,0)),('PAWL',(0,0,1.1)),('STOP_0',((1.16 if s=='L' else -1.16),0,0)),('STOP_1',((1.16 if s=='L' else -1.16),0,0))]:
            body=p[s+'_'+role];bound=sweep_box(body,vector);rr=None
            for k,b in extras.items():
                v,_=common(bound,b)
                if v>TOL:
                    if rr is None:rr=regions(body,vector)[0]
                    c=checks(rr,b);ok=c['all_regions_clear'];vals=c['region_common_mm3']
                else:ok=True;vals=[0.]
                moves.append({'side':s,'moving':role,'fixed':k,'clear':ok,'region_common_mm3':vals})
    # Translation invariant: an actually fixed B-to-KEY link cannot absorb 67.75
    # mm extra slide nor the independent 8.2 mm normal phase in the current guide.
    rejected_direct={'slide_mm':79.75,'KEY_max_withdrawal_mm':12.,'unabsorbed_Y_mm':67.75,'unabsorbed_Z_mm':8.2,
                     'one_to_one_rigid_link_compatible':False,'alternative_transmission_not_ruled_out':True}
    if any(sha(f)!=v for f,v in hashes.items()):raise ValueError('inputs changed while verifying')
    if 'mounted_mechanism' in sys.modules:raise ValueError('candidate builder imported')
    failed={'static':bad,'outside_A_outer':{k:v for k,v in contained.items() if v>TOL},
            'B_phases':[x for x in phases if x['A_outer_common_mm3']>TOL],
            'cassette_insertion':[x for x in insertion if x['sweep_common_mm3']>TOL],
            'screw_insertion':[x for x in screw_paths if not x['all_clear']],
            'tool_shaft':[x for x in tool_paths if x['common_mm3']>TOL],
            'local_motion':[x for x in moves if not x['clear']]}
    result={'source_sha256':r['source_sha256'],'verifier_sha256':sha(__file__),'input_sha256':hashes,
            'native_files':len(p),'complete_assembly_leaves':56,'source_parts':parent,'static_pairs':static,
            'all_component_outside_A_outer_mm3':contained,'complete_B_shell_phase_clearance':phases,
            'cassette_insertion':insertion,'screw_insertion':screw_paths,'tool_shaft_checks':tool_paths,
            'new_local_motion_checks':moves,'direct_coupling_rejection':rejected_direct,'failures':failed,
            'passed':not any(failed.values()),'same_CAD_kernel':True,'candidate_builder_imported':False,
            'B_to_KEY_actual_coupling_implemented':False,'housing_joint_threads_and_preload_qualified':False,
            'cassette_insertion_assumes_temporarily_held_moving_parts':True,
            'all_full_phone_electronics_screen_storage_battery_and_tolerances_still_missing':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('MOUNTED_RESULT',result['passed'],{k:len(v) for k,v in failed.items()},flush=True)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=verify(a.manifest,a.output);raise SystemExit(0 if r['passed'] else 1)
