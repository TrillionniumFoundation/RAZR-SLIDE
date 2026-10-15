"""NBK SNZS-M1-5 nominal dimension-envelope integration, not supplier CAD.

Four counterbore seats move from Z=.55 to 1.95, retaining the prior 6.95 tip
and 1.25mm nominal overlap with a real catalogue 5mm length. No actual thread,
head recess, tolerances, fillet or preload is inferred from the envelope.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import cadquery as cq
from manufacturing_fit import CatalogueScrew, axial_fit

TOL=1e-7
SEAT=1.95
COUNTERBORE_RADIUS=.95
SPEC=CatalogueScrew()


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def volume(shape, *, empty=False):
    leaves=[]
    def visit(s):
        if not s.isValid():raise ValueError('invalid topology')
        if s.ShapeType()=='Solid':
            if not math.isfinite(s.Volume()) or s.Volume()<=0:raise ValueError('nonpositive solid')
            leaves.append(s)
        elif s.ShapeType() in ('Compound','CompSolid'):
            children=list(s)
            if not children and not empty:raise ValueError('empty topology')
            for child in children:visit(child)
        else:raise ValueError('free non-solid topology')
    visit(shape);raw=shape.Volume()
    if not math.isfinite(raw) or raw<0 or abs(math.fsum(s.Volume() for s in leaves)-raw)>TOL:
        raise ValueError('whole signed volume mismatch')
    return raw


def single(s):
    volume(s)
    if len(s.Solids())!=1:raise ValueError('one complete solid required')
    return s


def common(a,b):return volume(a.intersect(b),empty=True)


def cylinder(r,z0,z1,x,y):
    return single(cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0)))


def load(manifest):
    manifest=Path(manifest).resolve();meta=json.loads(manifest.read_text());parts={}
    roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL',
           'TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER')
    if set(meta['exports'])!={s+'_'+r for s in 'LR' for r in roles}|{'A_BACK_PANEL'}:
        raise ValueError('missing or extra complete participant')
    for role,rec in meta['exports'].items():
        rel=Path(rec['path']);f=manifest.parent/rel
        if rel.parts!=(role+'.step',) or f.is_symlink():raise ValueError('unsafe native path')
        if sha(f)!=rec['sha256']:raise ValueError('native bytes differ')
        values=[rec['volume_mm3'],*rec['bounds_mm']]
        if len(values)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
            raise ValueError('nonfinite certificate')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra native root')
        body=single(roots[0]);bb=body.BoundingBox()
        actual=[volume(body),bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]
        if any(abs(a-b)>TOL for a,b in zip(actual,values)):raise ValueError('native certificate mismatch')
        parts[role]=body
    return meta,parts


def build(old):
    new=dict(old);panel=old['A_BACK_PANEL'];rows=[]
    for side in 'LR':
        x=(-1 if side=='L' else 1)*11.6;guide=old[side+'_GUIDE_REFERENCE']
        for index,y in enumerate((14.5,29.6)):
            cutter=cylinder(COUNTERBORE_RADIUS,-.1,SEAT,x,y)
            panel=single(panel.cut(cutter).clean());guide=single(guide.cut(cutter).clean())
            body=cylinder(SPEC.head_diameter_mm/2,SEAT-SPEC.head_height_mm,SEAT,x,y)
            body=single(body.fuse(cylinder(SPEC.diameter_mm/2,SEAT,SEAT+SPEC.length_under_head_mm,x,y)).clean())
            name=f'{side}_ROOF_SCREW_{index}_M1_NOMINAL';new[name]=body
            rows.append({'role':name,'catalogue_part':SPEC.part_number,'model':'nominal dimension envelope, NOT actual max-material or supplier STEP'})
        new[side+'_GUIDE_REFERENCE']=guide
    new['A_BACK_PANEL']=panel
    if volume(panel.cut(old['A_BACK_PANEL']),empty=True)>TOL:raise ValueError('unexpected panel addition')
    return new,{'part_selection_scope':'catalogue dimensional design candidate only',
                'screws':rows,'unchanged_roof_boss_and_contact_parts':True,
                'counterbore_radius_mm':COUNTERBORE_RADIUS,'seat_mm':SEAT,
                'panel_removed_mm3':volume(old['A_BACK_PANEL'].cut(panel),empty=True),
                'old_seat_catalogue_rejection':axial_fit(.55),'revised_nominal_axial_fit':axial_fit(SEAT),
                'stock_verified_or_ordered':False,'vendor_dimensional_tolerances_known':False,
                'threads_drive_engagement_preload_strength_qualified':False}


def generate(baseline,output):
    output=Path(output).resolve();root=Path(__file__).resolve().parents[1]
    if output==root or root in output.parents:raise ValueError('new external output required')
    output.mkdir(parents=True,exist_ok=False);meta,old=load(baseline);new,detail=build(old);exports={}
    for name,body in new.items():
        path=output/(name+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':sha(path),'volume_mm3':volume(body),
            'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    report={'base_main':'8675f58640550b4e0ae8a3b3d08eb233173c92e2','source_sha256':sha(__file__),
            'baseline_manifest_sha256':sha(baseline),'baseline_source_sha256':meta['source_sha256'],
            'exports':exports,'construction':detail,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=generate(a.baseline,a.output);print(json.dumps(r['construction']))
