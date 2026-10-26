"""Exact science allowlist; no native/runtime/source-identity collections."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def check_no_runtime_locator(value):
    if isinstance(value,str):
        if any(x in value for x in ('/workspace/','/home/','/tmp/','libfile_','oai-library:')) or re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',value):
            raise ValueError('non-scientific runtime locator in proposed projection')
    elif isinstance(value,list):
        for x in value:check_no_runtime_locator(x)
    elif isinstance(value,dict):
        for k,x in value.items():check_no_runtime_locator(k);check_no_runtime_locator(x)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',type=Path,required=True);ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    out=args.output;out.mkdir(exist_ok=False)
    raw=args.case/'capacity/worker/science';rejected=[]
    pattern=re.compile(r'call-[0-9]{6}(?:\.json|-[a-z0-9_-]+\.brep)\Z')
    if raw.is_dir():
        for p in sorted(raw.iterdir()):
            if p.name.endswith('.partial'):continue
            assert p.is_file() and not p.is_symlink()
            assert p.name in ('report.json','pair-inventory.json','INDEPENDENT_CAPACITY_RECORD_CHECK.json') or pattern.fullmatch(p.name)
            if p.suffix=='.json':
                try:check_no_runtime_locator(json.loads(p.read_text()))
                except Exception:
                    rejected.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'reason':'runtime_locator_or_invalid_JSON_not_exported'})
                    continue
            shutil.copyfile(p,out/p.name)
    source_names=('run_capacity_v4.py','supervise_capacity_v4.py','capacity_stage_v4.py','full_slide_api_v4.py',
                  'envelope_v2.py','correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py',
                  'K1_BINDING.json','read_capacity_v4.py','export_capacity_v4.py','check_capacity_stage.py')
    for n in source_names:
        p=args.sources/n
        if p.is_file() and not p.is_symlink():shutil.copyfile(p,out/('source-'+n))
    for name in ('V4_SOURCE_IDENTITY.json','V4_K1_PREREQUISITES_VERIFIED.json'):
        p=args.case/name
        if p.is_file():
            check_no_runtime_locator(json.loads(p.read_text()));shutil.copyfile(p,out/name)
    controller=args.case/'capacity/controller.json'
    if controller.is_file():
        r=json.loads(controller.read_text())
        allowed=('completed','worker_started','worker_exit_code','owned_child_identity_verified','source_bytes_unchanged',
                 'locked_environment_unchanged','owned_channel_descriptors_closed','reported_execution_completed',
                 'all_original_postguards_passed','limits','resource_start_refused','capacity_or_wall_stop','elapsed_seconds')
        record={k:r.get(k) for k in allowed};check_no_runtime_locator(record)
        record.update(original_controller_sha256=sha(controller),original_controller_bytes=controller.stat().st_size,
                      raw_runtime_exported=False,is_original_record=False)
        (out/'CONTROLLER_OUTCOME.json').write_text(json.dumps(record,indent=2)+'\n')
    (out/'EXPORT_SCOPE.json').write_text(json.dumps({'schema':'razr-V4-science-export-v1','raw_runtime_exported':False,
        'private_runtime_durable_preservation_claimed':False,'omitted_unreviewed_JSON':rejected,
        'complete_product_qualification':False},indent=2)+'\n')
    manifest={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return 0 if not rejected else 2


if __name__=='__main__':raise SystemExit(main())
