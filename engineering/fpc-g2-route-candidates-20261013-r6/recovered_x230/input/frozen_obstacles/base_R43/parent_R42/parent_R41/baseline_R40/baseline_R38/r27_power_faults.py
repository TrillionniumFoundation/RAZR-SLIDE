"""R27 dual-pack exposed-contact conceptual FAULT TREE (NO REAL SCHEMATIC).

Each pack A/B hypothetically has one upstream normally-off isolator in series
with EITHER the main switch or a precharge switch.  A hard solder/PCB bypass
is independent of the switches.  This is an architectural counterexample,
NOT an electrical component qualified for phone battery safety.
"""
from __future__ import annotations
import itertools,json
from pathlib import Path
V=Path(__file__).resolve().parent/'verification'
NAMES=('A_iso_weld','A_main_weld','A_precharge_weld',
       'B_iso_weld','B_main_weld','B_precharge_weld',
       'A_direct_pad_short','B_direct_pad_short','shared_live_bus_to_pad_short')

def evaluate(flags):
    f=dict(zip(NAMES,flags))
    activeA=(f['A_iso_weld'] and (f['A_main_weld'] or f['A_precharge_weld'])) or f['A_direct_pad_short']
    activeB=(f['B_iso_weld'] and (f['B_main_weld'] or f['B_precharge_weld'])) or f['B_direct_pad_short']
    return activeA or activeB or f['shared_live_bus_to_pad_short']

def run(write=True):
    rows=[]
    for bits in itertools.product((False,True),repeat=len(NAMES)):
        rows.append(dict(failed=[NAMES[i] for i,x in enumerate(bits) if x],exposed_pad_can_remain_live=evaluate(bits)))
    danger=[set(x['failed']) for x in rows if x['exposed_pad_can_remain_live']]
    minimal=[]
    for fs in sorted(danger,key=lambda x:(len(x),sorted(x))):
        if not any(pre.issubset(fs) for pre in minimal):minimal.append(fs)
    out=dict(revision='R27 conceptual 2-pack controlled exposure power fault tree, DO NOT fabricate from this',
       model_assumptions=['each pack has separate normally-open upstream isolator',
         'main and precharge branches meet AFTER upstream isolator',
         'hard PCB bypass shorts independent of switches',
         'all pack-bus rails presumed live for worst-case analysis',
         'no real FET, BMS, ESD, fuse, PCB layout or conducted test evidence'],
       enumerated_fault_states=len(rows),dangerous_states=len(danger),
       minimal_cut_sets=[sorted(m) for m in minimal],
       one_fault_dangerous_minimal_cuts=[sorted(m) for m in minimal if len(m)==1],
       zero_fault_live_pad=evaluate((False,)*len(NAMES)),
       selected_material=['TE 2199001-1 may be considered for rated signal only, not main power'],
       main_battery_connector_current_rating_not_verified=True,
       independent_USB2_USB3_CC_pinout_and_SI_not_verified=True,
       true_zero_volt_contact_measurement_missing=True,
       powered_contact_hot_swap_and_battery_reverse_current_unverified=True,
       no_real_hardware_qualifying_results=True,manufacturing_go=False)
    if write:(V/'R27_power_faults.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out
if __name__=='__main__':
 r=run();print('faults',r['enumerated_fault_states'],'danger',r['dangerous_states'],'minimal',r['minimal_cut_sets'])
