#!/usr/bin/env python3
"""Separate-process OCP readback of original finite materials and saved Commons.

No producer implementation is imported. This uses the same OCCT kernel and is
an independent execution/readback, not an independent geometry engine.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS_Shape, TopoDS_Iterator
from OCP.gp import gp_Pnt


def ident(path):
    b = path.read_bytes()
    return {"name": path.name, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def read(path):
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
        raise ValueError(f"BREP read failed: {path}")
    return shape


def mass(shape):
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    return properties.Mass()


def children(shape):
    it = TopoDS_Iterator(shape)
    items = []
    while it.More():
        items.append(it.Value())
        it.Next()
    return items


def mapped(shape, kind):
    mapping = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, mapping)
    return [mapping.FindKey(index) for index in range(1, mapping.Extent()+1)]


def kind_name(shape):
    return str(shape.ShapeType()).split("_")[-1].title()


def signature(shape):
    solids = mapped(shape, TopAbs_SOLID)
    return {
        "shape_type": kind_name(shape), "is_valid": BRepCheck_Analyzer(shape).IsValid(),
        "signed_volume_mm3": mass(shape), "solid_count": len(solids),
        "solid_signed_volumes_mm3": [mass(s) for s in solids],
        "top_level_children_types": [kind_name(s) for s in children(shape)],
        "face_count": len(mapped(shape, TopAbs_FACE)),
        "edge_count": len(mapped(shape, TopAbs_EDGE)),
        "vertex_count": len(mapped(shape, TopAbs_VERTEX)),
    }


def common(a,b):
    op = BRepAlgoAPI_Common(a,b)
    op.Build()
    if not op.IsDone():
        raise ValueError("Common did not finish")
    return op.Shape(), {"is_done": op.IsDone(), "fuzzy_value_mm": op.FuzzyValue(),
                        "run_parallel": op.RunParallel(), "non_destructive": op.NonDestructive()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-case", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    begin = time.monotonic()
    original_result = args.source_case / "result.json"
    producer_path = args.producer / "PRODUCER_REPORT.json"
    producer = json.loads(producer_path.read_text())
    original = json.loads(original_result.read_text())
    assert producer["pid"] != os.getpid()
    assert producer["source_result_identity"] == ident(original_result)
    assert producer["original_target"] == original["target"]
    sources = {}
    shapes = {}
    for mid in (1,2,3,4):
        name = f"material-{mid:03d}.brep"
        path = args.source_case / name
        sources[str(mid)] = ident(path)
        original_id = next(m["exports"]["brep"] for m in original["material_exports"] if m["id"] == mid)
        assert sources[str(mid)]["sha256"] == original_id["sha256"]
        assert sources[str(mid)]["bytes"] == original_id["bytes"]
        assert sources[str(mid)] == producer["source_material_identities"][str(mid)]
        shapes[mid] = read(path)
        assert BRepCheck_Analyzer(shapes[mid]).IsValid()
        assert all(mass(s)>0 for s in mapped(shapes[mid],TopAbs_SOLID))
    # Independently bind the two saved exception-local frames from original traces.
    for frame, moved_id, fixed_id in ((1,3,2),(2,4,1)):
        source = next(m for m in original["material_exports"] if m["id"]==moved_id)
        assert any(r.get("role")=="exception-local-shape" and r.get("native_reference_frame_index")==frame for r in source["references"])
        fixed_source = next(m for m in original["material_exports"] if m["id"]==fixed_id)
        assert any(r.get("role")=="exception-local-b" and r.get("native_reference_frame_index")==frame for r in fixed_source["references"])
    # Real analytic controls exercise positive, empty and signed-orientation paths.
    box = BRepPrimAPI_MakeBox(1.0,1.0,1.0).Shape()
    overlap = BRepPrimAPI_MakeBox(gp_Pnt(0.5,0,0),1.0,1.0,1.0).Shape()
    away = BRepPrimAPI_MakeBox(gp_Pnt(2.0,0,0),1.0,1.0,1.0).Shape()
    positive,_ = common(box,overlap)
    empty,_ = common(box,away)
    controls = {
        "positive_half_cube": {"expected_volume_mm3": 0.5, "actual": signature(positive)},
        "separated_cubes": {"expected_empty": True, "actual": signature(empty)},
        "orientation": {"forward_signed_volume_mm3": mass(box), "reversed_signed_volume_mm3": mass(box.Reversed())},
    }
    assert abs(mass(positive)-0.5)<=1e-7
    assert not children(empty) and mass(empty)==0
    assert mass(box)>0 and mass(box.Reversed())<0
    for name, shape in (("positive-half-cube",positive),("separated-cubes",empty),("reversed-unit-cube",box.Reversed())):
        assert BRepTools.Write_s(shape,str(args.output/(name+".brep")))
    evaluations=[]
    for frame, a_id,b_id in ((1,3,2),(2,4,1)):
        for reverse in (False,True):
            aa,bb=(b_id,a_id) if reverse else (a_id,b_id)
            label=f"frame-{frame}-{'reverse' if reverse else 'forward'}"
            old=next(e for e in producer["evaluations"] if e["label"]==label)
            assert old["a_material_id"]==aa and old["b_material_id"]==bb and not old["evaluation_failed"]
            saved_path=args.producer/old["common_artifact"]["name"]
            assert ident(saved_path)==old["common_artifact"]
            saved=read(saved_path)
            recomputed,settings=common(shapes[aa],shapes[bb])
            saved_sig=signature(saved)
            new_sig=signature(recomputed)
            same=saved_sig==new_sig==old["common"]
            assert BRepTools.Write_s(recomputed,str(args.output/(label+"-recomputed-common.brep")))
            evaluations.append({
                "label":label,"frame":frame,"a_material_id":aa,"b_material_id":bb,
                "producer_saved_common_identity":ident(saved_path),
                "readback":saved_sig,"recomputed":new_sig,
                "producer_saved_and_recomputed_signatures_exactly_equal":same,
                "settings":settings,
                "signed_volume_within_input_upper_bound":0<=new_sig["signed_volume_mm3"]<=min(mass(shapes[aa]),mass(shapes[bb])),
                "strictly_above_original_1e_minus7_volume_gate":new_sig["signed_volume_mm3"]>1e-7,
            })
    assert all(e["producer_saved_and_recomputed_signatures_exactly_equal"] and e["signed_volume_within_input_upper_bound"] for e in evaluations)
    assert all(ident(args.source_case/f"material-{int(mid):03d}.brep")==v for mid,v in sources.items())
    report={
        "schema":"razr-r8-original-saved-pair-common-independent-process-readback-v1",
        "recorded_utc":datetime.now(timezone.utc).isoformat(),
        "pid":os.getpid(),"producer_pid":producer["pid"],
        "executable":sys.executable,"cadquery_ocp_version":importlib.metadata.version("cadquery-ocp"),
        "reader_source":ident(Path(__file__)),
        "producer_report":ident(producer_path),"original_result":ident(original_result),
        "source_material_identities":sources,
        "original_target":original["target"],
        "input_signatures_raw_OCP":{str(mid):signature(shape) for mid,shape in shapes.items()},
        "analytic_controls":controls,"evaluations":evaluations,
        "saved_common_files_reopened":4,"new_original_pair_Common_calls":4,
        "new_analytic_control_Common_calls":2,
        "passed":True,"same_CAD_kernel":True,
        "separate_process":True,"producer_implementation_imported":False,"cadquery_imported":False,
        "source_material_bytes_unchanged":True,
        "original_result_rewritten":False,"full_continuous_G2":False,
        "physical_qualification":False,"new_K1_K3_factory_execution":False,
        "seconds":time.monotonic()-begin,
        "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    }
    (args.output/"INDEPENDENT_PROCESS_READBACK.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"case":original["target"]["case_id"],"raw_pair_calls":4,"analytic_controls":3,"seconds":report["seconds"]}))


if __name__=="__main__":
    main()
