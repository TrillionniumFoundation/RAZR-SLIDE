"""Synthetic G5 chain controls; not physical measurements or decisions."""
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path('/workspace/scratch/1b842ca762be/RAZR-SLIDE')
spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_product_qualification_contracts.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
q=module.q


def probe(kind):
    fixture=module.Contracts();fixture.setUp()
    try:
        plan,record,g3,raw=fixture.prerequisite_fixture()
        synthetic=q.evaluate_g4(plan,record,ROOT,fixture.folder)
        assert synthetic['execution_kind']=='synthetic_fixture' and synthetic['status']!='pass'
        # A deliberately fabricated prerequisite schema for parser testing only.
        # Reuse real evaluator's synthetic coverage/criteria structure to avoid
        # inventing a success-list representation that evaluate_g4 never emits.
        g4=dict(schema='razr-product-qualification-decision-v1',gate='G4',execution_kind='physical',
            execution_binding={'physical_commit_bytes_verified':True},specimen_ids=['SYNTHETIC-S1'],
            design_binding=plan['design_binding'],status='pass',sampled_criteria_status='pass',
            criteria=synthetic['criteria'],coverage=synthetic['coverage'],observations=synthetic['observations'],
            function_unknown_cells=synthetic['function_unknown_cells'],function_failure_witnesses=[],
            acquisition_started_at_utc='2026-10-02T21:30:00Z',acquisition_ended_at_utc='2026-10-02T22:00:00Z',
            qualification_reviewed_at_utc='2026-10-02T22:30:00Z',
            as_built_specimen_records={'SYNTHETIC-S1':g3['as_built_specimen_record']})
        if kind=='g3_review_after_g4_start':
            g3['qualification_reviewed_at_utc']='2026-10-02T23:00:00Z'
            g3['preregistration_verification']={'reviewed_at_utc':'2026-10-02T23:00:00Z'}
            # Isolate chronology from the separate empty-criteria regression.
            g4['criteria']=[{'metric':'synthetic','status':'pass'}]
            plan['prerequisites']['G3']['SYNTHETIC-S1']=fixture.save('g3-late-review.json',g3)
        plan['gate']='G5';plan['prerequisites']['G4']={'SYNTHETIC-S1':fixture.save('g4-schema-fixture.json',g4)}
        blockers=[]
        try:
            decisions=q.prerequisite_decisions(plan,q.Evidence(fixture.folder),blockers,record)
            return dict(case=kind,rejected=False,decisions=decisions,blockers=blockers,synthetic_fixture=True,
                actual_synthetic_evaluator_criteria=synthetic['criteria'],physical_measurements_or_overall_physical_pass_claimed=False)
        except ValueError as exc:return dict(case=kind,rejected=True,message=str(exc),blockers=blockers,synthetic_fixture=True,physical_measurements_or_overall_physical_pass_claimed=False)
    finally:fixture.doCleanups()


if __name__=='__main__':
    result=[probe(k) for k in ['valid_g4_empty_exception_criteria','g3_review_after_g4_start']]
    pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(schema='r12.independent_g5_chain_controls.v1',cases=result),indent=2)+'\n')
    print(json.dumps(result,indent=2))
