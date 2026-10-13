"""Validated whole-solid intersections; conservative AABB separation only.

Historical CQ booleans return single-solid Compound wrappers. They are allowed
only when each Compound has exactly one direct child and the leaf is the sole
Solid. Loose or repeated surfaces, wires, edges or vertices cannot be discarded.
"""
import math

from occ_signed_volume import InconsistentGeometry, common, validated_solid_volume


def participant(shape):
    value = validated_solid_volume(shape)
    solids = shape.Solids()
    sole = solids[0]
    sole_value = validated_solid_volume(sole)
    node = shape
    while node.ShapeType() == "Compound":
        children = list(node)
        if len(children) != 1:
            raise InconsistentGeometry("Single-solid Compound contains extra direct children")
        node = children[0]
    if node.ShapeType() != "Solid":
        raise InconsistentGeometry("Only Solid or pure nested single-solid Compounds are allowed")
    if shape.ShapeType() != "Solid":
        for method in ("Vertices", "Edges", "Wires", "Faces", "Shells"):
            if len(getattr(shape, method)()) != len(getattr(sole, method)()):
                raise InconsistentGeometry("Single-solid Compound contains extra topology: " + method)
        if value != sole_value:
            raise InconsistentGeometry("Single-solid Compound signed volume differs from sole Solid")
    box = shape.BoundingBox()
    bounds = {key: float(getattr(box, key)) for key in
              ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")}
    if not all(math.isfinite(number) for number in bounds.values()):
        raise InconsistentGeometry("Nonfinite participant bounding box")
    if any(bounds[axis + "min"] > bounds[axis + "max"] for axis in "xyz"):
        raise InconsistentGeometry("Inverted participant bounding box")
    return {"shape_type": shape.ShapeType(), "valid_single_solid": True,
            "pure_single_solid_compound_wrapper": shape.ShapeType() == "Compound",
            "signed_volume_mm3": value, "bounds_mm": bounds}


def strict_common(a, b, abs_tolerance_mm3=1e-7):
    """Reject every invalid input BEFORE any optional separation shortcut."""
    if not math.isfinite(abs_tolerance_mm3) or abs_tolerance_mm3 < 0.:
        raise InconsistentGeometry("Nonfinite or negative common tolerance")
    aa, bb = participant(a), participant(b)
    gaps = {axis: max(aa["bounds_mm"][axis + "min"] - bb["bounds_mm"][axis + "max"],
                     bb["bounds_mm"][axis + "min"] - aa["bounds_mm"][axis + "max"])
            for axis in "xyz"}
    if any(gap > 0. for gap in gaps.values()):
        return {"method": "strict_positive_AABB_separation_after_participant_validation",
                "raw_signed_volume_mm3": None, "checked_volume_mm3": 0.,
                "a": aa, "b": bb, "signed_axis_separations_mm": gaps,
                "absolute_numeric_tolerance_mm3": abs_tolerance_mm3,
                "OCC_boolean_was_run": False,
                "negative_raw_value_is_never_clamped_to_clearance": True}
    result = common(a, b, abs_tolerance_mm3)
    return {"method": "OCC_common_with_signed_volume_and_upper_bound_checks",
            "a": aa, "b": bb, "signed_axis_separations_mm": gaps,
            "OCC_boolean_was_run": True, **result}
