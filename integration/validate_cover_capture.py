"""Reimport candidate roots and check cover capture, old motions, and jaw release.
Uses generic geometry only, no candidate or scene generator. Tests nominal
straight uplift, not general 6-DOF form closure, material strength, or phone fit.
"""
from pathlib import Path
import argparse,hashlib,json,gzip,tarfile,tempfile,itertools,sys,platform,time
import cam_contact_native as n
from translation_regions import regions,checks
from verify_contact_motion import PARTS
FIELDS=('xmin','xmax','ymin','ymax','zmin','zmax')
ROOTS=('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbox(sh):return {k:getattr(sh.BoundingBox(),k) for k in FIELDS}
def read_step(p):
    vals=n.cq.importers.importStep(str(p)).vals()
    if len(vals)!=1:raise ValueError('unaccounted native STEP roots')
    return n.single(vals[0])
def difference(a,b):return n.whole_material(a.cut(b),empty=True)[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True,type=Path);ap.add_argument('--candidate',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();out=a.output.resolve()
    if out==a.repo.resolve() or a.repo.resolve() in out.parents:raise ValueError('use new external output folder')
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    phase=a.repo/'engineering/cover-assembly-order-20261014';archive=phase/'bench-geometry.tar.gz'
    gm=json.loads((phase/'geometry-manifest.json').read_text());assert sha(archive)==gm['archive_sha256']
    files={x['path']:x for x in gm['files']};inputs={str(archive):sha(archive),str(a.candidate/'manifest.json'):sha(a.candidate/'manifest.json')}
    cache={}
    def oldshape(name):
        if name in cache:return cache[name]
        info=files[name]
        with tarfile.open(archive,'r:gz') as t:b=t.extractfile(name).read()
        if len(b)!=info['bytes'] or hashlib.sha256(b).hexdigest()!=info['sha256']:raise ValueError('baseline member changed')
        with tempfile.TemporaryDirectory(prefix='capture-native-read-') as td:
            p=Path(td)/'shape.step';p.write_bytes(b);cache[name]=read_step(p)
        return cache[name]
    manifest=json.loads((a.candidate/'manifest.json').read_text());candidate={};keepers={};materials=[]
    expected={side+'_'+name+suffix for side in 'LR' for name in ROOTS for suffix in ('','_CHANNEL')}
    if set(manifest['exports'])!=expected:raise ValueError('candidate participant set differs')
    for role,x in manifest['exports'].items():
        p=a.candidate/x['path']
        if p.parent!=a.candidate or sha(p)!=x['sha256']:raise ValueError('candidate bytes changed')
        inputs[str(p)]=sha(p);sh=read_step(p)
        if abs(sh.Volume()-x['volume_mm3'])>1e-7 or any(abs(bbox(sh)[k]-v)>1e-7 for k,v in x['bounds_mm'].items()):raise ValueError('native export mismatch')
        (keepers if role.endswith('_CHANNEL') else candidate)[role]=sh
    def current(side,name):
        return candidate.get(side+'_'+name) or oldshape('cover-first/'+side+'_'+name+'.step')
    def components(side,name):
        old=oldshape('cover-first/'+side+'_'+name+'.step')
        return [old,keepers[side+'_'+name+'_CHANNEL']] if name in ROOTS else [old]
    for side in 'LR':
        for name in ROOTS:
            before=oldshape('cover-first/'+side+'_'+name+'.step');after=current(side,name);ch=keepers[side+'_'+name+'_CHANNEL']
            loss=difference(before,after);addition=difference(after,before);join=n.common(before,ch)
            if loss>1e-7 or difference(after,before.fuse(ch))>1e-7 or difference(before.fuse(ch),after)>1e-7 or join<=1e-7:raise ValueError('root/channel material not complete or joined')
            delta={k:bbox(after)[k]-bbox(before)[k] for k in FIELDS}
            if any(abs(v)>1e-7 for v in delta.values()):raise ValueError('new root envelope expanded')
            materials.append({'side':side,'root':name,'original_removed_mm3':loss,'added_mm3':addition,'positive_joint_overlap_mm3':join,'bounds_delta_mm':delta})
    regioncache={}
    def travel(side,name,vector):
        key=(side,name,tuple(vector))
        if key not in regioncache:regioncache[key]=[x for part in components(side,name) for x in regions(part,vector)[0]]
        return regioncache[key]
    def path(side,moving,vector,fixed):
        if moving.startswith('ROOT_') and fixed not in ('OLD_COVER','JAW_LOWER','JAW_UPPER'):
            swept=travel(side,fixed,tuple(-x for x in vector));targets=components(side,moving)
        else:swept=travel(side,moving,vector);targets=components(side,fixed)
        v=[x for target in targets for x in checks(swept,target)['region_common_mm3']]
        return {'maximum_region_common_mm3':max(v,default=0.),'positive_region_count':sum(x>1e-7 for x in v),'regions_checked':len(v)}
    orderfile=phase/'native/cover-first-22-stages-130-pairs.json.gz';motionfile=phase/'native/motion130.json.gz'
    inputs[str(orderfile)]=sha(orderfile);inputs[str(motionfile)]=sha(motionfile)
    order=json.loads(gzip.decompress(orderfile.read_bytes()));motion=json.loads(gzip.decompress(motionfile.read_bytes()))
    stagechecks=[];motionchecks=[];static=[];release=[];capture=[];reservations=[]
    for side in 'LR':
        installed={'JAW_LOWER'};rows=[x for x in order['stages'] if x['side']==side]
        if len(rows)!=11:raise ValueError('baseline stage coverage differs')
        for row in rows:
            if set(row['fixed_names'])!=installed:raise ValueError('installed participant coverage differs')
            moving=row['moving']
            if moving.startswith('JOIN_DRIVER'):
                for fixed in sorted(installed):stagechecks.append({'side':side,'stage':row['stage'],'fixed':fixed,'maximum_region_common_mm3':n.common(current(side,moving),current(side,fixed))})
            else:
                vector=row['start_translation_world_mm']
                for fixed in sorted(installed):stagechecks.append({'side':side,'stage':row['stage'],'fixed':fixed,**path(side,moving,vector,fixed)})
                installed.add(moving)
        # Re-use the exact frozen motion enclosures because KEY, STOP, PAWL and
        # all their paths are unchanged; recompute EVERY one of the 130 pairs.
        row=next(x for x in motion['rows'] if x['side']==side)
        for contact in row['contacts']:
            i=contact['stop'];names=[(f'PIN_{i}_COMPLETE_PATH','KEY')]+[(f'STOP_{i}_REST_CAGE_{j}','KEY') for j in range(3)]
            names += [(f'STOP_{i}_COMPLETE_R',k) for k in contact['complete_STOP_fixed_pairs']]
            for shape,fixed in names:motionchecks.append({'side':side,'moving_proof':shape,'fixed':fixed,'common_mm3':n.common(oldshape('motion/'+side+'_'+shape+'.step'),current(side,fixed))})
        for fixed in row['full_KEY_fixed_pairs']:
            body=oldshape('motion/'+side+'_'+fixed+'.step') if fixed.startswith('SPRING_') and fixed.endswith('_MAX_NOMINAL_OCCUPANCY') else current(side,fixed)
            motionchecks.append({'side':side,'moving_proof':'KEY_COMPLETE_Q','fixed':fixed,'common_mm3':n.common(oldshape('motion/'+side+'_KEY_COMPLETE_Q.step'),body)})
        motionchecks.append({'side':side,'moving_proof':'STOP_0','fixed':'STOP_1','common_mm3':n.common(current(side,'STOP_0'),current(side,'STOP_1'))})
        p={name:current(side,name) for name in PARTS}
        for aa,bb in itertools.combinations(sorted(p),2):static.append({'side':side,'parts':[aa,bb],'common_mm3':n.common(p[aa],p[bb])})
        # Jaws are withdrawn after nominal complete assembly; tool bodies have
        # already been removed. No live hardware is operated by this program.
        fixed=set(PARTS)|{'JAW_LOWER'}
        for jaw,vec in [('JAW_UPPER',(0,0,3)),('JAW_LOWER',(0,0,-3))]:
            fixed.discard(jaw)
            for name in sorted(fixed):release.append({'side':side,'moving':jaw,'fixed':name,**path(side,jaw,vec,name)})
        cover=p['OLD_COVER'];oldfixed={k:oldshape('cover-first/'+side+'_'+k+'.step') for k in PARTS if k!='OLD_COVER'}
        lift_regions,_=regions(cover,(0,0,1.))
        oldpath={k:checks(lift_regions,v) for k,v in oldfixed.items()}
        if not all(v['all_regions_clear'] for v in oldpath.values()):raise ValueError('old nominal 1 mm uplift control not established')
        contactdist=[]
        for name in ROOTS:
            channel=keepers[side+'_'+name+'_CHANNEL']
            gap=cover.distance(channel)
            low=n.common(cover.translate((0,0,.019)),channel);high=n.common(cover.translate((0,0,.05)),channel)
            if abs(gap-.02)>1e-7 or low>1e-7 or high<=1e-7:raise ValueError('keeper gap/catch differs')
            contactdist.append({'root':name,'gap_mm':gap,'lift_019_common_mm3':low,'lift_050_common_mm3':high})
        capture.append({'side':side,'old_continuous_1mm_uplift_against_all_22_parts_clear':True,'old_path':oldpath,'new_straight_uplift_stops':contactdist,'arbitrary_rotation_or_friction_force_capture_qualified':False})
        assembly=n.cq.Compound.makeCompound(list(p.values()));oldassembly=n.cq.Compound.makeCompound(list(oldfixed.values())+[cover])
        reservations.append({'side':side,'bounds_world_mm':bbox(assembly),'bounds_local_eqr_mm':n.bounds(side,assembly),'change_from_prior_bench_mm':{k:bbox(assembly)[k]-bbox(oldassembly)[k] for k in FIELDS},'prior_extra_local_q_mm':3.5,'registered_to_finished_A_B_cavity':False})
        n.cq.exporters.export(assembly,str(out/(side+'_RETAINED_BENCH_ASSEMBLY.step')))
        print(side,'nominal uplift control and new keeper checks complete',flush=True)
    if len(stagechecks)!=130 or len(motionchecks)!=130 or len(static)!=506 or len(release)!=94:raise ValueError('incomplete audit coverage')
    bad=[x for x in stagechecks+release if x['maximum_region_common_mm3']>1e-7]+[x for x in motionchecks+static if x['common_mm3']>1e-7]
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('native inputs changed')
    if any(x.startswith(('cover_capture','cover_admission','keycover_bypass')) for x in sys.modules):raise ValueError('candidate generator imported')
    report={'host':platform.node(),'verifier_sha256':sha(__file__),'input_sha256':inputs,'input_bytes_unchanged':True,'material':materials,
            'assembly_stages':22,'assembly_pairs':stagechecks,'motion_pairs':motionchecks,'static_pairs':static,'jaw_release_pairs':release,'capture':capture,'space_reservations':reservations,
            'positive_clearance_checks':bad,'all_declared_nominal_checks_passed':not bad,'old_motion_proof_envelopes_reused_not_regenerated':True,'candidate_builder_imported':False,
            'same_CAD_kernel_not_cross_engine':True,'tolerance_budget_for_positive_top_gap_mm':.02,
            'force_deflection_fatigue_arbitrary_motion_or_hardware_qualified':False,'finished_cavities_and_mount_transform_available':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('RESULT',len(stagechecks),len(motionchecks),len(static),len(release),'BAD',len(bad),flush=True)
    if bad:raise SystemExit(1)
if __name__=='__main__':main()
