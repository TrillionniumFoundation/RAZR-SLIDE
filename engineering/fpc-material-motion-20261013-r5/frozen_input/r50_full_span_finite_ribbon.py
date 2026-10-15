#!/usr/bin/env python3
"""R50 complete *research proxy* ribbon negative gate.

This constructs each of the 108 polyline cells as a finite rectangular ruled OCC
loft over frozen R47/R48 centerline. The local frame is mathematical parallel
transport; there is NO real FPC stackup/neutral axis/strain model or signed
OEM keep-out. Positive OCC collision is a route rejection, while no collision
would *never* constitute physical authorization. Do not derive a manufacturing
FPC from this program.
"""
from __future__ import annotations
import argparse, json, hashlib, math, sys, time, zipfile
from pathlib import Path
import numpy as np
import cadquery as cq

ROOT=Path(__file__).resolve().parent.parent
R47=ROOT/'baseline/R47'
R48=ROOT/'baseline/R48'
R49_SOURCE='494fbdb0b726f068dc5e72903ca4c99a4f188835929e8b22a6e339e89f8ba00d'
R48_SOURCE='b9a2904ea79e348576120e63f24cdebc2efd2b6bf68ff40f9cdad1fe544d2e72'
R47_SOURCE='25af6127c7bc51b0f62deaef86963f3fed818e93d14ff7dd7a9240afcb692f45'
WIDTH=1.2
THICKNESS=.2
TRIM=6.
POSES=[('STOW',0.,0.),('SLIDE_13p37',13.37,0.),('SLIDE_40p125',40.125,0.),('SLIDE_60p29',60.29,0.),('PREDOCK',79.75,0.),('DOCK_0p07',79.75,.07),('DOCK_4p013',79.75,4.013),('DOCK_8p19',79.75,8.19),('OPEN_SEATED',79.75,8.2)]

def sha(p:Path):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def verify_lineage(parent:Path):
    assert sha(parent)==R49_SOURCE, 'R49 package SHA mismatch'
    with zipfile.ZipFile(parent) as z:
        assert z.testzip() is None and len(z.namelist())==25
        assert sha(ROOT/'baseline/R48_PARENT_UNMODIFIED.zip')==R48_SOURCE
        assert z.read('baseline/R48_PARENT_UNMODIFIED.zip')==(ROOT/'baseline/R48_PARENT_UNMODIFIED.zip').read_bytes()
        for n in ('src/r49_cross_section_gate.py','results/R49_offgrid_crosssection_negative_gate.json','README_先读_R49.md'):
            assert z.read(n)==(ROOT/n).read_bytes(), n
    with zipfile.ZipFile(ROOT/'baseline/R48_PARENT_UNMODIFIED.zip') as z:
        assert hashlib.sha256(z.read('baseline/R47_PARENT_UNCHANGED.zip')).hexdigest()==R47_SOURCE
        for nm in ('src/r48_dense_gate.py','results/R48_dense_481_7_routes.json'):
            assert z.read(nm)==(R48/nm).read_bytes(),nm
    assert sha(R48/'baseline/R47_PARENT_UNCHANGED.zip')==R47_SOURCE
    for nm in ('src/r47_full_span_and_intake.py','baseline/R46_source/reference/R38_A_unchanged.brep','baseline/R46_source/reference/R38_B_unchanged.brep'):
        with zipfile.ZipFile(R48/'baseline/R47_PARENT_UNCHANGED.zip') as z:
            assert z.read(nm)==(R47/nm).read_bytes(),nm
    return dict(R49_sha256=R49_SOURCE,R48_sha256=R48_SOURCE,R47_sha256=R47_SOURCE,
                direct_parent_archive_byte_checked=True,inherited_source_and_BRep_frozen=True)

def unit(a):
    n=float(np.linalg.norm(a))
    if not math.isfinite(n) or n<1e-10:raise ValueError('degenerate tangent')
    return a/n

