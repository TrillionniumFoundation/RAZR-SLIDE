from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
src=HERE.parent/'pcb-source-repair-20261013-r4/build_reference_module.py'
s=src.read_text()
def change(old,new):
 global s
 assert old in s,old[:70]
 s=s.replace(old,new,1)
change('import csv, hashlib, json, uuid','import csv, hashlib, json, uuid,sys')
change('ROOT=Path(__file__).resolve().parent','ROOT=Path(sys.argv[1]).resolve();ROOT.mkdir(parents=True,exist_ok=True)\nSTAGE=ROOT.name')
change("'razr-cut-module-r4/'+s","'razr-cut-module-r5/'+STAGE+'/'+s")
change("'DVDT','FLT']","'DVDT','FLT','ISO_LED_P','ISO_LED_N','ISO_LED_A']")
change(" 'R':[(1,'1','passive'),(2,'2','passive')],", " 'PORT2':[(1,'POSITIVE','passive'),(2,'REFERENCE','passive')],\n 'StageSupply2':[(1,'UPSTREAM_STAGE_POWER','power_out'),(2,'PROTECTED_REFERENCE','power_out')],\n 'VOS618A-8X001T':[(1,'A','passive'),(2,'K','passive'),(3,'E','open_emitter'),(4,'C','power_in')],\n 'PMEG3050EP':[(1,'K','passive'),(2,'A','passive')],\n 'SMBJ5.0CA-E3/52':[(1,'TVS1','passive'),(2,'TVS2','passive')],\n 'R':[(1,'1','passive'),(2,'2','passive')],")
a=s.index('COMP=[\n');b=s.index('\ndef pad(',a)
s=s[:a]+'''COMP=[
 ('U1','TPS259470LRPW','TPS259470LRPW',['BENCH_EN',G,None,'FLT',P,O,'DVDT',G,'ILM',None],100,100,'RPW0010A_OWNED_NOMINAL'),
 ('R1','R','ERJ6ENF4702V',['BENCH_EN',G],96,98,'Passive_0805_Vertical_BENCH'),
 ('R2','R','ERJ6ENF2211V',['ILM',G],104,98.5,'Passive_0805_BENCH'),
 ('R3','R','ERJ6ENF1003V',['FLT',P],96,102,'Passive_0805_BENCH'),
 ('C1','C','C2012X7R1H105K125AB',[P,G],100,95,'Passive_0805_BENCH'),
 ('C2','C','C2012X7R1H105K125AB',[O,G],104,104,'Passive_0805_BENCH'),
 ('C3','C','C0805C103J5GACTU',['DVDT',G],104,101.5,'Passive_0805_BENCH'),
 ('C4','C','C2012X7R1H105K125AB',[O,G],104,108,'Passive_0805_BENCH'),
 ('U2','VOS618A-8X001T','VOS618A-8X001T',['ISO_LED_A','ISO_LED_N','BENCH_EN',P],81.625,98,'VOS618A_OWNED_DATASHEET'),
 ('R4','R','ERJ6ENF1501V',['ISO_LED_P','ISO_LED_A'],75,94.5,'Passive_0805_BENCH'),
 ('D1','SMBJ5.0CA-E3/52','SMBJ5.0CA-E3/52',[P,G],104,91,'SMB_OWNED_NOMINAL'),
 ('D2','PMEG3050EP','PMEG3050EP',[O,G],110,100,'SOD128_OWNED_NOMINAL'),
 ('J1','StageSupply2','B2B-PH-K-S(LF)(SN)',[P,G],90,94,'PH2_OWNED_VERTICAL_IN'),
 ('J2','PORT2','B2B-PH-K-S(LF)(SN)',[O,G],110,106,'PH2_OWNED_VERTICAL_OUT'),
 ('J3','PORT2','B2B-PH-K-S(LF)(SN)',['ISO_LED_P','ISO_LED_N'],73,92,'PH2_OWNED_HORIZONTAL'),
 ('TP1','Probe','FLT_HIGH_Z_ISOLATED_INSTRUMENT_ONLY',['FLT'],90,104,'Probe_1p8mm'),
 ('TP2','Probe','REFERENCE_HIGH_Z_ISOLATED_INSTRUMENT_ONLY',[G],90,106,'Probe_1p8mm'),
]
''' +s[b:]
change("drill=' (drill .8)'", "drill=' (drill .75)'")
change('if name.startswith("Probe") else "smd"','if name.startswith("Probe") or part in ["PORT2","StageSupply2"] else "smd"')
change("elif name.startswith('Probe'):s.append",'''elif part=='VOS618A-8X001T':
  for pin,xx,yy in [(1,-3.125,-.635),(2,-3.125,.635),(3,3.125,.635),(4,3.125,-.635)]:s.append(pad(pin,xx,yy,1.25,.5,nets[pin-1]))
 elif part=='SMBJ5.0CA-E3/52':s.extend([pad(1,-2.15,0,2.5,2.3,nets[0]),pad(2,2.15,0,2.5,2.3,nets[1])])
 elif part=='PMEG3050EP':s.extend([pad(1,-2.2,0,1.4,2.1,nets[0]),pad(2,2.2,0,1.4,2.1,nets[1])])
 elif part in ['PORT2','StageSupply2']:
  dx,dy=(0,-2) if name.endswith('_IN') else (0,2) if name.endswith('_OUT') else (2,0)
  s.extend([pad(1,0,0,1.75,1.2,nets[0],'rect',True),pad(2,dx,dy,1.75,1.2,nets[1],'oval',True)])
 elif name.startswith('Probe'):s.append''')
