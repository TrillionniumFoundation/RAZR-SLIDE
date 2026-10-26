"""Independent N8 readback: original arrays, native five gates, exact row sums.

Does not import the producer or its candidate-selection/acceptance functions.
Each affected equation is summed directly from the original coefficients and
candidate field, rather than trusting the producer's cached exact delta.
"""
from pathlib import Path
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
import math
import resource
import re
import subprocess
import time
import numpy as np
from scipy.sparse import load_npz
from n8_contract import (S4,S4_TREE,ND,NF,FIXED,LIMIT,MAX_FULL,MAX_SCALAR,MAX_ROW_SUPPORT,
 MAX_CACHE_ROWS,MAX_EXACT_TERMS,MAX_READER_EXACT_TERMS,MAX_CACHE_BYTES,MAX_FRACTION_BITS,
 AS_BYTES,KFF_SHA,K_SHA,C_SHA,HELPER,HELPER_SHA,POINT_SOURCE,POINT_SOURCE_SHA,
 ANCHOR_SEED_DOF,BASE_FIELDS_PREFIX,BASE_FIELD_SHA,
 GateError,require,sha_file,bits,verify_frozen_files,write_json)

def Q(value):
    n,d=float(value).as_integer_ratio()
    return Fraction(n,d)

def unpack(record):
    require(set(record)=={"numerator","denominator"},"reader_exact_record_keys")
    result=Fraction(int(record["numerator"]),int(record["denominator"]))
    require(max(result.numerator.bit_length(),result.denominator.bit_length())<=MAX_FRACTION_BITS,
            "reader_exact_integer_cap")
    return result

