"""Prepare a reviewable L5b fallback: one inline binding, twenty fixed sources.

This is source transport and static validation only. It does not write Git refs,
invoke a native producer, import downloaded CAD code, or rerun original L1.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
import yaml

BASE_COMMIT="33386f1d6046aee80b0446b9c21fb7c259c3523a"
BASE_TREE="c03bdbd891ba22902ab070ca9ab4c5ccfe39909f"
OLD_SOURCE_COMMIT="b3c9bef2abe0d7065063bc966ec2083616286bd5"
OLD_WORKFLOW_SHA="b355abfd73e34d9096b806ba098c72f88409f3c9aea252059c5aed05fefc4348"
OLD_BINDING_SHA="fa5def368eb9d837ab31d8729d2ff5a5bb080b394392d228429f27375baf2fbf"
NEW_BINDING_SHA="7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2"
STAGE1_REQUEST_SHA="b9773dc610e30196957a71fea34f5daea9884e45a64473119924763a15554e4c"
STAGE1_REPLAY_SHA="db5cbc494212b0e0dffad651e707c8959524be1bdc744c687abaf1a07c7bd62f"
MARKER="L5A_PINNED_PUBLIC_SOURCE"
BRANCH="diagnostic/s4-k1-l5b-inline-cylindrical-20261027"
PREFIX="engineering/engineering-integration-20261026/envelope-L5b-inline/"
SOURCE_PREFIX="engineering/engineering-integration-20261026/envelope-L5/"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(ok,message):
    if not ok:
        raise ValueError(message)

def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")

def body_span(run,marker):
    start_token="<<'"+marker+"'\n"
    require(run.count(start_token)==1 and run.count("\n"+marker+"\n")==1,"unique original heredoc")
    start=run.index(start_token)+len(start_token)
    end=run.index("\n"+marker+"\n",start)
    return start,end

def make_install(expected,binding):
    public={k:copy.deepcopy(v) for k,v in expected.items() if k!="L5_ORIGINAL_SEVEN_BINDING.json"}
    require(len(public)==20 and sum(v["bytes"] for v in public.values())==193306,"twenty exact public files")
    # repr preserves every original UTF-8 byte without executing JSON as Python.
    lines=[
        "import hashlib,json,os,pathlib,time,urllib.request",
        "root=pathlib.Path(os.environ['HOST_ROOT'])/'l5'",
        "copy=pathlib.Path(os.environ['CASE_DIR'])/'source'/'l5'",
        "binding_name='L5_ORIGINAL_SEVEN_BINDING.json'",
        "binding_raw="+repr(binding.decode("utf-8"))+".encode('utf-8')",
        "if len(binding_raw)!=39348 or hashlib.sha256(binding_raw).hexdigest()!="+repr(NEW_BINDING_SHA)+":",
        "    raise ValueError('inline_complete_target_binding_bytes_differ')",
        "for parent in (root,copy):",
        "    with (parent/binding_name).open('xb') as stream:",
        "        stream.write(binding_raw)",
        "expected="+repr(public),
        "prefix="+repr("https://raw.githubusercontent.com/TrillionniumFoundation/RAZR-SLIDE/"+BASE_COMMIT+"/"+SOURCE_PREFIX),
        "class NoRedirect(urllib.request.HTTPRedirectHandler):",
        "    def redirect_request(self,req,fp,code,msg,headers,newurl):",
        "        raise ValueError('unexpected_public_source_redirect')",
        "opener=urllib.request.build_opener(NoRedirect)",
        "started=time.monotonic()",
        "total=0",
        "for name,row in expected.items():",
        "    if pathlib.Path(name).name!=name:",
        "        raise ValueError('invalid_fixed_source_basename')",
        "    req=urllib.request.Request(prefix+name,headers={'User-Agent':'RAZR-L5b-inline-source-readback'})",
        "    with opener.open(req,timeout=15) as response:",
        "        if response.status!=200 or response.geturl()!=prefix+name:",
        "            raise ValueError('unexpected_public_source_response')",
        "        raw=response.read(row['bytes']+1)",
        "    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:",
        "        raise ValueError('published_source_bytes_differ')",
        "    for parent in (root,copy):",
        "        with (parent/name).open('xb') as stream:",
        "            stream.write(raw)",
        "    total+=len(raw)",
        "print(json.dumps({'public_source_commit':"+repr(BASE_COMMIT)+",'verified_public_source_count':len(expected),'verified_public_download_bytes':total,'inline_binding_bytes':len(binding_raw),'inline_binding_sha256':hashlib.sha256(binding_raw).hexdigest(),'installed_source_count':len(expected)+1,'installed_source_bytes':total+len(binding_raw),'elapsed_public_download_seconds':time.monotonic()-started,'credentials_sent':False,'native_executed':False}))",
    ]
    result="\n".join(lines)
    ast.parse(result,feature_version=(3,10))
    return result,public

def create(old_bytes,binding,expected):
    require(len(old_bytes)==148236 and sha(old_bytes)==OLD_WORKFLOW_SHA,"immutable L5a workflow")
    require(len(binding)==39348 and sha(binding)==NEW_BINDING_SHA,"reviewed complete original binding")
    old=yaml.safe_load(old_bytes);new=copy.deepcopy(old)
    new["name"]="L5b unchanged native diagnostic with one verified inline original-target binding"
    new["on"]["push"]["branches"]=[BRANCH]
    new["concurrency"]={"group":"l5b-inline-whole-sections-${{ github.ref }}","cancel-in-progress":False}
    installer,public=make_install(expected,binding)
    old_bodies=[];footers=[]
    for key in ("original","current"):
        run=old["jobs"][key]["steps"][2]["run"]
        a,b=body_span(run,MARKER);old_body=run[a:b];old_bodies.append(old_body)
        require("timeout --signal=TERM --kill-after=5s 90s python3 -B - <<'"+MARKER+"'" in run,"original transport cap")
        suffix=run[b:]
        require(suffix.count(OLD_BINDING_SHA)==1 and suffix.count("25013")==1,"single original identity footer pin")
        new_suffix=suffix.replace(OLD_BINDING_SHA,NEW_BINDING_SHA).replace("25013","39348")
        changed=run[:a]+installer+new_suffix
        aa,bb=body_span(changed,MARKER)
        restored=changed[:aa]+old_body+changed[bb:].replace(NEW_BINDING_SHA,OLD_BINDING_SHA).replace("39348","25013")
        require(restored==run,"prepare change outside source installer and binding identity footer")
        new["jobs"][key]["steps"][2]["run"]=changed
        f0,f1=body_span(changed,"L5_SOURCE_CHECK")
        footers.append(changed[f0:f1])
    require(old_bodies[0]==old_bodies[1] and footers[0]==footers[1],"both jobs have same transport and footer")
    # Native programs, all other steps, process ownership and resource fields must
    # be exactly the old values. Only source installation and top-level names move.
    restored=copy.deepcopy(new)
    for k in ("name","on","concurrency"):
        restored[k]=copy.deepcopy(old[k])
    for key in ("original","current"):
        restored["jobs"][key]["steps"][2]=copy.deepcopy(old["jobs"][key]["steps"][2])
    require(restored==old,"unexpected workflow semantic change")
    require(new["jobs"]["current"]["needs"]==old["jobs"]["current"]["needs"],"original current-stage prerequisite")
    require(all(x["timeout-minutes"]==40 for x in new["jobs"].values()),"original job time limit")
    output=yaml.safe_dump(new,sort_keys=False,width=100,allow_unicode=True).encode()
    require(len(output)<500000,"500KB workflow size guard")
    reparsed=yaml.safe_load(output)
    require(reparsed==new,"generated YAML round trip")
    shell_count=inline_count=0
    for job in reparsed["jobs"].values():
        for step in job["steps"]:
            if "run" not in step:
                continue
            run=step["run"]
            subprocess.run(["bash","-n"],input=run.encode(),check=True)
            shell_count+=1
            lines=run.splitlines()
            for i,line in enumerate(lines):
                m=re.search(r"\bpython(?:3)?(?: -B)? - <<'([A-Za-z0-9_]+)'$",line)
                if m:
                    end=next(j for j in range(i+1,len(lines)) if lines[j]==m.group(1))
                    ast.parse("\n".join(lines[i+1:end])+"\n",feature_version=(3,10))
                    inline_count+=1
    require(shell_count==19 and inline_count==11,"all original bash and Python blocks")
    for key in ("original","current"):
        run=reparsed["jobs"][key]["steps"][2]["run"];a,b=body_span(run,MARKER)
        require(run[a:b]==installer,"generated workflow installer differs from tested code")
    return output,installer,footers[0],public,{"bash_blocks_parsed":shell_count,"inline_python_3_10_blocks_parsed":inline_count,
        "original_two_jobs_and_dependency_preserved":True,"all_other_job_fields_and_steps_exactly_unchanged":True,
        "prepare_prefix_and_suffix_unchanged_except_complete_binding_identity":True,
        "both_job_installer_bytes_identical_to_actual_tested_source":True,"workflow_under_500000_bytes":True}

def make_test_dirs(root):
    host=root/"host";case=root/"case"
    (host/"l5").mkdir(parents=True);(case/"source/l5").mkdir(parents=True)
    return host,case

def verify_transport(installer,footer,expected,output):
    installed={};checks=[]
    with tempfile.TemporaryDirectory(prefix="source-transport-control-",dir=output) as tmp:
        base=Path(tmp);host,case=make_test_dirs(base)
        env=dict(os.environ,HOST_ROOT=str(host),CASE_DIR=str(case),PYTHONDONTWRITEBYTECODE="1")
        command=["timeout","--signal=TERM","--kill-after=5s","90s",sys.executable,"-B","-c",installer]
        proc=subprocess.run(command,env=env,capture_output=True,timeout=100,check=False)
        require(proc.returncode==0,"bounded source installation failed")
        receipt=json.loads(proc.stdout)
        require(receipt["verified_public_source_count"]==20 and receipt["verified_public_download_bytes"]==193306 and
                receipt["installed_source_count"]==21 and receipt["installed_source_bytes"]==232654 and
                receipt["inline_binding_bytes"]==39348 and receipt["inline_binding_sha256"]==NEW_BINDING_SHA,
                "transport counters differ from exact payload")
        require(proc.stderr==b"","unexpected source installer diagnostic")
        for name,identity in expected.items():
            a=(host/"l5"/name).read_bytes();b=(case/"source/l5"/name).read_bytes()
            require(a==b and len(a)==identity["bytes"] and sha(a)==identity["sha256"],"two installed copies exact identity")
            installed[name]=a;checks.append({"name":name,**identity,"both_installed_copies_sha_and_bytes_verified":True})
        checked=subprocess.run([sys.executable,"-B","-c",footer],env=env,capture_output=True,timeout=15,check=False)
        require(checked.returncode==0 and checked.stderr==b"","original source footer rejected installed files")
        require(json.loads((case/"L5_SOURCE_IDENTITY.json").read_text())==expected,"original full source identity footer differs")
    # Test the exact new inline guard with one changed byte, before any network.
    module=ast.parse(installer)
    for node in module.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id=="binding_raw":
            value=node.value.func.value
            require(isinstance(value,ast.Constant) and isinstance(value.value,str),"known inline UTF-8 literal AST")
            value.value="["+value.value[1:]
            break
    else:
        raise ValueError("inline binding AST assignment missing")
    bad_inline=compile(ast.fix_missing_locations(module),"<mutated inline binding control>","exec")
    network_calls=[]
    old_opener=urllib.request.build_opener
    old_env={k:os.environ.get(k) for k in ("HOST_ROOT","CASE_DIR")}
    try:
        with tempfile.TemporaryDirectory(prefix="inline-negative-control-",dir=output) as tmp:
            host,case=make_test_dirs(Path(tmp))
            os.environ["HOST_ROOT"]=str(host);os.environ["CASE_DIR"]=str(case)
            def no_network(*args,**kwargs):
                network_calls.append("unexpected")
                raise AssertionError("unexpected network")
            urllib.request.build_opener=no_network
            try:
                exec(bad_inline,{})
            except ValueError as exc:
                require(str(exc)=="inline_complete_target_binding_bytes_differ","wrong negative-control gate")
            else:
                raise ValueError("mutated inline binding accepted")
            require(not network_calls and not list((host/"l5").iterdir()) and not list((case/"source/l5").iterdir()),
                    "invalid inline data wrote files or reached network")
        # Preserve the original public-source SHA gate with a same-length byte
        # mutation in the first source response. No network or native execution.
        public_calls=[]
        class Response:
            status=200
            def __init__(self,url):self.url=url
            def __enter__(self):return self
            def __exit__(self,*unused):return False
            def geturl(self):return self.url
            def read(self,n):
                name=self.url.rsplit("/",1)[1];data=installed[name]
                return (bytes([data[0]^1])+data[1:])[:n]
        class Opener:
            def open(self,req,timeout):
                public_calls.append(req.full_url)
                require(timeout==15,"original socket cap changed")
                return Response(req.full_url)
        urllib.request.build_opener=lambda *args,**kwargs:Opener()
        with tempfile.TemporaryDirectory(prefix="public-source-negative-control-",dir=output) as tmp:
            host,case=make_test_dirs(Path(tmp))
            os.environ["HOST_ROOT"]=str(host);os.environ["CASE_DIR"]=str(case)
            try:
                with redirect_stdout(io.StringIO()):
                    exec(compile(installer,"<mutated public-source response control>","exec"),{})
            except ValueError as exc:
                require(str(exc)=="published_source_bytes_differ","wrong source byte negative-control gate")
            else:
                raise ValueError("mutated public source accepted")
            require(len(public_calls)==1,"negative source control count")
            require({p.name for p in (host/"l5").iterdir()}=={"L5_ORIGINAL_SEVEN_BINDING.json"},"corrupt public source installed")
    finally:
        urllib.request.build_opener=old_opener
        for key,value in old_env.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    return {"schema":"razr-L5b-inline-source-transport-actual-control-v1","public_source_commit":BASE_COMMIT,
        "public_source_tree":BASE_TREE,"installer_sha256":sha(installer.encode()),"installer_bytes":len(installer.encode()),
        "actual_source_install_receipt":receipt,"installed_files":checks,
        "original_full_21_file_source_footer_actually_passed":True,
        "actual_fixed_public_source_downloads":20,"fixed_public_download_bytes":193306,
        "inline_binding_bytes":39348,"total_installed_source_bytes":232654,
        "inline_one_byte_mutation_rejected_before_network_and_write":True,
        "public_same_length_one_byte_mutation_rejected_by_original_SHA_gate":True,
        "negative_control_network_requests":0,"native_source_imported_or_executed":False,
        "original_L1_replay_rerun":False,"raw_runtime_downloaded_or_exported":False,
        "credentials_sent":False,"redirects_permitted":False,
        "original_source_install_cap_seconds":90,"source_install_SIGTERM_grace_seconds":5,
        "original_per_request_socket_timeout_seconds":15,
        "original_host_deadline_seconds":2220,"original_job_minutes":40,
        "existing_worker_wall_seconds":1800,"existing_worker_peak_RSS_MiB":1536,
        "native_or_geometry_pass_claimed":False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old-workflow",type=Path,required=True)
    ap.add_argument("--old-transport-binding",type=Path,required=True)
    ap.add_argument("--stage1-directory",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    request_path=args.stage1_directory/"L5B_BINDING_PUBLIC_TREE_REQUEST.json"
    request_bytes=request_path.read_bytes()
    require(len(request_bytes)==90896 and sha(request_bytes)==STAGE1_REQUEST_SHA,"retain exact stage-1 request")
    stage1=json.loads(request_bytes)
    require(stage1["base_tree_sha"]==BASE_TREE and len(stage1["tree_elements"])==5,"stage-1 original base and file set")
    binding=(args.stage1_directory/"L5_ORIGINAL_SEVEN_BINDING.json").read_bytes()
    replay=(args.stage1_directory/"L5A_TARGET_BINDING_PURE_REPLAY.json").read_bytes()
    require(sha(replay)==STAGE1_REPLAY_SHA,"preserved original pure replay")
    for item in stage1["tree_elements"]:
        local=args.stage1_directory/item["path"].rsplit("/",1)[1]
        require(local.read_bytes()==item["content"].encode(),"stage-1 entity bytes changed")
    transport=json.loads(args.old_transport_binding.read_text())
    require(transport["source_commit"]==OLD_SOURCE_COMMIT and transport["source_count"]==21,"original public source inventory")
    expected={r["name"]:{"sha256":r["sha256"],"bytes":r["bytes"]} for r in transport["source_files"]}
    require(expected["L5_ORIGINAL_SEVEN_BINDING.json"]=={"sha256":OLD_BINDING_SHA,"bytes":25013},"original binding source identity")
    expected["L5_ORIGINAL_SEVEN_BINDING.json"]={"sha256":NEW_BINDING_SHA,"bytes":39348}
    workflow,installer,footer,public,checks=create(args.old_workflow.read_bytes(),binding,expected)
    actual=verify_transport(installer,footer,expected,args.output)
    wf=args.output/"s4-k1-l5b-inline-cylindrical-hosted.yml";wf.write_bytes(workflow)
    install_path=args.output/"l5b_inline_source_install.py";install_path.write_text(installer+"\n")
    # The stored installer has one final newline. The embedded body is the same
    # executable source; retain both identities explicitly.
    actual["standalone_installer_sha256"]=sha(install_path.read_bytes())
    actual["standalone_installer_bytes"]=install_path.stat().st_size
    write_json(args.output/"L5B_INLINE_TRANSPORT_READBACK.json",actual)
    static={"schema":"razr-L5b-inline-fallback-static-check-v1","base_commit":BASE_COMMIT,"base_tree":BASE_TREE,
        "old_workflow_sha256":OLD_WORKFLOW_SHA,"old_workflow_bytes":148236,
        "new_workflow_sha256":sha(workflow),"new_workflow_bytes":len(workflow),**checks,
        "unchanged_native_source_files":17,"unchanged_other_public_files":3,
        "complete_original_binding_sha256":NEW_BINDING_SHA,"complete_original_binding_bytes":39348,
        "all_original_20_public_file_identities_unchanged":public,
        "original_whole_pair_1e_minus_7_sum_guard_unchanged":True,
        "original_signed_volume_topology_and_containment_guards_unchanged":True,
        "original_process_ownership_source_closure_and_resource_guards_unchanged":True,
        "original_native_controls_and_two_readers_unchanged":True,
        "original_nominal_seven_unmeasured_cases_retained":True,
        "full11781_independent_factory_domain_or_K3_proved":False,
        "source_install_only_executed_locally":True,"native_execution":False,
        "raw_runtime_or_credentials_embedded":False,"git_write_executed_by_builder":False,
        "publication_status":"blocked_by_unconfirmed_publication",
        "stage1_request_preserved_sha256":STAGE1_REQUEST_SHA,
        "pure_binding_replay_preserved_sha256":STAGE1_REPLAY_SHA,
        "actual_transport_readback_sha256":sha((args.output/"L5B_INLINE_TRANSPORT_READBACK.json").read_bytes())}
    write_json(args.output/"L5B_INLINE_STATIC_CHECK.json",static)
    interruption={"schema":"razr-L5b-publication-interruption-record-v1",
        "stage1_request_sha256":STAGE1_REQUEST_SHA,"stage1_request_bytes":90896,
        "root_reported_publication_attempts_interrupted":2,
        "observation_source":"Parent task messages reporting interrupted publication attempts and subsequent read-only checks.",
        "root_last_observed_stage1_branch":"diagnostic/s4-k1-l5-target-binding-20261026",
        "root_last_observed_branch_HTTP_status":404,
        "root_observed_binding_blob_prefix":"090cdbe",
        "expected_binding_git_blob_sha1_computed_from_reviewed_bytes":hashlib.sha1(b"blob "+str(len(binding)).encode()+b"\0"+binding).hexdigest(),
        "binding_blob_presence_is_not_commit_or_branch_publication":True,
        "stage1_commit_confirmed":False,"stage1_tree_or_branch_publication_confirmed":False,
        "L5b_workflow_run_confirmed":False,"L5b_native_execution_confirmed":False,
        "original_L5_workflow_size_failure_retained":True,
        "original_L5a_pre_native_target_binding_failure_retained":True,
        "fallback_does_not_depend_on_unpublished_commit":True,
        "fallback_remains_unpublished_at_freeze":True,
        "publication_status":"blocked_by_unconfirmed_publication",
        "no_new_Git_write_or_native_execution_performed":True}
    write_json(args.output/"L5B_PUBLICATION_INTERRUPTION_RECORD.json",interruption)
    readme="""# L5b inline fallback: complete target binding plus twenty fixed public files

