#!/usr/bin/env python3
"""Actual bench ROOT split retains all cut fragments and adds connecting material."""
from pathlib import Path
import sys,json,itertools,time,math,platform
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import build_spring_cartridges as b
from strict_intersections import CheckedBody,Checker
def ecyl(rad,h,e,q,r):return b.cq.Solid.makeCylinder(rad,h,b.cq.Vector(e,q,r),b.cq.Vector(1,0,0))
def scene(port,side,lift=1.14,present=True):
 src,_=b.source(port);p=b.derived(port,side,src[side],lift,present);root=p.pop('ROOT')
 Q=1.3 if port=='STOW' else 6.2;qc=Q+.9;ee=4. if port=='OPEN' else 0.
 # The lower cap screw is moved 3 mm outward, beyond the upper STOP/CAP
 # projected shaft corridor. New material, cavities and source failures remain.
 root=root.cut(b.world(b.box(4.+ee,5.+ee,qc-.55,qc+.55,-.9,4.4),port,side)).clean()
 post=b.box(7.+ee,8.+ee,qc-.55,qc+.55,-.9,4.4).cut(b.cyl(.5,3.,7.5+ee,qc,1.7)).clean()
 link=b.box(4.9+ee,8.+ee,qc+.35,qc+.55,-.98,-.82)
 root=b.fuse([root,b.world(b.fuse([post,link]),port,side)])
 cap=b.fuse([b.box(2.3+ee,8.4+ee,qc-.8,qc+.8,4.4,4.7),b.cyl(.7,.3,2.8+ee,qc,4.4)]).cut(b.cyl(.55,.7,7.5+ee,qc,4.3)).clean()
 p['SPRING_CAP_0']=b.world(cap,port,side)
 p['SPRING_SCREW_0_M1x3_NOMINAL']=b.world(b.fuse([b.cyl(.5,3.,7.5+ee,qc,1.7),b.cyl(.9,.45,7.5+ee,qc,4.7)]),port,side)
 inner=root.intersect(b.world(b.box(-60,.05,-60,60,-60,60),port,side)).clean()
 outer=root.intersect(b.world(b.box(.05,60,-60,60,-60,60),port,side)).clean()
 raw={'INNER':{'solids':len(inner.Solids()),'volume':inner.Volume()},'OUTER':{'solids':len(outer.Solids()),'volume':outer.Volume()}}
 assert abs(inner.Volume()+outer.Volume()-root.Volume())<1e-6
 # These explicit new spines join every fragment; none is selected or discarded.
 if port=='STOW':spine=b.box(.7,.9,3.,3.2,-8.1,4.2)
 else:spine=b.fuse([b.box(.7,.9,8.,8.2,-.98,13.5),b.box(.7,.9,8.16,8.75,13.4,13.6)])
 outer=b.fuse([outer,b.world(spine,port,side)])
 if port=='STOW':
  passage=b.world(b.box(.68,.92,2.98,3.22,-8.12,4.22),port,side)
  p['OLD_COVER']=p['OLD_COVER'].cut(passage).clean();b.participant(p['OLD_COVER'])
 for i in range(2):
  off=5*i
  pi=b.fuse([b.box(-1.45,.05,-3.1,-1.7,-2.,-.6),b.box(-1.45,.05,-1.75,-1.4,-1.,-.8)]).translate((0,0,off))
  po=b.fuse([b.box(.05,1.75,-3.1,-1.7,-2.,-.6),b.box(.05,.9,-1.75,-1.4,-1.,-.8)]).translate((0,0,off))
  inner=b.fuse([inner,b.world(pi,port,side)]);outer=b.fuse([outer,b.world(po,port,side)])
  inner=inner.cut(b.world(ecyl(.5,1.4,-1.25,-2.4,-1.3+off),port,side)).clean()
  outer=outer.cut(b.world(ecyl(.55,1.75,.04,-2.4,-1.3+off),port,side)).clean()
  screw=b.fuse([ecyl(.5,3.,-1.25,-2.4,-1.3+off),ecyl(.9,.45,1.75,-2.4,-1.3+off)])
  p[f'ROOT_JOIN_SCREW_{i}_M1x3_NOMINAL']=b.world(screw,port,side)
 for i in range(2):
  off=5*i;Q=1.3 if port=='STOW' else 6.2;qc=Q+(.9 if i==0 else 3.)
  cut=b.world(b.box(.05,1.01,Q+.051,qc+.56,1.45+off,3.01+off),port,side)
  outer=outer.cut(cut).clean();b.participant(outer)
  if port=='OPEN':
   cut=b.world(b.box(.05,3.75,Q-.045,qc+.56,2.60+off,3.04+off),port,side)
   outer=outer.cut(cut).clean();b.participant(outer)
 if port=='STOW':
  outer=outer.cut(b.world(b.box(.93,1.27,1.68,3.36,-10.27,.30),port,side)).clean()
 else:
  outer=outer.cut(b.world(b.box(.38,.72,6.64,11.58,1.0,10.17),port,side)).clean()
 if port=='STOW':
  bypass=b.fuse([b.box(1.28,1.50,1.40,1.65,-10.50,.35),b.box(.70,1.50,1.40,1.75,-10.50,-10.35),b.box(.70,1.50,1.40,1.65,-.98,-.82),b.box(1.28,1.50,1.60,1.80,-.98,-.82),b.box(.21,.73,1.40,1.75,-7.30,-7.20),b.box(.70,1.50,1.40,1.65,-7.30,-7.20)])
  outer=b.fuse([outer,b.world(bypass,port,side)])
 b.participant(outer)
 p['ROOT_INNER']=inner;p['ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=outer
 for s in p.values():b.participant(s)
 return p,raw
def check(moving,fixed):
 guard=Checker();mb=CheckedBody(moving);return [{'part':n,**guard.common(mb,CheckedBody(s))} for n,s in fixed.items()]
def pairs(p):
 guard=Checker();bb={n:CheckedBody(s) for n,s in p.items()};return [{'parts':[x,y],**guard.common(bb[x],bb[y])} for x,y in itertools.combinations(p,2)]
def export(p,label):
 folder=HERE/'cad';folder.mkdir(exist_ok=True);a=b.cq.Assembly(name=label)
 for n,s in p.items():a.add(s,name=n)
 path=folder/(label+'.step');a.save(str(path),exportType='STEP');leaves,topology=b.identity.import_whole(path)
 expected=sorted(s.Volume() for s in p.values());actual=sorted(v.volume for v in leaves)
 assert len(actual)==len(expected) and all(abs(x-y)<1e-6 for x,y in zip(actual,expected))
 return {'path':str(path.relative_to(HERE)),'sha256':b.sha(path),'whole_payload':topology,'expected_part_count':len(p)}
def main():
 start=time.monotonic();rows=[];exports=[];assembly=[];topologies=[]
 for port in ('STOW','OPEN'):
  combined={}
  for side in 'LR':
   p,raw=scene(port,side);topologies.append({'port':port,'side':side,'initial_split_all_fragments':raw,'final_connected_root_count':2})
   rr=pairs(p);rows.append({'port':port,'side':side,'pairs':rr,'positive_intersections':[v for v in rr if v['checked_common_mm3']>b.EPS]})
   combined.update({side+'_'+n:s for n,s in p.items()})
   # INNER is placed first, then each STOP enters from positive E without KEY.
   for i in range(2):
    for d in (10.,6.,3.,2.,1.,.5,.1,0.):
     rr=check(p['STOP_'+str(i)].translate(b.identity.evec(port,side,d)),{'ROOT_INNER':p['ROOT_INNER']});assembly.append({'port':port,'side':side,'operation':'STOP_POSITIVE_E_INTO_INNER_ROOT','i':i,'translation_mm':d,'checks':rr,'bad':[x for x in rr if x['checked_common_mm3']>b.EPS]})
   fixed={'STOP_0':p['STOP_0'],'STOP_1':p['STOP_1'],'ROOT_INNER':p['ROOT_INNER']}
   for d in (10.,6.,3.,1.,.5,.1,0.):
    rr=check(p['ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'].translate(b.identity.evec(port,side,d)),fixed);assembly.append({'port':port,'side':side,'operation':'ROOT_OUTER_POSITIVE_E_APPROACH','translation_mm':d,'checks':rr,'bad':[x for x in rr if x['checked_common_mm3']>b.EPS]})
   # Neutral transverse M1x3 insertion and actual PH0 visible shaft union.
   for i in range(2):
    moving=p[f'ROOT_JOIN_SCREW_{i}_M1x3_NOMINAL'];fixed={n:sh for n,sh in p.items() if n!=f'ROOT_JOIN_SCREW_{i}_M1x3_NOMINAL'}
    for d in (10.,6.,3.,1.,.5,.1,0.):
     rr=check(moving.translate(b.identity.evec(port,side,d)),fixed);assembly.append({'port':port,'side':side,'i':i,'operation':'ROOT_JOIN_SCREW_E_INSERT','translation_mm':d,'checks':rr,'bad':[x for x in rr if x['checked_common_mm3']>b.EPS]})
    tool=b.world(ecyl(1.5,60.,2.20,-2.4,-1.3+5*i),port,side);rr=check(tool,fixed);assembly.append({'port':port,'side':side,'i':i,'operation':'ROOT_JOIN_PH0_FULL50_PLUS10_CONTINUOUS_UNION','translation_mm':10.,'checks':rr,'bad':[x for x in rr if x['checked_common_mm3']>b.EPS]})
   # Cover and spring cassettes are installed later. Parked PAWL can enter its
   # open original guide; no claim is made about an energized mechanism.
   parked=p['PAWL'].translate(b.identity.evec(port,side,1.1 if port=='STOW' else .55))
   fixed={n:s for n,s in p.items() if n not in ('PAWL','KEY','OLD_COVER') and not n.startswith(('SPRING_','CAP_','SCREW_'))}
   for d in (10.,6.,3.,1.,.5,.1,0.):
    vector=b.rvec(port,d) if port=='STOW' else b.identity.qvec(port,d)
    rr=check(parked.translate(vector),fixed);assembly.append({'port':port,'side':side,'operation':'PARKED_PAWL_OPEN_GUIDE_INSERT','translation_mm':d,'checks':rr,'bad':[x for x in rr if x['checked_common_mm3']>b.EPS]})
   print(json.dumps({'port':port,'side':side,'static_bad':len(rows[-1]['positive_intersections']),'assembly_bad':sum(bool(r['bad']) for r in assembly if r['port']==port and r['side']==side)}),flush=True)
  if not any(r['positive_intersections'] for r in rows if r['port']==port):exports.append(export(combined,port+'_ROOT_SPLIT_ASSEMBLED'))
 result={'host':platform.node(),'source_sha256':b.sha(__file__),'parent_builder_sha256':b.sha(b.__file__),'root_initial_split_fragments':topologies,'static_rows':rows,'assembly_rows':assembly,'STEP_exports':exports,'static_positive_pair_rows':sum(bool(x['positive_intersections']) for x in rows),'assembly_positive_rows':sum(bool(r['bad']) for r in assembly),'actual_all_fragments_kept_and_connected':True,'source_R4_STEP_unchanged':{k:b.sha(HERE.parent/'inputs'/k)==v for k,v in b.EXPECTED.items()},'complete_bench_assembly_qualified':False,'force_retraction_qualified':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'split-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'static_bad_rows':result['static_positive_pair_rows'],'assembly_bad_rows':result['assembly_positive_rows'],'STEP':len(exports)}),flush=True)
if __name__=='__main__':main()
