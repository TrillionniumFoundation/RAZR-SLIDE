"""One current native phone study, with explicit part and space provenance.

Reuses all 83 current mechanical participants. Design allocation boxes are
separate named participants, never substituted for selected donor components.
The front direction follows the requested rear-stacked B geometry; historical
part names are preserved so an actuator/display conflict cannot be relabelled
away. A successful report means that the requested checks completed, not that
the phone or every allocation fitted.
"""
from __future__ import annotations

import argparse
import csv
from functools import lru_cache
import hashlib
import itertools
import json
import math
from pathlib import Path
import tarfile
import tempfile

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from straight_envelope import single, whole_material, fuse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'design/product_geometry.json'
TOL = 1e-7
BODY_ROLES = {s+'_'+r for s in 'LR' for r in (
    'PAWL', 'SHOULDER_PIN_NOMINAL', 'TAB', 'THUMB_PAD',
    'PAD_SCREW_M06_NOMINAL', 'ROOF', 'ROOF_SCREW_0_M1_NOMINAL',
    'ROOF_SCREW_1_M1_NOMINAL', 'GUIDE_REFERENCE', 'ROOT_OUTER',
    'ROOT_INNER', 'OLD_COVER')} | {'A_BACK_PANEL'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite real value required')
    return float(value)


def load_config(path=None):
    result = json.loads(Path(path or CONFIG).read_text())
    if result.get('schema') != 'razr-product-geometry-v1':
        raise ValueError('unrecognized product geometry schema')
    d = result['dimensions']
    if any(finite(v) <= 0 for v in d.values()):
        raise ValueError('positive study dimensions required')
    # The inherited 83-part scene is fixed to these dimensions. Different
    # dimensions require an actual regenerated baseline, not changed labels.
    expected = {'width_mm':73.99, 'height_mm':94.25, 'thickness_mm':8.0,
                'slide_mm':79.75, 'normal_seating_mm':8.2,
                'study_wall_mm':.65, 'study_clearance_mm':.2}
    if d != expected:
        raise ValueError('dimensions differ from the registered native baseline')
    names = set()
    for item in result.get('components', []):
        name = item['name']
        if not isinstance(name, str) or not name or name in names:
            raise ValueError('unique component names required')
        names.add(name)
        if item['cabin'] not in ('A', 'B'):
            raise ValueError('component cabin must be A or B')
        if item['source_kind'] not in ('design_space_allocation', 'supplier_nominal_envelope', 'measured_component'):
            raise ValueError('component provenance required')
        for key in ('lo_mm', 'hi_mm'):
            if len(item[key]) != 3:
                raise ValueError('three box coordinates required')
        if any(finite(b) <= finite(a) for a,b in zip(item['lo_mm'],item['hi_mm'])):
            raise ValueError('positive allocation box required')
        if item['source_kind'] == 'measured_component' and not item.get('measurement_record'):
            raise ValueError('measured geometry needs its measurement record')
        if item.get('capacity_mAh') is not None and not item.get('selected_part'):
            raise ValueError('capacity cannot be assigned to unselected space')
    for key in ('candidate_go','fixture_fabrication_go','manufacturing_go'):
        if result.get(key) is not False:
            raise ValueError('this study cannot issue a physical release')
    return result


def b_transform(slide_mm, descent_mm=0.0):
    s,d = finite(slide_mm),finite(descent_mm)
    if not 0 <= s <= 79.75 or not 0 <= d <= 8.2:
        raise ValueError('outside native B travel')
    if d > 0 and s != 79.75:
        raise ValueError('normal seating requires full slide')
    return (0.0,s,8.2-d)


def box(lo, hi):
    if len(lo)!=3 or len(hi)!=3 or any(finite(b)<=finite(a) for a,b in zip(lo,hi)):
        raise ValueError('positive finite box required')
    return single(cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo)))


def volume(shape):
    return whole_material(shape,empty=True)[1]


def bounds(shape):
    # STL tessellation mutates OCCT's mesh cache. BoundingBox() may then use
    # triangles and produce different certificates for unchanged native solids.
    # Bound the underlying geometry explicitly, without cached triangulation.
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape.wrapped,b,False,False)
    xmin,ymin,zmin,xmax,ymax,zmax=b.Get()
    return [xmin,xmax,ymin,ymax,zmin,zmax]


