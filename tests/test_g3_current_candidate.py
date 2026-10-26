"""Current-candidate binding counterexamples; all fixtures are synthetic."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py'
spec = importlib.util.spec_from_file_location('g3_candidate_contract',PATH)
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


class CurrentCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = ['design/product_routing_ep5.json','integration/product_routing_ep5.py']
        payloads = [json.dumps({'schema':'razr-product-routing-ep5-v1','candidate_id':'SYNTHETIC_EP5'}).encode(),b'# synthetic geometry source\n']
        files = {}
        for path,payload in zip(self.paths,payloads):
            p = self.root/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(payload)
            files[path] = hashlib.sha256(payload).hexdigest()
        self.binding = {'files_sha256':files,'artifact_roles':{'routing':self.paths},
            'routing_candidate':{'candidate_id':'SYNTHETIC_EP5',
                'configuration_path':self.paths[0],'configuration_sha256':files[self.paths[0]],
                'generator_path':self.paths[1],'generator_sha256':files[self.paths[1]]}}

    def read(self,root,ref):
        raw = (Path(root)/ref['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['sha256']: raise ValueError('source hash changed')
        return raw

    def call(self): return contract.validate_current_routing_binding(self.binding,self.root,self.read)

    def test_v2_current_binding_is_explicit(self):
        self.assertEqual(self.call()['candidate_id'],'SYNTHETIC_EP5')
        self.assertIn('routing',contract.CURRENT_REQUIRED_ROLES)
        self.assertNotIn('ep4',contract.CURRENT_REQUIRED_ROLES)

    def test_legacy_schema_and_role_stay_readable(self):
        self.assertEqual(contract.PLAN_SCHEMA,'razr-unpowered-motion-qualification-plan-v1')
        self.assertIn('ep4',contract.REQUIRED_ROLES)
        self.assertNotEqual(contract.PLAN_SCHEMA,contract.CURRENT_PLAN_SCHEMA)

    def test_wrong_label_rejected(self):
        self.binding['routing_candidate']['candidate_id'] = 'OTHER'
        with self.assertRaises(ValueError): self.call()

    def test_ep4_substitution_rejected(self):
        self.binding['routing_candidate']['configuration_path'] = 'design/product_routing_ep4.json'
        with self.assertRaises(ValueError): self.call()

    def test_omitted_generator_role_rejected(self):
        self.binding['artifact_roles']['routing'] = self.paths[:1]
        with self.assertRaises(ValueError): self.call()

    def test_sha_inventory_substitution_rejected(self):
        self.binding['routing_candidate']['generator_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.call()

    def test_changed_actual_source_rejected(self):
        (self.root/self.paths[1]).write_text('# changed\n')
        with self.assertRaises(ValueError): self.call()

    def test_role_label_alone_is_insufficient(self):
        del self.binding['routing_candidate']
        with self.assertRaises(ValueError): self.call()


if __name__ == '__main__': unittest.main()
