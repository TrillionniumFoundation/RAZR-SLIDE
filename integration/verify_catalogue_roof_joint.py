"""Independent catalogue-dimension geometry checks; not a vendor CAD certificate.

Full mode joins the prior 79-part scene. Subset mode is explicitly restricted
to the supplied native templates. Expected process-scenario collisions are
kept as negative evidence, never treated as actual accepted process limits.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import cadquery as cq
from manufacturing_fit import CatalogueScrew, axial_fit, clearance_screen

TOL=1e-7


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vol(s):
    def visit(node):
        if not node.isValid():raise ValueError('invalid topology')
        if node.ShapeType()=='Solid':
            if not math.isfinite(node.Volume()) or node.Volume()<=0:raise ValueError('invalid signed volume')
            return [node]
        if node.ShapeType() not in ('Compound','CompSolid'):raise ValueError('loose non-solid')
        return [s for child in node for s in visit(child)]
    solids=visit(s);raw=s.Volume()
    if not math.isfinite(raw) or raw<0 or abs(math.fsum(p.Volume() for p in solids)-raw)>TOL:
        raise ValueError('signed volume mismatch')
    return raw


def common(a,b):return vol(a.intersect(b))


def equal(a,b):
    values=[vol(a.cut(b)),vol(b.cut(a))]
    if max(values)>TOL:raise ValueError('material identity mismatch')
    return values


def read(path):
    path=Path(path).resolve();m=json.loads(path.read_text());parts={};hashes={str(path):sha(path)}
    roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL',
           'TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER')
    if set(m['exports'])!={s+'_'+k for s in 'LR' for k in roles}|{'A_BACK_PANEL'}:
        raise ValueError('complete template identity mismatch')
    for key,rec in m['exports'].items():
        rel=Path(rec['path']);f=path.parent/rel
        if rel.parts!=(key+'.step',) or f.is_symlink():raise ValueError('unsafe STEP path')
        if sha(f)!=rec['sha256']:raise ValueError('changed STEP')
        certificate=[rec['volume_mm3'],*rec['bounds_mm']]
        if len(certificate)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in certificate):
            raise ValueError('invalid finite certificate')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1 or len(roots[0].Solids())!=1:raise ValueError('not one complete solid')
        s=roots[0];b=s.BoundingBox();actual=[vol(s),b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if any(abs(x-y)>TOL for x,y in zip(certificate,actual)):raise ValueError('certificate mismatch')
        parts[key]=s;hashes[str(f)]=sha(f)
    return m,parts,hashes


def cyl(radius,z0,z1,x,y):return cq.Solid.makeCylinder(radius,z1-z0,cq.Vector(x,y,z0))


def verify(baseline,manifest,output,*,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new report required')
    bmeta,base,h=read(baseline);meta,new,h2=read(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=sha(baseline):raise ValueError('wrong baseline')
    screws={f'{s}_ROOF_SCREW_{i}_M1_NOMINAL' for s in 'LR' for i in (0,1)}
    changed=screws|{'A_BACK_PANEL','L_GUIDE_REFERENCE','R_GUIDE_REFERENCE'}
    for key in set(base)-changed:equal(base[key],new[key])
    expected_panel=base['A_BACK_PANEL'];joints=[];cutters=[]
    spec=CatalogueScrew();seat=6.95-spec.length_under_head_mm
    for side in 'LR':
        x=(-1 if side=='L' else 1)*11.6;guide=base[side+'_GUIDE_REFERENCE']
        for i,y in enumerate((14.5,29.6)):
            hole=cyl(.95,-.1,seat,x,y);cutters.append(hole);expected_panel=expected_panel.cut(hole).clean();guide=guide.cut(hole).clean()
            expected=cyl(spec.head_diameter_mm/2,seat-spec.head_height_mm,seat,x,y).fuse(cyl(spec.diameter_mm/2,seat,6.95,x,y)).clean()
            role=f'{side}_ROOF_SCREW_{i}_M1_NOMINAL';equal(expected,new[role])
            # Directly recover the threaded-region carrier from native cylindrical faces.
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            holes=[]
            for face in new[side+'_ROOF'].Faces():
                if face.geomType()!='CYLINDER':continue
                carrier=BRepAdaptor_Surface(face.wrapped).Cylinder();origin=carrier.Location()
                if abs(carrier.Radius()-.5)<TOL and abs(origin.X()-x)<TOL and abs(origin.Y()-y)<TOL:
                    bb=face.BoundingBox();holes.append((bb.zmin,bb.zmax))
            if len(holes)!=1 or abs(holes[0][0]-5.7)>TOL or abs(holes[0][1]-7.)>TOL:
                raise ValueError('native female carrier mismatch')
            fit=axial_fit(seat,female_start_mm=holes[0][0],blind_end_mm=holes[0][1]);joints.append({'role':role,**fit})
        equal(guide,new[side+'_GUIDE_REFERENCE'])
    equal(expected_panel,new['A_BACK_PANEL'])
    if any(not j['nominal_axial_fit'] for j in joints):raise ValueError('catalogue dimensions do not fit')
    # Exact intersections with disjoint cutters avoid coincident whole-panel subtraction.
    for i,a in enumerate(cutters):
        for b in cutters[i+1:]:
            if common(a,b)>TOL:raise ValueError('cutters not disjoint')
    lost=math.fsum(common(base['A_BACK_PANEL'],c) for c in cutters)
    if abs(lost-meta['construction']['panel_removed_mm3'])>TOL or abs(vol(base['A_BACK_PANEL'])-lost-vol(new['A_BACK_PANEL']))>TOL:
        raise ValueError('panel disjoint-cutter material accounting mismatch')
    # Rejection of inserting the chosen 5mm screw at the original bearing plane.
    original_fit=axial_fit(.55)
    if original_fit['nominal_axial_fit'] or original_fit['nominal_axial_overlap_mm']!=0:raise ValueError('lost original short-screw rejection')
    actual_changed=screws|{'A_BACK_PANEL'}
    scenes=[]
    if full:
        import verify_endpoint_joint_pawl as e
        parent,prior,old,profiles=e.v.parent_native(h)
        slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
        for slide,descent,tabs in [(0.,0.,(0.,0.)),(0.,0.,(3.,3.)),(40.,0.,(3.,3.)),(79.75,8.2,(3.,3.))]:
            scenes.append(e.scene(new,parent,prior,old,profiles,slots,slide,descent,tabs))
    else:
        scenes=[{k:v for k,v in new.items() if not k.endswith('GUIDE_REFERENCE')}]
    checks=[];failures=[]
    for i,parts in enumerate(scenes):
        pairs={tuple(sorted((a,b))) for a in actual_changed for b in parts if a!=b}
        rows=[{'a':a,'b':b,'common_mm3':common(parts[a],parts[b])} for a,b in sorted(pairs)]
        failures.extend([{'scene':i,**r} for r in rows if r['common_mm3']>TOL])
        checks.append({'scene_index':i,'participants':len(parts),'changed_part_pairs':rows})
    # Exact swept union of two complete axial cylinders; not a sampled path.
    installed={k:v for k,v in scenes[0].items() if k not in ('A_FRAME','B_SHELL')};insertions=[];access=[]
    for role in sorted(screws):
        b=new[role].BoundingBox();x=(b.xmin+b.xmax)/2;y=(b.ymin+b.ymax)/2
        head=cyl(.9,1.5-10.,1.95,x,y);shaft=cyl(.5,1.95-10.,6.95,x,y);cage=head.fuse(shaft).clean()
        rows=[{'fixed':k,'common_mm3':common(cage,o)} for k,o in sorted(installed.items()) if k!=role]
        insertions.append({'role':role,'withdrawal_mm':10.,'checks':rows})
        failures.extend([{'insertion':role,**r} for r in rows if r['common_mm3']>TOL])
        # Reaches the nominal back face only, not an unmodeled Phillips recess.
        tool=cyl(.4,-10.,1.5,x,y)
        rows=[{'fixed':k,'common_mm3':common(tool,o)} for k,o in sorted(installed.items())]
        access.append({'role':role,'scope':'round tool shaft to back face only; actual drive engagement unknown','checks':rows})
        failures.extend([{'access':role,**r} for r in rows if r['common_mm3']>TOL])
    # Explicit process-error scenario, not an accepted tolerance or actuation.
    slope=1.06/3;lift=.02+.025*math.hypot(1,slope);witnesses=[]
    for side in 'LR':
        for dy in (-.02,.02):
            value=common(new[side+'_PAWL'].translate((0,dy,lift)),new[side+'_ROOT_OUTER'])
            if value<=TOL:raise ValueError('20um relative-location negative witness lost')
            witnesses.append({'side':side,'relative_Y_error_mm':dy,'PAWL_axial_mm':lift,'common_mm3':value,
                              'scope':'possible relative feature-location error in an explicit +/-50um scenario, not nominal guide travel'})
    # Measured native distance does not certify every point of a motion path.
    gaps=[new[s+'_PAWL'].translate((0,0,lift)).distance(new[s+'_ROOT_OUTER']) for s in 'LR']
    gap=min(gaps)
    generic=clearance_screen(gap,[('pawl_feature',1,.05),('root_feature',-1,.05)])
    proposed=clearance_screen(gap,[('pawl_feature',1,.005),('root_feature',-1,.005)])
    if generic['status'].startswith('certified') or proposed['status'].startswith('certified'):
        raise ValueError('small native clearance cannot certify these scenarios')
    if any(sha(f)!=v for f,v in h.items()):raise ValueError('input changed')
    if 'catalogue_roof_joint' in sys.modules:raise ValueError('candidate generator imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':sha(__file__),'input_sha256':h,
            'scope':'full prior scene' if full else 'local template subset only','native_templates':len(new),
            'candidate_builder_imported':False,'same_CAD_kernel':True,'parts_unchanged':len(base)-len(changed),
            'catalogue_fit':joints,'original_seat_rejection':original_fit,'panel_removed_mm3':lost,
            'scene_checks':checks,'screw_insertion_checks':insertions,'tool_shaft_access':access,
            'process_scenario_collision_witnesses':witnesses,'measured_endpoint_gap_mm':gap,
            'generic_vendor_tolerance_scenario':generic,'unqualified_5um_design_scenario':proposed,
            'nominal_geometry_passed':not failures,'failures':failures,'passed':not failures,
            'actual_process_preload_vendor_tolerances_or_threads_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'scope':result['scope'],'passed':result['passed'],'gap_mm':gap,'panel_removed_mm3':lost,'process_status':generic['status']}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full);raise SystemExit(0 if r['passed'] else 1)
