"""Reconnect the project-owned STOW outer root with a fixed narrow side web.

Retain v9 components and all material outside the explicit motion conflicts.
Rejected cut-only and U-bypass constructions remain as negative controls.
This is research geometry, not a proven strength/fastener/fatigue design.
"""
from pathlib import Path
import hashlib
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUP = ROOT / 'engineering/passive-return-spring-recovery-20261013-r6'
sys.path[:0] = [str(GROUP/'split-root-repair'), str(GROUP)]
import split_root_cartridges_v9 as parent
b = parent.b
check = parent.check
pairs = parent.pairs
ROOT_NAME = 'ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'
NUMERIC_VOLUME_TOLERANCE = 1e-7


def volume_leaves(shape):
    """Account for all result branches, including multiple retained fragments."""
    leaves = []
    def visit(node):
        if not node.isValid():
            raise ValueError('invalid complete topology')
        kind = node.ShapeType()
        if kind == 'Solid':
            v = float(node.Volume())
            if not math.isfinite(v) or v <= 0:
                raise ValueError('nonpositive signed material')
            leaves.append(v)
        elif kind in ('Compound', 'CompSolid'):
            children = list(node)
            # An empty compound is permitted only as an empty boolean result.
            for child in children:
                visit(child)
        else:
            raise ValueError('unexpected free topology: ' + kind)
    visit(shape)
    return leaves


def modification_geometry(port, side):
    if port != 'STOW' or side not in ('L', 'R'):
        raise ValueError('only declared STOW sides have modification geometry')
    windows, bridges = [], []
    for i in range(2):
        off = 5.0*i
        qc = 1.3 + (.9 if i == 0 else 3.0)
        windows.append(b.world(b.box(.49,.91,1.68,1.92,-.99+off,-.81+off),port,side))
        bridges.extend([
            b.world(b.box(.70,1.50,1.40,1.65,-.98+off,-.82+off),port,side),
            b.world(b.box(1.28,1.50,1.60,qc+.55,-.98+off,-.82+off),port,side),
            b.world(b.box(.70,1.50,1.95,2.15,-.98+off,-.82+off),port,side),
        ])
    return windows, bridges


from functools import lru_cache


@lru_cache(maxsize=2)
def canonical_envelopes(side):
    """Build one fixed nominal-geometry reference, never moving cutters."""
    if side not in ('L','R'):raise ValueError('unknown side')
    reference,_=parent.scene('STOW',side,1.14,True)
    returned,return_method=planar_translation_sweep(reference['PAWL'],b.identity.evec('STOW',side,1.1))
    parked=reference['PAWL'].translate(b.identity.evec('STOW',side,1.1))
    insertion,insert_method=planar_translation_sweep(parked,b.rvec('STOW',10.))
    return reference,returned,insertion,{'return':return_method,'insertion':insert_method}


