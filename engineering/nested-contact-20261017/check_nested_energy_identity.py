"""Independent small algebra check of the nested recovered-field metric.

No phone fields are created. Full SPD block matrices and explicit recovered
interiors are compared against the condensed identity used by the report.
"""
from pathlib import Path
import json,hashlib
import numpy as np
O=Path('/tmp/razr-level2-contact-20261017/nested-energy-metric-check.json');assert not O.exists()
rng=np.random.default_rng(172903);rows=[]
for i in range(32):
    n=6+(i%4);n1=3+(i%3);n2=4+(i%5);N=n+n1+n2
    a=rng.normal(size=(N+3,N));A=a.T@a+np.eye(N)
    A1=A[:n+n1,:n+n1]
    K1=A1[:n,:n]-A1[:n,n:]@np.linalg.solve(A1[n:,n:],A1[n:,:n])
    K2=A[:n,:n]-A[:n,n:]@np.linalg.solve(A[n:,n:],A[n:,:n])
    x=rng.normal(size=n);y=rng.normal(size=n)
    coarse=np.r_[x,-np.linalg.solve(A1[n:,n:],A1[n:,:n]@x),np.zeros(n2)]
    fine=np.r_[y,-np.linalg.solve(A[n:,n:],A[n:,:n]@y)]
    direct=float((fine-coarse)@A@(fine-coarse))
    recovered_metric=float(y@K2@y+x@K1@x-2*x@K2@y)
    residual=float(np.max(abs((A@fine)[n:])))
    rel=abs(direct-recovered_metric)/max(abs(direct),1e-30)
    assert rel<1e-12 and residual<1e-11
    # Incorrectly using fine condensed energy for the embedded old field
    # silently re-equilibrates old interiors instead of measuring that field.
    wrong=float(y@K2@y+x@K2@x-2*x@K2@y)
    assert direct-wrong>1e-6
    rows.append({'case':i,'direct_full_difference_energy':direct,'condensed_nested_metric':recovered_metric,'relative_difference':rel,'fine_internal_residual':residual,'wrong_old_self_energy_underestimation':direct-wrong})
O.write_text(json.dumps({'cases':rows,'passed':True,'number_of_algebraic_checks':32,'not_device_loads_or_mesh_convergence':True,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
print('NESTED_METRIC_IDENTITY32',max(r['relative_difference'] for r in rows),flush=True)
