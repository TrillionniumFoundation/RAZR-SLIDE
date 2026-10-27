"""L5d2 six-build raw Boolean status diagnosis of actual preserved L5d2 operands.

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
import re
import shutil
import signal
import sys
import time
import traceback

from run_l5 import ROOT, S4, HERE, SOURCES, identity, owned_process, sha
import capacity_stage_v4 as stage
import full_slide_api_v4 as api

C_SOURCES=("run_l5d2.py","supervise_l5d2.py","export_l5d2.py",
           "L5D2_INPUT_BINDING.json","L5D2_CAPACITY_PREREGISTRATION.json")
BINDING_SHA="3c5053b480482b2c47a90128e7e7a9737bd45c8ae7dce19ddbbab14263046f96"
MAX_SHAPE_FILES=32
MAX_SHAPE_BYTES=8*2**20
MAX_JSON_BYTES=4*2**20

def require(ok, message):
    if not ok:
        raise ValueError(message)

def checkpointed_native_method(attempt, gate, owner, method_name):
    """Attribute lookup itself is inside the recorded operation boundary."""
    return attempt(gate, lambda: getattr(owner, method_name)())

def safe_exception(exc):
    raw=str(exc).encode("utf-8",errors="replace")
    rows=[]
    for frame in traceback.extract_tb(exc.__traceback__):
        path=Path(frame.filename).resolve()
        if path.is_relative_to(ROOT/".venv") and path.is_file():
            rows.append({"source_family":"locked_environment_dependency_observation",
                         "immutable_Git_source_claimed":False,
                         "dependency_relative_path":path.relative_to(ROOT/".venv").as_posix(),
                         "function":frame.name,"line":frame.lineno,"source_sha256":sha(path)})
        elif path.is_relative_to(ROOT) and path.is_file():
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
    report={"schema":"razr-L5d2-six-build-raw-Boolean-status-diagnosis-v1",
            "functional_source_commit":S4,
            "original_L5b_workflow_commit":"690b1ed0df100fe175f5d6752b716105c0521a25",
            "original_L5b_run_id":40465353232,"original_L5b_artifact_id":12715683051,
            "scope":"preserved_L5c_first_cut_only_with_bound_STEP_failures",
            "original_L5c_workflow_commit":"f544f33c563ef4a44e8baa38c3e1225ad6e60b9e",
            "original_L5c_run_id":40468054101,"original_L5c_artifact_id":12717347119,
            "actual_L5d_predecessor_run_id":40470232086,
            "actual_L5d_predecessor_head":"40a4357903b63051578940d14ff8ee6426c04388",
            "actual_L5d1_predecessor_run_id":40471621804,
            "actual_L5d1_predecessor_head":"4927944f9ece18e0b5f67083ee9d8fb1da5d81a8",
            "prior_worker_signal_minus11_cause_proved":False,
            "STEP_failure_repair_proved":False,"conservative_continuous_containment_proved":False,
            "null_result_replaced_by_empty":False,"Boolean_build_calls_started":0,
            "raw_boolean_results":[],"original_STEP_failures_byte_retained":False,
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
            ("raw_mass_accessor_value",body.Volume),
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
        kind=result.get("shape_type")
        result["raw_mass_accessor_unit_for_mm_geometry"]={
            "Solid":"mm3", "Face":"mm2", "Shell":"mm2",
            "Edge":"mm", "Wire":"mm"}.get(kind,"undetermined_by_container_type")
        result["raw_mass_accessor_unit_is_not_a_material_acceptance"] = True
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
        require(sha(HERE/"L5D2_INPUT_BINDING.json")==BINDING_SHA,"frozen L5c input binding changed")
        binding=json.loads((HERE/"L5D2_INPUT_BINDING.json").read_text())
        inputs=args.inputs.resolve()
        manifest_path=inputs/"MANIFEST.json"
        require(manifest_path.is_file() and not manifest_path.is_symlink() and
                manifest_path.stat().st_size==binding["source_manifest_bytes"] and
                sha(manifest_path)==binding["source_manifest_sha256"],"exact L5c manifest changed")
        manifest=json.loads(manifest_path.read_text())
        require(manifest==binding["source_manifest"] and
                {p.name for p in inputs.iterdir()}==set(manifest)|{"MANIFEST.json"},
                "complete scientific member inventory changed")
        for name,item in manifest.items():
            path=inputs/name
            require(path.parent==inputs and path.is_file() and not path.is_symlink() and
                    path.stat().st_size==item["bytes"] and sha(path)==item["sha256"],
                    "exact L5c original scientific member changed")
        report["all_52_input_members_and_manifest_verified"]=True
        report["input_binding_sha256"]=BINDING_SHA;save()
        import verify_slide_native as original
        import cadquery as cq
        import product_assembly as p
        import translation_regions as original_regions
        budget=stage.ForwardBudget(original.Budget(SimpleNamespace(output=science/"report.json")),api)
        check_budget()
        report["native_started"]=True;save()

        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
        from OCP.TopTools import TopTools_ListOfShape
        import OCP.Message as message_module
        # These are the exact eight retained geometry operands and one unchanged
        # prior report. In particular, neither failed STEP is replaced.
        for item in binding["preserved_originals"]:
            src=inputs/item["input_path"];dest=science/item["output_path"]
            require(not dest.exists(),"original scientific copy duplicated")
            require(src.stat().st_size==item["bytes"] and sha(src)==item["sha256"],
                    "bound actual predecessor original differs")
            shutil.copyfile(src,dest)
            if dest.suffix in (".brep",".step"):
                shape_count+=1;shape_bytes+=dest.stat().st_size
            report["scientific_exports"].append({"path":dest.name,"bytes":dest.stat().st_size,
                "sha256":sha(dest),"source":"byte_identical_original_L5c_scientific_operand",
                "byte_identical_original":True})
        predecessor=json.loads((inputs/"report.json").read_text())
        report["predecessor_report_sha256"]=sha(inputs/"report.json")
        report["original_STEP_failures_byte_retained"]=all(
            x["import_passed"] is True and x["original_one_root_gate_passed"] is True
            for x in predecessor["STEP_attempts"]) and all(
            x.get("original_single_passed",x.get("original_face_valid_passed")) is False
            for x in predecessor["STEP_attempts"])
        require(report["original_STEP_failures_byte_retained"],"expected actual STEP failures absent")
        report["prior_STEP_failure_observations"]=predecessor["STEP_attempts"]
        require(sha(Path(cq.occ_impl.shapes.__file__))==
                binding["actual_expected_CadQuery_null_constant"]["locked_shapes_source_sha256"],
                "actual locked CadQuery wrapper source changed")
        save()
        def next_build(label):
            require(report["Boolean_build_calls_started"]<binding["maximum_boolean_build_calls"],
                    "six-build diagnostic cap")
            report["Boolean_build_calls_started"]+=1
            report["active_Boolean_build"]=label;save();check_budget()
        def original_pair(label,reverse=False):
            names=binding["actual_cut_operands"]
            values=[]
            for role in ("a","b"):
                path=inputs/names[role]
                ok,shape,entry=attempt(label+"."+role+".fresh_BREP_import",
                                      lambda path=path:cq.Shape.importBrep(str(path)))
                require(ok,"fresh actual input BREP import failed")
                entry["file"]={"path":path.name,"bytes":path.stat().st_size,"sha256":sha(path)}
                entry["signature"]=raw_signature(shape);save()
                ok,material=validate_material(label+"."+role+".original_positive_material",shape,False)
                require(ok,"fresh actual input original signed material guard failed")
                values.append(shape)
            return (values[1],values[0]) if reverse else tuple(values)
        def box_pair(label):
            a=cq.Solid.makeBox(1.,1.,1.,cq.Vector(0.,0.,0.))
            if label=="control-empty":
                b=cq.Solid.makeBox(3.,3.,3.,cq.Vector(-1.,-1.,-1.))
            elif label=="control-nonempty":
                b=cq.Solid.makeBox(1.,1.,1.,cq.Vector(2.,0.,0.))
            else:raise ValueError("unknown fixed control")
            for role,shape in (("a",a),("b",b)):
                ok,_=validate_material(label+"."+role+".original_positive_material",shape,False)
                require(ok,"fixed control material guard failed")
                keep(label+"-"+role+".brep",shape)
            return a,b
        # Original wrapper attempt is retained independently; its exception can
        # never serve as an empty-set result for the new observation route.
        a,b=original_pair("original-cq-cut")
        next_build("original-cq-cut")
        ok,result,row=attempt("original-cq-cut.unchanged_cut",lambda:a.cut(b))
        selected("original-cq-cut.unchanged_cut",ok)
        expected=binding["actual_expected_CadQuery_null_constant"]
        report["original_CadQuery_null_failure_reproduced"]=(
            not ok and row.get("failure_type")=="ValueError" and
            row.get("exception_message_utf8_sha256")==expected["sha256"] and
            row.get("exception_message_utf8_bytes")==expected["utf8_bytes"])
        if ok:
            keep("original-cq-cut-result.brep",result)
            validate_material("original-cq-cut.original_result_material",result,True)
        save()
        def alert_types(native_report,gravity_name):
            enum=getattr(message_module,"Message_Gravity",None)
            gravity=getattr(enum,gravity_name) if enum is not None else getattr(message_module,gravity_name)
            alerts=native_report.GetAlerts(gravity)
            size=alerts.Size()
            require(type(size) is int and 0<=size<=32,"bounded native alert list required")
            values=[]
            for alert in alerts:
                name=alert.DynamicType().Name()
                require(type(name) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}",name) is not None,
                        "only stable native alert type names may be exported")
                values.append(name)
            require(len(values)==size,"complete native alert type enumeration required")
            return {"count":size,"type_names":values,"raw_alert_message_exported":False}
        def interface_capabilities(label,owner,names):
            # Bounded known public names only; never dir(), recurse, dump an
            # object, or infer a missing Boolean status from method absence.
            record={"known_public_method_capabilities":[],
                    "method_absence_is_not_a_native_status_value":True}
            def type_name():
                value=type(owner).__module__+"."+type(owner).__qualname__
                require(value.startswith("OCP.") and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,191}",value) is not None,
                        "only public OCP type identity may be exported")
                return value
            got,value,rec=attempt(label+".capabilities.public_type",type_name)
            record["public_type"]=value if got else None
            sentinel=object()
            for name in names:
                def observe(name=name):
                    method=getattr(owner,name,sentinel)
                    return {"exists":method is not sentinel,
                            "callable":method is not sentinel and callable(method)}
                got,value,rec=attempt(label+".capabilities."+name,observe)
                record["known_public_method_capabilities"].append(
                    {"name":name,"observation_returned":got,**(value if got else {})})
            return record
        def raw_boolean_status_l5d2(label,kind,pair_factory,control_expected=None):
            row={"probe":label,"operation":kind,"completed":False,"classification":"unresolved",
                 "is_material_acceptance":False,"wrapper_null_was_not_converted_to_empty":True}
            report["raw_boolean_results"].append(row);save()
            a,b=pair_factory()
            row["inputs_before"]={"a":raw_signature(a),"b":raw_signature(b)};save()
            op=BRepAlgoAPI_Cut() if kind=="CUT" else BRepAlgoAPI_Common()
            arg=TopTools_ListOfShape();arg.Append(a.wrapped)
            tool=TopTools_ListOfShape();tool.Append(b.wrapped)
            op.SetArguments(arg);op.SetTools(tool);op.SetRunParallel(True)
            row["same_original_wrapper_parameters"]=True
            row["new_fuzzy_or_tolerance_or_nondestructive_option_set"]=False
            row["actual_Python_wrapper_capabilities"]=interface_capabilities(label,op,
                ("RunParallel","FuzzyValue","NonDestructive","CheckInverted","Build",
                 "IsDone","HasErrors","HasWarnings","GetReport","Shape"))
            save()
            for name in ("RunParallel","FuzzyValue","NonDestructive","CheckInverted"):
                got,value,rec=checkpointed_native_method(attempt,label+".parameter."+name,op,name)
                row.setdefault("actual_native_parameters",{})[name]=value if got else {"observation_failed":True}
                save()
            next_build(label)
            build_ok,_,rec=checkpointed_native_method(attempt,label+".Build",op,"Build")
            row["Build_returned"]=build_ok;save()
            flags={}
            for name in ("IsDone","HasErrors","HasWarnings"):
                got,value,rec=checkpointed_native_method(attempt,label+"."+name,op,name)
                if got:require(type(value) is bool,"Boolean kernel status must be a native bool")
                flags[name]=value if got else None
                row[name]=flags[name];save()
            selected(label+".Build_IsDone_without_errors",
                     build_ok and flags["IsDone"] is True and flags["HasErrors"] is False)
            got,native_report,rec=checkpointed_native_method(attempt,label+".GetReport",op,"GetReport")
            row["GetReport_returned"]=got and native_report is not None;save()
            if got and native_report is not None:
                for gravity in ("Message_Fail","Message_Warning"):
                    got_types,types,rec=attempt(label+".GetReport."+gravity,
                        lambda gravity=gravity:alert_types(native_report,gravity))
                    row.setdefault("native_alert_types",{})[gravity]=types if got_types else {"complete":False}
                    save()
            # Observation isolation: no Builder or DSFiller call is made.
            # The previous SIGSEGV cause remains unknown. Missing wrapper
            # statuses remain unavailable and keep the strict gate false.
            row["optional_child_algorithm_calls_omitted"]=True
            row["omission_proves_prior_crash_cause"]=False
            save()
            got,raw,rec=checkpointed_native_method(attempt,label+".Shape",op,"Shape")
            row["raw_Shape_returned"]=got;save()
            if got:
                null_ok,is_null,rec=checkpointed_native_method(attempt,label+".Shape.IsNull",raw,"IsNull")
                row["raw_Shape_IsNull"]=is_null if null_ok else None;save()
                if null_ok and is_null:
                    row["classification"]="null_result_not_accepted"
                    row["null_result_has_no_serializable_material_shape"]=True
                    row["original_material_guard_passed"]=False
                    row["legitimate_empty_material_proved"]=False
                    selected(label+".nonnull_original_material_result",False)
                elif null_ok:
                    cast_ok,body,rec=attempt(label+".nonnull_Shape_cast",lambda:cq.Shape.cast(raw))
                    if cast_ok:
                        row["result_BREP"]=keep(label+"-result.brep",body)
                        mat_ok,mat=validate_material(label+".original_whole_material_result",body,True)
                        row["original_material_guard_passed"]=mat_ok
                        if mat_ok:
                            leaves,volume=mat
                            valid_empty=not leaves and volume==0
                            row["legitimate_empty_material_proved"]=valid_empty
                            row["original_signed_material_volume_mm3"]=volume
                            row["original_solid_count"]=len(leaves)
                            kernel_ok=build_ok and flags["IsDone"] is True and flags["HasErrors"] is False
                            row["raw_build_success_and_original_material"]=kernel_ok
                            row["classification"]=("valid_empty_material" if valid_empty else "valid_positive_material") if kernel_ok else "valid_material_with_failed_or_unresolved_build"
                            if kind=="COMMON":
                                va=p.volume(a);vb=p.volume(b)
                                bound_ok=volume<=min(va,vb)+1e-7
                                row["original_Common_upper_bound_gate_passed"]=bound_ok
                                selected(label+".original_Common_upper_bound",bound_ok)
                            if control_expected is not None:
                                if control_expected==0:
                                    passed=kernel_ok and valid_empty
                                else:
                                    passed=kernel_ok and len(leaves)==1 and volume>0 and abs(volume-control_expected)<=1e-7
                                row["fixed_control_original_predicate_passed"]=passed
                                selected(label+".fixed_control_original_predicate",passed)
                        else:row["classification"]="non_null_invalid_original_material"
                    else:
                        row["classification"]="non_null_cast_failed"
                        row["original_material_guard_passed"]=False
                        selected(label+".nonnull_original_material_result",False)
            # Original defaults may modify subshape data. Preserve observations
            # and post-operation BREPs; a later probe always reimports originals.
            for role,shape in (("a",a),("b",b)):
                row.setdefault("inputs_after",{})[role]=raw_signature(shape);save()
                if label.startswith("actual-"):
                    row.setdefault("post_operation_input_BREPs",{})[role]=keep(label+"-after-"+role+".brep",shape)
            row["status_observation_complete"]=(
                row.get("GetReport_returned") is True and row.get("raw_Shape_returned") is True and
                type(row.get("raw_Shape_IsNull")) is bool and
                all(type(row.get(x)) is bool for x in ("IsDone","HasErrors","HasWarnings")) and
                all("type_names" in row.get("native_alert_types",{}).get(g,{}) for g in ("Message_Fail","Message_Warning")))
            row["completed"]=True;save()
            selected(label+".complete_status_and_alert_observations",row["status_observation_complete"])
        raw_boolean_status_l5d2("actual-cut","CUT",lambda:original_pair("actual-cut"))
        raw_boolean_status_l5d2("actual-common","COMMON",lambda:original_pair("actual-common"))
        raw_boolean_status_l5d2("actual-reverse-cut","CUT",lambda:original_pair("actual-reverse-cut",True))
        raw_boolean_status_l5d2("control-empty","CUT",lambda:box_pair("control-empty"),0)
        raw_boolean_status_l5d2("control-nonempty","CUT",lambda:box_pair("control-nonempty"),1)
        require(report["Boolean_build_calls_started"]==6,"complete fixed six-build inventory required")
        report["diagnostic_observations_completed"]=(
            len(report["raw_boolean_results"])==5 and all(x["completed"] for x in report["raw_boolean_results"]))
        report["all_raw_status_and_alert_records_complete"]=all(x["status_observation_complete"] for x in report["raw_boolean_results"])
        report["execution_completed"]=report["diagnostic_observations_completed"]
        report["all_selected_original_operation_guards_passed"]=all(x["passed"] for x in report["selected_original_guard_results"])
        report["named_safe_state_wrapper_proves_containment"]=False
        report["original_null_failure_repaired"]=False
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
        "all_selected_original_operation_guards_passed","original_CadQuery_null_failure_reproduced",
        "source_runtime_unchanged","external_source_unchanged","elapsed_seconds")}),flush=True)
    return 0 if (report["execution_completed"] and report["all_selected_original_operation_guards_passed"]
        and report["source_runtime_unchanged"] and report["external_source_unchanged"]
        and not report.get("diagnostic_failure") and not report.get("capacity_failure")
        and not report.get("postflight_failure") and report["scientific_retention_complete"]) else 2

if __name__=="__main__":
    raise SystemExit(main())
