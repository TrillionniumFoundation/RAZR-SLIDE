from pathlib import Path
import argparse,sys,json,hashlib,time
sys.dont_write_bytecode=True
import cover_admission as s
b=s.b;scene=s.scene;check=s.check;pairs=s.pairs;ecyl=s.parent.ecyl
GROUP=s.GROUP
import platform
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
HERE=args.output.resolve()
if HERE==ROOT or ROOT in HERE.parents:raise ValueError('new external output required')
HERE.mkdir(parents=True,exist_ok=False)
if hashlib.sha256((GROUP/'split-root-repair/split_root_cartridges_v9.py').read_bytes()).hexdigest()!='3949d4d8f022f334aab83dc9f1da0ee187e1479032b76a1193018d7c918689db':raise ValueError('original v9 source differs')
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
 result={'host':platform.node(),'source_sha256':b.sha(__file__),'parent_builder_sha256':b.sha(b.__file__),'root_initial_split_fragments':topologies,'static_rows':rows,'assembly_rows':assembly,'STEP_exports':exports,'static_positive_pair_rows':sum(bool(x['positive_intersections']) for x in rows),'assembly_positive_rows':sum(bool(r['bad']) for r in assembly),'actual_all_fragments_kept_and_connected':True,'source_R4_STEP_unchanged':{k:b.sha(GROUP/'inputs'/k)==v for k,v in b.EXPECTED.items()},'complete_bench_assembly_qualified':False,'force_retraction_qualified':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'split-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'static_bad_rows':result['static_positive_pair_rows'],'assembly_bad_rows':result['assembly_positive_rows'],'STEP':len(exports)}),flush=True)
if __name__=='__main__':
 main()
 receipt=json.loads((HERE/'split-receipt.json').read_text())
 if receipt['static_positive_pair_rows'] or receipt['assembly_positive_rows']:raise ValueError('replayed assembly rejected; complete receipt retained')
