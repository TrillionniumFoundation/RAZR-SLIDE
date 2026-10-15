#!/usr/bin/env python3
"""Original BM28 land geometry and static research coupon; no vendor CAD copying.

The supplier publishes no pin-1 designation and the connector has no polarity.
Pad names identify physical sites, not supplier contact numbers or system nets.
Dimensions are transcribed from native EDC drawings, page 1, and checked against
ETAD-H1016-00 pages 5/8. No complete PCBA or manufacturable phone is represented.
"""
from pathlib import Path
import datetime
import hashlib
import json
import platform

ROOT = Path(__file__).resolve().parent

# Millimetres. Drawing dimensions use the nominal values, retaining their
# asymmetric production tolerances separately in official_dimensions.json.
OFFICIAL = {
    'DP': dict(body=(6.12, 1.50, .465), pitch=.35, span=3.85,
        signal_width=.18, signal_inner=.57, signal_outer=1.80,
        power_width=.52, power_inner=.25, power_outer=1.05,
        power_x=2.515, paste_power_inner=.33, paste_power_outer=.97,
        drawing='EDC-364665-53-00', pdf_sha256='13dcd9aed8271eb83d6211f73d91457a383fa25a2cf5edb6ffcf70f75c05276e'),
    'DS': dict(body=(6.80, 1.70, .600), pitch=.35, span=3.85,
        signal_width=.18, signal_inner=1.18, signal_outer=1.80,
        power_width=.53, power_inner=1.24, power_outer=1.90,
        power_x=2.630, paste_power_inner=1.24, paste_power_outer=1.90,
        drawing='EDC-364666-53-00', pdf_sha256='3ac59f6fcd75894db2947297ea78735e15bf09b038d1029e79676e4bde7b9f21'),
}


def rectangles(role, paste=False):
    """Return exact nominal pad/stencil sites viewed from mounting side.

    DP: 4.51 mm is the inner-edge span of the power lands, hence centres
    +/- (4.51 + 0.52)/2. DS: 5.26 mm is the power land centre span.
    POS/NEG labels refer to signed drawing Y; KiCad Y grows down the screen.
    """
    d = OFFICIAL[role]
    rows = []
    for sign, row in ((-1, 'NEG'), (1, 'POS')):
        for i in range(12):
            rows.append(dict(site=f'S_{row}_{i:02d}', kind='signal',
                x=-d['span']/2 + i*d['pitch'],
                y=sign*(d['signal_outer']+d['signal_inner'])/4,
                w=d['signal_width'], h=(d['signal_outer']-d['signal_inner'])/2))
        inner = d['paste_power_inner'] if paste else d['power_inner']
        outer = d['paste_power_outer'] if paste else d['power_outer']
        for side, x in (('L', -d['power_x']), ('R', d['power_x'])):
            # Two lands per one electrically common power fitting. No net is
            # assigned, and these lands cannot be independently repurposed.
            rows.append(dict(site=f'P_{side}', subsite=row, kind='power',
                x=x, y=sign*(outer+inner)/4, w=d['power_width'], h=(outer-inner)/2))
    return rows


def orientation_map(axis='X'):
    """Geometric site correspondence for upper DP mounting-plane inversion.

    Both 180-degree rotations mechanically fit an unpolarized BM28. Only an
    actual continuity witness can prove the intended system-net orientation.
    """
    if axis not in ('X', 'Y'):
        raise ValueError('Only X or Y mounting-plane inversion is defined')
    rows = []
    for row in ('NEG', 'POS'):
        for i in range(12):
            target_row = ('POS' if row == 'NEG' else 'NEG') if axis == 'X' else row
            target_i = i if axis == 'X' else 11-i
            rows.append({'DP_site': f'S_{row}_{i:02d}', 'DS_site': f'S_{target_row}_{target_i:02d}'})
    for side in ('L', 'R'):
        target = side if axis == 'X' else ('R' if side == 'L' else 'L')
        rows.append({'DP_site': 'P_'+side, 'DS_site': 'P_'+target})
    return rows


def fnum(value):
    return f'{value:.6f}'.rstrip('0').rstrip('.')


