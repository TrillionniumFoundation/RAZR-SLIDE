"""Independent N10 readback, including every virtual rejection and full trial.

Only identities and bounded I/O are shared with the producer. Candidate positions
are decoded arithmetically, all virtual rows are re-summed in original CSC column
order, and each actual candidate's affected equations and unchanged anchor are
also summed directly as Fractions from its complete original-domain field.
"""
from pathlib import Path
import argparse
from fractions import Fraction
import gzip
import hashlib
import heapq
import json
import math
import resource
import re
import subprocess
import sys
import time
import numpy as np
from scipy.sparse import load_npz
from n10_contract import (S4,S4_TREE,ND,NF,FIXED,LIMIT,MAX_FULL,MAX_SCALAR,MAX_ROW_SUPPORT,
 MAX_CACHE_ROWS,MAX_EXACT_TERMS,MAX_READER_EXACT_TERMS,MAX_CACHE_BYTES,MAX_FRACTION_BITS,
 AS_BYTES,KFF_SHA,K_SHA,C_SHA,HELPER,HELPER_SHA,POINT_SOURCE,POINT_SOURCE_SHA,
 ANCHOR_SEED_DOF,BASE_FIELDS_PREFIX,BASE_FIELD_SHA,INPUT_PAYLOAD_PREFIX,
 ULP_STEPS,MAX_FLOAT_TERMS,MAX_INCREMENT_TERMS,MAX_AFFECTED_ROWS,INITIAL_VIOLATION_COUNT,WALL_SECONDS,
 GateError,require,sha_file,bits,verify_frozen_files,write_json)

def Q(value):
    n,d=float(value).as_integer_ratio()
    return Fraction(n,d)

def packed(value):
    require(max(value.numerator.bit_length(),value.denominator.bit_length())<=MAX_FRACTION_BITS,
            'reader_exact_integer_cap')
    return {'numerator':str(value.numerator),'denominator':str(value.denominator)}

def unpack(record):
    require(set(record)=={'numerator','denominator'},'reader_exact_record_keys')
    value=Fraction(int(record['numerator']),int(record['denominator']))
    require(packed(value)==record,'reader_canonical_exact_record')
    return value

def specification_at(position,columns,target,primary):
    """Decode a one-based finite position without the producer's generator."""
    n=len(columns);offset=position-1
    require(0<=offset<8*n+8*(n-1),'reader_finite_stage_position')
    if offset<8*n:
        radius,within=divmod(offset,2*n)
        column,sign=divmod(within,2)
        return 'single',[(int(columns[column]),(-1,1)[sign],ULP_STEPS[radius])]
    remaining=[int(j) for j in columns if int(j)!=target]
    radius,within=divmod(offset-8*n,2*len(remaining))
    column,sign=divmod(within,2)
    return 'paired',[(target,primary,1),(remaining[column],(-1,1)[sign],ULP_STEPS[radius])]

