#!/usr/bin/env python3
"""Independent STEP participants plus native common failure preservation."""
from pathlib import Path
import hashlib,json,platform,sys,time,traceback
sys.dont_write_bytecode=True
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R6=ROOT.parent/'fpc-g2-route-candidates-20261013-r6/recovered_x230/input'
sys.path[:0]=[str(R6),str(R6/'guards')]
from actual_obstacle_and_jacobian import obstacle_factory
from strict_intersections import participant,strict_common
from verify_endpoint_exports import leaves,match
def load(n):return json.loads((ROOT/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_ex(path,expected):
    p=ROOT/path;wp=cq.importers.importStep(str(p));raw=wp.vals()
    if len(raw)!=1:raise ValueError('more than one raw import payload')
    parts,types=leaves(raw)
    if len(parts)!=expected:raise ValueError('complete raw payload count differs')
    return parts,{'path':path,'sha256':sha(p),'complete_positive_solid_leaves':len(parts),'all_raw_hierarchy':types}
def check(own,other,original):
    try:
        actual=strict_common(own,other)
        return {'actual':actual,'original_rejected':bool(original.get('rejected_boolean')),
          'reimport_matches_original_accepted_volume':None if 'checked_volume_mm3' not in original else abs(actual['checked_volume_mm3']-original['checked_volume_mm3'])<=1e-6}
    except Exception as exc:
        return {'actual_rejected':True,'message':str(exc),'traceback':traceback.format_exc(),
          'original_rejected':bool(original.get('rejected_boolean')),'reimport_matches_original_accepted_volume':False if 'checked_volume_mm3' in original else None}
def run():
    start=time.monotonic();factory,_=obstacle_factory();exports=[];checks=[];raw_diagnostics=[]
    r=load('corner_bay_followup_receipt.json')
    for row in r['rows']:
        if not row.get('finite_STEP'):continue
        parts,e=read_ex(row['finite_STEP']['path'],1);exports.append(e);own=parts[0];obs=factory(79.75 if row['pose']!='STOW' else 0.,8.2 if row['pose']=='OPEN_SEATED' else 0.)
        for name,other in obs.items():
            original=row['pairs']['NEW_MOVED_A_FINITE_FPC'][name];checks.append({'path':e['path'],'part':'NEW_MOVED_A_FINITE_FPC','obstacle':name,**check(own,other,original)})
            if original.get('rejected_boolean'):
                try:
                    raw=own.intersect(other);p=ROOT/'cad'/('REIMPORT_COMMON_DIAGNOSTIC_'+row['pose']+'_'+name+'.brep');cq.exporters.export(raw,str(p))
                    raw_diagnostics.append({'pose':row['pose'],'obstacle':name,'raw_valid':raw.isValid(),'raw_type':raw.ShapeType(),'raw_solid_count':len(raw.Solids()),
                      'raw_signed_volume_mm3':raw.Volume(),'BREP':str(p.relative_to(ROOT)),'sha256':sha(p),'invalid_or_negative_is_not_converted_to_zero':True})
                except Exception as exc:raw_diagnostics.append({'pose':row['pose'],'obstacle':name,'actual_exception':str(exc)})
    mounts=[{'export':load('corner_bay_mount_report.json')['export'],'pose_rows':load('corner_bay_mount_report.json')['mount_rows']}]
    mounts+=load('mini_mount_reposition_receipt.json')['rows']
    for m in mounts:
        parts,e=read_ex(m['export']['path'],5);exports.append(e)
        for row in m['pose_rows']:
            obs=factory(79.75 if row['pose']!='STOW' else 0.,8.2 if row['pose']=='OPEN_SEATED' else 0.)
            for name,pairs in row['pairs'].items():
                ref=next((v for v in pairs.values() if 'a' in v),None)
                if ref is None:raise ValueError('all original participant certificates absent')
                own=match(parts,ref['a'])
                for label,other in obs.items():checks.append({'path':e['path'],'pose':row['pose'],'part':name,'obstacle':label,**check(own,other,pairs[label])})
    before={e['path']:e['sha256'] for e in exports};after={n:sha(ROOT/n) for n in before}
    if before!=after:raise ValueError('complete STEP bytes changed')
    result={'host':platform.node(),'CadQuery':cq.__version__,'script_sha256':sha(Path(__file__)),'R7_builders_imported':False,
      'exports':exports,'raw_common_followup_diagnostics':raw_diagnostics,'checks':checks,
      'actual_rechecked_pairs':len(checks),'original_accepted_volume_reimport_disagreements':sum(c['reimport_matches_original_accepted_volume'] is False for c in checks),
      'actual_reimport_rejected_pairs':sum(bool(c.get('actual_rejected')) for c in checks),'original_rejected_pairs':sum(c['original_rejected'] for c in checks),
      'STEP_hashes_before':before,'STEP_hashes_after':after,'same_host_new_process_independent_builder_review':True,
      'actual_dynamic_FPC_full_PCB_or_clamp_qualification':False,'candidate_route_accepted':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (ROOT/'independent_followup_verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['actual_rechecked_pairs','original_accepted_volume_reimport_disagreements','actual_reimport_rejected_pairs','original_rejected_pairs','manufacturing_go']}))
if __name__=='__main__':run()
