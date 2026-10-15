#!/usr/bin/env python3
"""Actual changed-material sweep, with byte-bound reuse of unchanged pairs.

The only CAD change is the STOW low connection's q-front. All PAWL pairs in
both STOW sides are re-evaluated. Unchanged pairs retain their actual native
baseline results, not a clearance assumption. Source single-line identity and
all unchanged static participant BREP bytes are checked before that reuse.
"""
from __future__ import annotations
import copy,hashlib,importlib.util,json,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import passive_repair as new

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_old():
 p=HERE/'rejected-lowlink-layout/passive_repair.py'
 spec=importlib.util.spec_from_file_location('rejected_lowlink_builder',p)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 mod.HERE=HERE;mod.REPO=new.REPO;mod.OLD=new.OLD
 return mod
def brep_sha(s):
 with tempfile.NamedTemporaryFile(suffix='.brep') as f:
  s.exportBrep(f.name)
  return sha(f.name)
def recheck(row,p):
 return [{'parts':x['parts'],'common_mm3':new.cv(p[x['parts'][0]],p[x['parts'][1]])}
         if 'PAWL' in x['parts'] else x for x in row]
def assert_main(report):
 for row in report['motion_rows']:
  pp=[x for sample in row['samples'] for x in sample['pairs']]
  stopped=any(x['common_mm3']>new.EPS for x in pp if 'PAWL' in x['parts'] and any(n.startswith('STOP') for n in x['parts']))
  if row['state'] in ('FULL','SEAT_0p10','DOUBLE_JAM_ABSENT') and any(x['common_mm3']>new.EPS for x in pp):raise ValueError('Unexpected release collision')
  if row['state'] in ('PARTIAL_0p25','ABSENT','PRIMARY_JAM_ABSENT','SECONDARY_JAM_ABSENT') and not stopped:raise ValueError('Actual independent stop veto failed')
 for row in report['actual_normal_and_jammed_key_withdrawal_rows']:
  if row['jam_state']=='NORMAL' and any(x['common_mm3']>new.EPS for x in row['pairs']):raise ValueError('Normal full withdrawal collision')
 for port in ('STOW','OPEN'):
  for side in 'LR':
   for state,index in [('PRIMARY_HELD_CLEAR',0),('SECONDARY_HELD_CLEAR',1)]:
    if not any(x['common_mm3']>new.EPS for r in report['actual_normal_and_jammed_key_withdrawal_rows'] if r['port']==port and r['side']==side and r['jam_state']==state for x in r['pairs'] if set(x['parts'])=={'KEY','STOP_'+str(index)}):raise ValueError('Held-clear removal path is not physically blocked')
