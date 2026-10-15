"""Reimport every assembly solid, then recheck original nominal motion pairs.
No scene/repair builders are imported. Complete insertion rejection is retained
separately from the now-clear outer-root geometry.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util,platform,time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True,type=Path)
    ap.add_argument('--assembly-receipt',required=True,type=Path)
    ap.add_argument('--assembly-sha256',required=True)
    ap.add_argument('--sweep-receipt',required=True,type=Path)
    ap.add_argument('--sweep-sha256',required=True)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    for p,h in [(args.assembly_receipt,args.assembly_sha256),(args.sweep_receipt,args.sweep_sha256)]:
        if sha(p)!=h:raise ValueError('receipt bytes changed')
    helper=args.repo/'integration/verify_stow_sweep.py'
    spec=importlib.util.spec_from_file_location('independent_sweep_reader',helper)
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    assembly=json.loads(args.assembly_receipt.read_text());sweep=json.loads(args.sweep_receipt.read_text())
    inputs={str(p):sha(p) for p in (args.assembly_receipt,args.sweep_receipt,helper)}
    stow=[];payloads=[];start=time.monotonic()
    for entry in assembly['STEP_exports']:
        path=args.assembly_receipt.parent/entry['path']
        if sha(path)!=entry['sha256']:raise ValueError('assembly STEP changed')
        inputs[str(path)]=sha(path)
        raw=v.cq.importers.importStep(str(path)).vals()
        if len(raw)!=1:raise ValueError('multiple unaccounted assembly roots')
        leaves,volume=v.material(raw[0])
        if len(leaves)!=entry['expected_part_count']:raise ValueError('complete assembly leaves missing')
        payloads.append({'path':str(path),'positive_solid_leaves':len(leaves),'whole_signed_volume_mm3':volume})
        if path.name.startswith('STOW'):stow=leaves
    if len(stow)!=46 or len(payloads)!=2 or sum(p['positive_solid_leaves'] for p in payloads)!=92:raise ValueError('full STOW/OPEN payload changed')
    def match(cert):
        found=[]
        for shape in stow:
            box=shape.BoundingBox()
            if abs(shape.Volume()-cert['signed_volume_mm3'])<1e-7 and all(abs(getattr(box,k)-x)<1e-7 for k,x in cert['bounds_mm'].items()):found.append(shape)
        if len(found)!=1:raise ValueError('ambiguous/missing complete native assembly participant')
        return found[0]
    checks=[]
    for row in sweep['rows']:
        entry=row['exports']['original_pawl'];path=args.sweep_receipt.parent/entry['path']
        if sha(path)!=entry['sha256']:raise ValueError('source pawl STEP changed')
        inputs[str(path)]=sha(path)
        original=v.single(v.cq.importers.importStep(str(path)).val())
        delta=row['sweep_method']['translation_mm'];returned,_=v.reverse_envelope(original,delta)
        parked=original.translate(delta);inserted,_=v.reverse_envelope(parked,[0.,0.,10.])
        for operation,key,envelope in [('PAWL_RETURN','all_fixed_part_checks',returned),('PARKED_PAWL_INSERTION','insertion_checks',inserted)]:
            for name,expected in row[key].items():
                participant=match(expected['a'])
                actual=v.signed_common(participant,envelope)
                old=expected['checked_volume_mm3']
                if abs(actual-old)>1e-7:raise ValueError('independent whole-assembly motion pair changed: '+name)
                checks.append({'side':row['side'],'operation':operation,'part':name,'native_common_mm3':actual,'producer_common_mm3':old,'positive':actual>1e-7})
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('inputs changed during native verification')
    positives=[row for row in checks if row['positive']]
    result={'host':platform.node(),'CadQuery':v.cq.__version__,'source_sha256':sha(__file__),
            'input_SHA256':inputs,'inputs_unchanged':True,'full_assembly_STEPs':payloads,
            'complete_positive_solid_leaves':92,'checks':checks,'native_pairs':len(checks),
            'positive_pairs':positives,'return_pairs_all_clear':not any(r['operation']=='PAWL_RETURN' for r in positives),
            'insertion_stage_all_clear':not any(r['operation']=='PARKED_PAWL_INSERTION' for r in positives),
            'scene_or_repair_builder_imported':False,'independent_reader_same_CAD_kernel':True,
            'geometry_repair_is_not_complete_installation_or_load_qualification':True,
            'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'complete_positive_solids':92,'native_pairs':len(checks),'positive_pairs':len(positives),'return_clear':result['return_pairs_all_clear'],'insertion_clear':result['insertion_stage_all_clear'],'manufacturing_go':False}))


if __name__=='__main__':main()
