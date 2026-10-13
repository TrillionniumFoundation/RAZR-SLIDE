"""Concrete path and dimensional checks; no hardware qualification inferred."""
import copy
import json
from pathlib import Path
import unittest
from design_review import cell_load_loop, graph, path, size

ROOT = Path(__file__).resolve().parent


class NodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net = json.loads((ROOT / 'candidate_netlist.json').read_text())

    def test_negative_bypass_is_a_complete_loop_only_if_positive_route_enabled(self):
        on = ['U_A1', 'U_A2', 'U_ARX']
        self.assertFalse(cell_load_loop(self.net, on)['conductive_loop_exists'])
        witness = cell_load_loop(self.net, on, faults=['raw_A_negative_to_USB_ground'])
        self.assertTrue(witness['conductive_loop_exists'])
        self.assertIn('INJECTED:raw_A_negative_to_USB_ground', [e['via'] for e in witness['return_path']])
        self.assertFalse(cell_load_loop(self.net, faults=['raw_A_negative_to_USB_ground'])['conductive_loop_exists'])

    def test_independent_source_cut_survives_one_weld(self):
        self.assertFalse(cell_load_loop(self.net, ['A_PACK_PROTECT'], ['U_A1'], positive='A_TX_P')['conductive_loop_exists'])
        self.assertTrue(cell_load_loop(self.net, ['A_PACK_PROTECT'], ['U_A1', 'U_A2'], positive='A_TX_P')['conductive_loop_exists'])

    def test_receiver_blocks_B_backfeed_until_actual_bypass(self):
        on = ['B_PACK_PROTECT', 'U_B1', 'U_B2', 'U_ARX']
        self.assertIsNone(path(graph(self.net, on), 'B_CELL_P', 'A_TX_P'))
        self.assertIsNotNone(path(graph(self.net, on, welded=['U_ARX']), 'B_CELL_P', 'A_TX_P'))

    def test_three_legacy_PCB_bypasses_still_produce_energy_paths(self):
        cases = [('A', ['A_PACK_PROTECT'], 'raw_A_to_harness', 'A_TX_P'),
                 ('B', ['B_PACK_PROTECT'], 'raw_B_to_harness', 'A_RX_P'),
                 ('B', ['B_PACK_PROTECT', 'U_B1', 'U_B2'], 'system_bus_to_harness', 'A_RX_P')]
        for cabin, on, fault, target in cases:
            with self.subTest(fault=fault):
                w = cell_load_loop(self.net, on, faults=[fault], cabin=cabin, positive=target)
                self.assertTrue(w['conductive_loop_exists'])
                self.assertIn('INJECTED:'+fault, [e['via'] for e in w['forward_path']])

    def test_external_adapter_is_not_a_battery_source(self):
        edges = graph(self.net, ['U_VBUS', 'CHARGER_B'], faults=['unsafe_B_charger_SYS_to_system'])
        w = path(edges, 'USB_VBUS_PORT', 'SYS_B_P')
        self.assertIsNotNone(w)
        self.assertFalse(any(e['via'].startswith('U_A') or e['via'].startswith('U_B') for e in w))
        self.assertIsNone(path(graph(self.net, ['CHARGER_B'], faults=['unsafe_B_charger_SYS_to_system']), 'USB_VBUS_PORT', 'SYS_B_P'))

    def test_unknown_fault_is_rejected(self):
        with self.assertRaises(ValueError):
            graph(self.net, faults=['fictional_safe_short'])

    def test_dedicated_return_open_still_uses_other_common_reference(self):
        on = ['A_PACK_PROTECT', 'U_A1', 'U_A2', 'U_ARX']
        witness = cell_load_loop(self.net, on, faults=['open_H_POWER_A_return'])
        self.assertTrue(witness['conductive_loop_exists'])
        refs = [e['via'] for e in witness['return_path']]
        self.assertNotIn('H_POWER_A.dedicated_return', refs)
        self.assertIn('H_CHARGE_A.dedicated_return', refs)
        # A physically separate positive-side cut can stop this loop while
        # USB/reference stays connected; hardware detection latency remains null.
        on.remove('U_A2')
        self.assertFalse(cell_load_loop(self.net, on, faults=['open_H_POWER_A_return'])['conductive_loop_exists'])

    def test_source_variant_pin_identity_and_data_orientation(self):
        for part in self.net['components']:
            if part.get('part_candidate') == 'TPS259470LRPW':
                self.assertEqual(part['pins']['5']['name'], 'IN')
                self.assertEqual(part['pins']['6']['name'], 'OUT')
                self.assertEqual(part['pins']['3']['name'], 'AUXOFF')
        usb = next(p for p in self.net['components'] if p['ref']=='U_USB2_HOST')
        self.assertEqual(usb['pins']['1']['net'], 'H_USB_DP_HOSTEND')
        self.assertEqual(usb['pins']['5']['net'], 'OEM_HOST_DP_NULL')


class SizingTests(unittest.TestCase):
    def test_missing_product_values_stay_null(self):
        r = size({})
        self.assertTrue(r['incomplete'])
        self.assertTrue(all(v is None for v in r['computed'].values()))
        self.assertFalse(r['manufacturing_go'])

    def test_dimensional_arithmetic_with_synthetic_numbers_only(self):
        r = size({'target_inrush_A':0.1, 'output_capacitance_F':100e-6,
                  'current_limit_A':2, 'load_continuous_A':2, 'A_pack_max_V':4})
        self.assertAlmostEqual(r['computed']['slew_V_per_ms'], 1)
        self.assertAlmostEqual(r['computed']['DVDT_C_pF_screen'], 2000)
        self.assertAlmostEqual(r['computed']['ILM_R_ohm_screen'], 1667)
        self.assertAlmostEqual(r['computed']['capacitor_energy_J'], 0.0008)
        self.assertAlmostEqual(r['computed']['single_eFuse_I2R_W_screen'], 0.18)
        self.assertFalse(r['product_qualified'])

    def test_invalid_negative_nan_infinite_zero_and_boolean_inputs(self):
        for value in [-1, float('nan'), float('inf'), 0, True]:
            with self.subTest(value=value):
                r = size({'current_limit_A':value})
                self.assertIsNone(r['computed']['ILM_R_ohm_screen'])
                self.assertTrue(r['invalid'])

    def test_residual_voltage_is_bounded_by_leakage_equilibrium(self):
        inputs = {'output_capacitance_F':1e-6, 'A_pack_max_V':4,
                  'residual_voltage_limit_V':0.1, 'leakage_max_A':1e-6, 'bleed_R_ohm':100000}
        r = size(inputs)
        self.assertIsNone(r['computed']['bleed_time_s'])
        self.assertTrue(r['invalid'])
        inputs['residual_voltage_limit_V'] = 0.2
        self.assertAlmostEqual(size(inputs)['computed']['bleed_time_s'], 0.3663561646129646)

    def test_actual_product_ranges_are_not_defaulted(self):
        self.assertIsNone(size({})['limits']['TPS_input_range_check'])
        self.assertFalse(size({'A_pack_min_V':2.6,'A_pack_max_V':4})['limits']['TPS_input_range_check'])
        self.assertFalse(size({'load_continuous_A':6})['limits']['TPS_continuous_current_check'])


if __name__ == '__main__':
    unittest.main()
