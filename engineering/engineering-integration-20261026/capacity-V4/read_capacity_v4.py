"""Separate pure record reader: source contract, signed values, all saved hashes.

No CAD imports or BREP recomputation; a native numerical certificate is not
converted into a formal continuous or physical-domain proof.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
import copy
import json
import math
import sys
from run_capacity_v4 import ROOT,S4,sha,require,validate_native_specification
import slide_evidence as evidence
import slide_domain as domain
import full_slide_api_v4 as api
import capacity_stage_v4 as stage


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--science',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();folder=args.science.resolve()
    result={'schema':'razr-V4-separate-record-reader-v1','execution_completed':False,'passed':False,
        'CAD_imported':False,'BREP_geometry_recomputed':False,'full_11781_native_execution_claimed':False,
        'formal_interval_certificate':False,'physical_qualification':False,'candidate_go':False,
        'fixture_fabrication_go':False,'manufacturing_go':False,'verified_call_JSON_files':0,
        'verified_BREP_files':0,'verified_input_whole_materials':0}
    try:
        path=folder/'report.json';report=json.loads(path.read_text())
        result['original_report_sha256']=sha(path)
        require(report['functional_source_commit']==S4,'functional source differs')
        require(report['execution_completed'] is True and report['all_original_postguards_passed'] is True
            and report['source_runtime_unchanged'] is True and report['external_source_unchanged'] is True,
            'producer unfinished or postguard/source gate failed')
        names=evidence.expected_names();require(names==report['complete_participant_names'],'source names differ')
        construction=report['construction']
        profiles=evidence.original_profiles()
        laws=domain.rigid_laws(names,construction['native_slot_halfwidth_mm'],names)
        springs={n:evidence.Spring(n,tuple(v)) for n,v in construction['base_spring_bounds_mm'].items()}
        contract=evidence.Contract(names,laws,profiles,springs)
        require(report['source_domain']==evidence.recorded_domain(profiles),'source nominal domain differs')
        evidence.validate_metadata(construction['current_candidate_factory_metadata'])
        require(evidence.validate_construction(construction['construction'],contract) is True,
                'complete original factory probes incomplete')
        result['original_factory_probes_rebuilt']=len(construction['construction']['probes'])
        result['whole_nonflex_probe_checks']=sum(len(p['material_law_checks']) for p in construction['construction']['probes'])
        calls={}
        for row in report['calls']:
            call=row['call_id'];require(call not in calls,'duplicated native call')
            path=folder/(call+'.json');require(sha(path)==row['case_json_sha256'] and path.stat().st_size==row['case_json_bytes'],'native call bytes differ')
            entry=json.loads(path.read_text());require(entry['execution_completed'] is True,'native call incomplete')
            require(entry['target']==row['target'],'native call target differs')
            require(entry['unchanged_original_postguards_passed'] is True,'original postguard failed')
            validate_native_specification(entry['new_result'],evidence.postguard)
            require(entry['new_result']['capacity_call_id']==call,'native result points to another call')
            for m in entry['material_exports']:
                p=folder/m['path'];require(p.parent==folder and p.is_file() and not p.is_symlink(),'unsafe BREP member')
                require(sha(p)==m['sha256'] and p.stat().st_size==m['bytes'],'saved BREP bytes differ')
                result['verified_BREP_files']+=1
                if m['label'] in ('moving-input','fixed-input'):
                    sig=m['signature'];require(sig['is_valid'] is True and math.isfinite(sig['signed_volume_mm3']) and sig['signed_volume_mm3']>0,
                        'original whole input signed topology invalid')
                    require(sig['solid_signed_volumes_mm3'] and all(math.isfinite(x) and x>0 for x in sig['solid_signed_volumes_mm3']),
                        'whole input contains nonpositive solid')
                    result['verified_input_whole_materials']+=1
            calls[call]=entry
        result['verified_call_JSON_files']=len(calls)
        require(result['verified_input_whole_materials']==2*len(calls),'whole input omitted')
        references=[]
        def expand(value):
            if isinstance(value,list):return [expand(v) for v in value]
            if isinstance(value,dict):
                if value.get('schema')==api.SCHEMA:
                    call=value['capacity_call_id'];references.append(call)
                    r=calls[call]['new_result'];require(r['disposition']==value['disposition'],'compact result changed')
                    return r
                return {k:expand(v) for k,v in value.items()}
            return value
        capacity=report['capacity'];selected=capacity['selected_pair_results']
        require([(r['a'],r['b']) for r in selected]==stage.priority_pairs(names),'selected pair inventory missing or substituted')
        for saved in selected:
            row=expand(saved)
            stage.validate_interval_record(row,row['a'],row['b'],F(0),F(12),contract=contract,api=api,
                validate_specification=lambda r:validate_native_specification(r,evidence.postguard))
        require(len(references)==len(set(references))==len(calls) and set(references)==set(calls),
                'native call omitted or referenced twice')
        reference=report['complete_pair_inventory'];path=folder/reference['path']
        require(path.parent==folder and sha(path)==reference['sha256'] and path.stat().st_size==reference['bytes'],'full pair inventory differs')
        rows=json.loads(path.read_text())['rows'];status=api.inventory_status(rows,names)
        require(status==capacity['full_inventory_status'],'full pending inventory status differs')
        actual={(r['a'],r['b']):r['disposition'] for r in selected}
        require(all(r['disposition']==actual.get((r['a'],r['b']),'not_evaluated') for r in rows),
                'unmeasured pair claimed as evaluated')
        require(status['counts'].get('not_evaluated')==11764 and status['all_pairs_evaluated'] is False,
                'capacity subset falsely presented as full execution')
        result.update(execution_completed=True,passed=True,selected_pairs=17,
            selected_pair_disposition_counts=report['selected_pair_disposition_counts'],
            complete_original_pair_inventory=11781,pending_unmeasured_pairs=11764,
            original_native_q_domain=report['source_domain'])
    except Exception as exc:
        result['failure_type']=type(exc).__name__
    finally:
        result['CAD_imported']=any(n=='cadquery' or n=='OCP' or n.startswith('OCP.') for n in sys.modules)
        if result['CAD_imported']:result['passed']=False
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result.get(k) for k in ('execution_completed','passed','verified_call_JSON_files','verified_BREP_files','failure_type')}))
    return 0 if result['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
