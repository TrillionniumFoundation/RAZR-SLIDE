"""Synthetic unit fixtures only: no output here is a real hardware observation.

Exercise immutable import/readback, version drift, original-source corruption,
wrong specimens and complete terminal inventories in temporary directories.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'integration'))
import product_interfaces as interfaces


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


hardware = module('hardware_evidence', ROOT/'engineering/product-integration-20261018/hardware/import_hardware_evidence.py')
donor = module('hardware_test_donor', ROOT/'tools/read_donor.py')


class HardwareEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'repository'
        (self.root/'design').mkdir(parents=True)
        self.data = json.loads((ROOT/'design/product_interfaces.json').read_text())
        (self.root/'design/product_geometry.json').write_bytes((ROOT/'design/product_geometry.json').read_bytes())
        self.write_config()
        for args in (['init', '-q'], ['add', 'design'],
                     ['-c', 'user.name=Synthetic unit fixture', '-c', 'user.email=fixture@invalid',
                      'commit', '-qm', 'Synthetic design fixture only']):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        self.raw = Path(self.temp.name)/'input'
        self.raw.mkdir()

    def write_config(self):
        (self.root/'design/product_interfaces.json').write_text(json.dumps(self.data))

    def current_binding(self, data=None):
        return hardware.binding(self.root, data or self.data)

    def source(self, name, kind, payload):
        path = self.raw/name
        path.write_bytes(payload.encode() if isinstance(payload, str) else payload)
        return {'id': path.stem, 'kind': kind, 'path': name, 'sha256': interfaces.sha(path),
                'specimen_id': 'SYNTHETIC-UNITTEST'}

    def capture(self):
        def query(adb, args, *, adb_server_port):
            self.assertEqual(adb_server_port, 5037)
            if args == ['devices', '-l']:
                return 'List of devices attached\nSYNTHETIC-TEST-SERIAL device\n'
            return {'ro.product.brand': 'motorola', 'ro.product.manufacturer': 'Motorola',
                    'ro.product.model': 'SYNTHETIC-ADB-MODEL',
                    'ro.build.fingerprint': 'SYNTHETIC-FINGERPRINT'}.get(args[-1], '')+'\n'
        with patch.object(donor, 'command', side_effect=query), patch.object(donor, 'design_identity', return_value=self.current_binding()):
            result = donor.capture('synthetic-adb', root=self.root, specimen_id='SYNTHETIC-UNITTEST')
        return self.source('capture.json', 'device_readback', json.dumps(result))

    def manifest(self, kind, sources):
        return {'schema': 'razr-hardware-import-v1', 'record_type': kind,
                'is_template': False, 'physical_execution_occurred': True,
                'specimen_id': 'SYNTHETIC-UNITTEST', 'recorded_at_utc': '2026-10-19T00:00:00+00:00',
                'measurement_method': 'SYNTHETIC UNIT TEST ONLY',
                'operator_or_instrument': 'unittest fixture, not a physical instrument',
                'design_binding': self.current_binding(), 'observations': sources}

    def identity_manifest(self):
        capture = self.capture()
        label = self.source('labels.txt', 'physical_label', 'SYNTHETIC TEST FIXTURE; not a donor photograph')
        manifest = self.manifest('donor_identity', [capture, label])
        manifest['device_readback_observation'] = 'capture'
        manifest['field_evidence'] = {
            key: {'value': 'synthetic-'+key, 'observation_ids': ['labels'], 'locator': 'synthetic label '+key}
            for key in self.data['donor']}
        manifest['field_evidence']['model'] = {'value': 'SYNTHETIC-ADB-MODEL',
                                              'observation_ids': ['capture'], 'locator': 'properties.ro.product.model'}
        manifest['part_inventory'] = [
            {'part_id': name, 'roles': roles,
             'label': {'value': 'synthetic-'+name, 'observation_ids': ['labels'], 'locator': 'synthetic fixture '+name}}
            for name, roles in [('MAIN', ['mainboard', 'USB_port_board']),
                                ('PANEL', ['display', 'touch', 'COF']), ('A', ['pack_A']), ('B', ['pack_B'])]]
        return manifest

    def execute(self, manifest, name):
        path = self.raw/(name+'.json')
        path.write_text(json.dumps(manifest))
        return hardware.import_manifest(path, self.root/'records'/name, self.root)

    def apply_identity(self, manifest=None):
        result = self.execute(manifest or self.identity_manifest(), 'identity')
        proposed = json.loads((Path(result['output'])/'proposed-config-update.json').read_text())
        self.data['donor'] = proposed['donor']
        self.data['donor_evidence']['identity_record'] = proposed['donor_evidence']['identity_record']
        self.write_config()
        return result

    def test_import_preserves_original_bytes_and_binds_without_promoting_flags(self):
        original = (self.root/'design/product_interfaces.json').read_bytes()
        result = self.execute(self.identity_manifest(), 'identity')
        self.assertEqual((self.root/'design/product_interfaces.json').read_bytes(), original)
        record = json.loads((Path(result['output'])/'record.json').read_text())
        self.assertFalse(record['physical_phone_verified'])
        self.assertFalse(record['summary']['platform_frozen'])
        proposed = json.loads((Path(result['output'])/'proposed-config-update.json').read_text())
        self.data['donor'] = proposed['donor']
        self.data['donor_evidence']['identity_record'] = proposed['donor_evidence']['identity_record']
        self.write_config()
        self.assertTrue(interfaces.donor_identity_bound(self.data, self.root))
        (self.raw/'labels.txt').write_text('changed external input')
        self.assertTrue(interfaces.donor_identity_bound(self.data, self.root))
        (Path(result['output'])/'raw/labels.txt').write_text('corrupted retained evidence')
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))

    def test_changed_design_is_rejected_before_import(self):
        manifest = self.identity_manifest()
        (self.root/'design/product_geometry.json').write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.execute(manifest, 'bad-design')
        self.assertFalse((self.root/'records/bad-design').exists())

    def test_source_commit_must_exist_and_working_input_difference_is_explicit(self):
        manifest = self.identity_manifest()
        manifest['design_binding']['git_commit'] = '0'*40
        with self.assertRaisesRegex(ValueError, 'source commit is missing'):
            self.execute(manifest, 'invented-commit')
        self.data['donor_evidence']['new_observation_note'] = 'synthetic working-tree metadata edit'
        self.write_config()
        actual = self.current_binding()
        self.assertFalse(actual['inputs_match_commit'])
        self.assertNotEqual(actual['files_sha256'], actual['commit_files_sha256'])

    def test_raw_hash_mismatch_and_wrong_specimen_are_rejected(self):
        manifest = self.identity_manifest()
        manifest['observations'][1]['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.execute(manifest, 'bad-hash')
        manifest = self.identity_manifest()
        manifest['observations'][1]['specimen_id'] = 'ANOTHER-SYNTHETIC-SPECIMEN'
        with self.assertRaisesRegex(ValueError, 'specimen'):
            self.execute(manifest, 'wrong-specimen')

    def test_physical_revision_cannot_be_inferred_from_runtime_properties(self):
        manifest = self.identity_manifest()
        manifest['field_evidence']['mainboard_revision']['observation_ids'] = ['capture']
        with self.assertRaisesRegex(ValueError, 'identity evidence'):
            self.execute(manifest, 'software-revision')

    def test_regional_OEM_document_alone_cannot_establish_observed_donor_parts(self):
        manifest = self.identity_manifest()
        catalog = manifest['observations'][1]
        catalog['kind'] = 'manufacturer_document'
        catalog.pop('specimen_id')
        catalog['applicable_skus'] = ['SYNTHETIC-OTHER-REGIONAL-SKU']
        catalog['physical_match_confirmed'] = False
        with self.assertRaisesRegex(ValueError, 'identity evidence'):
            self.execute(manifest, 'regional-catalog-is-not-specimen')

    def test_partial_connected_identity_remains_importable_without_physical_labels(self):
        manifest = self.identity_manifest()
        manifest['observations'] = [manifest['observations'][0]]
        manifest['field_evidence'] = {'model': manifest['field_evidence']['model']}
        manifest['part_inventory'] = []
        result = self.apply_identity(manifest)
        self.assertEqual(result['summary']['known_identity_fields'], 1)
        self.assertEqual(set(result['summary']['unknown_identity_fields']),
                         set(interfaces.DONOR_FIELDS) - {'model'})
        self.assertEqual(result['summary']['physical_parts_with_original_labels'], 0)
        self.assertEqual(len(result['summary']['missing_inventory_roles']), 7)
        self.assertFalse(result['summary']['platform_frozen'])
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))
        self.assertFalse(self.data['architecture_decision']['actual_donor_selected'])

    def test_donor_schema_cannot_drop_unknown_fields_or_add_unreviewed_fields(self):
        for field in interfaces.DONOR_FIELDS:
            data = copy.deepcopy(self.data)
            data['donor'].pop(field)
            with self.subTest(missing=field), self.assertRaisesRegex(ValueError, 'complete schema-owned'):
                interfaces.validate_config(data, self.root)
            self.assertFalse(interfaces.donor_identity_bound(data, self.root))
        for invalid in (None, [], {}, {'model': 'SYNTHETIC-ADB-MODEL'},
                        {**self.data['donor'], 'unreviewed_field': 'synthetic'}):
            data = copy.deepcopy(self.data)
            data['donor'] = invalid
            with self.subTest(donor=invalid), self.assertRaisesRegex(ValueError, 'complete schema-owned'):
                interfaces.validate_config(data, self.root)
            self.assertFalse(interfaces.donor_identity_bound(data, self.root))

    def test_reduced_donor_import_cannot_report_zero_unknown_identities(self):
        # Regression: the old importer used the mutable donor keys as the
        # requirements. Model-only config imported and then bound as complete.
        self.data['donor'] = {'model': None}
        self.write_config()
        manifest = self.identity_manifest()
        with self.assertRaisesRegex(ValueError, 'complete schema-owned'):
            self.execute(manifest, 'reduced-identity')
        self.assertFalse((self.root/'records/reduced-identity').exists())
        # Direct programmatic imports use the same guard as the file entry.
        with self.assertRaisesRegex(ValueError, 'complete schema-owned'):
            hardware.import_identity(manifest, {}, {}, self.data)

    def test_rehashed_matching_record_cannot_bless_deleted_identity_requirements(self):
        self.apply_identity()
        self.assertTrue(interfaces.donor_identity_bound(self.data, self.root))
        reference = self.data['donor_evidence']['identity_record']
        path = self.root/reference['path']
        record = json.loads(path.read_text())
        self.data['donor'].pop('mainboard_revision')
        record['donor'].pop('mainboard_revision')
        record['field_evidence'].pop('mainboard_revision')
        path.write_text(json.dumps(record))
        reference['sha256'] = interfaces.sha(path)
        self.write_config()
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))
        self.data['architecture_decision']['actual_donor_selected'] = True
        with self.assertRaisesRegex(ValueError, 'complete schema-owned'):
            interfaces.validate_config(self.data, self.root)

    def test_full_unknown_inventory_is_valid_but_malformed_values_are_rejected(self):
        self.data['donor'] = dict.fromkeys(interfaces.DONOR_FIELDS)
        interfaces.validate_config(self.data, self.root)
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))
        for value in ('', '  ', 1, True, [], ['valid', '']):
            data = copy.deepcopy(self.data)
            data['donor']['model'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'observed text or null'):
                interfaces.validate_config(data, self.root)
            self.assertFalse(interfaces.donor_identity_bound(data, self.root))

    def test_observed_identity_fields_do_not_turn_OEM_catalog_into_part_labels(self):
        manifest = self.identity_manifest()
        catalog = self.source('catalog.txt', 'manufacturer_document',
                              'SYNTHETIC SERVICE CANDIDATE; no observed specimen part')
        catalog.pop('specimen_id')
        manifest['observations'].append(catalog)
        for part in manifest['part_inventory']:
            part['label']['observation_ids'] = ['catalog']
        with self.assertRaisesRegex(ValueError, 'part label'):
            self.execute(manifest, 'catalog-only-inventory')

    def test_OEM_specs_can_corroborate_observed_labels_and_remain_reference_inputs(self):
        manifest = self.identity_manifest()
        catalog = self.source('catalog.txt', 'manufacturer_document',
                              'SYNTHETIC matching specification; not a physical observation')
        catalog.pop('specimen_id')
        manifest['observations'].append(catalog)
        for key, field in manifest['field_evidence'].items():
            if key != 'model':
                field['observation_ids'] = ['labels', 'catalog']
        for part in manifest['part_inventory']:
            part['label']['observation_ids'] = ['labels', 'catalog']
        reference = {'value': 'synthetic specification', 'locator': 'synthetic catalog section',
                     'observation_ids': ['catalog']}
        sources = {row['id']: row for row in manifest['observations']}
        self.assertTrue(interfaces.observed_field_bound(reference, sources))
        self.assertFalse(interfaces.observed_field_bound(reference, sources, True))
        result = self.apply_identity(manifest)
        self.assertEqual(result['summary']['physical_parts_with_original_labels'], 4)
        self.assertTrue(interfaces.donor_identity_bound(self.data, self.root))
        self.assertFalse(self.data['architecture_decision']['actual_donor_selected'])

    def test_readback_claim_must_match_retained_command_output(self):
        manifest = self.identity_manifest()
        capture = json.loads((self.raw/'capture.json').read_text())
        capture['properties']['ro.product.model'] = 'SYNTHETIC-MODIFIED-CLAIM'
        manifest['observations'][0] = self.source('capture.json', 'device_readback', json.dumps(capture))
        with self.assertRaisesRegex(ValueError, 'connected specimen'):
            self.execute(manifest, 'altered-readback')

    def test_missing_COF_stays_explicit_and_does_not_bind_complete_donor(self):
        manifest = self.identity_manifest()
        manifest['part_inventory'][1]['roles'].remove('COF')
        result = self.apply_identity(manifest)
        self.assertIn('COF', result['summary']['missing_inventory_roles'])
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))

    def test_legacy_v1_is_readable_but_cannot_establish_new_physical_selection(self):
        result = self.apply_identity()
        path = Path(result['output'])/'record.json'
        record = json.loads(path.read_text())
        record['schema'] = 'razr-observed-donor-identity-v1'
        path.write_text(json.dumps(record))
        reference = {'path': path.relative_to(self.root).as_posix(), 'sha256': interfaces.sha(path)}
        self.data['donor_evidence']['identity_record'] = reference
        self.assertIsNotNone(interfaces.evidence_record(reference, record['schema'], self.root))
        self.assertFalse(interfaces.donor_identity_bound(self.data, self.root))

    def terminal_manifest(self):
        self.apply_identity()
        mapping = self.source('pins.csv', 'physical_measurement',
            'net,source_connector,source_pin,sink_connector,sink_pin,observation_ids,locator\n'
            'SYNTHETIC_D0,MAIN:J1,1,PANEL:J1,1,pinlabels,fixture row 1\n'
            'SYNTHETIC_D1,MAIN:J1,2,PANEL:J1,2,pinlabels,fixture row 2\n')
        label = self.source('pinlabels.txt', 'physical_label', 'SYNTHETIC CONNECTOR FIXTURE ONLY')
        manifest = self.manifest('terminal_map', [mapping, label])
        manifest.update(donor_identity_record=self.data['donor_evidence']['identity_record'],
                        interface_id='MAIN_DISPLAY', terminal_csv_observation='pins',
                        connectors={name+':J1': {'part_id': name, 'observed_pins': ['1', '2'],
                                    'label': {'value': name+':J1', 'observation_ids': ['pinlabels'], 'locator': 'synthetic connector '+name}}
                                    for name in ('MAIN', 'PANEL')})
        return manifest

    def apply_terminal(self, manifest):
        result = self.execute(manifest, 'terminals')
        proposed = json.loads((Path(result['output'])/'proposed-config-update.json').read_text())
        row = next(row for row in self.data['interfaces'] if row['id'] == proposed['interface_id'])
        row.update({key: proposed[key] for key in ('actual_pinmap', 'terminal_measurement_record', 'extension_approved')})
        self.write_config()
        return result, row

    def test_terminal_CSV_import_binds_exact_parts_and_complete_pin_inventory(self):
        result, row = self.apply_terminal(self.terminal_manifest())
        self.assertTrue(interfaces.terminal_evidence_bound(row, self.data, self.root))
        self.assertEqual(result['summary']['observed_terminal_rows'], 2)
        self.assertFalse(row['extension_approved'])
        row['actual_pinmap'][0]['sink_pin'] = '2'
        self.assertFalse(interfaces.terminal_evidence_bound(row, self.data, self.root))

    def test_unmapped_observed_pin_is_reported_and_not_physically_complete(self):
        manifest = self.terminal_manifest()
        manifest['connectors']['MAIN:J1']['observed_pins'].append('3')
        result, row = self.apply_terminal(manifest)
        self.assertEqual(result['summary']['unmapped_observed_pins']['MAIN:J1'], ['3'])
        self.assertFalse(interfaces.terminal_evidence_bound(row, self.data, self.root))

    def test_connector_on_unobserved_part_is_rejected(self):
        manifest = self.terminal_manifest()
        manifest['connectors']['MAIN:J1']['part_id'] = 'UNOBSERVED'
        with self.assertRaisesRegex(ValueError, 'observed donor part'):
            self.execute(manifest, 'wrong-part')

    def test_OEM_document_cannot_alone_identify_an_observed_connector(self):
        manifest = self.terminal_manifest()
        manifest['observations'][1]['kind'] = 'manufacturer_document'
        manifest['observations'][1].pop('specimen_id')
        with self.assertRaisesRegex(ValueError, 'connector label'):
            self.execute(manifest, 'catalog-only-connectors')

    def test_OEM_pin_table_requires_observed_terminal_evidence(self):
        manifest = self.terminal_manifest()
        catalog = self.source('catalog.txt', 'manufacturer_document',
                              'SYNTHETIC OEM pin table; not a physical mapping')
        catalog.pop('specimen_id')
        manifest['observations'].append(catalog)
        payload = (self.raw/'pins.csv').read_text().replace(',pinlabels,', ',catalog,')
        manifest['observations'][0] = self.source('pins.csv', 'physical_measurement', payload)
        with self.assertRaisesRegex(ValueError, 'physical row'):
            self.execute(manifest, 'catalog-only-terminal-rows')

    def test_cross_role_pin_cannot_acquire_two_different_nets(self):
        rows = [{'net': net, 'source_connector': a, 'source_pin': '1', 'sink_connector': b, 'sink_pin': '1',
                 'identity_kind': 'observed_physical_terminal', 'evidence': 'synthetic fixture'}
                for net, a, b in [('P', 'J1', 'J2'), ('N', 'J2', 'J3')]]
        with self.assertRaisesRegex(ValueError, 'contradictory'):
            interfaces.validate_pinmap(rows)

    def phone_manifest(self):
        self.apply_identity()
        capture = self.capture()
        table = self.source('phone.csv', 'instrument_log',
            'time_s,phase,function,reported_outcome,metric,value,unit,observation_ids,locator\n'
            '0,baseline,display,observed_ok,,,,video,frame 0\n'
            '2,OPEN,usb,observed_failure,enumerations,0,count,video,frame 2\n')
        video = self.source('video.txt', 'operator_observation', 'SYNTHETIC VIDEO PLACEHOLDER; unit fixture only')
        manifest = self.manifest('phone_function', [capture, table, video])
        manifest.update(donor_identity_record=self.data['donor_evidence']['identity_record'],
                        device_readback_observation='capture', function_csv_observation='phone',
                        timebase_id='SYNTHETIC-BENCH-CLOCK')
        return manifest

    def test_phone_log_retains_failure_and_never_infers_unobserved_continuity(self):
        result = self.execute(self.phone_manifest(), 'phone-session')
        self.assertEqual(result['summary']['reported_failures'], 1)
        self.assertEqual(result['summary']['observed_time_span_s'], 2.)
        self.assertFalse(result['summary']['motion_continuity_verified'])
        self.assertFalse(result['summary']['phone_function_verified'])
        self.assertEqual(result['summary']['functions_recorded'], ['display', 'usb'])

    def test_phone_log_cannot_switch_to_another_donor_with_the_same_model(self):
        manifest = self.phone_manifest()
        capture = json.loads((self.raw/'capture.json').read_text())
        old = capture['selected_serial_sha256']
        capture = json.loads(json.dumps(capture).replace(old, '4'*64))
        manifest['observations'][0] = self.source('capture.json', 'device_readback', json.dumps(capture))
        with self.assertRaisesRegex(ValueError, 'another donor'):
            self.execute(manifest, 'wrong-device-phone')

    def test_dimension_import_normalizes_values_with_units_and_preserves_unknown_function(self):
        table = self.source('sizes.csv', 'physical_measurement',
            'part_id,quantity,value,unit,uncertainty,observation_ids,locator\n'
            'SYNTHETIC-PCB,connector_exit_x,-2.25,mm,0.01,sizes,row 2\n')
        manifest = self.manifest('dimensions', [table])
        manifest.update(coordinate_frame='synthetic PCB XY plane, front component normal +Z', measurement_csv_observation='sizes')
        result = self.execute(manifest, 'dimensions')
        record = json.loads((Path(result['output'])/'record.json').read_text())
        self.assertEqual(record['measurements'][0]['value'], -2.25)
        self.assertFalse(record['summary']['CAD_replaced_or_packing_verified'])
        bad = (self.raw/'sizes.csv').read_text().replace('-2.25', 'NaN')
        manifest['observations'][0] = self.source('sizes.csv', 'physical_measurement', bad)
        with self.assertRaisesRegex(ValueError, 'finite'):
            self.execute(manifest, 'non-finite-dimension')

    def test_contract_ignores_only_observation_pointers_but_detects_routing_change(self):
        original = interfaces.interface_contract_sha256(self.data)
        self.data['donor_evidence']['identity_record'] = {'path': 'record.json', 'sha256': '0'*64}
        self.data['architecture_decision']['actual_donor_selected'] = True
        self.data['interfaces'][0]['actual_pinmap'] = [{'synthetic': 'placeholder'}]
        self.assertEqual(interfaces.interface_contract_sha256(self.data), original)
        self.data['interfaces'][0]['cabin_or_route'] = 'A'
        self.assertNotEqual(interfaces.interface_contract_sha256(self.data), original)


if __name__ == '__main__':
    unittest.main()
