"""Read full STEP payloads independently of candidate/scene generators.
Checks old actual collision witnesses, all retained cover material, protected
plate geometry, actual KEY-subset separation, all unchanged components and
bench bounds. Same CAD kernel; no strength/fixture/phone qualification.
"""
from pathlib import Path
import argparse,hashlib,json,tarfile,tempfile,sys,platform,time
import cam_contact_native as n
from straight_envelope import whole_material
from keycover_connectivity import prove
from verify_contact_motion import PARTS

FIELDS=('xmin','xmax','ymin','ymax','zmin','zmax')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def match_eq(a,b,label):
    one=whole_material(a.cut(b),empty=True)[1];two=whole_material(b.cut(a),empty=True)[1]
    if max(one,two)>1e-7:raise ValueError('whole material differs: '+label)
    return {'label':label,'a_minus_b_mm3':one,'b_minus_a_mm3':two}
def load_step(path):
    roots=n.cq.importers.importStep(str(path)).vals()
    if len(roots)!=1:raise ValueError('unaccounted STEP roots')
    return roots[0]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True,type=Path);ap.add_argument('--receipt',required=True,type=Path)
    ap.add_argument('--expected-sha256',required=True);ap.add_argument('--assembly',type=Path)
    ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();start=time.monotonic()
    if sha(a.receipt)!=a.expected_sha256:raise ValueError('motion receipt hash mismatch')
    report=json.loads(a.receipt.read_text());parent=a.repo/'engineering/contact-motion-20261014'
    geometry=json.loads((parent/'geometry-manifest.json').read_text());arc=parent/'project-owned-native-geometry.tar.gz'
    if sha(arc)!=geometry['archive_sha256']:raise ValueError('historical archive modified')
    files={r['path']:r for r in geometry['files']};current={};old={};inputs={str(a.receipt):sha(a.receipt),str(arc):sha(arc),str(parent/'geometry-manifest.json'):sha(parent/'geometry-manifest.json')}
    with tempfile.TemporaryDirectory(prefix='razr-native-originals-') as td:
        with tarfile.open(arc,'r:gz') as ar:
            for side in 'LR':
                for name in PARTS:
                    key=side+'_'+name;archive_name='contact/'+key+'.step';entry=files[archive_name];b=ar.extractfile(archive_name).read()
                    if len(b)!=entry['bytes'] or hashlib.sha256(b).hexdigest()!=entry['sha256']:raise ValueError('historical STEP member mismatch')
                    p=Path(td)/(key+'.step');p.write_bytes(b);old[key]=n.single(load_step(p))
        for role,item in report['exports'].items():
            p=a.receipt.parent/item['path']
            if p.parent!=a.receipt.parent or sha(p)!=item['sha256']:raise ValueError('new native STEP bytes changed')
            shape=n.single(load_step(p));bb=shape.BoundingBox()
            if abs(shape.Volume()-item['volume_mm3'])>1e-7 or any(abs(getattr(bb,k)-v)>1e-7 for k,v in item['bounds_mm'].items()):raise ValueError('STEP certificate changed')
            current[role]=shape;inputs[str(p)]=sha(p)
        if len(current)!=76:raise ValueError('complete contact STEP set not read')
        unchanged=[];rows=[];negative=[]
        for side in 'LR':
            get=lambda name:current[side+'_'+name];previous=lambda name:old[side+'_'+name]
            key=get('KEY');cover=get('OLD_COVER');root=get('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS');sweep=get('KEY_COMPLETE_Q')
            for name in sorted(PARTS-{'OLD_COVER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'}):unchanged.append(match_eq(get(name),previous(name),side+'_'+name))
            oldcover=previous('OLD_COVER');oldroot=previous('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
            barrier,free,proof=prove(key,oldcover,side)
            fragments,cutvol=whole_material(oldcover.cut(sweep))
            if len(fragments)!=2:raise ValueError('old disconnected-cover control changed')
            retained=[whole_material(f.cut(cover),empty=True)[1] for f in fragments]
            if any(v>1e-7 for v in retained):raise ValueError('a retained old cover fragment was lost')
            removed=whole_material(oldcover.cut(cover),empty=True)[1];added=whole_material(cover.cut(oldcover),empty=True)[1]
            rootremoved=whole_material(oldroot.cut(root),empty=True)[1]
            outside=whole_material(oldcover.cut(cover).cut(sweep),empty=True)[1]
            if abs(removed-.048)>1e-7 or abs(added-1.848)>1e-7 or abs(rootremoved-.026)>1e-7 or outside>1e-7:raise ValueError('material change exceeds declared native KEY collision')
            if abs(oldcover.Volume()+added-removed-cover.Volume())>1e-7 or abs(oldroot.Volume()-rootremoved-root.Volume())>1e-7:raise ValueError('material balance mismatch')
            eb,qb,rb=n.bounds(side,oldcover);protected=n.box(side,eb[0]-.01,eb[1]+.01,qb[0]-.01,qb[1]+.01,rb[0]-.01,-6.4)
            protected_removed=whole_material(oldcover.cut(cover).intersect(protected),empty=True)[1];protected_added=whole_material(cover.cut(oldcover).intersect(protected),empty=True)[1]
            if max(protected_removed,protected_added)>1e-7:raise ValueError('original lower plate or holes changed')
            for q,name,oldpart,newpart in [(5.,'OLD_COVER',oldcover,cover),(2.5,'ROOT',oldroot,root),(3.,'ROOT',oldroot,root)]:
                pose=key.translate((0,-q,0));before=n.common(pose,oldpart);after=n.common(pose,newpart)
                if before<=1e-7 or after>1e-7:raise ValueError('old actual-pose rejection/new clearance not reproduced')
                negative.append({'side':side,'q_mm':q,'part':name,'old_common_mm3':before,'new_common_mm3':after})
            oldcompound=n.cq.Compound.makeCompound([previous(k) for k in PARTS]);newcompound=n.cq.Compound.makeCompound([get(k) for k in PARTS]);bb=oldcompound.BoundingBox();nb=newcompound.BoundingBox()
            delta={k:getattr(nb,k)-getattr(bb,k) for k in FIELDS}
            if any(abs(v)>1e-7 for v in delta.values()):raise ValueError('whole bench bounds changed')
            rows.append({'side':side,'old_cover_fragments_retained_whole':len(fragments),'old_fragments_missing_from_new_mm3':retained,
                'cover_removed_mm3':removed,'cover_added_mm3':added,'root_removed_mm3':rootremoved,
                'cover_original_material_removed_outside_KEY_motion_mm3':outside,'protected_plate_removed_mm3':protected_removed,'protected_plate_added_mm3':protected_added,
                'cover_original_bounds_eqr_mm':n.bounds(side,oldcover),'cover_new_bounds_eqr_mm':n.bounds(side,cover),'cover_q_min_growth_mm':2.1,
                'whole_bench_bounds_delta_mm':delta,'native_subset_separation_proof':proof,'new_cover_single_positive_solid':True,'new_root_single_positive_solid':True})
        assembly_results=[]
        if a.assembly:
            source=json.loads(a.assembly.read_text());inputs[str(a.assembly)]=sha(a.assembly)
            for item in source['STEP_exports']:
                p=a.assembly.parent/item['path']
                if not p.resolve().is_relative_to(a.assembly.parent.resolve()) or sha(p)!=item['sha256']:raise ValueError('assembly STEP identity mismatch')
                leaves,volume=whole_material(load_step(p));inputs[str(p)]=sha(p)
                if len(leaves)!=item['expected_part_count'] or len(leaves)!=46:raise ValueError('complete assembly leaf count differs')
                if p.name.startswith('STOW'):
                    refs={side+'_'+name:current[side+'_'+name] for side in 'LR' for name in PARTS}
                elif p.name.startswith('OPEN'):
                    path='assembly/OPEN_ROOT_SPLIT_ASSEMBLED.step'
                    with tarfile.open(arc,'r:gz') as ar:b=ar.extractfile(path).read()
                    if hashlib.sha256(b).hexdigest()!=files[path]['sha256']:raise ValueError('old OPEN hash differs')
                    f=Path(td)/'old-open.step';f.write_bytes(b);previous_leaves,_=whole_material(load_step(f));refs={'old_OPEN_'+str(i):s for i,s in enumerate(previous_leaves)}
                else:raise ValueError('unknown assembly pose')
                used=set()
                for name,ref in refs.items():
                    bb=ref.BoundingBox();matches=[i for i,l in enumerate(leaves) if abs(l.Volume()-ref.Volume())<=1e-7 and all(abs(getattr(l.BoundingBox(),k)-getattr(bb,k))<=1e-7 for k in FIELDS)]
                    if len(matches)!=1 or matches[0] in used:raise ValueError('assembly matching missing or ambiguous: '+name)
                    i=matches[0];used.add(i);match_eq(leaves[i],ref,name)
                if len(used)!=46:raise ValueError('assembly contains unchecked material')
                assembly_results.append({'path':p.name,'valid_positive_leaves':46,'bijectively_compared_leaves':len(used),'signed_volume_mm3':volume})
            if len(assembly_results)!=2:raise ValueError('both STOW and OPEN assemblies required')
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('input bytes changed during reimport')
    forbidden=('keycover_bypass','stow_contact_slots','stow_continuous_slots','stow_motion_slots','stow_web_repair','split_root_cartridges')
    if any(name.startswith(forbidden) for name in sys.modules):raise ValueError('candidate or scene builder imported')
    result={'host':platform.node(),'verifier_sha256':sha(__file__),'producer_sha256':a.expected_sha256,'inputs_SHA256':inputs,'inputs_unchanged':True,
        'complete_STEP_files_read':76,'unchanged_nonmodified_parts':unchanged,'unchanged_parts_compared':42,'sides':rows,
        'actual_pose_negative_controls':negative,'assembly_reimports':assembly_results,'builder_imported':False,
        'same_CAD_kernel_not_cross_engine':True,'old_cover_box_bound_must_change_not_hidden':True,'actual_phone_cavity_fit_unknown':True,
        'strength_tolerances_fixture_or_manufacturing_qualified':False,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PASS: full cover material / 42 unchanged parts / old actual collisions / bounded separation',flush=True)

if __name__=='__main__':main()
