"""R20: physically blocked *local* dual-end contact cartridge proposal.
Based on R19 endpoint locations and TE 2199001-1 public DRAWING dimensions.
None of the dog/actuator/seat/tolerance dimensions below are supplier-qualified.
Dimensions are mm. Coordinate frame: A contact pad face is Z=0;
contact carrier is behind it Z<0; X across width; Y longitudinal.
This IS NOT a full RAZR mechanical design, cannot prove lock actuation.
"""
from dataclasses import dataclass, asdict
import math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
@dataclass(frozen=True)
class Design:
    te_part:str='TE 2199001-1'
    te_url:str='https://www.te.com/en/product-2199001-1.html'
    free_height:float=1.20    # vendor
    hmin:float=.70             # vendor
    hmax:float=1.00            # vendor
    te_width:float=1.05        # vendor
    te_length:float=2.4        # vendor
    te_signal_current_A:float=1.5 # vendor: signal application only
    nominal_h:float=.85       # chosen nominal working height
    retract:float=.80         # unqualified carrier actuator stroke
    tongue_zmin:float=-1.50
    tongue_zmax:float=-1.20
    dog_zmin:float=-1.55
    dog_zmax:float=-1.00
    pad_t:float=.12
    pad_width:float=2.10
    pad_length:float=3.40
    # exact positional limits not yet tied to real manufacturing tolerance
    x_pins:tuple=(-12.,-4.,4.,12.)
    dog_closed_left:tuple=(-18.1,-16.9)
    tongue_left:tuple=(-17.8,-17.2)
    dog_retract_x:float=1.40
    local_housing_halfwidth:float=23.0
    station_halfwidth:float=24.0
    y_station_halfextent:float=3.20
    # screening assumptions: no source certifies these tolerances!
    global_preset_error:float=.25
    new_datums_error:float=.04
    carrier_machining_error:float=.02
    pcb_stack_error:float=.03
    contact_solder_error:float=.02
    thermal_wear_increment:float=.05
    contact_pad_xy_error:float=.25
    safe_retracted_tip_clearance_min:float=.15
    def __post_init__(self):
        assert self.hmax>self.hmin and self.free_height>self.hmax
        assert len(self.x_pins)==4
p=Design()

def working_height_window(error, params=p):
    lo=params.nominal_h-error;hi=params.nominal_h+error
    margin=min(lo-params.hmin,params.hmax-hi)
    return dict(half_stack_error_mm=round(error,6),working_height_interval_mm=[round(lo,6),round(hi,6)],
                min_vendor_margin_mm=round(margin,6),passes=margin>=-1e-10)

def tolerance_budget(params=p):
    stack=(params.new_datums_error+params.carrier_machining_error+
           params.pcb_stack_error+params.contact_solder_error)
    aged=stack+params.thermal_wear_increment
    old=working_height_window(params.global_preset_error,params)
    cand=working_height_window(stack,params)
    after=working_height_window(aged,params)
    # retract geometry uses spring free height, maximum error adds to tip towards pad.
    nominal_clearance=params.nominal_h+params.retract-params.free_height
    slide_clearance=nominal_clearance-params.global_preset_error
    overlap_x=(params.pad_width-params.te_width)/2-params.contact_pad_xy_error
    overlap_y=(params.pad_length-params.te_length)/2-params.contact_pad_xy_error
    return dict(old=old,preliminary_room_temp=cand,thermal_wear=after,
                proposed_error_sources_mm={'real_locating_faces':params.new_datums_error,
                  'carrier_seat':params.carrier_machining_error,'board_pad_stack':params.pcb_stack_error,
                  'solder_contact_seat':params.contact_solder_error,'additional_aging_thermal':params.thermal_wear_increment},
                proposed_stack_achieved_in_reality=False,
                retracted_free_tip_clearance_nominal_mm=round(nominal_clearance,6),
                retracted_free_tip_clearance_if_global_error_025_mm=round(slide_clearance,6),
                passes_hypothesized_retracted_min=slide_clearance>=params.safe_retracted_tip_clearance_min,
                nominal_xy_min_overlap_x_mm=overlap_x, nominal_xy_min_overlap_y_mm=overlap_y,
                signal_contact_NOT_battery_power_qualified=True)

def compatible_double_end_ports(s,q,g_slide=79.75,g_z=8.2,epsilon=1e-6):
    # Coordinates inherited from R19, but permit only *assumed* mechanical seating proofs.
    return dict(stowed=(abs(s)<epsilon and abs(q)<epsilon),
                deployed=(abs(s-g_slide)<epsilon and abs(q-g_z)<epsilon),
                intermediate=(epsilon<s<g_slide-epsilon or epsilon<q<g_z-epsilon))

def allowed_contact_carriage(left_dog_open,right_dog_open,endpoint_seated,
                             port_id='OPEN',spring_retract_verified=False):
    # This is a verification oracle, NOT proof real hardware can mechanically impose it.
    return bool(left_dog_open and right_dog_open and endpoint_seated and spring_retract_verified)

def screen_oled_limit(R=3.4,thick=.16,avail=7.3,clearance=.30):
    # Conservative ideal-plane single-U feasibility; NOT OLED vendor qualified.
    separation=2*R+thick
    geometric_remain=avail-separation
    return dict(R_assumed_mm=R,panel_total_thickness_assumed_mm=thick,
      required_stack_spacing_2R_plus_screen_t_mm=separation,available_mm=avail,ideal_spare_mm=geometric_remain,
      required_protective_spare_mm=clearance,screen_geometric_pass=geometric_remain>=clearance,
      supplier_dynamic_R_and_creep_qualified=False)

def model_report():
    return dict(revision='R20 local concept: gated / fail-retract terminal signal contacts; NOT production',
        design=asdict(p),R19_source='/mnt/data/RAZR_SLIDE_R19/r19_dock_model.py',
        vendor_source='https://www.te.com/en/product-2199001-1.html',
        tolerance=tolerance_budget(),bend=screen_oled_limit(),
        dock_positions=dict(closed=dict(B_slide_mm=0,B_dock_mm=0,A_station_y_mm=30,B_local_y_mm=30),
                            open=dict(B_slide_mm=79.75,B_dock_mm=8.2,A_station_y_mm=84.75,B_local_y_mm=5.)),
        gates={'local_right_left_blocking_geometry':False,'real_both_end_seating_cam':False,
               'real_carriage_actuation':False,'real_carriage_retract_before_unlock':False,
               'full_two_cabin_3D_noninterference':False,'power_USB_audio_qualified':False,
               'OLED_dynamic_R3_4_qualified':False,'4700mAh_real_cell_fit_qualified':False,
               'manufacturing_release':False})
if __name__=='__main__':print(json.dumps(model_report(),indent=2,ensure_ascii=False))
