"""Exact L5 science allowlist and one reviewed archive-locator projection.

Unknown names/locators remain red and are never copied. Already accepted
scientific members and a complete manifest survive any such rejection.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
from l5_science_contract import scientific_filename

SOURCE_NAMES=('run_l5.py','supervise_l5.py','cylindrical_sweep_l5.py','exact_xy_support_l5.py',
 'test_l5_native.py','check_l5_plan.py','l5_science_contract.py','read_l5_native.py','read_l5_records.py',
 'export_l5.py','test_export_l5.py','capacity_stage_v4.py','full_slide_api_v4.py','envelope_v2.py',
 'correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py','K1_BINDING.json','L5_ORIGINAL_SEVEN_BINDING.json')
ARCHIVE_SHA='249f50dae36b591df189e17ed8f46b1d1e793d481b1d0fb57f0ff1a553dfbd07'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def no_runtime(value):
    if isinstance(value,float) and not math.isfinite(value):
        raise ValueError('nonfinite scientific JSON')
    if isinstance(value,str):
        if any(x in value for x in ('/workspace/','/home/','/tmp/','libfile_','oai-library:')) or re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',value):
            raise ValueError('unreviewed runtime locator')
    elif isinstance(value,list):
        for item in value:no_runtime(item)
    elif isinstance(value,dict):
        for key,item in value.items():no_runtime(key);no_runtime(item)


def project_producer(value,root):
    result=copy.deepcopy(value);omitted=[]
    location=('construction','current_candidate_factory_metadata','research_relief','KEY_source','original_complete_KEY_source')
    node=result
    for key in location:
        if not isinstance(node,dict) or key not in node:
            no_runtime(result);return result,omitted
        node=node[key]
    if 'archive' in node:
        manifest=root/'engineering/cam-coupling-20261015/geometry-v5-manifest.json'
        archive=manifest.parent/json.loads(manifest.read_text())['archive']
        raw=node['archive']
        if raw!=str(archive) or node['archive_sha256']!=ARCHIVE_SHA or sha(archive)!=ARCHIVE_SHA:
            raise ValueError('unreviewed archive locator identity')
        node['archive']=archive.relative_to(root).as_posix()
        omitted.append({'field':'.'.join(location)+'.archive','original_locator_utf8_sha256':hashlib.sha256(raw.encode()).hexdigest(),
            'original_locator_utf8_bytes':len(raw.encode()),'replacement_repository_relative_path':node['archive'],
            'archive_content_sha256':ARCHIVE_SHA,'only_absolute_container_locator_changed':True})
    no_runtime(result)
    return result,omitted


def execute(case,sources,out,root):
    out.mkdir(exist_ok=False);rejected=[];projected=[]
    roots=(case/'l5/worker/science',case/'native-reader/worker/science')
    for folder in roots:
        if not folder.is_dir():continue
        for path in sorted(folder.iterdir()):
            if path.name.endswith('.partial'):continue
            if path.is_symlink() or not path.is_file():
                rejected.append({'reason':'nonregular_or_symlink_not_exported'});continue
            record={'sha256':sha(path),'bytes':path.stat().st_size}
            if not scientific_filename(path.name):
                rejected.append({**record,'reason':'filename_not_in_frozen_scientific_allowlist'});continue
            if path.suffix=='.json':
                try:
                    value=json.loads(path.read_text())
                    if path.name=='report.json':
                        value,changes=project_producer(value,root)
                        if changes:
                            wrapper={'schema':'razr-L5-producer-engineering-projection-v1','derived_projection_not_raw_original':True,
                                'original':record,'runtime_locator_projection':changes,'engineering_record':value}
                            dest=out/'report.engineering.json'
                            if dest.exists():raise ValueError('duplicated public report')
                            dest.write_text(json.dumps(wrapper,indent=2,allow_nan=False)+'\n');projected.append({'file':dest.name,**record})
                            continue
                    no_runtime(value)
                except Exception:
                    rejected.append({**record,'reason':'unreviewed_runtime_locator_or_invalid_JSON_not_exported'});continue
            dest=out/path.name
            if dest.exists():
                rejected.append({**record,'reason':'duplicate_scientific_output_name_not_exported'});continue
            shutil.copyfile(path,dest)
    for name in SOURCE_NAMES:
        src=sources/name
        if src.is_file() and not src.is_symlink():shutil.copyfile(src,out/('source-'+name))
    for name in ('L5_SOURCE_IDENTITY.json','L5_INPUT_VERIFIED.json','L5_K1_PREREQUISITES_VERIFIED.json','L5_SOURCE_PLAN_RECHECK.json'):
        src=case/name
        if src.is_file():no_runtime(json.loads(src.read_text()));shutil.copyfile(src,out/name)
    for phase in ('l5','native-reader'):
        src=case/phase/'controller.json'
        if src.is_file():
            c=json.loads(src.read_text());keys=('completed','worker_started','worker_exit_code','owned_child_identity_verified',
                'source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed','reported_execution_completed',
                'all_original_postguards_passed','limits','resource_start_refused','capacity_or_wall_stop','elapsed_seconds','scope','worker_mode')
            projected_controller={k:c.get(k) for k in keys};no_runtime(projected_controller)
            projected_controller.update(original_controller_sha256=sha(src),original_controller_bytes=src.stat().st_size,raw_runtime_exported=False,is_original_record=False)
            (out/(phase+'-CONTROLLER_OUTCOME.json')).write_text(json.dumps(projected_controller,indent=2)+'\n')
    (out/'EXPORT_SCOPE.json').write_text(json.dumps({'schema':'razr-L5-science-export-v1','raw_runtime_exported':False,
        'private_runtime_durable_preservation_claimed':False,'rejected_items':rejected,'derived_producer_projections':projected,
        'complete_product_qualification':False,'unknown_filename_or_link_never_exported':True},indent=2)+'\n')
    manifest={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return 0 if not rejected else 2


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True)
    ap.add_argument('--sources',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--source-root',type=Path,default=Path(os.environ.get('GITHUB_WORKSPACE','.')).resolve())
    a=ap.parse_args();return execute(a.case,a.sources,a.output,a.source_root)

if __name__=='__main__':raise SystemExit(main())
