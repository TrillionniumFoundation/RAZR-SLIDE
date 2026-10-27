"""Check only the newly embedded L5c transport/input code and failure-safe exporter; no CAD/network."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import yaml

def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def block(run,marker):
    lines=run.splitlines()
    start=next(i for i,x in enumerate(lines) if "<<'"+marker+"'" in x)
    end=next(i for i in range(start+1,len(lines)) if lines[i]==marker)
    return "\n".join(lines[start+1:end])+"\n"

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory",type=Path,required=True)
    ap.add_argument("--original-science",type=Path,required=True)
    ap.add_argument("--unchanged-source",type=Path,required=True)
    a=ap.parse_args();d=a.directory
    w=yaml.safe_load((d/"s4-l5c-extrusion-hosted.yml").read_text())
    steps=w["jobs"]["diagnostic"]["steps"]
    source_code=block(steps[2]["run"],"L5C_DIAGNOSTIC_SOURCES")
    input_code=block(steps[7]["run"],"L5C_INPUT_VERIFY")
    result={"schema":"razr-L5c-new-transport-and-export-check-v1","network_accessed":False,
        "native_CAD_executed":False,"old_L5_pure_native_control_tests_repeated":False,"controls":[]}
    with tempfile.TemporaryDirectory(prefix="L5c-new-code-only-",dir=d) as temp:
        t=Path(temp);host=t/"host";case=t/"case"
        (host/"l5").mkdir(parents=True);(case/"source/l5").mkdir(parents=True)
        env={**os.environ,"HOST_ROOT":str(host),"CASE_DIR":str(case),"PYTHONDONTWRITEBYTECODE":"1"}
        r=subprocess.run([sys.executable,"-B","-c",source_code],env=env,capture_output=True,text=True)
        require(r.returncode==0,"actual inline diagnostic source installer failed")
        identity=json.loads((case/"L5C_SOURCE_IDENTITY.json").read_text())
        for name,record in identity["sources"].items():
            wanted=(d/name).read_bytes()
            for folder in (host/"l5",case/"source/l5"):
                b=(folder/name).read_bytes()
                require(b==wanted and len(b)==record["bytes"] and sha(b)==record["sha256"],"new source copy identity")
        result["controls"].append({"name":"actual_inline_new_source_installer","passed":True,"verified_copies":10})
        shutil.copytree(a.original_science,host/"l5b-original-download")
        r=subprocess.run([sys.executable,"-B","-c",input_code],env=env,capture_output=True,text=True)
        require(r.returncode==0,"actual new input manifest verifier failed")
        result["controls"].append({"name":"actual_68_plus_manifest_input_verifier","passed":True,"source_originals_modified":False})
        damaged=host/"l5b-original-download/control-original-extrusion-original-shape.brep"
        b=damaged.read_bytes();damaged.write_bytes(b[:-1]+bytes([b[-1]^1]))
        r=subprocess.run([sys.executable,"-B","-c",input_code],env=env,capture_output=True,text=True)
        require(r.returncode!=0,"new input verifier accepted a changed native operand")
        result["controls"].append({"name":"one_byte_original_BREP_change_rejected","passed":True})
        sys.path[:0]=[str(d),str(a.unchanged_source)]
        spec=importlib.util.spec_from_file_location("new_L5c_exporter_for_pure_check",d/"export_l5c.py")
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        for label,private,unknown,expected_exit in (("negative_signed_failure_retained",False,False,0),
                ("unknown_filename_keeps_known_science_and_red_exit",False,True,2),
                ("private_locator_report_rejected",True,False,2)):
            folder=t/label;science=folder/"l5c/worker/science";science.mkdir(parents=True)
            sources=folder/"sources";sources.mkdir()
            rec={"schema":"razr-L5c-preserved-EXTRUSION-operation-diagnosis-v1",
                 "fixture_not_native_output":True,"execution_completed":False,
                 "raw_signed_volume_mm3":-2e-10,"original_failure_preserved":True}
            if private:rec["unreviewed_locator"]="/tmp/private-fixture-only"
            (science/"report.json").write_text(json.dumps(rec)+"\n")
            if unknown:(science/"unapproved-file-name.fixture").write_bytes(b"unapproved fixture bytes")
            out=folder/"publish";code=mod.execute(folder,sources,out)
            require(code==expected_exit,"failure-safe exporter disposition changed")
            if not private:
                require(json.loads((out/"report.json").read_text())["raw_signed_volume_mm3"]==-2e-10,
                        "negative signed value hidden or altered")
            else:require(not (out/"report.json").exists(),"private report exported")
            scope=json.loads((out/"EXPORT_SCOPE.json").read_text())
            require(all(set(x)=={"bytes","sha256","reason"} for x in scope["rejected_items"]),
                    "rejected private basename or text exposed")
            manifest=json.loads((out/"MANIFEST.json").read_text())
            require(set(p.name for p in out.iterdir())==set(manifest)|{"MANIFEST.json"},"partial export manifest incomplete")
            result["controls"].append({"name":label,"passed":True,"actual_exit_code":code,"fixtures_not_native":True})
    require(not any(k=="cadquery" or k=="OCP" or k.startswith("OCP.") for k in sys.modules),"pure diagnostic check imported CAD")
    result["all_controls_passed"]=True
    result["workflow_sha256"]=sha((d/"s4-l5c-extrusion-hosted.yml").read_bytes())
    result["script_sha256"]=sha(Path(__file__).read_bytes())
    (d/"L5C_NEW_CODE_CHECK.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"controls":len(result["controls"]),"passed":True,"native_executed":False}))
if __name__=="__main__":main()
