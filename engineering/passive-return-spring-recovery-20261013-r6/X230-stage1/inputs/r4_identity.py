#!/usr/bin/env python3
"""Independently import all exported R4 STEP branches; no CAD builder import."""
from __future__ import annotations
import hashlib,itertools,json,math,platform,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.TopAbs import TopAbs_COMPOUND,TopAbs_COMPSOLID,TopAbs_SOLID
from OCP.TopoDS import TopoDS_Iterator
from strict_intersections import CheckedBody,Checker
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent;EPS=1e-7
CASES={'SEATED':(True,0.,(1.2,1.2)), 'RELEASED':(True,0.,(1.2,1.2)),
       'ABSENT':(False,0.,(0.,0.)), 'NORMAL_KEY_WITHDRAW_1p4':(True,1.4,(0.,0.))}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(b,port,side):
    box=b.bounds;xc=-34.75 if side=='L' else 34.75
    sign=(-1 if side=='L' else 1) if port=='STOW' else (1 if side=='L' else -1)
    return {'e':sorted(sign*(v-xc) for v in box['x']),
            'q':sorted(1.2-v for v in box['y']) if port=='STOW' else [v+6 for v in box['z']],
            'r':[v-10 for v in box['z']] if port=='STOW' else [v+10 for v in box['y']]}
def qvec(port,v):return (0,-v,0) if port=='STOW' else (0,0,v)
def rvec(port,v):return (0,0,v) if port=='STOW' else (0,v,0)
def evec(port,side,v):
    sign=(-1 if side=='L' else 1) if port=='STOW' else (1 if side=='L' else -1)
    return (sign*v,0,0)

def import_whole(path):
    roots=cq.importers.importStep(str(path)).vals();bodies=[];nodes=0
    def visit(s):
        nonlocal nodes
        if not s.isValid():raise ValueError('Invalid entire STEP topology node')
        kind=s.wrapped.ShapeType()
        if kind==TopAbs_SOLID:bodies.append(CheckedBody(s));return
        if kind not in (TopAbs_COMPOUND,TopAbs_COMPSOLID):raise ValueError('Free non-solid STEP branch rejected')
        it=TopoDS_Iterator(s.wrapped);children=[];nodes+=1
        while it.More():children.append(cq.Shape.cast(it.Value()));it.Next()
        if not children:raise ValueError('Empty free compound rejected')
        for child in children:visit(child)
    for root in roots:visit(root)
    total=sum(b.volume for b in bodies);raw=sum(r.Volume() for r in roots)
    if not bodies or not math.isfinite(raw) or abs(raw-total)>1e-6:raise ValueError('Whole STEP signed-volume identity failed')
    return bodies,{'compound_nodes':nodes,'positive_valid_solid_leaves':len(bodies),'signed_all_leaf_volume_sum_mm3':total,'all_topology_branches_checked':True}

def identify(bodies,port,side,present):
    own=[b for b in bodies if (b.shape.Center().x<0)==(side=='L')]
    if len(own)!=(12 if present else 11):raise ValueError('Actual side solid count differs')
    result={}
    def assign(name,predicate,count):
        values=[b for b in own if predicate(b)]
        if len(values)!=count:raise ValueError(f'Cannot independently identify {name}: {len(values)}')
        return values
    stops=assign('STOP',lambda b:abs(b.bounds['x'][1]-b.bounds['x'][0]-1.25)<1e-6 and abs(canon(b,port,side)['r'][1]-canon(b,port,side)['r'][0]-1.9)<1e-6,2)
    stops.sort(key=lambda b:canon(b,port,side)['r'][0]);result.update({f'STOP_{i}':b for i,b in enumerate(stops)})
    result['PAWL']=assign('PAWL',lambda b:abs(b.bounds['x'][1]-b.bounds['x'][0]-(2.6 if port=='STOW' else 2.3))<1e-6,1)[0]
    keys=assign('KEY',lambda b:abs(b.bounds['x'][1]-b.bounds['x'][0]-1.7)<1e-6,int(present))
    if keys:result['KEY']=keys[0]
    caps=assign('CAP',lambda b:abs(b.bounds['x'][1]-b.bounds['x'][0]-5.60)<1e-6 and abs(canon(b,port,side)['r'][1]-canon(b,port,side)['r'][0]-.3)<1e-6,2)
    caps.sort(key=lambda b:canon(b,port,side)['r'][0]);result.update({f'CAP_{i}':b for i,b in enumerate(caps)})
    screws=assign('SCREW',lambda b:abs(b.bounds['x'][1]-b.bounds['x'][0]-1.8)<1e-6 and abs(canon(b,port,side)['r'][1]-canon(b,port,side)['r'][0]-2.45)<1e-6,4)
    screws.sort(key=lambda b:(canon(b,port,side)['r'][0],canon(b,port,side)['q'][0]));result.update({f'SCREW_{i//2}_{i%2}':b for i,b in enumerate(screws)})
    for b in screws:
        if abs(b.volume-(math.pi*.5**2*2+math.pi*.9**2*.45))>1e-6:raise ValueError('Actual neutral NBK screw envelope volume differs')
        if abs(sum(canon(b,port,side)['e'])/2+2.60)>1e-6:raise ValueError('Actual screw lateral center differs')
    remaining=[b for b in own if all(b is not v for v in result.values())]
    if len(remaining)!=2:raise ValueError('Unidentified complete STEP leaves')
    remaining.sort(key=lambda b:b.volume,reverse=True);result['ROOT'],result['OLD_COVER']=remaining
    return result

