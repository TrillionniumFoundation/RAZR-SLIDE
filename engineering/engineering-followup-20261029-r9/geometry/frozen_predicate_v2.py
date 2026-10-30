"""Memoize only predicates of frozen participants; preserve original Common.

Each complete original participant is validated using the original `single`
predicate before its AddOptimal bounds are cached. Booleans receive explicit
deep geometry copies (`BRepBuilderAPI_Copy(..., True, False)`). Original BREP
bytes are checked again after the whole matrix; no original shape is passed
to a Boolean by this module. A positive axis gap therefore proves exactly the
same original zero-Common branch for the same frozen participants. Every
nonseparated pair still executes the original strict_common implementation.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import math


def fingerprint(shape):
    stream = io.BytesIO()
    if shape.exportBrep(stream) is not True:
        raise ValueError("native BREP stream serialization failed")
    data = stream.getvalue()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class FrozenBodies:
    def __init__(self, parts, p):
        self.parts = parts
        self.p = p
        self.records = {}
        copy_source = inspect.getsource(type(next(iter(parts.values()))).copy)
        if "BRepBuilderAPI_Copy(self.wrapped, True, mesh)" not in copy_source:
            raise ValueError("unrecognized deep geometry copy implementation")
        self.copy_source = copy_source
        for name, body in sorted(parts.items()):
            p.single(body)
            bounds = p.bounds(body)
            if not all(math.isfinite(x) for x in bounds):
                raise ValueError("nonfinite frozen participant bounds")
            self.records[name] = {"BREP": fingerprint(body), "bounds_mm": bounds,
                                  "signed_volume_mm3": p.volume(body),
                                  "original_single_predicate_passed": True}

    def pair(self, left, right):
        a = self.records[left]["bounds_mm"]
        b = self.records[right]["bounds_mm"]
        gap = max(max(a[2*i] - b[2*i+1], b[2*i] - a[2*i+1]) for i in range(3))
        if gap > 0:
            return {"common_mm3": 0.0, "method": "positive_axis_gap", "axis_gap_lower_mm": gap}
        return self.p.strict_common(self.parts[left].copy(mesh=False), self.parts[right].copy(mesh=False))

    def check_unchanged(self):
        rows = {name: {"before": self.records[name]["BREP"], "after": fingerprint(shape)}
                for name, shape in sorted(self.parts.items())}
        for row in rows.values():
            row["unchanged"] = row["before"] == row["after"]
        return {"all_original_BREP_bytes_unchanged": all(row["unchanged"] for row in rows.values()),
                "bodies": rows}
