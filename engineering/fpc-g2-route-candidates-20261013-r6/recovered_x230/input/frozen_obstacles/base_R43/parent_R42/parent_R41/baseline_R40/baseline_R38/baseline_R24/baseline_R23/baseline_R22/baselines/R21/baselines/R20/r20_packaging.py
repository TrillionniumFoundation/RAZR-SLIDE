"""Negative physical integration check: local R20 dog-carriage envelopes vs old
R19 and R17 body/OLED/FPC proxies at both end poses. Do not pretend fit.
"""
import sys,json
from pathlib import Path
import cadquery as cq
from r20_model import ROOT
from r20_cad import local_assembly,vol
R19=ROOT/'legacy_R19'
R17=ROOT/'legacy_R17'
sys.path.insert(0,str(R19))
from r19_dock_model import assembly as r19_assembly,g
sys.path.insert(0,str(R17))
from r17_model import Params
from r17_cad import assembly as r17_assembly

def run():
  results=[]
  for stage,s,q,y,padface,leaf in [('STOW',0,0,30.,-.15,0.),
                                  ('OPEN',g.Y,g.Z,84.75,g.T-g.bridge_thickness-.15,1.)]:
    prior=r19_assembly(s,q,'RETRACTED')
    r17=r17_assembly(Params(),s,q,leaf)
    local=local_assembly(True,False,False)
    parts={k:v.translate(cq.Vector(0,y,padface)) for k,v in local.items() if not k.startswith('A_PAD')}
    hits=[]
    targets={'A_FRAME_PROXY':prior['A_FRAME_R16'],
             'B_CORE_RECESSED_PROXY':prior['B_FRAME_RECESSED'],
             'B_OPEN_FLOATING_ISLAND_PROXY':prior['B_OPEN_FLOATING_ISLAND'],
             'OLED_R17_PROXY':r17['OLED'],
             'LOCAL_B_FPC_R17_PROXY':r17['FPC']}
    totals={key:0. for key in targets}
    for pname,shape in parts.items():
      for tname,tsh in targets.items():
        v=vol(shape,tsh)
        if v>1e-5:
          totals[tname]+=v
          hits.append(dict(cartridge_part=pname,baseline_part=tname,volume_mm3=round(v,6)))
    results.append(dict(stage=stage,main_body_s_mm=s,main_body_q_mm=q,
                        pad_plane_global_z_mm=padface,center_global_y_mm=y,
                        crosstalk_intersect_mm3={k:round(v,6) for k,v in totals.items()},
                        collisions=hits,
                        includes_full_OEM_objects=False))
  out=dict(sources=dict(R17='R17/OLED and B display FPC proxy',R19='R19 A/B cores and floating island'),
           notes=['Overlap with B core requires carving pockets, weakening load path; it is not permitted automatically.',
                  'This is an adversarial footprint check, not a full Y/Z sweep of the cartridge.',
                  'Spring backs, driving links, TE real STEP and solder PCB stack are not represented.'],
           results=results, manufacturing_release=False)
  (ROOT/'verification'/'R20_integration_negative.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
  return out
if __name__=='__main__':
  d=run()
  for s in d['results']:print(s['stage'],s['crosstalk_intersect_mm3'])
