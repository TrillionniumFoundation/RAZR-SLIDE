"""DC circuit equations and event-driven hardware-latch logic, never physical qualification.

No TI macro-model, saturation recovery, EMI, sensor-open parasitic or thermal
model is implied. All numerical scenarios are explicitly synthetic fixtures.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib, importlib.util, itertools, json, math, platform, socket

ROOT=Path(__file__).resolve().parent

def finite_nonnegative(value):
 return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and value>=0

def return_split(current_A, branch_resistance_ohm):
 """Two-node DC nodal solve. None branch resistance means physically open.
 Positive supplied current returns from B to A; negative supports signed cases.
 """
 if not isinstance(current_A,(float,int)) or isinstance(current_A,bool) or not math.isfinite(current_A):raise ValueError('current must be finite')
 conductance={}
 for name,r in branch_resistance_ohm.items():
  if r is None:conductance[name]=0.0
  elif not finite_nonnegative(r) or r==0:raise ValueError('resistance must be positive or None(open)')
  else:conductance[name]=1.0/r
 total=math.fsum(conductance.values())
 if total==0:
  return {'closed_return_exists':False,'return_voltage_B_minus_A_V':None,'branch_A':{n:0.0 for n in conductance},'requested_current_A':current_A,'model_current_realizable':current_A==0}
 dv=current_A/total
 currents={n:dv*g for n,g in conductance.items()}
 return {'closed_return_exists':True,'return_voltage_B_minus_A_V':dv,'branch_A':currents,'requested_current_A':current_A,'model_current_realizable':True}

def threshold_interval(healthy_abs_imbalance_A, fault_abs_imbalance_A, error_A, transient_A):
 """A strict, conditionally separating threshold requires lower < upper.
 Empty/unknown supplied bounds never acquire a default threshold.
 """
 if healthy_abs_imbalance_A is None or fault_abs_imbalance_A is None or error_A is None or transient_A is None:
  return {'threshold_exists':None,'lower_exclusive_A':None,'upper_exclusive_A':None,'selected_product_threshold_A':None,'reason':'missing measured bounds'}
 if not healthy_abs_imbalance_A or not fault_abs_imbalance_A or not finite_nonnegative(error_A) or not finite_nonnegative(transient_A):raise ValueError('nonempty finite bounds required')
 if not all(finite_nonnegative(x) for x in healthy_abs_imbalance_A+fault_abs_imbalance_A):raise ValueError('finite nonnegative imbalance required')
 lower=max(healthy_abs_imbalance_A)+error_A+transient_A
 upper=min(fault_abs_imbalance_A)-error_A
 return {'threshold_exists':lower<upper and not math.isclose(lower,upper,rel_tol=1e-12,abs_tol=1e-15),'lower_exclusive_A':lower,'upper_exclusive_A':upper,'selected_product_threshold_A':None,'reason':'conditional synthetic separation only' if lower<upper else 'healthy/fault envelopes overlap'}

def amp_outputs(ip,im,vs=3.3,rs=.01,gain=20,shunt_gain_error=(0.,0.),offset_V=(0.,0.)):
 """Ideal static unsaturated voltages. Output headroom checks are explicit."""
 ref=vs/2
 op=ref+gain*(ip*rs*(1+shunt_gain_error[0])+offset_V[0])
 on=ref+gain*(im*rs*(1+shunt_gain_error[1])+offset_V[1])
 diff=ref+op-on
 return {'P_V':op,'N_V':on,'difference_V':diff,'within_INA240_documented_gain_test_headroom':.05<=min(op,on) and max(op,on)<=vs-.2,'ideal_imbalance_A':ip-im}

@dataclass
class HardwareLatch:
 q:bool=False
 previous_arm:bool=False
 def sample(self,power_good,hi_ok,lo_ok,arm):
  """D=1 PREn=1 /CLR=PG & HI_OK & LO_OK, EN=PG & Q.
  Abstract digital timing only. A powered-down/brownout transition is modeled
  as supervised /CLR; actual supervisor propagation remains unqualified.
  """
  clear_n=bool(power_good and hi_ok and lo_ok)
  edge=bool(arm and not self.previous_arm)
  if not clear_n:self.q=False
  elif edge:self.q=True
  self.previous_arm=bool(arm)
  return {'clear_n':clear_n,'Q':self.q,'U_A2_enable_command':bool(self.q and power_good),'arm_edge':edge}

def phantom_feed(source_V,clamp_drop_V,feed_ohm,bleed_ohm,cap_F,initial_V,time_s):
 """Explicit injected DC clamp path. Neither an OEM clamp nor a USB model."""
 vals=[source_V,clamp_drop_V,feed_ohm,bleed_ohm,cap_F,initial_V,time_s]
 if not all(finite_nonnegative(x) for x in vals) or min(feed_ohm,bleed_ohm,cap_F)<=0 or source_V<clamp_drop_V:raise ValueError('invalid phantom-feed parameters')
 available=source_V-clamp_drop_V
 equilibrium=available*bleed_ohm/(feed_ohm+bleed_ohm)
 tau=cap_F/(1/feed_ohm+1/bleed_ohm)
 v=equilibrium+(initial_V-equilibrium)*math.exp(-time_s/tau)
 return {'equilibrium_V':equilibrium,'tau_s':tau,'voltage_at_time_V':v,'stored_energy_at_equilibrium_J':.5*cap_F*equilibrium**2,'leakage_off_is_zero_energy':False,'actual_OEM_parameters_known':False}

def enabled_low_leakage_voltage(leakage_A,r_pd_ohm):
 if not finite_nonnegative(leakage_A) or not finite_nonnegative(r_pd_ohm) or r_pd_ohm<=0:raise ValueError('invalid leakage/pulldown')
 return leakage_A*r_pd_ohm

def pgood_dc(rail_V,r_pullup,r_pulldown,input_leakage_sink_A):
 """Static resistor divider with total input leakage. No brownout dynamics."""
 if not all(finite_nonnegative(x) for x in [rail_V,r_pullup,r_pulldown,input_leakage_sink_A]) or min(r_pullup,r_pulldown)<=0:raise ValueError('invalid PGOOD DC input')
 resistance=1/(1/r_pullup+1/r_pulldown)
 return {'healthy_high_V':rail_V*r_pulldown/(r_pullup+r_pulldown)-input_leakage_sink_A*resistance,
   'broken_driven_connection_max_V':input_leakage_sink_A*r_pulldown,
   'supervisor_max_pullup_sink_A':rail_V/r_pullup,
   'covers_brownout':False}

def run(output):
 f=json.loads((ROOT/'synthetic_fixture.json').read_text());rows=[]
 for i,rm,ra in itertools.product(f['load_A'],f['main_return_total_ohm_including_shunt'],f['alternate_return_equivalent_ohm']):
  healthy=return_split(i,{'main_N':rm,'alternate_protected_ground':ra})
  open_=return_split(i,{'main_N':None,'alternate_protected_ground':ra})
  hp=amp_outputs(i,healthy['branch_A']['main_N']);fp=amp_outputs(i,0.)
  rows.append({'scope':'SYNTHETIC_ONLY_NO_CHARGE_TRANSFER_BUT_CHARGE_GROUND_PRESENT','load_A':i,'Rmain_total_ohm':rm,'Ralt_eq_ohm':ra,
   'healthy':healthy,'main_return_open':open_,'correct_main_shunt_healthy':hp,'correct_main_shunt_fault':fp,
   'REJECTED_aggregate_ground_shunt_fault_imbalance_A':i-math.fsum(open_['branch_A'].values()),
   'zero_window_healthy_false_trip':i>0 and hp['ideal_imbalance_A']>1e-12,
   'research_0p75A_window_healthy_trip':abs(hp['ideal_imbalance_A'])>.75,
   'research_0p75A_window_fault_trip':abs(fp['ideal_imbalance_A'])>.75})
 healthy=[abs(r['correct_main_shunt_healthy']['ideal_imbalance_A']) for r in rows if r['load_A']>=1.]
 faults=[abs(r['correct_main_shunt_fault']['ideal_imbalance_A']) for r in rows if r['load_A']>=1.]
 # This 0.1 A error and 0.05 A transient allowance are explicit synthetic
 # assumptions, NOT a complete worst-case electronics bound.
 wide=threshold_interval(healthy,faults,.1,.05)
 narrow_i=3.;ns=return_split(narrow_i,{'main_N':.03,'alternate_protected_ground':.2})
 narrow=threshold_interval([narrow_i-ns['branch_A']['main_N']],[narrow_i],.1,.05)
 seq=[('power_up_default_off',False,True,True,False),('supply_stable_no_arm',True,True,True,False),
      ('manual_arm_edge',True,True,True,True),('upper_window_fault_while_arm_held',True,False,True,True),
      ('fault_clears_arm_still_high_no_retry',True,True,True,True),('release_arm',True,True,True,False),
      ('service_rearm_new_edge',True,True,True,True),('lower_window_fault',True,True,False,True),
      ('brownout',False,True,True,False),('supply_recovers_no_arm',True,True,True,False)]
 latch=HardwareLatch();events=[]
 for name,pg,hi,lo,arm in seq:events.append({'event':name,'PGOOD':pg,'HI_OK':hi,'LO_OK':lo,'ARM':arm,**latch.sample(pg,hi,lo,arm)})
 old=ROOT.parent/'power-usb-design-20261013';spec=importlib.util.spec_from_file_location('frozen_power_review',old/'design_review.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 n=json.loads((old/'candidate_netlist.json').read_text())
 old_loop=module.cell_load_loop(n,['A_PACK_PROTECT','U_A1','U_A2','U_ARX'],faults=['open_H_POWER_A_return'])
 cut_loop=module.cell_load_loop(n,['A_PACK_PROTECT','U_A1','U_ARX'],faults=['open_H_POWER_A_return'])
 pcb_faults={x:module.cell_load_loop(n,['A_PACK_PROTECT','B_PACK_PROTECT','U_B1','U_B2'],faults=[x],cabin=cabin,positive=hazard)
  for x,cabin,hazard in [('raw_A_to_harness','A','A_TX_P'),('raw_B_to_harness','B','A_RX_P'),('system_bus_to_harness','B','A_RX_P')]}
 adapter_on=module.path(module.graph(n,['U_VBUS','CHARGER_B'],faults=['unsafe_B_charger_SYS_to_system']),'USB_VBUS_PORT','SYS_B_P')
 adapter_off=module.path(module.graph(n,['CHARGER_B'],faults=['unsafe_B_charger_SYS_to_system']),'USB_VBUS_PORT','SYS_B_P')
 out={'schema':'razr-return-sensing-DC-and-latch-study-r2','host':socket.gethostname(),'platform':platform.platform(),
 'manufacturing_go':False,'physical_hardware_test':False,'SPICE_vendor_model_used':False,'synthetic_only':True,
 'DC_sweep_cases':rows,'wide_load_impedance_threshold':wide,'narrow_example_threshold':narrow,
 'product_threshold':threshold_interval(None,None,None,None),'hardware_latch_events':events,
 'exact_old_ground_return_failure':old_loop,'U_A2_cut_removes_A_intended_forward_path':cut_loop,
 'three_unclosed_PCB_bypasses':pcb_faults,
 'VBUS_own_cut_graph_screen':{'unsafe_adapter_with_battery_off_route':adapter_on,'same_intended_route_with_U_VBUS_off':adapter_off,'finite_leakage_and_alternate_feeds_not_removed_by_graph':True},
 'phantom_clamp_injected_counterexample':phantom_feed(5.,.3,1000.,100000.,1e-4,0.,1.),
 'leakage_pulldown_arithmetic':{'assumed_logic_Ioff_plus_EN_A':1.01e-5,'research_Rpd_ohm':10000.,'V_EN_at_VDD_zero_V':enabled_low_leakage_voltage(1.01e-5,10000.),'scope':'VDD exactly 0 only; brownout and all analog backfeeds not covered'},
 'PGOOD_static_dc_synthetic':pgood_dc(f['supply_V'],f['PGOOD_pullup_R_ohm'],f['default_low_R_ohm'],1e-5),
 'latency_qualification':{'INA240A1_settling_typical_us':9.6,'OPA333_GBW_typical_kHz':350.,'OPA333_slew_typical_V_per_us':.16,
   'TLV3202_2p7V_100mV_overdrive_15pF_specified_max_ns':55.,'TPS25947_RL100ohm_COUT1uF_2p7V_tDOFF_typical_us':64.44,
   'not_a_total_guaranteed_cutoff_time':True,'whole_chain_worst_s':None,'product_fault_energy_J':None},
 'unclosed_faults':['sensor Kelvin open or short without self test','both sensors stuck at matching outputs','comparator output short HIGH','latch Q/enable driver stuck HIGH','CLEARn short HIGH','eFuse switch welded','raw rail PCB bypass','uncontrolled shared-ground charge currents','EN phantom-feed during brownout','service arm repeated retry or power-cycle without qualified interlock'],
 'source_SHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'build_design.py',ROOT/'synthetic_fixture.json',ROOT/'product_design_inputs.json',old/'design_review.py',old/'candidate_netlist.json']}}
 output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'DC_sweep_cases':len(rows),'healthy_zero_window_false_trips':sum(r['zero_window_healthy_false_trip'] for r in rows),'wide_threshold_exists':wide['threshold_exists'],'narrow_conditional_threshold_exists':narrow['threshold_exists'],'manufacturing_go':False}))

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'simulation_receipt.json');args=parser.parse_args();run(args.output)
