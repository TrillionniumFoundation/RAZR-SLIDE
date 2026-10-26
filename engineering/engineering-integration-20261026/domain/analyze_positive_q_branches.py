"""Recompute original S4 contact branches and independently coupled source domains.
No CAD is executed. Real physical enforcement and preload remain unproved.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,ast,gzip,hashlib,importlib.util,json,math,subprocess,sys,types,itertools
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--domain-analyzer',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();repo=a.repository.resolve();out=a.output.resolve()
 if out.exists():raise ValueError('fresh output required')
 out.mkdir(parents=True)
 sources={}
 def read(rel):
  data=subprocess.check_output(['git','-C',str(repo),'show',S4+':'+rel]);sources[rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)};return data
 module=types.ModuleType('_frozen_S4_cam_profile');sys.modules[module.__name__]=module
 exec(compile(read('integration/cam_contact_profile.py'),'integration/cam_contact_profile.py','exec'),module.__dict__)
 data=json.loads(gzip.decompress(read('engineering/thin-mechanism-20261015/native-verification.json.gz')))
 for rel in ('integration/product_assembly.py','integration/verify_cam_coupling.py','integration/cam_coupling.py','integration/product_nominal_motion.py'):read(rel)
 spec=importlib.util.spec_from_file_location('_source_domain',a.domain_analyzer);domain=importlib.util.module_from_spec(spec);spec.loader.exec_module(domain)
 K=12/79.75;half=(.425-.4)*math.hypot(1,K);yoke=(.425-.4)*math.sqrt(2);k=F(K)
 profiles={};breaks=set((0.,12.));rows={}
 fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
 for side in 'LR':
  profiles[side]=[module.ContactProfile(**{f:r['profile'][f] for f in fields}) for r in data['sides'][side]['contacts']]
  rows[side]=[]
  for i,p in enumerate(profiles[side]):
   breaks.update(p.breakpoints);h0=p.evaluate(0)[0];sign=-1 if side=='L' else 1
   intervals=[]
   levels=[0.,*p.breakpoints,p.q_max]
   for lo,hi in zip(levels,levels[1:]):
    mid=lo+(hi-lo)/2.;state=p.evaluate(mid)
    intervals.append({'q_interval_mm':[lo,hi],'q_interval_binary64_exact':list(map(lambda v:str(F(v)),[lo,hi])),'branch_in_interior':state[2], 'height_bounds_mm':list(p.height_bounds(lo,hi)), 'STOP_translation_X_bounds_mm':sorted([sign*(p.evaluate(t)[0]-h0) for t in (lo,hi)]),'spring_envelope_extra_axial_length_bounds_mm':sorted([abs(p.evaluate(t)[0]-h0) for t in (lo,hi)])})
   probes=[]
   for q in p.breakpoints:
    probes.append({'breakpoint_mm':q,'breakpoint_hex':q.hex(),'slide_zero_offset_mm':q/K,'left_neighbor':{'q':math.nextafter(q,-math.inf),'state':p.evaluate(math.nextafter(q,-math.inf))},'at':p.evaluate(q),'right_neighbor':{'q':math.nextafter(q,math.inf),'state':p.evaluate(math.nextafter(q,math.inf))}})
   rows[side].append({'stop_index':i,'original_profile_receipt':p.receipt(),'intervals':intervals,'joins_binary64_evaluation':probes,'full_STOP_X_displacement_mm':sign*(p.evaluate(12)[0]-h0),'maximum_spring_envelope_length_mm':1.46+abs(p.evaluate(12)[0]-h0),'spring_radius_mm':.43,'spring_is_envelope_not_constitutive_or_dynamic_model':True})
 levels=sorted(breaks);intervals=list(zip(levels,levels[1:]));cells=[]
 def cset(left,right):
  result=domain.motion_polytope(k,F(half),F(yoke),F('79.75'),F(12))
  for side,interval in [('L',left),('R',right)]:
   for r in result:
    if r['name']==side+'_profile_q_-1':r['b']=-F(interval[0])
    elif r['name']==side+'_profile_q_1':r['b']=F(interval[1])
  return result
 def sect(s,lo,hi):
  cs=[domain.constraint('cam+', [1,0],F(half)),domain.constraint('cam-',[-1,0],F(half)),domain.constraint('yoke+',[1,-1],F(yoke)),domain.constraint('yoke-',[-1,1],F(yoke)),domain.constraint('q+',[0,1],F(hi)-k*s),domain.constraint('q-',[0,-1],k*s-F(lo))]
  points=set()
  for chosen in itertools.combinations(cs,2):
   x=domain.solve_equalities(chosen)
   if x is not None and all(domain.dot(c['a'],x)<=c['b'] for c in cs):points.add(x)
  return sorted(points)
 def sections(cs,left,right):
  levels={F(0),F('79.75')}
  for lo,hi in (left,right):
   for q in map(F,(lo,hi)):
    for dx,err in itertools.product((-F(half),F(half)),(-F(yoke),F(yoke))):
     s=(q-dx+err)/k
     if 0<=s<=F('79.75'):levels.add(s)
  result=set()
  for s in levels:
   for l,r in itertools.product(sect(s,*left),sect(s,*right)):
    x=(s,*l,*r);active=[c['a'] for c in cs if domain.dot(c['a'],x)==c['b']]
    if domain.rank(active)==5:result.add(x)
  return sorted(result)
 for li,left in enumerate(intervals):
  for ri,right in enumerate(intervals):
   cs=cset(left,right)
   # Unrestricted left/right branch labels can be infeasible because they share slide.
   verts=[]
   for chosen in itertools.combinations(cs,5):
    x=domain.solve_equalities(chosen)
    if x is not None and all(domain.dot(c['a'],x)<=c['b'] for c in cs):verts.append(x)
   verts=sorted(set(verts));independent=sections(cs,left,right);assert verts==independent
   row={'left_branch_cell':li,'right_branch_cell':ri,'qL_interval_mm':left,'qR_interval_mm':right,'feasible':bool(verts),'vertex_count':len(verts),'independent_section_construction_equal':True,'vertices_exact':[list(map(str,v)) for v in verts],'vertices_binary64':[list(map(float,v)) for v in verts]}
   cells.append(row);print(json.dumps({'left':li,'right':ri,'vertices':len(verts)}),flush=True)
 result={'schema':'razr-S4-positive-q-branch-source-domain-20261026-v1','functional_source_commit':S4,'source_identities':sources,'source_domain_analyzer_sha256':hashlib.sha256(a.domain_analyzer.read_bytes()).hexdigest(),'new_CAD_executed':False,'physical_motion_domain_enforced':False,'preload_and_reverse_branch_proved':False,'profiles':rows,'union_breakpoints_mm':levels,'union_breakpoint_hex':[q.hex() for q in levels],'per_side_closed_branch_cells':[{'interval_mm':[lo,hi],'exact_binary64_width':str(F(hi)-F(lo)),'decimal_text_width':str(F(str(hi))-F(str(lo))),'midpoint_states':{side:[p.evaluate(lo+(hi-lo)/2.) for p in profiles[side]] for side in 'LR'}} for lo,hi in intervals],'independent_source_domain_cells':cells,'nominal_source_halfwidths_mm':{'crosshead':half,'dx_minus_dq':yoke},'source_slot_comparison_TOL_shell_included':False,'disclaimer':'Cells partition nominal real inequalities using exact binary64 constants; boundary rounding and physical enforcement remain separate. Empty branch combinations are analytically infeasible under shared slide, not omitted for collisions.','candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
 (out/'POSITIVE_Q_BRANCH_DOMAIN.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'complete':True,'profile_count':4,'per_side_intervals':len(intervals),'cell_count':len(cells),'feasible_cell_count':sum(c['feasible'] for c in cells),'total_vertex_occurrences':sum(c['vertex_count'] for c in cells),'smallest_binary64_interval':min(hi-lo for lo,hi in intervals)}))
if __name__=='__main__':main()