class ReplayStage:
    def __init__(self,A,R,b,u,error,free,base_sha,scores,cost,guard,direct_exact):
        self.A,self.R,self.b,self.u,self.error,self.free=A,R,b,u,error,free
        self.sha,self.scores,self.cost,self.guard=base_sha,scores,cost,guard
        self.direct_exact=direct_exact;self.row_cache={};self.exact_cache={};self.storage=0
        self.den=scores[0]['normalization_denominator'];self.bad=scores[0]['over_gate_row_count']
        self.old_max=max(r['free_dof_residual_infinity_ratio'] for r in scores)
        self.other_max=max(r['free_dof_residual_infinity_ratio'] for r in scores[1:])
        # An independent heap selection, not the producer's NumPy partition.
        self.highest=heapq.nlargest(MAX_AFFECTED_ROWS+1,range(len(error)),key=lambda i:abs(float(error[i])))
        seed=[int(i) for i in np.flatnonzero(free==ANCHOR_SEED_DOF)]
        require(len(seed)==1,'reader_unique_original_anchor_seed')
        self.seed=seed[0];self.exact(self.seed)

    def float_charge(self,count):
        require(self.cost['float64_scalar_product_terms']+count<=MAX_FLOAT_TERMS,
                'reader_finite_virtual_float_work')
        self.cost['float64_scalar_product_terms']+=count

    def row(self,i):
        i=int(i)
        if i not in self.row_cache:
            self.guard();begin,end=map(int,self.R.indptr[i:i+2]);n=end-begin
            require(n<=1024 and len(self.row_cache)<MAX_CACHE_ROWS,'reader_stage_row_cache_bound')
            columns=self.R.indices[begin:end];coeff=self.R.data[begin:end];values=self.u[columns].copy()
            self.float_charge(n);total=0.0
            for a,u in zip(coeff,values):total=total+float(a)*float(u)
            require(bits(total-float(self.b[i]))==bits(self.error[i]),'reader_original_current_row_native_bits')
            entry=(columns,coeff,values)
            self.storage+=256+sys.getsizeof(entry)+sum(sys.getsizeof(v)+v.nbytes for v in entry)
            require(self.storage<=MAX_CACHE_BYTES,'reader_stage_cache_memory')
            self.row_cache[i]=entry
            self.cost['current_rows_native_bitmatched']+=1
            self.cost['stage_row_cache_peak']=max(self.cost['stage_row_cache_peak'],len(self.row_cache))
            self.cost['stage_cache_accounted_peak_bytes']=max(self.cost['stage_cache_accounted_peak_bytes'],self.storage)
        return self.row_cache[i]

    def dot(self,i,changes):
        columns,coeff,values=self.row(i);self.float_charge(len(columns));total=0.0
        # Explicit multiplication then addition; never compensated sum or dot.
        for k in range(len(columns)):
            j=int(columns[k]);value=changes[j] if j in changes else float(values[k])
            product=float(coeff[k])*value;total=total+product
        return total-float(self.b[i])

    def exact(self,i):
        i=int(i)
        if i not in self.exact_cache:
            count=len(self.row(i)[0])
            require(self.cost['exact_current_product_terms']+count<=MAX_EXACT_TERMS,
                    'reader_exact_current_cost')
            self.cost['exact_current_product_terms']+=count
            value=self.direct_exact(i,self.u)
            self.storage+=256+sys.getsizeof(value)+sys.getsizeof(value.numerator)+sys.getsizeof(value.denominator)
            require(self.storage<=MAX_CACHE_BYTES,'reader_combined_cache_memory')
            self.exact_cache[i]=value
            self.cost['stage_cache_accounted_peak_bytes']=max(self.cost['stage_cache_accounted_peak_bytes'],self.storage)
        return self.exact_cache[i]

    def evaluate(self,target,kind,spec):
        changes={};deltas={};descriptors=[]
        require(len(spec) in (1,2) and len({x[0] for x in spec})==len(spec),'reader_unique_changed_coordinates')
        for j,direction,distance in spec:
            require(direction in (-1,1) and distance in ULP_STEPS,'reader_registered_ULP_change')
            old=float(self.u[j]);new=old
            for _ in range(distance):new=math.nextafter(new,math.copysign(math.inf,direction))
            delta=Q(new)-Q(old)
            require(math.isfinite(new) and bits(new)!=bits(old) and float(delta)==new-old,'reader_actual_representable_ULP')
            changes[j]=new;deltas[j]=delta
            descriptors.append({'free_column_index':j,'original_DOF':int(self.free[j]),'direction':direction,
                'ULP_steps':distance,'old_value_hex':old.hex(),'new_value_hex':new.hex(),'actual_delta_hex':float(delta).hex()})
        cols,coeff,_=self.row(target)
        target_coeff={int(j):float(a) for j,a in zip(cols,coeff)}
        before=self.exact(target);after=before
        require(self.cost['exact_increment_terms']+len(changes)<=MAX_INCREMENT_TERMS,'reader_finite_exact_increment_work')
        self.cost['exact_increment_terms']+=len(changes)
        for j,delta in deltas.items():after+=Q(target_coeff.get(j,0.0))*delta
        value=self.dot(target,changes);ratio=abs(value)/self.den
        decision={'candidate_kind':kind,'coordinate_changes':descriptors,
            'predicted_target_residual_bits':bits(value),'predicted_target_ratio':ratio,
            'target_original_row_pass_predicted':ratio<=LIMIT,
            'exact_target_before':packed(before),'exact_target_after':packed(after),
            'all_affected_float64_predictions_evaluated':False,'exact_global_proof_evaluated':False,
            'eligible_for_full_candidate':False,'native_full_gate_evaluated_by_this_screen':False}
        if ratio>LIMIT:return decision,None,None,changes
        support={}
        for j in changes:
            begin,end=map(int,self.A.indptr[j:j+2]);selected={}
            for k in range(begin,end):
                if float(self.A.data[k])!=0.0:selected[int(self.A.indices[k])]=float(self.A.data[k])
            require(len(selected)<=MAX_AFFECTED_ROWS,'reader_complete_original_column_support_bound')
            support[j]=selected
        affected=sorted(set(i for entries in support.values() for i in entries))
        require(len(affected)<=MAX_AFFECTED_ROWS,'reader_complete_changed_union_bound')
        prediction={i:self.dot(i,changes) for i in affected}
        count=self.bad
        for i in affected:
            count-=int(abs(float(self.error[i]))/self.den>LIMIT)
            count+=int(abs(prediction[i])/self.den>LIMIT)
        changed_rows=set(affected)
        outside=max(abs(float(self.error[i])) for i in self.highest if i not in changed_rows)
        maximum=max([outside]+[abs(prediction[i]) for i in affected])/self.den
        five_max=max(maximum,self.other_max)
        progress=count<self.bad and five_max<=self.old_max
        digest=hashlib.sha256(json.dumps([[i,bits(prediction[i])] for i in affected],separators=(',',':')).encode()).hexdigest()
        decision.update(all_affected_float64_predictions_evaluated=True,affected_free_row_count=len(affected),
            predicted_affected_row_bits_sha256=digest,predicted_probe0_violation_count=count,
            predicted_probe0_max_ratio=maximum,predicted_full_five_max_ratio=five_max,
            original_full_float64_progress_predicted=progress)
        if not progress:return decision,None,prediction,changes
        self.cost['exact_increment_terms']+=len(affected)*len(changes)
        require(self.cost['exact_increment_terms']<=MAX_INCREMENT_TERMS,'reader_finite_joint_exact_increment_work')
        records=[];old_values=[];new_values=[]
        for i in affected:
            before=self.exact(i);after=before
            for j,delta in deltas.items():after+=Q(support[j].get(i,0.0))*delta
            old_values.append(abs(before));new_values.append(abs(after))
            records.append({'free_row_index':i,'original_row_DOF':int(self.free[i]),
                'changed_column_coefficients_hex':[{'free_column_index':j,'original_column_DOF':int(self.free[j]),
                    'coefficient_hex':support[j].get(i,0.0).hex()} for j in changes],
                'before':packed(before),'after':packed(after),
                'base_native_float64_residual_bits':bits(self.error[i]),
                'predicted_float64_residual_bits':bits(prediction[i])})
        old_max=max(old_values,default=Fraction());new_max=max(new_values,default=Fraction())
        available=[i for i in self.exact_cache if i not in changed_rows]
        anchor_index=None
        if self.seed in available and abs(self.exact_cache[self.seed])>=new_max:anchor_index=self.seed
        elif available:anchor_index=sorted(available,key=lambda i:(-abs(self.exact_cache[i]),int(self.free[i])))[0]
        anchor=None;anchor_ok=False
        if anchor_index is not None:
            exact=self.exact_cache[anchor_index];anchor_ok=abs(exact)>=new_max
            anchor={'base_field_sha256':self.sha,'free_row_index':anchor_index,
                'original_row_DOF':int(self.free[anchor_index]),'signed_exact_residual':packed(exact),
                'outside_complete_changed_columns_nonzero_support':True,
                'affected_after_max_bounded_by_anchor':anchor_ok,'exact_bound_margin':packed(abs(exact)-new_max),
                'known_current_exact_pool_rows':len(self.exact_cache)}
        ok=new_max<=old_max or anchor_ok
        proof={'all_affected_rows':records,'affected_row_count':len(affected),
            'affected_exact_infinity_before':packed(old_max),'affected_exact_infinity_after':packed(new_max),
            'all_affected_exact_infinity_nonincrease':new_max<=old_max,
            'outside_affected_columns_exact_equations_unchanged':True,
            'unaffected_exact_anchor':anchor,'unaffected_anchor_certificate_valid':anchor_ok,
            'global_exact_infinity_nonincrease_certified':ok,
            'global_certificate_uses_anchor':bool(new_max>old_max and anchor_ok)}
        digest=hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        decision.update(exact_global_proof_evaluated=True,exact_global_proof_sha256=digest,
            affected_exact_infinity_before=packed(old_max),affected_exact_infinity_after=packed(new_max),
            anchor_original_DOF=None if anchor is None else anchor['original_row_DOF'],
            anchor_exact_signed=None if anchor is None else anchor['signed_exact_residual'],
            global_exact_infinity_nonincrease_certified=ok,eligible_for_full_candidate=ok)
        return decision,proof,prediction,changes


