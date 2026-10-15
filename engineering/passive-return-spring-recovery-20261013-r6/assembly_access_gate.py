#!/usr/bin/env python3
"""Actual R6 bench installation/access paths; rigid geometry only, no qualification."""
import sys,itertools,json,time,platform
from pathlib import Path
sys.dont_write_bytecode=True
import build_spring_cartridges as b
from strict_intersections import CheckedBody,Checker
HERE=Path(__file__).resolve().parent
def against(moving,fixed):
 guard=Checker();bb=CheckedBody(moving)
 return [{'part':n,'checked_volume_mm3':x['checked_common_mm3'],**x} for n,s in fixed.items() for x in [guard.common(bb,CheckedBody(s))]]
def main():
 start=time.monotonic();before={str(p.relative_to(HERE)):b.sha(p) for p in (HERE/'inputs').rglob('*') if p.is_file()};rows=[]
 for port,side in itertools.product(('STOW','OPEN'),'LR'):
  src,_=b.source(port);p=b.derived(port,side,src[side],1.14,True);Q=1.3 if port=='STOW' else 6.2
  for i in range(2):
   qc=Q+(.9 if i==0 else 3.);ee=4. if port=='OPEN' else 0.;off=5*i
   fixed={n:s for n,s in p.items() if n not in {f'SPRING_{i}_OD_TOL_ENVELOPE',f'SPRING_CAP_{i}',f'SPRING_SCREW_{i}_M1x3_NOMINAL'}}
   if i==0:fixed={n:s for n,s in fixed.items() if n not in {'STOP_1','SPRING_GUIDE_1','SPRING_CAP_1','SPRING_SCREW_1_M1x3_NOMINAL','SPRING_1_OD_TOL_ENVELOPE'}}
   free=b.world(b.cyl(.43,3.,2.8+ee,qc,2.94+off),port,side)
   for op,shape in [('FREE_SPRING_AXIAL_APPROACH',free),('REMOVABLE_SPRING_CAP_APPROACH',p[f'SPRING_CAP_{i}'])]:
    for d in (10.,6.,4.,3.,2.,1.6,1.,.5,.1,0.):
     checks=against(shape.translate(b.rvec(port,d)),fixed);rows.append({'port':port,'side':side,'i':i,'operation':op,'raised_r_mm':d,'sampled_path_only':True,'checks':checks,'positive_intersections':[x for x in checks if x['checked_volume_mm3']>b.EPS]})
   # Full visible 50-mm shaft translated continuously +10 -> 0, geometric
   # union is one 60-mm cylinder. Tip/recess and handle remain unmodelled.
   tool=b.world(b.cyl(1.5,60.,4.5+ee,qc,5.15+off),port,side)
   tool_fixed={n:s for n,s in p.items() if n!=f'SPRING_SCREW_{i}_M1x3_NOMINAL'}
   if i==0:tool_fixed={n:s for n,s in tool_fixed.items() if n not in {'STOP_1','SPRING_GUIDE_1','SPRING_CAP_1','SPRING_SCREW_1_M1x3_NOMINAL','SPRING_1_OD_TOL_ENVELOPE'}}
   checks=against(tool,tool_fixed);rows.append({'port':port,'side':side,'i':i,'operation':'PH0_50mm_SHAFT_PLUS10_CONTINUOUS_SWEPT_UNION','blade_diameter_mm':3.,'shaft_length_mm':50.,'swept_translation_mm':10.,'complete_tool_handle_tip_engagement_not_validated':True,'checks':checks,'positive_intersections':[x for x in checks if x['checked_volume_mm3']>b.EPS]})
   # Existing full STOP insertion into the one-piece support is a separately
   # retained failure gate; removing key/pawl/caps does not prove it can enter.
   fixed_stop={n:s for n,s in p.items() if n=='ROOT'}
   for d in (10.,6.,3.,1.,.5,0.):
    checks=against(p[f'STOP_{i}'].translate(b.rvec(port,d)),fixed_stop);rows.append({'port':port,'side':side,'i':i,'operation':'COMPLETE_STOP_THROUGH_ONE_PIECE_ROOT','raised_r_mm':d,'sampled_path_only':True,'checks':checks,'positive_intersections':[x for x in checks if x['checked_volume_mm3']>b.EPS]})
 after={str(p.relative_to(HERE)):b.sha(p) for p in (HERE/'inputs').rglob('*') if p.is_file()};assert before==after
 summary={op:{'rows':len([r for r in rows if r['operation']==op]),'positive_intersection_rows':sum(bool(r['positive_intersections']) for r in rows if r['operation']==op),'maximum_positive_common_mm3':max((x['checked_volume_mm3'] for r in rows if r['operation']==op for x in r['positive_intersections']),default=0.)} for op in sorted({r['operation'] for r in rows})}
 result={'host':platform.node(),'source_sha256':b.sha(__file__),'builder_sha256':b.sha(b.__file__),'input_sha256':before,'inputs_unchanged':True,'rows':rows,'summary':summary,'lower_spring_installed_before_upper_STOP_and_upper_spring_subassembly':True,'complete_bench_assembly_pass':not any(r['positive_intersections'] for r in rows),'actual_qualification':False,'force_return_or_retraction_qualified':False,'whole_phone_assembly_qualified':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'assembly-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 # Exit zero means the audit recorded all paths, including failed paths.
if __name__=='__main__':main()
