"""Separate pure L5 record/source reader; no CAD imports or geometry calls."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from run_l5 import ROOT,S4,HERE,sha,require
import l5_science_contract as rules
import validate_product_nominal_report as guard


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--science',type=Path,required=True);ap.add_argument('--native-reader',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    r={'schema':'razr-L5-independent-pure-record-readback-v1','execution_completed':False,'passed':False,
        'verified_geometry_file_hashes':0,'verified_case_JSON_files':0,'source_q_partitions_rebuilt':0,
        'CAD_imported':False,'BREP_geometry_recomputed':False,**{k:False for k in rules.FALSE_FLAGS}}
    try:
        folder=args.science.resolve();report=json.loads((folder/'report.json').read_text())
        r['original_producer_report_sha256']=sha(folder/'report.json');r['original_producer_report_bytes']=(folder/'report.json').stat().st_size
        require(report['functional_source_commit']==S4,'functional source differs')
        binding=json.loads((HERE/'L5_ORIGINAL_SEVEN_BINDING.json').read_text());originals={c['case_id']:c for c in binding['original_cases']}
        exports={}
        for row in report.get('all_scientific_exports',[]):
            name=row['path'];require(rules.scientific_filename(name) and name not in exports,'unreviewed or duplicated scientific path')
            path=folder/name;require(path.parent==folder and path.is_file() and not path.is_symlink(),'missing or linked scientific original')
            require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'actual science bytes changed')
            if row.get('positive_whole_material_required') and path.suffix=='.brep':
                sig=row['signature'];require(sig['is_valid'] is True and math.isfinite(sig['signed_volume_mm3']) and sig['signed_volume_mm3']>0,'invalid whole signed material signature')
                require(sig['solid_signed_volumes_mm3'] and all(math.isfinite(v) and v>0 for v in sig['solid_signed_volumes_mm3']),'nonpositive source solid')
            exports[name]=row;r['verified_geometry_file_hashes']+=1
        seen=[];dispositions=[]
        for row in report.get('calls',[]):
            path=folder/(row['call_id']+'.json');require(path.stat().st_size==row['case_json_bytes'] and sha(path)==row['case_json_sha256'],'original case bytes differ')
            case=json.loads(path.read_text());r['verified_case_JSON_files']+=1
            original=originals[case['original_case_id']];require(case['target']==original['target'] and case['original_result_sha256']==original['original_result']['sha256'],'original exact full-q target differs')
            require(case['call_id']==report['scope']+'-'+case['original_case_id'] and case['call_id'] not in seen,'case identity duplicated or substituted')
            seen.append(case['call_id'])
            for export in case['scientific_exports']:require(exports[export['path']]==export,'case geometry not bound to actual global science original')
            if not case['execution_completed']:continue
            require(case['unchanged_original_postguards_passed'] is True,'completed original postguards failed')
            rules.validate_result(case['new_result'],case['target'],case['target']['specification'],ROOT,guard)
            r['source_q_partitions_rebuilt']+=1;dispositions.append(case['new_result']['disposition'])
        if report['scope']=='current':
            import slide_evidence as evidence
            import slide_domain as domain
            construction=report['construction'];names=evidence.expected_names();profiles=evidence.original_profiles()
            laws=domain.rigid_laws(names,construction['native_slot_halfwidth_mm'],names)
            springs={n:evidence.Spring(n,tuple(v)) for n,v in construction['base_spring_bounds_mm'].items()}
            contract=evidence.Contract(names,laws,profiles,springs)
            evidence.validate_metadata(construction['current_candidate_factory_metadata'])
            require(evidence.validate_construction(construction['construction'],contract) is True,'original five factory probes incomplete')
            require(construction['five_factory_probes_complete'] is True and report['current_factory_five_original_probes_passed'] is True,'actual K1 factory probes not complete')
            from fractions import Fraction as F
            for original in binding['original_cases']:
                target=original['target'];require(contract.specifications(target['a'],target['b'],F(0),F(12),'A')==[target['specification']],'current full source law differs')
            r['original_factory_probes_rebuilt']=len(construction['construction']['probes'])
            r['whole_nonflex_probe_checks']=sum(len(p['material_law_checks']) for p in construction['construction']['probes'])
        native=json.loads(args.native_reader.read_text());r['native_reader_original_sha256']=sha(args.native_reader)
        require(native['original_producer_report_sha256']==r['original_producer_report_sha256'],'native readback bound to another producer')
        require(native['execution_completed'] and native['all_original_postguards_passed'] and native['source_runtime_unchanged'] and native['external_source_unchanged'],'native reader incomplete/failed')
        require(native['verified_export_file_hashes']==len(exports),'native reader geometry inventory differs')
        require(report['execution_completed'] and report['all_original_postguards_passed'] and report['source_runtime_unchanged'] and report['external_source_unchanged'],'producer incomplete or original source gate failed')
        require(len(seen)==r['source_q_partitions_rebuilt']==7 and {x.split('-case-')[1] for x in seen}==set(rules.CASE_NUMBERS),'complete original seven omitted')
        controls=report['L5_primitive_controls'];require(controls['native_controls_completed'] and {x['name'] for x in controls['controls']}==set(rules.CONTROL_NAMES) and all(x['passed'] for x in controls['controls']),'new native primitive controls incomplete')
        old=report['unchanged_L2_native_controls'];require(old['native_controls_completed'] and len(old['controls'])==7,'unchanged L2 native controls incomplete')
        extrusion=report['original_EXTRUSION_direct_control'];require(extrusion['native_executed'] and extrusion['unchanged_original_branch']['same_unsupported_EXTRUSION_failure'] and extrusion['new_V2_native_checks_passed'] and extrusion['original_method_repaired'] is False,'original EXTRUSION was skipped or old failure erased')
        require(Counter(dispositions)==report['disposition_counts']==native['disposition_counts'],'complete result dispositions differ')
        r.update(execution_completed=True,passed=True,scope=report['scope'],disposition_counts=dict(Counter(dispositions)),
            complete_original_q_interval_exact=['0','12'],distinct_physical_pairs=7,
            independent_native_readback_executed=True,same_pinned_CAD_kernel_not_a_second_kernel=True,
            strict_containment_failures_retained=dispositions.count('unresolved_source_containment'))
    except Exception as exc:r['failure_type']=type(exc).__name__
    finally:
        r['CAD_imported']=any(n=='cadquery' or n=='OCP' or n.startswith('OCP.') for n in sys.modules)
        if r['CAD_imported']:r['passed']=False
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:r.get(k) for k in ('passed','execution_completed','verified_geometry_file_hashes','verified_case_JSON_files','failure_type')}))
    return 0 if r['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
