from r24_integration import *
import time
a,b,stats=integrate();print('integrate done',stats['B_removed_R23_mm3'],flush=True)
for name,s,q in [('stow',0,0),('early',1.,0),('yh',P.travel/2,0),('predock',P.travel,0),('zmid',P.travel,4.1),('open',P.travel,8.2)]:
 ref=r21.r17_assembly(P,s,q,0);bw=b.translate(cq.Vector(0,s,-P.z_travel+q));print('==',name,flush=True)
 for label,v,u in [('A_B',a,bw),('B_OLED',bw,ref['OLED']),('A_OLED',a,ref['OLED']),('B_FPC',bw,ref['FPC'])]:
  t=time.time();
  try:vv=intersection(v,u)
  except Exception as e:print(label,'ERROR',str(e));continue
  print(label,round(vv,9),'secs',round(time.time()-t,3),flush=True)
