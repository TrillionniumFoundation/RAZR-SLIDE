"""Prevent unauthorized/offline devices and error text from becoming donor facts."""
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('read_donor', ROOT / 'tools/read_donor.py')
donor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(donor)
from product_interfaces import readback_trace_consistent


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
        with patch.object(donor, 'command', side_effect=lambda adb, args, **kwargs: self.mock_connected(args)):
            result = donor.capture('adb', specimen_id='SYNTHETIC-UNITTEST')
        self.assertTrue(result['software_identity_complete'])
        self.assertEqual(result['schema'], 'razr-donor-readback-v2')
        self.assertTrue(result['design_inputs_unchanged'])
        self.assertEqual(result['specimen_id'], 'SYNTHETIC-UNITTEST')
        self.assertEqual(len(result['command_records']), len(donor.PROPERTIES)+4)
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))
        self.assertEqual(result['selected_serial_sha256'], hashlib.sha256(b'SYNTHETIC-SERIAL').hexdigest())
        self.assertFalse(result['phone_function_verified'])
        self.assertIsNone(result['adb_transport']['selected_transport_id_unchanged'])
        self.assertTrue(readback_trace_consistent(result))

    def test_device_removed_during_read_is_not_connected(self):
        with patch.object(donor, 'command', side_effect=lambda adb, args, **kwargs: self.mock_connected(args, True)):
            result = donor.capture('adb')
        self.assertFalse(result['selected_donor_connected'])
        self.assertFalse(result['software_identity_complete'])
        self.assertEqual(result['capture_status'], 'incomplete_or_disconnected')

    def test_partial_failure_retains_completed_values_and_raw_error(self):
        def query(adb, args, **kwargs):
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

    def test_explicit_port_reaches_every_subprocess_and_keeps_v2_importable(self):
        """Regression for the real 5037-empty / 5061-connected donor selection bug."""
        prefix = ['-H', '127.0.0.1', '-P', '5061']
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'SYNTHETIC-adb'
            content = b'SYNTHETIC TEST EXECUTABLE; never executed\n'
            executable.write_bytes(content)
            executable.chmod(0o700)

            def process(argv, **kwargs):
                self.assertEqual(argv[0], str(executable))
                self.assertEqual(argv[1:5], prefix)
                args = argv[5:]
                self.assertTrue(args == ['devices', '-l'] or args[2:4] == ['shell', 'getprop'])
                output = self.mock_connected(args).replace('product:test', 'product:test transport_id:7')
                return subprocess.CompletedProcess(argv, 0, output,
                    'SYNTHETIC-SERIAL successful read diagnostic\n')

            with patch.object(donor, 'design_identity', return_value={'synthetic_binding': True}), \
                 patch.object(donor.subprocess, 'run', side_effect=process) as calls:
                result = donor.capture(str(executable), adb_server_port=5061)
            self.assertEqual(calls.call_count, len(donor.PROPERTIES)+4)
            self.assertEqual(result['adb_transport']['adb_executable_path'], str(executable))
            self.assertEqual(result['adb_transport']['adb_executable_sha256'], hashlib.sha256(content).hexdigest())
        self.assertTrue(result['software_identity_complete'])
        self.assertTrue(result['adb_transport']['selected_transport_id_unchanged'])
        self.assertEqual(result['adb_transport']['selected_transport_id_before'], '7')
        self.assertEqual(result['adb_transport']['selected_transport_id_after'], '7')
        self.assertTrue(all(row['adb_global_args'] == prefix for row in result['command_records']))
        self.assertTrue(all('successful read diagnostic' in row['stderr_text'] for row in result['command_records']))
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))
        self.assertTrue(readback_trace_consistent(result))
        self.assertFalse(result['phone_function_verified'])
        self.assertFalse(result['physical_module_identified'])
        self.assertIsNone(result['connector_pinmap'])

    def test_default_port_remains_5037_on_the_local_host(self):
        with patch.object(donor, 'design_identity', return_value={'synthetic_binding': True}), \
             patch.object(donor.subprocess, 'run', return_value=subprocess.CompletedProcess(
                 [], 0, 'List of devices attached\n', '')) as calls:
            result = donor.capture('SYNTHETIC-adb')
        self.assertEqual(calls.call_args.args[0],
                         ['SYNTHETIC-adb', '-H', '127.0.0.1', '-P', '5037', 'devices', '-l'])
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result['adb_transport']['server_port'], 5037)
        self.assertEqual(result['capture_status'], 'no_authorized_motorola')

    def test_same_serial_with_changed_transport_is_not_a_complete_capture(self):
        def query(adb, args, **kwargs):
            output = self.mock_connected(args)
            if args == ['devices', '-l']:
                identity = '7' if self.inventory_reads == 1 else '8'
                output = output.replace('product:test', 'product:test transport_id:'+identity)
            return output
        with patch.object(donor, 'command', side_effect=query):
            result = donor.capture('SYNTHETIC-adb', adb_server_port=5061)
        self.assertTrue(result['selected_donor_connected'])
        self.assertFalse(result['software_identity_complete'])
        self.assertFalse(result['adb_transport']['selected_transport_id_unchanged'])
        self.assertEqual(result['capture_status'], 'transport_changed_during_capture')
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))

    def test_timeout_preserves_and_redacts_partial_output(self):
        error = subprocess.TimeoutExpired(['SYNTHETIC-adb'], 15,
            output=b'List of devices attached\nSYNTHETIC-SERIAL device transport_id:7\n',
            stderr=b'SYNTHETIC-SERIAL partial timeout diagnostic\n')
        with patch.object(donor, 'design_identity', return_value={'synthetic_binding': True}), \
             patch.object(donor.subprocess, 'run', side_effect=error):
            result = donor.capture('SYNTHETIC-adb', adb_server_port=5061)
        row = result['command_records'][0]
        self.assertIsNone(row['returncode'])
        self.assertTrue(row['timed_out'])
        self.assertIn('transport_id:7', row['stdout_text'])
        self.assertIn('partial timeout diagnostic', row['stderr_text'])
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(result))
        self.assertFalse(result['software_identity_complete'])

    def test_cli_forwards_explicit_server_port(self):
        result = {'schema': 'SYNTHETIC-UNITTEST', 'selected_donor_connected': False,
                  'software_identity_complete': False, 'design_inputs_unchanged': True}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'SYNTHETIC-report.json'
            argv = ['read_donor.py', '--adb', 'SYNTHETIC-adb',
                    '--adb-server-port', '5061', '--output', str(output)]
            with patch.object(donor.sys, 'argv', argv), patch.object(donor.sys, 'stdout', io.StringIO()), \
                 patch.object(donor, 'capture', return_value=result) as capture:
                with self.assertRaises(SystemExit) as exited:
                    donor.main()
            self.assertEqual(exited.exception.code, 2)
            self.assertEqual(capture.call_args.kwargs['adb_server_port'], 5061)
            self.assertEqual(json.loads(output.read_text()), result)

    def test_invalid_server_port_is_rejected_before_capture(self):
        for port in ('0', '65536', '-1', '5061x'):
            with self.subTest(port=port), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'SYNTHETIC-report.json'
                argv = ['read_donor.py', '--adb', 'SYNTHETIC-adb',
                        '--adb-server-port', port, '--output', str(output)]
                with patch.object(donor.sys, 'argv', argv), patch.object(donor.sys, 'stderr', io.StringIO()), \
                     patch.object(donor, 'capture') as capture:
                    with self.assertRaises(SystemExit) as exited:
                        donor.main()
                self.assertEqual(exited.exception.code, 2)
                capture.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
