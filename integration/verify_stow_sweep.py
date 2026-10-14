"""Independent complete STEP import and reverse-direction envelope comparison.

Does not import stow_web_repair or any historical scene builder. Uses the same
CadQuery/OCC kernel, so this is an independent reader, not a second CAD engine
or a tolerance/strength/physical certificate.
"""
from pathlib import Path
import argparse,hashlib,json,math,platform,time
import cadquery as cq

TOL=1e-7

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def material(shape, allow_empty=False):
    leaves=[]
    def walk(s):
        if not s.isValid():raise ValueError('invalid full topology')
        kind=s.ShapeType()
        if kind=='Solid':
            v=float(s.Volume())
            if not math.isfinite(v) or v<=0:raise ValueError('nonpositive signed solid')
            leaves.append(s)
        elif kind in ('Compound','CompSolid'):
            children=list(s)
            if not children and not allow_empty:raise ValueError('empty input node')
            for child in children:walk(child)
        else:raise ValueError('free non-solid topology '+kind)
    walk(shape)
    if not leaves and not allow_empty:raise ValueError('no material')
    v=float(shape.Volume())
    if not math.isfinite(v) or v<0 or abs(v-sum(s.Volume() for s in leaves))>TOL:
        raise ValueError('whole material volume mismatch')
    return leaves,v


def single(shape):
    leaves,v=material(shape)
    if len(leaves)!=1:raise ValueError('input is not one complete positive solid')
    return shape


def signed_common(a,b):
    single(a);single(b)
    result=a.intersect(b)
    if not result.isValid():raise ValueError('invalid native common')
    volume=float(result.Volume())
    if not math.isfinite(volume) or volume<0 or volume>min(a.Volume(),b.Volume())+TOL:
        raise ValueError('inconsistent signed common')
    return volume


def reverse_envelope(original,vector):
    end=original.translate(vector)
    back=cq.Vector(tuple(-v for v in vector))
    pieces=[end]
    faces=end.Faces()
    if any(f.geomType()!='PLANE' for f in faces):raise ValueError('non-planar source')
    used=[]
    for index,face in enumerate(faces):
        if face.normalAt().dot(back)>1e-12:
            prism=cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),back)
            single(prism);pieces.append(prism);used.append(index)
    if not used:raise ValueError('no reverse boundary prisms')
    shape=pieces[0]
    for part in pieces[1:]:shape=shape.fuse(part)
    return single(shape.clean()),used


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--receipt',required=True,type=Path);ap.add_argument('--expected-sha256',required=True)
    ap.add_argument('--output',required=True,type=Path);args=ap.parse_args()
    if sha(args.receipt)!=args.expected_sha256:raise ValueError('producer receipt identity changed')
    root=args.receipt.resolve().parent;report=json.loads(args.receipt.read_text());inputs={str(args.receipt):sha(args.receipt)};rows=[]
    start=time.monotonic()
    for row in report['rows']:
        shapes={}
        for role,entry in row['exports'].items():
            path=root/entry['path']
            if path.parent!=root or sha(path)!=entry['sha256']:raise ValueError('STEP path/hash mismatch')
            raw=cq.importers.importStep(str(path)).vals()
            if len(raw)!=1:raise ValueError('unaccounted input roots')
            shape=single(raw[0]);cert=entry['certificate'];bb=shape.BoundingBox()
            if abs(shape.Volume()-cert['signed_volume_mm3'])>TOL or any(abs(getattr(bb,k)-v)>1e-7 for k,v in cert['bounds_mm'].items()):raise ValueError('STEP geometry differs from producer certificate')
            shapes[role]=shape;inputs[str(path)]=sha(path)
        original=shapes['original_pawl'];forward=shapes['forward_sweep'];vector=row['sweep_method']['translation_mm']
        reverse,used=reverse_envelope(original,vector)
        forward_minus_reverse=material(forward.cut(reverse),allow_empty=True)[1]
        reverse_minus_forward=material(reverse.cut(forward),allow_empty=True)[1]
        if max(forward_minus_reverse,reverse_minus_forward)>TOL:raise ValueError('forward and reverse full envelopes differ')
        old_common=signed_common(shapes['original_root'],reverse)
        new_common=signed_common(shapes['candidate_root'],reverse)
        expected=row['original_root_positive_common']['checked_volume_mm3']
        if old_common<=TOL or abs(old_common-expected)>TOL or new_common!=0.:
            raise ValueError('original negative or repaired-clearance result changed')
        expected_vector=[-1.1 if row['side']=='L' else 1.1,0.,0.]
        if vector!=expected_vector or row['insertion_method']['translation_mm']!=[0.,0.,10.]:raise ValueError('declared motion changed')
        endpoint=original.translate(vector)
        if material(endpoint.cut(shapes['parked_pawl']),allow_empty=True)[1]>TOL or material(shapes['parked_pawl'].cut(endpoint),allow_empty=True)[1]>TOL:raise ValueError('parked source is not the same pawl at the endpoint')
        reverse_insert,insert_faces=reverse_envelope(shapes['parked_pawl'],[0.,0.,10.])
        insertion=shapes['insertion_sweep']
        ins_fwd_diff=material(insertion.cut(reverse_insert),allow_empty=True)[1]
        ins_rev_diff=material(reverse_insert.cut(insertion),allow_empty=True)[1]
        if max(ins_fwd_diff,ins_rev_diff)>TOL:raise ValueError('reverse insertion envelope differs')
        old_insert=signed_common(shapes['original_root'],reverse_insert)
        new_insert=signed_common(shapes['candidate_root'],reverse_insert)
        if old_insert<=TOL or abs(old_insert-row['original_insertion_common']['checked_volume_mm3'])>TOL or new_insert!=0.:raise ValueError('insertion rejection/repair not reproduced')
        removed=shapes['original_root'].cut(shapes['candidate_root']);remvol=material(removed,allow_empty=True)[1]
        outside=material(removed.cut(reverse).cut(reverse_insert),allow_empty=True)[1]
        if outside>TOL:raise ValueError('source material removed outside the two declared motion collisions')
        rows.append({'side':side,'single_positive_STEP_inputs':len(shapes),'reverse_boundary_faces_used':used,
                     'forward_minus_reverse_mm3':forward_minus_reverse,'reverse_minus_forward_mm3':reverse_minus_forward,
                     'old_root_reverse_sweep_common_mm3':old_common,'new_root_reverse_sweep_common_mm3':new_common,
                     'insertion_forward_minus_reverse_mm3':ins_fwd_diff,'insertion_reverse_minus_forward_mm3':ins_rev_diff,
                     'old_root_insertion_common_mm3':old_insert,'new_root_insertion_common_mm3':new_insert,
                     'removed_material_mm3':remvol,'removed_outside_motion_envelopes_mm3':outside})
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('input bytes changed during reimport')
    result={'host':platform.node(),'CadQuery':cq.__version__,'source_sha256':sha(__file__),
            'producer_receipt_sha256':args.expected_sha256,'inputs_SHA256':inputs,'inputs_unchanged':True,
            'rows':rows,'builder_imported':False,'reverse_sweep_built_from_reimported_endpoint_geometry':True,
            'same_CAD_kernel_not_cross_engine':True,'full_phone_or_strength_qualified':False,
            'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'sides':len(rows),'positive_solid_STEPs':sum(r['single_positive_STEP_inputs'] for r in rows),'reverse_envelope_agreement':True,'manufacturing_go':False}))


if __name__=='__main__':main()
