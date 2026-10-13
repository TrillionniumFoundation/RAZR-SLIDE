"""R36 RESEARCH ONLY: proposed separate pin-head anti-withdrawal keeper.
Matsumoto TE-00085 is represented by *catalogue cylinders*, NOT native OEM 3D.
The 0.22 mm R35 pin has no feasible DIN6799-0.8 E-ring fit (1.2 mm application shaft).
The nominal M0.8 screw proxy passes an unthreaded clearance bore, so it is NOT retained.
Units mm. No real connection to electronics or manufacturing safety qualification.
"""
import cadquery as cq
from r25_capture import blk
from r30_mechanics import mirrored
from r35_parts import PIN_X0,PIN_X1,PIN_Y,PIN_Z

# New load path *candidate*: inboard mounting boss, deliberately rear of old cap.
ANCHOR=(32.76,34.48,5.28,7.25,1.83,3.40)
KEEPER=(32.20,32.44,4.50,6.96,2.055,3.015)
SCREW_AXIS_Y,SCREW_AXIS_Z=6.18,2.53
SCREW_X0,SCREW_X1=32.20,34.20
SCREW_RADIUS=.400
SCREW_HEAD_X0,SCREW_HEAD_X1=31.90,32.20
SCREW_HEAD_RADIUS=.65
PLATE_BORE_R=.43
B_BORE_R=.415
# Vendor TN-00005 square nut: 2x2x1mm, 0.8mm female thread;
# below is ONLY a nominal, intentionally rejected envelope, no OEM 3D.
REJECTED_SQUARE_NUT=(33.20,34.20,5.18,7.18,1.53,3.53)

def boss(side):return mirrored(blk(*ANCHOR),side)
def keeper_blank(side):return mirrored(blk(*KEEPER),side)
def axis_cylinder(radius,x0,x1):
    return cq.Solid.makeCylinder(radius,x1-x0,cq.Vector(x0,SCREW_AXIS_Y,SCREW_AXIS_Z),cq.Vector(1,0,0))
def keeper(side):
    tool=axis_cylinder(PLATE_BORE_R,KEEPER[0]-.01,KEEPER[1]+.01)
    return mirrored(blk(*KEEPER).cut(tool).clean(),side)
def mount_bore(side):return mirrored(axis_cylinder(B_BORE_R,SCREW_X0-.03,SCREW_X1+.03),side)
def catalog_m08x2_screw(side):
    shaft=axis_cylinder(SCREW_RADIUS,SCREW_X0,SCREW_X1)
    head=axis_cylinder(SCREW_HEAD_RADIUS,SCREW_HEAD_X0,SCREW_HEAD_X1)
    return mirrored(shaft.fuse(head).clean(),side)
def catalog_m08x2_shank(side):return mirrored(axis_cylinder(SCREW_RADIUS,SCREW_X0,SCREW_X1),side)
def catalog_m08x2_head(side):return mirrored(axis_cylinder(SCREW_HEAD_RADIUS,SCREW_HEAD_X0,SCREW_HEAD_X1),side)
def rejected_square_nut(side):return mirrored(blk(*REJECTED_SQUARE_NUT),side)
def rejected_nut_pocket(side):
    x0,x1,y0,y1,z0,z1=REJECTED_SQUARE_NUT
    return mirrored(blk(x0-.02,x1+.02,y0-.02,y1+.02,z0-.02,z1+.02),side)
def pin_head_shear_surrogate(side):
    from r35_parts import pin
    from r35_parts import HEAD_X0,HEAD_X1,PIN_SHAFT_RADIUS
    sh=axis_cylinder # original pin along x, not screw y/z!
    p=cq.Solid.makeCylinder(PIN_SHAFT_RADIUS,PIN_X1-PIN_X0,
       cq.Vector(PIN_X0,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    return mirrored(p,side)
def metadata():
    return dict(revision='R36 pin-head keeper nominal solids; NO vendor-native CAD',
      original_pin_diameter_mm=.22,smallest_checked_DIN6799_application_shaft_diameter_mm=1.20,
      DIN6799_0p8_not_compatible_with_R35_pin=True,
      keeper_plate_nominal_thickness_x_mm=KEEPER[1]-KEEPER[0],
      screw_candidate='Matsumoto Sangyo TE-00085 M0.8x2 SUS304',
      screw_candidate_head_dia_mm=1.30,screw_candidate_head_height_mm=.30,
      screw_candidate_catalogue_AABB_only=True,
      proposed_B_bore_has_no_thread_model=True,thread_engagement_and_torque_unproven=True,
      vendor_nut_candidate='Matsumoto TN-00005 square nut M0.8 2x2x1mm',
      nut_candidate_only_catalogue_AABB=True,nut_fit_requires_rejected_pocket=True,
      original_R35_cap_and_TE_unpowered_proxy_only=True,
      no_real_spring_shear_load_or_retention_certificate=True)
