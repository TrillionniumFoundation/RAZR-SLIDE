import time
from r24_integration import *
t=time.time()
base=integrate_b_shell()['R23_b']
print('r23',round(time.time()-t,2),base.Volume(),flush=True)
b=base
for port in ('STOW','OPEN'):
 for side in 'LR':
  cut=shell_key_sweep(port,side)
  print('key',port,side,'bbox',cut.Volume(),flush=True)
  st=time.time();b=b.cut(cut).clean()
  print('time',round(time.time()-st,3),'solids',len(b.Solids()),'valid',b.isValid(),flush=True)
 for name,cut in module_motion_sweeps(port).items():
  st=time.time();print('START',port,name,'vol',cut.Volume(),flush=True)
  b=b.cut(cut).clean()
  print('DONE',round(time.time()-st,3),'solids',len(b.Solids()),'valid',b.isValid(),flush=True)
print('TOTAL',round(time.time()-t,3))
