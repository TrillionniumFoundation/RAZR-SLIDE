"""R22 addendum: independently scoped supplier documents and robust geometry sensitivity.
All dimensions are project-level ASSUMPTIONS unless explicitly sourced; NO accepted OEM panel.
"""
from __future__ import annotations
from pathlib import Path
import json
from r22_oled import ideal_gap
from r22_mechanics import ROOT


def oem_radius_screen():
    scenarios=[]
    for label,R,t,cavity,target in (
        ('R21_NOMINAL_ASSUMPTIONS',3.4,.16,7.30,.30),
        ('R21_CAVITY_MINUS_0P05_MM',3.4,.16,7.25,.30),
        ('R21_CAVITY_MINUS_0P10_MM',3.4,.16,7.20,.30),
        ('R21_OLED_STACK_PLUS_0P05_MM',3.4,.21,7.30,.30),
        ('PUBLIC_R5_DEMO_DIMENSIONAL_SUBSTITUTION_ONLY',5.,.16,7.30,.30),
        ('PUBLIC_R3_2026_DEMO_DIMENSIONAL_SUBSTITUTION_ONLY',3.,.16,7.30,.30),
    ):
        r=ideal_gap(R,t,cavity,target)
        # >=target is a geometrical screen, NOT a supplier authorization or GD&T qualification.
        scenarios.append(dict(case=label,**r,positive_target_margin_mm=round(
            r['nominal_residual_mm']-target,5),OEM_module_approved=False))
    return dict(scenarios=scenarios,
        nominal_R3p4_headroom_above_target_mm=.04,
        hypothetical_0p1_cavity_shrink_causes_target_shortfall_mm=.06,
        OLED_active_area_edge_reference_clearance_mm=.319619,
        edge_extra_0p15_per_side_R21_observed_nearest_mm=.28954,
        end_to_end_OEM_full_module_packaging_pass=False)


def source_review():
    return {
      'TE_2199001_1':{
        'official_product':'https://www.te.com/en/product-2199001-1.html',
        'rated_max_current_A':1.5,'intended_application':'Signal',
        'product_qualification_test_report':'https://www.te.com/commerce/DocumentDelivery/DDEController?Action=srchrtrv&DocFormat=pdf&DocLang=English&DocNm=501-78343&DocType=Specification+Or+Standard&PartCntxt=2199001-1',
        'qualification_report_sample_part_identified_as':'2134078-1',
        'qualification_report_nominal_repeated_mating_cycles':10,
        'transfer_to_exact_2199001_1_300k_slide_qualification':False,
        'OEM_STEP_link_offered_but_binary_import_failed':True,
        'power_or_USB3_qualified':False},
      'HARWIN_S1961_46R':{
        'manufacturer_comparison_chart':'https://cdn.harwin.com/pdfs/Harwin_SMT_Spring_Contacts_Comparison_Chart.pdf',
        'comparison_chart_min_durability_cycles':3000,
        'official_individual_drawing':'https://cdn.harwin.com/pdfs/S1961R.pdf',
        'individual_drawing_durability_cycles':5000,
        'interpretation':'Distinct document thresholds, not necessarily contradictory; obtain current revision/lot-specific written specification.',
        '300k_full_slide_qualified':False},
      'MILLMAX_0900_0_15_20_76_14_11_0':{
        'OEM_series_datasheet':'https://www.mill-max.com/sites/default/files/external/catalog/2019-04/023M-028M.pdf',
        'distributor_exact_part':'https://www.digikey.com/en/products/detail/mill-max-manufacturing-corp/0900-0-15-20-76-14-11-0/663496',
        'distributor_listed_mating_cycles':1000000,
        'distributor_listed_max_working_height_mm':3.48,
        'distributor_listed_recommended_working_height_mm':3.00,
        'distributor_listed_min_working_height_mm':2.50,
        'distributor_listed_continuous_A':2,
        'OEM_300k_cycle_our_orientation_and_loading_qualified':False,
        'fits_TE_1p2mm_recess_without_reCAD':False},
      'VISIONOX_2026_MWC':{
        'OEM_demo_news':'https://www.visionox.com/en/contents/191/676.html',
        'OEM_demo_publication_date':'2026-03-03',
        'module_dynamic_sliding_radius_mm':3.0,
        'travel_mm':48.55,
        'confirmed_on_project_7inch_79p75mm_travel':False,
        'project_R3p4_permission':False,
        'static_stow_and_flattening_force_evidence':False},
      'IEC_62715_6_42_2026':{
        'official':'https://webstore.iec.ch/en/publication/78233',
        'publication_date':'2026-06-19',
        'scope':'flattening force MEASUREMENT METHOD',
        '30万次_life_certificate':False}}


def run(write=True):
    out=dict(revision='R22 supplier primary evidence and tolerance audit addendum',
        vendor=source_review(),oled_sensitivity=oem_radius_screen(),
        no_new_OEM_test_or_formal_sample_qualification=True,
        physical_hard_gate='MANUFACTURING_NO_GO',manufacturing_go=False)
    if write:
        (ROOT/'verification'/'R22_supplier_review.json').write_text(
            json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return out

if __name__=='__main__':
    r=run()
    print(json.dumps({'R3p4_cases':r['oled_sensitivity']['scenarios'][:4],
                      'verdict':r['physical_hard_gate']},ensure_ascii=False,indent=2))
