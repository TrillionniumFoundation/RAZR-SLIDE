"""Prevent unauthorized/offline devices and error text from becoming donor facts."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('read_donor', ROOT / 'tools/read_donor.py')
donor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(donor)


class DonorReadbackTests(unittest.TestCase):
    def test_offline_and_unauthorized_are_not_selected(self):
        with patch.object(donor, 'command') as call:
            self.assertIsNone(donor.select_donor('adb', [('one', 'offline'), ('two', 'unauthorized')], None))
            call.assert_not_called()

    def test_multiple_devices_require_explicit_selection(self):
        with patch.object(donor, 'command', return_value='motorola'):
            with self.assertRaisesRegex(ValueError, 'multiple Motorola'):
                donor.select_donor('adb', [('one', 'device'), ('two', 'device')], None)
            self.assertEqual(donor.select_donor('adb', [('one', 'device'), ('two', 'device')], 'two'), 'two')

    def test_selected_non_motorola_is_rejected(self):
        with patch.object(donor, 'command', return_value='generic'):
            with self.assertRaisesRegex(ValueError, 'does not identify'):
                donor.select_donor('adb', [('one', 'device')], 'one')

    def test_failed_adb_does_not_create_software_identity(self):
        with patch.object(donor.subprocess, 'run') as run:
            run.return_value.returncode = 1
            run.return_value.stdout = 'motorola'
            with self.assertRaisesRegex(RuntimeError, 'no identity inferred'):
                donor.command('adb', ['devices'])

    def test_successful_process_stderr_is_retained_in_capture(self):
        with patch.object(donor.subprocess, 'run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = 'List of devices attached\n'
            run.return_value.stderr = 'SYNTHETIC successful-command daemon notice\n'
            output = donor.command('adb', ['devices', '-l'])
        self.assertIsInstance(output, str)
        with patch.object(donor, 'command', return_value=output):
            result = donor.capture('adb')
        self.assertEqual(result['command_records'][0]['stderr_text'],
                         'SYNTHETIC successful-command daemon notice\n')
        self.assertEqual(result['command_records'][0]['returncode'], 0)

    def test_empty_inventory_keeps_physical_inputs_unknown(self):
        with patch.object(donor, 'command', return_value='List of devices attached\n'):
            result = donor.capture('adb')
        self.assertFalse(result['selected_donor_connected'])
        self.assertIsNone(result['physical_cell_labels'])
        self.assertFalse(result['phone_function_verified'])
        self.assertNotIn('properties', result)

    def mock_connected(self, args, disappear=False):
        if args == ['devices', '-l']:
            self.inventory_reads = getattr(self, 'inventory_reads', 0)+1
            return 'List of devices attached\n' if disappear and self.inventory_reads > 1 else 'List of devices attached\nSYNTHETIC-SERIAL device product:test\n'
        key = args[-1]
        return {'ro.product.brand': 'motorola', 'ro.product.manufacturer': 'Motorola',
                'ro.product.model': 'SYNTHETIC-TEST-MODEL',
                'ro.build.fingerprint': 'SYNTHETIC-TEST-BUILD'}.get(key, '')+'\n'

    def test_complete_read_retains_trace_and_redacts_serial(self):
        with patch.object(donor, 'command', side_effect=lambda adb, args: self.mock_connected(args)):
            result = donor.capture('adb', specimen_id='SYNTHETIC-UNITTEST')
        self.assertTrue(result['software_identity_complete'])
        self.assertEqual(result['schema'], 'razr-donor-readback-v2')
        self.assertTrue(result['design_inputs_unchanged'])
        self.assertEqual(result['specimen_id'], 'SYNTHETIC-UNITTEST')
        self.assertEqual(len(result['command_records']), len(donor.PROPERTIES)+4)
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))
        self.assertEqual(result['selected_serial_sha256'], hashlib.sha256(b'SYNTHETIC-SERIAL').hexdigest())
        self.assertFalse(result['phone_function_verified'])

    def test_device_removed_during_read_is_not_connected(self):
        with patch.object(donor, 'command', side_effect=lambda adb, args: self.mock_connected(args, True)):
            result = donor.capture('adb')
        self.assertFalse(result['selected_donor_connected'])
        self.assertFalse(result['software_identity_complete'])
        self.assertEqual(result['capture_status'], 'incomplete_or_disconnected')

    def test_partial_failure_retains_completed_values_and_raw_error(self):
        def query(adb, args):
            if args[-1] == 'ro.product.board':
                raise donor.AdbCommandError(1, '', 'SYNTHETIC-SERIAL disconnected')
            return self.mock_connected(args)
        with patch.object(donor, 'command', side_effect=query):
            result = donor.capture('adb')
        self.assertEqual(result['properties']['ro.product.model'], 'SYNTHETIC-TEST-MODEL')
        self.assertFalse(result['software_identity_complete'])
        self.assertEqual(result['command_records'][-1]['returncode'], 1)
        self.assertIn('disconnected', result['command_records'][-1]['stderr_text'])
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))

    def test_duplicate_inventory_is_rejected_and_still_redacted(self):
        with patch.object(donor, 'command', return_value='List of devices attached\nSYNTHETIC-SERIAL device\nSYNTHETIC-SERIAL device\n'):
            result = donor.capture('adb')
        self.assertEqual(result['capture_status'], 'capture_error')
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))
        self.assertFalse(result['selected_donor_connected'])

    def test_a_name_containing_motorola_is_not_an_identity(self):
        with patch.object(donor, 'command', return_value='not-motorola-test'):
            self.assertIsNone(donor.select_donor('adb', [('test', 'device')], None))


if __name__ == '__main__':
    unittest.main()
