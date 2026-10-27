"""Failure-preserving, narrowly allowlisted L5d2 science exporter; no raw runtime."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

from export_l5 import no_runtime, SOURCE_NAMES

C_SOURCES=("run_l5d2.py","supervise_l5d2.py","export_l5d2.py",
           "L5D2_INPUT_BINDING.json","L5D2_CAPACITY_PREREGISTRATION.json")

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def scientific_name(name):
    originals={
        "control-original-extrusion-original-shape.brep",
        "control-original-extrusion-original-face.brep",
        "control-original-extrusion-original-shape.step",
        "control-original-extrusion-original-face.step",
        "step-original-whole-step-root-0.brep",
        "step-original-face-step-root-0.brep",
        "t025-translated.brep",
        "control-original-extrusion-v2-region-0.brep",
        "original-L5c-report.json",
        "report.json"}
    if name in originals:return True
    if name=="original-cq-cut-result.brep":return True
    if re.fullmatch(r"actual-(?:cut|common|reverse-cut)-(?:result|after-[ab])\.brep",name):return True
    return re.fullmatch(r"control-(?:empty|nonempty)-(?:a|b|result)\.brep",name) is not None

def execute(case,sources,out):
    out.mkdir(exist_ok=False);rejected=[]
    folder=case/"l5d2/worker/science"
    if folder.is_dir():
        for p in sorted(folder.iterdir()):
            if p.name.endswith(".partial"):continue
            if p.is_symlink() or not p.is_file():
                rejected.append({"reason":"nonregular_or_link_not_exported"});continue
            rec={"bytes":p.stat().st_size,"sha256":sha(p)}
            if not scientific_name(p.name):
                rejected.append({**rec,"reason":"unreviewed_filename_not_exported"});continue
            if p.suffix==".json":
                try:
                    obj=json.loads(p.read_text());no_runtime(obj)
                    if p.name=="original-L5c-report.json":
                        binding=json.loads((sources/"L5D2_INPUT_BINDING.json").read_text())
                        if rec!=binding["source_manifest"]["report.json"] or obj.get("schema")!="razr-L5c-preserved-EXTRUSION-operation-diagnosis-v1":
                            raise ValueError("unaltered exact original L5c report required")
                    elif obj.get("schema")!="razr-L5d2-six-build-raw-Boolean-status-diagnosis-v1":
                        raise ValueError("unreviewed schema")
                except Exception:
                    rejected.append({**rec,"reason":"unreviewed_runtime_locator_or_JSON_not_exported"});continue
            shutil.copyfile(p,out/p.name)
    for name in (*SOURCE_NAMES,*C_SOURCES):
        p=sources/name
        if p.is_file() and not p.is_symlink():shutil.copyfile(p,out/("source-"+name))
    for name in ("L5_SOURCE_IDENTITY.json","L5D2_SOURCE_IDENTITY.json","L5D2_INPUT_VERIFIED.json"):
        p=case/name
        if p.is_file() and not p.is_symlink():
            try:
                obj=json.loads(p.read_text());no_runtime(obj)
                shutil.copyfile(p,out/name)
            except Exception:
                rejected.append({"bytes":p.stat().st_size,"sha256":sha(p),"reason":"unreviewed_prerequisite_projection"})
    p=case/"l5d2/controller.json"
    if p.is_file():
        c=json.loads(p.read_text())
        keys=("completed","worker_started","worker_exit_code","owned_child_identity_verified",
              "source_bytes_unchanged","locked_environment_unchanged","owned_channel_descriptors_closed",
              "reported_execution_completed","all_selected_original_operation_guards_passed",
              "limits","resource_start_refused","capacity_or_wall_stop","elapsed_seconds","scope","worker_mode")
        obj={k:c.get(k) for k in keys}
        obj.update(original_controller_sha256=sha(p),original_controller_bytes=p.stat().st_size,
                   raw_runtime_exported=False,is_original_record=False)
        no_runtime(obj)
        (out/"L5D2_CONTROLLER_OUTCOME.json").write_text(json.dumps(obj,indent=2)+"\n")
    (out/"EXPORT_SCOPE.json").write_text(json.dumps({
        "schema":"razr-L5d2-narrow-scientific-export-v1","raw_runtime_exported":False,
        "raw_private_runtime_preservation_claimed":False,"rejected_items":rejected,
        "failed_original_operations_not_reclassified":True,"original_seven_reexecuted":False,
        "old_failed_STEP_originals_not_replaced":True,"null_result_not_replaced_by_empty":True,
        "complete_product_qualification":False},indent=2)+"\n")
    manifest={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
    (out/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return 0 if not rejected else 2

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case",type=Path,required=True)
    ap.add_argument("--sources",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args();return execute(a.case,a.sources,a.output)

if __name__=="__main__":
    raise SystemExit(main())
