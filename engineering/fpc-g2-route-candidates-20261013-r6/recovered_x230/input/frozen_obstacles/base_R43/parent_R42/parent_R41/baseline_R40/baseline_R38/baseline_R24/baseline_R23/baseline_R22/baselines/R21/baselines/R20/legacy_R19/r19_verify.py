"""Fail-closed tests and independent CAD assertions; no product qualification."""
from pathlib import Path
import json,csv,hashlib,math,unittest,itertools
from r19_dock_model import p,g,contact_window,witness,exact_audit,assembly,model_data,ROOT
import cadquery as cq

V=ROOT/'verification';C=ROOT/'cad';V.mkdir(exist_ok=True);C.mkdir(exist_ok=True)
CASES=[
 ('01_STOW_LOCKED',0.,0.,'STOW_DOCK'),
 ('02_STOW_RETRACTED',0.,0.,'RETRACTED'),
 ('03_Y_25PCT',g.Y*.25,0.,'RETRACTED'),
 ('04_Y_HALF',g.Y*.5,0.,'RETRACTED'),
 ('05_Y_END_PREDOCK',g.Y,0.,'RETRACTED'),
 ('06_Z_HALF',g.Y,g.Z*.5,'RETRACTED'),
 ('07_OPEN_RETRACTED',g.Y,g.Z,'RETRACTED'),
 ('08_OPEN_LOCKED',g.Y,g.Z,'OPEN_DOCK')]

def aabb_distance(a,b):
 a0=a.BoundingBox();b0=b.BoundingBox()
 gaps=[(a0.xmin-b0.xmax,b0.xmin-a0.xmax),
       (a0.ymin-b0.ymax,b0.ymin-a0.ymax),
       (a0.zmin-b0.zmax,b0.zmin-a0.zmax)]
 return max(0,max(max(pair) for pair in gaps))

def analytic_envelope(s,q):
 # Normally both contacts retracted during Y and Z.
 # B stow contact free tip z= T-.85+Hfree-Z+q= -.65+q
 # Pad underside z=-.15. At Y slide q=0 => pad gap .50.
 stow_top=g.T-p.stow_retract+p.h_free-g.Z+q
 open_top=5.40-p.open_retract+p.h_free-g.Z+q
 return dict(stow_free_tip_max_z=stow_top,open_free_tip_max_z=open_top,
             stow_min_clearance_to_A_fixed_core_mm=-stow_top,
             open_min_clearance_to_A_bridge_at_Z_complete_mm=(g.T-g.bridge_thickness-p.pad_t)-open_top,
             Y=s,Z=q)