def sections(centerline:np.ndarray, width:float=WIDTH, thickness:float=THICKNESS, frame_mode='transport'):
    N=len(centerline)
    wires=[]; normals=[]; tangents=[]; prior=None; angle_max=0.
    for i,p in enumerate(centerline):
        tangent=unit(centerline[min(i+1,N-1)]-centerline[max(i-1,0)])
        if frame_mode in ('transport','transport_seed_y') and prior is not None:
            width_dir=prior-np.dot(prior,tangent)*tangent
            if np.linalg.norm(width_dir)<1e-5:width_dir=np.cross(tangent,[0,0,1])
        else:
            seed=[0,1,0] if frame_mode=='transport_seed_y' else [0,0,1]
            width_dir=np.cross(tangent,seed)
        if np.linalg.norm(width_dir)<1e-5:width_dir=np.cross(tangent,[0,1,0] if frame_mode!='transport_seed_y' else [0,0,1])
        width_dir=unit(width_dir)
        if prior is not None and frame_mode in ('transport','transport_seed_y') and np.dot(width_dir,prior)<0:width_dir=-width_dir
        thick_dir=unit(np.cross(tangent,width_dir))
        if prior is not None:
            angle_max=max(angle_max,math.degrees(math.acos(float(np.clip(np.dot(prior,width_dir),-1.,1.)))))
        prior=width_dir
        vertices=[cq.Vector(*map(float,p+dw*width/2*width_dir+dt*thickness/2*thick_dir))
                  for dw,dt in [(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]]
        wires.append(cq.Wire.makePolygon(vertices))
        normals.append((width_dir,thick_dir));tangents.append(tangent)
    return wires,normals,tangents,angle_max

def solid_cells(wires):
    cells=[]
    for i in range(len(wires)-1):
        obj=cq.Solid.makeLoft([wires[i],wires[i+1]],ruled=True)
        if not obj.isValid() or len(obj.Solids())!=1 or obj.Volume()<=0:
            raise AssertionError(f'invalid solid cell {i}')
        cells.append(obj)
    return cells

def solid_intersection(cells,body):
    """Check each signed common before summing; overlapping cells are not a union."""
    from occ_signed_volume import common as checked_common, validated_solid_volume
    # Validate every participant BEFORE a bbox disjoint result can bypass booleans.
    validated_solid_volume(body)
    for cell in cells:validated_solid_volume(cell)
    bb=body.BoundingBox();sub=[]
    for cell in cells:
        r=cell.BoundingBox()
        if not (r.xmax<bb.xmin or r.xmin>bb.xmax or r.ymax<bb.ymin or r.ymin>bb.ymax or r.zmax<bb.zmin or r.zmin>bb.zmax):sub.append(cell)
    if not sub:return {'mm3':0.,'solid_count':0,'bbox_candidates':0,'computed':True,
                        'per_cell_signed_volumes_checked':True,'sum_is_not_union_volume':True}
    details=[checked_common(cell,body,abs_tolerance_mm3=1e-7) for cell in sub]
    return {'mm3':sum(row['checked_volume_mm3'] for row in details),
            'solid_count':sum(row['checked_volume_mm3']>1e-7 for row in details),
            'bbox_candidates':len(sub),'computed':True,
            'per_cell_signed_volumes_checked':True,'sum_is_not_union_volume':True,
            'cell_common_details':details}


def configure_source_root(path):
    """Point an isolated repaired module at a verified extracted R50 source tree."""
    global ROOT,R47,R48
    ROOT=Path(path).resolve()
    R47=ROOT/'baseline/R47';R48=ROOT/'baseline/R48'
    return verify_lineage(ROOT/'baseline/R49_PARENT_UNMODIFIED.zip')

def get_reference():
    sys.path.insert(0,str(R47/'src'))
    import r47_full_span_and_intake as r47
    routing=r47.import_R46()
    A=cq.importers.importBrep(str(R47/'baseline/R46_source/reference/R38_A_unchanged.brep')).val()
    B=cq.importers.importBrep(str(R47/'baseline/R46_source/reference/R38_B_unchanged.brep')).val()
    assert A.isValid() and B.isValid()
    return r47,routing,A,B

def make_row(r47,r,candidate,pose_name,s,q,A,B,mode='transport',export=None):
    start=time.monotonic()
    target=r.target_length(candidate)
    pts,dist,row,segs=r47.full_centerline(r,candidate,s,q,target)
    assert len(pts)==109 and len(dist)==109 and len(segs)==108
    assert abs(row['length_exact_mm']-target)<1e-7
    wires,normals,tangents,maxframe=sections(pts,frame_mode=mode)
    cells=solid_cells(wires)
    assert len(cells)==108
    total=sum(float(z.Volume()) for z in cells)
    eligible=[i for i in range(108) if 0.5*(dist[i]+dist[i+1])>=TRIM and 0.5*(dist[i]+dist[i+1])<=dist[-1]-TRIM]
    assert eligible
    Bworld=B.translate((0,s,q-8.2))
    # Full path proxy and qualified-study interior are reported *separately*.
    fullA=solid_intersection(cells,A)
    fullB=solid_intersection(cells,Bworld)
    interiorA=solid_intersection([cells[i] for i in eligible],A)
    interiorB=solid_intersection([cells[i] for i in eligible],Bworld)
    res={
        'candidate':candidate.name,'pose':pose_name,'s_mm':s,'q_mm':q,
        'crosssection_width_mm':WIDTH,'crosssection_thickness_mm':THICKNESS,
        'profile_frame_mode':mode,'frame_max_adjacent_angle_deg':round(maxframe,6),
        'polyline_vertices':len(pts),'ruled_loft_cells':len(cells),'valid_loft_cells':len(cells),
        'proxy_cell_volume_sum_mm3':round(total,8),
        'sample_polyline_length_mm':round(float(dist[-1]),7),'analytic_centerline_length_mm':round(float(target),7),
        'chord_shortfall_mm':round(float(target-dist[-1]),7),
        'free_span_trim_each_end_mm':TRIM,'free_span_loft_cells':len(eligible),
        'whole_proxy_A_occ_intersection_mm3':round(fullA['mm3'],8),
        'whole_proxy_B_occ_intersection_mm3':round(fullB['mm3'],8),
        'free_span_A_occ_intersection_mm3':round(interiorA['mm3'],8),
        'free_span_B_occ_intersection_mm3':round(interiorB['mm3'],8),
        'whole_proxy_A_intersect_solid_count':fullA['solid_count'],
        'whole_proxy_B_intersect_solid_count':fullB['solid_count'],
        'candidate_gross_width_overrun_mm':round(float(row['width_overrun_mm']),7),
        'physical_vendor_FPC':False,'OEM_A_B_are_research_solid_not_cut_authorization':True,
        'not_torsion_or_strain_assessed':True,'connector_stubs_intentionally_sharp':True,
        'usb_physically_measured':False,'manufacturing_go':False,
        'per_cell_boolean_audit':{'whole_A':fullA,'whole_B':fullB,'free_span_A':interiorA,'free_span_B':interiorB},
        'per_cell_signed_volume_guard_applied':True,
        'sum_of_overlapping_cell_commons_not_union_volume':True,
        'elapsed_seconds':round(time.monotonic()-start,2)
    }
    if export is not None:
        assert export.suffix=='.step'
        shape=cq.Compound.makeCompound([A,Bworld,*cells])
        assert shape.isValid()
        cq.exporters.export(shape,str(export),exportType='STEP')
        loaded=cq.importers.importStep(str(export)).val()
        assert loaded.isValid() and len(loaded.Solids())>=110, (len(loaded.Solids()),len(cells))
        res['STEP_ghost_file']='cad/'+export.name
        res['STEP_sha256']=sha(export)
        res['STEP_reimport_solids']=len(loaded.Solids())
    return res

def run_family(i,export=False):
    r47,r,A,B=get_reference()
    candidate=r.CANDIDATES[i]
    rows=[]
    export_poses={'STOW','SLIDE_40p125','OPEN_SEATED'}
    for pose_name,s,q in POSES:
        path=ROOT/'cad'/f'R50_{candidate.name}_{pose_name}_FULL_FINITE_LOFT_GHOST.step' if export and pose_name in export_poses else None
        if path:path.parent.mkdir(parents=True,exist_ok=True)
        result=make_row(r47,r,candidate,pose_name,s,q,A,B,export=path)
        rows.append(result)
        print(f'{candidate.name} {pose_name} A={result["free_span_A_occ_intersection_mm3"]} B={result["free_span_B_occ_intersection_mm3"]} seconds={result["elapsed_seconds"]}',flush=True)
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--family',type=int,required=True,choices=range(7));p.add_argument('--export',action='store_true');args=p.parse_args()
    output=ROOT/'results'/f'R50_finite_ribbon_family{args.family}.json'
    report={'family_index':args.family,'source_R49_sha256':R49_SOURCE,'finite_ribbon_study_only':True,
            'manufacturing_go':False,'poses':run_family(args.family,args.export)}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print('DONE',output,flush=True)
if __name__=='__main__':main()
