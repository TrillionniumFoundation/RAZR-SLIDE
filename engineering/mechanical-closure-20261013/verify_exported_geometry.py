#!/usr/bin/env python3
"""Independent STEP check: identify gauge bodies by bounds, not builder imports.

Import the exported geometry and compare its actual key/pawl common against
the independent rectangular bearing-face formula. No source builder is run.
"""
import hashlib
import itertools
import json
import platform
import sys
from pathlib import Path

import cadquery as cq

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"cad-review-20261013"))
from occ_signed_volume import common, validated_solid_volume


def overlap(a,b):
    return common(a,b)["checked_volume_mm3"]


def main():
    report=json.loads((HERE/"mechanical-closure-receipt.json").read_text())
    rows=[]
    for item in report["research_fixture_exported_steps"]:
        path=HERE/item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item["sha256"]:
            raise ValueError("STEP bytes changed")
        solids=cq.importers.importStep(str(path)).solids().vals()
        if len(solids)!=item["reimported_valid_positive_solids"]:
            raise ValueError("STEP count changed")
        for sh in solids:
            validated_solid_volume(sh)
        port="STOW" if "STOW" in path.name else "OPEN"
        keys=[s for s in solids if (s.BoundingBox().zmax>6.9 if port=="STOW" else s.BoundingBox().zmin< -7.)]
        # Gauge slider length is 4 mm along X, and its top face remains at the
        # independently measured inserted stroke level, unlike the guide/cover.
        top=2.75 if port=="STOW" else 5.4
        if "REJECTED" in path.name and port=="OPEN":
            top+=.08  # The explicit rejected witness raises the slider bodily.
        sliders=[s for s in solids if abs(s.BoundingBox().xlen-4.)<1e-6
                 and abs(s.BoundingBox().zmax-top)<1e-6]
        if len(sliders)!=2:
            raise ValueError(path.name+": cannot identify independent slider bodies")
        if "KEY_ABSENT" in path.name:
            if keys:
                raise ValueError("Absent-key witness contains a key")
            rows.append({"path":item["path"],"keys":0,"guided_sliders":2,
                "this_geometry_has_no_passive_absent_key_inhibit":True})
            continue
        if len(keys)!=2:
            raise ValueError("Cannot identify independent key coupons")
        pairs=[]
        for key in keys:
            slide=next(s for s in sliders if (s.Center().x>0)==(key.Center().x>0))
            actual=overlap(key,slide)
            # Nominal rectangular contact areas: 0.32*0.5 and 0.32*0.3 mm².
            # At forced reverse 0.05 mm, original 0.03 mm gap closes and the
            # 0.02 mm interference gives the independently expected volume.
            expected=(.32*(.5 if port=="STOW" else .3)*.02
                      if "FORCED_REVERSE" in path.name else 0.)
            if abs(actual-expected)>1e-7:
                raise ValueError(f"{path.name}: contact formula mismatch {actual} vs {expected}")
            play=[]
            if "SEATED_fixture" in path.name:
                reverse=(0,.05,0) if port=="STOW" else (0,0,-.05)
                for x,y,z in itertools.product((-.15,.15),(-.01,.01),(-.01,.01)):
                    moved=slide.translate((x,y,z))
                    seated=overlap(key,moved)
                    withdraw=overlap(key,moved.translate(reverse))
                    if seated>1e-7 or withdraw<=1e-7:
                        raise ValueError("Tight research fixture loses nominal geometric interception")
                    play.append({"offset_xyz_mm":[x,y,z],"seated_mm3":seated,
                        "forced_reverse_mm3":withdraw})
            pairs.append({"side":"R" if key.Center().x>0 else "L",
                "actual_key_slider_common_mm3":actual,
                "independent_rectangular_face_expected_mm3":expected,
                "assumed_rigid_guide_play_rows":play})
        rows.append({"path":item["path"],"keys":2,"guided_sliders":2,"pairs":pairs})
    result={"environment":{"host":platform.node(),"python":platform.python_version(),"cadquery":cq.__version__},
        "independent_exported_STEP_checks":rows,
        "all_exported_checks_passed":True,
        "geometry_is_not_material_strength_or_passive_fault_closure":True,
        "fixture_fabrication_go":False,"manufacturing_go":False}
    (HERE/"independent-exported-geometry-check.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"STEPs_checked":len(rows),"all_exported_checks_passed":True,
        "fixture_fabrication_go":False,"manufacturing_go":False},indent=2))


if __name__=="__main__":
    main()