def changed_pairs(checker,p):
    changed={n for n in p if n.startswith(('CAP_','SCREW_')) or n=='ROOT'}
    return [{'parts':[a,b],**checker.common(p[a],p[b])} for a,b in itertools.combinations(p,2) if a in changed or b in changed]

def main():
    started=time.monotonic();paths=sorted((PROJECT/'cad').glob('*.step'))
    expected={port+'_'+case+'.step' for port in ('STOW','OPEN') for case in CASES}
    if {p.name for p in paths}!=expected:raise ValueError('Expected eight complete exported states')
    hashes={str(p.relative_to(PROJECT)):sha(p) for p in paths}
    hashes.update({str((HERE/n).relative_to(PROJECT)):sha(HERE/n) for n in ('verify_fastened_step.py','strict_intersections.py','occ_signed_volume.py')})
    inputs=[];states={};rows=[];checker=Checker()
    for path in paths:
        port=path.name.split('_',1)[0];case=path.stem[len(port)+1:];present,key_q,lifts=CASES[case]
        bodies,topology=import_whole(path);inputs.append({'path':str(path.relative_to(PROJECT)),'sha256':sha(path),'whole_payload':topology})
        states[path.stem]={side:identify(bodies,port,side,present) for side in 'LR'}
        for side in 'LR':
            p=states[path.stem][side]
            actual=[canon(p['STOP_'+str(i)],port,side)['r'][0]+.1-i*5 for i in range(2)]
            if any(abs(a-b)>1e-6 for a,b in zip(actual,lifts)):raise ValueError('Actual STOP elevation differs from independent state')
            rows.append({'port':port,'side':side,'case':case,'checks':changed_pairs(checker,p)})
    # Rebuild only changed-part paths from complete actual STEP bodies. The
    # original R3 qualification remains separately frozen; no builder function
    # supplies the resulting geometry, lift trajectory or stroke.
    motion=[];withdraw=[];cap_retention=[]
    for port,side in itertools.product(('STOW','OPEN'),'LR'):
        seated=states[port+'_SEATED'][side];released=states[port+'_RELEASED'][side]
        stroke=canon(released['PAWL'],port,side)['e'][0]-canon(seated['PAWL'],port,side)['e'][0]
        if abs(stroke-(1.1 if port=='STOW' else .55))>1e-6:raise ValueError('Actual release stroke differs')
        for i in range(2):
            lifted=seated['CAP_'+str(i)].translate(rvec(port,.10))
            screws=['SCREW_'+str(i)+'_'+str(j) for j in range(2)]
            head_contacts=[{'screw':n,**checker.common(lifted,seated[n])} for n in screws]
            without_local_screws=[{'part':n,**checker.common(lifted,b)} for n,b in seated.items() if n not in screws and n!='CAP_'+str(i)]
            if not all(c['checked_common_mm3']>EPS for c in head_contacts):raise ValueError('Actual nominal screw heads fail straight cap withdrawal veto')
            cap_retention.append({'port':port,'side':side,'cap_index':i,'imposed_cap_lift_mm':.10,'installed_nominal_head_contacts':head_contacts,'with_both_local_screws_removed':without_local_screws,'removed_screws_allow_straight_cap_lift':not any(c['checked_common_mm3']>EPS for c in without_local_screws),'tilt_thread_strength_or_clamp_force_proven':False})
        for i in range(23):
            p=dict(seated);p['PAWL']=seated['PAWL'].translate(evec(port,side,stroke*i/22))
            motion.append({'port':port,'side':side,'fraction':i/22,'checks':changed_pairs(checker,p)})
        for q in (0.,.02,.05,.10,.15,.20,.25,.4,.7,.8,1.,1.2,1.4,2.,4.,8.,12.):
            lift=max(0.,min(1.2,1.2-2*(q-.1)));p=dict(released)
            p['KEY']=released['KEY'].translate(qvec(port,q))
            for i in range(2):p['STOP_'+str(i)]=released['STOP_'+str(i)].translate(rvec(port,lift-1.2))
            withdraw.append({'port':port,'side':side,'q_mm':q,'checks':changed_pairs(checker,p)})
    bad=[r for r in rows+motion+withdraw if any(c['checked_common_mm3']>EPS for c in r['checks'])]
    after={p:sha(PROJECT/p) for p in hashes}
    report={'environment':{'host':platform.node(),'python':platform.python_version(),'cadquery':cq.__version__},'builder_imported':False,'inputs_before_sha256':hashes,'inputs_bytes_unchanged':hashes==after,'complete_STEP_inputs':inputs,'static_export_rows':rows,'release_path_rows':motion,'normal_withdraw_rows':withdraw,'unexpected_collision_rows':bad,'actual_OCC_common_queries':checker.actual_occ_common_count,'validated_actual_AABB_proofs':checker.validated_actual_AABB_proven_zero_count,'fastener_thread_clamp_strength_tolerances_qualified':False,'physical_return_force_qualified':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-started}
    report['actual_cap_straight_withdrawal_and_removed_screws_counterexamples']=cap_retention
    (HERE/'independent-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    if bad:raise ValueError('Actual R4 STEP new-body collision; receipt retained')
    if hashes!=after:raise ValueError('Frozen independent input bytes changed')
    print(json.dumps({'complete_STEP':len(inputs),'solid_leaves':sum(r['whole_payload']['positive_valid_solid_leaves'] for r in inputs),'release_samples':len(motion),'withdraw_samples':len(withdraw),'actual_OCC_queries':checker.actual_occ_common_count,'unexpected_collisions':len(bad)}),flush=True)

if __name__=='__main__':main()
