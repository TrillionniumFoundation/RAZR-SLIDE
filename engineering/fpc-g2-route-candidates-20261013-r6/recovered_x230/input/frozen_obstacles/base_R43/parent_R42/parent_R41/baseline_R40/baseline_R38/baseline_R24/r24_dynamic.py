"""Selected full-assembly moving-part OCC collision regression; research only."""
import json
import cadquery as cq
from r24_mechanics import (ROOT,P,r21,intersection,to_global,
    outboard_lugs,outboard_jaws,carrier_arms,solve_jaw_shift_by_A_contact)
from r24_integration import integrate
from r23_gate import carrier_lugs as r23_carrier_lugs

POSES=[('STOW',0.,0.,0.),('STOW_PRE_1p59',1.59,0.,0.),
 ('STOW_CLEAR_8',8.,0.,0.),('STOW_CLEAR_16',16.,0.,0.),
 ('Y_HALF',P.travel/2,0.,0.),('PREDOCK',P.travel,0.,0.),
 ('OPEN_Z_4',P.travel,4.,0.),('OPEN_Z_6p6',P.travel,6.6,0.),
 ('OPEN_Z_7p9',P.travel,7.9,0.),('OPEN',P.travel,8.2,1.)]

def run(write=True):
  a,b,_=integrate()
  clashes=[]; rows=[];single_parts=0
  merged_cache={}
  for side in 'LR':
    m=outboard_lugs(0.)[f'B_R24_OUTBOARD_LUG_{side}'].fuse(
      carrier_arms(0.)[f'B_R24_ARM_{side}']).fuse(
      r23_carrier_lugs(0.)[f'B_R23_CARRIER_LUG_{side}']).clean()
    merged_cache[side]=(m.isValid(),len(m.Solids())==1)
  for tag,s,q,leaf in POSES:
    print('DYNAMIC',tag,flush=True)
    rf=r21.r17_assembly(P,s,q,leaf)
    bw=b.translate(cq.Vector(0,s,-P.z_travel+q))
    for port in ('STOW','OPEN'):
      shifts={side:(solve_jaw_shift_by_A_contact(port,side,s,q)
                    if (port=='STOW' and q==0.) or (port=='OPEN' and s==P.travel) else 0.)
                  for side in 'LR'}
      if any(x is None for x in shifts.values()):
          raise RuntimeError('cannot solve follower: unmodeled foreign stop')
      for side in 'LR':
        nm=f'{port}_{side}'
        shapes={
          'R24_lug':outboard_lugs(0.)[f'B_R24_OUTBOARD_LUG_{side}'],
          'R24_arm':carrier_arms(0.)[f'B_R24_ARM_{side}'],
          'R23_inner_lug':r23_carrier_lugs(0.)[f'B_R23_CARRIER_LUG_{side}'],
          'R24_jaw':outboard_jaws(shifts)[f'B_R24_OUTBOARD_JAW_{side}']}
        for name,part in shapes.items():
          world=to_global(part,port,s,q)
          test={'B':intersection(world,bw),'OLED':intersection(world,rf['OLED']),
             'FPC':intersection(world,rf['FPC']),'A_keyed_shell':intersection(world,a)}
          fail={key:round(v,7) for key,v in test.items() if v>1e-6}
          if fail:clashes.append(dict(pose=tag,station=port,side=side,part=name,clashes=fail))
          single_parts+=1
        # New connected moving group must be single solid in BOTH bays.
        valid,one_body=merged_cache[side]
        rows.append(dict(pose=tag,station=port,side=side,carrier_link_valid=valid,
                   carrier_link_one_solid=one_body,
                   jaw_shift_mm=shifts[side]))
  report=dict(revision='R24 selected 10 poses R23 inner carrier joined to side arm and stop OCC',
       moving_parts_compared=single_parts,individual_carrier_links=len(rows),
       carrier_links_all_one_solid=all(x['carrier_link_one_solid'] and x['carrier_link_valid'] for x in rows),
       unexpected_interference_count=len(clashes),unexpected_interference=clashes,
       cases=rows,actual_intermediate_thermal_fatigue_verified=False,
       contact_key_vs_R24_jaw_ideal_kinematic_only=True,manufacturing_go=False)
  if write:(ROOT/'verification'/'R24_dynamic.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
  return report
if __name__=='__main__':
 r=run()
 print(json.dumps({k:v for k,v in r.items() if k not in ('cases','unexpected_interference')},indent=2))
 print('FAILURES',r['unexpected_interference'][:20])
