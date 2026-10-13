"""Immutable-pose cache preserving participant validation before every prune.

Only this checker owns these inputs. Every import/translation is validated as
one finite positive solid before its AABB is inspected; possible intersections
always execute real OCC common and reject negative raw signed volumes.
"""
import math
from types import MappingProxyType
from occ_signed_volume import check_common_volume, validated_solid_volume


class CheckedBody:
    __slots__ = ("shape", "volume", "bounds", "_frozen")

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise TypeError("Validated pose attributes are immutable")
        object.__setattr__(self, name, value)

    def __init__(self, shape):
        self.volume = validated_solid_volume(shape)
        self.shape = shape
        b = shape.BoundingBox()
        self.bounds = MappingProxyType({a: (float(getattr(b, a + "min")), float(getattr(b, a + "max"))) for a in "xyz"})
        if not all(math.isfinite(v) for interval in self.bounds.values() for v in interval):
            raise ValueError("Nonfinite actual solid bounds")
        self._frozen = True

    def translate(self, vector):
        return CheckedBody(self.shape.translate(vector))


class Checker:
    def __init__(self):
        self.actual_occ_common_count = 0
        self.validated_actual_AABB_proven_zero_count = 0

    def common(self, first, second):
        if not isinstance(first, CheckedBody) or not isinstance(second, CheckedBody):
            raise TypeError("Only strictly validated immutable poses may enter this checker")
        if any(min(first.bounds[a][1], second.bounds[a][1]) <= max(first.bounds[a][0], second.bounds[a][0]) for a in "xyz"):
            self.validated_actual_AABB_proven_zero_count += 1
            return {"raw_signed_common_mm3": None, "checked_common_mm3": 0.0,
                    "proof": "validated_actual_solid_AABB_nonpositive_material_overlap"}
        self.actual_occ_common_count += 1
        intersection = first.shape.intersect(second.shape)
        if not intersection.isValid():
            raise ValueError("Invalid actual OCC common")
        raw = float(intersection.Volume())
        value = check_common_volume(raw, first.volume, second.volume)
        return {"raw_signed_common_mm3": raw, "checked_common_mm3": value,
                "proof": "actual_valid_signed_OCC_common_bounded_by_validated_inputs"}

    def volume(self, first, second):
        return self.common(first, second)["checked_common_mm3"]


def positive_bbox_separation(first, second):
    if not isinstance(first, CheckedBody) or not isinstance(second, CheckedBody):
        raise TypeError("Separation requires validated bodies")
    gaps = {a: max(first.bounds[a][0], second.bounds[a][0]) - min(first.bounds[a][1], second.bounds[a][1]) for a in "xyz"}
    return {a: v for a, v in gaps.items() if v > 0.0}
