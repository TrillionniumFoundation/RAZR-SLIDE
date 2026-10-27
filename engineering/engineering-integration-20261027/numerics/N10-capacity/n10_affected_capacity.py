"""Finite, stdlib-only support audit. Predictions never substitute for native gates."""
from pathlib import Path
from fractions import Fraction
from array import array
from bisect import bisect_left, bisect_right
import ast, datetime, hashlib, heapq, json, math, os, resource, struct, sys, time, zipfile

ROOT=Path('/tmp/razr-next-20261027/numerics')
OLD=Path('/tmp/razr-recovery-20261026/numerics/N8-original-scientific')
OUT=ROOT/'N10-affected-capacity'
K=OLD/'frozen/frozen/volume/panel/level-2/K.npz'
REPORT=ROOT/'N9-actual-summary/original/probe-N9/N9_REPORT.json'
FIXED=(0,1,2,13,14,8)
SORTED_FIXED=sorted(FIXED)
MAX_BYTES=4*1024**2
CHUNK_ENTRIES=262144

def require(x,key):
    if not x:raise ValueError(key)
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def pack(q):return {'numerator':str(q.numerator),'denominator':str(q.denominator)}
def unpack(q):return Fraction(int(q['numerator']),int(q['denominator']))
def bits(x):return struct.pack('>d',x).hex()
def fi(dof):return dof-bisect_left(SORTED_FIXED,dof)
def header(f):
    p=f.read(10);require(p[:8]==bytes([147])+b'NUMPY'+bytes([1,0]),'NPY_v1')
    n=struct.unpack('<H',p[8:10])[0]
    h=ast.literal_eval(f.read(n).decode('latin1').strip())
    return h,10+n
def array_bytes(path,dtype,shape,expected_sha):
    b=path.read_bytes();require(sha(b)==expected_sha,'input_NPY_byte_identity')
    import io
    h,n=header(io.BytesIO(b))
    require(h=={'descr':dtype,'fortran_order':False,'shape':shape},'input_NPY_shape_dtype_order')
    return bytearray(b),n

