#!/usr/bin/env python3
"""R79 independent high-precision calculation; does not import R79 primary source."""
import argparse,csv,json,math
from pathlib import Path
import mpmath as mp
mp.mp.dps=90
D=mp.mpf('30');E=mp.mpf('0.05');Y=mp.mpf('55');Z=mp.mpf('9.45');T=mp.mpf('79.75');A=mp.mpf('0.3');L=mp.mpf('70')

def dist(s,q=0):return mp.sqrt((s-Y)**2+(q-Z)**2)
def u(s):return D*mp.asin((dist(s)-E)/D)
def uprime(s):
 dd=dist(s);return (s-Y)/(dd*mp.sqrt(1-((dd-E)/D)**2))
def safe():return Y-mp.sqrt((D-E)**2-Z**2)
def root_start():
 l0=dist(mp.mpf('0'))+E
 f=lambda s:-s*uprime(s)-(l0-u(s))
 sm=mp.findroot(f,(mp.mpf('41'),mp.mpf('44')))
 k=(l0-u(sm))/sm
 return sm,k

def endpoint_root():
 lowend=dist(T)+E
 g=lambda s: -(T-s)*uprime(s)+2*(lowend-u(s))
 s=mp.findroot(g,(mp.mpf('72'),mp.mpf('74')))
 return s,2*(lowend-u(s))/(T-s)**2,g(s)

def start_pair_root():
 l0=dist(0)+E
 gap=lambda s:l0-u(s)
 def kval(s):return A*s-mp.sqrt(A*A*s*s-2*A*gap(s))
 sm=mp.findroot(lambda s:mp.diff(kval,s),(mp.mpf('41'),mp.mpf('43')))
 return sm,kval(sm)

def check_witness(csvpath):
 rows=[]
 with open(csvpath,newline='') as fh:
  for r in csv.DictReader(fh):rows.append({k:(mp.mpf(v) if v and k not in ('NOT_MOTOR_SETPOINT',) else v) for k,v in r.items()})
 max_pose=mp.mpf('0');max_vel=mp.mpf('0');max_acc=mp.mpf('0');min_lower=mp.inf;min_upper=mp.inf
 for i,r in enumerate(rows):
  s=r['s_mm'];val=r['F_free_mm'];v=r['derivative_dF_d_s'];
  max_vel=max(max_vel,abs(v))
  low=dist(s)+E;up=L if s<safe() else u(s)
  if s==T:up=min(up,D*mp.asin((dist(T,mp.mpf('8.2'))-E)/D))
  min_lower=min(min_lower,val-low);min_upper=min(min_upper,up-val)
  if i<len(rows)-1:
   h=rows[i+1]['s_mm']-s;aa=r['second_dF_d_s2_NEXT_INTERVAL'];max_acc=max(max_acc,abs(aa))
   d1=abs(val+v*h+aa*h*h/2-rows[i+1]['F_free_mm'])
   d2=abs(v+aa*h-rows[i+1]['derivative_dF_d_s'])
   max_pose=max(max_pose,d1,d2)
 assert max_pose<mp.mpf('1e-10') and max_vel<=mp.mpf('0.9800000001') and max_acc<=mp.mpf('0.3000000001')
 assert abs(rows[0]['derivative_dF_d_s'])<mp.mpf('1e-10') and abs(rows[-1]['derivative_dF_d_s'])<mp.mpf('1e-10')
 assert min_lower>mp.mpf('0.0035') and min_upper>mp.mpf('0.0035')
 return {'nodes_checked':len(rows),'max_node_recurrence_residual':mp.nstr(max_pose,30),'min_lower_node_clearance_mm':mp.nstr(min_lower,30),'min_upper_node_clearance_mm':mp.nstr(min_upper,30),'zero_start_and_slide_end_slope':True}

def run(csvpath,out):
 sm,k=root_start();em,amin,res=endpoint_root();pm,pk=start_pair_root();nodes=check_witness(csvpath)
 reference={'R78_k':mp.mpf('0.9277021685718772'),'A_end':mp.mpf('0.18798387608105407'),'start_k_pair':mp.mpf('0.9644012635024701')}
 assert abs(reference['R78_k']-k)<mp.mpf('1e-14')
 assert abs(reference['A_end']-amin)<mp.mpf('1e-13')
 assert abs(reference['start_k_pair']-pk)<mp.mpf('1e-12')
 r={'precision_decimal_digits':mp.mp.dps,'standalone_no_R79_import':True,
    'R78_sm_mm':mp.nstr(sm,85),'R78_kstar':mp.nstr(k,85),
    'R79_terminal_critical_s_mm':mp.nstr(em,85),'R79_terminal_acceleration_A_nec':mp.nstr(amin,85),
    'R79_terminal_stationarity_residual':mp.nstr(res,30),
    'R79_start_pair_critical_s_mm':mp.nstr(pm,85),'R79_start_pair_k_nec_A0p3':mp.nstr(pk,85),
    'witness_check':nodes,'new_real_3D_FPC_CAD':False,'manufacturing_go':False}
 Path(out).write_text(json.dumps(r,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
 print('90digit checks PASS; A_terminal=',mp.nstr(amin,22),' k_start=',mp.nstr(pk,22))
 return r

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--csv',required=True);ap.add_argument('--out',required=True);args=ap.parse_args();run(args.csv,args.out)