def run(args):
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(AS_BYTES,AS_BYTES))
    case=args.case.resolve(strict=True); root=args.root.resolve(strict=True)
    result={"schema":"razr-N10-independent-five-probe-readback-v1","completed":False,
        "producer_completed":False,"partial_evidence_verified":False,"original_five_qualification_verified":False,
        "producer_numerical_code_imported":False,"shared_code_scope":"frozen constants and bounded file I/O only",
        "original_gate":LIMIT,"baseline_sets_checked":0,"full_candidate_sets_checked":0,
        "final_sets_checked":0,"scalar_screens_checked":0,"exact_affected_equations_directly_checked":0,
        "direct_exact_product_terms":0,"accepted_trial_indices":[],"native_float64_gate_evaluations":0,
        "initial_anchor_seed_verified":False,"unaffected_anchor_pairs_directly_checked":0,
        "accepted_global_anchor_certificates":0,"per_candidate_frozen_references_verified":0}
    def guard():
        require(time.monotonic()-start<WALL_SECONDS,"reader_original_180_second_wall")
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
        report_path=case/"probe-N10/N10_REPORT.json"
        report=json.loads(report_path.read_text())
        result["producer_report_identity"]={"bytes":report_path.stat().st_size,"sha256":sha_file(report_path)}
        result["producer_completed"]=report["completed"]
        require(report["schema"]=="razr-N10-finite-original-five-probe-v1"
                and report["functional_source_commit"]==S4 and report["functional_source_tree"]==S4_TREE
                and report["original_gate"]==LIMIT and report["select_best_history"] is False
                and report["original_K_sha256"]==K_SHA and report["original_C_sha256"]==C_SHA
                and report["full_candidate_limit"]==MAX_FULL and report["scalar_screen_limit"]==MAX_SCALAR
                and report["target_support_limit"]==MAX_ROW_SUPPORT
                and report["stop_on_first_unaccepted_full_candidate"] is True,"reader_producer_contract")
        require(sha_file(root/HELPER)==HELPER_SHA and sha_file(root/POINT_SOURCE)==POINT_SOURCE_SHA
                and subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==S4
                and subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=root,text=True).strip()==S4_TREE,
                "reader_functional_original_source")
        frozen=case/INPUT_PAYLOAD_PREFIX; p=frozen/"probe-N5"; volume=frozen/"volume/panel/level-2"
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
                guard()
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
        def exact_row(row,free_field):
            guard();lo,hi=map(int,R.indptr[row:row+2]);n=hi-lo
            require(n<=1024 and result['direct_exact_product_terms']+n<=MAX_READER_EXACT_TERMS,
                    'reader_original_total_direct_exact_work_cap')
            result['direct_exact_product_terms']+=n
            value=-Q(rhs[row,0])
            for k in range(lo,hi):value+=Q(R.data[k])*Q(free_field[int(R.indices[k])])
            packed(value)
            return value
        def json_lines(name,cap):
            path=case/'probe-N10'/name
            if not path.exists():return [],False
            safe(path.relative_to(case).as_posix())
            require(path.stat().st_size<=cap,'reader_virtual_record_bytes_bound')
            lines=path.read_bytes().splitlines(keepends=True);rows=[];tail=False
            require(len(lines)<=MAX_SCALAR,'reader_virtual_record_line_bound')
            for i,line in enumerate(lines):
                try:rows.append(json.loads(line))
                except json.JSONDecodeError:
                    require(not report['completed'] and i==len(lines)-1,
                            'reader_only_inflight_last_virtual_record_may_be_partial')
                    tail=True
            return rows,tail
        cost={'float64_scalar_product_terms':0,'exact_current_product_terms':0,'exact_increment_terms':0,
              'stage_row_cache_peak':0,'stage_cache_accounted_peak_bytes':0,'current_rows_native_bitmatched':0,
              'stage_cache_resets':0}
        result['virtual_attempts_checked']=0
        result['all_unselected_virtual_decisions_replayed']=False
        baseline=report.get('baseline')
        if baseline is None:
            require(report['completed'] is False,'reader_missing_baseline_only_partial')
            result['partial_evidence_verified']=True
        else:
            scores,errors=check_fields(current,baseline);result['baseline_sets_checked']=1
            require([v['passes_original_threshold'] for v in scores]==[False,True,True,True,True]
                    and scores[0]['over_gate_row_count']==INITIAL_VIOLATION_COUNT,'reader_same_actual_N9_rejected_start')
            for j,e in enumerate(errors):
                require(e.tobytes()==load_array(f'{BASE_FIELDS_PREFIX}/probe-{j}-residual.npy',(NF,)).tobytes(),
                        'reader_frozen_original_start_native_bits')
            native_bound=min(MAX_FULL,scores[0]['over_gate_row_count'])
            require(report['all_native_attempts_derived_bound']==native_bound,'reader_all_attempts_bound_includes_terminal_rejection')
            trials=report['trials'];stages=report['stages']
            require(len(trials)<=native_bound and len(stages)<=native_bound,'reader_original_finite_native_and_stage_bounds')
            require([t['trial_index'] for t in trials]==list(range(1,len(trials)+1)), 'reader_chronological_full_trials')
            by_screen={t['screen_index']:t for t in trials}
            require(len(by_screen)==len(trials),'reader_unique_full_trial_screen')
            screens,screen_tail=json_lines('N10_SCALAR_SCREENS.jsonl',16*1024**2)
            intents,intent_tail=json_lines('N10_SCREEN_ATTEMPTS.jsonl',8*1024**2)
            require(len(screens)<=len(intents)<=len(screens)+1,'reader_every_screen_has_prior_persisted_intent')
            require(report['scalar_screen_count']<=len(screens)
                    and report['virtual_attempts_started']<=len(intents),'reader_partial_report_counters_not_ahead_of_original_records')
            base_ref=BASE_FIELDS_PREFIX+'/probe-0-field.npy';base_sha=sha_file(safe(base_ref))
            require(base_sha==BASE_FIELD_SHA,'reader_actual_N9_last_accepted_start_file')
            active=0;position=0;replay=None;stage=None;after_accept=False;passed=False;terminal=False
            checked_trials=set();stage_counts={}
            def begin_stage(stage_index):
                nonlocal active,position,replay,stage,after_accept
                require(1<=stage_index<=len(stages),'reader_stage_record_exists')
                require((active==0 and stage_index==1) or (after_accept and stage_index==active+1),
                        'reader_new_stage_only_after_accepted_current_state')
                stage=stages[stage_index-1]
                require(stage['stage_index']==stage_index and stage['base_field_file']==base_ref
                        and stage['base_field_sha256']==base_sha,'reader_stage_base_original_file_binding')
                target=int(np.argmax(np.abs(errors[0])))
                require(stage['target_free_index']==target and stage['target_original_DOF']==int(free[target]),
                        'reader_original_current_worst_row_first_tie')
                same(stage['base_global_ratio'],max(r['free_dof_residual_infinity_ratio'] for r in scores),'reader_stage_original_five_max')
                same(stage['base_probe0_violation_count'],scores[0]['over_gate_row_count'],'reader_stage_original_violation_count')
                lo,hi=map(int,R.indptr[target:target+2]);columns=R.indices[lo:hi]
                require(len(columns)<=MAX_ROW_SUPPORT and np.all(columns[1:]>columns[:-1])
                        and float(A[target,target])>0.0,'reader_original_canonical_positive_diagonal_target')
                expected=[{'free_column_index':int(j),'original_column_DOF':int(free[j]),'coefficient_hex':float(a).hex()}
                          for j,a in zip(columns,R.data[lo:hi])]
                same(stage['ordered_support'],expected,'reader_complete_original_target_support')
                primary=-1 if errors[0][target]>0.0 else 1
                same(stage['primary_direction'],primary,'reader_primary_original_residual_direction')
                replay=ReplayStage(A,R,rhs[:,0],current[0][free],errors[0],free,base_sha,scores,cost,guard,exact_row)
                cost['stage_cache_resets']+=1
                seed={'base_field_sha256':base_sha,'free_row_index':replay.seed,'original_row_DOF':ANCHOR_SEED_DOF,
                      'signed_exact_residual':packed(replay.exact_cache[replay.seed])}
                same(seed,stage['anchor_seed'],'reader_current_field_bound_direct_seed')
                if stage_index==1:
                    same(seed,report['initial_anchor_seed'],'reader_initial_original_anchor_equation')
                    result['initial_anchor_seed_verified']=True
                same(stage['first_screen_index'],sum(stage_counts.values())+1,'reader_stage_first_screen')
                active=stage_index;position=0;after_accept=False
            def expected_intent(index,stage_index,next_position):
                target=stage['target_free_index']
                columns=[r['free_column_index'] for r in stage['ordered_support']]
                kind,spec=specification_at(next_position,columns,target,stage['primary_direction'])
                intent={'schema':'razr-N10-virtual-attempt-v1','screen_index':index,'stage_index':stage_index,
                    'stage_candidate_position':next_position,'base_field_sha256':base_sha,
                    'target_original_DOF':int(free[target]),'candidate_kind':kind,
                    'coordinate_specifications':[{'free_column_index':j,'original_DOF':int(free[j]),'direction':d,'ULP_steps':n}
                                                 for j,d,n in spec],
                    'native_full_gate_evaluated_by_this_record':False}
                return intent,kind,spec
            for index,screen in enumerate(screens,1):
                guard();require(not terminal and not passed,'reader_no_screen_after_first_pass_or_terminal_full_rejection')
                stage_index=screen['stage_index']
                require(not after_accept or stage_index==active+1,'reader_next_screen_starts_next_accepted_state_stage')
                if active!=stage_index:begin_stage(stage_index)
                position+=1
                intent,kind,spec=expected_intent(index,stage_index,position)
                same(intents[index-1],intent,'reader_actual_intent_matches_finite_chronological_position')
                result['virtual_attempts_checked']+=1
                decision,proof,prediction,changes=replay.evaluate(stage['target_free_index'],kind,spec)
                expected={'schema':'razr-N10-virtual-support-screen-v1','screen_index':index,'stage_index':stage_index,
                    'stage_candidate_position':position,'base_field_sha256':base_sha,
                    'target_original_DOF':stage['target_original_DOF'],**decision}
                same(screen,expected,'reader_every_scalar_prediction_and_exact_eligibility_rederived')
                result['scalar_screens_checked']+=1;stage_counts[stage_index]=stage_counts.get(stage_index,0)+1
                if not decision['eligible_for_full_candidate']:
                    require(index not in by_screen,'reader_ineligible_screen_never_promoted_to_native')
                    continue
                trial=by_screen.get(index)
                if trial is None:
                    require(not report['completed'] and index==len(screens),
                            'reader_first_eligible_requires_immediate_full_trial_or_last_partial_stop')
                    terminal=True;continue
                require(trial['trial_index']==len(checked_trials)+1 and trial['stage_index']==stage_index
                        and trial['base_field_file']==base_ref and trial['base_field_sha256']==base_sha
                        and trial['coordinate_changes']==decision['coordinate_changes'],
                        'reader_full_trial_is_first_current_eligible_candidate')
                same(trial['exact_affected_proof'],proof,'reader_full_complete_column_proof_rederived')
                proof_rows=[r['free_row_index'] for r in proof['all_affected_rows']]
                anchor=proof['unaffected_exact_anchor']
                direct_rows=proof_rows+([] if anchor is None else [anchor['free_row_index']])
                reserved=2*sum(int(R.indptr[i+1]-R.indptr[i]) for i in direct_rows)
                same(trial['independent_full_direct_exact_terms_reserved'],reserved,'reader_reserved_full_direct_exact_cost')
                require(result['direct_exact_product_terms']+reserved<=MAX_READER_EXACT_TERMS,
                        'reader_original_direct_full_exact_bound')
                if not trial['complete']:
                    require(not report['completed'] and trial is trials[-1] and index==len(screens)
                            and trial['accepted'] is False,'reader_only_last_inflight_trial_may_be_incomplete')
                    terminal=True;continue
                prefix=f"probe-N10/trial-{trial['trial_index']:02d}"
                require(trial['requested_update_file']==prefix+'/requested-update.npy'
                        and trial['actual_update_file']==prefix+'/actual-update.npy','reader_trial_update_locations')
                records=trial['probes'];require(len(records)==5,'reader_full_trial_exactly_five_records')
                require(records[0]['field_file']==prefix+'/probe-0-field.npy'
                        and records[0]['residual_file']==prefix+'/probe-0-residual.npy'
                        and records[0]['scientific_storage']=='separate_actual_original_array_bytes',
                        'reader_changed_probe_actual_field_locations')
                candidate=[load_array(records[0]['field_file'],(ND,))]+current[1:]
                expected_field=current[0].copy();requested=np.zeros(ND,dtype=np.float64)
                for j,new in changes.items():
                    expected_field[free[j]]=new;requested[free[j]]=new-current[0][free[j]]
                require(candidate[0].tobytes()==expected_field.tobytes(),'reader_complete_field_exact_one_or_two_coordinates_only')
                actual=candidate[0]-current[0]
                require(actual.tobytes()==requested.tobytes() and np.count_nonzero(actual)==len(changes),
                        'reader_actual_nonzero_ULP_updates_not_rounded_away')
                for name,want in ((trial['requested_update_file'],requested),(trial['actual_update_file'],actual)):
                    require(load_array(name,(ND,)).tobytes()==want.tobytes(),'reader_complete_update_original_array_bytes')
                observation={'requested_nonzero_DOFs':len(changes),'actually_changed_DOFs':len(changes),
                    'rounded_away_nonzero_requests':0,'ULP_steps_by_original_DOF':[
                        {'DOF':r['original_DOF'],'steps':r['ULP_steps']} for r in decision['coordinate_changes']],
                    'actual_update_infinity_norm':float(np.max(np.abs(actual))),
                    'requested_update_infinity_norm':float(np.max(np.abs(requested)))}
                same(trial['update_observation'],observation,'reader_actual_complete_update_observation')
                for j in range(1,5):
                    require(candidate[j].tobytes()==initial[j].tobytes(),'reader_other_four_original_fields_unchanged')
                    rec=records[j]
                    for label in ('field','residual'):
                        source=f'probe-N9/final/probe-{j}-{label}.npy';relative='frozen/'+source
                        require(rec[label+'_file']==relative and rec[label+'_identity']==identity[source]
                                and {'bytes':safe(relative).stat().st_size,'sha256':sha_file(safe(relative))}==identity[source],
                                'reader_per_trial_original_complete_reference_file_identity')
                        result['per_candidate_frozen_references_verified']+=1
                    require(rec['scientific_storage']=='explicit_frozen_original_field_and_residual_reference'
                            and rec['new_native_residual_equals_frozen_original_array_bytes'] is True,
                            'reader_explicit_frozen_actual_native_reference_declaration')
                new_scores,new_errors=check_fields(candidate,records,True)
                for j in range(1,5):
                    require(new_errors[j].tobytes()==load_array(f'{BASE_FIELDS_PREFIX}/probe-{j}-residual.npy',(NF,)).tobytes(),
                            'reader_other_four_actual_native_residual_bytes_unchanged')
                # A second, direct exact summation from both complete fields. No delta formula here.
                before_field=current[0][free];after_field=candidate[0][free]
                before_exact=[];after_exact=[]
                for row in proof['all_affected_rows']:
                    i=row['free_row_index'];q0=exact_row(i,before_field);q1=exact_row(i,after_field)
                    require(unpack(row['before'])==q0 and unpack(row['after'])==q1,
                            'reader_direct_original_before_and_actual_candidate_exact_equations')
                    before_exact.append(abs(q0));after_exact.append(abs(q1))
                    result['exact_affected_equations_directly_checked']+=1
                old_exact=max(before_exact,default=Fraction());new_exact=max(after_exact,default=Fraction())
                anchor_ok=False
                if anchor is not None:
                    i=anchor['free_row_index']
                    require(i not in set(proof_rows),'reader_anchor_outside_complete_nonzero_changed_columns')
                    q0=exact_row(i,before_field);q1=exact_row(i,after_field)
                    require(q0==q1==unpack(anchor['signed_exact_residual']) and anchor['base_field_sha256']==base_sha,
                            'reader_unchanged_anchor_direct_actual_full_field_pair')
                    anchor_ok=abs(q0)>=new_exact;result['unaffected_anchor_pairs_directly_checked']+=1
                exact_ok=new_exact<=old_exact or anchor_ok
                require(exact_ok==proof['global_exact_infinity_nonincrease_certified'],
                        'reader_global_exact_infinity_certificate_from_actual_full_fields')
                expected_error=errors[0].copy()
                for i,value in prediction.items():expected_error[i]=value
                matches=(new_errors[0].tobytes()==expected_error.tobytes()
                    and new_scores[0]['over_gate_row_count']==decision['predicted_probe0_violation_count']
                    and new_scores[0]['free_dof_residual_infinity_ratio']==decision['predicted_probe0_max_ratio'])
                require(trial['native_prediction_matched']==matches
                        and trial['predicted_whole_probe0_residual_sha256']==hashlib.sha256(expected_error.tobytes()).hexdigest(),
                        'reader_whole_original_native_residual_matches_or_records_true_mismatch')
                conditions={'global_exact_infinity_nonincrease_certificate':exact_ok,
                    'probe0_violation_count_strictly_decreases':new_scores[0]['over_gate_row_count']<scores[0]['over_gate_row_count'],
                    'original_full_five_max_ratio_nonincrease':max(v['free_dof_residual_infinity_ratio'] for v in new_scores)
                        <=max(v['free_dof_residual_infinity_ratio'] for v in scores),
                    'other_four_original_gates_remain_passed':all(new_scores[j]['passes_original_threshold'] for j in range(1,5))}
                accepted=matches and all(conditions.values())
                require(trial['acceptance_conditions']==conditions and trial['accepted']==accepted
                        and trial['all_five_original_gates_passed']==all(v['passes_original_threshold'] for v in new_scores),
                        'reader_unchanged_original_acceptance_plus_true_prediction')
                checked_trials.add(trial['trial_index']);result['full_candidate_sets_checked']+=1
                if accepted:
                    current=candidate;scores=new_scores;errors=new_errors
                    base_ref=records[0]['field_file'];base_sha=sha_file(safe(base_ref))
                    result['accepted_trial_indices'].append(trial['trial_index']);after_accept=True
                    passed=all(v['passes_original_threshold'] for v in scores)
                    if new_exact>old_exact:result['accepted_global_anchor_certificates']+=1
                    require(stage['status']=='accepted' and stage['accepted_trial_index']==trial['trial_index'],
                            'reader_accepted_state_committed_once_in_chronological_order')
                else:
                    terminal=True
                    require(index==len(screens) and trial is trials[-1]
                            and stage['status']=='terminal_unaccepted_full_candidate',
                            'reader_first_unaccepted_full_trial_is_terminal_and_counted')
            if len(intents)>len(screens):
                require(not report['completed'] and not terminal and not passed,'reader_only_one_inflight_virtual_intent')
                intent=intents[-1]
                if active!=intent['stage_index']:begin_stage(intent['stage_index'])
                expected,_,_=expected_intent(len(screens)+1,intent['stage_index'],position+1)
                same(intent,expected,'reader_inflight_intent_identity_and_finite_next_position')
                result['virtual_attempts_checked']+=1
            # A stage may have been committed immediately before its first intent.
            if len(stages)>active:
                require(not report['completed'] and len(stages)==active+1 and not terminal and not passed,
                        'reader_only_one_inflight_empty_stage')
                begin_stage(len(stages))
            require({t['trial_index'] for t in trials if t['complete']}==checked_trials,'reader_every_complete_native_trial_checked')
            same(result['accepted_trial_indices'],report['accepted_trial_indices'],'reader_original_sequential_accepted_chain')
            require(result['scalar_screens_checked']==len(screens),'reader_all_virtual_rejections_replayed')
            result['all_unselected_virtual_decisions_replayed']=True
            result['virtual_record_partial_tails']={'screen':screen_tail,'attempt':intent_tail}
            if report['completed']:
                require(not screen_tail and not intent_tail and len(screens)==len(intents)==report['scalar_screen_count']
                        ==report['virtual_attempts_started'] and all(t['complete'] for t in trials),
                        'reader_complete_record_counts_and_all_full_trials')
                for st in stages:
                    require(st['last_screen_index']-st['first_screen_index']+1==stage_counts.get(st['stage_index'],0),
                            'reader_stage_exact_complete_screen_interval')
                termination=report['termination']
                if termination=='first_accepted_state_passing_all_five':require(passed,'reader_first_pass_termination')
                elif termination=='all_native_attempts_derived_limit':require(len(trials)==native_bound and not passed,'reader_all_attempts_limit_termination')
                elif termination=='finite_current_target_candidates_exhausted':
                    n=len(stage['ordered_support'])
                    require(not passed and not terminal and not after_accept and position==8*n+8*(n-1)
                            and stage['status']=='all_finite_target_candidates_rejected','reader_finite_all_candidates_really_exhausted')
                elif termination in ('first_full_candidate_prediction_mismatch','first_unaccepted_full_candidate'):
                    require(terminal and trials and not trials[-1]['accepted'],'reader_true_terminal_full_rejection')
                    require((termination=='first_full_candidate_prediction_mismatch')==
                            (not trials[-1]['native_prediction_matched']),'reader_terminal_mismatch_reason_matches_actual')
                else:raise GateError('reader_unknown_complete_termination')
                final=[load_array(r['field_file'],(ND,)) for r in report['final']]
                for j in range(5):
                    require(final[j].tobytes()==current[j].tobytes(),'reader_final_is_chronological_state_not_history_best')
                    require(report['final'][j]['field_file']==f'probe-N10/final/probe-{j}-field.npy'
                            and report['final'][j]['residual_file']==f'probe-N10/final/probe-{j}-residual.npy',
                            'reader_all_ten_final_original_arrays')
                final_scores,final_errors=check_fields(final,report['final'],True)
                for a,b in zip(final_errors,errors):require(a.tobytes()==b.tobytes(),'reader_final_original_native_state')
                require(report['final_sequential_base_field_file']==base_ref and report['final_sequential_base_field_sha256']==base_sha,
                        'reader_final_state_original_file_source')
                result['final_sets_checked']=1
                result['final_original_ratios']=[v['free_dof_residual_infinity_ratio'] for v in final_scores]
                result['original_five_qualification_verified']=all(v['passes_original_threshold'] for v in final_scores)
                same(result['original_five_qualification_verified'],report['original_five_passed'],'reader_actual_original_five_qualification')
                same(report['full_candidates_completed'],len(checked_trials),'reader_all_completed_native_trial_count')
                require(report['four_prior_pass_fields_array_and_file_bytes_unchanged'] is True
                        and report['final_original_Kff_unchanged'] is True,'reader_complete_original_state_flags')
                for key in ('float64_scalar_product_terms','exact_current_product_terms','exact_increment_terms',
                            'current_rows_native_bitmatched','stage_cache_resets','stage_row_cache_peak'):
                    same(cost[key],report['exact_capacity_counters'][key],'reader_complete_actual_work_counters')
                same(result['direct_exact_product_terms'],report['exact_capacity_counters']['reader_exact_product_terms_reserved'],
                     'reader_complete_direct_exact_cost_equals_registered_reservation')
            else:
                require(report['original_five_passed'] is False,'reader_partial_never_qualifies')
                result['partial_evidence_verified']=True
            counters=report['exact_capacity_counters']
            bounds={'float64_scalar_product_terms':MAX_FLOAT_TERMS,'exact_current_product_terms':MAX_EXACT_TERMS,
                'exact_increment_terms':MAX_INCREMENT_TERMS,'reader_exact_product_terms_reserved':MAX_READER_EXACT_TERMS,
                'stage_row_cache_peak':MAX_CACHE_ROWS,'stage_cache_accounted_peak_bytes':MAX_CACHE_BYTES}
            for key,limit in bounds.items():require(0<=counters[key]<=limit,'reader_actual_reported_bounded_work')
        checked=0
        for name,expected in report.get('files',{}).items():
            path=safe(name)
            same({'bytes':path.stat().st_size,'sha256':sha_file(path)},expected,'reader_retained_declared_original_array_identity')
            checked+=1
        extra=[]
        pattern=re.compile(r'probe-N10/(?:(?:trial-(?:0[1-9]|[1-8][0-9]|9[0-6])/(?:probe-[0-4]-(?:field|residual)|requested-update|actual-update))|(?:final/probe-[0-4]-(?:field|residual)))\.npy(?:\.writing)?$')
        for path in sorted((case/'probe-N10').rglob('*')):
            name=path.relative_to(case).as_posix()
            if path.is_file() and pattern.fullmatch(name) and name not in report.get('files',{}):
                safe(name);extra.append({'file':name,'bytes':path.stat().st_size,'sha256':sha_file(path),
                                        'full_native_equation_validation_available':False})
        result['incomplete_or_uncommitted_scientific_array_identities']=extra
        result['retained_declared_arrays_hash_checked']=checked
        result['replayed_capacity_counters']=cost
        result['uncompleted_array_policy']='Every actual allowlisted complete or .writing array is separately preserved and hashed; incomplete or uncommitted arrays do not qualify.'
        for key,digest in KFF_SHA.items():
            require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest()==digest,'reader_final_original_Kff_unchanged')
        for key in ('H_action_restore_executed','frame_inverse_executed','candidate_go','fixture_fabrication_go','manufacturing_go'):
            require(report[key] is False,'reader_no_downstream_release_claim')
        result['completed']=True
    except BaseException as e:
        result['original_five_qualification_verified']=False
        result['failure_type']=type(e).__name__
        if isinstance(e,GateError):result['failure_gate']=str(e)
        if isinstance(e,KeyError) and e.args and isinstance(e.args[0],str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,80}',e.args[0]):
            result['failure_key']=e.args[0]
    result['elapsed_seconds']=time.monotonic()-start
    result['peak_rss_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_json(args.output,result)
    return 0 if result['completed'] else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
