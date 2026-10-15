"""Fail closed on inconsistent OCC signed volumes, including isValid=True failures.

For overlapping loft cells, sum intersections is a cell tally, not union volume.
Every individual common is bounded against its own cell and body.
"""
import math


class InconsistentGeometry(ValueError):
    pass


def check_common_volume(common_volume, cell_volume, body_volume, abs_tolerance_mm3=1e-7):
    values = (common_volume, cell_volume, body_volume, abs_tolerance_mm3)
    if not all(math.isfinite(x) for x in values):
        raise InconsistentGeometry("Nonfinite volume or tolerance")
    if cell_volume <= 0. or body_volume <= 0. or abs_tolerance_mm3 < 0.:
        raise InconsistentGeometry("Input solid volume must be positive")
    if common_volume < 0.:
        raise InconsistentGeometry("Negative signed common volume")
    if common_volume > min(cell_volume, body_volume) + abs_tolerance_mm3:
        raise InconsistentGeometry("Common volume exceeds a participating solid")
    return common_volume


def validated_solid_volume(shape):
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise InconsistentGeometry("Input must contain one valid solid")
    value = float(shape.Volume())
    if not math.isfinite(value) or value <= 0:
        raise InconsistentGeometry("Input has nonpositive signed volume")
    return value


def common(cell, body, abs_tolerance_mm3=1e-7):
    cv, bv = validated_solid_volume(cell), validated_solid_volume(body)
    intersection = cell.intersect(body)
    if not intersection.isValid():
        raise InconsistentGeometry("Invalid OCC common")
    raw = float(intersection.Volume())
    value = check_common_volume(raw, cv, bv, abs_tolerance_mm3)
    return {"raw_signed_volume_mm3": raw, "checked_volume_mm3": value,
        "cell_volume_mm3": cv, "body_volume_mm3": bv,
        "absolute_numeric_tolerance_mm3": abs_tolerance_mm3,
        "checks_performed": "valid solid inputs; finite, strictly nonnegative raw common; participating-solid upper bound",
        "negative_raw_value_is_never_clamped_to_clearance": True}


def cells_against_body(cells, body, abs_tolerance_mm3=1e-7):
    details = [common(cell, body, abs_tolerance_mm3) for cell in cells]
    return {"cell_count": len(details), "per_cell": details,
        "sum_of_checked_cell_common_volumes_mm3": sum(row["checked_volume_mm3"] for row in details),
        "sum_is_not_union_or_authorized_cut_volume": True,
        "any_cell_collision_above_tolerance": any(row["checked_volume_mm3"] > abs_tolerance_mm3 for row in details),
        "manufacturing_go": False}
