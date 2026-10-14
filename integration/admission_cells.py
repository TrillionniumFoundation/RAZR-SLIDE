"""Finite translation covered by individually checked native solid cells.

The cells overlap. Their volumes are NEVER summed as a swept-volume measure.
A union of initial/end material and forward boundary-face sweeps covers the
nominal translation. Complete cylindrical carriers are explicit supersets.
Keeping cells separate avoids a fragile global Boolean fusion, without treating
failed/negative/extra topology as empty. This is not a CAD-kernel repair or a
manufacturing tolerance proof.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from straight_envelope import single, swept_cylinder


def vector3(values):
    if len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('three finite real translation coordinates required')
    return tuple(float(v) for v in values)


def translation_cells(shape,vector):
    single(shape);vec=vector3(vector);move=cq.Vector(vec)
    if move.Length<=1e-12:raise ValueError('nonzero translation required')
    cells=[('source',shape),('target',single(shape.translate(move)))];metadata=[]
    for index,face in enumerate(shape.Faces()):
        kind=face.geomType()
        if kind=='PLANE':
            if face.normalAt().dot(move)>1e-12:
                sh=single(cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),move))
                cells.append((f'plane_{index}',sh));metadata.append({'cell':f'plane_{index}','face':index,'construction':'full_forward_planar_face_prism_including_holes'})
        elif kind=='CYLINDER':
            a=BRepAdaptor_Surface(face.wrapped);c=a.Cylinder();d=c.Axis().Direction();axis=cq.Vector(d.X(),d.Y(),d.Z());p=c.Location();v0,v1=a.FirstVParameter(),a.LastVParameter()
            if not math.isfinite(v0) or not math.isfinite(v1) or v1<=v0:raise ValueError('unbounded cylindrical carrier')
            origin=cq.Vector(p.X(),p.Y(),p.Z()).add(axis.multiply(v0))
            sh,method=swept_cylinder(origin,axis,c.Radius(),v1-v0,move)
            cells.append((f'cylinder_{index}',single(sh)));metadata.append({'cell':f'cylinder_{index}','face':index,'construction':method,'whole_cylinder_is_conservative':True})
        else:raise ValueError('unsupported native surface: '+kind)
    return cells,{'translation_mm':vec,'face_count':len(shape.Faces()),'cell_count':len(cells),'cells':metadata,
        'representation':'union of independently validated possibly overlapping solid cells',
        'global_boolean_fusion_used':False,'not_a_discrete_pose_union':True,
        'cell_volume_sum_is_not_swept_volume':True,'numerical_topology_checks_not_formal_exact_arithmetic':True,'manufacturing_go':False}


@dataclass(frozen=True)
class Stage:
    name: str
    part: str
    start: tuple
    end: tuple

    def __post_init__(self):
        if not self.name or not self.part:raise ValueError('stage and part identity required')
        vector3(self.start);vector3(self.end)
        if self.start==self.end:raise ValueError('stage must actually move')


class AssemblyState:
    """Persistent part placement; failed stages never place or teleport a part."""
    def __init__(self,initial):
        self.poses={name:vector3(pose) for name,pose in initial.items()}
        self.completed=[];self.blocked=None

    def fixed_names(self,stage):
        if self.blocked is not None:raise ValueError('downstream stage blocked by earlier failure')
        if stage.name in self.completed:raise ValueError('duplicate stage')
        if stage.part in self.poses and self.poses[stage.part]!=vector3(stage.start):raise ValueError('moving part would teleport')
        return tuple(sorted(n for n in self.poses if n!=stage.part))

    def finish(self,stage,passed,checked_fixed):
        if type(passed) is not bool:raise ValueError('explicit boolean result required')
        expected=self.fixed_names(stage)
        if tuple(sorted(checked_fixed))!=expected:raise ValueError('an already-present obstacle was omitted or duplicated')
        if not passed:self.blocked=stage.name;return
        self.poses[stage.part]=vector3(stage.end);self.completed.append(stage.name)