def strict_common(a,b):
    # Validate complete participants before any numerical broad-phase shortcut.
    a,b=single(a),single(b)
    aa,bb=bounds(a),bounds(b)
    gaps=[max(aa[2*i]-bb[2*i+1],bb[2*i]-aa[2*i+1]) for i in range(3)]
    if max(gaps)>0:
        return {'common_mm3':0.0,'method':'positive_axis_gap','axis_gap_lower_mm':max(gaps)}
    value=volume(a.intersect(b))
    if value<0 or value>min(volume(a),volume(b))+TOL:
        raise ValueError('invalid signed common volume')
    return {'common_mm3':value,'method':'native_common','axis_gap_lower_mm':0.0}


@lru_cache(maxsize=1)
def native_inputs():
    import verify_frame_nut_anchor as n
    cfg=load_config();rec=cfg['native_baseline'];arc=ROOT/rec['archive']
    if sha(arc)!=rec['sha256']:
        raise ValueError('current native archive changed')
    with tarfile.open(arc,'r:gz') as stream,tempfile.TemporaryDirectory(prefix='razr-product-current-') as td:
        folder=Path(td)
        members=stream.getmembers()
        if len({m.name for m in members})!=len(members):
            raise ValueError('duplicate archived member')
        for m in members:
            if not m.isfile() or Path(m.name).name!=m.name:
                raise ValueError('unsafe native member')
            (folder/m.name).write_bytes(stream.extractfile(m).read())
        meta,parts,_=n.load(folder/'manifest.json',BODY_ROLES)
    if len(parts)!=rec['templates']:
        raise ValueError('current native template count differs')
    hashes={}
    parent,prior,old,profiles=n.e.v.parent_native(hashes)
    slots={s:n.e.native_slot(parts[s+'_TAB']) for s in 'LR'}
    provenance={'base_commit':cfg['base_commit'],'archive':rec['archive'],
        'archive_sha256':sha(arc),'template_source_sha256':meta['source_sha256'],
        'source_inputs':{str(Path(p).relative_to(ROOT)):h for p,h in hashes.items()
                         if Path(p).is_relative_to(ROOT)},
        'templates':34,'expected_scene_participants':83,
        'material_geometry_changed':False}
    return parts,parent,prior,old,profiles,slots,provenance


