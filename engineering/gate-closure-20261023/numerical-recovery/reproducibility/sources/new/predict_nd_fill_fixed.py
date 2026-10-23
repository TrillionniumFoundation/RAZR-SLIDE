"""Exact symbolic scalar Cholesky counts for the original block K graph.

This analyzes graph fill only. No elastic factor or inverse is computed. The
stored NPZ indices are read-only memory maps, avoiding large anonymous copies.
Each scalar graph edge represents the verified full 3x3 original nodal block.
Removing actual fixed coordinates can only remove paths from this upper-bound
graph. Numeric pivoting and SuperLU allocation peaks remain unmeasured.
"""
from pathlib import Path
import argparse
import gc
import json
import resource
import struct
import time
import zipfile
import numpy as np
from scipy.sparse import csr_matrix,csc_matrix
from rebuild_l2_only import sha,save_json
from build_geometric_nd import unreclaimable


def stored_array(path,name):
    with zipfile.ZipFile(path) as archive:
        member=archive.getinfo(name+'.npy')
        assert member.compress_type==zipfile.ZIP_STORED
        with Path(path).open('rb') as stream:
            stream.seek(member.header_offset)
            header=stream.read(30);parts=struct.unpack('<4s5H3I2H',header)
            assert parts[0]==b'PK\x03\x04'
            stream.seek(parts[-2]+parts[-1],1)
            version=np.lib.format.read_magic(stream)
            assert version==(1,0)
            shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
            assert not dtype.hasobject
            offset=stream.tell()
    return np.memmap(path,mode='r',offset=offset,dtype=dtype,shape=shape,
                     order='F' if fortran else 'C')


def column_counts(graph,callback=lambda *x:None):
    a=graph.tocsc();n=a.shape[0]
    parent=np.full(n,-1,np.int32);ancestor=np.full(n,-1,np.int32)
    for k in range(n):
        for raw in a.indices[a.indptr[k]:a.indptr[k+1]]:
            i=int(raw)
            if i>=k:break
            while i>=0 and i<k:
                previous=int(ancestor[i]);ancestor[i]=k
                if previous<0:parent[i]=k
                i=previous
        if k%4096==0:callback('elimination_tree',k,n)
    del ancestor
    seen=np.full(n,-1,np.int32);counts=np.ones(n,np.int64)
    for k in range(n):
        seen[k]=k
        for raw in a.indices[a.indptr[k]:a.indptr[k+1]]:
            i=int(raw)
            if i>=k:break
            while seen[i]!=k:
                assert i>=0
                seen[i]=k;counts[i]+=1;i=int(parent[i])
        if k%4096==0:callback('symbolic_counts',k,n)
    return counts


def check_small_graphs():
    rng=np.random.default_rng(20261023)
    for trial in range(100):
        n=2+trial%15
        a=np.triu(rng.random((n,n))<.2,1);a=a|a.T
        p=rng.permutation(n);a=a[p][:,p]
        neighbors=[set(np.flatnonzero(a[i]).tolist()) for i in range(n)]
        expected=np.ones(n,np.int64)
        for k in range(n):
            higher={i for i in neighbors[k] if i>k};expected[k]+=len(higher)
            for i in higher:neighbors[i].update(higher-{i})
        assert np.array_equal(column_counts(csc_matrix(a)),expected)


