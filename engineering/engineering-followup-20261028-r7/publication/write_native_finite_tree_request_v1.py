"""Bind immutable local native evidence to reviewable remote Git tree entries."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'r7-publication/native-finite-checkpoint-v1'
PREFIX = 'engineering/engineering-followup-20261028-r7/'
PARENT = '8bb6f52b624cd40a0570f8710f140bb5a0abf96f'
BASE_TREE = '5081698dbb0b73047270b389aec554575f35ba83'

def identity(p):
    d = p.read_bytes()
    return {'bytes':len(d), 'sha256':hashlib.sha256(d).hexdigest(),
            'git_blob_sha':hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()}

def main():
    target = ROOT / 'r7-publication/R7_NATIVE_FINITE_GIT_TREE_REQUEST_V1.json'
    assert not target.exists()
    plan = json.loads((CHECK/'PLAN.json').read_text())
    parts = json.loads((CHECK/'EXACT_ZIP_TRANSPORT_PARTS_V1.json').read_text())
    actual = json.loads((CHECK/'ACTUAL.json').read_text())
    assert actual['completed'] and actual['all_input_bytes_unchanged'] and parts['concatenation_exact_bytes_verified']
    known_raw = (ROOT/'r7-publication/base_HEAD_git_tree_records.bin').read_bytes().split(b'\0')
    known = {x.split(b'\t',1)[0].split()[2].decode() for x in known_raw if x}
    prior = json.loads((ROOT/'r7-publication/R7_ENVELOPE_RUNTIME_PUBLICATION_MANIFEST_V1.json').read_text())
    known.update(r['git_blob_sha'] for r in prior['files'])
    known.update(p['git_blob_sha'] for p in parts['parts'])
    selected = {}
    for r in plan['files']:
        p = Path(r['local_path']); now = identity(p)
        assert now == {'bytes':r['bytes'],'sha256':r['sha256'],'git_blob_sha':r['original_git_blob_sha']}
        if r['representation'] == 'individual_original_file':
            selected[r['repository_path']] = p
    for r in parts['parts']:
        p = Path(r['path'])
        assert identity(p) == {k:r[k] for k in ('bytes','sha256','git_blob_sha')}
        selected[r['repository_path']] = p
    for local, remote in (
        (CHECK/'PLAN.json', 'native/PUBLIC_NATIVE_ORIGINALS_PLAN_V1.json'),
        (CHECK/'ACTUAL.json', 'native/PUBLIC_NATIVE_ORIGINALS_ACTUAL_V1.json'),
        (CHECK/'EXACT_ZIP_TRANSPORT_PARTS_V1.json', 'native/EXACT_ZIP_TRANSPORT_PARTS_V1.json'),
        (ROOT/'r7-publication/reassemble_native_evidence_zip_v1.py', 'native/reassemble_native_evidence_zip_v1.py'),
        (ROOT/'r7-publication/NATIVE_CHECKPOINT_TRANSPORT_V1.md', 'native/TRANSPORT.md'),
        (ROOT/'r7-publication/R7_NATIVE_PUBLICATION_TRANSPORT_ATTEMPT1_ACTUAL_FAILURE_V1.json', 'publication/R7_NATIVE_PUBLICATION_TRANSPORT_ATTEMPT1_ACTUAL_FAILURE_V1.json'),
        (Path(__file__), 'publication/write_native_finite_tree_request_v1.py'),
    ):
        selected[PREFIX+remote] = local
    rows=[]; elements=[]
    for dest,p in sorted(selected.items()):
        ident=identity(p); rows.append({'repository_path':dest,'local_path':str(p),**ident})
        e={'path':dest,'type':'blob','mode':'100644'}
        if ident['git_blob_sha'] in known:
            e['sha']=ident['git_blob_sha']
        else:
            text=p.read_text(); assert '\0' not in text
            e['content']=text
        elements.append(e)
    manifest={'schema':'razr-r7-native-finite-git-publication-manifest-v1','parent_commit':PARENT,
              'base_tree':BASE_TREE,'files':rows,'selected_complete_original_count':len(plan['files']),
              'new_scientific_execution':False,'only_new_R7_paths_added':True,
              'workflows_or_RUN_REQUEST_modified':False,'exact_a11_requested_push_fulfilled':False,
              'full_continuous_G2':False,'all_blockers_closed':False}
    text=json.dumps(manifest,indent=2)+'\n'
    (ROOT/'r7-publication/R7_NATIVE_FINITE_PUBLICATION_MANIFEST_V1.json').write_text(text)
    elements.append({'path':PREFIX+'R7_NATIVE_FINITE_PUBLICATION_MANIFEST_V1.json','mode':'100644','type':'blob','content':text})
    request={'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':BASE_TREE,'tree_elements':elements}
    encoded=json.dumps(request,ensure_ascii=True,separators=(',',':'))+'\n'
    assert len(encoded.encode()) < 14*1024*1024
    target.write_text(encoded)
    print(json.dumps({'request_bytes':target.stat().st_size,'request_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                      'tree_entries':len(elements),'new_text_entries':sum('content' in e for e in elements),
                      'existing_blob_entries':sum('sha' in e for e in elements),'parent_commit':PARENT,'base_tree':BASE_TREE,
                      'branch_mutated':False}))

if __name__ == '__main__':
    main()
