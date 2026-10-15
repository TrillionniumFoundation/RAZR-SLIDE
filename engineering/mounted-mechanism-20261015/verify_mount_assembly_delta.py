"""Replay only preassembly pairs affected by new inner-root mounting ears.
Original 44 other native part identities are bound by the complete mount report.
This is geometry with the inherited temporary holding assumptions, not hardware.
"""
from pathlib import Path
import argparse,hashlib,json,sys

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--base-report',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 sys.path.insert(0,str(a.repo.resolve()/'integration'))
 import verify_mounted_mechanism as mounted
 import verify_thin_mechanism as thin
 import cam_contact_native as n
 from verify_contact_motion import PARTS
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 r,p,hashes=mounted.read_all(a.manifest);base=json.loads(a.base_report.read_text())
 if not base['passed'] or any(base['failures'].values()):raise ValueError('base full mount verification did not pass')
 for path,h in base['input_sha256'].items():
  if sha(path)!=h:raise ValueError('previously verified source bytes changed')
 oldrows=base['source_parts'];unchanged=[x for x in oldrows if x['name']!='ROOT_INNER']
 if len(unchanged)!=44 or any(x['source_added_mm3']>1e-7 or x['source_removed_mm3']>1e-7 for x in unchanged):raise ValueError('unrelated source changes forbid pair reuse')
 def inverse(b,side):
  return b.translate((13.85 if side=='L' else -13.85,-16.,30.55)).rotate((0,0,0),(0,0,1),180).rotate((0,0,0),(0,1,0),-90 if side=='L' else 90)
 rows=[]
 for side in 'LR':
  ex=-1 if side=='L' else 1
  parts={k:inverse(p[side+'_'+k],side) for k in PARTS}
  parts['PARKED_PAWL']=parts['PAWL'].translate((ex*1.1,0,0))
  parts['JAW_LOWER']=n.box(side,-.8,.8,12.15,12.55,-3.4,-2.9)
  parts['JAW_UPPER']=n.box(side,-.8,.8,12.15,12.55,-2.5,-2.)
  installed={'JAW_LOWER':parts['JAW_LOWER']}
  for name,vec in thin.stage_plan(side):
   affected=installed if name=='ROOT_INNER' else ({'ROOT_INNER':installed['ROOT_INNER']} if 'ROOT_INNER' in installed else {})
   if affected:
    result=thin.motion_check(name,parts[name],vec,affected,relative=name in thin.ROOT_NAMES)
    rows.append({'side':side,**result})
   installed[name]=parts[name]
  for name,vec in [('JAW_UPPER',(0,0,3.)),('JAW_LOWER',(0,0,-3.))]:
   result=thin.motion_check('WITHDRAW_'+name,parts[name],vec,{'ROOT_INNER':parts['ROOT_INNER']})
   rows.append({'side':side,**result})
  print(side,'changed preassembly pairs',sum(x['pairs'] for x in rows if x['side']==side),flush=True)
 bad=[x for x in rows if x['positive_pairs']]
 if any(sha(p)!=h for p,h in hashes.items()):raise ValueError('new native inputs changed')
 if any(x in sys.modules for x in ('mounted_mechanism','thin_mechanism')):raise ValueError('candidate generator imported')
 result={'manifest_sha256':sha(a.manifest),'base_report_sha256':sha(a.base_report),'reader_sha256':sha(__file__),'affected_pairs':sum(x['pairs'] for x in rows),'unchanged_source_parts_bound':44,'checks':rows,'failures':bad,'passed':not bad,'same_CAD_kernel':True,'candidate_builder_imported':False,'source_unchanged_pair_receipts_reused':True,'new_ears_preassembly_checked':True,'fixtures_preload_tools_and_material_strength_unqualified':True,'candidate_go':False,'manufacturing_go':False}
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('RESULT',result['passed'],'PAIRS',result['affected_pairs'],'FAILURES',len(bad),flush=True)
 if bad:raise SystemExit(1)
if __name__=='__main__':main()
