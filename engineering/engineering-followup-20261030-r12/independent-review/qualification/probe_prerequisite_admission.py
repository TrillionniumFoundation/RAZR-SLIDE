"""Synthetic record-admission counterexamples, never physical qualification."""
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path('/workspace/scratch/1b842ca762be/RAZR-SLIDE')
spec=importlib.util.spec_from_file_location('original_fixture',ROOT/'tests/test_product_qualification_contracts.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
q=fixture_module.q


def probe(kind):
    f=fixture_module.Contracts();f.setUp()
    try:
        plan,record,prior,original=f.prerequisite_fixture()
        if kind=='review_after_next_stage_start':
            prior['preregistration_verification']={'reviewed_at_utc':'2026-10-04T00:00:00Z'}
        elif kind=='review_before_previous_acquisition_end':
            prior['preregistration_verification']={'reviewed_at_utc':'2026-10-02T12:00:00Z'}
        elif kind=='explicit_failed_sampled_status':
            prior['sampled_criteria_status']='fail'
            prior['criteria']=[{'metric':'synthetic_force','status':'fail'}]
        elif kind=='missing_decision_time':
            pass
        else:raise ValueError(kind)
        plan['prerequisites']['G3']['SYNTHETIC-S1']=f.save('synthetic-admission.json',prior)
        blockers=[]
        try:
            decisions=q.prerequisite_decisions(plan,q.Evidence(f.folder),blockers,record)
            return dict(case=kind,rejected=False,blockers=blockers,decisions=decisions,
                synthetic_fixture=True,physical_measurement_or_overall_physical_pass_claimed=False,
                prior_record=prior,current_acquisition_start=record['started_at_utc'])
        except (ValueError,TypeError) as exc:
            return dict(case=kind,rejected=True,exception_type=type(exc).__name__,message=str(exc),blockers=blockers,
                synthetic_fixture=True,physical_measurement_or_overall_physical_pass_claimed=False)
    finally:f.doCleanups()


if __name__=='__main__':
    results=[probe(k) for k in ['review_after_next_stage_start','review_before_previous_acquisition_end','missing_decision_time','explicit_failed_sampled_status']]
    target=pathlib.Path(sys.argv[1]);target.write_text(json.dumps(dict(schema='r12.independent_qualification_admission_probes.v1',cases=results),indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ['case','rejected','blockers','decisions']} for r in results],indent=2))