def evidence_build():
 md=model_data();cad=[]
 for tag,s,q,mode in CASES:
  report=exact_audit(s,q,mode)
  assert not report['collisions'],report
  shapes=assembly(s,q,mode)
  a=cq.Assembly(name=tag)
  for name,sh in shapes.items():
   a.add(sh,name=name)
  dest=C/(tag+'.step');a.save(str(dest),exportType='STEP')
  # Need STEP reimport and solid validity, not only filesize.
  reimport=cq.importers.importStep(str(dest))
  solids=reimport.solids().vals()
  assert len(solids)==len(shapes) and all(k.isValid() for k in solids),(tag,len(solids),len(shapes))
  cad.append(dict(name=tag,s_mm=s,q_mm=q,mode=mode,solids=len(solids),valid=True,
                  checked_specific_pairs_no_positive_intersections=True,
                  sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
 # 2501 analytic states (Y 2001 and Z 500, excluding duplicated endpoint)
 swept=[]
 for k in range(2001):s=g.Y*k/2000;swept.append(analytic_envelope(s,0))
 for k in range(1,501):q=g.Z*k/500;swept.append(analytic_envelope(g.Y,q))
 assert len(swept)==2501
 with (V/'R19_motion_envelopes.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(swept[0]));w.writeheader();w.writerows(swept)
 # worst-case tangential registration overlap exact rectangular pad (center error ±0.25 assumed)
 xy=dict(x_registration_pm_mm=.25,y_registration_pm_mm=.25,
         x_overlap_margin_mm=(p.pad_x_width-p.contact_x_width)/2-.25,
         y_overlap_margin_mm=(p.pad_y_length-p.contact_y_length)/2-.25,
         minimum_guard_mm=.15)
 assert xy['x_overlap_margin_mm']>.15 and xy['y_overlap_margin_mm']>.15
 # Original R18.3 vs chosen assembly target ±0.12 mm not evidence that goal is met.
 sensitivity=[contact_window(i/1000) for i in range(0,251,5)]
 with (V/'R19_contact_tolerance_sweep.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(sensitivity[0]));w.writeheader();w.writerows(sensitivity)
 base=dict(md); base.pop('gates',None)
 result=dict(**base, R18_3_comparison=dict(input_residual_pm_mm=.25,source_compression_interval_mm=[.10,.50],
   nominal_window_mm=[.35,.25],feasible=False),
  R19_contact_window_passing_only_if_assumed_pm_mm=.12,
  worst_guards_mm={'working_height_height_error_0.12_mm':min(contact_window(.12)['lower_margin_mm'],contact_window(.12)['upper_margin_mm']),
                   'lateral_x':xy['x_overlap_margin_mm'],'lateral_y':xy['y_overlap_margin_mm']},
  limitations=['Vendor TE width/height/current known; modeled solids are axis-aligned PROXIES, not downloadable TE STEP.',
   'Specified contact height operating range does not establish 300k cycles, force or contact resistance.',
   'The assumed post-datum ±0.12 mm register tolerance is NOT demonstrated by R16 / hardware.',
   'No actuator, moving support flexure, independent mechanical latch or spring return developed.',
   'Contact PCB pads/recesses may occupy real B board/battery/antenna volume; OEM fit not validated.',
   'Open bridge contact load transmitted to OLED support bridge; FE and fatigue missing.',
   'Four pads per port insufficient to guarantee A battery charge, USB-C and audio/data functionality.',
   'During Y/Z movement, only B pack powers SoC; separate B power management mandatory.',
   'OLED R3.4 vendor durability and R17 contact/bridge safety failures remain open.' ],
  cad=cad, envelope_states=len(swept),
  stow_retracted_to_A_pad_clearance_mm=.50,
  open_retracted_to_A_pad_clearance_mm=.35,
  xy_registration=xy,
  gates=dict(md['gates'], R16_A_B_core_intersection_in_selected_states=False,
             selected_CAD_contact_intersection=False,
             cross_cabin_contact_docked_safe_at_full_vendor_tolerance=False,
             full_Y_Z_continuous_real_noninterference=False,
             R19_manufacturing_release=False))
 (V/'R19_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
 return result

class TestR19(unittest.TestCase):
 def test_r16_baseline(self): self.assertAlmostEqual(g.Y,79.75);self.assertAlmostEqual(g.Z,8.2)
 def test_stepped_contact_stow(self):
  self.assertAlmostEqual(-g.Z+g.T+p.h_nom,-p.pad_t,places=6)
 def test_stepped_contact_open(self):
  self.assertAlmostEqual(5.4+p.h_nom,g.T-g.bridge_thickness-p.pad_t,places=6)
 def test_R183_old_fails(self): self.assertFalse(contact_window(.25)['passes'])
 def test_R19_target_passes_mathematically(self): self.assertTrue(contact_window(.12)['passes'])
 def test_delta_0_15_boundary(self): self.assertTrue(contact_window(.15)['passes'])
 def test_delta_0_16_fails(self): self.assertFalse(contact_window(.16)['passes'])
 def test_stow_retracted_positive_clearance(self):
  self.assertAlmostEqual(-p.pad_t-(-g.Z+g.T-p.stow_retract+p.h_free),.50)
 def test_open_retracted_positive_clearance(self):
  self.assertAlmostEqual((g.T-g.bridge_thickness-p.pad_t)-(5.4-p.open_retract+p.h_free),.35)
 def test_active_early_unlatched_fail(self):
  self.assertTrue(witness('OPEN',g.Y,g.Z,open_extended=True,latched=False)['failure'])
 def test_midpoint_early_fail(self):
  self.assertTrue(witness('MOVE_Y',g.Y/2,0,stow_extended=True,latched=False)['failure'])
 def test_both_retracted_mid_allowed(self):
  self.assertFalse(witness('MOVE_Y',g.Y/2,0,latched=False)['failure'])
 def test_latched_only_stow(self):
  self.assertTrue(witness('STOW',0,0,latched=True)['can_command'])
 def test_latched_only_open(self):
  self.assertTrue(witness('OPEN',g.Y,g.Z,latched=True)['can_command'])
 def test_early_preset_not_enough(self):
  self.assertFalse(witness('OPEN',g.Y,g.Z-.05,latched=True)['can_command'])
 def test_stow_position_no_open_contact(self):
  self.assertFalse(witness('OPEN',0,0,latched=True)['can_command'])
 def test_open_station_aligned_in_Y(self): self.assertEqual(p.open_A_y-p.open_B_y,g.Y)
 def test_xy_guard_x(self): self.assertGreater((p.pad_x_width-p.contact_x_width)/2-.25,.15)
 def test_xy_guard_y(self): self.assertGreater((p.pad_y_length-p.contact_y_length)/2-.25,.15)
 def test_vendored_touch_low_but_no_force(self): self.assertTrue(p.h_nom>p.h_lo and p.h_nom<p.h_hi)
 def test_pin_spacing_no_interpenetration(self):
  self.assertGreater(min(b-a for a,b in zip(p.x_pins,p.x_pins[1:])),p.pad_x_width)
 def test_A_B_body_stow_clear(self):self.assertLess(exact_audit(0,0)['worst_intersection_mm3'],1e-8)
 def test_A_B_body_open_clear(self):self.assertLess(exact_audit(g.Y,g.Z)['worst_intersection_mm3'],1e-8)
 def test_A_B_body_Yhalf_clear(self):self.assertLess(exact_audit(g.Y/2,0)['worst_intersection_mm3'],1e-8)
 def test_A_B_body_Zhalf_clear(self):self.assertLess(exact_audit(g.Y,g.Z/2)['worst_intersection_mm3'],1e-8)
 def test_stow_active_no_clash(self):self.assertFalse(exact_audit(0,0,'STOW_DOCK')['collisions'])
 def test_open_active_no_clash(self):self.assertFalse(exact_audit(g.Y,g.Z,'OPEN_DOCK')['collisions'])
 def test_negative_pin_command_no_mech_enforcement(self):
  self.assertTrue(witness('STOW',0,0,stow_extended=True,latched=False)['failure'])
 def test_not_manufacturing(self):self.assertFalse(model_data()['gates']['manufacturing_release'])
 def test_high_current_not_certified(self):self.assertFalse(model_data()['current_estimate']['meets_parallel_current_without_sharing_evidence'])

def tests():
 res=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestR19))
 return {'testsRun':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'passed':res.wasSuccessful()}

if __name__=='__main__':
 report=evidence_build(); tr=tests(); report['unit_tests']=tr
 (V/'R19_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('SUMMARY',json.dumps(dict(unit_tests=tr,cad=len(report['cad']),envelope_states=report['envelope_states'],residual0_25=contact_window(.25),residual0_12=contact_window(.12)),indent=2))
 assert tr['passed']