def run(args):
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(AS_BYTES,AS_BYTES))
    case=args.case.resolve(strict=True); root=args.root.resolve(strict=True)
    result={"schema":"razr-N8-independent-five-probe-readback-v1","completed":False,
        "producer_completed":False,"partial_evidence_verified":False,"original_five_qualification_verified":False,
        "producer_numerical_code_imported":False,"shared_code_scope":"frozen constants and bounded file I/O only",
        "original_gate":LIMIT,"baseline_sets_checked":0,"full_candidate_sets_checked":0,
        "final_sets_checked":0,"scalar_screens_checked":0,"exact_affected_equations_directly_checked":0,
        "direct_exact_product_terms":0,"accepted_trial_indices":[],"native_float64_gate_evaluations":0,
        "initial_anchor_seed_verified":False,"unaffected_anchor_pairs_directly_checked":0,
        "accepted_global_anchor_certificates":0,"per_candidate_frozen_references_verified":0}
    def safe(name):
        p=case/name
        require(isinstance(name,str) and not Path(name).is_absolute() and ".." not in Path(name).parts
                and p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(case),"reader_relative_regular_file")
        return p
    def load_array(name,shape):
        a=np.load(safe(name),allow_pickle=False)
        require(a.shape==shape and a.dtype==np.float64 and np.isfinite(a).all(),"reader_array_shape_finiteness")
        return a
    def same(actual,record,code):
        require(actual==record,code)
    try:
        identity=verify_frozen_files(case)
        report_path=case/"probe-N8/N8_REPORT.json"
        report=json.loads(report_path.read_text())
        result["producer_report_identity"]={"bytes":report_path.stat().st_size,"sha256":sha_file(report_path)}
        result["producer_completed"]=report["completed"]
        require(report["schema"]=="razr-N8-finite-original-five-probe-v1"
                and report["functional_source_commit"]==S4 and report["functional_source_tree"]==S4_TREE
                and report["original_gate"]==LIMIT and report["select_best_history"] is False
                and report["original_K_sha256"]==K_SHA and report["original_C_sha256"]==C_SHA
                and report["full_candidate_limit"]==MAX_FULL and report["scalar_screen_limit"]==MAX_SCALAR
                and report["target_support_limit"]==MAX_ROW_SUPPORT,"reader_producer_contract")
        require(sha_file(root/HELPER)==HELPER_SHA and sha_file(root/POINT_SOURCE)==POINT_SOURCE_SHA
                and subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==S4
                and subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=root,text=True).strip()==S4_TREE,
                "reader_functional_original_source")
        frozen=case/"frozen/frozen"; p=frozen/"probe-N5"; volume=frozen/"volume/panel/level-2"
        fixed=np.load(p/"fixed-original-DOFs.npy",allow_pickle=False)
        free=np.load(p/"free-original-DOFs.npy",allow_pickle=False)
        require(fixed.dtype==free.dtype==np.int64 and tuple(int(x) for x in fixed)==FIXED
                and len(set(int(x) for x in fixed))==6 and np.array_equal(free,np.setdiff1d(np.arange(ND),fixed))
                and len(free)==NF,"reader_original_fixed_free_order")
        with np.load(volume/"loads.npz",allow_pickle=False) as z:
            require(np.array_equal(z["D"],fixed),"reader_original_fixed_from_loads")
        model=json.loads((volume/"report.engineering.json").read_text())["selected_engineering_fields"]
        require(model["body"]=="panel" and model["level"]==2 and model["E_normalization"]==1.0
                and model["nu"]==0.3 and model["K_sha256"]==K_SHA
                and model["original_faces_and_surface_P2_traces_unchanged"] is True
                and model["body_loads_on_added_internal_DOFs"] is False,"reader_original_model")
        seed=json.loads(gzip.decompress((root/POINT_SOURCE).read_bytes()))
        require(seed["case"]==6 and seed["volume_level"]==2
                and seed["contact_points"]==json.loads((p/"points.json").read_text())
                and len(seed["contact_points"])==3885,"reader_original_points")
        C=load_npz(p/"C.npz")
        require(C.format=="csc" and C.shape==(ND,3885) and C.nnz==24518
                and C.dtype==np.float64 and C.has_canonical_format,"reader_C")
        directions=np.load(p/"five-probe-directions.npy",allow_pickle=False)
        rhs=np.load(p/"five-probe-rhs.npy",allow_pickle=False)
        require(directions.dtype==rhs.dtype==np.float64 and directions.shape==(3885,5) and rhs.shape==(ND,5),
                "reader_original_directions_RHS_shape")
        rng=np.random.default_rng(73021)
        expected=[np.ones(3885)]+[rng.choice([-1.,1.],3885) for _ in range(4)]
        for j,d in enumerate(expected):
            require(directions[:,j].tobytes()==d.tobytes()
                    and rhs[:,j].tobytes()==np.asarray(C@d).ravel().tobytes(),"reader_original_same_C_b_directions")
        rhs=rhs[free,:]
        K=load_npz(volume/"K.npz")
        require(K.format=="csc" and K.shape==(ND,ND) and K.nnz==23646483
                and K.dtype==np.float64 and K.has_canonical_format,"reader_original_K")
        A=K[free][:,free].tocsc();del K
        require(A.nnz==23645561,"reader_original_Kff_nnz")
        for key,digest in KFF_SHA.items():
            require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest()==digest,"reader_original_Kff_bytes")
        require(np.array_equal(A.diagonal(),np.load(p/"original-diagonal.npy",allow_pickle=False)),"reader_original_diagonal")
        E=A.astype(np.longdouble);R=A.tocsr()
        require(np.finfo(np.longdouble).eps<np.finfo(np.float64).eps,"reader_longdouble_diagnostic_type")
        initial=[load_array(f"{BASE_FIELDS_PREFIX}/probe-{j}-field.npy",(ND,)) for j in range(5)]
        current=initial.copy()
        def check_fields(fields,records,persisted=False):
            scores=[];errors=[]
            require(len(fields)==len(records)==5,"reader_exactly_five")
            for j,(u,rec) in enumerate(zip(fields,records)):
                require(np.all(u[fixed]==0.0),"reader_fixed_zero")
                uf=u[free]; b=rhs[:,j]; e=A@uf-b
                require(np.isfinite(e).all(),"reader_finite_native_residual")
                numerator=float(np.max(np.abs(e))); denominator=max(float(np.max(np.abs(b))),1.0)
                ratio=numerator/denominator;at=int(np.argmax(np.abs(e)))
                values={"probe_index":j,"threshold":LIMIT,"free_dof_residual_infinity_ratio":ratio,
                    "residual_numerator":numerator,"normalization_denominator":denominator,
                    "passes_original_threshold":bool(ratio<=LIMIT),"max_residual_original_dof":int(free[at]),
                    "signed_residual_at_max_dof":float(e[at]),"rhs_at_max_dof":float(b[at]),
                    "solution_infinity_norm":float(np.max(np.abs(uf))),
                    "rhs_free_sha256":hashlib.sha256(b.tobytes()).hexdigest(),
                    "solution_free_sha256":hashlib.sha256(uf.tobytes()).hexdigest(),
                    "residual_sha256":hashlib.sha256(e.tobytes()).hexdigest(),
                    "over_gate_row_count":int(np.count_nonzero(np.abs(e)/denominator>LIMIT)),
                    "longdouble_residual_ratio_diagnostic_only":
                        float(np.max(np.abs(E@uf.astype(np.longdouble)-b.astype(np.longdouble))))/denominator}
                for k,v in values.items():same(v,rec[k],"reader_actual_original_native_gate_record")
                if persisted:
                    stored=load_array(rec["residual_file"],(NF,))
                    require(stored.tobytes()==e.tobytes(),"reader_full_native_residual_array")
                    for label in ("field","residual"):
                        q=safe(rec[label+"_file"])
                        same({"bytes":q.stat().st_size,"sha256":sha_file(q)},rec[label+"_identity"],
                             "reader_candidate_original_file_identity")
                scores.append(values);errors.append(e)
                result["native_float64_gate_evaluations"]+=1
            return scores,errors
        def exact_row(row,u):
            lo,hi=map(int,R.indptr[row:row+2]);count=hi-lo
            result["direct_exact_product_terms"]+=count
            require(count<=1024 and result["direct_exact_product_terms"]<=MAX_READER_EXACT_TERMS+MAX_FULL*MAX_ROW_SUPPORT,
                    "reader_direct_exact_cost_cap")
            value=-Q(rhs[row,0])
            for k in range(lo,hi):value+=Q(R.data[k])*Q(u[free[R.indices[k]]])
            return value
        baseline=report.get("baseline")
        if baseline is None:
            require(report["completed"] is False,"reader_missing_baseline_only_partial")
            result["partial_evidence_verified"]=True
        else:
            scores,errors=check_fields(current,baseline)
            result["baseline_sets_checked"]=1
            require([v["passes_original_threshold"] for v in scores]==[False,True,True,True,True],"reader_original_rejected_start")
            for j,e in enumerate(errors):
                require(e.tobytes()==load_array(f"{BASE_FIELDS_PREFIX}/probe-{j}-residual.npy",(NF,)).tobytes(),
                        "reader_original_frozen_start_native_bitpattern")
            trials=report["trials"];stages=report["stages"]
            require(len(trials)<=MAX_FULL and len(stages)<=MAX_FULL,"reader_finite_full_and_stage_counts")
            require([t["trial_index"] for t in trials]==list(range(1,len(trials)+1)),"reader_trial_order")
            by_screen={t["screen_index"]:t for t in trials}
            require(len(by_screen)==len(trials),"reader_unique_trial_screens")
            screen_path=case/"probe-N8/N8_SCALAR_SCREENS.jsonl"
            if screen_path.exists():
                require(screen_path.stat().st_size<=16*1024**2,"reader_scalar_bytes_cap")
                screen_lines=screen_path.read_bytes().splitlines(keepends=True)
            else:screen_lines=[]
            truncated_last=False;screens=[]
            for line in screen_lines:
                try:screens.append(json.loads(line))
                except json.JSONDecodeError:
                    require(report["completed"] is False and line is screen_lines[-1],"reader_only_inflight_scalar_line_may_be_partial")
                    truncated_last=True
            require(len(screens)<=MAX_SCALAR,"reader_scalar_count_cap")
            base_ref=BASE_FIELDS_PREFIX+"/probe-0-field.npy";base_sha=sha_file(case/base_ref)
            require(base_sha==BASE_FIELD_SHA,"reader_N7_last_sequential_accepted_start")
            seed_indices=np.flatnonzero(free==ANCHOR_SEED_DOF)
            require(len(seed_indices)==1,"reader_original_free_anchor_seed")
            seed_index=int(seed_indices[0]);known_exact_current={};seed_cost=0
            seed_record=report.get("initial_anchor_seed")
            if seed_record is not None:
                seed_value=exact_row(seed_index,current[0])
                seed_cost=int(R.indptr[seed_index+1]-R.indptr[seed_index])
                require(seed_record["base_field_sha256"]==base_sha and seed_record["free_row_index"]==seed_index
                        and seed_record["original_row_DOF"]==ANCHOR_SEED_DOF
                        and unpack(seed_record["signed_exact_residual"])==seed_value
                        and seed_record["direct_original_row_product_terms"]==seed_cost,
                        "reader_initial_anchor_seed_direct_original_equation")
                known_exact_current[seed_index]=seed_value;result["initial_anchor_seed_verified"]=True
            else:
                require(report["completed"] is False and not trials and not stages,
                        "reader_only_pretrial_partial_may_lack_seed")
            active=None;position=0;after_accept=False;passed=False;registered_reader_cost=seed_cost
            checked_trials=set();stage_screen_counts={}
            for index,screen in enumerate(screens,1):
                require(not passed,"reader_first_pass_stops")
                require(screen["schema"]=="razr-N8-virtual-row-screen-v1" and screen["screen_index"]==index,
                        "reader_screen_chronology")
                stage_index=screen["stage_index"]
                require(1<=stage_index<=len(stages),"reader_stage_exists")
                stage=stages[stage_index-1]
                if active!=stage_index:
                    require(active is None and stage_index==1 or after_accept and stage_index==active+1,
                            "reader_only_new_stage_after_accepted_current_state")
                    require(stage["stage_index"]==stage_index and stage["base_field_file"]==base_ref
                            and stage["base_field_sha256"]==base_sha,"reader_current_state_identity")
                    target=int(np.argmax(np.abs(errors[0])))
                    same(target,stage["target_free_index"],"reader_current_worst_row")
                    same(int(free[target]),stage["target_original_DOF"],"reader_current_original_worst_DOF")
                    same(max(r["free_dof_residual_infinity_ratio"] for r in scores),stage["base_global_ratio"],"reader_stage_base_gate")
                    same(scores[0]["over_gate_row_count"],stage["base_probe0_violation_count"],"reader_stage_base_violations")
                    lo,hi=map(int,R.indptr[target:target+2]);cols=R.indices[lo:hi];co=R.data[lo:hi]
                    require(len(cols)<=MAX_ROW_SUPPORT and np.all(cols[1:]>cols[:-1]),"reader_original_sorted_row_support")
                    same([{"free_column_index":int(j),"original_column_DOF":int(free[j]),"coefficient_hex":float(a).hex()}
                          for j,a in zip(cols,co)],stage["ordered_support"],"reader_original_support_entries")
                    vals=[float(current[0][free[j]]) for j in cols]
                    total=0.0
                    for a,u in zip(co,vals):total=total+float(a)*u
                    require(bits(total-float(rhs[target,0]))==bits(errors[0][target]),"reader_native_scalar_order_replay")
                    exact_before=exact_row(target,current[0])
                    if target in known_exact_current:
                        require(known_exact_current[target]==exact_before,"reader_known_current_target_exact_consistency")
                    known_exact_current[target]=exact_before
                    position=0;active=stage_index;after_accept=False
                require(not after_accept,"reader_no_old_stage_after_accept")
                at=position//2;direction=-1 if position%2==0 else 1
                require(at<len(cols) and screen["support_index"]==at and screen["direction"]==direction
                        and screen["base_field_sha256"]==base_sha
                        and screen["original_free_column_DOF"]==int(free[cols[at]])
                        and screen["target_original_DOF"]==int(free[target]),"reader_deterministic_column_direction_order")
                old=vals[at];new=math.nextafter(old,-math.inf if direction==-1 else math.inf)
                delta=Q(new)-Q(old);after=exact_before+Q(co[at])*delta
                total=0.0
                for n,(a,u) in enumerate(zip(co,vals)):total=total+float(a)*(new if n==at else u)
                predicted=total-float(rhs[target,0]);ratio=abs(predicted)/scores[0]["normalization_denominator"]
                eligible=ratio<=LIMIT and abs(after)<=abs(exact_before)
                require(screen["old_value_hex"]==old.hex() and screen["adjacent_value_hex"]==new.hex()
                        and screen["actual_delta_hex"]==float(delta).hex() and screen["actual_ULP_distance"]==1
                        and screen["predicted_original_order_float64_residual_bits"]==bits(predicted)
                        and screen["predicted_original_order_float64_residual"]==predicted
                        and screen["predicted_row_ratio"]==ratio
                        and unpack(screen["exact_row_before"])==exact_before and unpack(screen["exact_row_after"])==after
                        and screen["row_only_gate_predicted"]==(ratio<=LIMIT)
                        and screen["exact_row_absolute_nonincrease"]==(abs(after)<=abs(exact_before))
                        and screen["eligible_for_full_candidate"]==eligible
                        and screen["native_full_gate_evaluated_by_this_screen"] is False,"reader_all_virtual_predictions_exact")
                position+=1;stage_screen_counts[stage_index]=position;result["scalar_screens_checked"]+=1
                if not eligible:
                    require(index not in by_screen,"reader_no_ineligible_full_trial");continue
                t=by_screen.get(index)
                if t is None or not t["complete"]:
                    require(report["completed"] is False and index==len(screens),"reader_only_last_inflight_candidate_may_be_incomplete")
                    continue
                require(t["stage_index"]==stage_index and t["base_field_file"]==base_ref
                        and t["base_field_sha256"]==base_sha and t["original_changed_DOF"]==int(free[cols[at]])
                        and t["actual_ULP_distance"]==1,"reader_trial_binds_current_scalar")
                prefix=f"probe-N8/trial-{t['trial_index']:02d}"
                require(t["probes"][0]["field_file"]==prefix+"/probe-0-field.npy"
                        and t["probes"][0]["residual_file"]==prefix+"/probe-0-residual.npy"
                        and t["probes"][0]["scientific_storage"]=="separate_actual_original_array_bytes"
                        and t["requested_update_file"]==prefix+"/requested-update.npy"
                        and t["actual_update_file"]==prefix+"/actual-update.npy",
                        "reader_separate_original_candidate_and_update_files")
                for j in range(1,5):
                    rec=t["probes"][j]
                    for label in ("field","residual"):
                        source_name=f"probe-N7/final/probe-{j}-{label}.npy"
                        require(rec[label+"_file"]=="frozen/"+source_name
                                and rec[label+"_identity"]==identity[source_name],
                                "reader_exact_frozen_original_reference_path_and_identity")
                    require(rec["scientific_storage"]=="explicit_frozen_original_field_and_residual_reference"
                            and rec["new_native_residual_equals_frozen_original_array_bytes"] is True,
                            "reader_explicit_reference_storage_policy")
                candidate=[load_array(x["field_file"],(ND,)) for x in t["probes"]]
                wanted=current[0].copy();wanted[free[cols[at]]]=new
                require(candidate[0].tobytes()==wanted.tobytes(),"reader_exact_one_coordinate_candidate")
                for j in range(1,5):
                    require(candidate[j].tobytes()==initial[j].tobytes()
                            and sha_file(safe(t["probes"][j]["field_file"]))==identity[f"probe-N7/final/probe-{j}-field.npy"]["sha256"],
                            "reader_four_original_pass_array_and_file_bytes")
                request=np.zeros(ND,dtype=np.float64);request[free[cols[at]]]=float(delta)
                actual=candidate[0]-current[0]
                require(actual.tobytes()==request.tobytes() and np.count_nonzero(actual)==1
                        and load_array(t["requested_update_file"],(ND,)).tobytes()==request.tobytes()
                        and load_array(t["actual_update_file"],(ND,)).tobytes()==actual.tobytes(),"reader_full_requested_actual_updates")
                same(t["update_observation"],{"requested_nonzero_DOFs":1,"actually_changed_DOFs":1,
                    "rounded_away_nonzero_requests":0,"actual_ULP_distance":1,
                    "actual_update_infinity_norm":float(np.max(np.abs(actual))),
                    "requested_update_infinity_norm":float(np.max(np.abs(request)))},"reader_update_ULP_observation")
                new_scores,new_errors=check_fields(candidate,t["probes"],True)
                for j in range(1,5):
                    require(new_errors[j].tobytes()==load_array(f"{BASE_FIELDS_PREFIX}/probe-{j}-residual.npy",(NF,)).tobytes(),
                            "reader_every_new_native_residual_equals_original_frozen_reference")
                result["per_candidate_frozen_references_verified"]+=8
                require(bits(new_errors[0][target])==bits(predicted),"reader_full_native_matches_prediction")
                column=int(cols[at]);aa,bb=map(int,A.indptr[column:column+2])
                rows=A.indices[aa:bb];coeff=A.data[aa:bb];mask=coeff!=0.0;rows=rows[mask];coeff=coeff[mask]
                proof=t["exact_affected_proof"];details=proof["all_affected_rows"]
                require(len(rows)<=512 and len(details)==len(rows)==proof["affected_row_count"],"reader_all_affected_rows_count")
                old_max=Fraction();new_max=Fraction();exact_after_values={}
                affected_cost=2*sum(int(R.indptr[int(i)+1]-R.indptr[int(i)]) for i in rows)
                for i,a,rec in zip(rows,coeff,details):
                    i=int(i);bq=exact_row(i,current[0]);aq=exact_row(i,candidate[0])
                    require(rec["free_row_index"]==i and rec["original_row_DOF"]==int(free[i])
                            and rec["original_coefficient_hex"]==float(a).hex()
                            and unpack(rec["before"])==bq and unpack(rec["after"])==aq
                            and aq-bq==Q(a)*delta,"reader_every_affected_original_equation_direct")
                    old_max=max(old_max,abs(bq));new_max=max(new_max,abs(aq))
                    if i in known_exact_current:
                        require(known_exact_current[i]==bq,"reader_known_current_affected_exact_consistency")
                    known_exact_current[i]=bq;exact_after_values[i]=aq
                    result["exact_affected_equations_directly_checked"]+=1
                affected=set(map(int,rows));available=[i for i in known_exact_current if i not in affected]
                if seed_index in known_exact_current and seed_index not in affected and abs(known_exact_current[seed_index])>=new_max:
                    anchor_index=seed_index
                else:
                    anchor_index=max(available,key=lambda i:(abs(known_exact_current[i]),-int(free[i]))) if available else None
                anchor=proof["unaffected_exact_anchor"];anchor_ok=False;anchor_cost=0
                if anchor_index is None:
                    require(anchor is None,"reader_no_unaffected_known_row")
                else:
                    anchor_before=exact_row(anchor_index,current[0]);anchor_after=exact_row(anchor_index,candidate[0])
                    anchor_cost=2*int(R.indptr[anchor_index+1]-R.indptr[anchor_index])
                    anchor_ok=new_max<=abs(anchor_before)
                    require(anchor_index not in affected and anchor_before==anchor_after==known_exact_current[anchor_index],
                            "reader_anchor_outside_entire_original_column_and_directly_unchanged")
                    require(anchor["base_field_sha256"]==base_sha and anchor["free_row_index"]==anchor_index
                            and anchor["original_row_DOF"]==int(free[anchor_index])
                            and unpack(anchor["signed_exact_residual"])==anchor_before
                            and anchor["outside_complete_changed_column_nonzero_support"] is True
                            and anchor["affected_after_max_bounded_by_anchor"]==anchor_ok
                            and unpack(anchor["exact_bound_margin"])==abs(anchor_before)-new_max
                            and anchor["known_current_exact_pool_rows"]==len(known_exact_current)
                            and anchor["selection"]=="seed_if_sufficient_else_largest_absolute_unaffected_known_exact_row_first_original_DOF_tie"
                            and anchor["direct_reader_before_after_product_terms"]==anchor_cost,
                            "reader_full_exact_unaffected_anchor_certificate")
                    result["unaffected_anchor_pairs_directly_checked"]+=1
                cost=affected_cost+anchor_cost;registered_reader_cost+=cost
                require(affected_cost==proof["affected_direct_reader_product_terms"]
                        and cost==proof["direct_reader_product_terms_for_trial"]
                        and registered_reader_cost<=MAX_READER_EXACT_TERMS,
                        "reader_registered_direct_exact_cost_including_anchors")
                affected_ok=new_max<=old_max;exact_ok=affected_ok or anchor_ok
                require(unpack(proof["affected_exact_infinity_before"])==old_max
                        and unpack(proof["affected_exact_infinity_after"])==new_max
                        and proof["all_affected_exact_infinity_nonincrease"]==affected_ok
                        and proof["outside_affected_column_exact_equations_unchanged"] is True
                        and proof["unaffected_anchor_certificate_valid"]==anchor_ok
                        and proof["global_exact_infinity_nonincrease_certified"]==exact_ok
                        and proof["global_certificate_uses_anchor"]==(not affected_ok and anchor_ok),
                        "reader_global_exact_infinity_nonincrease_by_valid_explicit_certificate")
                require(len(known_exact_current)<=MAX_CACHE_ROWS,"reader_anchor_pool_row_cap")
                conditions={"global_exact_infinity_nonincrease_certificate":exact_ok,
                    "probe0_violation_count_strictly_decreases":new_scores[0]["over_gate_row_count"]<scores[0]["over_gate_row_count"],
                    "original_full_five_max_ratio_nonincrease":max(v["free_dof_residual_infinity_ratio"] for v in new_scores)
                        <=max(v["free_dof_residual_infinity_ratio"] for v in scores),
                    "other_four_original_gates_remain_passed":all(new_scores[j]["passes_original_threshold"] for j in range(1,5))}
                accepted=all(conditions.values())
                require(t["acceptance_conditions"]==conditions and t["accepted"]==accepted
                        and t["all_five_original_gates_passed"]==all(v["passes_original_threshold"] for v in new_scores),
                        "reader_complete_acceptance_rule")
                if accepted:
                    known_exact_current.update(exact_after_values)
                    if not affected_ok:result["accepted_global_anchor_certificates"]+=1
                    current=candidate;scores=new_scores;errors=new_errors
                    base_ref=t["probes"][0]["field_file"];base_sha=sha_file(safe(base_ref))
                    result["accepted_trial_indices"].append(t["trial_index"])
                    after_accept=True;passed=all(v["passes_original_threshold"] for v in scores)
                    require(stage["accepted_trial_index"]==t["trial_index"] and stage["status"]=="accepted","reader_accepted_stage_record")
                checked_trials.add(t["trial_index"]);result["full_candidate_sets_checked"]+=1
            require(set(t["trial_index"] for t in trials if t["complete"])==checked_trials,"reader_all_complete_trials_checked")
            same(result["accepted_trial_indices"],report["accepted_trial_indices"],"reader_sequential_acceptance_history")
            if report["completed"]:
                require(not truncated_last and len(screens)==report["scalar_screen_count"]
                        and all(t["complete"] for t in trials),"reader_complete_bounded_record_set")
                for st in stages:
                    count=stage_screen_counts.get(st["stage_index"],0)
                    require(st["last_screen_index"]-st["first_screen_index"]+1==count,"reader_stage_screen_count")
                terminal=report["termination"]
                if terminal=="first_accepted_state_passing_all_five":require(passed,"reader_first_pass_terminal")
                elif terminal=="96_full_candidate_limit":require(len(trials)==MAX_FULL and not passed,"reader_fixed_full_trial_terminal")
                elif terminal=="finite_current_target_candidates_exhausted":
                    require(not passed and not after_accept and position==2*len(cols),"reader_complete_finite_target_exhaustion")
                else:raise GateError("reader_unknown_complete_termination")
                final=[load_array(x["field_file"],(ND,)) for x in report["final"]]
                for j in range(5):require(final[j].tobytes()==current[j].tobytes(),"reader_final_current_state_not_history_best")
                final_scores,final_errors=check_fields(final,report["final"],True)
                for x,y in zip(final_errors,errors):require(x.tobytes()==y.tobytes(),"reader_final_same_native_residual")
                require(report["final_sequential_base_field_file"]==base_ref
                        and report["final_sequential_base_field_sha256"]==base_sha,"reader_final_state_source_binding")
                result["final_sets_checked"]=1
                result["final_original_ratios"]=[v["free_dof_residual_infinity_ratio"] for v in final_scores]
                result["original_five_qualification_verified"]=all(v["passes_original_threshold"] for v in final_scores)
                same(result["original_five_qualification_verified"],report["original_five_passed"],"reader_final_original_qualification")
            else:
                require(report["original_five_passed"] is False,"reader_partial_never_qualifies")
                result["partial_evidence_verified"]=True
            counters=report.get("exact_capacity_counters",{})
            require(counters.get("cached_rows",0)<=MAX_CACHE_ROWS and counters.get("exact_product_terms",0)<=MAX_EXACT_TERMS
                    and counters.get("direct_reader_exact_terms_registered",0)<=MAX_READER_EXACT_TERMS
                    and counters.get("cache_storage_estimate_bytes",0)<=MAX_CACHE_BYTES,"reader_actual_capacity_counters")
        checked=0
        for name,expected in report.get("files",{}).items():
            pth=safe(name)
            same({"bytes":pth.stat().st_size,"sha256":sha_file(pth)},expected,"reader_retained_file_actual_identity")
            checked+=1
        extra = []
        pattern = re.compile(r"probe-N8/(?:(?:trial-(?:0[1-9]|[1-8][0-9]|9[0-6])/(?:probe-[0-4]-(?:field|residual)|requested-update|actual-update))|(?:final/probe-[0-4]-(?:field|residual)))\.npy(?:\.writing)?$")
        for q in sorted((case/"probe-N8").rglob("*")):
            name=q.relative_to(case).as_posix()
            if q.is_file() and pattern.fullmatch(name) and name not in report.get("files",{}):
                safe(name)
                extra.append({"file":name,"bytes":q.stat().st_size,"sha256":sha_file(q),
                              "full_native_equation_validation_available":False})
        result["incomplete_or_uncommitted_scientific_array_identities"]=extra
        result["retained_declared_arrays_hash_checked"]=checked
        result["uncompleted_array_policy"]="Exporter separately hashes every allowlisted actual complete or .writing array, including any not yet committed to producer records; no incomplete file qualifies."
        for key,digest in KFF_SHA.items():
            require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest()==digest,"reader_final_original_Kff_unchanged")
        for key in ("H_action_restore_executed","frame_inverse_executed","candidate_go","fixture_fabrication_go","manufacturing_go"):
            require(report[key] is False,"reader_no_downstream_release_claim")
        result["completed"]=True
    except BaseException as e:
        result["failure_type"]=type(e).__name__
        if isinstance(e,GateError):result["failure_gate"]=str(e)
        if isinstance(e,KeyError) and e.args and isinstance(e.args[0],str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,80}",e.args[0]):result["failure_key"]=e.args[0]
    result["elapsed_seconds"]=time.monotonic()-start
    result["peak_rss_KiB"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_json(args.output,result)
    return 0 if result["completed"] else 2

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--case",type=Path,required=True);p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