def main():
    start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
    plan_bytes=(OUT/'N10_AFFECTED_CAPACITY_PREREGISTRATION.json').read_bytes()
    plan=json.loads(plan_bytes)
    r={'schema':'razr-N10-finite-all-affected-capacity-v1','completed':False,
       'capacity_contract_sha256':sha(plan_bytes),'source_sha256':file_sha(Path(__file__)),
       'native_numeric_CAD_or_solver_execution':False,'local_full_five_native_gate_evaluated':False,
       'virtual_arithmetic_does_not_qualify_original_five':True,
       'original_N9_complete_ZIP_actual_byte_readback_substituted':False,
       'current_field_and_residual_bytes_explicitly_derived':True,'candidate_records':[],
       'full_affected_row_certificates_for_first_three_predicted_eligible':[]}
    def guard():require(time.monotonic()-start<90,'finite_90s_capacity_wall')
    def save():
        r['elapsed_seconds']=time.monotonic()-start
        r['peak_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        b=(json.dumps(r,indent=2,allow_nan=False)+'\n').encode()
        require(len(b)<=MAX_BYTES,'finite_4MiB_diagnostic_report')
        (OUT/'N10_AFFECTED_CAPACITY_RESULT.json').write_bytes(b)
    try:
        require(plan['registered_before_execution'] is True,'preregistered')
        raw=REPORT.read_bytes();require(sha(raw)==plan['original_N9_report_sha256'],'actual_report_identity')
        report=json.loads(raw);stage=report['stages'][-1]
        require(report['accepted_trial_indices']==[1] and len(stage['ordered_support'])==57,'actual_N9_terminal_state')
        u,uo=array_bytes(OLD/'probe-N8/final/probe-0-field.npy','<f8',(344103,),
            '289153703ed68fd9b8161858195865a088325de58b0d66395f16844787c8420a')
        x=struct.unpack_from('<d',u,uo+8*160238)[0]
        struct.pack_into('<d',u,uo+8*160238,math.nextafter(x,-math.inf))
        require(sha(u)==plan['current_N9_field_sha256'],'derived_current_field_full_hash')
        residual,eo=array_bytes(OLD/'probe-N8/final/probe-0-residual.npy','<f8',(344097,),
            '5d8d628bb05ac1fd1233e4a39910e78259eab2f3d3b36c72575c621d2c20cb88')
        rhs,bo=array_bytes(OLD/'frozen/frozen/probe-N5/five-probe-rhs.npy','<f8',(344103,5),
            'c78a9fe77aadfa65b46d56a5ec2085122d46306872ae57e05e5701a0428e8bd1')
        free,fo=array_bytes(OLD/'frozen/frozen/probe-N5/free-original-DOFs.npy','<i8',(344097,),
            '3dc8d532337a3e32bcfdba50ec752e79f2351df72a70c85f69807c4b880eb2a1')
        fixed,xo=array_bytes(OLD/'frozen/frozen/probe-N5/fixed-original-DOFs.npy','<i8',(6,),
            'c5253eefb07da8a1e680eb31d3c6bb5d1d181a44ed1161f50aa6370c84709205')
        require(tuple(struct.unpack_from('<6q',fixed,xo))==FIXED,'actual_unsorted_fixed_order')
        require(all(j==fi(d) and d not in FIXED for j,(d,) in enumerate(struct.iter_unpack('<q',free[fo:]))),'actual_original_free_complement')
        del free,fixed
        def U(j):return struct.unpack_from('<d',u,uo+8*j)[0]
        def B(i):return struct.unpack_from('<d',rhs,bo+40*i)[0]
        require(file_sha(K)==plan['original_K_sha256'],'original_K_actual_file_SHA')
        guard()
        columns=[v['original_column_DOF'] for v in stage['ordered_support']]
        needed_columns=sorted(set(columns+[160238]));meta={}
        with zipfile.ZipFile(K) as z,K.open('rb') as f:
            require(set(z.namelist())=={'indices.npy','indptr.npy','data.npy','format.npy','shape.npy'},'original_CSC_NPZ_members')
            for info in z.infolist():
                require(info.compress_type==zipfile.ZIP_STORED and not info.flag_bits&1,'stored_unencrypted_original_NPZ')
                f.seek(info.header_offset);local=f.read(30)
                require(local[:4]==b'PK\x03\x04','local_ZIP_header')
                nl,xl=struct.unpack_from('<HH',local,26);begin=info.header_offset+30+nl+xl
                f.seek(begin);h,off=header(f);meta[info.filename]={'start':begin+off,'header':h}
            def read_payload(name,size):
                f.seek(meta[name]['start']);return f.read(size)
            require(read_payload('format.npy',3)==b'csc','original_CSC_format')
            require(struct.unpack('<2q',read_payload('shape.npy',16))==(344103,344103),'original_K_shape')
            require(meta['indices.npy']['header']=={'descr':'<i4','fortran_order':False,'shape':(23646483,)},'original_index_shape')
            require(meta['data.npy']['header']=={'descr':'<f8','fortran_order':False,'shape':(23646483,)},'original_data_shape')
            ptr=array('i');ptr.frombytes(read_payload('indptr.npy',344104*4))
            require(sys.byteorder=='little' and ptr.itemsize==4 and ptr[0]==0 and ptr[-1]==23646483,'original_CSC_pointer_domain')
            require(all(a<=b for a,b in zip(ptr,ptr[1:])),'original_CSC_monotone_pointers')
            column_values={}
            for col in needed_columns:
                lo,hi=ptr[col],ptr[col+1];n=hi-lo;require(n<=512,'finite_column_support')
                f.seek(meta['indices.npy']['start']+4*lo);indices=struct.unpack('<'+'i'*n,f.read(4*n))
                f.seek(meta['data.npy']['start']+8*lo);values=struct.unpack('<'+'d'*n,f.read(8*n))
                require(list(indices)==sorted(set(indices)),'original_column_canonical')
                column_values[col]={i:a for i,a in zip(indices,values) if i not in FIXED and a!=0.0}
        wanted=set().union(*(set(v) for v in column_values.values()))|{59009}
        require(len(wanted)<=4096,'finite_cached_rows')
        rows={i:[] for i in wanted};matched=0
        with K.open('rb') as ix,K.open('rb') as da:
            ix.seek(meta['indices.npy']['start']);da.seek(meta['data.npy']['start'])
            for lo in range(0,23646483,CHUNK_ENTRIES):
                guard();count=min(CHUNK_ENTRIES,23646483-lo)
                indices=array('i');indices.frombytes(ix.read(4*count));data=da.read(8*count)
                require(len(indices)==count and len(data)==8*count,'full_stream_chunk')
                for k,i in enumerate(indices):
                    if i in wanted:
                        j=bisect_right(ptr,lo+k)-1
                        if j not in FIXED:
                            a=struct.unpack_from('<d',data,8*k)[0];rows[i].append((j,a));matched+=1
                require(matched<=262144,'finite_cached_original_terms')
        require(all(len(v)<=1024 and [j for j,a in v]==sorted(set(j for j,a in v)) for v in rows.values()),'canonical_finite_original_rows')
        expected=[(x['original_column_DOF'],float.fromhex(x['coefficient_hex'])) for x in stage['ordered_support']]
        require(rows[138164]==expected,'actual_original_K_row_matches_recorded_CSC_order')
        values={j:U(j) for row in rows.values() for j,a in row}
        def row_dot(i,changes):
            total=0.0
            for j,a in rows[i]:total=total+float(a)*float(changes.get(j,values[j]))
            return total-B(i)
        row_base={i:row_dot(i,{}) for i in wanted}
        exact={i:sum((Fraction.from_float(a)*Fraction.from_float(values[j]) for j,a in row),Fraction())-Fraction.from_float(B(i)) for i,row in rows.items()}
        for q in report['trials'][0]['exact_affected_proof']['all_affected_rows']:
            require(exact[q['original_row_DOF']]==unpack(q['after']),'actual_trial1_full_exact_proof_reproduced')
        for i in column_values[160238]:struct.pack_into('<d',residual,eo+8*fi(i),row_base[i])
        require(sha(residual)==plan['current_N9_residual_sha256'],'derived_current_whole_residual_matches_actual_N9_SHA')
        for i in wanted:require(bits(row_base[i])==bits(struct.unpack_from('<d',residual,eo+8*fi(i))[0]),'every_cached_current_row_matches_actual_native_residual_bytes')
        errors=array('d');errors.frombytes(residual[eo:]);denom=report['final'][0]['normalization_denominator']
        baseline_count=sum(abs(e)/denom>1e-7 for e in errors)
        top=heapq.nlargest(513,enumerate(errors),key=lambda t:abs(t[1]))
        baseline_max=abs(top[0][1])/denom
        require(baseline_count==15 and baseline_max==report['final'][0]['free_dof_residual_infinity_ratio'],'actual_whole_baseline_reproduced')
        r.update(cached_rows=len(rows),cached_original_terms=matched,matrix_entries_streamed=23646483,
            matrix_array_loaded=False,derived_current_field_sha256=sha(u),derived_current_residual_sha256=sha(residual),
            all_cached_current_rows_bitmatch_declared_actual_native_residual=True,
            all_original_trial1_affected_exact_values_reproduced=True,
            original_K_file_SHA_checked=plan['original_K_sha256'],setup_seconds=time.monotonic()-start)
        pool=sorted(exact,key=lambda i:(-abs(exact[i]),i))
        float_terms=0;exact_increment_terms=0
        def candidate(kind,requested):
            nonlocal float_terms,exact_increment_terms
            guard();changes={};deltas={};description=[]
            for col,direction,steps in requested:
                before=values[col];after=before
                for _ in range(steps):after=math.nextafter(after,-math.inf if direction<0 else math.inf)
                changes[col]=after;deltas[col]=Fraction.from_float(after)-Fraction.from_float(before)
                description.append({'DOF':col,'direction':direction,'ULP_steps':steps,'old_hex':before.hex(),'new_hex':after.hex(),'delta_hex':(after-before).hex()})
            pred=row_dot(138164,changes);float_terms+=len(rows[138164])
            record={'index':len(r['candidate_records'])+1,'kind':kind,'base_field_sha256':plan['current_N9_field_sha256'],
                'changes':description,'target_original_DOF':138164,'target_predicted_residual_bits':bits(pred),
                'target_predicted_ratio':abs(pred)/denom,'target_predicted_pass':abs(pred)/denom<=1e-7,
                'global_support_checks_performed':False,'predicted_eligible_for_original_native_full_trial':False,
                'native_full_five_gate_executed':False}
            if record['target_predicted_pass']:
                affected=set().union(*(set(column_values[j]) for j in changes));require(len(affected)<=512,'finite_union_affected_rows')
                after={i:exact[i]+sum((Fraction.from_float(column_values[j].get(i,0.0))*deltas[j] for j in changes),Fraction()) for i in affected}
                exact_increment_terms+=len(affected)*len(changes)
                mb=max(abs(exact[i]) for i in affected);ma=max(abs(v) for v in after.values())
                anchor=59009
                if anchor in affected or abs(exact[anchor])<ma:anchor=next((i for i in pool if i not in affected),None)
                cert=ma<=mb or (anchor is not None and abs(exact[anchor])>=ma)
                predicted={i:row_dot(i,changes) for i in affected};float_terms+=sum(len(rows[i]) for i in affected)
                count=baseline_count-sum(abs(errors[fi(i)])/denom>1e-7 for i in affected)+sum(abs(v)/denom>1e-7 for v in predicted.values())
                # Use the original free complement, preserving the six unsorted fixed originals.
                def original_dof(index):
                    value=index
                    for fixed_dof in SORTED_FIXED:
                        if fixed_dof<=value:value+=1
                    return value
                outside=next(abs(v) for idx,v in top if original_dof(idx) not in affected)
                ratio=max(outside,max(abs(v) for v in predicted.values()))/denom
                eligible=cert and count<baseline_count and ratio<=baseline_max
                record.update(global_support_checks_performed=True,affected_rows=len(affected),
                    affected_exact_infinity_before=pack(mb),affected_exact_infinity_after=pack(ma),
                    anchor_original_DOF=anchor,anchor_exact=pack(exact[anchor]) if anchor is not None else None,
                    anchor_outside_all_changed_nonzero_support=anchor not in affected if anchor is not None else False,
                    global_exact_infinity_nonincrease_certified=cert,
                    predicted_whole_original_probe0_ratio=ratio,predicted_whole_probe0_violating_rows=count,
                    predicted_eligible_for_original_native_full_trial=eligible)
                if eligible and len(r['full_affected_row_certificates_for_first_three_predicted_eligible'])<3:
                    r['full_affected_row_certificates_for_first_three_predicted_eligible'].append({'candidate_index':record['index'],
                        'all_affected_rows':[{'DOF':i,'exact_before':pack(exact[i]),'exact_after':pack(after[i]),
                            'native_base_float64_bits':bits(errors[fi(i)]),'predicted_after_float64_bits':bits(predicted[i]),
                            'changed_column_coefficients_hex':{str(j):column_values[j].get(i,0.0).hex() for j in changes}} for i in sorted(affected)]})
                if kind=='single' and requested==[(138164,-1,1)]:
                    field=bytearray(u);res=bytearray(residual)
                    struct.pack_into('<d',field,uo+8*138164,changes[138164])
                    for i,v in predicted.items():struct.pack_into('<d',res,eo+8*fi(i),v)
                    require(sha(field)==report['trials'][1]['probes'][0]['field_identity']['sha256'],'actual_rejected_trial2_full_field_bytes_reproduced')
                    require(sha(res)==report['trials'][1]['probes'][0]['residual_identity']['sha256'],'actual_rejected_trial2_full_native_residual_bytes_reproduced')
                    require(ratio==report['trials'][1]['probes'][0]['free_dof_residual_infinity_ratio'] and count==15 and not cert,'actual_rejected_trial2_all_acceptance_controls')
                    r['actual_rejected_trial2_whole_field_residual_SHA_controls']=True
            require(float_terms<=16000000 and exact_increment_terms<=524288,'finite_scalar_arithmetic_term_caps')
            r['candidate_records'].append(record)
        for distance in (1,2,4,8):
            for col in columns:
                for direction in (-1,1):candidate('single',[(col,direction,distance)])
        for distance in (1,2,4,8):
            for col in columns:
                if col==138164:continue
                for direction in (-1,1):candidate('paired_with_actual_rejected_primary',[(138164,-1,1),(col,direction,distance)])
        require(len(r['candidate_records'])==904,'registered_candidate_count')
        r.update(completed=True,float64_scalar_product_terms=float_terms,exact_candidate_increment_terms=exact_increment_terms,
            predicted_eligible_indices=[x['index'] for x in r['candidate_records'] if x['predicted_eligible_for_original_native_full_trial']],
            full_native_execution_strategy_not_yet_registered=True)
    except BaseException as e:
        r['failure_type']=type(e).__name__
        if isinstance(e,ValueError):r['failure_gate']=str(e)
    save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('candidate_records','full_affected_row_certificates_for_first_three_predicted_eligible')},indent=2))
    return 0 if r['completed'] else 2

if __name__=='__main__':raise SystemExit(main())
