"""Re-evaluate all 130 pinned motion-envelope pairs after sole cover subtraction.
Does not claim forces or fixture release; does not rerun old sampled sequences.
"""
from pathlib import Path
import argparse,hashlib,json,tarfile,tempfile,gzip,platform,sys
import cam_contact_native as n

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True,type=Path);ap.add_argument('--admission',required=True,type=Path);ap.add_argument('--sha256',required=True);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
    if sha(a.admission)!=a.sha256:raise ValueError('admission input changed')
    current=json.loads(a.admission.read_text());root=a.repo/'engineering/keycover-geometry-20261014';index=json.loads((root/'raw-receipt-index.json').read_text());receipt_path='native/motion130.json.gz';entry=next(x for x in index['files'] if x['path']==receipt_path);b=gzip.decompress((root/receipt_path).read_bytes())
    if hashlib.sha256(b).hexdigest()!=entry['original_sha256']:raise ValueError('prior motion receipt changed')
    motion=json.loads(b);manifest=json.loads((root/'geometry-manifest.json').read_text());archive=root/'project-owned-geometry.tar.gz'
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('prior geometry archive changed')
    entries={x['path']:x for x in manifest['files']};shapes={};pairs=[];changed=[];inputs={str(a.admission):sha(a.admission),str(archive):sha(archive)}
    with tempfile.TemporaryDirectory() as tmp,tarfile.open(archive,'r:gz') as tar:
        for role,item in motion['exports'].items():
            member='motion/'+item['path'];data=tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=entries[member]['sha256']:raise ValueError('prior STEP member changed')
            p=Path(tmp)/item['path'];p.write_bytes(data);shapes[role]=n.single(n.cq.importers.importStep(str(p)).val())
        for side in 'LR':
            role=side+'_OLD_COVER';item=current['exports'][role];p=a.admission.parent/item['path']
            if sha(p)!=item['sha256']:raise ValueError('new cover changed')
            cover=n.single(n.cq.importers.importStep(str(p)).val());old=shapes[role];added=n.whole_material(cover.cut(old),empty=True)[1];removed=n.whole_material(old.cut(cover),empty=True)[1]
            if added>1e-7 or abs(removed-.04416)>1e-7:raise ValueError('new cover is not the certified subtraction')
            shapes[role]=cover;inputs[str(p)]=sha(p);changed.append({'side':side,'added_mm3':added,'removed_mm3':removed,'strict_subset':True})
        for row in motion['rows']:
            side=row['side'];get=lambda name:shapes[side+'_'+name]
            def pair(kind,a,b):
                v=n.common(get(a),get(b));pairs.append({'side':side,'kind':kind,'a':a,'b':b,'common_mm3':v})
                if v>1e-7:raise ValueError('new motion interference')
            for c in row['contacts']:
                i=c['stop'];pair('PIN_KEY',f'PIN_{i}_COMPLETE_PATH','KEY')
                for j in range(3):pair('REMAINDER_KEY',f'STOP_{i}_REST_CAGE_{j}','KEY')
                for name in c['complete_STOP_fixed_pairs']:pair('STOP_FIXED',f'STOP_{i}_COMPLETE_R',name)
            for name in row['full_KEY_fixed_pairs']:pair('KEY_FIXED','KEY_COMPLETE_Q',name)
            pair('STOP_STOP','STOP_0','STOP_1')
    if len(pairs)!=130:raise ValueError('pair coverage differs')
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('input mutated')
    if any(s.startswith(('cover_locator_slot','keycover_bypass','stow_contact_slots')) for s in sys.modules):raise ValueError('candidate builder imported')
    result={'host':platform.node(),'source_sha256':sha(__file__),'inputs_SHA256':inputs,'inputs_unchanged':True,'pairs':pairs,'pair_count':130,'positive_pairs':0,'cover_changes':changed,'builder_imported':False,'same_CAD_kernel':True,'old_564_184_sampled_runs_repeated':False,'all_noncover_native_shapes_unchanged':True,'prior_restoring_force_assumption_unchanged':True,'locator_capture_stiffness_and_real_fixture_qualified':False,'candidate_go':False,'manufacturing_go':False}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PASS:130 existing motion-envelope pairs, only certified cover subtraction')
if __name__=='__main__':main()