This package is a reviewable source-transport fallback. It does not depend on an unconfirmed stage-1 commit. The complete original L1 target binding is embedded as exact UTF-8 data (39,348 bytes, SHA-256 7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2). Its SHA and byte count are checked before writing either source copy or contacting the public source endpoint. The other twenty files are fetched without credentials from immutable commit 33386f1d6046aee80b0446b9c21fb7c259c3523a, with their original SHA/size checks, rejected redirects, and the original 15 s socket timeout.

The installer remains inside the original 90 s process cap plus 5 s termination grace. It writes all twenty-one files to the same two external source directories. The original full twenty-one-file source footer runs afterward; only its binding SHA/size changes. The public download payload is 193,306 bytes; the exact installed source set is 232,654 bytes. No worker or host budget grows: 1800 s worker, 1536 MiB peak RSS, original shared-memory and disk gates, 2220 s host deadline, 40 min job. Original and current jobs remain sequential with the original dependency.

All seventeen native Python sources, K1 binding, method plan and method README remain byte-identical. Producer, core, original exact-target equality, signed volume, topology, conservatism controls, whole-pair 1e-7 sum, native controls and both readers are unchanged. All other workflow steps and job fields remain the original parsed values. The separately named workflow, push branch and concurrency identify this fallback. The generated YAML is below 500,000 bytes and all nineteen bash blocks and eleven embedded Python blocks parse.

