#!/usr/bin/env python3
"""Four actual OCC swept solids on R6's conditional G2 path, no obstacles.

Nominal W=1.2 mm / T=.056 mm is a research section, not a specified FPC.
Native process success only means all outcomes were recorded. Geometry passes
only if the complete returned payload contains exactly one valid positive solid.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
import traceback

sys.dont_write_bytecode = True
import cadquery as cq
import numpy as np
from geometry_candidates import Config, build_candidate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pure_positive_single_solid(shape):
    if not shape.isValid():
        raise ValueError('returned complete OCC payload is invalid')
    if len(shape.Solids()) != 1:
        raise ValueError('returned complete OCC payload is not exactly one solid')
    node = shape
    wrapper_depth = 0
    while node.ShapeType() == 'Compound':
        children = list(node)
        if len(children) != 1:
            raise ValueError('returned compound contains extra direct children')
        node = children[0]
        wrapper_depth += 1
    if node.ShapeType() != 'Solid':
        raise ValueError('complete OCC payload contains loose topology')
    volume = float(shape.Volume())
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError('returned OCC payload has nonpositive/nonfinite signed volume')
    return dict(valid=True, solid_count=1, wrapper_depth=wrapper_depth,
                complete_payload_positive_volume_mm3=volume)


def _v(point):
    return cq.Vector(*map(float, point))


def route_wire(curve):
    edges = []
    for seg in curve.segments:
        p, first, _ = seg.derivatives([0., 1.])
        if seg.kind == 'line':
            edge = cq.Edge.makeLine(_v(p[0]), _v(p[1]))
        elif seg.kind == 'leg':
            # Exact degree-three restriction: no point-interpolated substitute.
            controls = (p[0], p[0]+first[0]/3, p[1]-first[1]/3, p[1])
            edge = cq.Edge.makeBezier([_v(point) for point in controls])
        elif seg.kind == 'bezier':
            if (seg.t0, seg.t1) != (0., 1.):
                raise ValueError('this preflight does not silently reparameterize a trimmed quintic')
            edge = cq.Edge.makeBezier([_v(point) for point in seg.data['control']])
        elif seg.kind == 'arc':
            mid = seg.derivatives([.5])[0][0]
            edge = cq.Edge.makeThreePointArc(_v(p[0]), _v(mid), _v(p[1]))
        else:
            raise ValueError('unexpected curve segment')
        if not edge.isValid():
            raise ValueError('invalid OCC edge '+seg.tag)
        edges.append(edge)
    wire = cq.Wire.assembleEdges(edges)
    if not wire.isValid() or wire.ShapeType() != 'Wire' or len(wire.Edges()) != 9:
        raise ValueError('complete route wire did not retain nine valid edges')
    return wire


def sweep_case(config, s, q, seed, width_mm=1.2, thickness_mm=.056):
    curve = build_candidate(config, s, q)
    wire = route_wire(curve)
    xyz, tangent, _ = curve.evaluate([0.])
    if abs(float(np.dot(tangent[0], seed))) > 1e-10:
        raise ValueError('profile seed not orthogonal to A endpoint tangent')
    plane = cq.Plane(origin=_v(xyz[0]), xDir=_v(seed), normal=_v(tangent[0]))
    wp = cq.Workplane(plane).rect(width_mm, thickness_mm)
    swept = wp.sweep(cq.Workplane(obj=wire), isFrenet=False)
    shapes = swept.vals()
    if len(shapes) != 1:
        raise ValueError('sweep returned multiple top-level payloads')
    return curve, wire, shapes[0]


def main(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cad = output.parent/'cad_preflight'
    cad.mkdir(exist_ok=True)
    source = Path(__file__)
    geometry = source.with_name('geometry_candidates.py')
    before = {'cad_preflight.py':sha(source), 'geometry_candidates.py':sha(geometry)}
    start = time.monotonic()
    config = Config(target_length_mm=148.20738578362864,dA_mm=1.,dB_mm=1.,dJ_mm=.25)
    results = []
    for pose, s, q in (('STOW',0.,0.),('OPEN_SEATED',79.75,8.2)):
        for seed_name, seed in (('WIDTH_Y',[0.,1.,0.]),('WIDTH_Z',[0.,0.,1.])):
            name = pose+'_'+seed_name
            row = {'case':name,'slide_mm':s,'normal_mm':q,'width_seed':seed,
                   'width_mm':1.2,'nominal_total_thickness_mm':.056,
                   'isFrenet':False,'controlled_finished_FPC':False,
                   'obstacle_interference_checked':False,'geometry_accepted':False}
            body = None
            try:
                curve, wire, body = sweep_case(config,s,q,seed)
                row['actual_wire_length_mm'] = float(wire.Length())
                row['analytic_integrated_curve_length_mm'] = float(curve.bounds[-1])
                row['reference_area_times_length_mm3'] = 1.2*.056*curve.target
                row['raw_payload_type'] = body.ShapeType()
                row['raw_payload_valid'] = bool(body.isValid())
                row['raw_payload_solid_count'] = len(body.Solids())
                row['raw_payload_signed_volume_mm3'] = float(body.Volume())
                row['complete_payload_guard'] = pure_positive_single_solid(body)
                row['signed_volume_minus_reference_mm3'] = row['raw_payload_signed_volume_mm3']-row['reference_area_times_length_mm3']
                body_path = cad/(name+'_CONDITIONAL_NOMINAL_56UM.step')
                wire_path = cad/(name+'_PATH_ONLY.step')
                cq.exporters.export(body,str(body_path))
                cq.exporters.export(wire,str(wire_path))
                imported = cq.importers.importStep(str(body_path))
                if len(imported.vals()) != 1:
                    raise ValueError('export reimport has extra top-level payloads')
                row['reimport_full_payload_guard'] = pure_positive_single_solid(imported.val())
                row['body_STEP'] = {'filename':body_path.name,'sha256':sha(body_path)}
                row['path_STEP'] = {'filename':wire_path.name,'sha256':sha(wire_path)}
                row['geometry_accepted'] = True
            except Exception as exc:
                row['exception'] = {'type':type(exc).__name__,'message':str(exc),
                                    'traceback':traceback.format_exc()}
                if body is not None:
                    # Keep even rejected actual BREP payloads; never repair or
                    # extract a convenient solid to force a qualification pass.
                    try:
                        path = cad/(name+'_REJECTED_ACTUAL_PAYLOAD.brep')
                        cq.exporters.export(body,str(path))
                        row['rejected_BREP'] = {'filename':path.name,'sha256':sha(path)}
                    except Exception as artifact_error:
                        row['rejected_BREP_save_error'] = str(artifact_error)
            row['manufacturing_go'] = False
            results.append(row)
            print(name,json.dumps({k:v for k,v in row.items() if k!='exception'},sort_keys=True),flush=True)
    after = {'cad_preflight.py':sha(source),'geometry_candidates.py':sha(geometry)}
    report = {'schema':'R6_ACTUAL_OCC_NOMINAL_56UM_SWEEP_PREFLIGHT','Python':platform.python_version(),
              'CadQuery':cq.__version__,'host':platform.node(),'input_hashes_before':before,
              'input_hashes_after':after,'input_bytes_unchanged':before==after,
              'requested_actual_case_count':4,'recorded_actual_case_count':len(results),
              'geometry_accepted_case_count':sum(r['geometry_accepted'] for r in results),
              'native_zero_means_outcomes_recorded_not_all_geometry_accepted':True,
              'volume_area_length_comparison_is_reference_not_acceptance_criterion':True,
              'supplier_FPC_qualification':False,'mechanical_or_OLED_qualification':False,
              'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start,'cases':results}
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    if before != after:
        raise ValueError('preflight inputs changed during actual execution')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(Path(__file__).with_name('cad_preflight.json')))
    main(parser.parse_args().output)
