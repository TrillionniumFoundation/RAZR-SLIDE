"""Finite counterbore walls for the current back-panel, not strength release.

The existing 0.95 mm radius counterbores are tangent to guide walls at
x = +/-10.65 and +/-12.55. Add four fixed rectangular collars, preserving
all old material and the same screw/counterbore dimensions. This is a CAD
candidate; strength, manufacturing, contact and preload are not inferred.
"""
from pathlib import Path
import argparse,json,math
import cadquery as cq
import verify_frame_nut_anchor as n
v=n.v
ROOT=Path(__file__).resolve().parents[1]
BASE='42fc8149ffc7b5e5abf5588c60df97c5d9ee749c'
HALF_WIDTH=1.1
BORE_RADIUS=.95
BOTTOM=.60
TOP=2.00
ROLES=('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')
BODY_ROLES={s+'_'+r for s in 'LR' for r in ROLES}|{'A_BACK_PANEL'}


def web(x,y,half=HALF_WIDTH,radius=BORE_RADIUS,z0=BOTTOM,z1=TOP):
    vals=(x,y,half,radius,z0,z1)
    if any(type(a) not in (int,float) or not math.isfinite(a) for a in vals) or half<=radius or radius<=0 or z1<=z0:
        raise ValueError('finite collar with positive radial wall required')
    return (v.box((x-half,y-half,z0),(x-radius,y+half,z1)),
            v.box((x+radius,y-half,z0),(x+half,y+half,z1)))


def build(parts):
    expected=BODY_ROLES|{'A_FRAME'}|{f'FRAME_{i}_{r}' for i in range(4) for r in ('M1x3_NOMINAL','NUT_SHNS_M1_NOMINAL')}
    if set(parts)!=expected:raise ValueError('complete current34 templates required')
    result=dict(parts);panel=v.single(parts['A_BACK_PANEL']);rows=[]
    for side,sign in [('L',-1),('R',1)]:
        x=sign*11.6
        for index,y in enumerate((14.5,29.6)):
            for strip,collar in enumerate(web(x,y)):
                overlap=v.common(collar,panel)
                if overlap<=v.TOL:raise ValueError('web disconnected from panel')
                panel=v.single(panel.fuse(collar).clean())
                rows.append({'side':side,'index':index,'strip':strip,'center_xy_mm':[x,y],'initial_native_overlap_mm3':overlap})
    result['A_BACK_PANEL']=panel
    for k in ('A_BACK_PANEL',):
        if v.vol(parts[k].cut(result[k]))>v.TOL:raise ValueError('old material removed')
    return result,{'changed_templates':['A_BACK_PANEL'],'new_physical_parts':0,
                   'panel_added_mm3':v.vol(panel.cut(parts['A_BACK_PANEL'])),'panel_removed_mm3':0.,'joins':rows,
                   'counterbore_radius_mm':BORE_RADIUS,'collar_halfwidth_mm':HALF_WIDTH,'minimum_nominal_wall_mm':HALF_WIDTH-BORE_RADIUS,
                   'old_guide_halfwidth_minus_bore_mm':.95-BORE_RADIUS,'not_a_tolerance_or_strength_allowable':True}


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    bm,old,h=n.load(baseline,BODY_ROLES)
    if bm['source_sha256']!=v.sha(ROOT/'integration/frame_nut_anchor.py'):raise ValueError('wrong current-frame source binding')
    result,report=build(old);out.mkdir(parents=True,exist_ok=False);exports={}
    for key,body in result.items():
        path=out/(key+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[key]={'path':path.name,'sha256':v.sha(path),'volume_mm3':v.vol(body),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(v.sha(p)!=s for p,s in h.items()):raise ValueError('native baseline changed')
    m={'base_main':BASE,'source_sha256':v.sha(__file__),'baseline_manifest_sha256':v.sha(baseline),'exports':exports,'material':report,
       'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=generate(a.baseline,a.output);print(json.dumps(r['material']))
