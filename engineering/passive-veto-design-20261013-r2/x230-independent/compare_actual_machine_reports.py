#!/usr/bin/env python3
"""Compare actual Cloud/X230 STEP receipts, excluding only runtime identity."""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
TOL=1e-7

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    maxima=[];numeric_count=0;identity_count=0
    ignore={'environment','host'}
    def compare(a,b,path=''):
        nonlocal numeric_count,identity_count
        if isinstance(a,bool) or isinstance(b,bool):
            if type(a) is not type(b) or a!=b:raise ValueError('Boolean mismatch '+path)
            identity_count+=1;return
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            if not math.isfinite(a) or not math.isfinite(b):raise ValueError('Nonfinite numeric '+path)
            d=abs(a-b);numeric_count+=1
            if d>TOL or (type(a) is int and type(b) is int and a!=b):raise ValueError('Numeric mismatch '+path)
            maxima.append((d,path));return
        if isinstance(a,dict) and isinstance(b,dict):
            ka=set(a)-ignore;kb=set(b)-ignore
            if ka!=kb:raise ValueError('Field mismatch '+path)
            for k in sorted(ka):compare(a[k],b[k],path+'/'+k)
            return
        if isinstance(a,list) and isinstance(b,list):
            if len(a)!=len(b):raise ValueError('List length mismatch '+path)
            for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
            return
        if type(a) is not type(b) or a!=b:raise ValueError('Identity mismatch '+path)
        identity_count+=1
    files=[]
    for name in ('independent-exported-veto-check.json','material-support-contact-result.json','full-step-payload-result.json'):
        local=PROJECT/'independent'/name;remote=HERE/name
        compare(json.loads(local.read_text()),json.loads(remote.read_text()),name)
        files.append({'name':name,'Cloud_result_sha256':sha(local),'X230_result_sha256':sha(remote)})
    native=json.loads((HERE/'remote-native-result.json').read_text())
    if not native['all_transferred_source_and_STEP_bytes_unchanged'] or any(n['native_exit_code']!=0 for n in native['native_operations']):
        raise ValueError('X230 did not complete all native actual input checks unchanged')
    maximum=max(maxima,default=(0.,''))
    report={'actual_machine_report_inputs':files,'numeric_values_compared':numeric_count,
        'identity_values_compared':identity_count,'maximum_absolute_numeric_difference':maximum[0],
        'maximum_difference_location':maximum[1],'numeric_tolerance':TOL,
        'excluded_fields':['runtime environment (host, Python runtime version)','top-level host identity'],
        'all_geometry_rows_state_flags_input_source_and_STEP_hashes_match':True,
        'three_X230_native_operations_exit_zero':True,
        'computer_repeatability_does_not_supply_physical_qualification':True,'manufacturing_go':False}
    (HERE/'local-vs-x230-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
