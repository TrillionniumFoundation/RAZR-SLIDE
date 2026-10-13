"""Concrete per-module terminal partition; no PCB-layout exclusion is assumed."""
from pathlib import Path
import json,copy,itertools,hashlib
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'power-usb-design-20261013/candidate_netlist.json'
original=BASE.read_bytes();n=json.loads(original);n=copy.deepcopy(n)
rx=next(c for c in n['components'] if c['ref']=='U_ARX')
rx['ref']='U_ARX1';rx['pins']['6']['net']='A_RX_MID_P'
rx2=copy.deepcopy(rx);rx2['ref']='U_ARX2';rx2['pins']['5']['net']='A_RX_MID_P';rx2['pins']['6']['net']='SYS_B_P'
for p in rx2['pins'].values():
 if p['net'] is not None and 'U_ARX_' in p['net']:p['net']=p['net'].replace('U_ARX_','U_ARX2_')
n['components'].append(rx2)
n['return_fault_hardware']['reverse_source_cutpoint']='Proposed independent U_ARX1 and U_ARX2 on separate module boards; physical boards not implemented'
n['hazardous_energy_nodes'].append('A_RX_MID_P')
boards=[]
for c in n['components']:
 c['proposed_separate_board']='BOARD_'+c['ref']
 nets=sorted({p['net'] for p in c['pins'].values() if p['net'] is not None})
 boards.append({'board':c['proposed_separate_board'],'component':c['ref'],'terminal_nets':nets,'PCB_layout_implemented':False,'control_supply_and_protection_parts_complete':False})
faults={'raw_A_to_harness':['A_CELL_P','A_TX_P'],'raw_B_to_harness':['B_CELL_P','A_RX_P'],'system_bus_to_harness':['SYS_B_P','A_RX_P']}
rows=[]
for name,pair in faults.items():
 co=[b['board'] for b in boards if all(net in b['terminal_nets'] for net in pair)]
 assert not co
 rows.append({'fault':name,'bridge_endpoints':pair,'eFuse_module_net_coexistence':co,'bridge_still_possible_across_boards_or_shared_harness':True,'physically_excluded_by_verified_layout':False})
n.update(schema='razr-slide-separate-cut-module-proposal-r3',components=n['components'],boards=boards,receiver_redundancy_added=True,physical_fault_domain_implemented=False,manufacturing_go=False)
(HERE/'partitioned_terminal_architecture.json').write_text(json.dumps(n,indent=2)+'\n')
(HERE/'partition_counterexamples.json').write_text(json.dumps({'base_sha256':hashlib.sha256(original).hexdigest(),'rows':rows,'all_legacy_global_bridge_faults_retained':True,'single_board_constraint_is_not_physical_evidence':True,'manufacturing_go':False},indent=2)+'\n')
assert BASE.read_bytes()==original
print(json.dumps({'separate_eFuse_module_domains':len(boards),'receiver_cuts':2,'cross_domain_faults_retained':3,'physical_PCBs_implemented':False,'manufacturing_go':False}))
