"""R23 'no supplier data' interval gate: sensitivity is NOT panel qualification."""
import itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
R3_4=3.4;THICK=.16;CAVITY=7.30;CLEARANCE=.30

def residual(avail=CAVITY,R=R3_4,t=THICK,clear=CLEARANCE):return round(avail-(2*R+t+clear),6)

def study(write=True):
 rows=[]
 for cavity_loss,r_delta,t_delta,storage_reserve in itertools.product(
           (0.,.05,.15), (0.,.05,.10),(0.,.05), (0.,.10)):
    margin=residual(CAVITY-cavity_loss,R3_4+r_delta,THICK+t_delta,CLEARANCE+storage_reserve)
    rows.append(dict(cavity_loss_mm=cavity_loss,additional_radius_mm=r_delta,
        stack_growth_mm=t_delta,storage_creep_reserve_mm=storage_reserve,
        resulting_margin_mm=margin,screening_pass=margin>=0))
 assert len(rows)==36
 passes=sum(x['screening_pass'] for x in rows)
 # All tolerance increments are INVENTED engineering stressors; no OEM material.
 worst=min(rows,key=lambda x:x['resulting_margin_mm'])
 required=2*(R3_4+.10)+(THICK+.05)+(CLEARANCE+.10)+.15
 assert abs(required-(7.3 - worst['resulting_margin_mm']))<1e-9
 result=dict(revision='R23 OLED no OEM datasheet independent interval screening',
     assumed_values_not_OEM=dict(nominal_cavity_mm=CAVITY,radius_mm=R3_4,
            full_laminate_thickness_mm=THICK,target_clearance_mm=CLEARANCE),
     base_margin_mm=residual(),
     stress_cases=len(rows),stress_cases_nominal_geometric_screen_pass=passes,
     stress_cases_failed=len(rows)-passes,
     hypothetical_worst_case=worst,
     hypothetical_required_cavity_depth_mm=round(required,4),
     relative_to_assumed_cavity_deficit_mm=round(required-CAVITY,4),
     not_a_CAD_dimensional_commitment=True,
     R21_OLED_AA_nearest_mm=.319619,
     R21_screen_increase_0p15_each_side_nearest_mm=.28954,
     R21_0p30_clearance_screen_pass_if_border_added=False,
     issuer_questions=['Complete 7-inch model DXF/STEP and gross encapsulated dimensions incl. black border, COF and stiffener',
        'Supplier license for dynamic R3.4 or any alternate static/dynamic minimum radius along intended neutral axis',
        'Full laminate t at min-max temperature, adhesive build and radius/strain tolerance',
        'Flat storage + 24/168/1000-hour parked R with residual curl/crease vs temp/humidity',
        'Flattening force measurement per IEC 62715-6-42:2026 (methods only, NOT life standard)',
        'Mechanism tension/force vs Y/Z position and screen failure map over 300k station-to-station cycles'],
     sample_part_number_and_real_module_document_received=False,
     real_panel_qualified=False,manufacturing_go=False)
 if write:(ROOT/'verification'/'R23_OLED_tolerance_gate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result

if __name__=='__main__':
 r=study();print(json.dumps({k:v for k,v in r.items() if k in ('base_margin_mm','stress_cases','stress_cases_nominal_geometric_screen_pass','hypothetical_worst_case','hypothetical_required_cavity_depth_mm')},ensure_ascii=False,indent=2))
