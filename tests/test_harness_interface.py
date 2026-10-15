import copy
import csv
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('harness_under_test', ROOT / 'integration/harness_interface.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)


class NativeHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {s: (h.SOURCE / 'native_pocket_v2/modules' / s / 'native.xml').read_bytes() for s in h.STAGES}
        cls.boards = {s: h.parse_native(p, s) for s, p in cls.payloads.items()}
        with (h.SOURCE / 'harness_terminal_schedule.csv').open(newline='') as f:
            cls.rows = list(csv.DictReader(f))

    def test_real_native_168_pins_and_18_conductors(self):
        self.assertEqual(sum(b['unique_pins'] for b in self.boards.values()), 168)
        self.assertEqual(h.check_harness(self.rows, self.boards)['conductors'], 18)

    def test_distinct_A_B_return_names_are_not_electrical_isolation(self):
        x = h.check_harness(self.rows, self.boards)
        self.assertTrue(x['A_PACK_N_and_B_SYS_N_are_connected_by_scheduled_harness'])
        self.assertIn('B1.J1.2', x['common_main_return_path'])
        self.assertFalse(x['independent_B_battery_implemented'])

    def test_missing_cross_return_is_rejected(self):
        with self.assertRaises(ValueError):
            h.check_harness([r for r in self.rows if r['from'] != 'A2.J2.2'], self.boards)

    def test_crossed_polarity_is_rejected(self):
        rows = copy.deepcopy(self.rows); rows[3]['to'] = 'B1.J1.1'
        with self.assertRaises(ValueError): h.check_harness(rows, self.boards)

    def test_duplicate_conductor_is_rejected(self):
        rows = copy.deepcopy(self.rows); rows[-1] = copy.deepcopy(rows[-2])
        with self.assertRaises(ValueError): h.check_harness(rows, self.boards)

    def test_control_pair_cannot_be_rerouted_to_power_ground(self):
        rows = copy.deepcopy(self.rows); rows[-1]['to'] = 'B2.J2.2'
        with self.assertRaises(ValueError): h.check_harness(rows, self.boards)

    def test_static_wire_schedule_cannot_claim_motion_qualification(self):
        rows = copy.deepcopy(self.rows); rows[0]['motion_qualified'] = 'True'
        with self.assertRaises(ValueError): h.check_harness(rows, self.boards)

    def test_native_eFuse_pin_function_error_rejected(self):
        x = ET.fromstring(self.payloads['A1'])
        n = x.find("./nets/net/node[@ref='U1'][@pin='5']"); n.set('pinfunction', 'OUT')
        with self.assertRaises(ValueError): h.parse_native(ET.tostring(x), 'A1')

    def test_duplicate_native_pin_rejected(self):
        x = ET.fromstring(self.payloads['A1']); net = x.find('./nets/net')
        net.append(copy.deepcopy(net.find('node')))
        with self.assertRaises(ValueError): h.parse_native(ET.tostring(x), 'A1')

    def test_incomplete_four_board_set_is_rejected(self):
        with self.assertRaises(ValueError):
            h.check_harness(self.rows, {s:b for s,b in self.boards.items() if s != 'B2'})
