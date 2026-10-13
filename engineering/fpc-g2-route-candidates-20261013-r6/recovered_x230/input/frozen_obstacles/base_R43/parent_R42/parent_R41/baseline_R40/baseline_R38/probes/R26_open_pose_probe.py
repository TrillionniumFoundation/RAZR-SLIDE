import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from r26_open_mechanics import *
from r25_dynamic import POSES
from r24_mechanics import r21
from r22_mechanics import to_blocal
A=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
B=cq.importers.importBrep(str(ROOT/'cad'/'R25_B_REWORKED.brep')).val()
for name,s,q in POSES:
 print('\nPOSE',name)
 refs=r21.r17_assembly(P,s,q,0)
 for side in 'LR':
  for shname,sh in [('OPEN_PAWL_PARK',open_pawl(side,False)),('OPEN_GATE_CLOSED',open_gate(side,0)),('OPEN_EAR_RETR',open_carrier_ear(side,0))]:
   glob=to_global(sh,'OPEN',s,q)
   aa=intersection(A,glob);oo=intersection(refs['OLED'],glob);ff=intersection(refs['FPC'],glob)
   if aa>1e-8 or oo>1e-8 or ff>1e-8:print(side,shname,'A',round(aa,6),'OLED',round(oo,6),'FPC',round(ff,6))
