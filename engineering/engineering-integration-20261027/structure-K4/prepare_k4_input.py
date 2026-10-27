"""Stream-verify the immutable engineering ZIP and retain only bounded K4 inputs.

No native imports. Authentication is sent only to the official repository API,
never forwarded to the signed archive host. Existing local ZIP mode is a pure
transport control; hosted acquisition uses the pinned Actions artifact identity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def atomic(path,data):
    p=Path(path);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');t.replace(p)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def acquire(binding,target):
    require(not target.exists(),'input archive cannot overwrite an existing original')
    available=os.statvfs(target.parent);require(available.f_bavail*available.f_frsize>=2*2**30,'stricter hosted pre-download 2 GiB ordinary-disk reserve unavailable')
    token=os.environ.get('GH_READ_TOKEN');require(bool(token),'read-only workflow token required for its repository artifact')
    base='https://api.github.com/repos/'+binding['repository']+'/actions/artifacts/'+str(binding['artifact_id'])
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    with urllib.request.urlopen(urllib.request.Request(base,headers=headers),timeout=30) as f:
        meta=json.loads(f.read(2*2**20))
    require(meta['id']==binding['artifact_id'] and meta['name']==binding['artifact_name'] and not meta['expired'],'actual artifact metadata differs or expired')
    require(meta['workflow_run']['id']==binding['run_id'] and meta['workflow_run']['head_sha']==binding['head_sha'],'actual artifact run or source differs')
    digest=meta.get('digest');require(digest in (None,'sha256:'+binding['ZIP']['sha256']),'API archive digest differs from frozen science')
    opener=urllib.request.build_opener(NoRedirect())
    try:
        response=opener.open(urllib.request.Request(base+'/zip',headers=headers),timeout=30)
    except urllib.error.HTTPError as error:
        require(error.code==302,'official repository archive redirect unavailable')
        url=error.headers.get('Location','');u=urllib.parse.urlparse(url)
        require(u.scheme=='https' and u.username is None and u.password is None and u.port in (None,443),'unsafe signed archive redirect')
        require(u.hostname is not None and (u.hostname.endswith('.blob.core.windows.net') or u.hostname.endswith('.actions.githubusercontent.com')),'unregistered archive delivery host')
        # This fresh request has no Authorization header.
        response=urllib.request.urlopen(urllib.request.Request(url),timeout=30)
    start=time.monotonic();h=hashlib.sha256();count=0
    with response as f,target.open('xb') as output:
        while True:
            require(time.monotonic()-start<=300,'bounded input transport deadline reached')
            block=f.read(1024*1024)
            if not block:break
            count+=len(block);require(count<=binding['ZIP']['bytes'],'archive exceeded immutable byte limit')
            h.update(block);output.write(block)
    require(count==binding['ZIP']['bytes'] and h.hexdigest()==binding['ZIP']['sha256'],'complete original ZIP digest or bytes differ')
    return {'artifact_id':meta['id'],'run_id':meta['workflow_run']['id'],'head_sha':meta['workflow_run']['head_sha'],
        'artifact_name':meta['name'],'expires_at':meta.get('expires_at'),'immutable_ZIP_SHA_bytes_verified':True,
        'authentication_only_sent_to_official_repository_API':True,'seconds':time.monotonic()-start}


def verify_original(zip_path,binding,out=None):
    require(zip_path.stat().st_size==binding['ZIP']['bytes'] and sha(zip_path)==binding['ZIP']['sha256'],'original archive byte identity differs')
    selected={};prerequisites={};total=0
    with zipfile.ZipFile(zip_path) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        require(len(names)==len(set(names))==binding['regular_member_count'],'original regular member inventory differs')
        for info in infos:
            name=PurePosixPath(info.filename);mode=info.external_attr>>16
            require(not info.is_dir() and not name.is_absolute() and '..' not in name.parts and '\\' not in info.filename and str(name)==info.filename,'unsafe original ZIP path')
            require(not stat.S_ISLNK(mode) and not (info.flag_bits&1),'linked or encrypted original ZIP member prohibited')
        raw=z.read('ENGINEERING_MANIFEST.json')
        require(len(raw)==binding['manifest']['bytes'] and hashlib.sha256(raw).hexdigest()==binding['manifest']['sha256'],'original manifest identity differs')
        manifest=json.loads(raw);members=manifest['members']
        require(manifest['schema']==binding['manifest_schema'] and len(members)==binding['manifest_member_count'],'wrong original engineering manifest')
        require(set(names)==set(members)|{'ENGINEERING_MANIFEST.json'},'complete ZIP inventory must equal original manifest plus itself')
        for name,ref in members.items():
            info=z.getinfo(name);require(info.file_size==ref['bytes'],'original member byte declaration differs')
            h=hashlib.sha256();count=0;capture=name in binding['selected_original_members'] or name in binding['projected_prerequisite_reports'];data=bytearray() if capture else None
            with z.open(info) as stream:
                while True:
                    block=stream.read(1024*1024)
                    if not block:break
                    count+=len(block);h.update(block)
                    if capture:data.extend(block)
            # Reaching member EOF verifies ZipExtFile CRC, including all unselected
            # members. The same bytes are additionally checked by SHA256 and size.
            require(count==ref['bytes'] and h.hexdigest()==ref['sha256'],'original member SHA/bytes/CRC closure failed')
            total+=count
            if name in binding['selected_original_members']:
                require(ref==binding['selected_original_members'][name],'selected whole original differs')
                selected[name]=bytes(data)
            if name in binding['projected_prerequisite_reports']:
                require(ref==binding['projected_prerequisite_reports'][name],'frozen prerequisite projection differs')
                prerequisites[name]=json.loads(data)
        require(total+len(raw)==binding['uncompressed_bytes'],'original complete uncompressed byte count differs')
        obs=prerequisites['K3FULL-complete-observation.json']
        require(obs['pose']==binding['pose'] and obs['complete_full_pair_execution'] is True and obs['finite_state_clear'] is True and not obs['completion_failures'],'actual complete K3FULL state prerequisite not clear')
        projected={}
        for mode in ('factory','readback'):
            wrapper=prerequisites[mode+'/worker/report.engineering.json'];r=wrapper['engineering_record']
            require(wrapper['derived_projection_not_raw_original'] is True,'prior engineering projection must not be relabelled as raw report')
            require(r['functional_source_commit']==binding['functional_source_commit'] and r['pose']==binding['pose'],'prior source or pose differs')
            require(r['execution_completed'] is True and r['finite_pose_clear'] is True and len(r['participant_names'])==154 and len(r['pairs'])==11781,'prior complete whole factory pair result missing')
            require(not r['evaluation_failures'] and not r['mismatches_to_factory'],'prior native pair failures unresolved')
            projected[mode]={'original_raw_report_sha256':wrapper['original']['sha256'],
                'projected_engineering_member':mode+'/worker/report.engineering.json',
                'execution_completed':r['execution_completed'],'finite_pose_clear':r['finite_pose_clear'],
                'participant_count':154,'pair_count':11781,'candidate_name':r['candidate_name'],
                'candidate_source_sha256':r['candidate_source_sha256'],
                'projection_is_not_the_original_runtime_report':True}
        result={'schema':'razr-K4-original-input-stream-verification-v1','ZIP':binding['ZIP'],
            'engineering_manifest':binding['manifest'],'manifest_members_verified':len(members),'regular_members_verified':len(names),
            'uncompressed_bytes_verified':total+len(raw),'all_original_manifest_members_SHA_bytes_CRC_verified':True,
            'selected_whole_STEP_members':binding['selected_original_members'],'actual_prerequisite_projection':projected,
            'complete_factory_not_rerun':True,'independent_local_K4_native_run_not_performed_by_this_check':True}
        if out is not None:
            require(not out.exists(),'fresh input subset directory required');out.mkdir(parents=True)
            (out/'whole_STEP').mkdir()
            for name,data in selected.items():(out/'whole_STEP'/PurePosixPath(name).name).write_bytes(data)
            (out/'K3FULL_ENGINEERING_MANIFEST.json').write_bytes(raw)
            (out/'K3FULL-complete-observation.json').write_bytes(z.read('K3FULL-complete-observation.json'))
            atomic(out/'K4-input-verification.json',result)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True)
    ap.add_argument('--existing-zip',type=Path);ap.add_argument('--validate-only',action='store_true');a=ap.parse_args()
    b=json.loads((HERE/'K4_INPUT_BINDING.json').read_text());case=a.case.resolve();case.mkdir(parents=True,exist_ok=True)
    result={'schema':'razr-K4-input-acquisition-observation-v1','completed':False,'binding_sha256':sha(HERE/'K4_INPUT_BINDING.json')}
    try:
        archive=a.existing_zip or case/'original-K3FULL-stow3.zip'
        if a.existing_zip is None:result['transport']=acquire(b,archive)
        else:result['transport']={'existing_original_byte_verification_only':True}
        result['verification']=verify_original(archive,b,None if a.validate_only else case/'inputs')
        result['completed']=True
    except BaseException as error:
        result['failure']={'exception_type':type(error).__name__,'phase':'bounded_original_input_acquisition_or_byte_verification'}
        # Raw exception detail (which could contain a signed URL) is intentionally
        # kept only in the ephemeral private failure file, never engineering export.
        (case/'input-acquisition-private-error.txt').write_text(type(error).__name__+': '+str(error)+'\n')
    finally:atomic(case/'K4-input-acquisition.json',result)
    print(json.dumps({'input_complete':result['completed'],'failure':result.get('failure')},sort_keys=True))
    return 0 if result['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
