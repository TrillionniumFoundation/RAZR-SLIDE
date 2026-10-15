from pathlib import Path
import hashlib,json,unittest
from selftest_model import Circuit,healthy,STATES,EXPECTED

class TestR5(unittest.TestCase):
    def startup(self,**faults):
        c=Circuit();c.faults=faults;c.rail(True,True);c.service(True,True);c.run();return c
    def test_Johnson_state_changes_exactly_one_bit(self):
        for i,a in enumerate(STATES):
            b=STATES[(i+1)%4];self.assertEqual(sum(x!=y for x,y in zip(a,b)),1)
    def test_known_high_injection_requires_upper_output_low(self):
        self.assertEqual(EXPECTED[2],(1,0,0))
        c=healthy();self.assertTrue(any(r['state']==2 and r['sense_V']==3.3 and r['comparator_bits'][1]==0 for r in c.history))
    def test_healthy_four_state_canary(self):healthy()
    def test_no_service_or_old_dc_flag_can_start(self):
        c=Circuit();c.rail(True,True);c.run();self.assertFalse(c.coupon_powered_ideal_forward)
    def test_one_phase_sample_cannot_form_permission(self):
        c=Circuit();c.rail(True,True);c.service(True,True);c.run(1);self.assertFalse(c.qualified)
    def test_upper_stuck_high_blocks_open_loop_escape(self):
        c=self.startup(upper=True,dry_open=True);self.assertFalse(c.qualified)
    def test_upper_stuck_high_blocks_healthy_loop_permission(self):
        self.assertFalse(self.startup(upper=True).qualified)
    def test_upper_stuck_low_blocks_healthy_loop_permission(self):
        self.assertFalse(self.startup(upper=False).qualified)
    def test_all_six_single_comparator_static_faults_rejected(self):
        for key in ['upper','lower','low']:
            for value in [False,True]:
                with self.subTest(key=key,value=value):self.assertFalse(self.startup(**{key:value}).qualified)
    def test_single_comparator_fault_after_enable_revokes(self):
        for key in ['upper','lower','low']:
            for value in [False,True]:
                c=healthy();c.faults[key]=value;c.run(24)
                with self.subTest(key=key,value=value):self.assertFalse(c.coupon_powered_ideal_forward)
    def test_mux_stuck_normal_rejects_selftest(self):self.assertFalse(self.startup(mux='normal').qualified)
    def test_mux_stuck_test_rejects_real_loop_phase(self):self.assertFalse(self.startup(mux='test').qualified)
    def test_test_driver_static_high_or_low_rejected(self):
        for v in [False,True]:self.assertFalse(self.startup(test_drive=v).qualified)
    def test_open_and_short_dry_loop_rejected(self):
        for key in ['dry_open','dry_short']:self.assertFalse(self.startup(**{key:True}).qualified)
    def test_clock_stop_after_enable_expires_both_receivers(self):
        c=healthy();c.advance(1000);self.assertFalse(c.coupon_powered_ideal_forward)
    def test_each_dynamic_link_stuck_high_or_low_after_enable_expires(self):
        for i in [0,1]:
            for v in [False,True]:
                c=healthy();c.faults['link_'+str(i)]=v;c.run(40)
                with self.subTest(i=i,v=v):self.assertFalse(c.coupon_powered_ideal_forward)
    def test_receiver_manual_rearm_cannot_override_stuck_link(self):
        for i in [0,1]:
            for v in [False,True]:
                c=healthy();c.faults['link_'+str(i)]=v;c.run(30)
                c.service(rx=False);c.service(rx=True);c.run(2)
                with self.subTest(i=i,v=v):self.assertFalse(c.coupon_powered_ideal_forward)
    def test_single_final_ON_stuck_high_does_not_bypass_other_cut(self):
        for key in ['on_a_high','on_b_high']:
            c=healthy();c.faults[key]=True;c.faults['dry_open']=True;c.run(40)
            self.assertFalse(c.coupon_powered_ideal_forward)
    def test_single_switch_weld_does_not_bypass_other_cut(self):
        for key in ['switch_a_weld','switch_b_weld']:
            c=healthy();c.faults[key]=True;c.faults['dry_open']=True;c.run(40)
            self.assertFalse(c.coupon_powered_ideal_forward)
    def test_supervisor_loss_clears_without_synthetic_service_edge(self):
        c=healthy();c.rail(False,False);c.rail(True,True);c.run(8)
        self.assertFalse(c.coupon_powered_ideal_forward)
        self.assertTrue(c.tx_service_level and c.rx_service_level)
    def test_TX_WDI_static_cannot_be_rearmed_manually(self):
        for v in [False,True]:
            c=healthy();c.faults['tx_wdi']=v;c.run(30)
            c.service(tx=False);c.service(tx=True);c.run(2)
            self.assertFalse(c.qualified)
    def test_counter_stall_after_enable_cannot_reuse_old_phase_samples(self):
        c=healthy();c.faults['state_stall']=True;c.run(40)
        self.assertFalse(c.qualified);self.assertFalse(c.coupon_powered_ideal_forward)
    def test_one_source_or_receiver_watchdog_stuck_high_still_clock_stop_closes(self):
        for where in ['tx','phase0','rx0']:
            c=healthy()
            if where=='tx':c.txwd.stuck_high=True
            elif where=='phase0':c.phasewd[0].stuck_high=True
            else:c.rxwd[0].stuck_high=True
            c.advance(1000);self.assertFalse(c.coupon_powered_ideal_forward)
    def test_preserve_two_final_ON_stuck_high_escape(self):
        c=Circuit();c.faults={'on_a_high':True,'on_b_high':True};self.assertTrue(c.coupon_powered_ideal_forward)
    def test_preserve_bridge_across_both_cuts_escape(self):
        c=Circuit();c.faults={'physical_bridge_both_cuts':True};self.assertTrue(c.coupon_powered_ideal_forward)
    def test_preserve_upper_and_selftest_valid_latch_double_fault_escape(self):
        c=self.startup(upper=True,valid_test_stuck_high=True,dry_open=True);self.assertTrue(c.qualified)
    def test_preserve_matched_local_signature_and_main_return_open(self):
        c=healthy();c.faults={'main_return_open':True,'matched_local_signature':True};c.run(8)
        self.assertTrue(c.qualified)
    def test_preserve_post_sample_detection_latency(self):
        c=healthy();c.faults['upper']=True;c.advance(.001);self.assertTrue(c.receiver_enabled)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TestR5)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    p=Path(__file__).parent;c=healthy()
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
      'assertions_pass':result.wasSuccessful(),'healthy_trace':c.history,
      'model_is_SPICE_or_physical_qualification':False,'analog_settling_or_hold_proven':False,
      'counterexamples_preserved':['two final ON nets forced high','physical bridge across both cuts','upper comparator plus test-valid latch simultaneous stuck-high','main return open or signature moved locally','fault immediately after sample','common source corruption'],
      'manufacturing_go':False,
      'source_sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['selftest_model.py','test_selftest_model.py']}}
    (p/'model_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
