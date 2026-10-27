"""Build separately named L5c diagnosis; preserve frozen L5b resource/source guard prefix."""
from pathlib import Path
import argparse, ast, copy, hashlib, json, re, subprocess
import yaml

OLD_SHA="954e3fe1c0a039f24bc32eeef80e87ecb4225f51010292a482312bc880cd1333"
PARENT="690b1ed0df100fe175f5d6752b716105c0521a25"
BASE_TREE="40ed335630e030487d213104fb49a2c3af3b575b"
BRANCH="diagnostic/s4-l5c-extrusion-20261027"
NEW_FILES=("run_l5c.py","supervise_l5c.py","export_l5c.py","L5C_INPUT_BINDING.json","L5C_CAPACITY_PREREGISTRATION.json")
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,gate):
    if not ok:raise ValueError(gate)
def expr(text):return "$"+"{{ "+text+" }}"

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old-workflow",type=Path,required=True)
    ap.add_argument("--directory",type=Path,required=True)
    a=ap.parse_args();d=a.directory
    old_raw=a.old_workflow.read_bytes()
    require(sha(old_raw)==OLD_SHA,"frozen L5b workflow changed")
    old=yaml.safe_load(old_raw);w=copy.deepcopy(old)
    w["name"]="L5c exact preserved EXTRUSION operation diagnosis"
    w["on"]={"push":{"branches":[BRANCH]},"workflow_dispatch":None}
    w["concurrency"]={"group":"l5c-preserved-extrusion-"+expr("github.ref"),"cancel-in-progress":False}
    job=copy.deepcopy(old["jobs"]["original"]);steps=job["steps"]
    job["name"]="L5c preserved EXTRUSION and STEP operation diagnosis"
    payload={}
    for name in NEW_FILES:
        b=(d/name).read_bytes()
        if name.endswith(".py"):ast.parse(b)
        payload[name]={"content":b.decode(),"bytes":len(b),"sha256":sha(b)}
    install_code="""import hashlib,json,os,pathlib
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR'])
payload=json.loads(INLINE_JSON_LITERAL)
records={}
for name,row in payload.items():
 data=row['content'].encode('utf-8')
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
 for folder in (host/'l5',case/'source/l5'):
  path=folder/name
  with path.open('xb') as stream:stream.write(data)
 records[name]={'bytes':len(data),'sha256':row['sha256']}
receipt={'schema':'razr-L5c-frozen-diagnostic-source-byte-check-v1','sources':records,
 'old_L5b_workflow_commit':'690b1ed0df100fe175f5d6752b716105c0521a25',
 'unchanged_original_19_scientific_sources':True,'new_native_execution':False}
(case/'L5C_SOURCE_IDENTITY.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps({'L5c_exact_source_files':len(records),'installed_bytes':sum(x['bytes'] for x in records.values())}))
"""
    install_code=install_code.replace("INLINE_JSON_LITERAL",repr(json.dumps(payload,separators=(",",":"))))
    bind_step=copy.deepcopy(steps[2])
    bind_step["name"]="Bind unchanged S4 and L5 sources plus exact named L5c diagnostic sources"
    bind_step["run"] += "\n/usr/bin/python3 -B - <<'L5C_DIAGNOSTIC_SOURCES'\n"+install_code+"L5C_DIAGNOSTIC_SOURCES\n"
    download=copy.deepcopy(steps[6])
    download["name"]="Download exact preserved L5b scientific artifact only"
    download["with"].update({"artifact-ids":"12715683051","run-id":"40465353232",
        "path":expr("runner.temp")+"/razr-s4-k1-l5-cylindrical-20261026/l5b-original-download"})
    verify_code="""import hashlib,json,os,pathlib
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR']);src=(host/'l5b-original-download').resolve()
b=json.loads((host/'l5/L5C_INPUT_BINDING.json').read_text())
manifest=src/'MANIFEST.json';raw=manifest.read_bytes()
assert not manifest.is_symlink() and len(raw)==b['source_manifest_bytes'] and hashlib.sha256(raw).hexdigest()==b['source_manifest_sha256']
entries=json.loads(raw)
assert entries==b['source_manifest'] and len(entries)==68
assert {p.name for p in src.iterdir()}==set(entries)|{'MANIFEST.json'}
for name,row in entries.items():
 p=src/name;assert p.parent==src and p.is_file() and not p.is_symlink()
 raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
receipt={'schema':'razr-L5c-actual-input-member-byte-check-v1',
 'source_run_id':b['source_run_id'],'source_artifact_id':b['source_artifact_id'],
 'source_workflow_head':b['source_workflow_commit'],'source_archive_sha256':b['source_zip_sha256'],
 'source_manifest_sha256':b['source_manifest_sha256'],'verified_manifest_members':68,
 'verified_regular_members_including_manifest':69,'exact_member_set_passed':True,
 'all_actual_member_SHA_and_bytes_passed':True,'raw_runtime_exported':False,
 'whole_compressed_ZIP_bytes_hashed_on_this_runner':False,
 'compressed_ZIP_identity_was_independently_verified_before_freeze':True}
(case/'L5C_INPUT_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps(receipt))
"""
    verify={"name":"Verify complete preserved 68-member L5b scientific manifest and exact bytes",
        "shell":"bash","run":"set -euo pipefail\npython3 -B - <<'L5C_INPUT_VERIFY'\n"+verify_code+"L5C_INPUT_VERIFY\n"}
    native={"name":"Diagnose saved EXTRUSION and STEP operators under original owned limits","shell":"bash",
        "run":'set -euo pipefail\n/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/l5c-runner" .venv/bin/python -B "$HOST_ROOT/l5/supervise_l5c.py" --output "$CASE_DIR/l5c" --mode producer --scope original --inputs "$HOST_ROOT/l5b-original-download"\n'}
    export={"name":"Always retain exact failed operation science without raw runtime","if":"always()","shell":"bash",
        "run":'set -euo pipefail\npython3 -B "$HOST_ROOT/l5/export_l5c.py" --case "$CASE_DIR" --sources "$HOST_ROOT/l5" --output "$CASE_DIR/publish"\n'}
    upload=copy.deepcopy(steps[12]);upload["name"]="Retain L5c scoped diagnostic scientific originals"
    upload["with"]["name"]="S4-L5c-diagnostic-"+expr("github.run_id")+"-"+expr("github.run_attempt")
    job["steps"]=[*copy.deepcopy(steps[:2]),bind_step,*copy.deepcopy(steps[3:6]),download,verify,native,export,upload]
    w["jobs"]={"diagnostic":job}
    require(w["permissions"]==old["permissions"] and w["env"]==old["env"],"original permissions/host environment altered")
    require(job["timeout-minutes"]==40,"original job timeout altered")
    for ni,oi in ((0,0),(1,1),(3,3),(4,4),(5,5)):
        require(job["steps"][ni]==steps[oi],"unchanged host/resource/source prerequisite differs")
    require(bind_step["run"].startswith(steps[2]["run"]+"\n"),"original source transport or guard prefix changed")
    bash_count=0;python_count=0
    for step in job["steps"]:
        if "run" not in step:continue
        run=step["run"];subprocess.run(["bash","-n"],input=run,text=True,check=True,capture_output=True);bash_count+=1
        lines=run.splitlines();index=0
        while index<len(lines):
            line=lines[index];match=re.search(r"<<'([A-Za-z0-9_]+)'",line)
            if match and "python" in line:
                marker=match.group(1);end=index+1
                while end<len(lines) and lines[end]!=marker:end+=1
                require(end<len(lines),"unterminated Python heredoc")
                ast.parse("\n".join(lines[index+1:end]));python_count+=1;index=end
            index+=1
    raw=yaml.safe_dump(w,sort_keys=False,width=120,allow_unicode=False).encode()
    require(len(raw)<500000,"platform YAML 500KB gate")
    require(yaml.safe_load(raw)==w,"YAML roundtrip altered workflow")
    (d/"s4-l5c-extrusion-hosted.yml").write_bytes(raw)
    static={"schema":"razr-L5c-workflow-freeze-static-readback-v1","original_L5b_workflow_sha256":OLD_SHA,
        "functional_checkout_commit":"dd7def6e6a4de9f47dc91ca2ab336fb1a8828560",
        "parent_diagnostic_commit":PARENT,"base_tree":BASE_TREE,"branch":BRANCH,
        "new_workflow_sha256":sha(raw),"new_workflow_bytes":len(raw),"below_platform_500000_byte_limit":True,
        "native_gate_or_original_scientific_source_modified":False,
        "exact_original_host_source_guard_prefix_retained":True,
        "original_wall_RSS_memory_disk_child_source_and_locked_environment_limits_unchanged":True,
        "only_original_scope_diagnostic_no_seven_pair_jobs":True,"always_science_export_and_upload":True,
        "parsed_bash_blocks":bash_count,"parsed_inline_Python_blocks":python_count,
        "new_source_files":{n:{"bytes":r["bytes"],"sha256":r["sha256"]} for n,r in payload.items()},
        "actual_native_execution":False}
    (d/"L5C_STATIC_CHECK.json").write_text(json.dumps(static,indent=2)+"\n")
    print(json.dumps({"workflow_bytes":len(raw),"workflow_sha256":sha(raw),"bash_blocks":bash_count,
        "inline_Python_blocks":python_count,"native_executed":False}))

if __name__=="__main__":main()
