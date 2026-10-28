"""Prepare new named contracts; does not run the mathematical worker."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path


def identity(path):
    path=Path(path).resolve()
    with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h}


def main():
    p=argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--phase',choices=['single_stationary_witness','preflight','all_raw','verify_single','verify_all'],required=True)
    p.add_argument('--label',required=True);p.add_argument('--producer-report',type=Path)
    a=p.parse_args();root=Path(__file__).resolve().parent;workspace=root.parent
    old=workspace/'r4-envelope';phase=a.phase
    previous=json.loads((old/'R4E_SUPPORT_SUPERVISION_V4_OWNED.json').read_text())
    worker=root/('verify_exterior_channels_r5e_v1.py' if phase.startswith('verify_') else 'exterior_channels_r5e_v1.py')
    contract={'schema':'razr-r5e-exterior-channel-contract-v1','registered_utc':datetime.now(timezone.utc).isoformat(),
              'phase':phase,'producer_sha256':identity(worker)['sha256'],
              'r4_report':identity(old/'support-v4/report.json'),'r4_independent_report':identity(old/'independent-support-v4/report.json'),
              'r4_stationary_diagnostic':identity(old/'remaining-spatial-diagnostic/report.json'),
              'method':identity(root/'R5E_EXTERIOR_CHANNEL_METHOD.md'),
              'capacity':{'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_candidate_cells':1 if phase=='single_stationary_witness' else 1474,
                          'maximum_static_boundary_box_tests':50000000},
              'native_Common_as_acceptance_premise':False,'original_float64_TOL_unchanged':True,'all_original_D_components_retained':True,
              'native_boundary_semantics_remains_a_premise':True,'current_factory_G2_qualified':False}
    if phase=='single_stationary_witness':contract.update(case_id='case-001',frame=1)
    if phase in ('preflight','all_raw'):
        single=root/'single-stationary-witness/report.json'
        if single.exists():contract['prior_actual_single_witness']=identity(single)
        else:contract['prior_actual_single_witness_missing']=True
    if phase=='all_raw':
        preflight=root/'preflight/report.json'
        if preflight.exists():contract['prior_actual_preflight']=identity(preflight)
        else:contract['prior_actual_preflight_missing']=True
    if phase.startswith('verify_'):
        if a.producer_report is None:raise ValueError('producer report required')
        contract['verifier_sha256']=identity(worker)['sha256'];contract['producer_report']=identity(a.producer_report)
    output=root/a.label;cp=root/(a.label+'-contract.json');sp=root/(a.label+'-supervision-contract.json')
    if cp.exists() or sp.exists():raise ValueError('new named contracts only')
    cp.write_text(json.dumps(contract,indent=2)+'\n')
    supervision=dict(previous)
    supervision.update(schema='razr-r5e-exterior-channel-owned-supervision-v1',registered_utc=contract['registered_utc'],
                       registered_math_contract_sha256=identity(cp)['sha256'],worker=identity(worker),
                       worker_output_directory=str(output),canonical_worker_options=['--contract','--output'],
                       expected_output_bytes=41943040,maximum_output_bytes=41943040,
                       algorithm_basis='Finite complete-boundary exterior channels; see the bound pre-execution method document and phase contract. Original R4 process limits unchanged.')
    sp.write_text(json.dumps(supervision,indent=2)+'\n')
    print(json.dumps({'contract':identity(cp),'supervision':identity(sp),'output':str(output)}))


if __name__=='__main__':main()
