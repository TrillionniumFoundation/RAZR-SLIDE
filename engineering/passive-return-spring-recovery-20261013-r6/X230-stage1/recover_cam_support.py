#!/usr/bin/env python3
"""Recompute q=0 lowest collision-free rigid support from pinned R4 actual CAD."""
import json,itertools,time,platform,sys
from pathlib import Path
sys.dont_write_bytecode=True
import build_spring_cartridges as b
from strict_intersections import CheckedBody,Checker
HERE=Path(__file__).resolve().parent
def main():
 start=time.monotonic();rows=[]
 for port,side in itertools.product(('STOW','OPEN'),'LR'):
  src,_=b.source(port);p=b.derived(port,side,src[side],0.,True)
  for i in range(2):
   stop=p['STOP_'+str(i)];guard=Checker();key=CheckedBody(p['KEY']);root=CheckedBody(p['ROOT']);trace=[]
   for name,target,lo,hi in [('CAM_SUPPORT_Q0',key,1.,1.2),('LOWER_ROOT_SUPPORT_KEY_REMOVED',root,-.1,0.)]:
    def query(v):
     rr=guard.common(CheckedBody(stop.translate(b.rvec(port,v))),target)
     trace.append({'target':name,'lift_mm':v,**rr});return rr['checked_common_mm3']
    assert query(lo)>1e-10 and query(hi)<=1e-10
    for _ in range(32):
     mid=(lo+hi)/2
     if query(mid)>1e-10:lo=mid
     else:hi=mid
    rows.append({'port':port,'side':side,'i':i,'target':name,'collision_side_bracket_mm':lo,'collision_free_bracket_mm':hi,'numeric_collision_threshold_mm3':1e-10,'actual_checked_OCP_common_count':guard.actual_occ_common_count,'trace':list(trace),'physical_friction_or_cam_force_not_proven':True});trace=[]
 result={'host':platform.node(),'source_sha256':b.sha(__file__),'builder_sha256':b.sha(b.__file__),'rows':rows,'manufacturing_go':False,'physical_test_executed':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'cam-support-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([{'port':r['port'],'side':r['side'],'i':r['i'],'target':r['target'],'lo':r['collision_side_bracket_mm'],'hi':r['collision_free_bracket_mm']} for r in rows],indent=2),flush=True)
if __name__=='__main__':main()
