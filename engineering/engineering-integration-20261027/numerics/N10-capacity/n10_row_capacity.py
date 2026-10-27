"""Finite stdlib-only N9 terminal-row capacity analysis; no native full solve."""
from pathlib import Path
from fractions import Fraction
import ast, datetime, hashlib, json, math, os, resource, struct, time

ROOT = Path('/tmp/razr-next-20261027/numerics')
N8 = Path('/tmp/razr-recovery-20261026/numerics/N8-original-scientific')
REPORT = ROOT/'N9-actual-summary/original/probe-N9/N9_REPORT.json'
OUT = ROOT/'N10-row-capacity'
STEPS = (1, 2, 4, 8)

def require(value, label):
    if not value: raise ValueError(label)

def digest(b): return hashlib.sha256(b).hexdigest()
def packed(q): return {'numerator': str(q.numerator), 'denominator': str(q.denominator)}
def fraction(q): return Fraction(int(q['numerator']), int(q['denominator']))
def bits(x): return struct.pack('>d', x).hex()

def main():
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(64*1024**2,64*1024**2))
    plan=json.loads((OUT/'N10_ROW_CAPACITY_PREREGISTRATION.json').read_text())
    require(plan['registered_before_execution'] is True,'registration_required')
    receipt={'schema':'razr-N10-N9-terminal-row-capacity-v1','completed':False,
        'source_report_sha256':plan['source_report_sha256'],
        'capacity_contract_sha256':digest((OUT/'N10_ROW_CAPACITY_PREREGISTRATION.json').read_bytes()),
        'analysis_source_sha256':digest(Path(__file__).read_bytes()),
        'native_full_gate_evaluated':False,'global_exact_certificate_claimed':False,
        'original_N9_scientific_ZIP_byte_readback_substituted':False,
        'source_field_is_explicit_derivation_from_verified_N8_and_N9_trial1':True,
        'H_frame_restore_executed':False,'records':[]}
    path=OUT/'N10_ROW_CAPACITY_RESULT.json'
    def save():
        receipt['elapsed_seconds']=time.monotonic()-start
        receipt['peak_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        data=(json.dumps(receipt,indent=2,allow_nan=False)+'\n').encode()
        require(len(data)<=2*1024**2,'finite_small_report_byte_cap')
        path.write_bytes(data)
    try:
        raw=REPORT.read_bytes();require(digest(raw)==plan['source_report_sha256'],'actual_N9_report_identity')
        report=json.loads(raw)
        require(report['completed'] is True and report['original_five_passed'] is False,'actual_N9_rejection')
        require(report['accepted_trial_indices']==[1] and report['full_candidates_completed']==2,'actual_trial_chain')
        old=(N8/'probe-N8/final/probe-0-field.npy').read_bytes()
        require(digest(old)==plan['starting_N8_field_sha256'],'verified_N8_field_identity')
        require(old[:8]==bytes([147])+b'NUMPY'+bytes([1,0]),'NPY_v1')
        hlen=struct.unpack('<H',old[8:10])[0];offset=10+hlen
        header=ast.literal_eval(old[10:offset].decode('latin1').strip())
        require(header=={'descr':'<f8','fortran_order':False,'shape':(344103,)},'original_full_field_header')
        require(len(old)==offset+344103*8,'original_full_field_length')
        current=bytearray(old)
        x=struct.unpack_from('<d',current,offset+8*160238)[0]
        xnext=math.nextafter(x,-math.inf)
        require(xnext-x==-2.9802322387695312e-8,'actual_accepted_trial1_delta')
        struct.pack_into('<d',current,offset+8*160238,xnext)
        require(digest(current)==plan['current_N9_field_sha256']==report['final'][0]['field_identity']['sha256'],
            'derived_current_full_NPY_hash_matches_actual_N9_report')
        stage=report['stages'][-1]
        require(stage['target_original_DOF']==138164 and len(stage['ordered_support'])==57,'actual_last_stage')
        require(stage['base_field_sha256']==plan['current_N9_field_sha256'],'stage_current_field_binding')
        columns=[r['original_column_DOF'] for r in stage['ordered_support']]
        coeff=[float.fromhex(r['coefficient_hex']) for r in stage['ordered_support']]
        values=[struct.unpack_from('<d',current,offset+8*j)[0] for j in columns]
        require(columns==sorted(set(columns)),'original_CSC_column_order')
        rhs=float(report['final'][0]['rhs_at_max_dof'])
        denom=float(report['final'][0]['normalization_denominator'])
        def dot(v):
            out=0.0
            for a,u in zip(coeff,v):out=out+float(a)*float(u)
            return out-rhs
        residual=dot(values)
        require(bits(residual)==bits(report['final'][0]['signed_residual_at_max_dof']),
            'reported_native_current_row_bits_reproduced')
        exact=sum((Fraction.from_float(a)*Fraction.from_float(u) for a,u in zip(coeff,values)),Fraction())-Fraction.from_float(rhs)
        t2=report['trials'][1]
        target=[r for r in t2['exact_affected_proof']['all_affected_rows'] if r['original_row_DOF']==138164]
        require(len(target)==1 and exact==fraction(target[0]['before']),'actual_exact_target_before_reproduced')
        anchor=t2['exact_affected_proof']['unaffected_exact_anchor']
        require(anchor['base_field_sha256']==plan['current_N9_field_sha256'],'anchor_current_field_binding')
        anchor_abs=abs(fraction(anchor['signed_exact_residual']))
        adjacent_eligible=[]
        for distance in STEPS:
            for at,(dof,a,u) in enumerate(zip(columns,coeff,values)):
                for direction in (-1,1):
                    require(time.monotonic()-start<10,'finite_10s_local_arithmetic_cap')
                    new=u
                    for _ in range(distance):new=math.nextafter(new,-math.inf if direction<0 else math.inf)
                    delta=Fraction.from_float(new)-Fraction.from_float(u)
                    candidate=values.copy();candidate[at]=new
                    predicted=dot(candidate);after=exact+Fraction.from_float(a)*delta
                    passed=abs(predicted)/denom<=1e-7
                    record={'base_field_sha256':plan['current_N9_field_sha256'],'target_original_DOF':138164,
                        'support_index':at,'original_free_column_DOF':dof,'direction':direction,'ULP_steps':distance,
                        'coefficient_hex':a.hex(),'old_value_hex':u.hex(),'candidate_value_hex':new.hex(),
                        'actual_delta_hex':(new-u).hex(),'predicted_original_row_float64_residual_bits':bits(predicted),
                        'predicted_original_row_float64_residual':predicted,'predicted_row_ratio':abs(predicted)/denom,
                        'predicted_original_row_pass':passed,'exact_target_before':packed(exact),'exact_target_after':packed(after),
                        'target_after_abs_within_known_anchor_magnitude':abs(after)<=anchor_abs,
                        'known_anchor_outside_changed_column_support_checked':False,
                        'all_affected_equations_checked':False,'native_full_five_gate_evaluated':False}
                    if distance==1 and passed:adjacent_eligible.append({'original_screen_index':stage['first_screen_index']+2*at+(direction==1),'column':dof,'direction':direction})
                    receipt['records'].append(record)
        require(adjacent_eligible==[{'original_screen_index':142,'column':138164,'direction':-1}],
            'all_114_adjacent_controls_match_original_report_complete_candidate')
        require(len(receipt['records'])==456,'registered_finite_record_count')
        receipt.update(completed=True,derived_current_field_sha256=digest(current),
            original_native_current_row_bits=bits(residual),exact_current_target=packed(exact),
            known_anchor_original_DOF=59009,known_anchor_exact_absolute=packed(anchor_abs),
            original_adjacent_control_eligible=adjacent_eligible,
            counts_by_ULP_steps={str(k):{'total':sum(r['ULP_steps']==k for r in receipt['records']),
                'predicted_row_pass':sum(r['ULP_steps']==k and r['predicted_original_row_pass'] for r in receipt['records']),
                'predicted_row_pass_and_target_abs_bounded_by_known_anchor':sum(r['ULP_steps']==k and r['predicted_original_row_pass'] and r['target_after_abs_within_known_anchor_magnitude'] for r in receipt['records'])} for k in STEPS})
    except BaseException as e:
        receipt['failure_type']=type(e).__name__
        if isinstance(e,ValueError):receipt['failure_gate']=str(e)
    save()
    print(json.dumps({k:v for k,v in receipt.items() if k!='records'},indent=2))
    return 0 if receipt['completed'] else 2

if __name__=='__main__':raise SystemExit(main())
