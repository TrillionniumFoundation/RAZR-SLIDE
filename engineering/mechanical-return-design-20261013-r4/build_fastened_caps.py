#!/usr/bin/env python3
"""Actual R3-derived research cap fastener envelopes, not a qualified clamp.

NBK SNZS-M1-2 supplies nominal screw envelope dimensions. The screw and
thread-hole are deliberately neutral envelopes: detailed threads, tool access,
clamp load, manufacturing tolerances and strength require controlled drawings.
"""
from __future__ import annotations
import functools, hashlib, itertools, json, platform, sys, time
from pathlib import Path
import cadquery as cq
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[1]
BASE=REPO/'engineering/passive-veto-repair-20261013-r3'
sys.path.insert(0,str(BASE))
import passive_repair as r3
from strict_intersections import strict_common
from occ_signed_volume import validated_solid_volume
EPS=1e-7
SCREW={'manufacturer':'NBK','part':'SNZS-M1-2','nominal_thread_mm':1.,
       'nominal_pitch_mm':.25,'nominal_length_mm':2.,
       'nominal_head_diameter_mm':1.8,'nominal_head_height_mm':.45,
       'manufacturer_max_tightening_torque_Nm':.02,
       'target_tightening_torque_Nm':None,'clamp_load_N':None,
       'dimension_tolerances_mm':None,'actual_vendor_STEP_used':False,
       'nominal_envelope_derived_from_public_manufacturer_table':True}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def protected():return {str(p.relative_to(REPO)):sha(p) for p in sorted(BASE.rglob('*')) if p.is_file()}
def cyl(radius,height,x,q,r):return cq.Solid.makeCylinder(radius,height,cq.Vector(x,q,r),cq.Vector(0,0,1))
PAIR_CACHE={};CACHE_HITS=0;ACTUAL_PAIR_QUERIES=0
def cv(a,b):
    # A hash selects only a bucket. Real OCP isSame (TShape and Location) on
    # both retained immutable shapes is required before any cache reuse.
    # Retaining strong references avoids Python id recycling as identity.
    global CACHE_HITS,ACTUAL_PAIR_QUERIES
    key=(a.hashCode(),b.hashCode())
    for olda,oldb,value in PAIR_CACHE.get(key,[]):
        if a.isSame(olda) and b.isSame(oldb):
            CACHE_HITS+=1;return value
    value=strict_common(a,b)['checked_volume_mm3'];ACTUAL_PAIR_QUERIES+=1
    PAIR_CACHE.setdefault(key,[]).append((a,b,value));return value

@functools.lru_cache(maxsize=4)
def modified(port,side,variant='final'):
    old,dx=r3.static(port,side); out=dict(old); root=old['ROOT']
    Q=r3.qleaf(port)
    # Rejected compact location is kept and tested as a concrete counterexample.
    x=-2.60 if variant=='final' else -1.65
    positions=(x,-1.15),(x,Q-.10)
    fasteners={}
    for i,off in enumerate(r3.LEVELS):
        cap=old['CAP_'+str(i)+'_UNFASTENED']
        bosses=[];ears=[]
        for j,(e,q) in enumerate(positions):
            bosses.append(r3.world(cyl(.70,4.02,e,q,-1.+off),port,side))
            ears.append(r3.world(cyl(1.,.30,e,q,3.02+off),port,side))
        root=r3.fuse([root,*bosses]);cap=r3.fuse([cap,*ears])
        for j,(e,q) in enumerate(positions):
            # Nominal major-diameter thread envelope; no detailed thread or
            # pullout qualification is implied by this neutral CAD cavity.
            root=root.cut(r3.world(cyl(.5,2.70,e,q,1.+off),port,side)).clean()
            cap=cap.cut(r3.world(cyl(.55,.70,e,q,2.9+off),port,side)).clean()
            shank=cyl(.5,2.,e,q,1.32+off)
            head=cyl(.9,.45,e,q,3.32+off)
            fasteners[f'SCREW_{i}_{j}_NBK_SNZS_M1_2_NOMINAL_ENVELOPE']=r3.world(r3.fuse([shank,head]),port,side)
        del out['CAP_'+str(i)+'_UNFASTENED']
        out['CAP_'+str(i)+'_M1_INTERFACE_UNQUALIFIED']=cap
    out['ROOT']=root;out.update(fasteners)
    for s in out.values():validated_solid_volume(s)
    return out,dx

def scene(port,side,q=0.,retreat=0.,present=True,jam=None,variant='final'):
    p,dx=modified(port,side,variant);out={n:s for n,s in p.items() if n!='KEY'}
    out['PAWL']=p['PAWL'].translate((dx*retreat,0,0))
    for i in range(2):out['STOP_'+str(i)]=p['STOP_'+str(i)].translate(r3.delta_r(port,(jam or {}).get(i,r3.lift(q) if present else 0.)))
    if present:out['KEY']=p['KEY'].translate(r3.delta_q(port,q))
    return out

def new_names(p):return [n for n in p if n.startswith(('SCREW_','CAP_')) or n=='ROOT']
def added_pair_checks(p):
    changed=set(new_names(p))
    return [{'parts':[a,b],'common_mm3':cv(p[a],p[b])} for a,b in itertools.combinations(p,2) if a in changed or b in changed]

