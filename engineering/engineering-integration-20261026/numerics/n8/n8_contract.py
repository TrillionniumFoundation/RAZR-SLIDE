"""N8 frozen identities and bounded file I/O; no numerical acceptance code."""
from pathlib import Path
import hashlib
import json
import os
import struct

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
S4_TREE = "cdd9e2c41216201b6cd04dd610d45fde80499045"
ND, NF, NP = 344103, 344097, 5
FIXED = (0, 1, 2, 13, 14, 8)
LIMIT = 1e-7
MAX_FULL = 96
ANCHOR_SEED_DOF = 59009
BASE_FIELDS_PREFIX = "frozen/probe-N7/final"
BASE_FIELD_SHA = "d28f4626b3985612d14ab3b894e70b93f930c251f0239e8256593c979d4788b4"
MAX_SCALAR = 8192
MAX_ROW_SUPPORT = 256
MAX_CACHE_ROWS = 4096
MAX_EXACT_TERMS = 1000000
MAX_READER_EXACT_TERMS = 2000000
MAX_CACHE_BYTES = 16 * 1024**2
MAX_FRACTION_BITS = 4096
AS_BYTES = 4831838208
OUTPUT_BYTES = 1610612736
RESERVE_BYTES = 500 * 1024**2
WALL_SECONDS = 180
CHUNK = 1024**2
ZIP_BYTES = 307198106
ZIP_SHA = "2541e06e5c5dcc6a1797e5c85cde410a35056e4e23cae22b2ef9bb7759d85a1c"
MANIFEST_BYTES = 167280
MANIFEST_SHA = "f911ecc8f08fe78526af1be49ea2292f94ee49e64789f514359196d7875d01b2"
K_SHA = "80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb"
C_SHA = "9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f"
KFF_SHA = {
 "data": "6e3a53865fa86c99aa1ce0feb3025a7b3b27a0a88406e83c2d471b441b6834fa",
 "indices": "0f03b4b97ec9ff2e47f1edb31799e927c1259377e317483ed635e1e7d8ded44d",
 "indptr": "50b9c2af8e95b8cb83abce3bfa697e90f9aa133a26a8defe6797b3de6ef3ac39",
}
POINT_SOURCE = "engineering/nested-contact-20261017/level-2/case-6/report.json.gz"
POINT_SOURCE_SHA = "3e0177c8405ddeb27af68325ea65793d5eedb8a5aaf3680a3bfc5b1305fc2d06"
HELPER = "engineering/engineering-integration-20261025/numerics/probe_original_actions.py"
HELPER_SHA = "1f8334a1dda34a4101662ccdbd14c2db0bb77b8a3e080b5f5ec74d918955a2c6"

class GateError(ValueError):
    """Only source-controlled gate codes; never runtime paths."""
class CapacityStop(GateError):
    pass

def require(condition, code):
    if not condition:
        raise GateError(code)

def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()

def bits(x):
    return struct.pack(">d", float(x)).hex()

def load_frozen_contract():
    p = Path(__file__).with_name("N8_FROZEN_INPUTS.json")
    c = json.loads(p.read_text())
    require(c["source_ZIP_sha256"] == ZIP_SHA and c["source_ZIP_bytes"] == ZIP_BYTES
            and c["source_manifest_sha256"] == MANIFEST_SHA
            and c["functional_source_commit"] == S4
            and c["functional_source_tree"] == S4_TREE
            and c["starting_probe0_field_sha256"] == BASE_FIELD_SHA
            and c["members"]["probe-N7/final/probe-0-field.npy"]["sha256"] == BASE_FIELD_SHA,
            "frozen_input_contract_identity")
    return c

def verify_frozen_files(case):
    c = load_frozen_contract()
    observed = {}
    for name, identity in c["members"].items():
        p = case / "frozen" / name
        require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(case.resolve()),
                "frozen_input_regular_relative_file")
        actual = {"bytes": p.stat().st_size, "sha256": sha_file(p)}
        require(actual == identity, "frozen_input_byte_identity")
        observed[name] = actual
    return observed

def payload_bytes(case):
    return sum(p.stat().st_size for p in case.rglob("*") if p.is_file())

def reserve(case, additional):
    fs = os.statvfs(case)
    if fs.f_bavail * fs.f_frsize < RESERVE_BYTES + additional:
        raise CapacityStop("original_500MiB_filesystem_reserve")
    if payload_bytes(case) + additional > OUTPUT_BYTES:
        raise CapacityStop("original_1_5GiB_task_payload")

def write_json(path, value, case=None):
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    if case is not None:
        reserve(case, len(data))
    path.parent.mkdir(parents=True, exist_ok=True)
    t = path.with_name(path.name + ".writing")
    with t.open("wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(t, path)
