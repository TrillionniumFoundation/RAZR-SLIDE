#!/usr/bin/env python3
"""Reject unsafe scope transfers from real public profiles to the project.

This is a document/engineering screen, not a copper fatigue model or physical
qualification. Generic radius guidance must never become a production limit.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path

def number(x,name,zero=False):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 or (x==0 and not zero):
        raise ValueError(name+' must be finite '+('nonnegative' if zero else 'positive'))
    return float(x)

def dynamic_profile_screen(profile,radius_mm,bend_axis='THICKNESS',twist=False):
    radius=number(radius_mm,'radius');nom=number(profile['flex_thickness_mm'],'nominal thickness')
    tolerance=profile.get('flex_thickness_tolerance_plus_mm')
    reasons=[]
    if tolerance is None:
        worst=None;minimum=None;radius_check=None;reasons.append('maximum_total_stackup_thickness_uncontrolled')
    else:
        worst=nom+number(tolerance,'positive thickness tolerance',True)
        minimum=100*worst # Sierra manufacturer generic dynamic design screen, not material qualification.
        radius_check=radius>=minimum
        if not radius_check:reasons.append('below_generic_100x_max_thickness_design_screen')
    if profile.get('use')!='B_DYNAMIC':reasons.append('supplied_profile_is_not_Use_B_dynamic')
    if profile.get('base_copper')!='RA':reasons.append('RA_copper_not_specified_in_delivered_profile')
    if profile.get('copper_plated_in_flex'):reasons.append('plated_copper_in_dynamic_zone_requires_specific_review')
    if profile.get('copper_layers',0)!=1:reasons.append('multilayer_dynamic_zone_requires_specific_review')
    if bend_axis!='THICKNESS' or twist:reasons.append('3D_hard_axis_or_twist_is_outside_generic_radius_guidance')
    if not profile.get('dynamic_qualified'):reasons.append('no_project_dynamic_qualification_report')
    return {'profile_id':profile['id'],'radius_mm':radius,'max_total_thickness_mm':worst,'generic_dynamic_min_radius_mm':minimum,'generic_radius_screen_only_passed':radius_check,
      'generic_guide':'Sierra Circuits own layout guide, dynamic 100x finished board thickness','required_Use_B_stackup_received':profile.get('use')=='B_DYNAMIC',
      'public_profile_suitable_for_project_dynamic_use':len(reasons)==0,'rejection_reasons':reasons,'manufacturing_go':False}

def bm28_contact_screen(signal_currents,power_currents,mate_cycles,moving_mate):
    if len(signal_currents)>24 or len(power_currents)>2:raise ValueError('exact pair has 24 signal contacts and 2 power fittings')
    currents=[number(x,'contact current',True) for x in signal_currents+power_currents]
    cycles=number(mate_cycles,'mating cycles',True)
    reasons=[]
    if any(c>.3 for c in signal_currents):reasons.append('signal_contact_above_0.3A')
    if any(c>5 for c in power_currents):reasons.append('power_fitting_above_5A')
    if sum(currents)>10:reasons.append('catalog_total_current_above_10A')
    if cycles>10:reasons.append('above_specified_10_mating_cycles')
    if moving_mate:reasons.append('sliding_motion_must_not_mate_or_unmate_BM28')
    return {'contact_rating_screen_passed':not reasons,'rejection_reasons':reasons,'rated_current_is_FPC_capacity':False,'manufacturing_go':False}

def source_conflict_screen(conflict):
    reasons=[]
    if abs(conflict['overall_thickness_mm']-conflict['PDF_rigid_total_mm'])>1e-6:reasons.append('XML_overall_vs_PDF_rigid_thickness_mismatch')
    if conflict['not_used_layer_mm']>0:reasons.append('unused_physical_layer_in_XML_thickness_sum')
    if float(conflict['XML_stackup_tolerances']['tolPlus'])!=conflict['PDF_actual_flex_tolerance_plus_minus_mm']:reasons.append('XML_zero_vs_PDF_nonzero_thickness_tolerance')
    return {'automatic_import_allowed':not reasons,'rejection_reasons':reasons,'supplier_source_silently_repaired':False,'manufacturing_go':False}

def illustrative_copper_loop(length_mm,width_mm,copper_mm,current_A):
    """Two separate full-width conductors, 20 C assumed rho, no ampacity result."""
    length=number(length_mm,'conductor length')/1000
    area=number(width_mm,'full conductor width')*number(copper_mm,'copper thickness')/1e6
    current=number(current_A,'current',True)
    rho=1.724e-8 # Explicit assumed resistivity; no actual material or temperature data.
    loop=2*rho*length/area
    return {'assumed_copper_rho_ohm_m':rho,'temperature_assumed_C':20,'each_conductor_length_mm':length_mm,'each_full_conductor_width_mm':width_mm,'copper_mm':copper_mm,'current_A':current,'ideal_loop_ohm':loop,'ideal_loop_drop_V':loop*current,'ideal_loop_loss_W':loop*current**2,'ignores_pad_neckdowns_contacts_heat_transfer_and_tolerance':True,'is_actual_FPC_ampacity_or_temperature_result':False}

def build_report(folder:Path):
    facts=json.loads((folder/'input_audit.json').read_text())
    profiles=[dynamic_profile_screen(p,16.5) for p in facts['vendor_standard_profiles']]
    proxy={'id':'R44_RESEARCH_T0.15_ILLUSTRATIVE_WORST_PLUS0.05_NOT_PROJECT_TOLERANCE','flex_thickness_mm':.15,'flex_thickness_tolerance_plus_mm':.05,'use':'UNKNOWN','base_copper':'UNKNOWN','copper_layers':None,'dynamic_qualified':False}
    return {'frozen_slide_mm':79.75,'frozen_normal_seating_mm':8.2,'original_public_profile_screens':profiles,'source_conflict':source_conflict_screen(facts['FLEX2_machine_readable_conflict']),
      'preserved_counterexamples':{
       'same_R44_nominal_thickness_does_not_control_worst_case':dynamic_profile_screen(proxy,16.5),
       'same_100x_radius_does_not_cover_width_axis':dynamic_profile_screen(dict(proxy,flex_thickness_mm=.10,flex_thickness_tolerance_plus_mm=0),16.5,'WIDTH'),
       'all_24_signal_pins_at_5A':bm28_contact_screen([5.0]*24,[],1,False),
       'two_5A_power_fittings_plus_24_0p3A_signal':bm28_contact_screen([.3]*24,[5.0,5.0],1,False),
       'connector_mates_on_every_slide':bm28_contact_screen([],[],300000,True)},
      'conditional_electrical_loss_examples':[illustrative_copper_loop(120,1.2,.018,c) for c in (.3,5)],
      'all_loss_examples_use_two_separate_full_width_strips_not_one_split_strip':True,'no_actual_current_or_temp_or_force_or_fatigue_measured':True,
      'supplier_selected_dynamic_FPC_part_and_revision':None,'full_artwork_and_netlist_received':False,'continuous_3D_material_frames_and_twist_received':False,
      'complete_phone_PCBA_received':False,'manufacturing_go':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--out',type=Path);a=p.parse_args()
    result=build_report(a.folder);out=a.out or a.folder/'dynamic_screen.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'real_public_profiles':len(result['original_public_profile_screens']),'eligible_dynamic_profiles':sum(r['public_profile_suitable_for_project_dynamic_use'] for r in result['original_public_profile_screens']),'manufacturing_go':False}))

if __name__=='__main__':main()
