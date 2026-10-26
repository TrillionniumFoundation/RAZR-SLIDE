"""Recover embedded historical JSON bytes and accept only exact original SHA256.

The archived nested reports preserve ordered JSON values. The original writers
used json.dumps(indent=2) plus a newline. Re-encoding them can restore exact old
metadata; the immutable original external-file digest is the acceptance test.
Missing response/K numerical bytes are never synthesized or relabeled here.
"""
from pathlib import Path
import gzip
import hashlib
import json

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def main():
    output=BASE/'historical-original'
    output.mkdir(exist_ok=False)
    nested=ROOT/'engineering/nested-contact-20261017'
    durable_path=nested/'durable-fields-and-checkpoints.json'
    durable=json.loads(durable_path.read_text())
    identities={row['durable_path']:row for row in durable['immutable_files']}
    identities.update({row['durable_path']:row for row in durable['existing_refined_inputs_rechecked'].values()})
    volume_prefix='/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3'
    state_prefix='/home/qian-qi/.local/share/razr-slide-evidence/nested-contact-20261017/level-2/final-case7-state'
    source_seed=nested/'level-2/case-6/report.json.gz'
    source_summary=nested/'level-2/SUMMARY.json'
    volume_path=ROOT/'engineering/volume-convergence-20261017/volume-matrix-levels.json'
    seed=json.loads(gzip.decompress(source_seed.read_bytes()))
    summary=json.loads(source_summary.read_text())
    volume=json.loads(volume_path.read_text())
    case7=next(row for row in summary['cases'] if row['case']==7)
    manifest={'case':7,'exchange':0,'volume_level':2,'input_sha256':seed['input_sha256'],
              'source_sha256':seed['source_sha256'],
              'response_sha256':identities[state_prefix+'/response.npz']['sha256'],
              'points_sha256':identities[state_prefix+'/points.json']['sha256'],
              'state_is_finite_QP_not_gap_qualification':True,
              'minimum_gap_mm':case7['minimum_gap_mm'],'gap_tolerance_mm':1e-7}
    reconstructed=[('legacy-seed/points.json',state_prefix+'/points.json',seed['contact_points']),
                   ('legacy-seed/manifest.json',state_prefix+'/manifest.json',manifest)]
    for body in volume:
        level=next(row for row in body['levels'] if row['level']==2)
        name=body['body']
        reconstructed.append((f'volume/{name}/level-2/report.json',f'{volume_prefix}/{name}/level-2/report.json',level))
    rows=[]
    for relative,original,value in reconstructed:
        expected=identities[original]
        payload=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
        sha=hashlib.sha256(payload).hexdigest()
        assert sha==expected['sha256'] and len(payload)==expected['bytes'],original
        target=output/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(payload)
        assert digest(target)==expected['sha256']
        rows.append({'historical_path':original,'recovered_path':str(target),'bytes':len(payload),
                     'sha256':sha,'exact_original_bytes_verified':True,
                     'method':'original JSON values serialized by the original writer format, accepted only by immutable original SHA256'})
    for body in ('panel','frame'):
        for name in ('mesh.npz','loads.npz'):
            original=f'{volume_prefix}/{body}/level-2/{name}'
            expected=identities[original]
            target=BASE/'frozen-original'/body/name
            assert target.stat().st_size==expected['bytes'] and digest(target)==expected['sha256']
            rows.append({'historical_path':original,'recovered_path':str(target),'bytes':target.stat().st_size,
                         'sha256':expected['sha256'],'exact_original_bytes_verified':True,
                         'method':'exact original member recovered from frozen-elastic-inputs.tar.gz'})
    missing=[identities[f'{volume_prefix}/{body}/level-2/K.npz'] for body in ('panel','frame')]
    missing.append(identities[state_prefix+'/response.npz'])
    sources=[Path(__file__),durable_path,source_seed,source_summary,volume_path,
             ROOT/'engineering/volume-convergence-20261017/solve_enriched_contact.py',
             ROOT/'engineering/volume-convergence-20261017/assemble_volume.py']
    receipt={'schema':'razr-exact-PR35-input-recovery-v2','original_required_inputs':11,
             'exact_original_files_recovered':8,'files':rows,
             'historical_numerical_files_still_unavailable':missing,
             'source_sha256':{str(path):digest(path) for path in sources},
             'new_K_matrices_exist_under_separate_identity':True,
             'historical_reports_must_not_be_paired_with_new_K_hashes':True,
             'legacy_state_usable':False,'reason':'historical response.npz numerical matrix remains unavailable',
             'new_QP_executed':False,'historical_checkpoint_restored':False,
             'physical_or_contact_qualification':False}
    (BASE/'exact-PR35-input-recovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'exact_original_files_recovered':8,'remaining_numerical_files':3,
                      'receipt':str(BASE/'exact-PR35-input-recovery.json')}))


if __name__=='__main__':
    main()
