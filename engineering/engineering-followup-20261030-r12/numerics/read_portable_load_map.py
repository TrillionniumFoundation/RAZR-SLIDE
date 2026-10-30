"""Independent Fraction and rounding-cell verifier; imports no producer code."""
import argparse
from fractions import Fraction as Q
import hashlib
import itertools
import json
import math
from pathlib import Path
import resource
import struct
import sys
import time

import numpy as np


def ident(p):
    p=Path(p)
    with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(name=p.name,bytes=p.stat().st_size,sha256=digest)


def need(value,message):
    if not value:raise ValueError(message)


def bits(x):return struct.pack('>d',float(x))


def validate_terms_and_map(terms_path,map_path,reference):
    with np.load(terms_path,allow_pickle=False) as z:indices,left,right,offsets=[z[k] for k in ['indices','left','right','offsets']]
    mapped=np.load(map_path,allow_pickle=False)
    need(mapped.shape==(6,4) and mapped.dtype==np.float64 and np.isfinite(mapped).all(),'portable map shape/dtype/finite differs')
    need(indices.dtype==np.int64 and left.dtype==right.dtype==np.float64 and offsets.dtype==np.int64,'term precision differs')
    need(indices.ndim==left.ndim==right.ndim==1 and indices.shape==left.shape==right.shape,'term shapes differ')
    need(offsets.shape==(25,) and offsets[0]==0 and offsets[-1]==len(left) and np.all(np.diff(offsets)>=0),'term offsets differ')
    need(np.isfinite(left).all() and np.isfinite(right).all(),'nonfinite term')
    exact=[];rounding=[]
    for index,row in enumerate(reference):
        need((row['row'],row['column'])==divmod(index,4),'reference row ordering differs')
        a,b=int(offsets[index]),int(offsets[index+1]);ii=indices[a:b]
        need(len(ii)==row['nonzero_product_count'] and np.all((ii>=0)&(ii<344103)) and np.all(np.diff(ii)>0),'term original row index differs')
        need(np.all(left[a:b]!=0) and np.all(right[a:b]!=0),'zero term included')
        value=sum((Q(float(x))*Q(float(y)) for x,y in zip(left[a:b],right[a:b])),Q())
        expected=Q(int(row['exact_sum']['numerator']),int(row['exact_sum']['denominator']))
        need(value==expected,'exact rational reference mismatch')
        observed=float(mapped[row['row'],row['column']]);rounded=float(value)
        need(bits(observed)==bits(rounded),'once-rounded map mismatch')
        lower=(Q(observed)+Q(math.nextafter(observed,-math.inf)))/2
        upper=(Q(observed)+Q(math.nextafter(observed,math.inf)))/2
        need(lower<=value<=upper,'outside nearest rounding cell')
        if value in (lower,upper):need((int.from_bytes(bits(observed),'big')&1)==0,'midpoint does not round to even')
        error=Q(observed)-value;ulp=Q(math.ulp(observed))
        rounding.append(dict(row=row['row'],column=row['column'],error_numerator=str(error.numerator),error_denominator=str(error.denominator),error_ulps=float(error/ulp),nearest_cell_verified=True))
        exact.append(value)
    return mapped,exact,rounding,(indices,left,right,offsets)


def outward_float(q):
    f=float(q)
    return math.nextafter(f,math.inf) if Q(f)<q else f


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--r9-reference',type=Path,required=True);p.add_argument('--original-loads',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));started=time.monotonic()
    producer=json.loads((a.run/'PORTABLE_LOAD_MAP.json').read_text());reference=json.loads(a.r9_reference.read_text())
    need(ident(a.r9_reference)['sha256']=='43b2d386e53d80df038e66c798bb2a54220a6ca07ed6259c254f2f30d7782149','immutable R9 reference differs')
    for name,record in producer['files'].items():need(ident(a.run/name)==record,'producer file identity differs')
    mapped,exact,rounding,terms=validate_terms_and_map(a.run/'original_nonzero_terms.npz',a.run/'portable_loadG.npy',reference['loadG_exact_reference'])
    for row,value in zip(producer['rows'],exact):
        need(Q(int(row['integer']))*Q(2)**int(row['exponent'])==value,'producer dyadic certificate differs')
    bound_to_original=False
    if a.original_loads is not None:
        need(ident(a.original_loads)==producer['original_loads'],'original load file differs')
        with np.load(a.original_loads,allow_pickle=False) as z:R,F=z['R'],z['F']
        indices,left,right,offsets=terms
        for index,row in enumerate(reference['loadG_exact_reference']):
            lo,hi=int(offsets[index]),int(offsets[index+1]);j,k=row['row'],row['column']
            source_indices=np.flatnonzero((R[:,j]!=0)&(F[:,k]!=0))
            need(np.array_equal(indices[lo:hi],source_indices),'source term support differs')
            need(left[lo:hi].tobytes()==R[source_indices,j].tobytes() and right[lo:hi].tobytes()==F[source_indices,k].tobytes(),'source term bytes differ')
        bound_to_original=True
    comparisons={};bounds={}
    for name in ['historical-loadG.npy','current-loadG.npy','nearest-exact-loadG.npy']:
        old=np.load(a.run/name,allow_pickle=False);errors=[Q(float(x))-q for x,q in zip(old.flat,exact)]
        comparisons[name]=dict(unequal_from_portable=int(np.count_nonzero(old!=mapped)),max_abs_difference=float(np.max(np.abs(old-mapped))),
            maximum_absolute_error_ulps=max(abs(float(e/Q(math.ulp(float(q))))) for e,q in zip(errors,exact)))
        rows=[]
        for j in range(6):
            delta=[Q(float(mapped[j,k]))-Q(float(old[j,k])) for k in range(4)]
            row_bound=sum(map(abs,delta),Q())
            corners=[sum((c*d for c,d in zip(signs,delta)),Q()) for signs in itertools.product((-1,1),repeat=4)]
            need(max(map(abs,corners))==row_bound,'16-corner exact box bound differs')
            rows.append(dict(row=j,numerator=str(row_bound.numerator),denominator=str(row_bound.denominator),outward_binary64_bound=outward_float(row_bound),all_16_corners_verified=True))
        bounds[name]=rows
    result=dict(schema='r12.portable_load_map_independent_readback.v1',completed=True,source=ident(__file__),producer_report=ident(a.run/'PORTABLE_LOAD_MAP.json'),
        source_integer_implementation_imported=False,independent_Fraction_reference=True,original_load_terms_reextracted_and_byte_checked=bound_to_original,
        exact_dot_entries=24,term_count=len(terms[1]),rounding_cells=rounding,comparisons=comparisons,
        per_coordinate_real_arithmetic_difference_bounds_for_weight_box_minus1_plus1=bounds,
        bound_scope='For represented matrices acting in real arithmetic on weights in [-1,1]^4; not a guarantee for downstream QP, contact active sets, physical force/torque limits, or native BLAS reduction error.',
        historical_whole_seed_bitwise_passed=False,new_full_seed_or_arbitrary_RHS_inverse_qualified=False,
        seconds=time.monotonic()-started,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,runtime=sys.version)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ['completed','exact_dot_entries','term_count','seconds','peak_RSS_KiB','comparisons']}))


if __name__=='__main__':main()
