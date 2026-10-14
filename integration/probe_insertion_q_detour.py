"""Bounded detour diagnostic on complete serialized assembly inputs, not a product route."""
from pathlib import Path
import argparse,json,hashlib,sys,time,platform
import verify_stow_sweep as v

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
 out=a.output;out.mkdir(parents=True,exist_ok=False);e=a.evidence
 rp=e/'assembly-fixed-slots/split-receipt.json';sp=e/'sweep-fixed-slots/report.json'
 receipts={str(rp):sha(rp),str(sp):sha(sp)};assembly=json.loads(rp.read_text());sweep=json.loads(sp.read_text())
 entry=next(x for x in assembly['STEP_exports'] if x['path'].startswith('cad/STOW'))
 path=rp.parent/entry['path'];assert sha(path)==entry['sha256'];receipts[str(path)]=sha(path)
 raw=v.cq.importers.importStep(str(path)).vals();assert len(raw)==1
 leaves,volume=v.material(raw[0]);assert len(leaves)==46
 def match(cert):
  found=[s for s in leaves if abs(s.Volume()-cert['signed_volume_mm3'])<1e-7 and all(abs(getattr(s.BoundingBox(),k)-n)<1e-7 for k,n in cert['bounds_mm'].items())]
  if len(found)!=1:raise ValueError('ambiguous assembly component')
  return found[0]
 rows=[];start=time.monotonic()
 for side in ['L']:
  sr=next(r for r in sweep['rows'] if r['side']==side)
  p=sp.parent/sr['exports']['parked_pawl']['path'];assert sha(p)==sr['exports']['parked_pawl']['sha256'];receipts[str(p)]=sha(p)
  parked=v.single(v.cq.importers.importStep(str(p)).val())
  fixed={n:match(x['a']) for n,x in sr['insertion_checks'].items()}
  sign=-1 if side=='L' else 1
  for extra_e in [0.,.02,.05,.1,.2,.5,-.02,-.05,-.1,-.2]:
   first=parked.translate((0.,-extra_e,0.));ins,_=v.reverse_envelope(first,(0.,0.,10.))
   checks=[{'segment':'AXIAL_AT_Q_OFFSET','part':n,'volume_mm3':v.signed_common(s,ins)} for n,s in fixed.items()]
   if extra_e!=0:
    close,_=v.reverse_envelope(parked,(0.,-extra_e,0.))
    checks += [{'segment':'SETTLED_Q_RETURN','part':n,'volume_mm3':v.signed_common(s,close)} for n,s in fixed.items()]
   bad=[x for x in checks if x['volume_mm3']>1e-7]
   row={'side':side,'extra_q_mm':extra_e,'fixed_part_count':len(fixed),'checks':checks,'positive':bad,'candidate_clear':not bad}
   rows.append(row);(out/'progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2))
   print(side,extra_e,'positive',[(x['segment'],x['part'],x['volume_mm3']) for x in bad],flush=True)
 assert receipts=={p:sha(Path(p)) for p in receipts}
 result={'rows':rows,'source_sha256':sha(Path(__file__)),'input_SHA256':receipts,'complete_assembly_leaf_count':46,'inputs_unchanged':True,'scene_or_repair_builder_imported':False,'elapsed_seconds':time.monotonic()-start,'manufacturing_go':False}
 (out/'report.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