def repair_parts(parts, port, side, *, enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:
        raise ValueError('invalid scene identity or repair switch')
    original=parts[ROOT_NAME];b.participant(original);out=dict(parts)
    report={'port':port,'side':side,'repair_enabled':enabled,'changed_parts':[],
            'mechanical_strength_qualified':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    if not enabled or port=='OPEN':return out,report
    reference,returned,insertion,method=canonical_envelopes(side)
    # E < 0.5 is outside the parked pawl's whole insertion envelope. The narrow
    # side web connects the retained root fragments rather than crossing the
    # axial insertion passage. Source parameters are research choices only.
    parameters=(.05,.30,1.10,2.15,-9.60,9.35)
    plate=b.world(b.box(*parameters),port,side)
    candidate=original.fuse(plate).clean().cut(returned).cut(insertion).clean()
    # These are fixed CANONICAL assembly slots; changing lift/key state later
    # does not manufacture a different root or erase a moving collision.
    for name,shape in reference.items():
        if name not in (ROOT_NAME,'PAWL'):candidate=candidate.cut(shape).clean()
    b.participant(candidate)
    removed=original.cut(candidate);added=candidate.cut(original)
    removed_total=sum(volume_leaves(removed));added_total=sum(volume_leaves(added))
    outside=sum(volume_leaves(removed.cut(returned).cut(insertion)))
    if outside>NUMERIC_VOLUME_TOLERANCE:raise ValueError('removed original material outside declared motion collisions')
    if abs(original.Volume()+added_total-removed_total-candidate.Volume())>NUMERIC_VOLUME_TOLERANCE:
        raise ValueError('material accounting mismatch')
    old_box,new_box=original.BoundingBox(),candidate.BoundingBox()
    bounds_delta={key:float(getattr(new_box,key)-getattr(old_box,key)) for key in ('xmin','xmax','ymin','ymax','zmin','zmax')}
    if any(abs(v)>1e-7 for v in bounds_delta.values()):raise ValueError('outer-root envelope expanded')
    out[ROOT_NAME]=candidate
    if any(not out[k].wrapped.IsSame(v.wrapped) for k,v in parts.items() if k!=ROOT_NAME):raise ValueError('unrelated scene part changed')
    report.update({'changed_parts':[ROOT_NAME],'candidate':'side_web','side_web_parameters_local_mm':list(parameters),
                   'nominal_web_thickness_mm':.25,'old_volume_mm3':original.Volume(),'new_volume_mm3':candidate.Volume(),
                   'removed_material_mm3':removed_total,'added_material_mm3':added_total,'bounds_delta_mm':bounds_delta,
                   'removed_outside_declared_motion_envelopes_mm3':outside,
                   'all_other_parts_same_shape_identity':True,'final_root_solids':1,
                   'all_material_outside_declared_motion_envelopes_retained':True,
                   'canonical_cut_state':{'lift_mm':1.14,'key_present':True},'root_not_recut_for_actual_lift_or_key_state':True,
                   'load_path_material_connected_not_strength_qualified':True})
    return out,report


def scene(port,side,lift=1.14,present=True,*,enabled=True):
    parts,raw=parent.scene(port,side,lift,present)
    repaired,audit=repair_parts(parts,port,side,enabled=enabled)
    return repaired,{**raw,'stow_web_repair':audit}


def planar_translation_sweep(shape, vector):
    """Finite straight sweep for a pure solid with exclusively planar faces.

Union the initial solid and prisms of every forward-facing boundary face.
For a rigid straight translation, newly occupied material crosses one such
boundary face. Preserve inner wires; reject curved faces, invalid solids and
any negative-volume result rather than approximating by a bounding box.
The kernel result is a nominal geometric envelope, not toleranced qualification.
CadQuery's extrudeLinear uses OCC BRepPrimAPI_MakePrism for zero taper.
"""
    b.participant(shape)
    direction = b.cq.Vector(vector)
    if not all(math.isfinite(v) for v in direction.toTuple()) or direction.Length <= 1e-12:
        raise ValueError('nonfinite or zero translation')
    faces = shape.Faces()
    if any(face.geomType() != 'PLANE' for face in faces):
        raise ValueError('only planar-boundary solids are supported')
    pieces = [shape]; forward = []
    for index,face in enumerate(faces):
        dot = float(face.normalAt().dot(direction))
        if dot > 1e-12:
            prism = b.cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),direction)
            b.participant(prism);pieces.append(prism)
            forward.append({'face_index':index,'normal_dot_translation_mm':dot,
                            'prism_volume_mm3':float(prism.Volume())})
    if not forward:
        raise ValueError('no forward boundary faces')
    swept = b.fuse(pieces)
    b.participant(swept)
    if swept.Volume()+NUMERIC_VOLUME_TOLERANCE < shape.Volume():
        raise ValueError('sweep lost source material')
    return swept, {'source_faces':len(faces),'forward_faces':forward,
                   'translation_mm':list(direction.toTuple()),
                   'source_volume_mm3':shape.Volume(),'swept_volume_mm3':swept.Volume(),
                   'construction':'initial solid union all forward planar face prisms',
                   'is_discrete_pose_union':False,'shape_is_nominal_not_toleranced':True,
                   'force_or_continuous_multi_axis_motion_qualified':False,
                   'manufacturing_go':False}