def save(p,name):
    a=cq.Assembly(name=name)
    for n,s in p.items():a.add(s,name=n)
    path=HERE/'cad'/f'{name}.step';a.save(str(path),exportType='STEP')
    leaves=cq.importers.importStep(str(path)).solids().vals()
    volumes=sorted(validated_solid_volume(s) for s in leaves)
    expected=sorted(validated_solid_volume(s) for s in p.values())
    if len(leaves)!=len(p) or any(abs(a-b)>1e-6 for a,b in zip(volumes,expected)):raise ValueError('STEP export count/volume mismatch')
    return {'path':str(path.relative_to(HERE)),'sha256':sha(path),'valid_positive_solids':len(leaves)}

def main():
    started=time.monotonic();before=protected();(HERE/'cad').mkdir(exist_ok=True)
    rows=[];rejected=[];exports=[]
    for port in ('STOW','OPEN'):
        for side in 'LR':
            # Source immutability and saved failed compact placement are part
            # of the executed evidence, rather than hiding its obstruction.
            p=scene(port,side,q=1.15,retreat=1.,variant='compact-rejected')
            bad=[x for x in added_pair_checks(p) if x['common_mm3']>EPS]
            rejected.append({'port':port,'side':side,'variant':'x=-1.65 compact bosses','actual_collisions':bad})
            for state,q,pres,jam in [('FULL',0,True,None),('SEAT_0p10',.1,True,None),('ABSENT',0,False,None),('PRIMARY_JAM_ABSENT',0,False,{0:1.2}),('SECONDARY_JAM_ABSENT',0,False,{1:1.2}),('DOUBLE_JAM_ABSENT_ESCAPE',0,False,{0:1.2,1:1.2})]:
                for i in range(23):
                    p=scene(port,side,q,i/22,pres,jam)
                    checked=added_pair_checks(p)
                    rows.append({'port':port,'side':side,'state':state,'fraction':i/22,'pairs':checked})
                print(json.dumps({'port':port,'side':side,'state':state,'rows_so_far':len(rows),'actual_pair_queries':ACTUAL_PAIR_QUERIES,'exact_identity_reuses':CACHE_HITS}),flush=True)
            for q in (0.,.02,.05,.10,.15,.20,.25,.4,.7,.8,1.,1.2,1.4,2.,4.,8.,12.):
                p=scene(port,side,q,1.)
                rows.append({'port':port,'side':side,'state':'NORMAL_KEY_WITHDRAW','q_mm':q,'pairs':added_pair_checks(p)})
            print(json.dumps({'port':port,'side':side,'completed_rows':len(rows)}),flush=True)
        for name,q,pres,jam,f in [('SEATED',0,True,None,0),('RELEASED',0,True,None,1),('ABSENT',0,False,None,0),('NORMAL_KEY_WITHDRAW_1p4',1.4,True,None,1)]:
            combined={}
            for side in 'LR':combined.update({side+'_'+n:s for n,s in scene(port,side,q,f,pres,jam).items()})
            exports.append(save(combined,port+'_'+name))
    unchanged=before==protected()
    bad=[{'port':r['port'],'side':r['side'],'state':r['state'],'fraction':r.get('fraction'),'q_mm':r.get('q_mm'),'pair':p} for r in rows for p in r['pairs'] if p['common_mm3']>EPS]
    report={'environment':{'host':platform.node(),'python':platform.python_version(),'cadquery':cq.__version__},'builder_sha256':sha(__file__),'protected_r3_members':len(before),'protected_r3_sha256':before,'protected_r3_bytes_unchanged':unchanged,'selected_nominal_screw_envelope':SCREW,'research_mounting_geometry':{'screw_center_x_mm':-2.60,'screw_centers_q_mm':'-1.15 and qleaf-.10','boss_radius_mm':.70,'cap_ear_radius_mm':1.,'cap_thickness_mm':.30,'nominal_neutral_thread_envelope_mm':1.,'cap_clearance_hole_mm':1.10,'proposed_thread_engagement_mm':1.70,'thread_geometry_validated':False},'actual_motion_rows':rows,'actual_motion_row_count':len(rows),'added_or_changed_pair_check_count':sum(len(r['pairs']) for r in rows),'unexpected_collision_rows':bad,'rejected_compact_boss_results':rejected,'STEP_exports':exports,'independent_return_spring_selected':None,'fail_closed_force_qualified':False,'finite_retraction_limit_N':None,'OEM_installation_validated':False,'fastener_tolerance_and_preload_qualified':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-started}
    report['actual_strict_pair_queries_including_rejected']=ACTUAL_PAIR_QUERIES
    report['exact_OCP_identity_cache_reuses_including_rejected']=CACHE_HITS
    report['cache_requires_isSame_for_both_shapes']=True
    (HERE/'build-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    if not unchanged:raise ValueError('Frozen R3 bytes changed')
    if bad:raise ValueError('New mounting geometry has actual collision; receipt kept')
    if not any(r['actual_collisions'] for r in rejected):raise ValueError('Expected compact boss counterexample not observed')
    print(json.dumps({'native_result':'completed','rows':len(rows),'pair_checks':report['added_or_changed_pair_check_count'],'STEP':len(exports),'unexpected_collisions':len(bad),'elapsed_seconds':report['elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