def kicad_footprint(role):
    d = OFFICIAL[role]
    name = f'Hirose_BM28B0.6-24{role}_2-0.35V_53_RESEARCH_PHYSICAL_SITES'
    lines = [f'(footprint "{name}"', '  (version 20221018)',
        '  (generator "razr_slide_original_endpoint")', '  (layer "F.Cu")',
        f'  (descr "RESEARCH ONLY. Exact nominal {d["drawing"]} land/stencil geometry. Physical site names, NO supplier pin-1 or net assignment. Mask process unqualified.")',
        '  (attr smd exclude_from_pos_files exclude_from_bom)',
        '  (fp_text reference "REF**" (at 0 -2.0) (layer "F.SilkS") (effects (font (size 0.6 0.6) (thickness 0.1))))',
        f'  (fp_text value "BM28_24{role}_RESEARCH" (at 0 2.0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))',
        '  (fp_text user "NO_PIN1_NO_NETS" (at 0 2.9) (layer "Cmts.User") (effects (font (size 0.5 0.5) (thickness 0.1))))',
        # Explicit zero mask expansion is a coupon hypothesis, not a supplier
        # soldermask rule. Copper and stencil apertures remain separately exact.
        '  (solder_mask_margin 0)',
        f'  (fp_rect (start {fnum(-d["body"][0]/2)} {fnum(-d["body"][1]/2)}) (end {fnum(d["body"][0]/2)} {fnum(d["body"][1]/2)}) (stroke (width 0.08) (type default)) (fill none) (layer "F.Fab"))']
    for p in rectangles(role):
        lines.append(f'  (pad "{p["site"]}" smd rect (at {fnum(p["x"])} {fnum(p["y"])}) (size {fnum(p["w"])} {fnum(p["h"])}) (layers "F.Cu" "F.Mask"))')
    # Copper pads deliberately have no F.Paste layer. The independent stencil
    # primitives encode DP 80% power-fitting aperture instead of a guessed ratio.
    for p in rectangles(role, paste=True):
        lines.append(f'  (fp_rect (start {fnum(p["x"]-p["w"]/2)} {fnum(p["y"]-p["h"]/2)}) (end {fnum(p["x"]+p["w"]/2)} {fnum(p["y"]+p["h"]/2)}) (stroke (width 0) (type default)) (fill solid) (layer "F.Paste"))')
    # The DS under-body no-conductive-trace area: between power pads' inner
    # edges and between the inner edges of the signal-pad rows. The original
    # guideline qualifies solder-resist-covered routing, which is unresolved;
    # this coupon applies the stricter copper/track/via exclusion instead.
    if role == 'DS':
        x = d['power_x']-d['power_width']/2
        y = d['signal_inner']/2
        lines.extend(['  (zone (net 0) (net_name "") (layer "F.Cu") (hatch edge 0.2)',
            '    (connect_pads (clearance 0)) (min_thickness 0.05) (fill (thermal_gap 0.2) (thermal_bridge_width 0.2))',
            '    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))',
            f'    (polygon (pts (xy {fnum(-x)} {fnum(-y)}) (xy {fnum(x)} {fnum(-y)}) (xy {fnum(x)} {fnum(y)}) (xy {fnum(-x)} {fnum(y)})))',
            '  )'])
    # DP supplier allocation has side-shaped exclusions; the coupon records
    # the precise published 7.0 x 1.9 mm no-obstruction minimum on User.Drawings.
    # Do not substitute a full rectangle copper keepout through the actual pads.
    if role == 'DP':
        lines.append('  (fp_rect (start -3.5 -0.95) (end 3.5 0.95) (stroke (width 0.08) (type default)) (fill none) (layer "Dwgs.User"))')
    lines.append(')')
    return '\n'.join(lines)+'\n'


# All values here except the connector gap and FR4 minimum are openly stated
# coupon design hypotheses. They are NOT selected materials or production sizes.
COUPON = dict(pcb_t=.8, fpc_t=.15, adhesive_t=.05, stiffener_t=.3,
    buffer_compressed_t=.4, cover_t=.4, fpc_tab_x=8., fpc_tab_y=2.6,
    free_neck_width=2., free_neck_length=8., clamp_length=2.)


