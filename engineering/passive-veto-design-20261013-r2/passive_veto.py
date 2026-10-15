#!/usr/bin/env python3
"""Actual 1:1 research latch release interposers; hardware remains unqualified.

Each original pawl is extended with a release tab. Its OWN key coupon carries
a ramp that lifts its OWN guided stop. No position oracle authorizes movement.
All imposed contact positions are rigid research boundary conditions; neither
return force nor actual operation under friction is proven by these samples.
"""
from __future__ import annotations
import functools, hashlib, itertools, json, platform, sys
from pathlib import Path
import cadquery as cq

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PREVIOUS=REPO/'engineering/mechanical-closure-20261013'
BASE=REPO/'baselines/fpc-r39-20261013'
sys.dont_write_bytecode=True
sys.path.insert(0,str(PREVIOUS))
from mechanical_closure import fixture_parts, normalized_originals, blk
sys.path.insert(0,str(REPO/'engineering/cad-review-20261013'))
from occ_signed_volume import common, validated_solid_volume

EPS=1e-7
HYPOTHESIS={
 'cam_lift_mm':1.2, 'cam_lift_to_insert_ratio':2.0,
 'release_tab_r_height_mm':1.19, 'nominal_full_seat_clearance_mm':.01,
 'interposer_guide_gap_mm':.02,
 'all_dimensions_research_hypotheses':True,
 'OEM_dimensions_or_manufacturing_tolerances':False,
 'spring_return_curve_N_vs_mm':None,'friction_N_vs_mm':None,
 'capture_damage_limit_N':None,'force_limiter_upper_N':None,
 'material':None,'final_fasteners':None,
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_inventory():
    files=list(BASE.rglob('*'))+list(PREVIOUS.rglob('*'))
    return {str(p.relative_to(REPO)):sha(p) for p in sorted(files) if p.is_file()}
def cv(a,b): return common(a,b)['checked_volume_mm3']
def fuse(parts):
    s=parts[0]
    for p in parts[1:]: s=s.fuse(p)
    s=s.clean();validated_solid_volume(s);return s
def bounds(s):
    b=s.BoundingBox();return {k:float(getattr(b,k)) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}

def transform(s,port,side):
    """Canonical e=each-side pawl retreat, q=key withdraw, r=stop lift."""
    xc=-34.75 if side=='L' else 34.75
    sign=(-1 if side=='L' else 1) if port=='STOW' else (1 if side=='L' else -1)
    if sign<0: s=s.mirror('YZ')
    if port=='STOW':
        return s.mirror('XZ').translate((xc,1.2,10.))
    # q -> +Z, r -> +Y; exchanging axes is reflection + rigid rotation.
    return s.mirror('XZ').rotate((0,0,0),(1,0,0),-90).translate((xc,-10.,-6.))

def world(s,port,side):
    # Keep original untouched; transforms may be mirrors but never scaling.
    return transform(s,port,side)

def box(e0,e1,q0,q1,r0,r1): return blk(e0,e1,q0,q1,r0,r1)
def ramp():
    # Sketch q/r on YZ; extrude positive X to retain one valid positive solid.
    # A flat trailing land prevents the high ramp tail from hitting the lifted
    # crosspiece when the key is subsequently removed (retained r4 failure).
    profile=[(-.6,-.5),(.6,-.5),(.6,1.2),(.05,1.2),(-.6,-.1)]
    return cq.Workplane('YZ',origin=(-.6,0,0)).polyline(profile).close().extrude(.4).val()

@functools.lru_cache(maxsize=2)
def canonical_new_parts(port):
    qleaf=1.3 if port=='STOW' else 6.2
    # Nose touches the true ramp edge at q=+.05. At qwithdraw=0,
    # lift=1.2; every 0.01mm under-insertion reduces lift 0.02mm.
    stop=fuse([box(-.6,-.2,-.05,.05,0,1.8),
               box(-.6,.4,0,qleaf+.05,1.5,1.8),
               box(.2,.4,qleaf-.05,qleaf+.05,0,1.8)])
    if port=='STOW':
        adapter=box(-1.5,-1.1,-.05,.05,-3.2,-.4)
        stalk=box(-.1,0,qleaf-.05,qleaf+.05,-9.8,1.19)
        brace=box(-.1,0,qleaf-.05,qleaf+.05,-9.85,-9.77)
        root_q=(3.,3.2); root_r=(-11.06,-.8)
    else:
        adapter=box(-1.5,-1.1,-.05,.05,-.5,9.7)
        # OPEN actuator joins original stem on a separate q plane, not through
        # the lifted stop's spine. Its low link travels below the cleared stop.
        stalk=box(-.1,0,qleaf+.45,qleaf+.55,1.17,9.9)
        brace=box(-.1,0,qleaf+.04,qleaf+.55,1.0,1.19)
        root_q=(8.,8.2); root_r=(-.8,13.0)
    keycam=fuse([ramp(),adapter,box(-1.5,-.2,-.2,.6,-.6,-.4)])
    leaf=box(-.1,0,qleaf-.05,qleaf+.05,.1,1.19)
    tab=fuse([stalk,leaf,brace])
    base=box(-2.9,.8,-.25,root_q[1],-1.,-.8)
    # Open upper insertion channel with a separately removable retaining cap.
    rail=box(-1.,.8,-.25,qleaf+.25,-.8,3.02)
    cavity=box(-.62,.42,-.07,qleaf+.07,-.02,3.02)
    cam_slot=box(-1.52,-.18,-.61,1.61,-3.22,2.4)
    gate_slot=box(-.12,1.32,qleaf-.07,qleaf+(.07 if port=='STOW' else .57),
                  -10. if port=='STOW' else .08,
                  1.21)
    rail=rail.cut(cavity).cut(cam_slot).cut(gate_slot).clean()
    root=box(-2.9,-2.7,*root_q,*root_r)
    front_ear=box(-2.,2.,-.25,-.08,2.2,3.02)
    rear_ear=box(-2.,2.,qleaf+.08,qleaf+.25,2.2,3.02)
    guide=fuse([base,rail,root,front_ear,rear_ear]).cut(cam_slot).cut(gate_slot).clean()
    if port=='STOW':
        # Actual support-path perturbation found that the lower guide floor had
        # been removed for the release stalk. A connected under-bridge ledge
        # now arrests the stop's downward travel with the same .02mm research
        # gap. It is away from the release tab and the key/cam swept planes.
        guide=fuse([guide,box(.1,.8,.7,.9,1.21,1.48)])
    cap=box(-2.,2.,-.25,qleaf+.25,3.02,3.32).cut(gate_slot)
    # An OPEN adapter passes through the cap; key movement must remain possible.
    adapter_slot=box(-1.52,-1.08,-.07,1.61,3.,3.34)
    cap=cap.cut(adapter_slot).clean()
    # Four small through-hole placeholders: no thread, fastener, material or
    # preload is selected. They define a bench interface only.
    for e in (-1.7,1.7):
        for q in (-.165,qleaf+.165):
            tool=cq.Solid.makeCylinder(.075,1.6,cq.Vector(e,q,2.),cq.Vector(0,0,1))
            guide=guide.cut(tool).clean();cap=cap.cut(tool).clean()
    validated_solid_volume(guide);validated_solid_volume(cap)
    return {'STOP_INTERPOSER':stop,'KEY_CAM_ADAPTER':keycam,
            'PAWL_RELEASE_TAB':tab,'FIXED_INTERPOSER_ROOT':guide,
            'INTERPOSER_RETAINING_CAP_UNFASTENED':cap},qleaf

@functools.lru_cache(maxsize=4)
def static_parts(port,side):
    prev,dx=fixture_parts(port,side)
    raw,qleaf=canonical_new_parts(port)
    new={k:world(s,port,side) for k,s in raw.items()}
    for s in new.values(): validated_solid_volume(s)
    pawn=fuse([prev['PAWL_SLIDER'],new['PAWL_RELEASE_TAB']])
    fixed=fuse([prev['GUIDE_CARTRIDGE'],new['FIXED_INTERPOSER_ROOT']])
    cover=prev['REMOVABLE_COVER_UNFASTENED']
    if port=='STOW':
        cover=cover.cut(world(box(-2.92,-2.68,2.98,3.22,-8.,-6.),port,side)).clean()
        # The original key itself is preserved. New bench access removes a
        # guide/cover front-wall collision exposed during actual withdrawal.
        xc=prev['PAWL_SLIDER'].Center().x
        key_access=blk(xc-.22,xc+.22,-.82,2.5,-.72,3.02)
        fixed=fixed.cut(key_access).clean();cover=cover.cut(key_access).clean()
    validated_solid_volume(cover)
    if port=='STOW':
        original_key=normalized_originals(port,side)[0]
        narrow_grip=blk(xc-.18,xc+.18,.5,2.,2.95,7.)
        top_link=world(box(-1.5,.18,-.3,.4,-3.2,-3.),port,side)
        key=fuse([original_key,narrow_grip,top_link,new['KEY_CAM_ADAPTER']])
    else:
        key=fuse([prev['KEY_COUPON'],new['KEY_CAM_ADAPTER']])
    return {'PAWL_WITH_RELEASE_TAB':pawn,'FIXED_ROOT_AND_GUIDE':fixed,
         'COVER_WITH_RESEARCH_ROOT_SLOT_UNFASTENED':cover,
         'STOP_INTERPOSER':new['STOP_INTERPOSER'],'KEY_WITH_PRESENCE_CAM':key,
         'INTERPOSER_RETAINING_CAP_UNFASTENED':new['INTERPOSER_RETAINING_CAP_UNFASTENED']},dx,qleaf

def parts(port,side,key_depth_mm=0.,stop_lift_mm=None,pawl_fraction=0.,key_present=True):
    template,dx,qleaf=static_parts(port,side)
    lift=max(0.,1.2-2*key_depth_mm) if stop_lift_mm is None and key_present else (0. if stop_lift_mm is None else stop_lift_mm)
    lift_vec=(0,0,lift) if port=='STOW' else (0,lift,0)
    withdraw_vec=(0,-key_depth_mm,0) if port=='STOW' else (0,0,key_depth_mm)
    out={n:s for n,s in template.items() if n!='KEY_WITH_PRESENCE_CAM'}
    out['PAWL_WITH_RELEASE_TAB']=template['PAWL_WITH_RELEASE_TAB'].translate((dx*pawl_fraction,0,0))
    out['STOP_INTERPOSER']=template['STOP_INTERPOSER'].translate(lift_vec)
    if key_present: out['KEY_WITH_PRESENCE_CAM']=template['KEY_WITH_PRESENCE_CAM'].translate(withdraw_vec)
    return out,{'dx_mm':dx,'lift_mm':lift,'qleaf_mm':qleaf}

def pairs(parts):
    return [{'pair':[a,b],'common_mm3':cv(parts[a],parts[b])} for a,b in itertools.combinations(parts,2)]

def save(parts,path):
    assembly=cq.Assembly(name=path.stem)
    for n,s in parts.items(): validated_solid_volume(s);assembly.add(s,name=n)
    assembly.save(str(path),exportType='STEP')
    restored=cq.importers.importStep(str(path)).solids().vals()
    if len(restored)!=len(parts): raise ValueError('STEP solid count changed')
    vols=sorted(validated_solid_volume(s) for s in restored)
    if any(abs(a-b)>1e-6 for a,b in zip(vols,sorted(s.Volume() for s in parts.values()))): raise ValueError('STEP volumes changed')
    return {'path':str(path.relative_to(HERE)),'sha256':sha(path),'valid_positive_reimported_solids':len(restored),'manufacturing_go':False}

def main():
    before=source_inventory();(HERE/'cad').mkdir(exist_ok=True)
    rows=[];exports=[];coupled=[];assembly_rows=[];source_no_veto=[];independent_roots=[]
    for port in ('STOW','OPEN'):
      for side in 'LR':
        old,dx=fixture_parts(port,side)
        source_no_veto.append({'port':port,'side':side,'absent_key_parked_guide_common_mm3':cv(old['PAWL_SLIDER'].translate((dx,0,0)),old['GUIDE_CARTRIDGE']),
          'original_absent_key_full_retreat_unblocked':True})
        full,meta=parts(port,side)
        independent_roots.append({'port':port,'side':side,'single_material_connected_fixed_root_solid':len(full['FIXED_ROOT_AND_GUIDE'].Solids())==1,
          'original_root_positive_material_join_mm3':cv(full['FIXED_ROOT_AND_GUIDE'],old['GUIDE_CARTRIDGE']),
          'whole_root_volume_mm3':validated_solid_volume(full['FIXED_ROOT_AND_GUIDE']),
          'material_mounting_fastening_strength_not_qualified':True,
          'original_pawl_preserved_common_mm3':cv(full['PAWL_WITH_RELEASE_TAB'],old['PAWL_SLIDER']),
          'original_pawl_volume_mm3':validated_solid_volume(old['PAWL_SLIDER']),
          'original_key_preserved_common_mm3':cv(full['KEY_WITH_PRESENCE_CAM'],normalized_originals(port,side)[0]),
          'original_key_volume_mm3':validated_solid_volume(normalized_originals(port,side)[0])})
        for delta in (0.,.02,.1,.5,1.,3.,10.):
            # Insert stop with key absent and its retaining cap removed.
            no_key,_=parts(port,side,key_present=False)
            vector=(0,0,delta) if port=='STOW' else (0,delta,0)
            moving=no_key['STOP_INTERPOSER'].translate(vector)
            clashes={n:cv(moving,s) for n,s in no_key.items() if n not in ('STOP_INTERPOSER','INTERPOSER_RETAINING_CAP_UNFASTENED')}
            assembly_rows.append({'port':port,'side':side,'operation':'lower_stop_without_key_or_cap','raised_r_mm':delta,'clashes_mm3':clashes})
            cap=full['INTERPOSER_RETAINING_CAP_UNFASTENED'].translate(vector)
            clashes={n:cv(cap,s) for n,s in full.items() if n!='INTERPOSER_RETAINING_CAP_UNFASTENED'}
            assembly_rows.append({'port':port,'side':side,'operation':'lower_unfastened_cap_after_stop','raised_r_mm':delta,'clashes_mm3':clashes})
        for state,q,present,lift_override in [('FULL',0.,True,None),('PARTIAL_0p01',.01,True,None),('PARTIAL_0p05',.05,True,None),('PARTIAL_0p3',.3,True,None),('ABSENT',0.,False,None),('JAMMED_CLEAR_ABSENT',0.,False,1.2),('JAMMED_CLOSED_FULL',0.,True,0.)]:
          state_rows=[]
          for i in range(23):
            p,meta=parts(port,side,q,lift_override,i/22,present)
            collisions=pairs(p)
            state_rows.append({'fraction':i/22,'pawn_retreat_mm':abs(dx)*i/22,
              'stop_lift_mm':meta['lift_mm'],'all_pair_common':collisions,
              'stop_vs_pawl_common_mm3':cv(p['STOP_INTERPOSER'],p['PAWL_WITH_RELEASE_TAB']),
              'key_vs_stop_common_mm3':cv(p['KEY_WITH_PRESENCE_CAM'],p['STOP_INTERPOSER']) if present else None})
          rows.append({'port':port,'side':side,'state':state,'key_withdraw_mm':q,'key_present':present,
             'prescribed_stop_lift_is_rigid_contact_boundary_not_measured_return':True,
             'sampled_rows':state_rows,'full_release_interference_mm3':state_rows[-1]['stop_vs_pawl_common_mm3'],
             'max_path_interference_mm3':max(s['stop_vs_pawl_common_mm3'] for s in state_rows),
             'first_sampled_stop_contact_retreat_mm':next((s['pawn_retreat_mm'] for s in state_rows if s['stop_vs_pawl_common_mm3']>EPS),None),
             'release_path_geom_blocked':any(s['stop_vs_pawl_common_mm3']>EPS for s in state_rows),
             'failed_jam_safety_witness':state=='JAMMED_CLEAR_ABSENT'})
          print(json.dumps({'port':port,'side':side,'state':state,'path_max_stop_common_mm3':rows[-1]['max_path_interference_mm3']}),flush=True)
        # Both actual keys present: retreat pawls fully BEFORE withdrawing them.
        for i in range(16):
          fraction=min(1.,i/7);q=0. if i<=7 else (i-7)*.1
          p,meta=parts(port,side,q,None,fraction,True)
          coupled.append({'port':port,'side':side,'index':i,'pawn_fraction':fraction,'key_withdraw_mm':q,
              'stop_lift_mm':meta['lift_mm'],'pair_common':pairs(p),
              'sampled_not_continuous_and_no_force_qualification':True})
      for label,qL,qR,presentL,presentR,liftL,liftR,frac in [
        ('FULL_KEYS_CAPTURED',0,0,True,True,None,None,0),
        ('FULL_KEYS_RELEASED',0,0,True,True,None,None,1),
        ('ABSENT_BOTH_FORCE_RELEASE_FAILURE',0,0,False,False,None,None,1),
        ('LEFT_ONLY_FORCE_RIGHT_RELEASE_FAILURE',0,0,True,False,None,None,1),
        ('RIGHT_ONLY_FORCE_LEFT_RELEASE_FAILURE',0,0,False,True,None,None,1),
        ('PARTIAL_BOTH_0p05_FORCE_RELEASE_FAILURE',.05,.05,True,True,None,None,1),
        ('JAMMED_CLEAR_BOTH_ABSENT_ESCAPE',0,0,False,False,1.2,1.2,1),
        ('FULL_RELEASED_KEY_WITHDRAW_0p7',.7,.7,True,True,None,None,1)]:
         combined={}
         for side,q,pres,li in [('L',qL,presentL,liftL),('R',qR,presentR,liftR)]:
           actual_fraction=frac
           if ('FORCE_' in label and (not pres or q>0.)):
               actual_fraction=.35/abs(fixture_parts(port,side)[1])
           p,_=parts(port,side,q,li,actual_fraction,pres);combined.update({side+'_'+n:s for n,s in p.items()})
         exports.append(save(combined,HERE/'cad'/f'{port}_{label}.step'))
    after=source_inventory()
    if before!=after: raise ValueError('Protected prior source changed')
    report={'revision':'passive presence interposer actual research geometry r2','environment':{'host':platform.node(),'python':platform.python_version(),'cadquery':cq.__version__},
      'source_local_git_HEAD':'de3e982a04a3b4f62d0c301a9930aa9cd494cce5','source_hashes':before,'protected_source_members':len(before),'protected_source_bytes_unchanged':True,
      'controlled_research_dimensions':HYPOTHESIS,'absent_key_original_counterexamples':source_no_veto,'independent_material_root_rows':independent_roots,
      'actual_geometric_motion_rows':rows,'normal_release_then_key_withdraw_coupled_samples':coupled,'STEP_exports':exports,
      'sampled_stop_and_cap_assembly_paths':assembly_rows,
      'normal_key_withdraw_limit_mm':.8,'full_key_extraction_not_proven':True,
      'design_is_bench_only_not_phone_OEM_integration':True,'fail_closed_return_spring_qualification':False,'jammed_clear_fault_qualification':False,
      'drop_impact_contamination_breakage_strength_qualification':False,'limited_force_retraction_qualification':False,
      'fabrication_go':False,'manufacturing_go':False}
    (HERE/'passive-veto-receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    summary={'STEP_count':len(exports),'independent_root_count':len(independent_roots),'motion_state_count':len(rows),
      'release_sample_count':sum(len(r['sampled_rows']) for r in rows),'coupled_sample_count':len(coupled),
      'full_key_collision_samples':sum(v['common_mm3']>EPS for r in rows if r['state']=='FULL' for s in r['sampled_rows'] for v in s['all_pair_common']),
      'coupled_collision_samples':sum(v['common_mm3']>EPS for r in coupled for v in r['pair_common']),
      'assembly_collision_samples':sum(v>EPS for r in assembly_rows for v in r['clashes_mm3'].values()),
      'manufacturing_go':False}
    if summary['full_key_collision_samples'] or summary['coupled_collision_samples'] or summary['assembly_collision_samples']:
        raise ValueError('Nominal/assembly/coupled real geometry has an unresolved collision; receipt preserved')
    for row in rows:
        blocked=row['release_path_geom_blocked']
        if row['state'] in ('FULL','JAMMED_CLEAR_ABSENT') and blocked:
            raise ValueError('Expected clear release path is geometrically blocked')
        if row['state'] in ('PARTIAL_0p01','PARTIAL_0p05','PARTIAL_0p3','ABSENT','JAMMED_CLOSED_FULL') and not blocked:
            raise ValueError('Expected stop failed to block actual release path')
    for row in independent_roots:
        if abs(row['original_pawl_preserved_common_mm3']-row['original_pawl_volume_mm3'])>1e-6 or abs(row['original_key_preserved_common_mm3']-row['original_key_volume_mm3'])>1e-6:
            raise ValueError('Active original contact geometry was cut')
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__': main()
