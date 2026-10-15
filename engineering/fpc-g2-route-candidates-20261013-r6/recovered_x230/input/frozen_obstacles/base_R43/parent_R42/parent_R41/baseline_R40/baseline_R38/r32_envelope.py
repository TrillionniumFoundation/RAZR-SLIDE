"""Bounded CAD envelope check: product intent != automatically equal solids.

These are the extents of the currently modeled internal chassis BReps, NOT a
measured dimension of industrial-design cover parts or OEM housing drawings.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT

def bounds(b):
    return dict(x=[round(b.xmin,6),round(b.xmax,6)],
                y=[round(b.ymin,6),round(b.ymax,6)],
                z=[round(b.zmin,6),round(b.zmax,6)],
                lengths_xyz_mm=[round(b.xlen,6),round(b.ylen,6),round(b.zlen,6)])

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R32_A_R31_UNMODIFIED.brep')).val().BoundingBox()
    B=cq.importers.importBrep(str(ROOT/'cad'/'R32_B_REAR_CASSETTE_BAYS.brep')).val().BoundingBox()
    delta=[round(x-y,6) for x,y in zip((A.xlen,A.ylen,A.zlen),(B.xlen,B.ylen,B.zlen))]
    d=dict(revision='R32 A/B solid bounding-box audit, NOT OEM exterior dimensions',
        A_native_chassis_solid_bbox=bounds(A),B_native_chassis_solid_bbox=bounds(B),
        A_minus_B_extent_xyz_mm=delta,
        same_X_outer_span_within_1e_6=abs(delta[0])<1e-6,
        native_solids_full_bbox_equal=False,
        A_B_identical_finished_outer_shells_NOT_proven=True,
        complementary_mating_endcuts_may_explain_native_body_extent_difference=True,
        no_separate_outer_cosmetic_shell_CAD_or_OEM_authority=True,
        product_equal_outer_size_requirement_unchanged=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_envelope.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':
    d=run();print('R32 A-B EXTENT',d['A_minus_B_extent_xyz_mm'],flush=True)
