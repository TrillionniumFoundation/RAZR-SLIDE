"""R22 independent local CAD + whole-B selected-pose proxies; not a mechanism certificate."""
from pathlib import Path
import json
import cadquery as cq
from r22_mechanics import (ROOT,P,r21,intersection,integrated_b_shell,
      stop_contact_metrics,assembly_local,to_blocal,to_global,station_position,
      qualifying_seat,fault_scan,stop_effectively_locked,regression_scenario)
from r22_oled import report as oled_report
from r22_electrical import report as power_report


def check_geometry(write=True):
    assembled=integrated_b_shell();b=assembled['R22_b']
    from r21_verify import baseline_battery_boxes,nearest
    original=assembled['R21_b'];batteries=baseline_battery_boxes()
    poses=[('STOW',0.,0.,0.),('Y_HALF',P.travel/2,0.,0.),
           ('PREDOCK',P.travel,0.,0.),('Z_HALF',P.travel,P.z_travel/2,0.),
           ('OPEN',P.travel,P.z_travel,1.)]
    pose_rows=[];largest_illegal=0.;collision_examples=[]
    for name,s,q,leaf in poses:
      refs=r21.r17_assembly(P,s,q,leaf)
      model_b=b.translate(cq.Vector(0,s,-P.z_travel+q))
      body={k:round(intersection(model_b,sh),7) for k,sh in refs.items()
            if k in ('A','A_fixed_skin','A_moving_leaf','OLED','FPC')}
      moving=[]
      for port in ('STOW','OPEN'):
       seat=qualifying_seat(port,s,q)
       pieces=assembly_local(True,seat['left_face_proxied_seated'],seat['right_face_proxied_seated'],
             seat['captive_A_center_key_proxied_seated'])
       for partkey,sh in pieces.items():
         if not partkey.startswith(('B_CARRIAGE_SAFETY','B_LOAD_FACE_BOLT','B_INDEPENDENT_CENTRE')):continue
         at=to_global(sh,port,s,q)
         bad_b=intersection(at,model_b)
         bad_oled=intersection(at,refs['OLED'])
         bad_fpc=intersection(at,refs['FPC'])
         bad_a=intersection(at,refs['A'])
         badleaf=intersection(at,refs['A_moving_leaf'])
         if max(bad_b,bad_oled,bad_fpc,bad_a,badleaf)>1e-6:
          moving.append(dict(port=port,part=partkey,against_B=round(bad_b,5),
                             OLED=round(bad_oled,5),FPC=round(bad_fpc,5),
                             A=round(bad_a,5),A_leaf=round(badleaf,5)))
      d=nearest(model_b,refs['OLED'])
      row=dict(name=name,B_core_vs_existing_R21_solids_mm3=body,
         min_B_core_to_OLED_mm=round(d,6),new_safety_hardware_illegal_intersections=moving)
      pose_rows.append(row)
      largest_illegal=max(largest_illegal,*(body.values() or [0]))
      collision_examples.extend([(name,x) for x in moving])
    nominal_local_volume=[]
    for port in ('STOW','OPEN'):
      for retracted,seated in ((True,False),(False,False),(False,True)):
       pieces=assembly_local(retracted,seated,seated,seated,True,True)
       collisions=stop_contact_metrics(pieces)
       tab=pieces['B_CARRIAGE_SAFETY_TAB']
       close_engaged=(not retracted and not seated)
       nominal_local_volume.append(dict(port=port,retracted=retracted,seated=seated,
             expected_block=close_engaged,actual_block=stop_effectively_locked(pieces),
             deadbolt_overlaps_mm3=collisions,
             tab_backbone_overlap_mm3=round(intersection(tab,pieces['B_BOTTOM_CARRIER_BACKBONE_PROXY']),5)))
    # The *full B proxy* remains a connected valid CAD body after extra cuts.
    output=dict(revision='R22 mechanically interlocked PROXY only',
      B_one_solid=assembled['one_connected_body'],B_valid=assembled['valid'],
      B_extra_removed_volume_mm3=assembled['cut_from_R21_mm3'],
      R21_ref_B_valid=original.isValid(),
      B_carve_rows=assembled['pocket_rows'],
      local_3stop_contacts=nominal_local_volume,
      selected_poses=pose_rows,
      B_vs_R21_reference_max_overlap_mm3=largest_illegal,
      extra_safety_moving_parts_vs_OLED_FPC_A_and_B_collision_count=len(collision_examples),
      extra_safety_moving_parts_collisions=collision_examples,
      B_battery_interface=dict(
       B_battery_proxy_in_R22_removed_extra_volume_mm3=round(intersection(original.cut(b),batteries['B_battery']),6),
       B_PCB_proxy_in_R22_removed_extra_volume_mm3=round(intersection(original.cut(b),batteries['B_PCB']),6),
       B_camera_proxy_in_R22_removed_extra_volume_mm3=round(intersection(original.cut(b),batteries['B_camera']),6)),
      assembly_load_faces_mated_mechanical_linkage_proof=False,
      captive_cam_kicker_and_actual_spring_engineered=False,
      GD_T_blind_bay_and_open_stow_shearing_load_verified=False,
      manufacturing_go=False)
    if write:(ROOT/'verification'/'R22_mechanical_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    return output


def fault_report(write=True):
 f=fault_scan()
 parked=assembly_local(True,False,False,False,True,True)
 all_open=assembly_local(False,True,True,True,True,True)
 both_old_dogs_open=assembly_local(False,False,False,False,True,True)
 both_sides_wrong_open_center_closed=assembly_local(False,True,True,False,True,True)
 center_wrong_open_sides_closed=assembly_local(False,False,False,True,True,True)
 cases=dict(parked_gate_clear=not stop_effectively_locked(parked),
           old_both_dogs_false_open_still_blocked=stop_effectively_locked(both_old_dogs_open),
           even_both_side_loadbolts_false_open_center_remains_blocked=stop_effectively_locked(both_sides_wrong_open_center_closed),
           center_stop_wrong_open_both_side_bolts_still_block=stop_effectively_locked(center_wrong_open_sides_closed),
           all_three_stops_false_open_unmitigated=not stop_effectively_locked(all_open))
 out=dict(ideal_fault_scan=f,explicit_negative_cases=cases,
     critical_remaining_fault='All three physical stops false open or centre stop held open during dual side misrelease',
     sprung_default_closed_verified_on_actual_hardware=False,
     actuator_retraction_precedes_unseating_verified_on_actual_hardware=False,
     sequencing_mechanical_positive_capture_unproven=True,
     hardware_proven=False,manufacturing_go=False)
 if write:(ROOT/'verification'/'R22_fault_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 return out

if __name__=='__main__':
 print(json.dumps({'mechanics':check_geometry(),'faults':fault_report(),
     'electrical':power_report(),'oled':oled_report()},ensure_ascii=False)[:1500])
