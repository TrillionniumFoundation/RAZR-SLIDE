"""Explicit board-to-board and isolated-control terminal schedule; bench only."""
from pathlib import Path
import csv,itertools,json
HERE=Path(__file__).resolve().parent
rows=[]
def pair(h,a,b,length):
 for pin,color in [(1,'RED'),(2,'BLACK')]:rows.append({'harness':h,'from':a+'.'+str(pin),'to':b+'.'+str(pin),'wire_family':'Alpha Wire 3050','color':color,'AWG':24,'cut_length_mm_bench':length,'housing_each_board_end':'PHR-2','crimp_each_board_end':'SPH-002T-P0.5S','motion_qualified':False})
pair('H_A_LOCAL','A1.J2','A2.J1',100)
pair('H_CROSS','A2.J2','B1.J1',200)
pair('H_B_LOCAL','B1.J2','B2.J1',100)
pair('H_INPUT','ISOLATED_PROTECTED_SUPPLY_BOUNDARY','A1.J1',150)
pair('H_OUTPUT','B2.J2','ISOLATED_LOAD_BOUNDARY',150)
for stage in ['A1','A2','B1','B2']:pair('CTRL_'+stage,'FLOATING_DRIVER_'+stage,'{}.J3'.format(stage),150)
with (HERE/'harness_terminal_schedule.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
nodes=['A_PACK_P','A_MID_P','A_TX_P','A_RX_P','A_RX_MID_P','SYS_B_P']
cuts={'A1':(nodes[0],nodes[1]),'A2':(nodes[1],nodes[2]),'B1':(nodes[3],nodes[4]),'B2':(nodes[4],nodes[5])}
def path(source,target,on=(),weld=(),bridges=()):
 adj={n:[] for n in nodes}
 for stage,(a,b) in cuts.items():
  if stage in on or stage in weld:adj[a].append(b)
  if stage in weld:adj[b].append(a)
 adj['A_TX_P'].append('A_RX_P');adj['A_RX_P'].append('A_TX_P')
 for a,b in bridges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
 queue=[[source]];seen=set()
 while queue:
  p=queue.pop(0);a=p[-1]
  if a==target:return p
  if a in seen:continue
  seen.add(a)
  for b in adj.get(a,[]):queue.append(p+[b])
 return None
tests=[]
for i in range(16):
 on=[s for j,s in enumerate(cuts) if i&(1<<j)]
 p=path('A_PACK_P','SYS_B_P',on=on);assert bool(p)==(len(on)==4)
 tests.append({'on':on,'ideal_forward_path':p})
counter=[
 {'fault':'both_A_source_cuts_welded','path':path('A_PACK_P','A_TX_P',weld=['A1','A2']),'harness_energized_while_receivers_off':True},
 {'fault':'both_B_receiver_cuts_welded','path':path('SYS_B_P','A_RX_P',weld=['B1','B2']),'remote_bus_can_energize_harness':True},
 {'fault':'protected_input_to_harness_cross_board_bridge','path':path('A_PACK_P','A_TX_P',bridges=[('A_PACK_P','A_TX_P')]),'physically_excluded':False},
 {'fault':'system_bus_to_harness_cross_board_bridge','path':path('SYS_B_P','A_RX_P',bridges=[('SYS_B_P','A_RX_P')]),'physically_excluded':False},
]
for c in counter:assert c['path']
result={'scope':'ideal semiconductor weld/bridge path enumeration, not measured isolation or qualification','normal_forward_cases':tests,'counterexamples':counter,'legacy_raw_cell_faults':[{'endpoints':['A_CELL_P','A_TX_P'],'raw_cell_not_on_any_module_but_external_pack_layout_unknown':True,'physical_exclusion_qualified':False},{'endpoints':['B_CELL_P','A_RX_P'],'raw_cell_not_on_any_module_but_external_pack_layout_unknown':True,'physical_exclusion_qualified':False},{'endpoints':['SYS_B_P','A_RX_P'],'physical_exclusion_qualified':False}],'finite_leakage_IV_not_modeled':True,'reference_ground_parallel_faults_not_qualified':True,'controls_independent_actual_LED_nets':True,'pack_protection_implemented':False,'full_phone_PCB':False,'manufacturing_go':False}
(HERE/'chain_fault_paths.json').write_text(json.dumps(result,indent=2)+'\n')
print('16 ideal forward combinations; 4 live fault paths retained; 18 conductors / 36 ends scheduled')
