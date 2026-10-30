"""Read-only AST audit of the source guide rectangles; no CAD replay/inference."""
from pathlib import Path
from fractions import Fraction as F
import ast,hashlib,json,datetime

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'inputs/cam_coupling.py'
def ident(p):
    p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def evaluate(node,y=None):
    if isinstance(node,ast.Constant) and type(node.value) in (int,float):return F(node.value)
    if isinstance(node,(ast.Tuple,ast.List)):return [evaluate(x,y) for x in node.elts]
    if isinstance(node,ast.Name) and node.id=='y':assert y is not None;return y
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):return evaluate(node.left,y)+evaluate(node.right,y)
    raise ValueError('unexpected source expression '+ast.dump(node))

def main():
    text=SOURCE.read_text();tree=ast.parse(text)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='housing_study')
    loops=[n for n in ast.walk(fn) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='y']
    assert len(loops)==1;loop=loops[0];ys=evaluate(loop.iter);assert ys==[F(56),F(62)]
    assignment=next(n for n in loop.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pieces' for t in n.targets))
    assert isinstance(assignment.value,ast.List) and len(assignment.value.elts)==4
    records=[]
    for y in ys:
        boxes=[]
        for call in assignment.value.elts:
            assert isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='box' and len(call.args)==2 and not call.keywords
            lo,hi=[evaluate(v,y) for v in call.args];assert all(a<b for a,b in zip(lo,hi));boxes.append((lo,hi))
        floor,left,right,top=boxes
        hole=((left[1][0],right[0][0]),(floor[1][2],top[0][2]))
        assert hole==((F(10.75),F(11.45)),(F(1.15),F(1.65)))
        for sign in (-1,1):
            actual=[]
            for lo,hi in boxes:
                X=sorted((sign*lo[0],sign*hi[0]));actual.append([X,[lo[1],hi[1]],[lo[2],hi[2]]])
            hx=tuple(sorted((sign*hole[0][0],sign*hole[0][1])));hz=hole[1]
            # Entire open cross-section, all Y in the source two-unit guide:
            # each source component is outside it in X or Z, with exact equality
            # at the boundary allowed only for the open ideal source aperture.
            witnesses=[]
            for index,box in enumerate(actual):
                gaps=[(max(hx[0]-box[0][1],box[0][0]-hx[1]),0),(max(hz[0]-box[2][1],box[2][0]-hz[1]),2)]
                gap,axis=max(gaps);assert gap>=0
                witnesses.append({'component':index,'separating_axis':axis,'exact_gap_to_open_source_aperture':str(gap)})
            records.append({'side':'L' if sign<0 else 'R','guide_Y_exact':[str(y),str(y+2)],
                'complete_source_component_boxes_exact':[[list(map(str,p)) for p in box] for box in actual],
                'ideal_open_source_aperture_XZ_exact':[list(map(str,hx)),list(map(str,hz))],
                'all_four_components_excluded_from_open_aperture':witnesses})
    result={'schema':'razr-r13-guide-source-context-exact-AST-audit-v1','completed':True,'source':ident(SOURCE),'audit_source':ident(__file__),
            'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'function':'housing_study','source_statement_lines':[assignment.lineno,assignment.end_lineno],
            'literal_four_component_guide_construction':records,'CAD_modules_imported':False,
            'whole_factory_rebuilt':False,'later_fusions_proved_not_to_fill_aperture':False,
            'current_native_aperture_or_trim_identity_proved_by_source_context':False,
            'used_as_substitute_for_all_298_face_channel_certificate':False,
            'scope':'Exact literal source component context only; current whole-body channel deduction uses every original boundary face under B0 AND T.'}
    path=ROOT/'SOURCE_GUIDE_CONTEXT.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'completed':True,'source_guides':len(records),'component_boxes':sum(len(r['complete_source_component_boxes_exact']) for r in records)}))

if __name__=='__main__':main()
