#!/usr/bin/env python3
"""Necessary-only geometry for a 180-degree transverse U in sidewall XZ cross-section.
NOT a proof about XY/YZ U or general multi-loop 3D routings.
"""
from pathlib import Path
import json, math
ROOT=Path(__file__).resolve().parent
EDGE_X=36.995
DISPLAY_HALF_X=33.660
WINDOW_Z_LOW=-8.20
WINDOW_Z_HIGH=7.68
SIDE_W=EDGE_X-DISPLAY_HALF_X
Z_H=WINDOW_Z_HIGH-WINDOW_Z_LOW
RECT_DIAGONAL=math.hypot(SIDE_W,Z_H)
RADII=[3.4,5.2,8,10,15,16.33527007391368,16.5,20,22.5]
rows=[]
for r in RADII:
 d=2*r
 exZ=math.sqrt(max(0,d*d-SIDE_W**2))-Z_H
 exX=math.sqrt(max(0,d*d-Z_H**2))-SIDE_W
 rows.append({'assumed_radius_mm':r,'semicircle_endpoint_span_mm':d,
  'side_section_diagonal_mm':RECT_DIAGONAL,'fits_necessary_transverse_span':d<=RECT_DIAGONAL,
  'diameter_minus_diagonal_mm':round(max(0,d-RECT_DIAGONAL),6),
  'additional_Z_height_if_X_fixed_lower_bound_mm':round(max(0,exZ),6),
  'additional_X_width_if_Z_fixed_lower_bound_mm':round(max(0,exX),6)})
result={'scope':'Only a planar 180-degree transverse U whose diameter endpoints both lie in an XZ rectangle',
        'not_a_universal_FPC_topology_impossibility_proof':True,
        'source':'R41 research outer half width 36.995mm and OLED half width 33.66mm, R42 research Z range',
        'available_side_X_width_mm':SIDE_W,'Z_height_mm':Z_H,
        'diagonal_mm':RECT_DIAGONAL,'conditional_radii':rows,
        'vendor_dynamic_R_unknown':True,'300000_cycles_unproven':True,
        'candidate_go':False,'manufacturing_go':False}
p=ROOT/'verification/R43_sidewall_180deg_transverse_bound.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k in ('available_side_X_width_mm','Z_height_mm','diagonal_mm')},indent=2))
