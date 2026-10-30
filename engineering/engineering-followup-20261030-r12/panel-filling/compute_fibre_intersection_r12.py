"""Exact cell volumes for full-material orthogonal fibre-cover intersections."""
import argparse
from fractions import Fraction as F
import gzip,hashlib,json,os,resource,signal,time,traceback
from pathlib import Path


def identity(p):
    p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}


def parse(body):
    return [tuple(tuple(map(F,v)) for v in face['complete_swept_support']) for face in body['faces']]


def compute(first,second,output,label):
    import numpy as np
    grid=[sorted({v for B in first+second for v in B[k]}) for k in range(3)]
    n=tuple(len(g)-1 for g in grid)
    lookup=[{v:i for i,v in enumerate(g)} for g in grid]
    indexed=[[[[lookup[k][a],lookup[k][b]] for k,(a,b) in enumerate(B)] for B in bodies] for bodies in (first,second)]
    assert all(d>0 for d in n)
    estimate=2*2*4*(n[0]*n[1]+n[0]*n[2]+n[1]*n[2])+12*n[1]*n[2]
    assert estimate<384*1024*1024,'admitted 384MB array budget exceeded'
    basis={'grid_intervals':n,'positive_3D_cells':n[0]*n[1]*n[2],
           'estimated_arrays_bytes':estimate,'streaming_X_slices':True}
    (output/(label+'-grid-admission.json')).write_text(json.dumps(basis,indent=2)+'\n')
    def fibres(boxes):
        result=[]
        for axis in range(3):
            others=[k for k in range(3) if k!=axis]
            lo=np.full((n[others[0]],n[others[1]]),n[axis]+1,dtype=np.int32)
            hi=np.full(lo.shape,-1,dtype=np.int32)
            for B in boxes:
                a,b=others
                sl=(slice(*B[a]),slice(*B[b]))
                if B[a][0]==B[a][1] or B[b][0]==B[b][1]:continue
                np.minimum(lo[sl],B[axis][0],out=lo[sl]);np.maximum(hi[sl],B[axis][1],out=hi[sl])
            result.append((lo,hi))
        return result
    data=[fibres(boxes) for boxes in indexed]
    y=np.arange(n[1])[:,None];z=np.arange(n[2])[None,:]
    states={name:{'last_bytes':None,'start':None,'rows':None,'pieces':[], 'total':F(0),'occupied_cells':0,'sha':hashlib.sha256()}
            for name in ('Z_only','XYZ_intersection')}
    def finish_segment(state,xend):
        if state['start'] is None:return
        xstart=state['start'];rows=state['rows'];area=F(0)
        for j,runs in rows:
            dz=sum((grid[2][b]-grid[2][a] for a,b in runs),F(0))
            area+=(grid[1][j+1]-grid[1][j])*dz
        volume=(grid[0][xend]-grid[0][xstart])*area
        state['pieces'].append({'x_grid_interval':[xstart,xend],'occupied_y_rows':rows,'exact_volume':str(volume)})
        state['total']+=volume
    for i in range(n[0]):
        masks=[]
        for D in data:
            vertical=(z>=D[2][0][i,:,None])&(z<D[2][1][i,:,None])
            radial_x=(D[0][0]<=i)&(i<D[0][1])
            radial_y=(y>=D[1][0][i,None,:])&(y<D[1][1][i,None,:])
            masks.append((vertical,vertical&radial_x&radial_y))
        for mode,index in (('Z_only',0),('XYZ_intersection',1)):
            mask=masks[0][index]&masks[1][index]
            state=states[mode];packed=np.packbits(mask,axis=None).tobytes();state['sha'].update(packed)
            state['occupied_cells']+=int(mask.sum())
            if packed==state['last_bytes']:continue
            finish_segment(state,i)
            rows=[]
            for j in np.flatnonzero(np.any(mask,axis=1)):
                padded=np.empty(n[2]+2,dtype=np.int8);padded[0]=padded[-1]=0;padded[1:-1]=mask[j]
                changes=np.diff(padded);starts=np.flatnonzero(changes==1);ends=np.flatnonzero(changes==-1)
                rows.append([int(j),[[int(a),int(b)] for a,b in zip(starts,ends)]])
            state.update(last_bytes=packed,start=i,rows=rows)
    result={}
    for mode,state in states.items():
        finish_segment(state,n[0])
        proof={'schema':'razr-r12-complete-fibre-grid-intersection-v1','mode':mode,
               'grid_exact':[list(map(str,g)) for g in grid],'indexed_boundary_boxes':indexed,
               'complete_open_cells_partitioned':True,'closed_boundary_hulls_retained_measure_zero':True,
               'positive_tiny_cells_discarded':False,'grid_admission':basis,'x_pieces':state['pieces'],
               'packed_complete_intersection_mask_sha256':state['sha'].hexdigest(),
               'occupied_open_cells':state['occupied_cells'],'exact_intersection_upper_volume':str(state['total'])}
        path=output/(label+'-'+mode+'.json.gz')
        with gzip.open(path,'wt') as stream:json.dump(proof,stream,separators=(',',':'))
        result[mode]={'proof':identity(path),'exact_upper_mm3':str(state['total']),
                      'upper_mm3_approx':float(state['total']),'original_1e_minus7_gate_passes':state['total']<=F(1e-7),
                      'occupied_open_cells':state['occupied_cells'],'x_runs':len(state['pieces']),
                      'packed_mask_sha256':state['sha'].hexdigest()}
    assert states['XYZ_intersection']['total']<=states['Z_only']['total']
    return {'label':label,'grid':basis,'results':result,
            'actual_collision_proved':False,'native_material_set_identity_proved':False,
            'compiled_error_uniformly_bounded':False,'whole_15D_G2':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--native-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180-second complete fibre computation')));signal.alarm(180)
    report={'schema':'razr-r12-current-key-panel-whole-material-fibre-intersection-v1','completed':False,'pairs':[],
            'source':identity(__file__),'original_threshold_exact':str(F(1e-7)),
            'native_Common_calls':0,'native_set_identity_or_uniform_compiled_error_proved':False,'full_continuous_G2':False,
            'limits':{'seconds':180,'address_space_bytes':805306368,'cpus':1}}
    try:
        native=json.loads(args.native_report.read_text());assert native['completed']
        report['native_boundary_report']=identity(args.native_report)
        first=parse(native['bodies']['A_BACK_PANEL'])
        for key in ('L_KEY','R_KEY'):
            report['pairs'].append(compute(first,parse(native['bodies'][key]),args.output,key))
            (args.output/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
        report['completed']=True
    except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('completed','pairs','seconds','peak_RSS_bytes','failure')}))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