def main():
 started=time.monotonic();before=new.protected()
 archived=HERE/'rejected-lowlink-layout/passive_repair.py'
 text=archived.read_text();oldline='link=box(-.1,0,Q-.05,stalk_q+.05,-9.85,-9.77)'
 newline='link=box(-.1,0,Q+.10,stalk_q+.05,-9.85,-9.77)'
 if text.count(oldline)!=1 or text.replace(oldline,newline)!=(HERE/'passive_repair.py').read_text():raise ValueError('Change exceeds the bounded STOW lowlink repair')
 old=load_old();same=[]
 for port in ('STOW','OPEN'):
  for side in 'LR':
   aa,ad=old.static(port,side);bb,bd=new.static(port,side)
   if ad!=bd or set(aa)!=set(bb):raise ValueError('Participant identity changed')
   for name in aa:
    if name=='PAWL' and port=='STOW':continue
    a,b=brep_sha(aa[name]),brep_sha(bb[name])
    if a!=b:raise ValueError('Unchanged native BREP differs: '+port+' '+side+' '+name)
    same.append({'port':port,'side':side,'part':name,'before_and_after_native_brep_sha256':a})
 baseline=HERE/'rejected-lowlink-layout/r3-receipt.json'
 report=copy.deepcopy(json.loads(baseline.read_text()));count=0
 states={'FULL':(0,True,None),'SEAT_0p10':(.1,True,None),'PARTIAL_0p25':(.25,True,None),'ABSENT':(0,False,None),'PRIMARY_JAM_ABSENT':(0,False,{0:1.2}),'SECONDARY_JAM_ABSENT':(0,False,{1:1.2}),'DOUBLE_JAM_ABSENT':(0,False,{0:1.2,1:1.2})}
 for row in report['motion_rows']:
  if row['port']!='STOW':continue
  q,present,jam=states[row['state']]
  for sample in row['samples']:
   p=new.scene(row['port'],row['side'],q,sample['fraction'],present,jam)
   sample['pairs']=recheck(sample['pairs'],p);count+=sum('PAWL' in x['parts'] for x in sample['pairs'])
  print(json.dumps({'operation':'changed-material-release','port':row['port'],'side':row['side'],'state':row['state']}),flush=True)
 for row in report['actual_normal_and_jammed_key_withdrawal_rows']:
  if row['port']!='STOW':continue
  jam={'NORMAL':None,'PRIMARY_HELD_CLEAR':{0:1.2},'SECONDARY_HELD_CLEAR':{1:1.2}}[row['jam_state']]
  p=new.scene('STOW',row['side'],row['key_withdraw_mm'],1.,True,jam)
  row['pairs']=recheck(row['pairs'],p);count+=sum('PAWL' in x['parts'] for x in row['pairs'])
 extra=[]
 for side in 'LR':
  samples=[]
  for i in range(23):
   p=new.scene('STOW',side,.15,i/22,True,{0:1.2,1:1.2})
   samples.append({'fraction':i/22,'pairs':new.pairs(p)})
  extra.append({'port':'STOW','side':side,'key_withdraw_mm':.15,'actual_stop_lifts_mm':[1.2,1.2],'samples':samples})
  print(json.dumps({'operation':'repaired-concrete-q0p15-counterexample','side':side,'max_actual_common_mm3':max(x['common_mm3'] for s in samples for x in s['pairs'])}),flush=True)
 steps=[]
 for port in ('STOW','OPEN'):
  for name,q,pres,jam,fraction in [('SEATED',0,True,None,0),('RELEASED',0,True,None,1),('ABSENT_BLOCKED',0,False,None,.35/abs(new.static(port,'L')[1])),('PRIMARY_JAM_ABSENT_BLOCKED',0,False,{0:1.2},.35/abs(new.static(port,'L')[1])),('DOUBLE_JAM_ABSENT_ESCAPE',0,False,{0:1.2,1:1.2},1),('NORMAL_KEY_WITHDRAW_1p4',1.4,True,None,1),('PRIMARY_HELD_CLEAR_WITHDRAW_BLOCKED',.4,True,{0:1.2},1)]:
   combined={}
   for side in 'LR':combined.update({side+'_'+n:s for n,s in new.scene(port,side,q,fraction,pres,jam).items()})
   steps.append(new.save(combined,port+'_'+name))
 if before!=new.protected():raise ValueError('Protected source changed')
 report['source_r3_builder_sha256']=sha(HERE/'passive_repair.py')
 report['STEP_exports']=steps
 report['lowlink_repair']={'single_source_line_replacement':{'before':oldline,'after':newline},'baseline_builder_sha256':sha(archived),'baseline_full_native_receipt_sha256':sha(baseline),'unchanged_participant_native_brep_identity':same,'unchanged_pairs_reused_from_byte_bound_actual_baseline':True,'all_changed_STOW_pawl_pairs_actual_native_recomputed':True,'changed_material_pair_check_count':count,'repaired_q0p15_23_sample_per_side_paths':extra,'negative_q_is_not_a_qualified_seat':True,'manufacturing_go':False}
 report['environment']=dict(report['environment'],final_check_host=new.platform.node())
 (HERE/'r3-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 assert_main(report)
 if any(x['common_mm3']>new.EPS for r in extra for s in r['samples'] for x in s['pairs']):raise ValueError('Known STOW q=.15 lowlink counterexample remains; receipt retained')
 result={'executed_verifier_sha256':sha(__file__),'builder_sha256':sha(HERE/'passive_repair.py'),'receipt_sha256':sha(HERE/'r3-receipt.json'),'baseline_actual_main_samples':644,'baseline_actual_withdraw_samples':204,'recomputed_changed_STOW_pawl_pair_checks':count,'additional_whole_assembly_release_samples':46,'final_STEP_count':len(steps),'all_final_STEP_reimports_valid_positive_solids':sum(x['valid_positive_solids'] for x in steps),'elapsed_monotonic_seconds':time.monotonic()-started,'protected_bytes_unchanged':True,'physical_return_force_strength_or_tolerance_qualification':False,'manufacturing_go':False}
 (HERE/'lowlink-repair-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