def main(args):
    start=time.monotonic();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,)*2)
    state={'schema':'razr-symbolic-ND-fill-progress-v1','body':args.body,'completed':False,'numeric_factorization_executed':False}
    last=-100.
    def progress(phase,*values):
        nonlocal last
        if unreclaimable()>int(6.8*1024**3):raise MemoryError('shared cgroup guard')
        if time.monotonic()-start>180:raise TimeoutError('symbolic 180-second bound')
        if time.monotonic()-last>=10:
            state.update(phase=phase,position=list(values),seconds=time.monotonic()-start,
                         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            save_json(out/'progress.json',state);print(json.dumps(state),flush=True);last=time.monotonic()
    try:
        progress('initial_guard');check_small_graphs()
        order=json.loads(args.ordering_report.read_text())
        assert order['completed'] and order['new_permutation_identity']
        folder=args.volume.resolve()/args.body/'level-2';path=folder/'K.npz'
        assert sha(path)==order['input_sha256'][str(path)]
        permutation_path=args.ordering_report.parent/'permutation.npz'
        assert sha(permutation_path)==order['permutation_sha256']
        with np.load(permutation_path,allow_pickle=False) as z:p=z['scalar_order']
        indices=stored_array(path,'indices');pointer=stored_array(path,'indptr')
        count=len(p);assert len(pointer)==3*count+1
        lengths=np.diff(pointer)[::3]//3;ptr=np.r_[0,np.cumsum(lengths)]
        idx=np.empty(int(ptr[-1]),np.int32)
        for node in range(count):
            column=indices[pointer[3*node]:pointer[3*node+1]]
            assert len(column)==3*lengths[node]
            assert np.array_equal(column,indices[pointer[3*node+1]:pointer[3*node+2]])
            assert np.array_equal(column,indices[pointer[3*node+2]:pointer[3*node+3]])
            block=column.reshape(-1,3)
            assert np.all(block[:,0]%3==0) and np.all(block[:,1]==block[:,0]+1) and np.all(block[:,2]==block[:,0]+2)
            idx[ptr[node]:ptr[node+1]]=block[:,0]//3
            if node%16384==0:progress('verify_actual_K_blocks',node,count)
        graph=csr_matrix((np.ones(len(idx),bool),idx,ptr),shape=(count,count))
        assert (graph!=graph.T).nnz==0
        indices._mmap.close();pointer._mmap.close();del indices,pointer,idx,ptr
        load_path=folder/'loads.npz'
        assert sha(load_path)==order['input_sha256'][str(load_path)]
        with np.load(load_path,allow_pickle=False) as z:fixed=z['D']
        fixed_nodes,fixed_counts=np.unique(fixed//3,return_counts=True)
        all_fixed=fixed_nodes[fixed_counts==3]
        partial_count=int(np.count_nonzero(fixed_counts!=3))
        kept=np.ones(count,dtype=bool);kept[all_fixed]=False
        p=p[kept[p]];original_count=count;count=len(p)
        graph=graph[p][:,p].tocsc();graph.sort_indices();gc.collect()
        counts=column_counts(graph,progress)
        scalar_nnz=int(counts.sum());lower_vector=9*(scalar_nnz-count)+6*count
        lu_bound=2*lower_vector-3*count
        np.save(out/'scalar-L-column-counts.npy',counts)
        result={'schema':'razr-exact-symbolic-ND-fill-fixed-v1','completed':True,'body':args.body,
                'numeric_factorization_executed':False,'original_K_sha256':sha(path),
                'ordering_report_sha256':sha(args.ordering_report),'permutation_sha256':sha(permutation_path),
                'scalar_nodes':count,'original_scalar_nodes':original_count,'removed_fully_fixed_nodes':len(all_fixed),'remaining_partial_fixed_nodes':partial_count,'exact_free_block_pattern_if_zero_partial_nodes':partial_count==0,'symbolic_scalar_L_nnz_including_diagonal':scalar_nnz,
                'block_L_nnz_after_removing_fully_fixed_nodes':lower_vector,
                'symmetric_L_plus_U_nnz_after_removing_fully_fixed_nodes':lu_bound,
                'float64_plus_int32_LU_array_bytes_upper_bound':12*lu_bound+8*(3*count+1),
                'not_a_SuperLU_peak_RSS_prediction':True,'pivoting_and_allocation_overhead_not_measured':True,
                'small_graph_explicit_elimination_checks':100,
                'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'source_sha256':{str(Path(__file__).resolve()):sha(Path(__file__)),'loads_sha256':sha(load_path)},
                'counts_sha256':sha(out/'scalar-L-column-counts.npy'),
                'no_constraints_energy_precision_or_acceptance_changed':True}
        save_json(out/'report.json',result);print(json.dumps(result),flush=True)
    except BaseException as error:
        state.update(phase='interrupted_or_failed',error_type=type(error).__name__,error=str(error),seconds=time.monotonic()-start)
        save_json(out/'progress.json',state);raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--body',choices=['panel','frame'],required=True)
    p.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    p.add_argument('--ordering-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
