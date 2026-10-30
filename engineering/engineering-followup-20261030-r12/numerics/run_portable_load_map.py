"""Compute a new portable loadG from immutable original R/F, keeping legacy maps."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

import numpy as np
from exact_dyadic import exact_dot64

EXPECTED_LOADS='811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'
EXPECTED_R9='43b2d386e53d80df038e66c798bb2a54220a6ca07ed6259c254f2f30d7782149'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def ident(path):
    path=Path(path);return dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path))


def array_sha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--loads',type=Path,required=True);ap.add_argument('--r9',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    started=time.monotonic();args.output.mkdir(parents=True,exist_ok=False)
    if sha(args.loads)!=EXPECTED_LOADS or sha(args.r9/'R9_SEED_ROUNDING_DIAGNOSTIC.json')!=EXPECTED_R9:
        raise ValueError('immutable original loads/reference identity differs')
    reference=json.loads((args.r9/'R9_SEED_ROUNDING_DIAGNOSTIC.json').read_text())
    with np.load(args.loads,allow_pickle=False) as z:R,F=z['R'],z['F']
    if R.shape!=(344103,6) or F.shape!=(344103,4) or R.dtype!=np.float64 or F.dtype!=np.float64 or not np.isfinite(R).all() or not np.isfinite(F).all():
        raise ValueError('original finite binary64 load shape differs')
    native=R.T@F
    portable=np.zeros((6,4),dtype=np.float64)
    indices=[];left=[];right=[];offsets=[0];rows=[]
    for old in reference['loadG_exact_reference']:
        j,k=old['row'],old['column']
        selected=np.flatnonzero((R[:,j]!=0)&(F[:,k]!=0))
        a,b=R[selected,j],F[selected,k]
        result=exact_dot64(a,b)
        exact=Fraction(result.integer)*Fraction(2)**result.exponent
        expected=Fraction(int(old['exact_sum']['numerator']),int(old['exact_sum']['denominator']))
        if exact!=expected or result.nonzero_products!=old['nonzero_product_count']:
            raise ArithmeticError('integer accumulation differs from original independent exact rational reference')
        portable[j,k]=result.value
        indices.extend(selected.tolist());left.extend(a.tolist());right.extend(b.tolist());offsets.append(len(indices))
        rows.append(dict(row=j,column=k,integer=str(result.integer),exponent=result.exponent,nonzero_products=result.nonzero_products,
            rounded_hex=result.value.hex(),exact_reference_matches=True))
    np.savez(args.output/'original_nonzero_terms.npz',indices=np.asarray(indices,dtype=np.int64),left=np.asarray(left,dtype=np.float64),right=np.asarray(right,dtype=np.float64),offsets=np.asarray(offsets,dtype=np.int64))
    np.save(args.output/'portable_loadG.npy',portable,allow_pickle=False)
    np.save(args.output/'observed_native_loadG.npy',native,allow_pickle=False)
    legacy={}
    for name in ['historical-loadG.npy','current-loadG.npy','nearest-exact-loadG.npy']:
        source=args.r9/'seed-rounding-arrays'/name
        expected=reference['saved_diagnostic_arrays'][name]
        if ident(source)!=dict(name=name,**expected):raise ValueError('R9 saved array identity differs')
        (args.output/name).write_bytes(source.read_bytes())
        old=np.load(source,allow_pickle=False)
        legacy[name]=dict(portable_equal_bits=portable.tobytes()==old.tobytes(),portable_unequal_entries=int(np.count_nonzero(portable!=old)),
            portable_max_abs_difference=float(np.max(np.abs(portable-old))),native_equal_bits=native.tobytes()==old.tobytes())
    if not legacy['nearest-exact-loadG.npy']['portable_equal_bits']:raise ArithmeticError('once-rounded original exact reference differs')
    if sha(args.loads)!=EXPECTED_LOADS:raise ValueError('loads changed during execution')
    result=dict(schema='r12.portable_original_auxiliary_load_map.v1',completed=True,new_versioned_map=True,
        original_loads=ident(args.loads),original_R_array_sha256=array_sha(R),original_F_array_sha256=array_sha(F),
        source=ident(__file__),exact_dot_source=ident(Path(__file__).with_name('exact_dyadic.py')),original_R9_reference=ident(args.r9/'R9_SEED_ROUNDING_DIAGNOSTIC.json'),
        runtime=dict(python=sys.version,numpy=np.__version__),original_K_b_C_and_fields_modified=False,old_seed_modified=False,original_float64_gate_modified=False,
        portable_map_exact_products_integer_sum_once_rounding=True,legacy_full_seed_bitwise_replay_passed=False,portable_full_seed_created=False,
        original_R9_qualification_retained=True,full_inverse_or_finite_QP_qualified=False,current_geometry_FE_qualified=False,
        rows=rows,comparisons=legacy,portable_array_sha256=array_sha(portable),observed_native_array_sha256=array_sha(native),
        files={p.name:ident(p) for p in sorted(args.output.iterdir())},seconds=time.monotonic()-started,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (args.output/'PORTABLE_LOAD_MAP.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['completed','seconds','peak_RSS_KiB','comparisons']}))


if __name__=='__main__':main()
