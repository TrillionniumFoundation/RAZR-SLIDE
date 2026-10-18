"""Prevent unauthorized/offline devices and error text from becoming donor facts."""
import importlib.util
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

    def test_empty_inventory_keeps_physical_inputs_unknown(self):
        with patch.object(donor, 'command', return_value='List of devices attached\n'):
            result = donor.capture('adb')
        self.assertFalse(result['selected_donor_connected'])
        self.assertIsNone(result['physical_cell_labels'])
        self.assertFalse(result['phone_function_verified'])
        self.assertNotIn('properties', result)


if __name__ == '__main__':
    unittest.main()
