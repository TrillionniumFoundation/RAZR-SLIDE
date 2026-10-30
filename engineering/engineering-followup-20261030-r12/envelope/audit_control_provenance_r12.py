"""Bind the new exact filling controls to the retained original R11 counterexample."""
import argparse
import copy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import time
import traceback


def identity(path):
    p = Path(path)
    return {"path": str(p.resolve()), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def decode(value):
    if isinstance(value, dict) and set(value) == {"numerator", "denominator"}:
        return F(value["numerator"], value["denominator"])
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--producer", type=Path, required=True)
    p.add_argument("--reader", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    report = {"schema": "razr-r12-independent-original-counterexample-control-binding-v1",
              "completed": False, "native_calls": 0, "negative_controls": [],
              "full_continuous_G2": False, "source": identity(__file__)}
    try:
        import check_filling_r12 as check
        original_path = args.inputs / "prior-hollow-shell-negative-control.json"
        original = json.loads(original_path.read_text())
        manifest = json.loads((args.inputs / "manifest.json").read_text())
        entry = next(x for x in manifest["files"].values() if x["relative"] == original_path.name)
        actual = identity(original_path)
        check.need(all(entry[k] == actual[k] for k in ("bytes", "sha256")), "exact prior counterexample bytes")
        payload_path = args.producer / "certificates.json"
        payload = json.loads(payload_path.read_text())
        reader = json.loads((args.reader / "report.json").read_text())
        check.need(reader["completed"] and reader["recorded_budget_passed"], "completed actual native reader")
        controls = {c["name"]:c for c in payload["controls"]}
        shells = [decode(r["bounds"]) for r in original["carrier_slabs"]]
        fixed = decode(original["fixed_body"])
        source = decode(original["source_material"])
        check.need(source == [[F(0),F(1)]]*3, "actual original source cube")
        check.need(decode(original["omitted_volume"]) == F(1,8), "actual original omitted interior volume")
        check.need(decode(original["actual_source_fixed_intersection_volume"]) == F(1,64), "actual original missed intersection")

        def binding(proof,expected):
            actual = [[list(map(F,iv)) for iv in B] for B in proof["boundary_boxes_exact"]]
            check.need(actual == expected, "entire control geometry differs from original source-derived boxes")
            return check.check_completion(proof)

        original_control = controls["original_hollow_shell"]["certificate"]
        first = binding(original_control,shells)
        check.need(check.carrier_intersection_volume(original_control,[[str(x) for x in iv] for iv in fixed]) == F(1,64), "restored exact original fixed-body intersection")
        thin = copy.deepcopy(shells)
        for B in thin:
            B[2] = [v/F(1<<80) for v in B[2]]
        second = binding(controls["positive_thin_shell"]["certificate"],thin)
        touching = [[[F(0),F(1)],[F(0),F(1)],[F(0),F(1)]],
                    [[F(2),F(3)],[F(1),F(2)],[F(0),F(1)]]]
        third = binding(controls["touching_projection_singleton"]["certificate"],touching)
        for name,changed,expected in [
            ("replace_original_boundary_slab",copy.deepcopy(original_control),shells),
            ("replace_positive_thin_input_by_zero",copy.deepcopy(controls["positive_thin_shell"]["certificate"]),thin)]:
            if name.startswith("replace_original"):
                changed["boundary_boxes_exact"][0][0][1] = "1/8"
            else:
                changed["boundary_boxes_exact"][0][2][1] = changed["boundary_boxes_exact"][0][2][0]
            path = args.output/(name+".json")
            path.write_text(json.dumps(changed,indent=2)+"\n")
            try:
                binding(changed,expected)
            except ValueError as exc:
                report["negative_controls"].append({"name":name,"rejected":True,"reason":str(exc),"input":identity(path)})
            else:
                raise ValueError("control source substitution accepted")
        report.update(original_counterexample=identity(original_path),new_certificate=identity(payload_path),
                      prior_completed_native_reader=identity(args.reader/"report.json"),
                      checker=identity(check.__file__),original_control=first,thin_control=second,touching_control=third,
                      original_control_source_identity_verified=True,completed=True)
    except Exception as exc:
        report["failure"] = {"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    report["seconds"] = time.monotonic()-start
    (args.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report.get(k) for k in ("completed","seconds","failure")}))
    if not report["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
