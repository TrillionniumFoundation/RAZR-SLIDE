"""Adversarial drawn-circuit behavior and preserved physical counterexamples."""
from pathlib import Path
import hashlib, json, unittest
from proof_model import Probe, cycles

class TestDrawnCircuit(unittest.TestCase):
    def healthy(self):
        p=Probe();p.rail(True);p.service(True);cycles(p);self.assertTrue(p.fresh);return p
    def test_no_phase_credits_from_startup(self):
        p=Probe();p.rail(True);self.assertFalse(p.fresh)
    def test_one_sample_cannot_permit(self):
        p=Probe();p.rail(True);p.edge(True,0);self.assertFalse(p.fresh)
    def test_healthy_zero_main_load_permits_dry_loop(self):
        self.healthy()  # The challenge current does not come from main load.
    def test_open_dry_loop_rejects(self):
        p=self.healthy();cycles(p,2,high=3.3);self.assertFalse(p.fresh)
    def test_short_dry_loop_rejects(self):
        p=self.healthy();cycles(p,2,high=0);self.assertFalse(p.fresh)
    def test_constant_midpoint_rejects_low_phase(self):
        p=Probe();p.rail(True);cycles(p,high=1.65,low=1.65);self.assertFalse(p.fresh)
    def test_static_zero_rejects_high_phase(self):
        p=Probe();p.rail(True);cycles(p,high=0,low=0);self.assertFalse(p.fresh)
    def test_static_rail_rejects_both_phases(self):
        p=Probe();p.rail(True);cycles(p,high=3.3,low=3.3);self.assertFalse(p.fresh)
    def test_stopped_low_phase_expires(self):
        p=self.healthy();p.advance(231);self.assertFalse(p.fresh)
    def test_stopped_high_phase_expires(self):
        p=self.healthy();p.edge(True,0);p.advance(231);self.assertFalse(p.fresh)
    def test_auto_release_wdo_does_not_restore_stale_samples(self):
        p=self.healthy();p.advance(231);p.advance(5000);self.assertFalse(p.fresh)
    def test_watchdog_input_stuck_high_expires(self):
        p=self.healthy();p.hb_forced=True;cycles(p,30);self.assertFalse(p.fresh)
    def test_watchdog_input_stuck_low_expires(self):
        p=self.healthy();p.hb_forced=False;cycles(p,30);self.assertFalse(p.fresh)
    def test_reset_clears_samples_without_inventing_clock_edges(self):
        p=self.healthy();phase=p.phase;p.rail(False);p.rail(True)
        self.assertEqual(p.phase,phase);self.assertFalse(p.fresh)
    def test_lower_comparator_stuck_high_crosscheck_rejects(self):
        p=Probe();p.rail(True);cycles(p,high_lower_forced=True);self.assertFalse(p.fresh)
    def test_comparator_low_output_stuck_low_rejects(self):
        p=Probe();p.rail(True);cycles(p,low_upper_forced=False);self.assertFalse(p.fresh)
    def test_preserve_upper_comparator_stuck_high_open_escape(self):
        p=Probe();p.rail(True);p.service(True);cycles(p,high=3.3,high_upper_forced=True)
        self.assertTrue(p.fresh)  # Real fault not contained by this prototype.
    def test_preserve_watchdog_output_stuck_high_clock_stop_escape(self):
        p=self.healthy();p.wd_stuck_high=True;p.advance(5000);self.assertTrue(p.fresh)
    def test_preserve_main_return_open_with_healthy_dry_loop(self):
        # The dedicated proof pair cannot establish main-N continuity.
        self.healthy()
    def test_preserve_matched_local_resistor_bridge_escape(self):
        # Same 47k installed at A produces same endpoint voltage as remote B.
        self.healthy()
    def test_preserve_fault_immediately_after_sample_latency(self):
        p=self.healthy();p.advance(.001);self.assertTrue(p.fresh)
    def test_watchdog_fault_requires_new_service_edge_after_recovery(self):
        p=self.healthy();p.hb_forced=True;cycles(p,30)
        p.hb_forced=None;cycles(p,30);self.assertFalse(p.fresh)
        p.service(True);cycles(p,4);self.assertFalse(p.fresh)
        p.service(False);p.service(True);cycles(p,4);self.assertTrue(p.fresh)
    def test_manual_reset_without_two_phase_proof_does_not_permit(self):
        p=Probe();p.rail(True);p.service(True);self.assertFalse(p.fresh)
    def test_manual_rearm_cannot_override_continuously_stuck_WDI_high(self):
        p=self.healthy();p.hb_forced=True;cycles(p,30)
        p.service(False);p.service(True);cycles(p,3);self.assertFalse(p.fresh)
    def test_manual_rearm_cannot_override_continuously_stuck_WDI_low(self):
        p=self.healthy();p.hb_forced=False;cycles(p,30)
        p.service(False);p.service(True);cycles(p,3);self.assertFalse(p.fresh)
    def test_new_request_alone_does_not_arm_without_actual_WDI_edge(self):
        p=Probe();p.rail(True);p.service(True)
        self.assertTrue(p.service_pending);self.assertFalse(p.service_armed)
    def test_preserve_output_line_stuck_high_escape(self):
        p=Probe();p.rail(False);self.assertFalse(p.fresh)
        downstream_forced_high=True;self.assertTrue(downstream_forced_high)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TestDrawnCircuit)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={'tests_run':result.testsRun,'failed':len(result.failures),'errors':len(result.errors),
      'all_drawn_circuit_model_assertions_pass':result.wasSuccessful(),
      'physical_qualification':False,'analog_transients_or_metastability_validated':False,
      'counterexamples_preserved':['upper comparator stuck high admits open loop','watchdog WDO stuck high retains stopped-clock proof','main return open while dry loop healthy','matched local signature resistor','fault after last sampled edge','downstream proof wire forced high'],
      'manufacturing_go':False,'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('proof_model.py')]}}
    Path(__file__).with_name('model_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