def build_cad():
    import cadquery as cq
    def box(x0,x1,y0,y1,z0,z1):
        return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)).val()
    def add_pads(assembly, role, z, upward=True):
        for i,p in enumerate(rectangles(role)):
            y = p['y'] if upward else -p['y']
            shape=box(p['x']-p['w']/2,p['x']+p['w']/2,y-p['h']/2,y+p['h']/2,z,z+.035)
            assembly.add(shape,name=f'{role}_{p["site"]}_{i}_nominal_Cu_RESEARCH')
    paths=[]
    for role in ('DP','DS'):
        a=cq.Assembly(name='RESEARCH_ONLY_original_'+role+'_land_geometry')
        a.add(box(-4.5,4.5,-1.5,1.5,-.3,0),name='COUPON_SUBSTRATE_ASSUMED_0p3')
        add_pads(a,role,0)
        path=ROOT/'step'/f'BM28_{role}_ORIGINAL_NOMINAL_LANDS_RESEARCH.step'
        a.save(str(path),exportType='STEP');paths.append(path)
    c=COUPON
    zfpc=.6; zadh=zfpc+c['fpc_t']; zstiff=zadh+c['adhesive_t']
    zbuf=zstiff+c['stiffener_t']; zcover=zbuf+c['buffer_compressed_t']
    a=cq.Assembly(name='RESEARCH_ONLY_original_static_endpoint_coupon_NOT_OEM_FIT')
    a.add(box(-6,6,-3,13,-c['pcb_t'],0),name='RIGID_PCB_ASSUMED_T')
    # One reserved pair volume prevents pretending the header's 0.465-mm
    # height or the 0.6-mm board gap describes the full assembled stack.
    a.add(box(-3.4,3.4,-.85,.85,0,.6),name='STATIC_MATED_CONNECTOR_RESERVED_ENVELOPE_NOT_VENDOR_SHAPE')
    tab=box(-4,4,-1.3,1.3,zfpc,zadh)
    neck=box(-1,1,1.3,11.3,zfpc,zadh)
    a.add(tab.fuse(neck),name='FPC_TAB_AND_FREE_NECK_ASSUMED_MATERIAL')
    a.add(box(-4,4,-1.3,1.3,zadh,zstiff),name='STIFFENER_ADHESIVE_ASSUMED_T')
    a.add(box(-4,4,-1.3,1.3,zstiff,zbuf),name='FR4_STIFFENER_OFFICIAL_MIN_0p3')
    a.add(box(-4,4,-1.3,1.3,zbuf,zcover),name='COMPLIANT_BUFFER_COMPRESSED_T_ASSUMED')
    a.add(box(-5,5,-2,2,zcover,zcover+c['cover_t']),name='REMOVABLE_COVER_ASSUMED_T_NO_DIRECT_FPC_BOSS')
    for side in (-1,1):
        a.add(box(side*5-.5,side*5+.5,-2,2,0,zcover),name=f'COVER_SUPPORT_{side}_OUTSIDE_7p0x1p9_MATING_AREA')
    a.add(box(-1,1,9.3,11.3,zadh,zadh+.5),name='DISTAL_STRAIN_RELIEF_CLAMP_ASSUMED_NO_LOAD_QUALIFICATION')
    path=ROOT/'step'/'BM28_STATIC_ENDPOINT_COUPON_RESEARCH_NOT_OEM_FIT.step'
    a.save(str(path),exportType='STEP');paths.append(path)
    checks=[]
    for p in paths:
        ss=cq.importers.importStep(str(p)).solids().vals()
        checks.append(dict(file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            solid_count=len(ss),all_solids_valid=all(s.isValid() for s in ss),
            all_solid_volumes_positive=all(s.Volume()>0 for s in ss)))
    return checks, dict(board_top_z=0, upper_fpc_mounting_face_z=zfpc,
        cover_inner_z=zcover,cover_outer_z=zcover+c['cover_t'],
        overall_coupon_stack_mm=c['pcb_t']+zcover+c['cover_t'],
        dynamic_force_at_BM28_proven_N=None, buffer_preload_proven_N=None,
        OLED_or_OEM_fit_verified=False,minimum_free_neck_length_assumed_mm=8.)


def main():
    (ROOT/'RAZR_ENDPOINT_RESEARCH.pretty').mkdir(exist_ok=True)
    (ROOT/'step').mkdir(exist_ok=True)
    for role in ('DP','DS'):
        name=f'Hirose_BM28B0.6-24{role}_2-0.35V_53_RESEARCH_PHYSICAL_SITES.kicad_mod'
        (ROOT/'RAZR_ENDPOINT_RESEARCH.pretty'/name).write_text(kicad_footprint(role))
    (ROOT/'physical_site_map.json').write_text(json.dumps(dict(
        official_pin1_designation_available=False, supplier_no_polarity=True,
        coordinate_site_names_are_not_supplier_pin_numbers=True,
        selected_system_net_mapping=None, physical_continuity_verified=False,
        DP_upper_board_rotate_180_about_X=orientation_map('X'),
        DP_upper_board_rotate_180_about_Y_wrong_orientation_counterexample=orientation_map('Y'),
        manufacturing_go=False),indent=2)+'\n')
    steps,stack=build_cad()
    rec=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),machine=platform.node(),
        step_exports=steps, official_nominal_rectangles={r:rectangles(r) for r in ('DP','DS')},
        research_coupon_hypotheses=COUPON,stack=stack,
        native_KiCad_engine_load_verified=False,vendor_raw_shape_exported=False,
        system_pinout_assigned=False,physical_coupon_built=False,
        manufacturing_go=False)
    (ROOT/'endpoint_build_receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({'step_exports':steps,'stack':stack,'manufacturing_go':False},indent=2))


if __name__=='__main__':
    main()
