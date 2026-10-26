from pathlib import Path
import json,sys,datetime,hashlib,subprocess,time
R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020')
PY='/home/qian-qi/.local/share/razr-slide-evidence/product-integration-20261018/venv-recheck-20261019/bin/python'
HEAD='a33e58cd555b8d9aff1e3649f79cd0dba378a804'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
assert git('rev-parse','HEAD')==HEAD and git('status','--porcelain')==''
before=sha(R/'integration/product_routing_ep3.py')
out=E/'ep3-unit-api-repair-a33e58c';assert not out.exists();out.mkdir()
cmd=[PY,'-B','tools/run_suite.py','--directory',str(R/'integration/ep3-routing-tests'),'--minimum','7','--report',str(out/'ep3-routing.json')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
with (out/'ep3-routing.log').open('w') as log:q=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT)
unit=json.loads((out/'ep3-routing.json').read_text())
assert q.returncode==0 and unit['tests_run']==7 and unit['passed']
sys.path.insert(0,str(R/'integration'))
import product_routing_ep3 as ep
import product_assembly as p
import product_interfaces as interfaces
import product_fpc as f
import cadquery as cq
A=p.box((0.,0.,0.),(10.,10.,10.));B=p.box((10.,0.,0.),(20.,10.,10.))
B_gap=p.box((11.,0.,0.),(21.,10.,10.))
cases=[
 ('inside_A',p.box((1.,1.,1.),(2.,2.,2.)),[A,B],0.),
 ('inside_B',p.box((11.,1.,1.),(12.,2.,2.)),[A,B],0.),
 ('spans_touching_A_B',p.box((9.,1.,1.),(11.,2.,2.)),[A,B],0.),
 ('partly_outside',p.box((19.,1.,1.),(21.,2.,2.)),[A,B],1.),
 ('fully_outside',p.box((21.,1.,1.),(22.,2.,2.)),[A,B],1.),
 ('gap_between_separate_domains',p.box((9.,1.,1.),(12.,2.,2.)),[A,B_gap],1.),
 ('small_positive_residual_not_zeroed',p.box((20.,1.,1.),(20.001,1.01,1.001)),[A,B],1e-8)]
rows=[]
for name,body,domains,expected in cases:
 r=ep.containment({name:body},domains)['rows'][0]
 assert not r.get('evaluation_failed') and abs(r['outside_outer_union_mm3']-expected)<1e-10,(name,r)
 if expected>0:assert r['outside_outer_union_mm3']>0.
 rows.append({'case':name,'expected_outside_mm3':expected,'actual':r,'passed':True})
bad=ep.containment({'free_face':cq.Face.makePlane(1.,1.)},[A,B])['rows'][0]
assert bad.get('evaluation_failed') is True and 'outside_outer_union_mm3' not in bad
rows.append({'case':'free_non_solid_is_not_empty_material','actual':bad,'passed':True})
cfg=ep.candidate_interface_config(interfaces.load_config(),ep.load_config())
sections,route=f.route_pose(cfg,79.75,0.)
raw=51.+route['straight_A_mm'];normalized=float(raw)
w=p.box((-6.,94.25,1.4),(6.,normalized,1.5))
assert abs(p.volume(w)-35.03125052611621)<1e-8
endpoints={e:ep.ep3_local_parts(e) for e in ['A','B']}
old=git('show','bdb1bc19fce49692fd49cd508031bfc456e15208:integration/product_routing_ep3.py')
assert old.split('def ep3_local_parts',1)[1].split('def outer_domains',1)[0]==(R/'integration/product_routing_ep3.py').read_text().split('def ep3_local_parts',1)[1].split('def outer_domains',1)[0]
report={'schema':'razr-ep3-native-api-regression-v1','source_commit':HEAD,'started_utc':start,
 'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-t,
 'source_sha256':before,'source_bytes_unchanged':sha(R/'integration/product_routing_ep3.py')==before,
 'unit_tests':7,'unit_passed':True,'unit_report':'ep3-routing.json','native_cases':rows,
 'scalar_witness':{'raw_type':type(raw).__name__,'normalized_type':type(normalized).__name__,'native_volume_mm3':p.volume(w),'passed':True},
 'endpoint_construction_text_unchanged':True,'actual_endpoint_positive_solids':{e:len(v) for e,v in endpoints.items()},
 'configuration_sha256':sha(R/'design/product_routing_ep3.json'),'all_declared_regressions_passed':True,
 'full_109_reexecuted':False,'full_1310_reexecuted':False,'candidate_go':False,'manufacturing_go':False}
(out/'native-api-regression.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert git('rev-parse','HEAD')==HEAD and git('status','--porcelain')==''
