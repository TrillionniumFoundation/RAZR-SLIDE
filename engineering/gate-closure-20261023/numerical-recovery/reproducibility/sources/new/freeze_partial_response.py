"""Hash-bind completed linear response columns after a stopped worker exits.

This records an unfinished linear algebra computation. It is explicitly not a
bearing restart, finite-QP checkpoint, complete H, or contact qualification.
"""
from pathlib import Path
import argparse
import json
import os
import numpy as np
from scipy.sparse import load_npz
from rebuild_l2_only import sha, save_json


def main(args):
    supervision=json.loads(args.supervisor_report.read_text())
    assert supervision['finished'] is True and supervision['exit_code']!=0
    output=Path(supervision['output'])
    progress_path=output/'progress.json'
    progress=json.loads(progress_path.read_text())
    assert sha(progress_path)==supervision['worker_progress_sha256']
    assert progress==supervision['worker_final_progress']
    worker_source=supervision['worker_source']
    assert progress['source_sha256'][worker_source]==supervision['worker_sha256']
    assert sha(worker_source)==supervision['worker_sha256']
    assert progress['completed'] is False
    allowed_errors={'TimeoutError','MemoryError','RuntimeError',None}
    assert progress.get('error_type') in allowed_errors
    if progress.get('error_type')=='RuntimeError':
        assert ('time budget' in progress.get('error','') or 'disk reserve' in progress.get('error',''))
    m=progress['ordered_seed_columns'];n=progress['original_vector_dofs']
    completed=progress.get('completed_columns')
    assert type(completed) is int and 0<completed<=m
    partial=Path(progress['private_temporary_directory'])/'H.partial.npy'
    H=np.load(partial,mmap_mode='r',allow_pickle=False)
    assert H.shape==(m,m) and H.dtype==np.float64
    for lo in range(0,completed,128):
        assert np.isfinite(H[:,lo:min(lo+128,completed)]).all()
    del H
    with partial.open('rb') as source:os.fsync(source.fileno())
    C=load_npz(output/'C.npz')
    assert C.shape==(n,m) and C.nnz==progress['C_nnz']
    points=json.loads((output/'points.json').read_text())
    assert len(points)==m
    for name,digest in {**progress['input_sha256'],**progress['source_sha256']}.items():
        assert sha(name)==digest
    record={'schema':'razr-partial-linear-response-v1','body':progress['body'],
            'completed_columns':completed,'required_columns':m,'original_vector_dofs':n,
            'partial_H_path':str(partial),'partial_H_sha256':sha(partial),
            'C_path':str(output/'C.npz'),'C_sha256':sha(output/'C.npz'),
            'points_path':str(output/'points.json'),'points_sha256':sha(output/'points.json'),
            'progress_path':str(progress_path),'progress_sha256':sha(progress_path),
            'supervisor_report_path':str(args.supervisor_report),'supervisor_report_sha256':sha(args.supervisor_report),
            'input_sha256':progress['input_sha256'],'producer_source_sha256':progress['source_sha256'],
            'freeze_source_sha256':{str(Path(__file__)):sha(Path(__file__))},
            'linear_solve_residual_max':progress.get('linear_solve_residual_max'),
            'producer_response_solve_seconds':progress.get('response_solve_seconds'),
            'complete_H':False,'accepted_finite_QP':False,'bearing_restart_checkpoint':False,
            'historical_checkpoint_restored':False,'contact_or_physical_qualification':False,
            'resume_rule':'Recreate exact full K and ordered C, verify all hashes, recompute from completed_columns onward, then validate all complete-H five inverse probe actions.'}
    target=output/'partial-linear-response-manifest.json'
    assert not target.exists()
    save_json(target,record)
    print(json.dumps({'manifest':str(target),'manifest_sha256':sha(target),
                      'completed_columns':completed,'required_columns':m}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supervisor-report',type=Path,required=True)
    main(parser.parse_args())
