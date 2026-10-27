"""L5c bounded native operation diagnosis of preserved L5b EXTRUSION operands.

This new diagnostic retains failed original predicates. It never runs the
seven physical pairs, never repairs the old report and never qualifies a domain.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import math
import resource
import shutil
import signal
import sys
import time
import traceback

from run_l5 import ROOT, S4, HERE, SOURCES, identity, owned_process, sha
import capacity_stage_v4 as stage
import full_slide_api_v4 as api

C_SOURCES=("run_l5c.py","supervise_l5c.py","export_l5c.py",
           "L5C_INPUT_BINDING.json","L5C_CAPACITY_PREREGISTRATION.json")
BINDING_SHA="a06aed5fc76b5a7bc5c538eb1920802b14594fa63cb36b171b3fcebbac12d173"
MAX_SHAPE_FILES=96
MAX_SHAPE_BYTES=64*2**20
MAX_JSON_BYTES=4*2**20

def require(ok, message):
    if not ok:
        raise ValueError(message)

def safe_exception(exc):
    raw=str(exc).encode("utf-8",errors="replace")
    rows=[]
    for frame in traceback.extract_tb(exc.__traceback__):
        path=Path(frame.filename).resolve()
        if path.is_relative_to(ROOT) and path.is_file():
            rows.append({"source_family":"immutable_S4",
                         "repository_path":path.relative_to(ROOT).as_posix(),
                         "function":frame.name,"line":frame.lineno,"source_sha256":sha(path)})
        elif path.parent==HERE and path.name in set(SOURCES)|set(C_SOURCES) and path.is_file():
            rows.append({"source_family":"frozen_external_diagnostic",
                         "source_name":path.name,"function":frame.name,
                         "line":frame.lineno,"source_sha256":sha(path)})
    return {"failure_type":type(exc).__name__,
            "exception_message_utf8_sha256":hashlib.sha256(raw).hexdigest(),
            "exception_message_utf8_bytes":len(raw),"raw_exception_text_exported":False,
            "controlled_source_traceback":rows}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope",choices=("original",),required=True)
    ap.add_argument("--inputs",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    owned_process.announce_worker_from_environment(Path(__file__).resolve())
    out=args.output.resolve()
    require(not out.exists() and not out.is_relative_to(ROOT),"fresh external diagnostic output required")
    out.mkdir(parents=True);science=out/"science";science.mkdir()
    started=time.monotonic()
    report={"schema":"razr-L5c-preserved-EXTRUSION-operation-diagnosis-v1",
            "functional_source_commit":S4,
            "original_L5b_workflow_commit":"690b1ed0df100fe175f5d6752b716105c0521a25",
            "original_L5b_run_id":40465353232,"original_L5b_artifact_id":12715683051,
            "scope":"preserved_original_EXTRUSION_and_STEP_only",
            "execution_completed":False,"diagnostic_observations_completed":False,
            "all_selected_original_operation_guards_passed":False,
            "all_original_L5_controls_and_pairs_passed":False,
            "source_runtime_unchanged":False,"external_source_unchanged":False,
            "native_started":False,"active_gate":None,
            "operations":[],"scientific_exports":[],"selected_original_guard_results":[],
            "no_abs_volume_or_negative_clamp":True,"original_failure_not_overwritten":True,
            "original_seven_pair_calls":0,"current_seven_pair_calls":0,
            "full_15D_domain_proved":False,"full_11781_pair_execution":False,
            "K3_qualification":False,"physical_qualification":False,"candidate_go":False}
    source_before={n:sha(HERE/n) for n in (*SOURCES,*C_SOURCES)}
    report["external_source_sha256"]=source_before
    before=None;executed=[];budget=None;shape_bytes=0;shape_count=0
    def save():
        report["elapsed_seconds"]=time.monotonic()-started
        report["peak_RSS_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        data=json.dumps(report,indent=2,allow_nan=False).encode()
        if len(data)>MAX_JSON_BYTES:
            raise api.CapacityStop("diagnostic JSON output cap")
        identity.atomic_json(science/"report.json",report)
    def check_budget():
        if budget is not None:budget.check()
    def raw_signature(body):
        # These are observations; none substitute for the original material gate.
        result={"raw_mass_accessor_is_not_material_volume_acceptance":True}
        for key,fn in (
            ("shape_type",body.ShapeType),("native_is_valid",body.isValid),
            ("native_is_null",lambda:body.wrapped.IsNull()),
            ("raw_signed_volume_mm3",body.Volume),
            ("solid_count",lambda:len(body.Solids())),
            ("raw_solid_signed_volumes_mm3",lambda:[float(x.Volume()) for x in body.Solids()]),
            ("face_count",lambda:len(body.Faces()))):
            try:
                value=fn()
                if isinstance(value,float) and not math.isfinite(value):
                    result[key+"_nonfinite_hex"]=value.hex()
                elif isinstance(value,list) and any(isinstance(x,float) and not math.isfinite(x) for x in value):
                    result[key+"_raw_hex"]=[float(x).hex() for x in value]
                else:result[key]=value
            except Exception as exc:
                result[key+"_observation_failure"]=safe_exception(exc)
        return result
    def keep(name,body):
        nonlocal shape_bytes,shape_count
        check_budget()
        require(name.endswith(".brep") and name.count("/") == 0 and name.count("\\") == 0,
                "controlled diagnostic BREP name required")
        path=science/name;require(not path.exists(),"new scientific BREP path required")
        row={"path":name,"source":"new_native_diagnostic_observation","signature":raw_signature(body)}
        try:
            status=body.exportBrep(str(path))
            row["native_export_status"]=str(status)
            if path.is_file():
                row.update(bytes=path.stat().st_size,sha256=sha(path))
                shape_bytes+=path.stat().st_size;shape_count+=1
            row["export_completed"]=status is True and path.is_file() and path.stat().st_size>0
        except Exception as exc:
            row["export_completed"]=False;row["export_failure"]=safe_exception(exc)
        report["scientific_exports"].append(row)
        save()
        if shape_count>MAX_SHAPE_FILES or shape_bytes>MAX_SHAPE_BYTES:
            raise api.CapacityStop("diagnostic shape output cap")
        return row
    def attempt(gate,fn):
        check_budget()
        row={"gate":gate,"status":"started","completed":False}
        report["operations"].append(row);report["active_gate"]=gate;save()
        t=time.monotonic()
        try:
            result=fn()
        except (api.CapacityStop,InterruptedError):
            row["status"]="capacity_or_signal_interrupted";save();raise
        except Exception as exc:
            row.update(status="failed",completed=True,elapsed_seconds=time.monotonic()-t,**safe_exception(exc))
            save();return False,None,row
        row.update(status="returned",completed=True,elapsed_seconds=time.monotonic()-t)
        report["active_gate"]=None;save()
        return True,result,row
    def selected(gate,ok):
        report["selected_original_guard_results"].append({"gate":gate,"passed":bool(ok)})
        save()
    def validate_material(gate,body,empty=False):
        ok,value,row=attempt(gate,lambda:p.whole_material(body,empty=empty))
        if ok:
            leaves,volume=value
            row.update(original_signed_volume_mm3=volume,original_solid_count=len(leaves),
                       original_validated_empty_material=not leaves and volume==0,
                       original_empty_material_allowed=empty)
            save()
        selected(gate,ok)
        return ok,value
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError("owned SIGTERM")))
    save()
    try:
        require(identity.git("rev-parse","HEAD")==S4 and not identity.git("status","--porcelain"),
                "immutable clean S4 required")
        before=identity.snapshot();executed=identity.record_executed_project_files()
        identity.atomic_json(out/"source-before-private.json",before)
        require(sha(HERE/"L5C_INPUT_BINDING.json")==BINDING_SHA,"frozen L5b input binding changed")
        binding=json.loads((HERE/"L5C_INPUT_BINDING.json").read_text())
        inputs=args.inputs.resolve()
        manifest_path=inputs/"MANIFEST.json"
        require(manifest_path.is_file() and not manifest_path.is_symlink() and
                manifest_path.stat().st_size==binding["source_manifest_bytes"] and
                sha(manifest_path)==binding["source_manifest_sha256"],"exact L5b manifest changed")
        manifest=json.loads(manifest_path.read_text())
        require(manifest==binding["source_manifest"] and
                {p.name for p in inputs.iterdir()}==set(manifest)|{"MANIFEST.json"},
                "complete scientific member inventory changed")
        for name,item in manifest.items():
            path=inputs/name
            require(path.parent==inputs and path.is_file() and not path.is_symlink() and
                    path.stat().st_size==item["bytes"] and sha(path)==item["sha256"],
                    "exact L5b original scientific member changed")
        report["all_68_input_members_and_manifest_verified"]=True
        report["input_binding_sha256"]=BINDING_SHA;save()
        import verify_slide_native as original
        import cadquery as cq
        import product_assembly as p
        import translation_regions as original_regions
        budget=stage.ForwardBudget(original.Budget(SimpleNamespace(output=science/"report.json")),api)
        check_budget()
        report["native_started"]=True;save()
        # Input byte copies preserve the original actual scientific operands.
        wanted=list(binding["operands"].values())+binding["saved_V2_regions"]
        for item in wanted:
            src=inputs/item["path"];dest=science/item["path"]
            require(not dest.exists(),"original operand copy duplicated")
            shutil.copyfile(src,dest);shape_count+=1;shape_bytes+=dest.stat().st_size
            report["scientific_exports"].append({"path":dest.name,"bytes":dest.stat().st_size,
                "sha256":sha(dest),"source":"byte_identical_original_L5b_scientific_operand",
                "byte_identical_original":True})
        save()
        # STEP operations are isolated so a failed whole STEP cannot erase the
        # subsequent face or BREP-only operation diagnosis.
        step_rows=[]
        report["STEP_attempts"]=step_rows
        for label in ("original-whole-step","original-face-step"):
            path=inputs/binding["operands"][label]["path"];item={"role":label};step_rows.append(item);save()
            ok,workplane,row=attempt(label+".importStep",lambda path=path:cq.importers.importStep(str(path)))
            item["import_passed"]=ok
            if not ok:selected(label+".importStep",False);continue
            ok,roots,row=attempt(label+".vals",workplane.vals);item["vals_passed"]=ok
            if not ok:selected(label+".vals",False);continue
            item["root_count"]=len(roots);save()
            ok,_,row=attempt(label+".original_one_root_gate",
                             lambda roots=roots:require(len(roots)==1,"one complete STEP root required"))
            item["original_one_root_gate_passed"]=ok;selected(label+".original_one_root_gate",ok)
            if len(roots)>8:
                raise api.CapacityStop("bounded diagnostic STEP root retention cap")
            item["fresh_root_BREPs"]=[keep("step-"+label+"-root-"+str(i)+".brep",body) for i,body in enumerate(roots)]
            if not ok:continue
            if label=="original-whole-step":
                ok,body,row=attempt(label+".original_p_single",lambda:p.single(roots[0]))
                item["original_single_passed"]=ok;selected(label+".original_p_single",ok)
                if ok:row["signature"]=raw_signature(body);save()
            else:
                ok,_,row=attempt(label+".original_face_valid_gate",
                                 lambda:require(roots[0].isValid(),"original face STEP root invalid"))
                item["original_face_valid_passed"]=ok;selected(label+".original_face_valid_gate",ok)
        original_whole_path=inputs/binding["operands"]["original-whole-brep"]["path"]
        original_face_path=inputs/binding["operands"]["original-face-brep"]["path"]
        ok,whole,row=attempt("original_whole.BREP_import",lambda:cq.Shape.importBrep(str(original_whole_path)))
        require(ok,"original whole BREP import unavailable")
        row["signature"]=raw_signature(whole);save()
        whole_ok,_=validate_material("original_whole.original_positive_material_gate",whole,False)
        ok,face,row=attempt("original_face.BREP_import",lambda:cq.Shape.importBrep(str(original_face_path)))
        require(ok,"original face BREP import unavailable")
        row["signature"]=raw_signature(face)
        face_ok=bool(face.isValid() and len(face.Faces())==1 and face.Faces()[0].geomType()=="EXTRUSION")
        row["original_EXTRUSION_face_identity_passed"]=face_ok;selected("original_face.EXTRUSION_identity",face_ok)
        require(whole_ok and face_ok,"original whole/face source gate failed")
        region_shapes=[]
        for i,item in enumerate(binding["saved_V2_regions"]):
            ok,body,row=attempt("saved_V2_region_"+str(i)+".BREP_import",
                               lambda item=item:cq.Shape.importBrep(str(inputs/item["path"])))
            if not ok:
                selected("saved_V2_region_"+str(i)+".BREP_import",False);continue
            row["signature"]=raw_signature(body);save()
            valid,_=validate_material("saved_V2_region_"+str(i)+".original_positive_material_gate",body,False)
            if valid:region_shapes.append(body)
        require(len(region_shapes)==len(binding["saved_V2_regions"]) and
                0<len(region_shapes)<=binding["original_region_cap"],
                "all original saved V2 regions are required")
        report["saved_V2_regions_used_byte_identical"]=True
        report["V2_region_constructor_reexecuted"]=False;save()
        ok,_,row=attempt("old_regions.original_EXTRUSION_rejection",
                         lambda:original_regions.regions(whole,binding["original_vector_xyz"]))
        expected="unsupported advancing surface EXTRUSION".encode()
        reproduced=(not ok and row.get("failure_type")=="ValueError" and
                    row.get("exception_message_utf8_sha256")==hashlib.sha256(expected).hexdigest() and
                    row.get("exception_message_utf8_bytes")==len(expected))
        report["old_unsupported_EXTRUSION_failure_reproduced"]=reproduced
        row["expected_original_rejection_retained"]=reproduced
        selected("old_regions.expected_original_EXTRUSION_rejection",reproduced)
        # Direct unchanged operations preserve their exact original call order.
        direct=[]
        report["direct_original_subtraction_attempts"]=direct
        for t in binding["direct_parameters"]:
            key="t000" if t==0. else "t025"
            entry={"parameter":t,"new_diagnostic_replay_not_original_L5b_operation":True}
            direct.append(entry);save()
            vector=tuple(t*v for v in binding["original_vector_xyz"])
            ok,translated,row=attempt(key+".translate",lambda vector=vector:whole.translate(vector))
            entry["translate_passed"]=ok;selected(key+".translate",ok)
            if not ok:continue
            entry["translated_BREP"]=keep(key+"-translated.brep",translated)
            ok,residue,row=attempt(key+".unchanged_subtract_regions",
                                  lambda translated=translated:original_regions.subtract_regions(translated,region_shapes))
            entry["unchanged_subtract_regions_returned"]=ok;selected(key+".unchanged_subtract_regions",ok)
            if not ok:continue
            entry["residue_BREP"]=keep(key+"-original-subtract-result.brep",residue)
            ok,volume,row=attempt(key+".unchanged_p_volume",lambda residue=residue:p.volume(residue))
            entry["original_p_volume_returned"]=ok;selected(key+".unchanged_p_volume",ok)
            if not ok:continue
            entry["original_outside_mm3"]=volume;save()
            ok,_,row=attempt(key+".unchanged_containment_gate",
                             lambda volume=volume:require(0<=volume<=1e-7,"direct EXTRUSION new region material escape"))
            entry["original_containment_gate_passed"]=ok;selected(key+".unchanged_containment_gate",ok)
        # This is a separate diagnostic replay of the exact source loop, with
        # each cut and clean split into separately checkpointed operations.
        trace={"parameter":binding["traced_parameter"],"source_function":"integration/translation_regions.py:subtract_regions",
               "distinct_replay_not_original_failed_operation":True,"steps":[],"completed":False}
        report["traced_original_subtraction_loop"]=trace;save()
        vector=tuple(binding["traced_parameter"]*v for v in binding["original_vector_xyz"])
        ok,result,row=attempt("trace_t025.translate",lambda:whole.translate(vector))
        if ok:
            trace["translated_BREP"]=keep("trace-t025-translated.brep",result)
            stopped=False
            for i,region in enumerate(region_shapes):
                entry={"index":i};trace["steps"].append(entry);save()
                ok,material,row=attempt("trace_t025.region_"+str(i)+".original_whole_material_before",
                                       lambda result=result:original_regions.whole_material(result,empty=True))
                entry["whole_material_before_returned"]=ok
                if not ok:stopped=True;break
                leaves,volume=material
                entry.update(original_signed_volume_mm3=volume,original_solid_count=len(leaves),
                             original_validated_empty_material=not leaves and volume==0)
                save()
                if not leaves:
                    trace["original_validated_empty_early_return"]=True;trace["completed"]=True;break
                ok,cut,row=attempt("trace_t025.region_"+str(i)+".cut",lambda result=result,region=region:result.cut(region))
                entry["cut_returned"]=ok
                if not ok:stopped=True;break
                entry["cut_BREP"]=keep("trace-t025-cut-"+str(i)+".brep",cut)
                ok,clean,row=attempt("trace_t025.region_"+str(i)+".clean",cut.clean)
                entry["clean_returned"]=ok
                if not ok:stopped=True;break
                entry["clean_BREP"]=keep("trace-t025-clean-"+str(i)+".brep",clean)
                result=clean;save()
            if not stopped and not trace["completed"]:
                ok,mat,row=attempt("trace_t025.original_whole_material_final",
                                   lambda:original_regions.whole_material(result,empty=True))
                trace["final_original_whole_material_returned"]=ok
                if ok:
                    trace["final_original_solid_count"]=len(mat[0]);trace["final_original_signed_volume_mm3"]=mat[1]
                trace["completed"]=ok;save()
        trace["selected_diagnostic_original_operation_gates_passed"]=trace["completed"]
        selected("traced_original_subtraction_loop",trace["completed"])
        report["diagnostic_observations_completed"]=True
        report["execution_completed"]=True
        report["all_selected_original_operation_guards_passed"]=all(x["passed"] for x in report["selected_original_guard_results"])
        save()
    except (api.CapacityStop,InterruptedError) as exc:
        report["capacity_failure"]=safe_exception(exc)
    except BaseException as exc:
        report["diagnostic_failure"]=safe_exception(exc)
    finally:
        try:
            if before is not None:
                after=identity.finish(before,executed);identity.atomic_json(out/"source-after-private.json",after)
                report["source_runtime_unchanged"]=after["source_bytes_and_locked_environment_unchanged"]
                require(after["repository_head_at_finish"]==S4 and not identity.git("status","--porcelain"),
                        "immutable S4 closure changed")
            report["external_source_unchanged"]=source_before=={n:sha(HERE/n) for n in (*SOURCES,*C_SOURCES)}
            require(report["external_source_unchanged"],"frozen diagnostic external sources changed")
        except BaseException as exc:
            report["postflight_failure"]=safe_exception(exc);report["source_runtime_unchanged"]=False
        if budget is not None:report["original_resource_record"]=budget.record()
        report["scientific_shape_bytes"]=shape_bytes;report["scientific_shape_file_count"]=shape_count
        report["scientific_retention_complete"]=all(x.get("byte_identical_original") is True or x.get("export_completed") is True
            for x in report["scientific_exports"])
        report["native_diagnostic_is_not_a_second_kernel"]=True
        save()
    print(json.dumps({k:report.get(k) for k in ("execution_completed","diagnostic_observations_completed",
        "all_selected_original_operation_guards_passed","old_unsupported_EXTRUSION_failure_reproduced",
        "source_runtime_unchanged","external_source_unchanged","elapsed_seconds")}),flush=True)
    return 0 if (report["execution_completed"] and report["all_selected_original_operation_guards_passed"]
        and report["source_runtime_unchanged"] and report["external_source_unchanged"]
        and not report.get("diagnostic_failure") and not report.get("capacity_failure")
        and not report.get("postflight_failure") and report["scientific_retention_complete"]) else 2

if __name__=="__main__":
    raise SystemExit(main())
