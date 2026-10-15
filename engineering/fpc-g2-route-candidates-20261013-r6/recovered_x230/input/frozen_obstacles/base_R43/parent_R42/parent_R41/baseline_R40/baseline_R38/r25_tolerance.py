"""R25 small deterministic GD&T stress PROBES, NOT actual manufacturer tolerances.
X/Y/Z offsets apply to moving B pawl relative to A key at both dock positions.
We test 0.05mm reverse attempt versus initial free space.  A valid tolerance
range cannot be inferred without actual panel, latching and machining GD&T.
"""
import itertools,json
import cadquery as cq
from r25_capture import ROOT,P,PORT_DATA,pawl,a_key,to_global,intersection

def run(write=True):
 rows=[]
 for width in (.02,.05):
  for port in ('STOW','OPEN'):
   for side in 'LR':
    base=a_key(port,side)
    for dx,dy,dz in itertools.product((-width,0.,width),repeat=3):
     offset=cq.Vector(dx,dy,dz)
     d=PORT_DATA[port]
     at_seat=to_global(pawl(port,side,True),port,*d['dock']).translate(offset)
     departing=to_global(pawl(port,side,True),port,*d['depart']).translate(offset)
     clash_at_seat=intersection(base,at_seat)
     clash_on_0p05_reverse=intersection(base,departing)
     rows.append(dict(hypothetical_abs_offset_mm=width,port=port,side=side,
      dx=dx,dy=dy,dz=dz,dock_intersection_mm3=round(clash_at_seat,8),
      withdraw_0p05_intersection_mm3=round(clash_on_0p05_reverse,8),
      no_interference_docking=clash_at_seat<1e-8,
      anti_separation_0p05_contact=clash_on_0p05_reverse>1e-8))
 groups=[]
 for width in (.02,.05):
  sample=[x for x in rows if x['hypothetical_abs_offset_mm']==width]
  groups.append(dict(hypothetical_single_axis_magnitude_mm=width,sample_count=len(sample),
    clashes_at_seat=sum(not x['no_interference_docking'] for x in sample),
    no_0p05_retention_contact=sum(not x['anti_separation_0p05_contact'] for x in sample),
    jointly_pass_all_conditions=sum(x['no_interference_docking'] and x['anti_separation_0p05_contact'] for x in sample)))
 report=dict(revision='R25 deterministic non-OEM X/Y/Z offsets of A-key/B-pawl retention',
   groups=groups,all_rows=rows,cannot_establish_bounded_0p05_retention=True,
   underlying_0p03_nominal_separation_is_not_supplier_tolerance=True,
   material_elasticity_friction_contact_stiffness_not_modeled=True,
   manufacturing_go=False)
 if write:(ROOT/'verification'/'R25_tolerance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report
if __name__=='__main__':
 x=run();print(json.dumps(x['groups'],indent=2))
