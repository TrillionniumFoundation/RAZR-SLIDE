"""I/O and serial native operations for R12 current-K1/K3 motion evidence.

This file deliberately contains no motion-envelope builder.  BREP producer and
STEP/reverse reader construct their own region sets.  All comparisons retain
the original S4 1e-7 mm3 predicate; measured native Common is not a formal
directed-rounding upper bound.
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import math
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.TopTools import TopTools_ListOfShape

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'inputs'
spec = importlib.util.spec_from_file_location('current_key_original_material_gate', INPUT / 'straight_envelope.py')
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def verify_inputs():
    m = json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    for name, row in m['files'].items():
        p = INPUT/name
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], name
    return m

def clone(shape):
    op = BRepBuilderAPI_Copy(shape.wrapped, True, False)
    assert op.IsDone()
    return cq.Shape.cast(op.Shape())

def fingerprint(shape):
    data = io.BytesIO()
    assert shape.exportBrep(data)
    raw = data.getvalue()
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped,b,False,False)
    x0,y0,z0,x1,y1,z1=b.Get()
    return [x0,x1,y0,y1,z0,z1]

def signature(shape,empty=False):
    solids, volume = strict.whole_material(shape,empty=empty)
    return {'valid_original_topology_and_signed_volume_gate':True,
            'positive_solids':len(solids),'signed_volume_mm3':volume,
            'bounds_mm':bounds(shape) if solids else None,
            'faces':len(shape.Faces()),'edges':len(shape.Edges())}

def serial(a,b,kind):
    left=TopTools_ListOfShape();right=TopTools_ListOfShape()
    left.Append(clone(a).wrapped);right.Append(clone(b).wrapped)
    op={'common':BRepAlgoAPI_Common,'cut':BRepAlgoAPI_Cut,'fuse':BRepAlgoAPI_Fuse}[kind]()
    op.SetArguments(left);op.SetTools(right);op.SetRunParallel(False)
    op.SetNonDestructive(True);op.Build();assert op.IsDone()
    return cq.Shape.cast(op.Shape())

def save_raw(shape,path,step=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists()
    if step:
        cq.exporters.export(clone(shape),str(path))
    else:
        assert clone(shape).exportBrep(str(path))
    return {'path':str(path.relative_to(HERE)),'bytes':path.stat().st_size,'sha256':sha(path)}

def save(shape,path,empty=False):
    raw=save_raw(shape,path)
    return {'file':raw,**signature(shape,empty=empty)}

def load_body(name,role):
    if role=='producer':
        body=cq.Shape.importBrep(str(INPUT/(name+'.brep')))
    else:
        roots=cq.importers.importStep(str(INPUT/(name+'.step'))).vals()
        body=roots[0] if len(roots)==1 else cq.Compound.makeCompound(roots)
    strict.single(body)
    report=json.loads((INPUT/'report.json').read_text())
    expected=report['body_exports'][name]['signature']
    sig=signature(body)
    assert abs(sig['signed_volume_mm3']-expected['signed_volume_mm3'])<=strict.TOL
    assert all(abs(a-b)<=strict.TOL for a,b in zip(sig['bounds_mm'],expected['bounds_mm']))
    return body,{'source_format':'brep' if role=='producer' else 'step',
                 'signature':sig,'fingerprint_before':fingerprint(body)}

def complete_pair(region,panel,path):
    a,b=signature(region),signature(panel)
    aa,bb=a['bounds_mm'],b['bounds_mm']
    gaps=[max(aa[2*i]-bb[2*i+1],bb[2*i]-aa[2*i+1]) for i in range(3)]
    if max(gaps)>0:
        return {'method':'positive_axis_gap','axis_gaps_mm':gaps,
                'measured_common_mm3':0.0,'original_gate_clear':True}
    common=serial(region,panel,'common')
    raw=save_raw(common,path)
    sig=signature(common,empty=True)
    v=sig['signed_volume_mm3']
    assert 0<=v<=min(a['signed_volume_mm3'],b['signed_volume_mm3'])+strict.TOL
    return {'method':'native_serial_Common','axis_gaps_mm':gaps,
            'measured_common_mm3':v,'original_gate_clear':v<=strict.TOL,
            'common_result':{'file':raw,**sig}}

def exact_sum_nonnegative(values):
    from fractions import Fraction
    assert values and all(math.isfinite(v) and v>=0 for v in values)
    exact=sum(map(Fraction,values),Fraction(0))
    rounded=float(exact)
    if Fraction(rounded)<exact:
        rounded=math.nextafter(rounded,math.inf)
    return {'binary64_results_exact_rational_sum':str(exact),
            'sum_rounded_up_mm3':rounded,
            'measured_sum_passes_original_1e_7_gate':exact<=Fraction(strict.TOL),
            'rounding_of_sum_is_outward':True,
            'individual_native_Common_error_bounds_available':False,
            'formal_intersection_volume_upper_bound':False}
