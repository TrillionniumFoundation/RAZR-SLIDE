"""R22 OLED procurement gating grounded in publicly stated device-class demos.

Crucial: public technology demonstrations DO NOT equal sample acceptance of
an exactly sized 7-inch OEM module, nor grant R3.4 for this layup.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
AVAIL_MM=7.3                 # R20 project packaging assumption, not measured OEM
ASSUMED_T_MM=.16             # R20 assumed laminated stack thickness, not OEM
DESIGN_CLEARANCE_MM=.30      # internal screening target, not statutory requirement
ASSUMED_R_MM=3.4

def ideal_gap(R,t=ASSUMED_T_MM,available=AVAIL_MM,minimum=DESIGN_CLEARANCE_MM):
  return dict(radius_mm=R,module_stack_mm=t,available_stack_mm=available,
      path_2R_plus_t_mm=round(2*R+t,5),nominal_residual_mm=round(available-2*R-t,5),
      target_residual_mm=minimum,ideal_geometry_screening_pass=(available-2*R-t >= minimum-1e-9),
      model_is_ideal_and_does_not_include_adhesive_rails_flattening_force_or_aging=True)

def report(write=True):
 out=dict(revision='R22 OLED supply-data RFI; no released panel drawing',
   r21_assumed_screen_mm=dict(R=ASSUMED_R_MM,t=ASSUMED_T_MM,available=AVAIL_MM,
     target_clearance=DESIGN_CLEARANCE_MM,
     theoretical_max_R_if_t_assumption_and_target_clearance_hold_mm=round((AVAIL_MM-ASSUMED_T_MM-DESIGN_CLEARANCE_MM)/2,4)),
   candidate_public_technologies=[
     dict(vendor='Visionox',public_claim='Min roll radius 5 mm for complete module; slidable demonstration R10, travel75',
       radii_mm=[5.,10.],url='https://www.visionox.com/en/technology-product/multi-form.html',
       this_7inch_OLED_specific_DCAD_status='UNAVAILABLE',OEM_permission_to_use_R3_4=False),
     dict(vendor='Visionox',public_claim='2017 older bendable prototype with R3, 207micron module',
       radius_mm=3.,prototype_only=True,
       url='https://www.visionox.com/en/contents/190/338.html',
       this_7inch_OLED_specific_DCAD_status='UNAVAILABLE',OEM_permission_to_use_R3_4=False),
     dict(vendor='BOE',public_claim='slidable/rollable f-OLED technology portfolio; no public target part datasheet',
       url='https://www.boe.com/global/en/Products_OLED.html',
       this_7inch_OLED_specific_DCAD_status='UNAVAILABLE',OEM_permission_to_use_R3_4=False)],
   ideal_screening=[ideal_gap(R) for R in (3.0,3.4,3.42,5.0,10.0)],
   r21_screen_edge_mm=[dict(extra_per_side_mm=0,nearest_mm=.319619,meets_0_30=True),
       dict(extra_per_side_mm=.15,nearest_mm=.28954,meets_0_30=False),
       dict(extra_per_side_mm=.20,nearest_mm=.23954,meets_0_30=False)],
   must_obtain_OEM=[
     'Real complete 7-inch module active area, gross encapsulation outer XY envelope and COF/COG routing/cut shape STEP',
     'Full layer stack after lamination including cover, OCA, OLED, backplate, liner, neutral axis and adhesives',
     'Vendor-approved dynamic and long-stow static Rmin for this exact stack, both tension and compression orientations',
     'Flattening force-vs-position, speed, temperature, prestorage time; IEC 62715-6-42:2026 methods',
     'Post 24/168/1000-hour static R3.4 stow residual strain/crease, flatness, stress relaxation and irreversible curl',
     'Dust/scratch/edge delamination, thermal-humidity lifetime and design target 300k full slide cycles',
     'Cable tail strength, lamination sliding friction, tensioner spring envelope and transport/storage constraints'],
   IEC_62715_6_42_2026='Flattening force MEASUREMENT method for rolled display devices, neither product qualification nor lifetime standard',
   IEC_source='https://webstore.iec.ch/en/publication/78233',
   seven_inch_module_oem_specifications_received=False,
   engineering_geometric_candidate_passes_only_assumptions=True,
   module_lifetime_and_R3_4_qualified=False,manufacture_go=False)
 if write:(ROOT/'verification'/'R22_oled_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 return out
if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False,indent=2))
