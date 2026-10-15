"""Catalogue M1 screw/nut seats in the existing frame, not thread qualification.

Four NBK SHNS-M1 nominal hex envelopes sit in top-loaded antirotation pockets.
Existing frame screw envelopes match SNZS-M1-3 catalogue outer dimensions.
Helical flanks, chamfers, strength, preload, locking and vendor size tolerances
are NOT inferred from the smooth clearance-hole representation used for CAD.
"""
from pathlib import Path
import argparse,json,math
import cadquery as cq
import verify_panel_shear_key as p
v=p.v
ROOT=Path(__file__).resolve().parents[1]
BASE='000972e84b80bc2c2022d87f86d2be46d58ddee0'
CENTERS=((-34.8,50.),(34.8,50.),(-34.8,70.),(34.8,70.))
NUT_AF=2.5
NUT_HEIGHT=.8
POCKET_AF=2.56
SEAT_Z=2.55
PITCH=.25
SCREW_LENGTH=3.
SCREW_SEAT=.55


def finite(*args):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in args):raise ValueError('finite real dimensions required')


def hex_prism(af,z0,z1,x=0.,y=0.):
    finite(af,z0,z1,x,y)
    if af<=0 or z1<=z0:raise ValueError('positive ordered hex dimensions required')
    radius=af/math.sqrt(3)
    pts=[(x+radius*math.cos(i*math.pi/3),y+radius*math.sin(i*math.pi/3)) for i in range(6)]
    return v.single(cq.Workplane('XY',origin=(0,0,z0)).polyline(pts).close().extrude(z1-z0).val())


def cylinder(radius,z0,z1,x,y):
    finite(radius,z0,z1,x,y)
    if radius<=0 or z1<=z0:raise ValueError('positive ordered cylinder dimensions required')
    return v.single(cq.Solid.makeCylinder(radius,z1-z0,cq.Vector(x,y,z0)))


def nominal_nut(x,y):
    return v.single(hex_prism(NUT_AF,SEAT_Z,SEAT_Z+NUT_HEIGHT,x,y).cut(cylinder(.5,SEAT_Z-.1,SEAT_Z+NUT_HEIGHT+.1,x,y)).clean())


def pocket(x,y):return hex_prism(POCKET_AF,SEAT_Z,4.4,x,y)


def dimensions():
    tip=SCREW_SEAT+SCREW_LENGTH
    return {'screw':'NBK SNZS-M1-3','nut':'NBK SHNS-M1','thread_nominal':'M1x0.25',
            'screw_seat_z_mm':SCREW_SEAT,'screw_tip_z_mm':tip,'nut_seat_z_mm':SEAT_Z,
            'nut_top_z_mm':SEAT_Z+NUT_HEIGHT,'nominal_axial_overlap_mm':min(tip,SEAT_Z+NUT_HEIGHT)-SEAT_Z,
            'nominal_tip_protrusion_mm':tip-SEAT_Z-NUT_HEIGHT,'nominal_nut_height_over_pitch':NUT_HEIGHT/PITCH,
            'actual_complete_engaged_threads':None,'chamfers_and_thread_runout_known':False,
            'screw_tightening_torque_Nm':None,'catalogue_max_torque_NOT_installation_setpoint_Nm':.02}


def build(base,frame,screws):
    expected={s+'_'+r for s in 'LR' for r in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')}|{'A_BACK_PANEL'}
    names={f'FRAME_{i}_M1x3_NOMINAL' for i in range(4)}
    if set(base)!=expected or set(screws)!=names:raise ValueError('complete25 templates and four actual frame screws required')
    before=v.single(frame);revised=before;result=dict(base);cuts=[]
    for i,(x,y) in enumerate(CENTERS):
        nominal=v.single(cylinder(.5,.55,3.55,x,y).fuse(cylinder(.9,.10,.55,x,y)).clean())
        v.equal(nominal,screws[f'FRAME_{i}_M1x3_NOMINAL'])
        cutter=v.single(pocket(x,y).fuse(cylinder(.55,1.1,4.4,x,y)).clean())
        volume=v.vol(revised.intersect(cutter))
        if volume<=1e-7:raise ValueError('nut seat misses original frame')
        revised=v.single(revised.cut(cutter).clean())
        cuts.append({'index':i,'center_xy_mm':[x,y],'frame_removed_mm3':volume})
        result[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL']=nominal_nut(x,y)
        result[f'FRAME_{i}_M1x3_NOMINAL']=screws[f'FRAME_{i}_M1x3_NOMINAL']
    result['A_FRAME']=revised
    lost=v.vol(before.cut(revised));added=v.vol(revised.cut(before))
    if added>1e-7 or abs(v.vol(before)-lost-v.vol(revised))>1e-7:raise ValueError('frame material balance differs')
    return result,{'only_existing_part_changed':'A_FRAME','new_physical_parts':4,'frame_removed_mm3':lost,'frame_added_mm3':added,'cuts':cuts,'connected_frame_solids':1}


def generate(baseline,output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output directory required')
    bm,base,h=p.w.w.w.load_new(baseline)
    if bm['source_sha256']!=v.sha(ROOT/'integration/panel_shear_key.py'):raise ValueError('not current panel-shear baseline')
    parent,prior,old,profiles=p.e.v.parent_native(h)
    slots={s:p.e.native_slot(base[s+'_TAB']) for s in 'LR'}
    home=p.w.scene(base,parent,prior,old,profiles,slots)
    screws={k:b for k,b in home.items() if k.startswith('FRAME_')}
    parts,material=build(base,home['A_FRAME'],screws);out.mkdir(parents=True,exist_ok=False);exports={}
    for name,body in parts.items():
        path=out/(name+'.step');cq.exporters.export(body,str(path));b=body.BoundingBox()
        exports[name]={'path':path.name,'sha256':v.sha(path),'volume_mm3':v.vol(body),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    if any(v.sha(f)!=value for f,value in h.items()):raise ValueError('native baseline changed')
    report={'base_main':BASE,'source_sha256':v.sha(__file__),'baseline_manifest_sha256':v.sha(baseline),'baseline_input_sha256':h,'exports':exports,'material':material,'dimensions':dimensions(),
            'catalogue_sources':['https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNZS-M/SNZS-M1/SNZS-M1-3/','https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SHNS/'],
            'nominal_catalogue_shapes_not_supplier_threaded_STEP':True,'unfastened_nuts_not_captive_against_upward_removal':True,'assembly_requires_bare_frame_rear_aperture_before_panel_and_B_installation':True,
            'actual_threads_preload_material_tolerances_and_strength_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();r=generate(a.baseline,a.output);print(json.dumps({'templates':len(r['exports']),'material':r['material'],'dimensions':r['dimensions']}))
