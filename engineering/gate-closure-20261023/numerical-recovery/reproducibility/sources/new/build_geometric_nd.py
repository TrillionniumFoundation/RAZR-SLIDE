"""New symmetric nested-dissection permutation of an unchanged real K graph.

Read the stored CSC pattern, verify every three-axis nodal block, and split
using original coordinates plus an exact bipartite vertex cover. Every split
is checked against the actual sparse graph. No stiffness, support, load,
arithmetic tolerance, or solver is changed or executed by this program.
"""
from pathlib import Path
import argparse
import gc
import json
import os
import resource
import sys
import time
import traceback
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching, reverse_cuthill_mckee
from rebuild_l2_only import sha, save_json

BASE=Path(__file__).resolve().parent


def unreclaimable():
    p=Path('/sys/fs/cgroup/memory.stat')
    values={k:int(v) for k,v in (line.split() for line in p.read_text().splitlines())}
    return values['anon']+values.get('shmem',0)+max(values.get('kernel',0)-values.get('slab_reclaimable',0),0)+values.get('unevictable',0)


def minimum_vertex_cover(cross):
    # SciPy perm_type='column' returns one matched column per left row.
    matching=maximum_bipartite_matching(cross,perm_type='column')
    assert matching.shape==(cross.shape[0],)
    inverse=np.full(cross.shape[1],-1,dtype=np.int32)
    matched=np.flatnonzero(matching>=0)
    inverse[matching[matched]]=matched
    seen_left=matching<0;seen_right=np.zeros(cross.shape[1],dtype=bool)
    frontier=np.flatnonzero(seen_left).tolist()
    for left in frontier:
        for right in cross.indices[cross.indptr[left]:cross.indptr[left+1]]:
            if right==matching[left] or seen_right[right]:continue
            seen_right[right]=True
            next_left=inverse[right]
            if next_left>=0 and not seen_left[next_left]:
                seen_left[next_left]=True;frontier.append(int(next_left))
    cover_left=~seen_left;cover_right=seen_right
    assert int(cover_left.sum()+cover_right.sum())==len(matched)
    assert cross[~cover_left][:,~cover_right].nnz==0
    return cover_left,cover_right,len(matched)


