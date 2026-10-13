"""R16 complementary end relief geometry candidate, in mm.
No OEM CAD and NO validated OLED bend/contact/volume or load life.
Axes: x across width, y up along device, z forward to screen.
A fixed front-low cabin; B rear-low cabin slides +y and docks forward +z.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import math,json
ROOT=Path(__file__).resolve().parent
@dataclass(frozen=True)
class G:
    H:float=94.25
    W:float=73.99
    Y:float=79.75
    T:float=7.20
    gap_z:float=1.00
    bridge_end_relief:float=.35
    bridge_thickness:float=.80
    overlap_outer_lane_x0:float=35.60
    overlap_inner_lane_x0:float=34.00
    overlap_inner_lane_x1:float=35.10
    top_u_R_ASSUMED:float=5.2
    battery_nominal_V:float=3.85
    battery_target_mAh:int=4700
    # screen aspect estimate is not a module supplier mechanical drawing
    assumed_screen_aspect_long:float=22.
    assumed_screen_aspect_short:float=9.
    OLED_inch:float=7.
    Y_end_error_max:float=.20
    front_screen_above_body_mm:float=.40
    storage_track_min_from_B_back_mm:float=.30
    X_center_error_max:float=.10
    screen_active_clearance_min_trail:float=.30
    trial_load_N:float=2.
    trial_touch_patch_width_mm:float=10.
    trial_E_MPa:float=110000.
    assumed_battery_A_w:float=62.
    assumed_battery_A_h:float=65.
    assumed_battery_B_w:float=60.
    assumed_battery_B_h:float=36.
    assumed_battery_t:float=4.1
    @property
    def O(self):return self.H-self.Y
    @property
    def Z(self):return self.T+self.gap_z
    @property
    def active_width(self):return self.OLED_inch*25.4*self.assumed_screen_aspect_short/math.hypot(self.assumed_screen_aspect_long,self.assumed_screen_aspect_short)
    @property
    def active_height(self):return self.OLED_inch*25.4*self.assumed_screen_aspect_long/math.hypot(self.assumed_screen_aspect_long,self.assumed_screen_aspect_short)

class M:
    def __init__(self,g=None):self.g=g or G()
    def state(self,s,z=0.,dx=0.,dy=0.,pin=False):
        p=self.g
        return dict(A_y=(0,p.H),B_y=(s+dy,s+dy+p.H),y_overlap=max(0.,p.H-s-dy),
                    B_z=(-p.Z+z,-p.gap_z+z),
                    core_overlap_y=max(0.,min(p.Y,s+dy+p.H)-max(0.,s+dy+p.O)),
                    dock_z=z,lock_pin=pin,dx=dx)
    def metrics(self):
        p=self.g
        near_left_clearance=p.overlap_outer_lane_x0-p.overlap_inner_lane_x1-2*p.X_center_error_max
        b_inner_to_OLED=p.overlap_inner_lane_x0-p.active_width/2
        seam_min=p.bridge_end_relief-p.Y_end_error_max
        seam_max=p.bridge_end_relief+p.Y_end_error_max
        volume_full=p.H*p.W*p.T/1000
        nominal_full_clash=p.O*p.W*p.T/1000
        volume_A_battery=p.assumed_battery_A_w*p.assumed_battery_A_h*p.assumed_battery_t/1000
        volume_B_battery=p.assumed_battery_B_w*p.assumed_battery_B_h*p.assumed_battery_t/1000
        E=p.battery_target_mAh/1000*p.battery_nominal_V
        battery_req_density=1000*E/(volume_A_battery+volume_B_battery)
        # Simple cantilever strip estimate. Actual plate's 2D boundary stiffness not validated.
        L=p.O-p.bridge_end_relief; b=p.trial_touch_patch_width_mm;t=p.bridge_thickness
        I=b*t**3/12
        delta=p.trial_load_N*L**3/(3*p.trial_E_MPa*I)
        # plate width within OLED area, bending as beam along y
        bridge_vol= (67.*L*t)/1000
        available_fold_plane_sep=p.T+p.front_screen_above_body_mm-p.storage_track_min_from_B_back_mm
        min_required_fold_plane_sep=2*p.top_u_R_ASSUMED
        return dict(single_U_available_plane_separation_at_dock_mm=available_fold_plane_sep,
                    single_U_needed_plane_separation_at_R5_2_mm=min_required_fold_plane_sep,
                    single_U_dock_R5_2_shortfall_mm=max(0,min_required_fold_plane_sep-available_fold_plane_sep),
                    single_U_packaging_MAX_possible_R_dock_mm=available_fold_plane_sep/2,
                    R5_2_screen_turn_feasible_inside_one_7_2mm_module=False,
                    revision='R16 complementary terminal overlap — provisional geometry only',
                    params=asdict(p),
                    A_and_B_same_external_bounding_rectangles=True,
                    cabin_H=p.H,cabin_W=p.W,slide_s=p.Y,expanded_H=p.Y+p.H,
                    cabin_Y_overlap=p.O,
                    baseline_full_rect_prism_overlap_cm3=nominal_full_clash,
                    total_cabin_rectangular_envelope_cm3_each=volume_full,
                    nominal_interleaved_X_lane_gap_mm=p.overlap_outer_lane_x0-p.overlap_inner_lane_x1,
                    worst_interleaved_X_gap_with_offsets_mm=near_left_clearance,
                    OLED_active_edge_to_inner_rail_mm=b_inner_to_OLED,
                    central_support_seam_nominal_mm=p.bridge_end_relief,
                    central_support_seam_min_mm=seam_min,
                    central_support_seam_max_mm=seam_max,
                    A_bridge_cantilever_mm=L,
                    A_bridge_volume_cm3=bridge_vol,
                    A_bridge_simplified_touch_delta_mm=delta,
                    A_bridge_FE_or_finger_load_qualified=False,
                    added_docking_Z_mm=p.Z,
                    battery_energy_target_Wh=E,
                    A_battery_ASSUMED_envelope_cm3=volume_A_battery,
                    B_battery_ASSUMED_envelope_cm3=volume_B_battery,
                    battery_min_active_volumetric_density_Wh_per_L=battery_req_density,
                    real_battery_energy_or_fit_qualified=False,
                    OLED_active_width_estimated_mm=p.active_width,
                    OLED_active_height_estimated_mm=p.active_height,
                    top_U_radius_supplier_qualified=False,
                    full_OLED_Z_motion_conservation_qualified=False,
                    entire_phone_oem_assembled_or_qualified=False)
    def sweep(self):
        p=self.g
        # Full Y traverses with rear-plane separation = 1 mm.
        # End-stage Z traverses with B central y starting just beyond A bridge edge.
        ys=[i*p.Y/2000 for i in range(2001)]
        zs=[i*p.Z/400 for i in range(401)]
        ys_states=[self.state(s) for s in ys]
        z_states=[self.state(p.Y,z) for z in zs]
        assert all(a['B_z'][1]<=0 for a in ys_states)
        assert all(a['B_z'][1] <= -p.gap_z+1e-10 for a in ys_states) # core overlap in y IS expected, but B remains behind A in z
        assert all(a['core_overlap_y']<=1e-10 for a in z_states)
        # The central functional protected volumes are intentionally cut back by O.
        # The B center envelope begins s+O, and at any s≤Y may overlap A center at small s,
        # but lies in rear plane with 1mm separation; correct status is Z-separation, not XY separation.
        return dict(Y_states=len(ys_states),Z_states=len(z_states),worst_B_front_minus_A_rear_z_mm=max(a['B_z'][1] for a in ys_states),
                    min_nominal_center_core_y_gap_at_dock=p.bridge_end_relief,
                    entire_OLED_included=False,full_cabins_are_simplified_solids=True)
if __name__=='__main__':
  m=M(); print(json.dumps({'metrics':m.metrics(),'sweep':m.sweep()},ensure_ascii=False,indent=2))
