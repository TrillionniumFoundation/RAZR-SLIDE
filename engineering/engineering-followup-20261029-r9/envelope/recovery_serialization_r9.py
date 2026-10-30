"""Preserve complete committed payloads after a failed qualified write."""
import gzip
import hashlib
import json
from pathlib import Path
import time


def identity(path):
    path=Path(path)
    return {'path':str(path.resolve()),'bytes':path.stat().st_size,
            'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest()}


def pending_commit_state(trace,live_root):
    children=trace.get('completed_children',[]);index=trace.get('node_index')
    if index is None or not 0<=index<len(live_root['nodes']):return 'undetermined'
    parent=live_root['nodes'][index]
    if parent['kind']!='split':return 'uncommitted'
    ids=[c['id'] for c in children]
    if len(ids)==2 and parent['children']==ids and all(live_root['nodes'][i] is c for i,c in zip(ids,children)):
        return 'committed_before_interruption'
    return 'undetermined'


def recover(payloads,destination,pending=None):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);start=time.monotonic();entries=[]
    for name,payload in payloads:
        target=destination/name
        with gzip.open(target,'wt') as f:json.dump(payload,f,separators=(',',':'))
        with gzip.open(target,'rt') as f:restored=json.load(f)
        if restored!=payload:raise ValueError('recovery readback differs')
        entries.append(identity(target))
    if pending is not None:
        p=destination/'pending-attempt-evidence.json.gz'
        with gzip.open(p,'wt') as f:json.dump(pending,f,separators=(',',':'))
        entries.append(identity(p))
    record={'schema':'razr-r9-failed-run-committed-state-recovery','completed':True,
            'qualified_execution':False,'time_after_qualification_failure_seconds':time.monotonic()-start,
            'payload_count':len(payloads),'files':entries}
    (destination/'recovery-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def controls():
    import tempfile
    import atomic_refinement_r9 as atomic
    with tempfile.TemporaryDirectory(prefix='razr-recovery-') as tmp:
        p=Path(tmp);payloads=[('frame-1.json.gz',{'frame':1,'roots':[1,2]}),('frame-2.json.gz',{'frame':2,'roots':[3,4]})]
        failure=None
        try:
            for index,(name,data) in enumerate(payloads):
                with gzip.open(p/name,'wt') as f:
                    if index==1:
                        f.write('{"frame":2,"roots":[')
                        raise TimeoutError('injected deadline while second frame serialized')
                    json.dump(data,f)
        except TimeoutError as exc:failure=str(exc)
        assert failure=='injected deadline while second frame serialized'
        partial=p/'frame-2.json.gz';before=identity(partial)
        report=recover(payloads,p/'recovery')
        assert report['completed'] and report['payload_count']==2 and report['qualified_execution'] is False
        assert identity(partial)==before
        try:
            with gzip.open(partial,'rt') as f:json.load(f)
        except json.JSONDecodeError:pass
        else:raise AssertionError('actual truncated original falsely complete')
        original={'nodes':[{'id':0,'depth':0,'kind':'leaf'}]};trace={}
        new=atomic.prepare_split(original,0,0,'1/2',(None,None),lambda B,i,d:{'id':i,'depth':d,'kind':'leaf'},trace)
        assert pending_commit_state(trace,original)=='uncommitted'
        assert pending_commit_state(trace,new)=='committed_before_interruption'
        return {'schema':'razr-r9-recovery-serialization-controls','completed':True,
                'original_failure':failure,'original_truncated_payload_preserved':True,
                'recovery_payloads_reopened_and_equal':2,'qualification_after_failure':False,
                'pre_commit_and_post_commit_pending_labels_distinguished':True,
                'source':identity(__file__)}


if __name__=='__main__':
    result=controls();Path(__file__).with_name('RECOVERY_SERIALIZATION_CONTROLS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