change("route('BENCH_EN',[(99.1,99.3),(98,99.3),(98,97.1),(96,97.1),(90,97.1)])",'''route('BENCH_EN',[(99.1,99.3),(98,99.3),(98,97.1),(96,97.1),(90,97.1),(90,98.635),(84.75,98.635)])
route(P,[(84.75,97.365),(85,95),(90,94)])
route('ISO_LED_P',[(73,92),(73,94.5),(74.1,94.5)])
route('ISO_LED_A',[(75.9,94.5),(76.5,96.5),(78.5,97.365)])
route('ISO_LED_N',[(75,92),(75,99.2),(77,99.2)],.12,'B.Cu');via('ISO_LED_N',77,99.2)
route('ISO_LED_N',[(77,99.2),(78.5,98.635)])
route(P,[(101.85,91),(99.1,91),(99.1,95)],.3)
route(G,[(106.15,91),(108,91)],.3);via(G,108,91);route(G,[(108,91),(108,110)],.3,'B.Cu')
route(O,[(107.8,100),(107.8,106.5),(106,107)],.3)
route(G,[(112.2,100),(113,100)],.3);via(G,113,100);route(G,[(113,100),(113,110),(110,110)],.3,'B.Cu')
route(O,[(103.1,104),(103.1,108)],.3)
route(G,[(104.9,108),(105.6,108)]);via(G,105.6,108);route(G,[(105.6,108),(105.6,110)],.2,'B.Cu')''')
change("[(90,92),(90,99.1),(90,106)]","[(90,92),(90,106)]")
change('(start 85 89) (end 114 113)','(start 71 89) (end 116 113)')
change('SINGLE-CUT BENCH REFERENCE - NOT PHONE PCB','FOUR-STAGE CUT MODULE - UNPOWERED BENCH')
change("'input_V':[2.7,4.4]","'input_V':[3.4,4.4]")
change("'R_ILM_ohm':1690","'R_ILM_ohm':2210")
change('3334/1690','3334/2210')
change("'R_EN_default_off_ohm':10000","'R_EN_default_off_ohm':47000")
change("'circuit_role':'first discharge source cut U_A1 bench reference only'","'circuit_role':STAGE+' independent optically controlled source/receiver cut bench reference'")
s+='''
# Complete per-stage identities; physical network parity is checked natively.
stages={'A1':('A_PACK_P','A_MID_P','A_PACK_N'),'A2':('A_MID_P','A_TX_P','A_PACK_N'),'B1':('A_RX_P','A_RX_MID_P','B_SYS_N'),'B2':('A_RX_MID_P','SYS_B_P','B_SYS_N')}
vin,vout,ref=stages[STAGE]
rename={'PACK_PROTECTED_P':vin,'AFTER_FIRST_CUT_P':vout,'PACK_PROTECTED_N':ref}
for n in ['BENCH_EN','ILM','DVDT','FLT','ISO_LED_P','ISO_LED_N','ISO_LED_A']:rename[n]=STAGE+'_'+n
for f in ROOT.rglob('*'):
 if f.is_file() and f.suffix not in ['.gz','.png']:
  t=f.read_text()
  for old,new in rename.items():t=t.replace(old,new)
  for pin_name in ['FLT','ILM','DVDT']:t=t.replace('(name "'+STAGE+'_'+pin_name+'"','(name "'+pin_name+'"')
  f.write_text(t)
'''
(HERE/'module_template.py').write_text(s)
print('derived owned template from frozen R4',hashlib.sha256(src.read_bytes()).hexdigest())