def native_scene(slide_mm=0.0,descent_mm=0.0,left_tab_mm=0.0,right_tab_mm=0.0,*,flanks=(0,0),telescope_offsets=None):
    import verify_endpoint_joint_pawl as e
    import verify_cam_coupling as cam
    b_transform(slide_mm,descent_mm)
    tabs=(finite(left_tab_mm),finite(right_tab_mm))
    if any(not 0<=x<=3 for x in tabs) or len(flanks)!=2 or any(finite(x) not in (-1,0,1) for x in flanks):
        raise ValueError('invalid independent manual controls or slot flank')
    parts,parent,prior,old,profiles,slots,provenance=native_inputs()
    state=e.scene(parts,parent,prior,old,profiles,slots,slide_mm,descent_mm,tabs,flanks=flanks)
    for s in 'LR':
        state[s+'_ROOT_INNER']=parts[s+'_ROOT_INNER']
        state[s+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=parts[s+'_ROOT_OUTER']
        state[s+'_OLD_COVER']=parts[s+'_OLD_COVER']
    state['A_FRAME']=parts['A_FRAME']
    for i in range(4):
        for role in ('M1x3_NOMINAL','NUT_SHNS_M1_NOMINAL'):
            k=f'FRAME_{i}_{role}';state[k]=parts[k]
    if telescope_offsets is not None:
        actual=cam.prototype(prior,slide_mm,descent_mm,offsets=telescope_offsets)
        for s in 'LR':
            for i in range(1,4):state[f'{s}_TELESCOPE_{i}']=actual[f'{s}_TELESCOPE_{i}']
    if len(state)!=83:
        raise ValueError('incomplete current mechanical scene')
    return state,{**provenance,'slide_mm':slide_mm,'descent_mm':descent_mm,
        'left_tab_mm':tabs[0],'right_tab_mm':tabs[1],'slot_flanks':list(flanks),
        'B_translation_mm':b_transform(slide_mm,descent_mm),
        'telescope_allocation':'nominal equal allocation, not physically enforced' if telescope_offsets is None else 'explicit admissible joint allocation',
        'physical_holding_and_force_qualified':False}


def registered_components(config=None,slide_mm=0.0,descent_mm=0.0):
    config=config or load_config();shift=b_transform(slide_mm,descent_mm)
    return {row['name']:box(row['lo_mm'],row['hi_mm']).translate(shift if row['cabin']=='B' else (0,0,0))
            for row in config['components']}


def cylinder(radius,z0,z1,x,y):
    return single(cq.Solid.makeCylinder(radius,z1-z0,cq.Vector(x,y,z0)))


def nominal_screw(x,y,shaft_radius,head_radius,z0,head_end,tip):
    body=fuse([cylinder(head_radius,z0,head_end,x,y),cylinder(shaft_radius,head_end,tip,x,y)])
    slit=box((x-head_radius-.05,y-.10,z0-.01),(x+head_radius+.05,y+.10,z0+.10))
    return single(body.cut(slit).clean())


@lru_cache(maxsize=1)
def product_templates():
    """Explicit product candidate material, with no edits to frozen templates.

    Two replaceable pads keep the existing M0.6 attachment. Each side bridge
    is installed afterwards on two new panel bosses. OPEN uses two separate
    manually installed nominal screws; their helical threads are not modeled.
    OLED channel cuts are an investigated geometry, not a strength release.
    """
    original,_=native_scene();new={};accounts={}
    panel=original['A_BACK_PANEL'];frame=original['A_FRAME']
    b=original['B_SHELL'].translate((0,0,-8.2))
    cfg=load_config()['current_product_candidate']
    channel=cfg['OLED_channels']
    a_window=box(*channel['A_head_turn_window_lo_hi_mm'])
    panel=single(panel.cut(a_window).clean());frame=single(frame.cut(a_window).clean())
    b=single(b.cut(box(*channel['B_return_lap_channel_lo_hi_mm'])).cut(box(*channel['B_front_turn_window_lo_hi_mm'])).clean())
    for side,sign in (('L',-1),('R',1)):
        handed=lambda body:single(body.mirror('YZ')) if sign<0 else body
        pad=original[side+'_THUMB_PAD']
        arm=handed(box((9.,23.2,-.75),(36.995,25.4,-.15)))
        joint=handed(box((9.,23.2,-.20),(12.45,25.4,.25)))
        if strict_common(pad,joint)['common_mm3']<=TOL:
            raise ValueError('side arm does not join original detachable pad')
        updated=fuse([pad,joint,arm])
        updated=single(updated.cut(cylinder(.575,-.80,.25,sign*11.6,24.5)).clean())
        if volume(pad.cut(updated))>TOL:raise ValueError('original pad attachment material lost')
        new[side+'_THUMB_PAD']=updated
        bridge=fuse([box((33.4,22.8,-1.05),(35.6,28.8,-.85)),
                     box((33.4,22.8,-1.00),(35.6,23.0,0.)),
                     box((33.4,28.6,-1.00),(35.6,28.8,0.)),
                     box((33.4,20.5,-.4),(35.6,23.0,0.)),
                     box((33.4,28.6,-.4),(35.6,31.1,0.))])
        for index,y in enumerate((21.6,30.0)):
            x=sign*34.5
            boss=cylinder(1.1,.60,2.15,x,y)
            if strict_common(panel,boss)['common_mm3']<=TOL:raise ValueError('panel boss disconnected')
            panel=single(panel.fuse(boss).cut(cylinder(.5,-.05,1.85,x,y)).clean())
            bridge=single(bridge.cut(cylinder(.55,-.5,.1,34.5,y)).clean())
            new[f'{side}_SIDE_GUIDE_{index}_M1_NOMINAL']=nominal_screw(x,y,.5,.9,-.85,-.4,1.8)
        new[side+'_SIDE_GUIDE']=handed(bridge)
        # The existing overlap faces have 0.2 mm separation. A finite annular
        # shoulder gives a nominal seated datum in both normal directions once
        # the specified threaded connection holds the screw in A.
        x=sign*34.5
        shoulder=cylinder(1.2,3.85,4.1,x,87.)
        if strict_common(frame,shoulder)['common_mm3']<=TOL:raise ValueError('OPEN shoulder disconnected')
        frame=single(frame.fuse(shoulder).cut(cylinder(.5,1.2,4.2,x,87.)).clean())
        b=single(b.cut(cylinder(.55,4.05,8.05,x,7.25)).cut(cylinder(.95,7.45,8.05,x,7.25)).clean())
        # A head at the positive-Z surface is reversed relative to the other
        # nominal screws. The smooth shaft only specifies the thread envelope.
        lock=fuse([cylinder(.5,1.25,7.45,x,87.),cylinder(.9,7.45,7.95,x,87.)])
        slit=box((x-1.,86.9,7.85),(x+1.,87.1,7.96))
        new[side+'_OPEN_HOLD_M1_NOMINAL']=single(lock.cut(slit).clean())
        # Matching fixed-body front depth on B. In STOW these side rims nest
        # in an explicitly removed A rear-edge corridor; the current inner
        # mechanism is retained. The rim is part of B, not an invisible box.
        rim=handed(box((35.8,14.7,-1.15),(36.995,94.25,.1)))
        if strict_common(b,rim)['common_mm3']<=TOL:raise ValueError('B front rim disconnected')
        b=single(b.fuse(rim).clean())
        recess=handed(box((35.65,-.1,6.9),(37.1,94.4,8.1)))
        frame=single(frame.cut(recess).clean());panel=single(panel.cut(recess).clean())
    # Right-side admission for the separate OPEN support insert. The head rim
    # remains at full height; a hypothetical uncut full side rim is retained
    # as an obstruction witness by the motion report.
    b=single(b.cut(box((35.7,14.6,-1.2),(37.1,85.65,.05))).clean())
    # Two flat guide surfaces retain the B-local return sheet with 0.05 mm
    # nominal normal gaps. They are connected to the original solid lap.
    for z0,z1 in ((5.65,5.85),(6.15,6.35)):
        plate=box((-33.7,5.4,z0),(33.7,85.9,z1))
        if strict_common(b,plate)['common_mm3']<=TOL:raise ValueError('return guide is floating')
        b=single(b.fuse(plate).clean())
    # A's detachable front support is installed after side controls. Four
    # screw axes sit outside the 67 mm trial display and retain tool access.
    a_support=box((-33.5,2.,-1.15),(33.5,85.65,-.95))
    b_support=box((-33.5,5.95,-1.10),(33.5,85.6,-.1))
    for side,sign in (('L',-1),('R',1)):
        handed=lambda body:single(body.mirror('YZ')) if sign<0 else body
        # Local guide clearance avoids a real small intersection at the
        # bridge/plate edge; no participant is omitted from the collision set.
        a_support=single(a_support.cut(handed(box((33.35,22.7,-1.2),(33.6,28.9,-.9)))).clean())
        for index,y in enumerate((42.,76.)):
            x=sign*34.5;foot=handed(box((33.,y-1.1,-1.15),(35.6,y+1.1,0.)))
            a_support=single(a_support.fuse(foot).cut(cylinder(.55,-1.2,.1,x,y)).cut(cylinder(.95,-1.2,-.4,x,y)).clean())
            boss=cylinder(1.1,.6,2.15,x,y)
            if strict_common(panel,boss)['common_mm3']<=TOL:raise ValueError('A support boss disconnected')
            panel=single(panel.fuse(boss).cut(cylinder(.5,-.1,1.85,x,y)).clean())
            new[f'{side}_A_SUPPORT_{index}_M1_NOMINAL']=nominal_screw(x,y,.5,.9,-.85,-.4,1.8)
        for index,y in enumerate((40.,70.)):
            x=sign*34.5;foot=handed(box((33.,y-1.1,-.4),(35.6,y+1.1,0.)))
            b_support=single(b_support.fuse(foot).cut(cylinder(.55,-1.2,.1,x,y)).clean())
            boss=cylinder(1.1,.6,2.15,x,y)
            if strict_common(b,boss)['common_mm3']<=TOL:raise ValueError('B support boss disconnected')
            b=single(b.fuse(boss).cut(cylinder(.5,-.1,1.85,x,y)).clean())
            new[f'{side}_B_SUPPORT_{index}_M1_NOMINAL']=nominal_screw(x,y,.5,.9,-.85,-.4,1.8)
    new['A_DISPLAY_SUPPORT']=a_support;new['B_OPEN_DISPLAY_SUPPORT_ACCESSORY']=b_support
    new.update({'A_BACK_PANEL':panel,'A_FRAME':frame,'B_SHELL':b})
    for name in cfg['changed_native_parts']:
        before=original[name].translate((0,0,-8.2)) if name=='B_SHELL' else original[name]
        after=new[name];loss=volume(before.cut(after));gain=volume(after.cut(before))
        if abs(volume(before)-loss+gain-volume(after))>TOL:raise ValueError('product material accounting differs')
        accounts[name]={'original_mm3':volume(before),'removed_mm3':loss,'added_mm3':gain,'new_mm3':volume(after)}
    return new,{'changed_native_parts':cfg['changed_native_parts'],'unchanged_native_parts':78,
                'added_guide_parts':6,'added_A_support_parts':5,'optional_separate_B_OPEN_support_parts':5,
                'optional_separate_OPEN_screws':2,'material_accounting':accounts,
                'source_sha256':sha(__file__),'configuration_sha256':sha(CONFIG),
                'nominal_thread_connections_specified_not_geometrically_retained':True,
                'machinability_strength_preload_and_screen_support_qualified':False}


def product_scene(slide_mm=0.0,descent_mm=0.0,left_tab_mm=0.0,right_tab_mm=0.0,*,flanks=(0,0),telescope_offsets=None,open_hold=False,open_support=False):
    """The common product candidate obstacle field used by OLED and FPC.

    Returns 94 installed mechanical pieces before optional OPEN accessories,
    101 with the support insert, its four screws and two hold screws. Loose accessories are not silently
    treated as onboard storage. Component allocations and OLED are separate
    named participants so their intersection tests remain explicit.
    """
    if type(open_hold) is not bool or type(open_support) is not bool:raise ValueError('OPEN accessory state must be explicit')
    if (open_hold or open_support) and (slide_mm!=79.75 or descent_mm!=8.2):
        raise ValueError('OPEN accessories can only be installed at seated OPEN')
    state,meta=native_scene(slide_mm,descent_mm,left_tab_mm,right_tab_mm,flanks=flanks,telescope_offsets=telescope_offsets)
    new,changes=product_templates()
    state['A_FRAME']=new['A_FRAME'];state['A_BACK_PANEL']=new['A_BACK_PANEL']
    state['B_SHELL']=new['B_SHELL'].translate(b_transform(slide_mm,descent_mm))
    for side,u in (('L',left_tab_mm),('R',right_tab_mm)):
        state[side+'_THUMB_PAD']=new[side+'_THUMB_PAD'].translate((0,u,0))
        for role in ('SIDE_GUIDE','SIDE_GUIDE_0_M1_NOMINAL','SIDE_GUIDE_1_M1_NOMINAL'):
            state[side+'_'+role]=new[side+'_'+role]
        for index in (0,1):state[f'{side}_A_SUPPORT_{index}_M1_NOMINAL']=new[f'{side}_A_SUPPORT_{index}_M1_NOMINAL']
        if open_support:
            for index in (0,1):
                name=f'{side}_B_SUPPORT_{index}_M1_NOMINAL';state[name]=new[name].translate(b_transform(slide_mm,descent_mm))
        if open_hold:state[side+'_OPEN_HOLD_M1_NOMINAL']=new[side+'_OPEN_HOLD_M1_NOMINAL']
    state['A_DISPLAY_SUPPORT']=new['A_DISPLAY_SUPPORT']
    if open_support:state['B_OPEN_DISPLAY_SUPPORT_ACCESSORY']=new['B_OPEN_DISPLAY_SUPPORT_ACCESSORY'].translate(b_transform(slide_mm,descent_mm))
    expected=94+(2 if open_hold else 0)+(5 if open_support else 0)
    if len(state)!=expected:raise ValueError('product candidate participant omission')
    return state,{**meta,
                 'native_baseline_expected_scene_participants':meta['expected_scene_participants'],
                 'native_baseline_material_geometry_changed':meta['material_geometry_changed'],
                 'expected_scene_participants':len(state),'material_geometry_changed':True,
                 'product_changes':changes,'installed_mechanical_parts':expected,
                 'OPEN_hold_screws_installed':open_hold,'OPEN_thread_retention_load_qualified':False,
                 'OPEN_display_support_insert_installed':open_support,
                 'loose_OPEN_accessories_have_onboard_storage':False,
                 'complete_functional_phone':False,'candidate_go':False,'manufacturing_go':False}


def source_unchanged(provenance):
    return all(sha(ROOT/p)==h for p,h in provenance['source_inputs'].items()) and sha(ROOT/provenance['archive'])==provenance['archive_sha256']


def export_scene(output,*,slide_mm=0.0,descent_mm=0.0,left_tab_mm=0.0,right_tab_mm=0.0,include_components=True):
    output=Path(output).resolve()
    if output.exists() or output==ROOT or ROOT in output.parents:
        raise ValueError('use a new output outside source')
    config=load_config();parts,meta=native_scene(slide_mm,descent_mm,left_tab_mm,right_tab_mm)
    native_names=set(parts)
    if include_components:parts.update(registered_components(config,slide_mm,descent_mm))
    output.mkdir(parents=True);exports={}
    for name,part in sorted(parts.items()):
        f=output/(name+'.step');cq.exporters.export(single(part),str(f))
        exports[name]={'path':f.name,'sha256':sha(f),'volume_mm3':volume(part),'bounds_mm':bounds(part),
                       'role':'native_mechanical_part' if name in native_names else 'design_space_allocation'}
    assembly=cq.Assembly(name='RAZR_CURRENT_PRODUCT_STUDY')
    for name,part in sorted(parts.items()):assembly.add(part,name=name)
    combined=output/'product-assembly.step';assembly.export(str(combined))
    if not source_unchanged(meta):raise ValueError('native input changed')
    result={'schema':'razr-product-export-v1','source_sha256':sha(__file__),'configuration_sha256':sha(CONFIG),
        'mechanical':meta,'exports':exports,'combined':{'path':combined.name,'sha256':sha(combined)},
        'component_register':config['components'],'missing_functional_geometry':config['missing_functional_geometry'],
        'complete_functional_phone':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def packing_report(config=None):
    config=config or load_config();rows=[];failures=[]
    for pose,s,d,u in [('STOW',0.,0.,0.),('PREDOCK',79.75,0.,3.),('OPEN_SEATED',79.75,8.2,3.)]:
        parts,meta=native_scene(s,d,u,u);allocations=registered_components(config,s,d)
        for name,a in allocations.items():
            comparisons=[]
            for obstacle,b in sorted(parts.items()):
                try:r=strict_common(a,b);r.update({'obstacle':obstacle})
                except Exception as exc:r={'obstacle':obstacle,'error':type(exc).__name__+': '+str(exc),'rejected':True}
                if r.get('common_mm3',0)>TOL or r.get('rejected'):failures.append({'pose':pose,'allocation':name,**r})
                comparisons.append(r)
            rows.append({'pose':pose,'allocation':name,'volume_mm3':volume(a),'comparisons':comparisons})
        for (na,a),(nb,b) in itertools.combinations(sorted(allocations.items()),2):
            r=strict_common(a,b)
            if r['common_mm3']>TOL:failures.append({'pose':pose,'allocation':na,'other_allocation':nb,**r})
    return {'scope':'three registered native states, not continuous motion or selected component fit',
        'mechanical_participants':83,'allocation_names':[r['name'] for r in config['components']],
        'rows':rows,'rejected_pairs':failures,'allocations_clear_at_sampled_states':not failures,
        'selected_battery_capacities_known':False,'donor_component_fit_verified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}


def export_product_scene(output,*,slide_mm=0.,descent_mm=0.,left_tab_mm=0.,right_tab_mm=0.,open_hold=False,open_support=False):
    """Native STEP and visualization meshes for the complete declared study."""
    import oled_storage
    out=Path(output).resolve()
    if out.exists() or out==ROOT or ROOT in out.parents:raise ValueError('new external output directory required')
    input_hashes={'integration/product_assembly.py':sha(__file__),
                  'integration/oled_storage.py':sha(oled_storage.__file__),'design/product_geometry.json':sha(CONFIG)}
    config=load_config();parts,meta=product_scene(slide_mm,descent_mm,left_tab_mm,right_tab_mm,open_hold=open_hold,open_support=open_support)
    native_names=set(parts);parts.update(registered_components(config,slide_mm,descent_mm));sheet,screen=oled_storage.geometry(slide_mm,descent_mm)
    parts['OLED_GEOMETRIC_TRIAL']=sheet;out.mkdir(parents=True);rows={};bom=[]
    assembly=cq.Assembly(name='RAZR_PRODUCT_INTEGRATION_STUDY')
    for name,part in sorted(parts.items()):
        step=out/(name+'.step');mesh=out/(name+'.stl');cq.exporters.export(single(part),str(step));cq.exporters.export(single(part),str(mesh),tolerance=.03,angularTolerance=.1)
        role='mechanical_candidate' if name in native_names else ('dummy_strip_geometry' if name=='OLED_GEOMETRIC_TRIAL' else 'design_space_allocation')
        rows[name]={'path':step.name,'sha256':sha(step),'volume_mm3':volume(part),'bounds_mm':bounds(part),'role':role,
                    'mesh':{'path':mesh.name,'sha256':sha(mesh),'deflection_mm':.03,'manufacturing_approval':False}}
        assembly.add(part,name=name)
        bom.append({'name':name,'quantity':1,'role':role,'material':'unselected; nominal fasteners are geometry envelopes only',
                    'STEP':step.name,'STL':mesh.name,'make_from_this_mesh_without_review':'NO'})
    combined=out/'product-assembly.step';assembly.export(str(combined))
    with (out/'assembly-BOM.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(bom[0]));writer.writeheader();writer.writerows(bom)
    if any(sha(ROOT/rel)!=value for rel,value in input_hashes.items()) or not source_unchanged(meta):raise ValueError('input changed during export')
    result={'schema':'razr-product-export-v1','generator_source_sha256':input_hashes,'mechanical':meta,'OLED':screen,
            'exports':rows,'combined':{'path':combined.name,'sha256':sha(combined),'expected_solid_count':len(parts)},
            'component_register':config['components'],'BOM_sha256':sha(out/'assembly-BOM.csv'),
            'selected_donor_OLED_battery_and_populated_PCB':False,
            'thin_regions_not_ordinary_FDM_qualified':{'A_front_plate_mm':.2,'side_arm_mm':.6,'B_return_guides_mm':.2,
                'inherited_KEY_arm_section_mm':[.25,.30],'inherited_cover_min_wall_mm':.17,'inherited_bearing_wall_mm':.15},
            'complete_functional_phone':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--slide',type=float,default=0.)
    parser.add_argument('--descent',type=float,default=0.)
    parser.add_argument('--left-tab',type=float,default=None)
    parser.add_argument('--right-tab',type=float,default=None)
    parser.add_argument('--baseline',action='store_true',help='explicitly export the unchanged 83-piece inherited scene')
    parser.add_argument('--open-hold',action='store_true',help='include the two separate OPEN hold screws')
    parser.add_argument('--open-support',action='store_true',help='include the separate OPEN support plate and four screws')
    parser.add_argument('--packing',action='store_true')
    args=parser.parse_args()
    default_tab=3. if args.slide or args.descent else 0.
    left=default_tab if args.left_tab is None else args.left_tab
    right=default_tab if args.right_tab is None else args.right_tab
    if args.baseline:
        if args.open_hold or args.open_support:parser.error('OPEN product accessories are not baseline participants')
        r=export_scene(args.output,slide_mm=args.slide,descent_mm=args.descent,left_tab_mm=left,right_tab_mm=right)
    else:
        r=export_product_scene(args.output,slide_mm=args.slide,descent_mm=args.descent,left_tab_mm=left,right_tab_mm=right,
                               open_hold=args.open_hold,open_support=args.open_support)
    if args.packing:
        if args.baseline:report=packing_report()
        else:
            import product_motion
            report=product_motion.verify()
        (args.output/'packing-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'exported_parts':len(r['exports']),'mechanical_parts':r['mechanical'].get('installed_mechanical_parts',83),
                      'explicit_native_baseline':args.baseline,'complete_functional_phone':False}))
