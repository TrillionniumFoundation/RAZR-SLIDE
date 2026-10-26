"""Bounded stdlib reads of the frozen, reviewed N5a scientific archive.

This module does no sparse solve, sparse matvec, field update or gate evaluation.
Numeric audit and independent readback share only typed, hash-checked input I/O.
"""
from __future__ import annotations
from array import array
import ast
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import stat
import struct
import sys
import zipfile

CHUNK = 1024 * 1024
ND = 344103
NF = 344097
ROW = 87824
ORIGINAL_FIXED_ORDER = (0, 1, 2, 13, 14, 8)
LIMIT = 1e-7
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
S4_TREE = "cdd9e2c41216201b6cd04dd610d45fde80499045"
ZIP_SHA = "46440881a264e6749d9c2ffd77676185bc8af219a536cb19e4b21132a1ee7a10"
ZIP_BYTES = 565978451
MANIFEST_SHA = "158b19afd6dd1a822d1609f954edb1b1eec6427460a32b9c2e7d7a91c484b9fa"
MANIFEST_BYTES = 323415
K_SHA = "80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb"
K_BYTES = 285135469
C_SHA = "9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f"
K_COMPONENTS = {
    "data": "c82485750257344a64e3f60cf4d03b826f38e067fc8e52e8a44a23e54bf058fc",
    "indices": "6d1119bbb2c8e32d79b4e6e84f773619263bb917ca417237e7c1831170d899f7",
    "indptr": "e49d96fff51663d4af693bd733515b5e7eb720a9d0e765d06e67db1c2581aa44",
    "shape": "c94902777e906187a797b881b94d59c7a86d40894ae865d5858367628eeece8e",
    "format": "cc0f38ba8c4acb904fd27131c2e8612a0832b2fc37fca5db2ccae35143f69db7",
}
KFF_COMPONENTS = {
    "data": "6e3a53865fa86c99aa1ce0feb3025a7b3b27a0a88406e83c2d471b441b6834fa",
    "indices": "0f03b4b97ec9ff2e47f1edb31799e927c1259377e317483ed635e1e7d8ded44d",
    "indptr": "50b9c2af8e95b8cb83abce3bfa697e90f9aa133a26a8defe6797b3de6ef3ac39",
}


class AuditGateError(ValueError):
    """The message is a fixed source-controlled gate code, never a runtime path."""
    pass


def require(condition, gate):
    if not condition:
        raise AuditGateError(gate)


def sha_file(path):
    h = hashlib.sha256()
    count = 0
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            count += len(b)
            h.update(b)
    return {"bytes": count, "sha256": h.hexdigest()}


def float_bits(value):
    return struct.pack(">d", value).hex()


def ulp_distance(a, b):
    def ordered(x):
        n = struct.unpack(">Q", struct.pack(">d", x))[0]
        return ((~n) & ((1 << 64) - 1)) if n >> 63 else (n | (1 << 63))
    return abs(ordered(a) - ordered(b))


def validate_original_domain(free, fixed):
    """Original fixed order is intentionally unsorted; free is its complement.

The frozen N1/N4b/N5a six-value member has SHA c5253eef... and literal order
0,1,2,13,14,8. Original force_maps returns loads['D'] unchanged; original free
construction is np.setdiff1d(np.arange(n), fixed), which sorts only the free set.
"""
    require(len(free) == NF and len(fixed) == 6, "original_domain_sizes")
    require(len(set(fixed)) == 6 and all(0 <= g < ND for g in fixed), "original_fixed_unique_and_in_range")
    require(tuple(fixed) == ORIGINAL_FIXED_ORDER, "original_fixed_order_preserved")
    excluded = set(fixed)
    require(list(free) == [g for g in range(ND) if g not in excluded], "original_free_exact_sorted_complement")
    require(ROW in free, "audit_row_is_original_free")


class HashingReader:
    def __init__(self, raw):
        self.raw, self.h, self.count = raw, hashlib.sha256(), 0

    def read(self, n):
        b = self.raw.read(n)
        self.h.update(b)
        self.count += len(b)
        return b


def read_npy(raw, max_elements=24_000_000):
    """Read a bounded unpickled C-order little-endian NPY with no NumPy import."""
    r = HashingReader(raw)
    require(r.read(6) == b"\x93NUMPY", "npy_magic")
    version = r.read(2)
    require(version in (b"\x01\x00", b"\x02\x00", b"\x03\x00"), "npy_version")
    width = 2 if version[0] == 1 else 4
    size_bytes = r.read(width)
    require(len(size_bytes) == width, "npy_header_size")
    nheader = int.from_bytes(size_bytes, "little")
    require(0 < nheader <= 65536, "npy_header_budget")
    encoded = r.read(nheader)
    require(len(encoded) == nheader, "npy_header_complete")
    header = ast.literal_eval(encoded.decode("utf8" if version[0] == 3 else "latin1"))
    require(set(header) == {"descr", "fortran_order", "shape"}, "npy_header_fields")
    require(header["fortran_order"] is False and isinstance(header["shape"], tuple), "npy_C_order")
    shape = header["shape"]
    require(all(type(n) is int and n >= 0 for n in shape), "npy_shape_integers")
    count = math.prod(shape)
    require(count <= max_elements, "npy_element_budget")
    descr = header["descr"]
    types = {"<f8": ("d", 8), "<i4": ("i", 4), "<i8": ("q", 8), "|S3": (None, 3)}
    require(descr in types and sys.byteorder == "little", "npy_dtype_and_endian")
    kind, width = types[descr]
    payload_sha = hashlib.sha256()
    remaining = count * width
    result = array(kind) if kind else bytearray()
    require(kind is None or result.itemsize == width, "native_array_itemsize")
    while remaining:
        block = r.read(min(CHUNK, remaining))
        require(block and len(block) % width == 0, "npy_payload_truncated_or_misaligned")
        remaining -= len(block)
        payload_sha.update(block)
        if kind:
            result.frombytes(block)
        else:
            result.extend(block)
    require(r.read(1) == b"", "npy_trailing_bytes")
    return result, {"shape": list(shape), "descr": descr, "payload_sha256": payload_sha.hexdigest(),
                    "sha256": r.h.hexdigest(), "bytes": r.count}