def main(args):
    start=time.monotonic();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,)*2)
    state={'schema':'razr-new-graph-ND-order-progress-v1','body':args.body,'completed':False,'factorization_executed':False}
    def guard():
        if unreclaimable()>int(6.8*1024**3):raise MemoryError('shared cgroup unreclaimable guard')
        if time.monotonic()-start>120:raise TimeoutError('ordering 120-second budget')
    def progress(phase,**extra):
        state.update(phase=phase,seconds=time.monotonic()-start,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**extra)
        save_json(out/'progress.json',state);print(json.dumps(state),flush=True)
    try:
        guard()
        folder=args.volume.resolve()/args.body/'level-2'
        r=json.loads((folder/'report.json').read_text())
        inputs={str(folder/'report.json'):sha(folder/'report.json')}
        for name,key in [('K.npz','K_sha256'),('loads.npz','loads_sha256')]:
            assert sha(folder/name)==r[key];inputs[str(folder/name)]=r[key]
        sources={str(Path(__file__).resolve()):sha(Path(__file__))}
        with np.load(folder/'K.npz',allow_pickle=False) as z:
            index=z['indices'];pointer=z['indptr'];shape=z['shape']
            assert str(z['format'].item().decode())=='csc'
        n=int(shape[0]);assert np.array_equal(shape,[n,n]) and n%3==0
        count=n//3;degrees=np.diff(pointer)
        assert np.all(degrees%3==0)
        assert np.array_equal(degrees[::3],degrees[1::3]) and np.array_equal(degrees[1::3],degrees[2::3])
        scalar_pointer=np.r_[0,np.cumsum(degrees[::3]//3,dtype=np.int64)]
        scalar_index=np.empty(int(scalar_pointer[-1]),dtype=np.int32)
        for node in range(count):
            column=index[pointer[3*node]:pointer[3*node+1]]
            assert np.array_equal(column,index[pointer[3*node+1]:pointer[3*node+2]])
            assert np.array_equal(column,index[pointer[3*node+2]:pointer[3*node+3]])
            block=column.reshape(-1,3)
            assert np.all(block[:,0]%3==0) and np.all(block[:,1]==block[:,0]+1) and np.all(block[:,2]==block[:,0]+2)
            scalar_index[scalar_pointer[node]:scalar_pointer[node+1]]=block[:,0]//3
            if node%16384==0:guard()
        graph=csr_matrix((np.ones(len(scalar_index),dtype=np.bool_),scalar_index,scalar_pointer),shape=(count,count))
        assert (graph!=graph.T).nnz==0
        graph.setdiag(False);graph.eliminate_zeros();graph.sort_indices()
        del index,pointer,degrees,scalar_index,scalar_pointer
        gc.collect()
        with np.load(folder/'loads.npz',allow_pickle=False) as z:
            xyz=z['xyz'];fixed=z['D']
        assert xyz.shape==(3,n) and np.array_equal(xyz[:,::3],xyz[:,1::3]) and np.array_equal(xyz[:,1::3],xyz[:,2::3])
        coordinates=xyz[:,::3].T.copy();del xyz
        splits=[];leaves=[]
        progress('actual_symmetric_nodal_graph_verified',scalar_nodes=count,scalar_graph_edges=int(graph.nnz),
                 vector_dofs=n,fixed_dofs=len(fixed),input_sha256=inputs,source_sha256=sources)
        def ordered(nodes,depth):
            guard()
            if len(nodes)<=args.leaf:
                sub=graph[nodes][:,nodes]
                local=reverse_cuthill_mckee(sub,symmetric_mode=True)
                leaves.append({'depth':depth,'nodes':len(nodes)})
                return nodes[local]
            extent=np.ptp(coordinates[nodes],axis=0);axis=int(np.argmax(extent))
            order=np.argsort(coordinates[nodes,axis],kind='stable')
            cut=len(nodes)//2;left=nodes[order[:cut]];right=nodes[order[cut:]]
            cross=graph[left][:,right].tocsr()
            if cross.nnz:
                cover_l,cover_r,matching=minimum_vertex_cover(cross)
            else:
                cover_l=np.zeros(len(left),bool);cover_r=np.zeros(len(right),bool);matching=0
            separator=np.r_[left[cover_l],right[cover_r]]
            first=left[~cover_l];second=right[~cover_r]
            # A direct check on the original graph, independently of matching.
            assert graph[first][:,second].nnz==0
            row={'depth':depth,'nodes':len(nodes),'axis':axis,'left':len(first),'right':len(second),
                 'separator':len(separator),'cross_edges':int(cross.nnz),'maximum_matching':matching,
                 'minimum_vertex_cover_verified':True,'original_graph_remaining_cross_edges':0}
            splits.append(row)
            del cross,left,right,order
            if min(len(first),len(second))<max(1,len(nodes)//20):
                # Do not pretend an unbalanced partition is useful ND.
                row['unbalanced_fallback']=True
                local=reverse_cuthill_mckee(graph[nodes][:,nodes],symmetric_mode=True)
                leaves.append({'depth':depth,'nodes':len(nodes),'fallback':True})
                return nodes[local]
            a=ordered(first,depth+1);b=ordered(second,depth+1)
            if len(separator):
                p=reverse_cuthill_mckee(graph[separator][:,separator],symmetric_mode=True)
                separator=separator[p]
            return np.r_[a,b,separator]
        permutation=ordered(np.arange(count,dtype=np.int32),0)
        assert np.array_equal(np.sort(permutation),np.arange(count))
        mask=np.ones(n,dtype=bool);mask[fixed]=False;free=np.flatnonzero(mask)
        original=(3*permutation[:,None]+np.arange(3)).ravel();original=original[mask[original]]
        lookup=np.full(n,-1,dtype=np.int32);lookup[free]=np.arange(len(free),dtype=np.int32)
        p=lookup[original]
        assert np.array_equal(np.sort(p),np.arange(len(free))) and np.array_equal(free[p],original)
        np.savez_compressed(out/'permutation.npz',scalar_order=permutation,free_order=p,
                            free_original_dofs=free,permuted_original_dofs=original)
        levels=[]
        for depth in sorted({r['depth'] for r in splits}):
            rows=[r for r in splits if r['depth']==depth]
            levels.append({'depth':depth,'splits':len(rows),'separator_nodes':sum(r['separator'] for r in rows),
                           'maximum_separator_nodes':max(r['separator'] for r in rows),
                           'sum_separator_vector_dense_entries':sum((3*r['separator'])**2 for r in rows)})
        for path,digest in {**inputs,**sources}.items():assert sha(path)==digest
        result={**state,'completed':True,'schema':'razr-new-geometric-ND-order-v1',
                'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'permutation_sha256':sha(out/'permutation.npz'),'free_vector_dofs':len(free),
                'algorithm':'longest-original-coordinate-axis median; exact bipartite minimum vertex cover; recursively left/right then separator; RCM leaves',
                'leaf_scalar_limit':args.leaf,'all_original_graph_separator_cross_checks_passed':True,
                'levels':levels,'split_records':splits,'leaves':leaves,
                'original_constraints_or_K_changed':False,'original_RHS_or_tolerances_changed':False,
                'new_permutation_identity':True,'factorization_executed':False,'lower_fill_not_yet_measured':True,
                'future_solver':'Kff[p,p], splu(permc_spec=NATURAL,diag_pivot_thresh=0,SymmetricMode=True); rhs[p]; u[p]=solved; validate complete original Kff residual and five original inverse probes',
                'historical_factor_bytes_restored':False,'physical_or_EP5_qualification':False}
        save_json(out/'report.json',result)
        progress('completed',completed=True,permutation_sha256=result['permutation_sha256'],
                 report_sha256=sha(out/'report.json'),split_count=len(splits))
    except BaseException as error:
        progress('interrupted_or_failed',error_type=type(error).__name__,error=str(error))
        traceback.print_exc();raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--body',choices=['panel','frame'],required=True)
    p.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--leaf',type=int,default=128)
    main(p.parse_args())
