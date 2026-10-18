"""Builder-independent whole-payload STEP readback. Same OCCT kernel.

No product generator imports. Rejects free non-solid topology, duplicate or
unsafe member paths, shape-record drift and changed source/configuration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import time
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

ROOT=Path(__file__).resolve().parents[3]
TOL=1e-7


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def solids(shape,*,allow_empty=False):
    leaves=[]
    def visit(node):
        if not node.isValid():raise ValueError('invalid native topology')
        kind=node.ShapeType()
        if kind=='Solid':
            v=float(node.Volume())
            if not math.isfinite(v) or v<=0:raise ValueError('invalid signed solid')
            leaves.append(node)
        elif kind in ('Compound','CompSolid'):
            children=list(node)
            if not children and not allow_empty:raise ValueError('empty native payload')
            for child in children:visit(child)
        else:raise ValueError('free non-solid native topology: '+kind)
    visit(shape)
    total=sum(float(s.Volume()) for s in leaves)
    if abs(total-float(shape.Volume()))>TOL:raise ValueError('native payload volume differs from all leaves')
    return leaves,total


def bounds(shape):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape.wrapped,b,False,False)
    xmin,ymin,zmin,xmax,ymax,zmax=b.Get()
    return [xmin,xmax,ymin,ymax,zmin,zmax]


def load(path):
    roots=cq.importers.importStep(str(path)).vals()
    if len(roots)!=1:raise ValueError('multiple STEP roots')
    parts,volume=solids(roots[0]);return roots[0],parts,volume


def verify(manifest,output):
    started=time.monotonic()
    path=Path(manifest).resolve();record=json.loads(path.read_text());exports=record['exports'];rows=[];total=0.;native={}
    if record.get('schema') not in ('razr-product-export-v1','razr-oled-geometric-export-v1'):raise ValueError('unknown manifest')
    if not exports:raise ValueError('no participants')
    for name,item in sorted(exports.items()):
        rel=Path(item['path']);f=path.parent/rel
        if len(rel.parts)!=1 or rel.name!=name+'.step' or f.is_symlink() or sha(f)!=item['sha256']:raise ValueError('unsafe or changed participant')
        raw=[item['volume_mm3'],*item['bounds_mm']]
        if len(raw)!=7 or any(type(x) not in (int,float) or not math.isfinite(x) for x in raw):raise ValueError('invalid finite certificate')
        body,leaves,vol=load(f)
        if len(leaves)!=1:raise ValueError('participant is not one entire connected solid')
        native[name]=body
        verror=abs(vol-raw[0]);berror=max(abs(a-b) for a,b in zip(bounds(body),raw[1:]))
        if max(verror,berror)>TOL:raise ValueError('native participant record differs: '+name)
        rows.append({'name':name,'one_valid_complete_solid':True,'volume_error_mm3':verror,'maximum_bound_error_mm':berror});total+=vol
        if item.get('mesh'):
            mesh=path.parent/item['mesh']['path']
            if mesh.parent!=path.parent or mesh.is_symlink() or sha(mesh)!=item['mesh']['sha256']:raise ValueError('mesh bytes changed')
    combined=None
    if record.get('combined'):
        rec=record['combined'];f=path.parent/rec['path']
        if f.parent!=path.parent or f.is_symlink() or sha(f)!=rec['sha256']:raise ValueError('combined STEP bytes changed')
        body,allparts,vol=load(f)
        if len(allparts)!=len(exports) or len(allparts)!=rec['expected_solid_count']:raise ValueError('combined scene loses or adds physical participants')
        if abs(vol-total)>TOL:raise ValueError('combined whole volume mismatch')
        combined={'solid_count':len(allparts),'whole_volume_mm3':vol,'sum_part_volume_mm3':total,'volume_error_mm3':abs(vol-total)}
    for rel,value in record.get('generator_source_sha256',{}).items():
        if sha(ROOT/rel)!=value:raise ValueError('generator/config changed after export')
    if any(name in sys.modules for name in ('product_assembly','oled_storage','product_motion')):raise ValueError('candidate builder imported')
    tools=[]
    # Finite 1.2 x 0.12 mm blade prisms are taken from each actual exported
    # screw head datum, not from a second phone layout. They model access only,
    # not an available tool, torque, fingers, or an actual helical fastening.
    for name,body in sorted(native.items()):
        if not any(key in name for key in ('_A_SUPPORT_','_B_SUPPORT_','_SIDE_GUIDE_','_OPEN_HOLD_')):
            continue
        if not name.endswith('_M1_NOMINAL'):continue
        bb=bounds(body);x=(bb[0]+bb[1])/2;y=(bb[2]+bb[3])/2
        rear='_OPEN_HOLD_' in name
        lower=bb[5]-.09 if rear else bb[4]-8.
        upper=bb[5]+10. if rear else bb[4]+.09
        blade=cq.Solid.makeBox(1.2,.12,upper-lower,cq.Vector(x-.6,y-.06,lower))
        solids(blade);bad=[]
        for obstacle,fixed in sorted(native.items()):
            if obstacle==name:continue
            aa=bounds(blade);ob=bounds(fixed)
            gap=max(max(aa[2*i]-ob[2*i+1],ob[2*i]-aa[2*i+1]) for i in range(3))
            if gap>0:continue
            common=blade.intersect(fixed)
            _,volume=solids(common,allow_empty=True)
            if volume < -TOL or volume > min(float(blade.Volume()),float(fixed.Volume()))+TOL:
                raise ValueError('invalid finite driver intersection')
            if volume>TOL:bad.append({'obstacle':obstacle,'common_mm3':volume})
        advanced=blade.translate((0,0,-.02 if rear else .02))
        _,contact=solids(advanced.intersect(body),allow_empty=True)
        tools.append({'fastener':name,'approach':'rear' if rear else 'front',
                      'finite_blade_section_mm':[1.2,.12],
                      'other_material_penetrations':bad,
                      'slot_floor_contact_after_0p02_advance_mm3':contact,
                      'finite_tool_access_clear':not bad and contact>TOL,
                      'commercial_tool_and_torque_not_qualified':True})
    result={'passed':True,'reader_sha256':sha(__file__),'manifest_sha256':sha(path),'participant_count':len(rows),'parts':rows,
            'combined':combined,'all_payload_topology_checked':True,'same_CAD_kernel':True,'builder_imported':False,
            'added_nominal_M1_driver_access_checks':tools,
            'added_nominal_M1_driver_access_clear':all(x['finite_tool_access_clear'] for x in tools),
            'STL_bytes_checked_not_mesh_manufacturability':True,'dimensions_are_study_geometry_not_measurements':True,
            'elapsed_seconds':time.monotonic()-started,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    Path(output).write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.manifest,a.output)
    print(json.dumps({'passed':r['passed'],'parts':r['participant_count'],'builder_imported':False}))
