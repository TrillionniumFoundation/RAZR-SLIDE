"""Synthetic protocol fixtures only; none are physical qualification evidence."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'integration'))
import product_qualification as q


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.save('synthetic-protocol.txt',b'SYNTHETIC TEST FIXTURE. Not measured hardware or approved limits.\n')

    def save(self,name,data):
        if not isinstance(data,bytes): data = json.dumps(data).encode()
        (self.folder/name).write_bytes(data)
        return {'path':name,'sha256':hashlib.sha256(data).hexdigest()}

    def criterion(self,unit,direction):
        limits = {'minimum':0.,'maximum':2.} if direction == 'range' else {direction:2.}
        return {'unit':unit,**limits,'source':self.source,'source_locator':'hypothetical test limits only'}

    def cal(self,unit):
        return {'unit':unit,'absolute_error_bound':0. if unit == 'count' else .01,
                'source':self.source,'recorded_at_utc':'2026-10-01T00:00:00Z'}

    def base(self,gate):
        plan = q.templates(ROOT)[gate]
        plan.update(is_template=False,specimen_ids=['SYNTHETIC-S1'],declared_at_utc='2026-10-02T00:00:00Z',approved_by='synthetic test fixture',approval_evidence=[self.source])
        record = {'schema':'razr-product-qualification-acquisition-v1','gate':gate,'execution_kind':'synthetic_fixture',
            'specimen_ids':plan['specimen_ids'],'design_binding':plan['design_binding'],
            'started_at_utc':'2026-10-03T00:00:00Z','ended_at_utc':'2026-10-03T00:10:00Z',
            'as_built':{'SYNTHETIC-S1':{'design_binding':plan['design_binding'],**{role:{'identity':'synthetic','source':self.source} for role in ('parts','material_lots','process','firmware','assembly')}}}}
        return plan,record

    def g4(self):
        plan,record = self.base('G4')
        values = {'minimum_cycles_per_mode':1,'minimum_samples_per_phase':2,'maximum_sampling_gap_s':1.,'maximum_alignment_error_s':0.}
        for key,value in values.items(): plan['requirements'][key] = {'value':value,'source':self.source,'source_locator':'synthetic requirement'}
        record['calibrations'] = {}
        for channel,item in plan['channels'].items():
            _,unit,direction = q.G4_METRICS[item['metric']]
            item.update(measured_location='synthetic channel only',identity_source=self.source,criterion=self.criterion(unit,direction))
            record['calibrations'][channel] = self.cal(unit)
        record.update(alignment_error_bound_s=0.,synchronization_evidence=self.source,phase_windows=[])
        plan['function_protocols'] = {f:{'identity':'synthetic','source':self.source,'source_locator':'synthetic protocol'} for f in q.FUNCTIONS}
        record['function_evidence'] = {f:{'source':self.source,'source_locator':'synthetic raw observation'} for f in q.FUNCTIONS}
        rows = []
        for mode_index,mode in enumerate(q.MODES):
            for i,phase in enumerate(q.PHASES):
                base = 100*mode_index+i*2.
                record['phase_windows'].append({'specimen_id':'SYNTHETIC-S1','mode':mode,'cycle':1,'phase':phase,'start_s':base,'end_s':base+1.})
                for t in (base,base+1.):
                    rows.append({'specimen_id':'SYNTHETIC-S1','mode':mode,'cycle':1,'phase':phase,'time_s':t,
                        'function_outcomes':{f:'observed_ok' for f in q.FUNCTIONS},
                        'values':{c:0 if q.G4_METRICS[x['metric']][1] == 'count' else 1. for c,x in plan['channels'].items()}})
        record['raw_observations'] = self.save('observations.json',rows)
        return plan,record,rows

    def run4(self,plan,record): return q.evaluate_g4(plan,record,ROOT,self.folder)

    def g5(self):
        plan,record = self.base('G5')
        for key,value in {'required_cycles':2,'minimum_specimens':1,'maximum_exposure_sampling_gap_s':.1,'minimum_samples_per_exposure_phase':2,'maximum_alignment_error_s':0.}.items():
            plan['requirements'][key] = {'value':value,'source':self.source,'source_locator':'synthetic requirement'}
        plan['checkpoints_cycles'] = [0,2]
        plan['criteria'] = {m:self.criterion(u,d) for m,(u,d) in q.G5_METRICS.items()}
        plan['exposure'] = {m:self.criterion(u,'range') for m,(u,_,_) in q.EXPOSURE.items()}
        plan['critical_dimensions'] = {'synthetic_wall':self.criterion('mm','range')}
        plan['cycle_protocol'] = {'identity':'synthetic','source':self.source,'source_locator':'synthetic complete cycle'}
        record['calibrations'] = {m:self.cal(u) for m,(u,_) in q.G5_METRICS.items()}
        record['calibrations'].update({'exposure:'+m:self.cal(u) for m,(u,_,_) in q.EXPOSURE.items()})
        record['calibrations']['dimension:synthetic_wall'] = self.cal('mm')
        fields = ['specimen_id','cycle','start_s','end_s','maximum_sampling_gap_s','observed_phase_order']+[k for _,a,b in q.EXPOSURE.values() for k in (a,b)]
        rows = []
        raw = []; windows = []
        for n in (1,2):
            base = 1.+(n-1)*.17
            rows.append({'specimen_id':'SYNTHETIC-S1','cycle':n,'start_s':base,'end_s':base+.17,'maximum_sampling_gap_s':.01,'observed_phase_order':'|'.join(q.PHASES),**{k:1. for k in fields[6:]}})
            for i,phase in enumerate(q.PHASES):
                a,b = base+i*.01,base+(i+1)*.01
                windows.append({'specimen_id':'SYNTHETIC-S1','cycle':n,'phase':phase,'start_s':a,'end_s':b})
                for t in (a,b): raw.append({'specimen_id':'SYNTHETIC-S1','cycle':n,'phase':phase,'time_s':t,'values':{m:1. for m in q.EXPOSURE}})
        stream = io.StringIO(); writer = csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        record['cycle_csv'] = self.save('cycles.csv',stream.getvalue().encode())
        record['raw_exposure_samples'] = self.save('exposure-samples.json',raw)
        record['exposure_phase_windows'] = self.save('exposure-phases.json',windows)
        record['phase_observation_evidence'] = self.source
        record['synchronization_evidence'] = self.source
        record['alignment_error_bound_s'] = 0.
        observations = [{'specimen_id':'SYNTHETIC-S1','cycle':n,'metric':m,'reported_outcome':'observed_ok','value':0 if u == 'count' else 1.} for n in (0,2) for m,(u,_) in q.G5_METRICS.items()]
        record['checkpoint_observations'] = self.save('checkpoints.json',observations)
        record['process_measurements'] = [{'specimen_id':'SYNTHETIC-S1','dimension':'synthetic_wall','value':1.,'source':self.source}]
        record['failures'] = []
        record['maintenance_or_replacement_events'] = []
        return plan,record,observations

    def run5(self,plan,record): return q.evaluate_g5(plan,record,ROOT,self.folder)

    def rewrite_summary(self,record,edit):
        reader = csv.DictReader(io.StringIO((self.folder/'cycles.csv').read_text())); rows = list(reader)
        edit(rows)
        out = io.StringIO(); writer = csv.DictWriter(out,fieldnames=reader.fieldnames); writer.writeheader(); writer.writerows(rows)
        record['cycle_csv'] = self.save('cycles.csv',out.getvalue().encode())

    def test_g4_cross_phase_sampling_gap_cannot_be_split(self):
        p,r,rows = self.g4(); rows[1]['time_s'] = .6; rows[2]['time_s'] = 2.4
        r['raw_observations'] = self.save('observations.json',rows)
        out = self.run4(p,r)
        self.assertFalse(out['coverage'][1]['complete'])
        self.assertAlmostEqual(out['coverage'][1]['maximum_gap_including_boundaries_s'],1.8)

    def test_g5_cross_phase_sampling_gap_is_rederived(self):
        p,r,_ = self.g5(); p['requirements']['maximum_exposure_sampling_gap_s']['value'] = .011
        raw = json.loads((self.folder/'exposure-samples.json').read_text())
        for row,t in zip(raw[:4],(1.003,1.004,1.016,1.017)): row['time_s'] = t
        r['raw_exposure_samples'] = self.save('exposure-samples.json',raw)
        with self.assertRaisesRegex(ValueError,'summary statistic'):
            self.run5(p,r)
        self.rewrite_summary(r,lambda rows:rows[0].update(maximum_sampling_gap_s='.012'))
        self.assertIn('cycle_exposure_coverage_incomplete:SYNTHETIC-S1:1',self.run5(p,r)['blockers'])

    def test_g5_cross_cycle_exposure_gap_stays_unknown(self):
        p,r,_ = self.g5()
        for key,name,fields in (('raw_exposure_samples','exposure-samples.json',('time_s',)),('exposure_phase_windows','exposure-phases.json',('start_s','end_s'))):
            raw = json.loads((self.folder/name).read_text())
            for row in raw:
                if row['cycle'] == 2:
                    for field in fields: row[field] += 1.
            r[key] = self.save(name,raw)
        def edit(rows):
            rows[1].update(start_s=str(float(rows[1]['start_s'])+1),end_s=str(float(rows[1]['end_s'])+1),maximum_sampling_gap_s='1.0')
        self.rewrite_summary(r,edit)
        self.assertIn('cycle_exposure_coverage_incomplete:SYNTHETIC-S1:2',self.run5(p,r)['blockers'])

    def test_synthetic_g3_cannot_qualify_a_physical_prerequisite(self):
        p,r,_ = self.g4()
        prior = {'schema':'razr-unpowered-motion-qualification-decision-v1','current_EP5_candidate_bound':True,
            'execution_kind':'synthetic_fixture','specimen_id':'SYNTHETIC-S1','design_binding':p['design_binding'],'status':'pass'}
        p['prerequisites']['G3'] = {'SYNTHETIC-S1':self.save('prior-g3.json',prior)}
        with self.assertRaisesRegex(ValueError,'physical current EP5 G3'):
            self.run4(p,r)

    def test_g4_prerequisite_requires_verified_physical_commit_bytes(self):
        p,r,_ = self.g5()
        prior = {'schema':'razr-product-qualification-decision-v1','gate':'G4',
            'execution_kind':'physical','specimen_ids':['SYNTHETIC-S1'],'design_binding':p['design_binding'],'status':'pass',
            'execution_binding':{'physical_commit_bytes_verified':False}}
        p['prerequisites']['G4'] = {'SYNTHETIC-S1':self.save('prior-g4.json',prior)}
        with self.assertRaisesRegex(ValueError,'physical commit bytes'):
            self.run5(p,r)

    def test_g4_complete_synthetic_matrix_is_not_physical_pass(self):
        p,r,_ = self.g4(); out = self.run4(p,r)
        self.assertEqual(out['sampled_criteria_status'],'pass')
        self.assertEqual(out['status'],'unknown')
        self.assertEqual(len(out['coverage']),34)
        self.assertTrue(all(x['complete'] for x in out['coverage']))
        self.assertFalse(out['manufacturing_go'])

    def test_g4_missing_function_never_passes(self):
        p,r,rows = self.g4(); rows[0]['function_outcomes'].pop('usb')
        r['raw_observations'] = self.save('observations.json',rows)
        self.assertEqual(self.run4(p,r)['sampled_criteria_status'],'unknown')

    def test_g4_not_observed_never_passes(self):
        p,r,rows = self.g4(); rows[0]['function_outcomes']['display'] = 'not_observed'
        r['raw_observations'] = self.save('observations.json',rows)
        self.assertEqual(self.run4(p,r)['sampled_criteria_status'],'unknown')

    def test_g4_failure_survives_missing_metrics_and_coverage(self):
        p,r,rows = self.g4(); rows = rows[:1]
        rows[0]['function_outcomes']['usb'] = 'observed_failure'; rows[0]['values'] = {}
        r['raw_observations'] = self.save('observations.json',rows)
        out = self.run4(p,r)
        self.assertEqual(out['status'],'fail')
        self.assertEqual(out['function_failure_witnesses'][0]['function'],'usb')

    def test_g4_categorical_failure_survives_missing_raw_samples(self):
        p,r,_ = self.g4(); r['raw_observations'] = None
        r['failures'] = [{'specimen_id':'SYNTHETIC-S1','description':'synthetic damaged display tail','source':self.source}]
        out = self.run4(p,r)
        self.assertEqual(out['status'],'fail')
        self.assertEqual(out['retained_failure_records'],r['failures'])

    def test_g4_unsourced_categorical_failure_is_not_erased(self):
        p,r,_ = self.g4()
        r['failures'] = [{'specimen_id':'SYNTHETIC-S1','description':'synthetic reported failure','source':None}]
        out = self.run4(p,r)
        self.assertEqual(out['status'],'fail')
        self.assertIn('failure_original_missing',out['blockers'])

    def test_g4_missing_event_history_is_unknown(self):
        p,r,_ = self.g4(); out = self.run4(p,r)
        self.assertIn('maintenance_history_undeclared',out['blockers'])
        self.assertIn('failure_history_undeclared',out['blockers'])

    def test_g4_repair_and_replacement_are_retained_separately(self):
        p,r,_ = self.g4(); r['failures'] = []
        r['maintenance_or_replacement_events'] = [
            {'specimen_id':'SYNTHETIC-S1','event_type':kind,'description':'synthetic '+kind,'source':self.source}
            for kind in ('repair','replacement')]
        out = self.run4(p,r)
        self.assertEqual(out['retained_maintenance_records'],r['maintenance_or_replacement_events'])
        self.assertIn('uninterrupted_specimen_identity_broken_by_maintenance_or_replacement',out['blockers'])
        self.assertEqual(out['status'],'unknown')

    def prerequisite_fixture(self, end='2026-10-02T20:00:00Z'):
        # Deliberately fabricated physical-schema records, only in TemporaryDirectory.
        # These exercise record validation; they are not measured evidence.
        p,r,_ = self.g4()
        original = {'schema':'synthetic-as-built-record','specimen_id':'SYNTHETIC-S1',
            'is_template':False,'execution_kind':'synthetic_fixture',
            'design_binding':p['design_binding'],'assembly_revision':'SYNTHETIC-REV-1',
            'qualification_assembly':{role:r['as_built']['SYNTHETIC-S1'][role]
                for role in ('parts','material_lots','process','firmware','assembly')}}
        ref = self.save('as-built-synthetic.json',original)
        r['as_built']['SYNTHETIC-S1']['specimen_record'] = ref
        prior = {'schema':'razr-unpowered-motion-qualification-decision-v1',
            'current_EP5_candidate_bound':True,'execution_kind':'physical',
            'specimen_id':'SYNTHETIC-S1','design_binding':p['design_binding'],'status':'pass',
            'acquisition_started_at_utc':'2026-10-02T10:00:00Z','acquisition_ended_at_utc':end,
            'qualification_reviewed_at_utc':end,'sampled_criteria_status':'pass',
            'criteria':[{'metric':'synthetic_test_only','status':'pass'}],
            'as_built_specimen_record':ref}
        p['prerequisites']['G3'] = {'SYNTHETIC-S1':self.save('prior-g3-temporal.json',prior)}
        return p,r,prior,original

    def test_prerequisite_cannot_finish_after_next_stage_starts(self):
        p,r,_,_ = self.prerequisite_fixture('2026-10-04T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'prerequisite.*chronology'):
            self.run4(p,r)

    def test_prerequisite_without_time_does_not_qualify_next_stage(self):
        p,r,prior,_ = self.prerequisite_fixture(); del prior['acquisition_ended_at_utc']
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        self.assertIn('prerequisite_chronology_missing:G3:SYNTHETIC-S1',self.run4(p,r)['blockers'])

    def test_same_specimen_with_changed_as_built_record_is_rejected(self):
        p,r,_,original = self.prerequisite_fixture()
        original['assembly_revision'] = 'SYNTHETIC-REV-2-AFTER-REPAIR'
        r['as_built']['SYNTHETIC-S1']['specimen_record'] = self.save('as-built-repaired.json',original)
        with self.assertRaisesRegex(ValueError,'prerequisite.*as-built'):
            self.run4(p,r)

    def test_prerequisite_without_as_built_binding_remains_unknown(self):
        p,r,prior,_ = self.prerequisite_fixture(); del prior['as_built_specimen_record']
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        self.assertIn('prerequisite_as_built_missing:G3:SYNTHETIC-S1',self.run4(p,r)['blockers'])

    def test_prerequisite_pass_cannot_hide_retained_failure(self):
        p,r,prior,_ = self.prerequisite_fixture()
        prior['retained_failure_records'] = [{'description':'synthetic retained failure'}]
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        with self.assertRaisesRegex(ValueError,'prerequisite pass contradicts'):
            self.run4(p,r)

    def test_prerequisite_native_payload_binding_cannot_change(self):
        p,r,prior,_ = self.prerequisite_fixture()
        prior['design_binding'] = copy.deepcopy(prior['design_binding'])
        prior['design_binding']['native_payload_sha256']['synthetic-native-path'] = '0'*64
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        with self.assertRaisesRegex(ValueError,'prerequisite.*design binding'):
            self.run4(p,r)

    def test_same_raw_as_built_cannot_mask_changed_firmware_wrapper(self):
        p,r,_,_ = self.prerequisite_fixture()
        r['as_built']['SYNTHETIC-S1']['firmware'] = {'identity':'SYNTHETIC-CHANGED','source':self.source}
        with self.assertRaisesRegex(ValueError,'as-built.*firmware'):
            self.run4(p,r)

    def test_missing_as_built_role_mapping_stays_unknown(self):
        p,r,prior,original = self.prerequisite_fixture(); del original['qualification_assembly']
        ref = self.save('as-built-synthetic.json',original)
        r['as_built']['SYNTHETIC-S1']['specimen_record'] = prior['as_built_specimen_record'] = ref
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        self.assertIn('as_built_role_binding_missing:SYNTHETIC-S1',self.run4(p,r)['blockers'])

    def test_matching_earlier_prerequisite_and_raw_assembly_are_accepted_as_records(self):
        p,r,_,_ = self.prerequisite_fixture(); out = self.run4(p,r)
        self.assertFalse(any(x.startswith(('prerequisite_chronology_missing:',
            'prerequisite_as_built_missing:','as_built_role_binding_missing:')) for x in out['blockers']))
        self.assertEqual(out['as_built_specimen_records']['SYNTHETIC-S1'],r['as_built']['SYNTHETIC-S1']['specimen_record'])
        self.assertEqual(out['status'],'unknown')  # synthetic input is never a hardware pass
        self.assertEqual(out['prerequisite_decisions'][0]['status'],'pass')

    def test_prerequisite_review_must_precede_next_stage_and_follow_raw_run(self):
        for when in ('2026-10-04T00:00:00Z','2026-10-02T12:00:00Z'):
            with self.subTest(reviewed_at_utc=when):
                p,r,prior,_ = self.prerequisite_fixture(); prior['qualification_reviewed_at_utc'] = when
                p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
                with self.assertRaisesRegex(ValueError,'prerequisite review chronology'):
                    self.run4(p,r)

    def test_missing_prerequisite_decision_time_is_unknown(self):
        p,r,prior,_ = self.prerequisite_fixture(); del prior['qualification_reviewed_at_utc']
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        out = self.run4(p,r)
        self.assertIn('prerequisite_decision_time_missing:G3:SYNTHETIC-S1',out['blockers'])
        self.assertEqual(out['prerequisite_decisions'][0]['reported_status'],'pass')
        self.assertEqual(out['prerequisite_decisions'][0]['status'],'unknown')

    def test_prerequisite_report_cannot_contradict_sampled_criteria(self):
        for status in ('fail','unknown'):
            p,r,prior,_ = self.prerequisite_fixture()
            prior['sampled_criteria_status'] = status
            prior['criteria'][0]['status'] = status
            p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
            with self.assertRaisesRegex(ValueError,'prerequisite pass contradicts its sampled'):
                self.run4(p,r)

    def test_g5_requires_g3_then_g4_order_even_when_both_predate_g5(self):
        p,r,prior,_ = self.prerequisite_fixture('2026-10-02T20:00:00Z')
        p['gate'] = 'G5'
        earlier = dict(prior,schema='razr-product-qualification-decision-v1',gate='G4',
            specimen_ids=['SYNTHETIC-S1'],execution_binding={'physical_commit_bytes_verified':True},
            acquisition_started_at_utc='2026-10-02T08:00:00Z',acquisition_ended_at_utc='2026-10-02T09:00:00Z',
            qualification_reviewed_at_utc='2026-10-02T09:00:00Z',
            as_built_specimen_records={'SYNTHETIC-S1':prior['as_built_specimen_record']})
        p['prerequisites']['G4'] = {'SYNTHETIC-S1':self.save('prior-g4-too-early.json',earlier)}
        with self.assertRaisesRegex(ValueError,'G3/G4 chronology'):
            q.prerequisite_decisions(p,q.Evidence(self.folder),[],r)

    def test_g5_requires_g3_pass_review_before_g4_started(self):
        p,r,prior,_ = self.prerequisite_fixture('2026-10-02T12:00:00Z'); p['gate'] = 'G5'
        prior['qualification_reviewed_at_utc'] = '2026-10-02T20:00:00Z'
        p['prerequisites']['G3']['SYNTHETIC-S1'] = self.save('prior-g3-temporal.json',prior)
        g4 = dict(prior,schema='razr-product-qualification-decision-v1',gate='G4',
            specimen_ids=['SYNTHETIC-S1'],execution_binding={'physical_commit_bytes_verified':True},
            acquisition_started_at_utc='2026-10-02T13:00:00Z',acquisition_ended_at_utc='2026-10-02T14:00:00Z',
            qualification_reviewed_at_utc='2026-10-02T14:30:00Z',
            as_built_specimen_records={'SYNTHETIC-S1':prior['as_built_specimen_record']})
        p['prerequisites']['G4'] = {'SYNTHETIC-S1':self.save('prior-g4-premature.json',g4)}
        with self.assertRaisesRegex(ValueError,'G3 review/G4 chronology'):
            q.prerequisite_decisions(p,q.Evidence(self.folder),[],r)

    def test_g4_empty_exception_list_with_actual_coverage_supports_record_chain(self):
        p,r,prior,_ = self.prerequisite_fixture('2026-10-02T12:00:00Z'); p['gate'] = 'G5'
        g4 = dict(prior,schema='razr-product-qualification-decision-v1',gate='G4',
            specimen_ids=['SYNTHETIC-S1'],execution_binding={'physical_commit_bytes_verified':True},
            acquisition_started_at_utc='2026-10-02T13:00:00Z',acquisition_ended_at_utc='2026-10-02T14:00:00Z',
            qualification_reviewed_at_utc='2026-10-02T14:30:00Z',criteria=[],
            coverage=[{'specimen_id':'SYNTHETIC-S1','complete':True}],observations=2,
            as_built_specimen_records={'SYNTHETIC-S1':prior['as_built_specimen_record']})
        p['prerequisites']['G4'] = {'SYNTHETIC-S1':self.save('prior-g4-empty-exceptions.json',g4)}
        blockers=[]; decisions=q.prerequisite_decisions(p,q.Evidence(self.folder),blockers,r)
        self.assertEqual(blockers,[])
        self.assertEqual([d['status'] for d in decisions],['pass','pass'])
        del g4['coverage']
        p['prerequisites']['G4']['SYNTHETIC-S1'] = self.save('prior-g4-empty-exceptions.json',g4)
        blockers=[]; decisions=q.prerequisite_decisions(p,q.Evidence(self.folder),blockers,r)
        self.assertIn('prerequisite_observation_coverage_missing:G4:SYNTHETIC-S1',blockers)
        self.assertEqual(decisions[-1]['status'],'unknown')

    def test_g4_missing_limit_source_is_unknown(self):
        p,r,_ = self.g4(); p['channels']['power_rail_voltage']['criterion']['source'] = None
        self.assertIn('limit_source_missing:power_rail_voltage',self.run4(p,r)['blockers'])

    def test_g4_uncertainty_straddling_limit_is_unknown(self):
        p,r,rows = self.g4(); rows[0]['values']['power_rail_voltage'] = 2.
        r['raw_observations'] = self.save('observations.json',rows)
        self.assertEqual(self.run4(p,r)['sampled_criteria_status'],'unknown')

    def test_g4_proved_numeric_violation_fails(self):
        p,r,rows = self.g4(); rows[0]['values']['power_rail_voltage'] = 3.
        r['raw_observations'] = self.save('observations.json',rows)
        self.assertEqual(self.run4(p,r)['status'],'fail')

    def test_g4_missing_boundary_samples_are_incomplete(self):
        p,r,rows = self.g4(); rows = rows[1:]
        r['raw_observations'] = self.save('observations.json',rows)
        out = self.run4(p,r); self.assertFalse(out['coverage'][0]['complete'])

    def test_g4_required_function_channel_cannot_be_deleted(self):
        p,r,_ = self.g4(); del p['channels']['usb_error_count']
        rows = json.loads((self.folder/'observations.json').read_text())
        for row in rows: del row['values']['usb_error_count']
        r['raw_observations'] = self.save('observations.json',rows)
        self.assertIn('mandatory_metric_missing:usb_error_count',self.run4(p,r)['blockers'])

    def test_g4_cannot_omit_manual_phase(self):
        p,r,_ = self.g4(); p['phase_order'].remove('UNSEAT')
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_g4_cannot_omit_original_charging_mode(self):
        p,r,_ = self.g4(); p['power_modes'] = ['original_battery']
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_g4_clock_cannot_restart_to_duplicate_exposure(self):
        p,r,_ = self.g4()
        r['phase_windows'][17]['start_s'] = 0.
        r['phase_windows'][17]['end_s'] = 1.
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_g4_function_original_missing_is_explicit(self):
        p,r,_ = self.g4(); del r['function_evidence']['usb']
        self.assertIn('function_original_evidence_missing:usb',self.run4(p,r)['blockers'])

    def test_phase_cannot_extend_beyond_declared_acquisition(self):
        p,r,_ = self.g4(); r['ended_at_utc'] = '2026-10-03T00:00:10Z'
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_review_cannot_approve_another_acquisition(self):
        p,r,_ = self.g4()
        review = {'gate':'G4','plan_semantic_sha256':q.sha_bytes(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
                  'specimen_ids':p['specimen_ids'],'acquisition_semantic_sha256':'0'*64}
        with self.assertRaises(ValueError): q.evaluate_g4(p,r,ROOT,self.folder,review)

    def test_cross_candidate_record_rejected(self):
        p,r,_ = self.g4(); r['design_binding'] = copy.deepcopy(p['design_binding']); r['design_binding']['candidate_id'] = 'OTHER'
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_old_commit_with_identical_configuration_is_not_current(self):
        p,r,_ = self.g4()
        old = copy.deepcopy(p['design_binding']); old['git_commit'] = '0'*40
        old['files_sha256'] = {k:v for k,v in old['files_sha256'].items() if k in q.DESIGN_PATHS}
        p['design_binding'] = old; r['design_binding'] = old
        out = self.run4(p,r)
        self.assertEqual(out['status'],'unknown')
        self.assertIn('historical_commit_is_not_current_qualification',out['blockers'])
        self.assertIn('current_geometry_source_closure_incomplete',out['blockers'])

    def test_current_geometry_source_is_in_required_binding(self):
        paths = q.current_source_paths(ROOT)
        for path in ('integration/product_assembly.py','integration/product_routing_ep5.py','integration/product_nominal_motion.py'):
            self.assertIn(path,paths)

    def test_changed_raw_evidence_rejected(self):
        p,r,_ = self.g4(); (self.folder/'observations.json').write_text('[]')
        with self.assertRaises(ValueError): self.run4(p,r)

    def test_duplicate_json_cannot_hide_reported_failure(self):
        with self.assertRaises(ValueError):
            q.strict_json('{"usb":"observed_failure","usb":"observed_ok"}')

    def test_bool_and_nan_measurements_rejected(self):
        for bad in (True,float('nan'),float('inf')):
            with self.subTest(bad=bad):
                p,r,rows = self.g4(); rows[0]['values']['power_current'] = bad
                r['raw_observations'] = self.save('observations.json',rows)
                with self.assertRaises(ValueError): self.run4(p,r)

    def test_malformed_or_absolute_evidence_rejected(self):
        for ref in ({'path':'../outside','sha256':'0'*64},{'path':str(self.folder/'synthetic-protocol.txt'),'sha256':self.source['sha256']}):
            with self.assertRaises(ValueError): q.Evidence(self.folder).read(ref)

    def test_g5_complete_synthetic_protocol_remains_unknown(self):
        p,r,_ = self.g5(); out = self.run5(p,r)
        self.assertEqual(out['sampled_criteria_status'],'pass')
        self.assertEqual(out['status'],'unknown')
        self.assertEqual(out['completed_cycles_by_specimen'],{'SYNTHETIC-S1':2})

    def test_g5_missing_checkpoint_stays_unknown(self):
        p,r,rows = self.g5(); r['checkpoint_observations'] = self.save('checkpoints.json',rows[:-1])
        self.assertIn('checkpoint_metric_coverage_incomplete',self.run5(p,r)['blockers'])

    def test_g5_unfinished_life_not_passed(self):
        p,r,_ = self.g5(); payload = (self.folder/'cycles.csv').read_text().splitlines()
        r['cycle_csv'] = self.save('cycles.csv',('\n'.join(payload[:-1])+'\n').encode())
        for key,name in (('raw_exposure_samples','exposure-samples.json'),('exposure_phase_windows','exposure-phases.json')):
            raw = json.loads((self.folder/name).read_text())
            r[key] = self.save(name,[row for row in raw if row['cycle'] == 1])
        self.assertIn('required_lifetime_exposure_incomplete:SYNTHETIC-S1',self.run5(p,r)['blockers'])

    def test_g5_failure_survives_early_termination(self):
        p,r,_ = self.g5(); r['cycle_csv'] = None
        r['raw_exposure_samples'] = None
        r['failures'] = [{'specimen_id':'SYNTHETIC-S1','description':'synthetic broken conductor','source':self.source}]
        out = self.run5(p,r)
        self.assertEqual(out['status'],'fail')
        self.assertEqual(out['retained_failure_records'],r['failures'])

    def test_g5_process_missing_and_uncertainty(self):
        p,r,_ = self.g5(); r['process_measurements'] = []
        self.assertIn('process_dimension_coverage_incomplete',self.run5(p,r)['blockers'])
        p,r,_ = self.g5(); r['process_measurements'][0]['value'] = 2.
        self.assertEqual(self.run5(p,r)['sampled_criteria_status'],'unknown')

    def test_g5_cannot_skip_original_cycles(self):
        p,r,_ = self.g5(); payload = (self.folder/'cycles.csv').read_text().replace('SYNTHETIC-S1,2,','SYNTHETIC-S1,3,')
        r['cycle_csv'] = self.save('cycles.csv',payload.encode())
        with self.assertRaises(ValueError): self.run5(p,r)

    def test_g5_cannot_use_short_final_checkpoint(self):
        p,r,_ = self.g5(); p['checkpoints_cycles'] = [0,1]
        with self.assertRaises(ValueError): self.run5(p,r)

    def test_g5_missing_exposure_limit_source_is_unknown(self):
        p,r,_ = self.g5(); p['exposure']['temperature']['source'] = None
        self.assertEqual(self.run5(p,r)['sampled_criteria_status'],'unknown')

    def test_g5_counting_partial_cycles_cannot_pass(self):
        p,r,_ = self.g5()
        payload = (self.folder/'cycles.csv').read_text().replace('|UNSEAT|','|')
        r['cycle_csv'] = self.save('cycles.csv',payload.encode())
        with self.assertRaises(ValueError): self.run5(p,r)

    def test_g5_summary_only_never_qualifies(self):
        p,r,_ = self.g5(); r.pop('raw_exposure_samples')
        out = self.run5(p,r)
        self.assertEqual(out['status'],'unknown')
        self.assertEqual(out['G5_cycle_evidence_scope'],'summary_only_not_qualifying')
        self.assertIn('summary_only_G5_raw_exposure_or_phase_evidence_missing',out['blockers'])

    def test_g5_summary_cannot_hide_raw_exposure_peak(self):
        p,r,_ = self.g5(); rows = json.loads((self.folder/'exposure-samples.json').read_text())
        rows[0]['values']['temperature'] = 3.
        r['raw_exposure_samples'] = self.save('exposure-samples.json',rows)
        with self.assertRaises(ValueError): self.run5(p,r)

    def test_g5_raw_exposure_peak_remains_failure(self):
        p,r,_ = self.g5(); rows = json.loads((self.folder/'exposure-samples.json').read_text())
        rows[0]['values']['temperature'] = 3.
        r['raw_exposure_samples'] = self.save('exposure-samples.json',rows)
        stream = io.StringIO((self.folder/'cycles.csv').read_text()); reader = csv.DictReader(stream); summary = list(reader)
        summary[0]['temperature_max_C'] = '3.0'
        out = io.StringIO(); writer = csv.DictWriter(out,fieldnames=reader.fieldnames); writer.writeheader(); writer.writerows(summary)
        r['cycle_csv'] = self.save('cycles.csv',out.getvalue().encode())
        self.assertEqual(self.run5(p,r)['status'],'fail')

    def test_g5_replacement_cannot_silently_continue_same_life(self):
        p,r,_ = self.g5(); r['maintenance_or_replacement_events'] = [{'specimen_id':'SYNTHETIC-S1','description':'synthetic replacement','source':self.source}]
        self.assertIn('uninterrupted_specimen_identity_broken_by_maintenance_or_replacement',self.run5(p,r)['blockers'])

    def test_g5_event_counts_cannot_be_negative(self):
        p,r,rows = self.g5()
        row = next(x for x in rows if x['metric'] == 'usb_error_count'); row['value'] = -1
        r['checkpoint_observations'] = self.save('checkpoints.json',rows)
        with self.assertRaises(ValueError): self.run5(p,r)

    def test_actual_current_inputs_are_still_missing(self):
        current = q.product_inputs(ROOT)
        config = json.loads((ROOT/'design/product_interfaces.json').read_text())
        self.assertEqual(set(current['unknown_donor_identity_fields']),{k for k,v in config['donor'].items() if v is None})
        self.assertEqual(len(current['physically_bound_interfaces'])+len(current['missing_physical_interfaces']),12)

    def test_templates_never_manufacture_thresholds(self):
        for gate,p in q.templates(ROOT).items():
            out = (q.evaluate_g4 if gate == 'G4' else q.evaluate_g5)(p,None,ROOT,self.folder)
            self.assertEqual(out['status'],'unknown')
            self.assertFalse(out['candidate_go']); self.assertFalse(out['manufacturing_go'])
            self.assertTrue(all(x['value'] is None for x in p['requirements'].values()))


if __name__ == '__main__': unittest.main()