Validation actually ran only the bounded standard-library source installer and original SHA footer in fresh temporary directories. It fetched the fixed twenty public files and checked both installed copies of all twenty-one files. A one-byte inline-binding mutation was rejected before network access or file writes. A same-length mutation in a simulated public response was rejected by the original SHA gate. Downloaded source was never imported or executed. No CAD, original L1 replay, producer or native reader was run.

The exact stage-1 request b9773dc610e30196957a71fea34f5daea9884e45a64473119924763a15554e4c and its five reviewed files are preserved. This tree request includes those files unchanged alongside the fallback workflow and transport evidence. The parent reported two interrupted publication attempts, a binding blob, a 404 branch and no confirmed L5b run. Blob presence alone establishes neither a commit nor a published branch. Both original preparation failures remain: initial L5 workflow size rejection and L5a pre-native target-binding mismatch. At freeze this package is blocked_by_unconfirmed_publication, with no new Git write.

Native evidence remains unmeasured for the seven original nominal q=[0,12] cases and their current-K1 counterparts. This transport work does not prove the full binary64 factory acceptance slabs, independent left/right domain, K3, all 11,781 pairs, OEM electrical qualification or physical G3–G5.
"""
    (args.output/"README.md").write_text(readme)
    own_code=args.output/"build_l5b_inline_workflow.py"
    if own_code.resolve()!=Path(__file__).resolve():
        own_code.write_bytes(Path(__file__).read_bytes())
    names=["build_l5b_inline_workflow.py","l5b_inline_source_install.py","L5B_INLINE_TRANSPORT_READBACK.json",
        "L5B_INLINE_STATIC_CHECK.json","L5B_PUBLICATION_INTERRUPTION_RECORD.json","README.md"]
    elements=copy.deepcopy(stage1["tree_elements"])
    elements.extend({"path":PREFIX+n,"mode":"100644","type":"blob","content":(args.output/n).read_text()} for n in names)
    elements.append({"path":".github/workflows/s4-k1-l5-cylindrical.yml","mode":"100644","type":"blob","content":workflow.decode()})
    require(len(elements)==12 and len({e["path"] for e in elements})==12,"standalone twelve-file fallback tree")
    tree={"repository_full_name":"TrillionniumFoundation/RAZR-SLIDE","base_tree_sha":BASE_TREE,"tree_elements":elements}
    out_request=args.output/"L5B_INLINE_PUBLIC_TREE_REQUEST.json";write_json(out_request,tree)
    mapping=[]
    for i,e in enumerate(elements):
        path=(args.stage1_directory/e["path"].rsplit("/",1)[1] if i<5 else wf if e["path"].startswith(".github/") else args.output/e["path"].rsplit("/",1)[1])
        data=path.read_bytes();require(data==e["content"].encode(),"mapped exact request bytes")
        mapping.append({"repository_path":e["path"],"local_path":str(path),"bytes":len(data),"sha256":sha(data)})
    mp=args.output/"L5B_INLINE_SAFE_INTEGRATION_MAPPING.json";write_json(mp,{"entries":mapping})
    handoff={"schema":"razr-L5b-inline-final-local-handoff-v1","publication_status":"blocked_by_unconfirmed_publication",
        "branch":BRANCH,"base_commit":BASE_COMMIT,"base_tree":BASE_TREE,"request_entries":12,
        "request_bytes":out_request.stat().st_size,"request_sha256":sha(out_request.read_bytes()),
        "workflow_bytes":len(workflow),"workflow_sha256":sha(workflow),
        "mapping_sha256":sha(mp.read_bytes()),"static_check_sha256":sha((args.output/"L5B_INLINE_STATIC_CHECK.json").read_bytes()),
        "actual_transport_readback_sha256":sha((args.output/"L5B_INLINE_TRANSPORT_READBACK.json").read_bytes()),
        "preserved_stage1_request_sha256":STAGE1_REQUEST_SHA,"stage1_commit_confirmed":False,
        "two_interrupted_publication_attempts_preserved":True,"Git_mutations_performed":False,"native_executed":False}
    write_json(args.output/"FINAL_HANDOFF_STATUS.json",handoff)
    print(json.dumps(handoff,indent=2))

if __name__=="__main__":
    main()
