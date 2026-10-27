"""N12 finite one/two-coordinate ULP search with original five native gates.
Virtual all-affected arithmetic is a pre-screen only. Every actual full candidate
is preserved, counted before execution, and a mismatch or rejection stops the run.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, os, re, resource, subprocess, sys, time
from pathlib import Path
from fractions import Fraction
import numpy as np
from scipy.sparse import load_npz
from n12_contract import (S4,S4_TREE,ND,NF,NP,FIXED,LIMIT,MAX_FULL,MAX_SCALAR,
 MAX_ROW_SUPPORT,MAX_CACHE_ROWS,MAX_EXACT_TERMS,MAX_READER_EXACT_TERMS,
 MAX_CACHE_BYTES,MAX_FRACTION_BITS,AS_BYTES,OUTPUT_BYTES,RESERVE_BYTES,
 ANCHOR_SEED_DOF,BASE_FIELDS_PREFIX,BASE_FIELD_SHA,INPUT_PAYLOAD_PREFIX,
 WALL_SECONDS,KFF_SHA,K_SHA,C_SHA,HELPER,HELPER_SHA,POINT_SOURCE,POINT_SOURCE_SHA,
 ULP_STEPS,MAX_FLOAT_TERMS,MAX_INCREMENT_TERMS,MAX_AFFECTED_ROWS,INITIAL_VIOLATION_COUNT,MAX_TARGETS_PER_FIELD,INITIAL_EXHAUSTED_TARGET_DOF,
 GateError,CapacityStop,require,sha_file,bits,verify_frozen_files,reserve,write_json)
RESIDUAL_LIMIT=LIMIT

def array_sha(value):
    return hashlib.sha256(np.asarray(value, dtype=np.float64).tobytes()).hexdigest()


def residual_record(K, solution, rhs, free):
    if not np.isfinite(solution).all() or not np.isfinite(rhs).all():
        raise ValueError('nonfinite solution or original RHS')
    error = K @ solution - rhs
    if not np.isfinite(error).all():
        raise ValueError('nonfinite original float64 residual')
    numerator = float(np.max(np.abs(error)))
    denominator = max(float(np.max(np.abs(rhs))), 1.0)
    ratio = numerator / denominator
    at = int(np.argmax(np.abs(error)))
    result = {
        "free_dof_residual_infinity_ratio": ratio,
        "residual_numerator": numerator,
        "normalization_denominator": denominator,
        "threshold": RESIDUAL_LIMIT,
        "passes_original_threshold": bool(np.isfinite(ratio) and ratio <= RESIDUAL_LIMIT),
        "max_residual_original_dof": int(free[at]),
        "signed_residual_at_max_dof": float(error[at]),
        "rhs_at_max_dof": float(rhs[at]),
        "solution_infinity_norm": float(np.max(np.abs(solution))),
        "rhs_free_sha256": array_sha(rhs),
        "solution_free_sha256": array_sha(solution),
        "residual_sha256": array_sha(error),
    }
    return result, error


def qpack(q):
    require(max(q.numerator.bit_length(), q.denominator.bit_length()) <= MAX_FRACTION_BITS,
            "exact_integer_size_cap")
    return {"numerator": str(q.numerator), "denominator": str(q.denominator)}


def exact_product(a, b):
    return Fraction.from_float(float(a)) * Fraction.from_float(float(b))


def ordered_row_dot(coefficients, values):
    out = 0.0
    for a, u in zip(coefficients, values):
        out = out + float(a) * float(u)
    return out


def acceptance_conditions(proof, old, new):
    return {
        "global_exact_infinity_nonincrease_certificate": proof["global_exact_infinity_nonincrease_certified"],
        "probe0_violation_count_strictly_decreases": new[0]["over_gate_row_count"] < old[0]["over_gate_row_count"],
        "original_full_five_max_ratio_nonincrease": max(r["free_dof_residual_infinity_ratio"] for r in new)
            <= max(r["free_dof_residual_infinity_ratio"] for r in old),
        "other_four_original_gates_remain_passed": all(new[k]["passes_original_threshold"] for k in range(1,5)),
    }


def select_unaffected_anchor(values, affected_rows, free, after_max, seed):
    affected = set(map(int, affected_rows))
    available = [i for i in values if i not in affected]
    if seed in values and seed not in affected and abs(values[seed]) >= after_max:
        return seed
    return max(available, key=lambda i: (abs(values[i]), -int(free[i]))) if available else None


def load_inputs(case, root):
    identities = verify_frozen_files(case)
    require(sha_file(root/HELPER) == HELPER_SHA and sha_file(root/POINT_SOURCE) == POINT_SOURCE_SHA,
            "original_helper_and_point_source")
    require(subprocess.check_output(["git","rev-parse","HEAD"], cwd=root, text=True).strip() == S4
            and subprocess.check_output(["git","rev-parse","HEAD^{tree}"], cwd=root, text=True).strip() == S4_TREE,
            "functional_S4_commit_tree")
    frozen = case/INPUT_PAYLOAD_PREFIX; volume = frozen/"volume/panel/level-2"; p = frozen/"probe-N5"
    model = json.loads((volume/"report.engineering.json").read_text())["selected_engineering_fields"]
    require(model["body"] == "panel" and model["level"] == 2 and model["E_normalization"] == 1.0
            and model["nu"] == 0.3 and model["K_sha256"] == K_SHA
            and model["original_faces_and_surface_P2_traces_unchanged"] is True
            and model["body_loads_on_added_internal_DOFs"] is False, "original_model_domain")
    fixed = np.load(p/"fixed-original-DOFs.npy", allow_pickle=False)
    free = np.load(p/"free-original-DOFs.npy", allow_pickle=False)
    require(fixed.dtype == free.dtype == np.int64 and tuple(map(int,fixed)) == FIXED
            and len(set(map(int,fixed))) == 6
            and np.array_equal(free, np.setdiff1d(np.arange(ND),fixed)) and len(free) == NF,
            "original_fixed_order_and_exact_free_complement")
    with np.load(volume/"loads.npz", allow_pickle=False) as loads:
        require(np.array_equal(loads["D"], fixed), "original_load_fixed_order")
    points = json.loads((p/"points.json").read_text())
    seed = json.loads(gzip.decompress((root/POINT_SOURCE).read_bytes()))
    require(seed["case"] == 6 and seed["volume_level"] == 2
            and points == seed["contact_points"] and len(points) == 3885,
            "original_ordered_point_domain")
    C = load_npz(p/"C.npz").tocsc()
    require(C.shape == (ND,3885) and C.nnz == 24518 and C.dtype == np.float64
            and C.has_canonical_format, "original_C_structure")
    directions = np.load(p/"five-probe-directions.npy", allow_pickle=False)
    rhs = np.load(p/"five-probe-rhs.npy", allow_pickle=False)
    require(directions.shape == (3885,5) and rhs.shape == (ND,5)
            and directions.dtype == rhs.dtype == np.float64, "original_five_shapes")
    rng = np.random.default_rng(73021)
    expected = [np.ones(3885)] + [rng.choice([-1.,1.],3885) for _ in range(4)]
    for j,d in enumerate(expected):
        require(np.array_equal(directions[:,j],d) and np.array_equal(rhs[:,j],np.asarray(C@d).ravel()),
                "original_five_directions_RHS_same_C")
    A = load_npz(volume/"K.npz")
    require(A.format == "csc" and A.shape == (ND,ND) and A.nnz == 23646483
            and A.dtype == np.float64 and A.has_canonical_format, "original_K_structure")
    A = A[free][:,free].tocsc()
    require(A.nnz == 23645561, "original_Kff_nnz")
    for key,digest in KFF_SHA.items():
        require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest() == digest, "original_Kff_buffer_identity")
    require(np.array_equal(A.diagonal(),np.load(p/"original-diagonal.npy",allow_pickle=False)),
            "original_diagonal_identity")
    base = case/BASE_FIELDS_PREFIX
    fields = [np.load(base/f"probe-{j}-field.npy", allow_pickle=False) for j in range(5)]
    old_errors = [np.load(base/f"probe-{j}-residual.npy", allow_pickle=False) for j in range(5)]
    for u,e in zip(fields,old_errors):
        require(u.shape == (ND,) and e.shape == (NF,) and u.dtype == e.dtype == np.float64
                and np.isfinite(u).all() and np.isfinite(e).all() and np.all(u[fixed] == 0),
                "original_five_frozen_fields")
    return A, free, fixed, rhs[free,:], fields, old_errors, identities

def ordered_target_indices(error, free, denominator, base_sha):
    """Finite current-field target policy; previous exhaustion is field-bound."""
    excluded = INITIAL_EXHAUSTED_TARGET_DOF if base_sha == BASE_FIELD_SHA else None
    rows = [i for i,e in enumerate(error) if abs(float(e))/denominator > LIMIT and int(free[i]) != excluded]
    rows.sort(key=lambda i: (-abs(float(error[i]))/denominator, int(free[i])))
    return rows[:MAX_TARGETS_PER_FIELD]


def candidate_specs(columns, target, primary_direction):
    """Finite fixed order; every descriptor is based on the same current field."""
    for steps in ULP_STEPS:
        for column in columns:
            for direction in (-1,1):
                yield 'single', [(int(column),direction,steps)]
    for steps in ULP_STEPS:
        for column in columns:
            if int(column)==int(target):
                continue
            for direction in (-1,1):
                yield 'paired', [(int(target),primary_direction,1),(int(column),direction,steps)]

def changed_values(values, specification, free):
    result,delta,records={},{},[]
    require(len(specification) in (1,2) and len({x[0] for x in specification})==len(specification),
            'unique_one_or_two_original_free_coordinates')
    for column,direction,steps in specification:
        require(direction in (-1,1) and steps in ULP_STEPS,'registered_ULP_direction_distance')
        old=float(values[column]);new=old
        for _ in range(steps):
            new=math.nextafter(new,-math.inf if direction<0 else math.inf)
        require(math.isfinite(new) and bits(new)!=bits(old),'finite_changed_float64_value')
        d=Fraction.from_float(new)-Fraction.from_float(old)
        require(float(d)==new-old,'exact_representable_ULP_delta')
        result[column]=new;delta[column]=d
        records.append({'free_column_index':int(column),'original_DOF':int(free[column]),
            'direction':direction,'ULP_steps':steps,'old_value_hex':old.hex(),
            'new_value_hex':new.hex(),'actual_delta_hex':float(d).hex()})
    return result,delta,records

class StagePrediction:
    """Stage-local caches. All cumulative arithmetic counters survive a reset."""
    def __init__(self,A,R,b,u,error,free,base_sha,current_scores,counters,guard):
        self.A,self.R,self.b,self.u,self.error,self.free=A,R,b,u,error,free
        self.base_sha,self.scores,self.counters,self.guard=base_sha,current_scores,counters,guard
        self.rows={};self.exact_values={};self.storage=0
        self.denominator=current_scores[0]['normalization_denominator']
        self.bad=current_scores[0]['over_gate_row_count']
        self.old_max=max(v['free_dof_residual_infinity_ratio'] for v in current_scores)
        self.other_max=max(v['free_dof_residual_infinity_ratio'] for v in current_scores[1:])
        self.top=np.argpartition(np.abs(error),-(MAX_AFFECTED_ROWS+1))[-(MAX_AFFECTED_ROWS+1):]
        found=np.flatnonzero(free==ANCHOR_SEED_DOF)
        require(len(found)==1,'original_free_anchor_seed_domain')
        self.seed=int(found[0]);self.exact(self.seed)

    def charge_float(self,n):
        if self.counters['float64_scalar_product_terms']+n>MAX_FLOAT_TERMS:
            raise CapacityStop('finite_float64_virtual_product_cap')
        self.counters['float64_scalar_product_terms']+=n

    def get_row(self,i):
        i=int(i)
        if i in self.rows:return self.rows[i]
        self.guard()
        lo,hi=map(int,self.R.indptr[i:i+2]);n=hi-lo
        if n>1024 or len(self.rows)>=MAX_CACHE_ROWS:
            raise CapacityStop('finite_stage_row_cache_cap')
        columns=self.R.indices[lo:hi];coeff=self.R.data[lo:hi];values=self.u[columns].copy()
        self.charge_float(n)
        base=ordered_row_dot(coeff,values)-float(self.b[i])
        require(bits(base)==bits(self.error[i]),'virtual_every_current_row_matches_native_CSC_bits')
        record=(columns,coeff,values)
        size=256+sys.getsizeof(record)+sum(sys.getsizeof(v)+v.nbytes for v in record)
        if self.storage+size>MAX_CACHE_BYTES:
            raise CapacityStop('finite_combined_stage_cache_memory_cap')
        self.storage+=size;self.rows[i]=record
        self.counters['stage_row_cache_peak']=max(self.counters['stage_row_cache_peak'],len(self.rows))
        self.counters['stage_cache_accounted_peak_bytes']=max(self.counters['stage_cache_accounted_peak_bytes'],self.storage)
        self.counters['current_rows_native_bitmatched']+=1
        return record

    def dot(self,i,changes):
        columns,coeff,values=self.get_row(i);self.charge_float(len(columns))
        total=0.0
        for j,a,u in zip(columns,coeff,values):
            total=total+float(a)*float(changes.get(int(j),u))
        return total-float(self.b[i])

    def exact(self,i):
        i=int(i)
        if i in self.exact_values:return self.exact_values[i]
        columns,coeff,values=self.get_row(i);n=len(columns)
        if self.counters['exact_current_product_terms']+n>MAX_EXACT_TERMS:
            raise CapacityStop('finite_exact_current_product_cap')
        if self.counters['reader_exact_product_terms_reserved']+n>MAX_READER_EXACT_TERMS:
            raise CapacityStop('finite_independent_exact_product_reservation')
        self.counters['exact_current_product_terms']+=n
        self.counters['reader_exact_product_terms_reserved']+=n
        value=-Fraction.from_float(float(self.b[i]))
        for a,u in zip(coeff,values):value+=exact_product(a,u)
        qpack(value)
        size=256+sys.getsizeof(value)+sys.getsizeof(value.numerator)+sys.getsizeof(value.denominator)
        if self.storage+size>MAX_CACHE_BYTES:
            raise CapacityStop('finite_combined_stage_cache_memory_cap')
        self.storage+=size;self.exact_values[i]=value
        self.counters['stage_cache_accounted_peak_bytes']=max(self.counters['stage_cache_accounted_peak_bytes'],self.storage)
        return value

    def evaluate(self,target,kind,specification):
        changes,deltas,descriptors=changed_values(self.u,specification,self.free)
        columns,coeff,_=self.get_row(target);coefficient={int(j):float(a) for j,a in zip(columns,coeff)}
        q0=self.exact(target)
        if self.counters['exact_increment_terms']+len(changes)>MAX_INCREMENT_TERMS:
            raise CapacityStop('finite_exact_increment_term_cap')
        self.counters['exact_increment_terms']+=len(changes)
        q1=q0+sum((Fraction.from_float(coefficient.get(j,0.0))*deltas[j] for j in changes),Fraction())
        predicted_target=self.dot(target,changes);target_ratio=abs(predicted_target)/self.denominator
        decision={'candidate_kind':kind,'coordinate_changes':descriptors,
            'predicted_target_residual_bits':bits(predicted_target),'predicted_target_ratio':target_ratio,
            'target_original_row_pass_predicted':target_ratio<=LIMIT,
            'exact_target_before':qpack(q0),'exact_target_after':qpack(q1),
            'all_affected_float64_predictions_evaluated':False,'exact_global_proof_evaluated':False,
            'eligible_for_full_candidate':False,'native_full_gate_evaluated_by_this_screen':False}
        if target_ratio>LIMIT:return decision,None,None,changes
        coefficients={}
        for j in changes:
            lo,hi=map(int,self.A.indptr[j:j+2])
            selected={int(i):float(a) for i,a in zip(self.A.indices[lo:hi],self.A.data[lo:hi]) if a!=0.0}
            if len(selected)>MAX_AFFECTED_ROWS:raise CapacityStop('finite_original_column_support_cap')
            coefficients[j]=selected
        affected=sorted(set().union(*(set(v) for v in coefficients.values())))
        if len(affected)>MAX_AFFECTED_ROWS:raise CapacityStop('finite_changed_column_union_cap')
        predicted={i:self.dot(i,changes) for i in affected}
        before_bad=sum(abs(float(self.error[i]))/self.denominator>LIMIT for i in affected)
        after_bad=sum(abs(v)/self.denominator>LIMIT for v in predicted.values())
        count=self.bad-before_bad+after_bad
        affected_set=set(affected)
        outside=max(abs(float(self.error[i])) for i in self.top if int(i) not in affected_set)
        probe_ratio=max(outside,max((abs(x) for x in predicted.values()),default=0.0))/self.denominator
        global_ratio=max(probe_ratio,self.other_max)
        digest=hashlib.sha256(json.dumps([[i,bits(predicted[i])] for i in affected],separators=(',',':')).encode()).hexdigest()
        progress=count<self.bad and global_ratio<=self.old_max
        decision.update(all_affected_float64_predictions_evaluated=True,affected_free_row_count=len(affected),
            predicted_affected_row_bits_sha256=digest,predicted_probe0_violation_count=count,
            predicted_probe0_max_ratio=probe_ratio,predicted_full_five_max_ratio=global_ratio,
            original_full_float64_progress_predicted=progress)
        if not progress:return decision,None,predicted,changes
        before,after,records={},{},[]
        if self.counters['exact_increment_terms']+len(affected)*len(changes)>MAX_INCREMENT_TERMS:
            raise CapacityStop('finite_exact_increment_term_cap')
        self.counters['exact_increment_terms']+=len(affected)*len(changes)
        for i in affected:
            before[i]=self.exact(i)
            after[i]=before[i]+sum((Fraction.from_float(coefficients[j].get(i,0.0))*deltas[j] for j in changes),Fraction())
            records.append({'free_row_index':i,'original_row_DOF':int(self.free[i]),
                'changed_column_coefficients_hex':[{'free_column_index':j,'original_column_DOF':int(self.free[j]),
                    'coefficient_hex':coefficients[j].get(i,0.0).hex()} for j in changes],
                'before':qpack(before[i]),'after':qpack(after[i]),
                'base_native_float64_residual_bits':bits(self.error[i]),
                'predicted_float64_residual_bits':bits(predicted[i])})
        old_max=max((abs(v) for v in before.values()),default=Fraction())
        new_max=max((abs(v) for v in after.values()),default=Fraction())
        anchor_index=select_unaffected_anchor(self.exact_values,affected,self.free,new_max,self.seed)
        anchor=None;anchor_ok=False
        if anchor_index is not None:
            value=self.exact_values[anchor_index];anchor_ok=abs(value)>=new_max
            anchor={'base_field_sha256':self.base_sha,'free_row_index':anchor_index,
                'original_row_DOF':int(self.free[anchor_index]),'signed_exact_residual':qpack(value),
                'outside_complete_changed_columns_nonzero_support':True,
                'affected_after_max_bounded_by_anchor':anchor_ok,'exact_bound_margin':qpack(abs(value)-new_max),
                'known_current_exact_pool_rows':len(self.exact_values)}
        ok=bool(new_max<=old_max or anchor_ok)
        proof={'all_affected_rows':records,'affected_row_count':len(affected),
            'affected_exact_infinity_before':qpack(old_max),'affected_exact_infinity_after':qpack(new_max),
            'all_affected_exact_infinity_nonincrease':new_max<=old_max,
            'outside_affected_columns_exact_equations_unchanged':True,
            'unaffected_exact_anchor':anchor,'unaffected_anchor_certificate_valid':anchor_ok,
            'global_exact_infinity_nonincrease_certified':ok,
            'global_certificate_uses_anchor':bool(new_max>old_max and anchor_ok)}
        proof_hash=hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        decision.update(exact_global_proof_evaluated=True,exact_global_proof_sha256=proof_hash,
            affected_exact_infinity_before=qpack(old_max),affected_exact_infinity_after=qpack(new_max),
            anchor_original_DOF=None if anchor is None else anchor['original_row_DOF'],
            anchor_exact_signed=None if anchor is None else anchor['signed_exact_residual'],
            global_exact_infinity_nonincrease_certified=ok,eligible_for_full_candidate=ok)
        return decision,proof,predicted,changes

    def reserve_full_reader(self,proof):
        rows=[x['free_row_index'] for x in proof['all_affected_rows']]
        anchor=proof['unaffected_exact_anchor']
        if anchor is not None:rows.append(anchor['free_row_index'])
        cost=2*sum(len(self.get_row(i)[0]) for i in rows)
        if self.counters['reader_exact_product_terms_reserved']+cost>MAX_READER_EXACT_TERMS:
            raise CapacityStop('finite_independent_full_exact_reservation')
        self.counters['reader_exact_product_terms_reserved']+=cost
        return cost

def run(args):
    start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(AS_BYTES,AS_BYTES))
    case=args.case.resolve(strict=True);root=args.root.resolve(strict=True)
    folder=case/'probe-N12';folder.mkdir(exist_ok=False)
    counters={'float64_scalar_product_terms':0,'exact_current_product_terms':0,
        'exact_increment_terms':0,'reader_exact_product_terms_reserved':0,
        'stage_row_cache_peak':0,'stage_cache_accounted_peak_bytes':0,
        'current_rows_native_bitmatched':0,'stage_cache_resets':0}
    report={'schema':'razr-N12-finite-original-five-probe-v1','completed':False,
        'phase':'frozen_input_validation','functional_source_commit':S4,'functional_source_tree':S4_TREE,
        'original_gate':LIMIT,'original_K_sha256':K_SHA,'original_C_sha256':C_SHA,
        'strategy':'finite one/two-coordinate ULP candidates; all-affected float64 prediction and unchanged global exact proof precede actual original five native gates; stop on first unaccepted full trial',
        'full_candidate_field_storage_policy':'Every actual full candidate keeps probe0 field/residual and requested/actual updates; four unchanged fields/residuals are explicit verified frozen references and are natively re-evaluated each time.',
        'full_candidate_limit':MAX_FULL,'scalar_screen_limit':MAX_SCALAR,'target_support_limit':MAX_ROW_SUPPORT,'maximum_targets_per_field':MAX_TARGETS_PER_FIELD,
        'initial_exhausted_target_original_DOF':INITIAL_EXHAUSTED_TARGET_DOF,
        'initial_exhaustion_inherited_only_for_field_sha256':BASE_FIELD_SHA,
        'virtual_attempts_started':0,'scalar_screen_count':0,'stages':[],'trials':[],'files':{},
        'accepted_trial_indices':[],'original_five_passed':False,'select_best_history':False,
        'stop_on_first_unaccepted_full_candidate':True,'exact_capacity_counters':counters,
        'H_action_restore_executed':False,'frame_inverse_executed':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    bytes_written={'N12_SCALAR_SCREENS.jsonl':0,'N12_SCREEN_ATTEMPTS.jsonl':0}
    def guard():
        if time.monotonic()-start>=WALL_SECONDS:raise CapacityStop('original_180_second_worker_wall')
    def save():
        report['elapsed_seconds']=time.monotonic()-start
        report['peak_rss_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['virtual_record_bytes']=dict(bytes_written)
        write_json(folder/'N12_REPORT.json',report,case)
    def append(name,value,limit):
        data=(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
        if bytes_written[name]+len(data)>limit:raise CapacityStop('finite_virtual_record_byte_cap')
        if report['virtual_attempts_started']%64==0:reserve(case,len(data)+1024**2)
        with (folder/name).open('ab',buffering=0) as stream:stream.write(data)
        bytes_written[name]+=len(data)
    def save_array(name,value):
        reserve(case,int(value.nbytes)+4096)
        p=case/name;p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.writing')
        with temp.open('wb') as stream:
            np.save(stream,value,allow_pickle=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,p)
        identity={'bytes':p.stat().st_size,'sha256':sha_file(p)}
        report['files'][name]=identity;save()
        return identity
    try:
        save();A,free,fixed,rhs,current,old_errors,identities=load_inputs(case,root)
        report['frozen_input_identities']=identities;report['original_Kff_buffer_hashes']=dict(KFF_SHA)
        report['input_validation_and_Kff_seconds']=time.monotonic()-start
        extended=A.astype(np.longdouble);R=A.tocsr()
        require(np.finfo(np.longdouble).eps<np.finfo(np.float64).eps and R.has_canonical_format,
            'diagnostic_longdouble_and_CSR_only')
        report['diagnostic_CSR_only_original_gate_stays_CSC']=True
        report['matrix_array_bytes']={name:sum(getattr(v,k).nbytes for k in ('data','indices','indptr'))
            for name,v in (('original_Kff_CSC',A),('diagnostic_CSR',R),('diagnostic_longdouble_CSC',extended))}
        report['input_and_matrix_setup_seconds']=time.monotonic()-start
        initial_fields=[u.copy() for u in current]
        def measure(fields,prefix=None,reuse=False):
            rows=[];errors=[]
            for j,u in enumerate(fields):
                guard();t=time.monotonic();rec,e=residual_record(A,u[free],rhs[:,j],free)
                rec['probe_index']=j
                rec['over_gate_row_count']=int(np.count_nonzero(np.abs(e)/rec['normalization_denominator']>LIMIT))
                ld=extended@u[free].astype(np.longdouble)-rhs[:,j].astype(np.longdouble)
                rec['longdouble_residual_ratio_diagnostic_only']=float(np.max(np.abs(ld)))/rec['normalization_denominator']
                if prefix is not None:
                    if reuse and j in range(1,5):
                        require(u.tobytes()==initial_fields[j].tobytes() and e.tobytes()==old_errors[j].tobytes(),
                            'unchanged_frozen_reference_array_and_actual_native_residual_bytes')
                        for label in ('field','residual'):
                            original=f'probe-N10/final/probe-{j}-{label}.npy';name='frozen/'+original
                            p=case/name;identity=identities[original]
                            require({'bytes':p.stat().st_size,'sha256':sha_file(p)}==identity,
                                'unchanged_frozen_reference_complete_original_file_bytes')
                            rec[label+'_file']=name;rec[label+'_identity']=dict(identity)
                        rec['scientific_storage']='explicit_frozen_original_field_and_residual_reference'
                        rec['new_native_residual_equals_frozen_original_array_bytes']=True
                    else:
                        for label,value in (('field',u),('residual',e)):
                            name=f'{prefix}/probe-{j}-{label}.npy'
                            rec[label+'_file']=name;rec[label+'_identity']=save_array(name,value)
                        rec['scientific_storage']='separate_actual_original_array_bytes'
                rec['native_gate_diagnostic_and_persistence_seconds']=time.monotonic()-t
                rows.append(rec);errors.append(e)
            return rows,errors
        scores,errors=measure(current)
        for j,e in enumerate(errors):require(e.tobytes()==old_errors[j].tobytes(),'baseline_native_matches_frozen_original_bytes')
        require([v['passes_original_threshold'] for v in scores]==[False,True,True,True,True]
            and scores[0]['over_gate_row_count']==INITIAL_VIOLATION_COUNT,'same_actual_N10_rejected_start')
        report['baseline']=scores
        native_bound=min(MAX_FULL,scores[0]['over_gate_row_count'])
        report['all_native_attempts_derived_bound']=native_bound
        report['derived_bound_scope']='Every full attempt is counted before execution; only accepted strict-count-decreasing trials permit another attempt; first mismatch or rejection is terminal. Initial 12 bad rows and first-pass stop bound all attempts, including a terminal rejection, by 12. At most three target stages are allowed per current accepted field.'
        base_ref=BASE_FIELDS_PREFIX+'/probe-0-field.npy';base_sha=sha_file(case/base_ref)
        require(base_sha==BASE_FIELD_SHA,'actual_N10_last_sequential_field_identity')
        report['phase']='finite_coupled_trials';save();stop=False
        target_base_sha=None;target_order=[];target_position=0
        while not all(v['passes_original_threshold'] for v in scores):
            guard()
            if len(report['trials'])>=native_bound:
                report['termination']='all_native_attempts_derived_limit';break
            if report['virtual_attempts_started']>=MAX_SCALAR:raise CapacityStop('finite_virtual_attempt_count_cap')
            if target_base_sha!=base_sha:
                target_order=ordered_target_indices(errors[0],free,scores[0]['normalization_denominator'],base_sha)
                target_position=0;target_base_sha=base_sha
            if target_position>=len(target_order):
                report['termination']='finite_registered_target_order_exhausted';break
            target=target_order[target_position];lo,hi=map(int,R.indptr[target:target+2])
            columns=R.indices[lo:hi]
            if len(columns)>MAX_ROW_SUPPORT:raise CapacityStop('finite_target_row_support_cap')
            require(np.all(columns[1:]>columns[:-1]) and float(A[target,target])>0.0,'canonical_target_with_positive_original_diagonal')
            primary=-1 if errors[0][target]>0 else 1
            pred=StagePrediction(A,R,rhs[:,0],current[0][free],errors[0],free,base_sha,scores,counters,guard)
            counters['stage_cache_resets']+=1
            seed={'base_field_sha256':base_sha,'free_row_index':pred.seed,'original_row_DOF':ANCHOR_SEED_DOF,
                'signed_exact_residual':qpack(pred.exact_values[pred.seed])}
            if 'initial_anchor_seed' not in report:report['initial_anchor_seed']=seed
            stage={'stage_index':len(report['stages'])+1,'base_field_file':base_ref,'base_field_sha256':base_sha,
                'target_free_index':target,'target_original_DOF':int(free[target]),
                'target_position_in_current_field':target_position+1,
                'ordered_current_target_original_DOFs':[int(free[i]) for i in target_order],
                'initial_exhaustion_applied':base_sha==BASE_FIELD_SHA,
                'current_field_epoch':len(report['accepted_trial_indices'])+1,
                'base_global_ratio':max(v['free_dof_residual_infinity_ratio'] for v in scores),
                'base_probe0_violation_count':scores[0]['over_gate_row_count'],'primary_direction':primary,
                'ordered_support':[{'free_column_index':int(j),'original_column_DOF':int(free[j]),
                    'coefficient_hex':float(a).hex()} for j,a in zip(columns,R.data[lo:hi])],
                'first_screen_index':report['scalar_screen_count']+1,'last_screen_index':report['scalar_screen_count'],
                'anchor_seed':seed,'status':'screening','accepted_trial_index':None}
            report['stages'].append(stage);save();accepted=False
            for position,(kind,spec) in enumerate(candidate_specs(columns,target,primary),1):
                guard()
                if report['virtual_attempts_started']>=MAX_SCALAR:raise CapacityStop('finite_virtual_attempt_count_cap')
                intent={'schema':'razr-N12-virtual-attempt-v1','screen_index':report['scalar_screen_count']+1,
                    'stage_index':stage['stage_index'],'stage_candidate_position':position,'base_field_sha256':base_sha,
                    'target_original_DOF':int(free[target]),'candidate_kind':kind,
                    'coordinate_specifications':[{'free_column_index':j,'original_DOF':int(free[j]),
                        'direction':d,'ULP_steps':n} for j,d,n in spec],
                    'native_full_gate_evaluated_by_this_record':False}
                append('N12_SCREEN_ATTEMPTS.jsonl',intent,8*1024**2)
                report['virtual_attempts_started']+=1
                decision,proof,predicted,changes=pred.evaluate(target,kind,spec)
                screen={'schema':'razr-N12-virtual-support-screen-v1','screen_index':report['scalar_screen_count']+1,
                    'stage_index':stage['stage_index'],'stage_candidate_position':position,
                    'base_field_sha256':base_sha,'target_original_DOF':int(free[target]),**decision}
                append('N12_SCALAR_SCREENS.jsonl',screen,16*1024**2)
                report['scalar_screen_count']+=1;stage['last_screen_index']=screen['screen_index']
                if report['scalar_screen_count']%64==0:save()
                if not decision['eligible_for_full_candidate']:continue
                if len(report['trials'])>=native_bound:raise CapacityStop('all_native_attempts_derived_limit')
                reader_cost=pred.reserve_full_reader(proof)
                index=len(report['trials'])+1
                if index==1:
                    require(int(free[target])==196556 and screen['screen_index']==5
                        and [(x['original_DOF'],x['direction'],x['ULP_steps']) for x in decision['coordinate_changes']]==[(3110,-1,1)],
                        'first_native_candidate_matches_frozen_N12_capacity_witness')
                trial={'trial_index':index,'screen_index':screen['screen_index'],'stage_index':stage['stage_index'],
                    'base_field_file':base_ref,'base_field_sha256':base_sha,'coordinate_changes':decision['coordinate_changes'],
                    'complete':False,'accepted':False,'native_prediction_matched':False,'exact_affected_proof':proof,
                    'independent_full_direct_exact_terms_reserved':reader_cost}
                report['trials'].append(trial);save()
                candidates=[current[0].copy()]+current[1:]
                request=np.zeros(ND,dtype=np.float64)
                for j,value in changes.items():
                    candidates[0][free[j]]=value;request[free[j]]=value-current[0][free[j]]
                actual=candidates[0]-current[0]
                require(np.count_nonzero(actual)==len(changes) and actual.tobytes()==request.tobytes(),
                    'all_requested_ULP_coordinates_changed_exactly')
                prefix=f'probe-N12/trial-{index:02d}'
                trial['requested_update_file']=prefix+'/requested-update.npy'
                trial['actual_update_file']=prefix+'/actual-update.npy'
                save_array(trial['requested_update_file'],request);save_array(trial['actual_update_file'],actual)
                trial['update_observation']={'requested_nonzero_DOFs':len(changes),'actually_changed_DOFs':len(changes),
                    'rounded_away_nonzero_requests':0,'ULP_steps_by_original_DOF':[
                        {'DOF':x['original_DOF'],'steps':x['ULP_steps']} for x in decision['coordinate_changes']],
                    'actual_update_infinity_norm':float(np.max(np.abs(actual))),
                    'requested_update_infinity_norm':float(np.max(np.abs(request)))}
                rows,new_errors=measure(candidates,prefix,reuse=True)
                predicted_error=errors[0].copy()
                for i,value in predicted.items():predicted_error[i]=value
                match=(new_errors[0].tobytes()==predicted_error.tobytes()
                    and rows[0]['over_gate_row_count']==decision['predicted_probe0_violation_count']
                    and rows[0]['free_dof_residual_infinity_ratio']==decision['predicted_probe0_max_ratio'])
                conditions=acceptance_conditions(proof,scores,rows)
                trial.update(complete=True,probes=rows,native_prediction_matched=bool(match),
                    predicted_whole_probe0_residual_sha256=array_sha(predicted_error),
                    acceptance_conditions=conditions,accepted=bool(match and all(conditions.values())),
                    all_five_original_gates_passed=all(v['passes_original_threshold'] for v in rows))
                if not trial['accepted']:
                    report['termination']='first_full_candidate_prediction_mismatch' if not match else 'first_unaccepted_full_candidate'
                    stage['status']='terminal_unaccepted_full_candidate';stop=True;save();break
                current=candidates;scores=rows;errors=new_errors
                base_ref=rows[0]['field_file'];base_sha=rows[0]['field_identity']['sha256']
                report['accepted_trial_indices'].append(index)
                stage['status']='accepted';stage['accepted_trial_index']=index;accepted=True;save();break
            if stop:break
            if not accepted:
                stage['status']='all_finite_target_candidates_rejected';target_position+=1;save()
                if target_position>=len(target_order):
                    report['termination']='finite_registered_target_order_exhausted';break
                continue
            if all(v['passes_original_threshold'] for v in scores):
                report['termination']='first_accepted_state_passing_all_five';break
        report['phase']='final_sequential_state';save()
        final,final_errors=measure(current,'probe-N12/final')
        for old,new in zip(errors,final_errors):require(old.tobytes()==new.tobytes(),'final_native_state_is_last_sequential_state')
        report.update(completed=True,phase='complete_finite_trial_evidence',final=final,
            final_sequential_base_field_file=base_ref,final_sequential_base_field_sha256=base_sha,
            original_five_passed=all(v['passes_original_threshold'] for v in final),
            full_candidates_completed=sum(t['complete'] for t in report['trials']),
            four_prior_pass_fields_array_and_file_bytes_unchanged=True,
            exact_global_nonincrease_proof_scope='Every accepted one/two-coordinate change is checked over the full union of nonzero original columns. Outside this union every exact equation is unchanged; affected infinity nonincrease or an unchanged directly summed anchor bounds the global exact infinity norm.')
        for k,digest in KFF_SHA.items():require(hashlib.sha256(getattr(A,k).tobytes()).hexdigest()==digest,'final_original_Kff_unchanged')
        report['final_original_Kff_unchanged']=True;save()
        return 0 if report['original_five_passed'] else 2
    except BaseException as e:
        report.update(completed=False,original_five_passed=False,failure_type=type(e).__name__,partial_evidence_preserved=True)
        if isinstance(e,GateError):report['failure_gate']=str(e)
        if isinstance(e,CapacityStop):report['capacity_stop']=True
        if isinstance(e,KeyError) and e.args and isinstance(e.args[0],str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,80}',e.args[0]):report['failure_key']=e.args[0]
        try:save()
        except BaseException:pass
        return 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    raise SystemExit(run(p.parse_args()))


