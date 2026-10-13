#!/usr/bin/env python3
"""R79 conditional scalar acceleration gate. NO physical FPC/CAD or manufacturing claims.

DO NOT interpret mechanical-travel derivatives as mm/s or mm/s². Frozen R78:
L=70 mm, R=15 mm, E=0.05 mm, s in [0,79.75], q in [0,8.2],
Y=55, Z=9.45, robust bounds l=d+E, u=30 asin((d-E)/30) after
s_safe, else u=L. Acceleration and velocity are relative to *path coordinate*.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from scipy.optimize import brentq,linprog,minimize_scalar
from scipy.sparse import lil_matrix

Y=55.0;Z=9.45;E=0.05;R=15.0;D=2*R;T=79.75;Q=8.2;L=70.0
A_DEMO=0.30; K_DEMO=0.98; MARGIN=0.004; NSEG=800
PARENT_SHA={
 'R78':'7f6cc2be3f0bd08879b39db48ef85b292a43b344947b932ea2aeb21512f7ea52',
 'R77':'43a61e1afd43d075d35638dcb683eefe1682a3cdae65f916e1409c44ae3abee2',
 'R76':'d3205dbabc1c72adfbbac63948b9cb20285e0bf52e07dd184b45268f628e397e'
}

def sha(path):
 h=hashlib.sha256();f=Path(path).open('rb')
 with f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def parent_check(paths:dict):
 rv={}
 for key in ('R78','R77','R76'):
  p=Path(paths[key]);actual=sha(p)
  if actual!=PARENT_SHA[key]:raise ValueError(f'{key} original source SHA mismatch {actual}')
  with ZipFile(p) as z:
   if z.testzip() is not None:raise ValueError(f'{key} archive CRC failed')
   names=z.namelist();expected={'R78':25,'R77':21,'R76':19}[key]
   if len(names)!=expected or len(set(names))!=expected:raise ValueError(f'{key} membership incorrect')
   if key=='R78':
    r=json.loads(z.read('results/R78_results.json'))
    if (r['manufacturing_go'] is not False or r['CAD_modify_go'] is not False or
        abs(r['exact_optimal_robust_scalar_rate_mm_FPC_per_mm_mechanical']-0.9277021685718772)>1e-12):
     raise ValueError('R78 parent gate altered')
   rv[key]={'sha256':actual,'members':len(names),'CRC':True,'role':('direct mathematical parent' if key=='R78' else 'read-only historical mathematical ancestor')}
 return rv

def d(s,q=0.0):return math.hypot(s-Y,q-Z)

def gate():return Y-math.sqrt((D-E)**2-Z**2)

def upper(s,q=0.0):
 c=d(s,q)-E
 if not 0<=c<=D:raise ValueError(f'short arc chord domain {c}')
 return D*math.asin(c/D)

def lower(s,q=0.0):return d(s,q)+E

def short_upper_second_bound(s0,s1):
 # Conservative analytic interval enclosure of |U_E''| over a slide segment.
 # d(s) convex; bound dmin via projection of Y into [s0,s1].
 dmin=d(min(max(Y,s0),s1));dmax=max(d(s0),d(s1))
 gamma=math.sqrt(1-((dmax-E)/D)**2)
 if gamma<=0:raise ValueError('unqualified short arc')
 xmax=max(abs(s0-Y),abs(s1-Y))
 return Z**2/(dmin**3*gamma)+(xmax**2)*(dmax-E)/(D**2*dmin**2*gamma**3)

def robust_bounds(t):
 if t<T:
  return lower(t),(L if t<gate() else upper(t))
 if t==T:return lower(T),min(upper(T),upper(T,Q))
 if T<t<=T+Q:return lower(T,t-T),upper(T,t-T)
 raise ValueError('range')

def up_prime(s):
 x=s-Y;ds=d(s);gamma=math.sqrt(1-((ds-E)/D)**2)
 return x/(ds*gamma)

def up_second(s):
 ds=d(s);x=s-Y;g=math.sqrt(1-((ds-E)/D)**2)
 return Z**2/(ds**3*g)+(x**2)*(ds-E)/(D**2*ds**2*g**3)

def r78_stationary():
 start=lower(0)
 def f(s):return -s*up_prime(s)-(start-upper(s))
 sm=brentq(f,gate()+1e-8,Y,xtol=1e-13)
 k=(start-upper(sm))/sm
 return sm,k

def endpoint_minimum_acceleration():
 # Exact continuum necessary max for slide-end rest:
 # F(T)>=l(T), F(s)<=U(s); with F'(T)=0, |F''|<=A,
 # F(T)-F(s)<=A*(T-s)^2/2, giving A>=2*(l(T)-U(s))/(T-s)^2.
 # Unique positive maximum stationary point on s in (Y,T), since
 # H(s)=-(T-s)U'(s)+2(l(T)-U(s)) has H'<0 for s>Y.
 lt=lower(T)
 def stationarity(s):return -(T-s)*up_prime(s)+2*(lt-upper(s))
 root=brentq(stationarity,Y,T-1e-6,xtol=1e-13)
 abound=2*(lt-upper(root))/(T-root)**2
 assert stationarity(Y)>0 and stationarity(T-1e-6)<0 and abound>0
 return {'critical_s_mm':root,'critical_u_mm':upper(root),'terminal_lower_mm':lt,
         'minimal_A_necessary_mm_per_mm2':abound,'stationarity_residual':stationarity(root),
         'proof':'At t=T, Fdot_travel=0 and F(T)>=l(T). For any s<T, F(s)<=u(s), |Fddot_travel|<=A gives F(T)-F(s)<= A(T-s)^2/2; maximize ratio over s>Y. Unique root by strictly negative Hprime for s>Y.',
         'not_physical_time_acceleration':True}

def start_rate_lower(acc):
 # Rest at s=0 and velocity cap k; maximum reduction after s:
 # if k/A <= s: k*s-k*k/(2A); else .5*A*s*s.
 if acc<=0:raise ValueError('A>0')
 def kp(s):
  gap=lower(0)-upper(s)
  if gap<=0:return 0.0
  if gap>acc*s*s/2:return math.inf
  return acc*s-math.sqrt(max(0,acc*acc*s*s-2*acc*gap))
 q=minimize_scalar(lambda s:-kp(s),bounds=(gate()+1e-6,Y),method='bounded',options={'xatol':1e-11})
 # crosscheck with sampled search as solver not formal global optimizer.
 points=np.linspace(gate()+1e-6,Y,12001)
 g=max((kp(float(s)),float(s)) for s in points)
 assert kp(float(q.x))+1e-8>=g[0]
 return {'assumed_A':acc,'s_critical_mm':float(q.x),'minimum_k_pair_mm_per_mm':kp(float(q.x)),
   'R78_kstar_strictly_infeasible_for_finite_A_if_Fprime_start_zero':True,
   'scope':'necessary two-pose scalar condition; not a sufficient full-motion rate'}

def grid():
 x=np.r_[np.linspace(0,T,NSEG+1),gate(),Y,T-1.0]
 sm,_=r78_stationary();x=np.unique(np.sort(np.r_[x,sm,2*Y-sm]))
 assert x[0]==0 and x[-1]==T and min(np.diff(x))>1e-7
 return x

def solve_piecewise(acc=A_DEMO,k=K_DEMO,margin=MARGIN):
 x=grid();n=len(x);h=np.diff(x)
 M=lil_matrix((2*(n-1),3*n-1)); rhs=np.zeros(2*(n-1))
 for i,step in enumerate(h):
  M[2*i,i]=-1;M[2*i,i+1]=1;M[2*i,n+i]=-step;M[2*i,2*n+i]=-(step**2)/2
  M[2*i+1,n+i]=-1;M[2*i+1,n+i+1]=1;M[2*i+1,2*n+i]=-step
 limits=[]
 for s in x:
  lo,hi=robust_bounds(float(s)); limits.append((lo+margin,hi-margin))
 limits.extend([(-k,k)]*n);limits.extend([(-acc,acc)]*(n-1));limits[n]=(0.,0.);limits[2*n-1]=(0.,0.)
 res=linprog(np.zeros(3*n-1),A_eq=M.tocsr(),b_eq=rhs,bounds=limits,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
 if not res.success:raise RuntimeError('NOT_FEASIBLE_AT_ASSUMED_K_A: '+res.message)
 f,v,a=res.x[:n],res.x[n:2*n],res.x[2*n:]
 eqres=np.max(np.abs(M.tocsr().dot(res.x)-rhs));assert eqres<1e-8
 assert abs(v[0])<1e-9 and abs(v[-1])<1e-9
 assert max(abs(v))<=k+1e-8 and max(abs(a))<=acc+1e-8
 return x,f,v,a,{'LP_status':'feasible only, not minimal rate proof','nodes':n,'segments':n-1,'max_linear_equality_residual':float(eqres),'maximum_abs_v':float(max(abs(v))),'maximum_abs_a':float(max(abs(a)))}

def certify(x,f,v,a,acc=A_DEMO,k=K_DEMO):
 # Entire real-valued slide interval certification via a general derivative bound
 # for quadratic F and analytic l,u. This is *interval conservative*; no 'N grid passed' shortcut.
 minlo=float('inf');minhi=float('inf');worst=None;max_drop=0
 for i in range(len(a)):
  s0=float(x[i]);s1=float(x[i+1]);h=s1-s0
  lower_end=[f[j]-lower(float(x[j])) for j in (i,i+1)]
  # l''=Z²/d³ <= 1/Z, F''=a, so |(F-l)''| <= A+1/Z.
  drop_lo=(acc+1/Z)*h*h/8
  cert_lo=min(lower_end)-drop_lo
  # upper jumps from 70 to forced-short at the mode gate; use the *smaller*
  # actual short-arc upper at the right endpoint, a conservative pre-gate bound.
  up_end=[]
  for j in (i,i+1):
   xx=float(x[j]);up_end.append(robust_bounds(xx)[1]-f[j])
  if s0<gate()-1e-11:
   if s1>gate()+1e-9:raise AssertionError('grid crosses discontinuous gate')
   Udd=0.0
  else:Udd=short_upper_second_bound(s0,s1)
  drop_hi=(acc+Udd)*h*h/8
  cert_hi=min(up_end)-drop_hi
  if cert_lo<minlo:minlo=cert_lo
  if cert_hi<minhi:minhi=cert_hi;worst=(s0,s1,Udd,drop_hi,min(up_end))
  max_drop=max(max_drop,drop_hi)
 if not(minlo>0 and minhi>0):raise AssertionError(f'NO_CONTINUUM_CERTIFICATE: {minlo} {minhi}, worst={worst}')
 # Dock: F stays constant and d(T,q) strictly decreases on q in [0,8.2] < Z,
 # so lower maximized at q=0, short upper minimized at q=8.2.
 fend=float(f[-1]);dock_lo=fend-lower(T);dock_hi=upper(T,Q)-fend
 if not(dock_lo>0 and dock_hi>0):raise AssertionError('DOCK_FAIL')
 return {'continuum_slide_LOWER_min_certified_mm':float(minlo),'continuum_slide_UPPER_min_certified_mm':float(minhi),
  'dock_lower_margin_mm':dock_lo,'dock_upper_margin_mm':dock_hi,
  'largest_conservative_curvature_drop_mm':float(max_drop),'worst_upper_interval':worst,
  'method':'For twice-differentiable gap g, g(t)>=min(g_endpoints)-sup|g_second|*h²/8 on every segment; bound d_second<=1/Z and analytic upper_second via enclosing dmin,dmax; handle safe_mode discontinuity conservatively; dock monotonicity.'}

def independent_grid_check(x,f,v,a,n=50001):
 s=np.linspace(0,T,n);ids=np.searchsorted(x,s,side='right')-1;ids=np.minimum(ids,len(a)-1)
 h=s-x[ids];F=f[ids]+v[ids]*h+.5*a[ids]*h*h
 lo=np.hypot(s-Y,Z)+E
 dval=np.hypot(s-Y,Z)-E
 arc=np.full_like(dval,np.nan)
 mask=s>=gate()
 arc[mask]=D*np.arcsin(dval[mask]/D)
 U=np.where(mask,arc,L)
 U[-1]=min(U[-1],upper(T,Q))
 return {'grid_points':n,'min_lower_margin_mm':float(np.min(F-lo)),
         'min_upper_margin_mm':float(np.min(U-F)),
         'max_abs_slope_grid':float(max(abs(v))),'max_abs_acc_segment':float(max(abs(a))),
         'not_substitute_for_continuum_cert':True}

def produce(out:Path,parents:dict):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 pin=parent_check(parents);sm,kstar=r78_stationary();end=endpoint_minimum_acceleration();start=start_rate_lower(A_DEMO)
 x,f,v,a,meta=solve_piecewise();cert=certify(x,f,v,a);scan=independent_grid_check(x,f,v,a)
 assert kstar<start['minimum_k_pair_mm_per_mm']<K_DEMO
 result={'version':'R79-conditional-standstill-acceleration','parent_archives':pin,
  'frozen_R78_kstar':kstar,'frozen_R78_sminus':sm,
  'required_standstill_Fprime_start':0,'required_dock_Fprime_end':0,
  'acceleration_terminal_necessary':end,'acceleration_start_rate_necessary':start,
  'example_software_only':{'hypothetical_acceleration_A_mmF_per_mmTravel_squared':A_DEMO,'hypothetical_rate_K_mmF_per_mmTravel':K_DEMO,
    'margin_requested_per_grid_node_mm':MARGIN,'nonoptimal_existence_witness_only':True,**meta,**cert,**scan},
  'real_time_domain_conversion':'If mechanical progress p(τ), reel free material F(p): F_time_dot=Fprime(p)*p_time_dot; F_time_ddot=Fsecond(p)*p_time_dot²+Fprime(p)*p_time_ddot. No motor/speed/tension qualification.',
  'new_protected_OEM_CAD_modified':False,'real_FPC_copper_3D_OCC_swaps':0,
  'new_real_FPC_USB_power_OLED_supplier_evidence':0,'RFQ_sent':False,
  'candidate_go':False,'CAD_modify_go':False,'manufacturing_go':False}
 (out/'R79_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
 with (out/'R79_C1_piecewise_quadratic_witness.csv').open('w',newline='') as of:
  cw=csv.writer(of);cw.writerow(['s_mm','F_free_mm','derivative_dF_d_s','second_dF_d_s2_NEXT_INTERVAL','lower_mm','upper_mm','NOT_MOTOR_SETPOINT'])
  for i,ss in enumerate(x):
   ll,uu=robust_bounds(float(ss));cw.writerow([f'{ss:.14g}',f'{f[i]:.14g}',f'{v[i]:.14g}',f'{a[i]:.14g}' if i<len(a) else '',f'{ll:.14g}',f'{uu:.14g}',True])
 (out/'R79_motion_interval_certificate.json').write_text(json.dumps(cert,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
 (out/'R79_time_domain_nonqualification.json').write_text(json.dumps({'actual_motor_speed_mmpers':None,'actual_user_slide_velocity_mmpers':None,
  'actual_user_acceleration_mmpers2':None,'actual_FPC_tension_force_N':None,'physical_motor_acceleration_approved':False,
  'mechanical_coordinate_slope_bound_only':K_DEMO,'mechanical_coordinate_curvature_bound_only':A_DEMO,
  'interpretation':result['real_time_domain_conversion']},indent=2)+'\n')
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--r78',required=True);ap.add_argument('--r77',required=True);ap.add_argument('--r76',required=True)
 args=ap.parse_args();r=produce(Path(args.out),{'R78':args.r78,'R77':args.r77,'R76':args.r76})
 print(json.dumps({'end_acc_nec':r['acceleration_terminal_necessary']['minimal_A_necessary_mm_per_mm2'],
                   'start_k_nec_for_A0.3':r['acceleration_start_rate_necessary']['minimum_k_pair_mm_per_mm'],
                   'nonoptimal_feasible_example':r['example_software_only']['continuum_slide_UPPER_min_certified_mm'],
                   'manufacturing_go':r['manufacturing_go']}))