class Evidence:
    def __init__(self, archive, matrix):
        self.archive, self.matrix = Path(archive), Path(matrix)
        require(self.archive.is_file() and not self.archive.is_symlink(), "input_zip_regular")
        require(self.matrix.is_file() and not self.matrix.is_symlink(), "input_K_regular")
        require(sha_file(self.archive) == {"sha256": ZIP_SHA, "bytes": ZIP_BYTES}, "input_zip_exact")
        self.z = zipfile.ZipFile(self.archive)
        names = self.z.namelist()
        require(len(names) == len(set(names)) == 372, "input_zip_member_count")
        for i in self.z.infolist():
            p = PurePosixPath(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in i.filename
                    and not i.is_dir() and not stat.S_ISLNK(i.external_attr >> 16), "input_zip_paths")
        raw = self.z.read("EXPORT_MANIFEST.json")
        require(len(raw) == MANIFEST_BYTES and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA,
                "input_manifest_exact")
        self.manifest = json.loads(raw)
        self.members = self.manifest["exported_files"]
        require(len(self.members) == 371 and set(names) == set(self.members) | {"EXPORT_MANIFEST.json"},
                "input_zip_exact_member_set")
        require(self.manifest["raw_runtime_records_durable"] is False
                and self.manifest["complete_original_runtime_collection_exported"] is False
                and self.manifest["producer_originals_modified"] is False,
                "input_scientific_export_contract")
        self.used = {}

    def check(self, name, size, digest):
        require(self.members.get(name) == {"bytes": size, "sha256": digest}, "used_member_exact")
        self.used[name] = {"bytes": size, "sha256": digest}

    def byte_check(self, name):
        h, count = hashlib.sha256(), 0
        with self.z.open(name) as f:
            for b in iter(lambda: f.read(CHUNK), b""):
                count += len(b)
                h.update(b)
        self.check(name, count, h.hexdigest())
        return self.used[name]

    def read_json(self, name):
        require(self.members[name]["bytes"] < 2 * CHUNK, "json_input_budget")
        raw = self.z.read(name)
        self.check(name, len(raw), hashlib.sha256(raw).hexdigest())
        return json.loads(raw)

    def npy(self, name, shape=None, descr="<f8"):
        with self.z.open(name) as f:
            value, meta = read_npy(f)
        self.check(name, meta["bytes"], meta["sha256"])
        require(meta["descr"] == descr and (shape is None or meta["shape"] == list(shape)), "npy_expected_layout")
        return value

    def original_matrix(self):
        identity = sha_file(self.matrix)
        require(identity == {"bytes": K_BYTES, "sha256": K_SHA}, "original_K_file_exact")
        self.check("volume/panel/level-2/K.npz", identity["bytes"], identity["sha256"])
        result, meta = {}, {}
        with zipfile.ZipFile(self.matrix) as z:
            require(set(z.namelist()) == {k + ".npy" for k in K_COMPONENTS}, "original_K_npz_layout")
            for key in ("shape", "format", "indptr", "indices", "data"):
                with z.open(key + ".npy") as f:
                    value, m = read_npy(f)
                require(m["payload_sha256"] == K_COMPONENTS[key], "original_K_component_exact")
                result[key], meta[key] = value, m
        require(list(result["shape"]) == [ND, ND] and result["format"] == b"csc", "original_K_CSC_shape")
        require(len(result["indices"]) == len(result["data"]) == 23646483
                and len(result["indptr"]) == ND + 1, "original_K_component_lengths")
        require(meta["data"]["descr"] == "<f8" and meta["indices"]["descr"] == "<i4"
                and meta["indptr"]["descr"] == "<i4", "original_K_component_dtypes")
        require(result["indptr"][0] == 0 and result["indptr"][-1] == 23646483
                and all(a <= b for a, b in zip(result["indptr"], result["indptr"][1:])), "CSC_indptr_valid")
        return result, meta

    def domain(self):
        free = self.npy("probe-N5/free-original-DOFs.npy", (NF,), "<i8")
        fixed = self.npy("probe-N5/fixed-original-DOFs.npy", (6,), "<i8")
        validate_original_domain(free, fixed)
        self.byte_check("probe-N5/C.npz")
        require(self.used["probe-N5/C.npz"]["sha256"] == C_SHA, "original_C_exact")
        self.byte_check("probe-N5/points.json")
        self.byte_check("probe-N5/five-probe-directions.npy")
        return free, fixed

    def close(self):
        self.z.close()
