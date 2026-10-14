"""Builder-free reimport and exhaustive replay of the declared cover-first steps.
Uses the same native kernel and generic enclosure math; not cross-kernel,
force, autonomous handling, actual gripper or finished-phone qualification.
"""
from pathlib import Path
import argparse,json,hashlib,tempfile,tarfile,sys,platform
import cam_contact_native as n
from translation_regions import regions,checks,subtract_regions
from verify_contact_motion import PARTS


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_step(p):
    vals=n.cq.importers.importStep(str(p)).vals()
    if len(vals)!=1:raise ValueError('extra STEP root')
    return n.single(vals[0])

def equal(a,b):
    av=n.whole_material(a.cut(b),empty=True)[1];bv=n.whole_material(b.cut(a),empty=True)[1]
    if max(av,bv)>1e-7:raise ValueError('unaccounted shape/material change')
    return [av,bv]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if sha(a.receipt)!=a.sha256:raise ValueError('receipt identity mismatch')
    r=json.loads(a.receipt.read_text());inputs={str(a.receipt):sha(a.receipt)};p={};comparisons=[];proofs=[]
    names=PARTS|{'PARKED_PAWL','JAW_LOWER','JAW_UPPER','JOIN_DRIVER_0','JOIN_DRIVER_1'}
    if set(r['exports'])!={side+'_'+name for side in 'LR' for name in names}:raise ValueError('complete native participant set differs')
    for name,rec in r['exports'].items():
        path=a.receipt.parent/rec['path']
        if path.parent!=a.receipt.parent or sha(path)!=rec['sha256']:raise ValueError('native bytes/path differ')
        body=read_step(path);bb=body.BoundingBox()
        if abs(body.Volume()-rec['volume_mm3'])>1e-7 or any(abs(getattr(bb,k)-v)>1e-7 for k,v in rec['bounds_mm'].items()):raise ValueError('full native certificate differs')
        p[name]=body;inputs[str(path)]=sha(path)
    olddir=a.repo/'engineering/keycover-geometry-20261014';gm=json.loads((olddir/'geometry-manifest.json').read_text());arc=olddir/'project-owned-geometry.tar.gz'
    if sha(arc)!=gm['archive_sha256']:raise ValueError('baseline archive identity differs')
    inputs[str(arc)]=sha(arc);files={x['path']:x for x in gm['files']};old={}
    with tempfile.TemporaryDirectory(prefix='cover-order-native-') as td:
        with tarfile.open(arc,'r:gz') as t:
            for side in 'LR':
                for name in PARTS:
                    entry='installation/'+side+'_'+name+'.step';data=t.extractfile(entry).read()
                    if hashlib.sha256(data).hexdigest()!=files[entry]['sha256']:raise ValueError('baseline member hash mismatch')
                    f=Path(td)/(side+'_'+name+'.step');f.write_bytes(data);old[side+'_'+name]=read_step(f)
    for side in 'LR':
        ex=-1 if side=='L' else 1
        for name in sorted(PARTS-{'OLD_COVER'}):comparisons.append({'part':side+'_'+name,'symmetric_difference_mm3':equal(p[side+'_'+name],old[side+'_'+name])})
        equal(p[side+'_PARKED_PAWL'],p[side+'_PAWL'].translate((ex*1.1,0,0)))
        equal(p[side+'_JAW_LOWER'],n.box(side,-.8,.8,12.15,12.55,-3.4,-2.9))
        equal(p[side+'_JAW_UPPER'],n.box(side,-.8,.8,12.15,12.55,-2.5,-2.0))
        installed={'JAW_LOWER'}
        expected=[('PLACE_COVER','OLD_COVER',(0,0,5.)),('CLAMP_UPPER','JAW_UPPER',(0,0,3.)),('INSERT_INNER','ROOT_INNER',(-ex*10.,0,0)),('INSERT_PAWL_FROM_BELOW','PARKED_PAWL',(0,0,-25.)),('INSERT_STOP0','STOP_0',(ex*10.,0,0)),('INSERT_STOP1','STOP_1',(ex*10.,0,0)),('CLOSE_OUTER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',(ex*10.,0,0)),('INSERT_JOIN_SCREW0','ROOT_JOIN_SCREW_0_M1x3_NOMINAL',(ex*10.,0,0)),('INSERT_JOIN_SCREW1','ROOT_JOIN_SCREW_1_M1x3_NOMINAL',(ex*10.,0,0))]
        rows=[x for x in r['stages'] if x['side']==side]
        if len(rows)!=11:raise ValueError('missing assembly stage')
        for index,(stage,name,vec) in enumerate(expected):
            row=rows[index]
            if row['stage']!=stage or row['moving']!=name or row['start_translation_world_mm']!=list(vec) or row['end_translation_world_mm']!=[0,0,0] or set(row['fixed_names'])!=installed or set(row['checks'])!=installed:raise ValueError('altered path or omitted previously installed participant')
            moving=p[side+'_'+name];own,_=regions(moving,vec)
            for fixed_name in sorted(installed):
                fixed=p[side+'_'+fixed_name]
                if name.startswith('ROOT_') and fixed_name not in ('OLD_COVER','JAW_LOWER','JAW_UPPER'):
                    rel,_=regions(fixed,tuple(-v for v in vec));rec=checks(rel,moving)
                else:rec=checks(own,fixed)
                oldrec=row['checks'][fixed_name]
                if len(rec['region_common_mm3'])!=len(oldrec['region_common_mm3']) or any(abs(x-y)>1e-7 for x,y in zip(rec['region_common_mm3'],oldrec['region_common_mm3'])):raise ValueError('reimported enclosure result differs')
                proofs.append({'side':side,'stage':stage,'fixed':fixed_name,**rec})
            installed.add(name)
        for i in range(2):
            row=rows[9+i];name='JOIN_DRIVER_'+str(i);tool=p[side+'_'+name]
            expected_tool=n.cq.Solid.makeCylinder(1.5,60.,n.world(side,2.2,-2.4,-1.3+5*i),n.cq.Vector(ex,0,0));equal(tool,expected_tool)
            if row['stage']!=name or set(row['fixed_names'])!=installed or set(row['checks'])!=installed:raise ValueError('tool participants omitted')
            for fixed in sorted(installed):
                val=n.common(tool,p[side+'_'+fixed])
                if abs(val-row['checks'][fixed]['region_common_mm3'][0])>1e-7:raise ValueError('tool reimport differs')
                proofs.append({'side':side,'stage':name,'fixed':fixed,'region_common_mm3':[val],'all_regions_clear':val<=1e-7})
        print('REIMPORTED',side,'proof pairs',len(proofs),flush=True)
    if len(proofs)!=130 or len(comparisons)!=44:raise ValueError('native coverage differs')
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('input mutated during independent reimport')
    if any(x.startswith(('cover_admission','cover_order_gate','keycover_bypass','stow_contact_slots','stow_continuous_slots','split_root_cartridges')) for x in sys.modules):raise ValueError('candidate or scene generator imported')
    bad=[x for x in proofs if not x['all_regions_clear']]
    result={'host':platform.node(),'verifier_sha256':sha(__file__),'receipt_sha256':a.sha256,'input_SHA256':inputs,'inputs_unchanged':True,'complete_STEP_files':len(p),'unchanged_noncover_parts':comparisons,'unchanged_part_count':44,'stage_count':22,'pair_count':130,'checks':proofs,'positive_pairs':bad,'candidate_builder_imported':False,'same_kernel_and_generic_math_not_cross_engine':True,'nominal_sequence_clear':not bad,'jaw_force_actuation_threads_and_handling_unqualified':True,'phone_fit_unknown':True,'candidate_go':False,'manufacturing_go':False}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('REIMPORTED_ALL',len(proofs),'POSITIVE',len(bad),flush=True)
    if bad:raise SystemExit(1)

if __name__=='__main__':main()
