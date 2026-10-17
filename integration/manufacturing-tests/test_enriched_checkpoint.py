"""Same-energy resume identity tests; numerical contact acceptance stays separate."""
from pathlib import Path
import importlib.util,json,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'engineering/volume-convergence-20261017/solve_enriched_contact.py'
spec=importlib.util.spec_from_file_location('enriched_resume_under_test',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class EnrichedCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.repo=self.base/'repo';self.inputs=self.base/'volume';self.state=self.base/'state';self.state.mkdir()
        self.output=self.base/'new-result';self.provenance={}
        for body in ('panel','frame'):
            for name in ('K.npz','loads.npz','mesh.npz','report.json'):
                f=self.inputs/body/'level-1'/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(body+':'+name)
                self.provenance[str(f)]=m.sha256(f)
        for name in ('common-cell-results.json.gz','coupled-field-audit.json.gz'):
            f=self.repo/'engineering/contact-field-20261015'/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(name);self.provenance[str(f)]=m.sha256(f)
        for name in ('assembly_inputs.json','roof_joint_load_inputs.json','frame_thread_actual_inputs.json'):
            f=self.repo/'integration'/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(name);self.provenance[str(f)]=m.sha256(f)
        (self.state/'response.npz').write_text('payload');(self.state/'points.json').write_text('points')
        self.meta={'case':6,'gap_tolerance_mm':1e-7,'state_is_finite_QP_not_gap_qualification':True,'input_sha256':self.provenance,'response_sha256':m.sha256(self.state/'response.npz'),'points_sha256':m.sha256(self.state/'points.json')}
        self.save()
    def save(self):
        (self.state/'manifest.json').write_text(json.dumps(self.meta))
    def read(self,**kwargs):
        return m.read_same_energy_state(self.state,self.inputs,kwargs.get('level',1),self.repo,kwargs.get('output',self.output))
    def test_old_manifest_requires_exact_level_energy_not_optional_label(self):
        self.assertEqual(self.read()['case'],6)
    def test_new_explicit_level_supported(self):
        self.meta['volume_level']=1;self.save();self.assertEqual(self.read()['volume_level'],1)
    def test_cross_level_cache_is_rejected_even_with_matching_dimensions(self):
        self.meta['volume_level']=2;self.save()
        with self.assertRaises(ValueError):self.read()
    def test_changed_stiffness_dependency_is_rejected(self):
        (self.inputs/'panel/level-1/K.npz').write_text('changed')
        with self.assertRaises(ValueError):self.read()
    def test_missing_current_energy_identity_is_rejected(self):
        self.provenance.pop(str(self.inputs/'panel/level-1/K.npz'));self.save()
        with self.assertRaises(ValueError):self.read()
    def test_tampered_response_payload_is_rejected(self):
        (self.state/'response.npz').write_text('wrong')
        with self.assertRaises(ValueError):self.read()
    def test_tampered_point_identity_is_rejected(self):
        (self.state/'points.json').write_text('other')
        with self.assertRaises(ValueError):self.read()
    def test_changed_audit_domain_is_rejected(self):
        (self.repo/'engineering/contact-field-20261015/common-cell-results.json.gz').write_text('different')
        with self.assertRaises(ValueError):self.read()
    def test_changed_actual_inputs_are_rejected(self):
        (self.repo/'integration/assembly_inputs.json').write_text('changed')
        with self.assertRaises(ValueError):self.read()
    def test_qualification_flag_cannot_substitute_for_finite_state(self):
        self.meta['state_is_finite_QP_not_gap_qualification']=False;self.save()
        with self.assertRaises(ValueError):self.read()
    def test_gap_threshold_cannot_change(self):
        self.meta['gap_tolerance_mm']=2e-7;self.save()
        with self.assertRaises(ValueError):self.read()
    def test_output_cannot_replace_or_contain_prior_state(self):
        for output in (self.state,self.base,self.state/'child'):
            with self.assertRaises(ValueError):self.read(output=output)
    def test_invalid_case_or_level_is_rejected(self):
        for case in (True,8,-1,2.5):
            self.meta['case']=case;self.save()
            with self.assertRaises(ValueError):self.read()
        for level in (True,0,3,1.5):
            with self.assertRaises(ValueError):self.read(level=level)
    def test_boolean_level_metadata_is_not_a_level_number(self):
        self.meta['volume_level']=True;self.save()
        with self.assertRaises(ValueError):self.read()
    def test_state_bytes_unchanged_by_validation(self):
        before={str(f):f.read_bytes() for f in self.base.rglob('*') if f.is_file()};self.read()
        self.assertEqual(before,{str(f):f.read_bytes() for f in self.base.rglob('*') if f.is_file()})
