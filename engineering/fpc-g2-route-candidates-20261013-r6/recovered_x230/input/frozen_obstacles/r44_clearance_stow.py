#!/usr/bin/env python3
"""Nominal OCC shortest solid distance at STOW only; no tolerance or real OEM data."""
import json,time
from pathlib import Path
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from r44_rear_bypass import ribbon_at,protected,ROOT
sh,_,_=ribbon_at(0.,0.,-7.95)
d={}
for name,shape in protected(0.,0.).items():
 calc=BRepExtrema_DistShapeShape(sh.wrapped,shape.wrapped)
 assert calc.IsDone()
 d[name]=round(float(calc.Value()),7)
out={'revision':'R44 R38 research proxy OCC direct solid-to-solid distance STOW only',
     'branch':'NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95','s_mm':0.,'q_mm':0.,
     'nominal_min_distances_mm':d,'OEM_full_package_not_represented':True,
     'no_claim_continuous_dynamics_or_tolerance':True,'manufacturing_go':False}
ROOT.joinpath('evidence').mkdir(exist_ok=True)
ROOT.joinpath('evidence/R44_STOW_exact_clearance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,indent=2))
