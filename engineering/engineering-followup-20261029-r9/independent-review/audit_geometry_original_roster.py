"""Read-only independent audit of original state/input identities and counts.

No CAD modules are imported. This does not mark any unexecuted pose complete.
"""
import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

HERE = Path(__file__).resolve().parent
GEO = HERE.parent / "geometry"
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digests(path):
    path = Path(path)
    size = path.stat().st_size
    sha256 = hashlib.sha256()
    gitblob = hashlib.sha1(("blob " + str(size) + "\0").encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(chunk)
            gitblob.update(chunk)
    return {"bytes": size, "sha256": sha256.hexdigest()}, gitblob.hexdigest()


def identity(path):
    return digests(path)[0]


def assignments(path):
    tree = ast.parse(Path(path).read_text())
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}


def main(args):
    source_catalog_path = GEO / "producer-attempt1/S4_SOURCE_CATALOG.json"
    source_catalog = json.loads(source_catalog_path.read_text())
    git_tree = subprocess.check_output(["git", "-C", str(args.git_repo), "rev-parse", S4 + "^{tree}"], text=True).strip()
    tree_bytes = subprocess.check_output(["git", "-C", str(args.git_repo), "ls-tree", "-rz", S4])
    tree_entries = {}
    for row in tree_bytes.split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        if kind == "blob":
            tree_entries[name.decode()] = blob
    count = total_bytes = 0
    for relative, expected in source_catalog.items():
        observed, git_blob = digests(args.s4_root / relative)
        need(observed == expected, "original S4 input bytes changed: " + relative)
        need(tree_entries.get(relative) == git_blob, "exact S4 Git blob changed: " + relative)
        count += 1
        total_bytes += observed["bytes"]
    need(count == 973, "complete archived S4 input census")
    helper_path = GEO / "producer-attempt1/ORIGINAL_HELPERS_CATALOG.json"
    helpers = json.loads(helper_path.read_text())
    for relative, expected in helpers.items():
        need(identity(GEO / "source-originals" / relative) == expected, "original helper bytes changed: " + relative)

    state_paths = [GEO / "source-originals/full_stop_states.py",
                   args.git_repo / "engineering/engineering-next-20261026/panel-key-stop-k3full/full_stop_states.py",
                   args.near_root / "engineering/source/k3full/full_stop_states.py"]
    need(all(p.read_bytes() == state_paths[0].read_bytes() for p in state_paths), "registered ten-state source bytes differ")
    values = assignments(state_paths[0])
    states, ends = values["STATES"], values["EXPECTED_CONTACT_ENDS"]
    need(len(states) == len(ends) == 10 and set(states) == set(ends), "complete ten-state roster")
    K_tree = ast.parse((args.s4_root / "integration/verify_cam_coupling.py").read_text())
    K_expr = next(n.value for n in K_tree.body if isinstance(n, ast.Assign) and
                  any(isinstance(t, ast.Name) and t.id == "K" for t in n.targets))
    need(isinstance(K_expr, ast.BinOp) and isinstance(K_expr.op, ast.Div), "original K operation")
    K = ast.literal_eval(K_expr.left) / ast.literal_eval(K_expr.right)
    roster = []
    for name, spec in states.items():
        bodies = spec["expected_bodies"]
        need(bodies == (161 if name == "open_installed" else 154), "original per-state body count")
        q = [K * spec["slide"] + offset for offset in spec["key_offsets"]]
        expected_q = spec["actual_binary64_q_from_declared_factory_inputs"]
        need(all(struct.pack(">d", a) == struct.pack(">d", b) for a, b in zip(q, expected_q)),
             "original binary64 state q changed: " + name)
        roster.append({"state": name, "unchanged_original_state_record": spec,
                       "unchanged_expected_contacts": ends[name], "expected_participant_count": bodies,
                       "required_complete_unordered_pairs": bodies * (bodies - 1) // 2,
                       "recomputed_q_binary64_hex": [x.hex() for x in q]})
    need(sum(x["required_complete_unordered_pairs"] for x in roster) == 118909, "ten-state complete pair total")

    legacy = []
    for pose in ("stow_tabs_3", "predock"):
        root = args.near_root / ("engineering/prerequisite-" + pose) / "factory/worker"
        path = root / "report.engineering.json"
        doc = json.loads(path.read_text())
        record = doc["engineering_record"]
        names = record["participant_names"]
        pairs = record["pairs"]
        roster_pairs = [(r["a"], r["b"]) for r in pairs]
        need(len(names) == 154 and len(pairs) == 153, "actual historical panel-only census")
        need(all("A_BACK_PANEL" in p for p in roster_pairs), "historical pairs are only panel-vs-other")
        need(len(set(roster_pairs)) == 153, "historical unique panel pairs")
        need(set(roster_pairs) != set(itertools.combinations(sorted(names), 2)), "panel-only must not satisfy full matrix")
        journal_path = root / "pairs.jsonl"
        journal_lines = sum(1 for _ in journal_path.open())
        legacy.append({"state": pose, "report": identity(path), "pair_journal": identity(journal_path),
                       "participant_count": 154, "actual_panel_only_pairs": 153,
                       "journal_event_lines": journal_lines, "full_matrix_required_pairs": 11781,
                       "stored_finite_pose_clear": record["finite_pose_clear"],
                       "counts_as_full_matrix_completion": False})
    result = {"schema": "razr-r9-independent-original-ten-state-roster-and-input-audit-v1", "completed": True,
              "audit_source": identity(__file__), "original_S4_commit": S4, "original_S4_tree": git_tree,
              "archived_S4_files_rehashed_and_Git_blob_checked": count,
              "archived_S4_total_bytes_rehashed": total_bytes, "S4_catalog": identity(source_catalog_path),
              "original_helper_files_rehashed": len(helpers), "helper_catalog": identity(helper_path),
              "state_source_copies": [{"path": str(p), **identity(p)} for p in state_paths],
              "all_three_registered_roster_copies_identical": True,
              "full_original_roster": roster, "expected_full_matrix_pair_total": 118909,
              "historical_panel_only_matrices": legacy,
              "coverage_is_not_execution": True, "new_CAD_arithmetic_performed": False,
              "all_ten_actual_executions_qualified_by_this_roster_audit": False,
              "scope": {"original_input_identity_and_required_count_only": True,
                        "full_continuous_G2": False, "physical_allowed_domain_proved": False,
                        "physical_qualification": False, "manufacturing_go": False}}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"completed": True, "S4_files": count, "helpers": len(helpers),
                      "original_states": 10, "required_full_pairs": 118909,
                      "legacy_panel_only_pairs_per_pose": 153, "CAD_executed": False}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--s4-root", type=Path, required=True)
    p.add_argument("--git-repo", type=Path, required=True)
    p.add_argument("--near-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
