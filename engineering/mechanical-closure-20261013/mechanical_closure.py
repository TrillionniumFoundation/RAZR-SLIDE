#!/usr/bin/env python3
"""One-to-one geometric capture coupons and guided bench cartridges.

This supplies real OCC geometry for the missing retention/false-seat experiment.
It does not alter the phone research core, select materials, supply a spring or
force limiter, or qualify hardware. Every output retains manufacturing_go=False.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / "baselines/fpc-r39-20261013"
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(REPO / "engineering/cad-review-20261013"))
from occ_signed_volume import common, validated_solid_volume
from r25_capture import a_key, pawl, PORT_DATA, to_global, blk
from r26_open_mechanics import open_pawl


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
    return {str(p.relative_to(BASE)): digest(p)
            for p in sorted(BASE.rglob("*")) if p.is_file()}


def checked_common(a, b):
    return common(a, b)["checked_volume_mm3"]


def bbox(sh):
    b = sh.BoundingBox()
    return {n: float(getattr(b, n)) for n in
            ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")}


def normalized_originals(port, side):
    """Translate original rigid gauge bodies; no scaling of contact geometry."""
    d = PORT_DATA[port]
    original = to_global(pawl(port, side, True), port, *d["dock"])
    c = original.Center()
    # Preserve the original L/R spacing; place seated contact centre at Y=Z=0.
    offset = (0., -c.y, -c.z)
    key = a_key(port, side).translate(offset)
    p = original.translate(offset)
    parked_local = open_pawl(side, False) if port == "OPEN" else pawl(port, side, False)
    parked = to_global(parked_local, port, *d["dock"]).translate(offset)
    return key, p, parked


def fixture_parts(port, side, parked=False, normal_guide_gap_mm=.01):
    """Custom research dimensions only; actual fasteners/materials unselected.

    Rigid guide cartridge has a base, side/end walls and separately removable
    upper cover. Mount bores are interface placeholders, not modelled threads.
    These added supports change stiffness relative to the phone; force results
    cannot be transferred to a phone without root/guide equivalence evidence.
    """
    key, p, parked_p = normalized_originals(port, side)
    xc = p.Center().x
    dx = parked_p.Center().x - xc
    if port == "STOW":
        y0, y1, z0, z1 = -6., -2., -.25, 2.75
        stem = blk(xc-.16, xc+.16, -2.02, -.015, -.25, .25)
        grip = blk(xc-2., xc+2., .5, 2., 2.95, 7.)
    else:
        y0, y1, z0, z1 = -2., 2., 2.4, 5.4
        stem = blk(xc-.16, xc+.16, -.15, .15, .10, 2.42)
        grip = blk(xc-2., xc+2., -.6, .6, -8., -4.70)
    slider = blk(xc-2., xc+2., y0, y1, z0, z1).fuse(stem).fuse(p).clean()
    key_coupon = key.fuse(grip).clean()
    x0, x1 = min(xc, xc+dx)-2.-.15, max(xc, xc+dx)+2.+.15
    # The housing is a physical CAD guide with end shoulders. The clearance is
    # a fixture hypothesis, not a specified manufacturing tolerance.
    gap = normal_guide_gap_mm
    if not 0 < gap < .2:
        raise ValueError("Fixture normal guide gap outside reviewed geometry range")
    lowz = z0-gap
    bottom = blk(x0-1., x1+1., y0-1.65, y1+1.65, lowz-.8, lowz)
    outer = blk(x0-1., x1+1., y0-1.65, y1+1.65, lowz, z1+gap)
    channel = blk(x0, x1, y0-gap, y1+gap, lowz-.01, z1+gap+.01)
    body = bottom.fuse(outer.cut(channel)).clean()
    # Let the active finger leave the guide without fictitious obstruction.
    if port == "STOW":
        slot = blk(min(xc,xc+dx)-.31, max(xc,xc+dx)+.31,
                   y1-.1, y1+1.7, -.40, .40)
    else:
        slot = blk(min(xc,xc+dx)-.31, max(xc,xc+dx)+.31,
                   -.30, .30, lowz-.85, lowz+.01)
    body = body.cut(slot).clean()
    cover = blk(x0-1., x1+1., y0-1.65, y1+1.65, z1+gap, z1+gap+.8)
    # Two equal through-bores define a replaceable closure interface. The final
    # fastening method and preload are deliberately absent pending real loads.
    for y in (y0-.9, y1+.9):
        tool = cq.Solid.makeCylinder(.30, 8., cq.Vector((x0+x1)/2., y, lowz-1.), cq.Vector(0,0,1))
        body = body.cut(tool).clean()
        cover = cover.cut(tool).clean()
    if parked:
        slider = slider.translate((dx,0,0))
    return {"KEY_COUPON": key_coupon, "PAWL_SLIDER": slider,
            "GUIDE_CARTRIDGE": body, "REMOVABLE_COVER_UNFASTENED": cover}, dx


def save_assembly(parts, path):
    ass = cq.Assembly(name=path.stem)
    for name, sh in parts.items():
        validated_solid_volume(sh)
        ass.add(sh, name=name)
    ass.save(str(path), exportType="STEP")
    restored = cq.importers.importStep(str(path)).solids().vals()
    if len(restored) != len(parts):
        raise ValueError("STEP component count changed")
    volumes = sorted(validated_solid_volume(sh) for sh in restored)
    if any(abs(a-b) > 1e-6 for a,b in zip(volumes, sorted(sh.Volume() for sh in parts.values()))):
        raise ValueError("STEP volume changed")
    return {"path": str(path.relative_to(HERE)), "sha256": digest(path),
            "reimported_valid_positive_solids": len(restored),
            "CAD_geometry_only": True, "fixture_fabrication_go": False,
            "phone_manufacturing_go": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    # For reproducible reports that use relative paths, output stays in this
    # work item's folder; no source, baseline or other task directory is written.
    if args.out.resolve() != HERE:
        raise ValueError("Output must be this isolated engineering folder")
    before = inventory()
    (HERE/"cad").mkdir(exist_ok=True)
    A = cq.importers.importBrep(str(BASE/"cad/R37_A_R36_IDENTICAL.brep")).val()
    B = cq.importers.importBrep(str(BASE/"cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep")).val()
    structural_rows, tolerance_rows, fixture_rows, steps, rejected_play = [], [], [], [], []
    for port in ("STOW", "OPEN"):
        d = PORT_DATA[port]
        for side in "LR":
            for engaged in (False, True):
                p0 = (open_pawl(side, engaged) if port=="OPEN" else pawl(port,side,engaged))
                p = to_global(p0, port, *d["dock"])
                movedB = B.translate((0,d["dock"][0],d["dock"][1]-8.2))
                structural_rows.append({"port":port,"side":side,"engaged":engaged,
                    "pawl_volume_mm3":validated_solid_volume(p),
                    "pawl_A_overlap_mm3":checked_common(p,A),
                    "pawl_B_overlap_mm3":checked_common(p,movedB),
                    "pawl_A_exact_distance_mm":p.distance(A),
                    "pawl_B_exact_distance_mm":p.distance(movedB),
                    "no_material_connection_to_B_shell":p.distance(movedB)>1e-8,
                    "spring_guide_fastener_and_control_missing":True})
            key,p,parked_p = normalized_originals(port,side)
            # Unlike the legacy Boolean tree, test three-dimensional geometric
            # misalignment with direct OCC common on each unchanged solid.
            for width in (.02,.05,.10):
                for x,y,z in itertools.product((-width,0.,width),repeat=3):
                    pp=p.translate((x,y,z))
                    departure=(0.,.05,0.) if port=="STOW" else (0.,0.,-.05)
                    seated=checked_common(key,pp)
                    reversed_volume=checked_common(key,pp.translate(departure))
                    tolerance_rows.append({"port":port,"side":side,
                        "synthetic_each_axis_offset_mm":width,"offset_xyz_mm":[x,y,z],
                        "seated_clash_mm3":seated,
                        "reverse_0p05_clash_mm3":reversed_volume,
                        "nominal_clearance_geometry_lost":seated>1e-7,
                        "reverse_0p05_interception_lost":reversed_volume<=1e-7,
                        "supplier_GDT_or_probability":False})
        all_seated,all_parked,all_rejected = {},{},{}
        for side in "LR":
            parts,dx=fixture_parts(port,side)
            park_parts,_=fixture_parts(port,side,True)
            wide,_=fixture_parts(port,side,normal_guide_gap_mm=.15)
            drift=(0.,-.08,0.) if port=="STOW" else (0.,0.,.08)
            departure=(0.,.05,0.) if port=="STOW" else (0.,0.,-.05)
            shifted=wide["PAWL_SLIDER"].translate(drift)
            rejected_play.append({"port":port,"side":side,"normal_guide_gap_mm":.15,
                "unobstructed_rigid_drift_xyz_mm":list(drift),
                "guide_clash_mm3":checked_common(shifted,wide["GUIDE_CARTRIDGE"]),
                "cover_clash_mm3":checked_common(shifted,wide["REMOVABLE_COVER_UNFASTENED"]),
                "key_seated_clash_mm3":checked_common(shifted,wide["KEY_COUPON"]),
                "key_reverse_0p05_clash_mm3":checked_common(shifted.translate(departure),wide["KEY_COUPON"]),
                "capture_geometry_defeated_without_material_fracture":True})
            wide["PAWL_SLIDER"]=shifted
            all_rejected.update({side+"_"+n:sh for n,sh in wide.items()})
            all_seated.update({side+"_"+n:sh for n,sh in parts.items()})
            all_parked.update({side+"_"+n:sh for n,sh in park_parts.items()})
            # Test the entire linear slider interval against the actual new
            # guide and cover. This sampled check is NOT continuous proof.
            motion=[]
            for i in range(23):
                slide=parts["PAWL_SLIDER"].translate((dx*i/22.,0,0))
                motion.append({"index":i,"x_mm":dx*i/22.,
                    "guide_clash_mm3":checked_common(slide,parts["GUIDE_CARTRIDGE"]),
                    "cover_clash_mm3":checked_common(slide,parts["REMOVABLE_COVER_UNFASTENED"])})
            assembly_pairs=[]
            for first,second in itertools.combinations(parts,2):
                assembly_pairs.append({"parts":[first,second],
                    "checked_common_mm3":checked_common(parts[first],parts[second])})
            # An upper cover can be lowered onto the guide with sliders at either
            # stroke end. This is a straight sampled assembly path, not fastening.
            covers=[]
            for raise_z in (0.,.1,.5,1.,3.,10.):
                cover=parts["REMOVABLE_COVER_UNFASTENED"].translate((0,0,raise_z))
                covers.append({"raised_z_mm":raise_z,
                    "clashes_mm3":{n:checked_common(cover,sh) for n,sh in parts.items()
                        if n!="REMOVABLE_COVER_UNFASTENED"}})
            tight_shift=parts["PAWL_SLIDER"].translate(drift)
            guide_play=[]
            for xx,yy,zz in itertools.product((-.15,.15),(-.01,.01),(-.01,.01)):
                ps=parts["PAWL_SLIDER"].translate((xx,yy,zz))
                guide_play.append({"rigid_normal_play_xyz_mm":[xx,yy,zz],
                    "seated_key_common_mm3":checked_common(ps,parts["KEY_COUPON"]),
                    "reverse_0p05_key_common_mm3":checked_common(ps.translate(departure),parts["KEY_COUPON"])})
            fixture_rows.append({"port":port,"side":side,
                "synthetic_normal_guide_gap_mm":.01,
                "new_guide_blocks_previous_0p08_normal_drift_mm3":
                    checked_common(tight_shift,parts["GUIDE_CARTRIDGE"])+checked_common(tight_shift,parts["REMOVABLE_COVER_UNFASTENED"]),
                "independent_slide_travel_mm":dx,"sampled_slide_rows":motion,
                "nominal_assembly_pairs":assembly_pairs,"sampled_cover_assembly_rows":covers,
                "extreme_assumed_rigid_guide_play_rows":guide_play,
                "key_slider_seated_clash_mm3":checked_common(parts["KEY_COUPON"],parts["PAWL_SLIDER"]),
                "key_slider_parked_clash_mm3":checked_common(park_parts["KEY_COUPON"],park_parts["PAWL_SLIDER"]),
                "false_seat_with_key_absent_is_not_physically_vetoed":True,
                "spring_preload_N":None,"available_retraction_force_N":None,
                "force_limiter_upper_N":None,"capture_strength_min_N":None,
                "final_cover_fasteners_and_thread_engagement_unselected":True})
        for label,parts in (("SEATED",all_seated),("PARKED",all_parked)):
            steps.append(save_assembly(parts,HERE/"cad"/f"RESEARCH_1to1_{port}_{label}_fixture.step"))
        steps.append(save_assembly(all_rejected,HERE/"cad"/f"REJECTED_{port}_0p15_GUIDE_PLAY_CAPTURE_ESCAPE.step"))
        fail={}
        for side in "LR":
            parts,_=fixture_parts(port,side)
            # Hold the guided pawl fixed in the B frame and attempt the inverse
            # A/key motion; moving the whole slider across its guide would be
            # an unrelated cartridge collision witness.
            parts["KEY_COUPON"]=parts["KEY_COUPON"].translate((0,-.05,0) if port=="STOW" else (0,0,.05))
            fail.update({side+"_"+n:sh for n,sh in parts.items()})
        steps.append(save_assembly(fail,HERE/"cad"/f"FAILURE_WITNESS_{port}_FORCED_REVERSE_0p05.step"))
        no_keys={n:sh for n,sh in all_seated.items() if not n.endswith("KEY_COUPON")}
        steps.append(save_assembly(no_keys,HERE/"cad"/f"FAILURE_WITNESS_{port}_FALSE_SEAT_KEY_ABSENT.step"))
    after=inventory()
    if before!=after:
        raise ValueError("Protected baseline bytes changed")
    report={"revision":"2026-10-13 exact mechanical load-path audit and 1:1 bench CAD",
        "environment":{"host":platform.node(),"python":platform.python_version(),"cadquery":cq.__version__},
        "source_HEAD":"de3e982a04a3b4f62d0c301a9930aa9cd494cce5",
        "source_baseline_member_count":len(before),"protected_baseline_bytes_unchanged":True,
        "baseline_file_hashes":before,"phone_structural_rows":structural_rows,
        "synthetic_misalignment_rows":tolerance_rows,"research_fixture_rows":fixture_rows,
        "rejected_loose_guide_physical_geometry_witnesses":rejected_play,
        "active_contact_geometry_not_scaled":True,
        "research_fixture_geometry_added":["separate guided L/R slider cartridges","assembled upper cover geometry","replaceable original contact coupons","independent release grip and force-instrument clamp faces"],
        "nominal_geometric_bearing_area_mm2":{"STOW":.32*.5,"OPEN":.32*.3},
        "nominal_pressure_MPa_per_N_ignoring_edge_contact_bending_and_material":{"STOW":1/(.32*.5),"OPEN":1/(.32*.3)},
        "this_is_not_strength_FEA_or_allowable_load":True,
        "research_fixture_exported_steps":steps,
        "physical_blockers":["OEM shell, keys and actual mounting-root material/GDT",
            "manufacturable latch guide bearings and retained covers with measured preload",
            "independent return springs with measured force/stroke and breakage response",
            "passive absent-key and partial-seat release veto geometry and physical tests",
            "calibrated measured full-travel friction/FPC/OLED/actuator/jam forces",
            "weakest capture/key/OLED/FPC damage thresholds including impact/aging",
            "physical force limiter and fault injection on both sides/common causes"],
        "phone_integrated_mechanical_fix_implemented":False,
        "fixture_fabrication_go":False,"manufacturing_go":False}
    (HERE/"mechanical-closure-receipt.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    summary={k:report[k] for k in ("source_baseline_member_count","protected_baseline_bytes_unchanged","fixture_fabrication_go","manufacturing_go")}
    summary["misalignment_states"]=len(tolerance_rows)
    summary["fixture_STEPs"]=len(steps)
    summary["slider_sample_collision_count"]=sum(x["guide_clash_mm3"]>1e-7 or x["cover_clash_mm3"]>1e-7 for r in fixture_rows for x in r["sampled_slide_rows"])
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
