#!/usr/bin/env python3
"""Complete raw topology check for intentionally non-solid route-path STEPs."""
from pathlib import Path
import hashlib,json,math,platform,sys
sys.dont_write_bytecode=True
import cadquery as cq
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    data=json.loads((ROOT/'corner_bay_followup_receipt.json').read_text());rows=[]
    for r in data['rows']:
        p=ROOT/r['path_only_STEP']['path'];before=sha(p);wp=cq.importers.importStep(str(p));roots=wp.vals();edges=[];counts={}
        def visit(s):
            counts[s.ShapeType()]=counts.get(s.ShapeType(),0)+1
            if not s.isValid():raise ValueError('invalid complete path topology')
            if s.ShapeType()=='Edge':edges.append(s)
            elif s.ShapeType() in ['Compound','Wire']:
                children=list(s)
                if not children:raise ValueError('empty path wrapper')
                for c in children:visit(c)
            else:raise ValueError('unexpected extra path topology '+s.ShapeType())
        for s in roots:visit(s)
        if len(edges)!=9:raise ValueError('complete path did not preserve all nine curve edges')
        length=sum(e.Length() for e in edges)
        if abs(length-r['fixed_material_length_mm'])>1e-6:raise ValueError('path material length differs')
        # Detect two degree-one ends from real imported vertex coordinates,
        # using explicit 1um coordinate matching. No curve is rejoined/cleaned.
        nodes=[];degree=[]
        for e in edges:
            for v in e.Vertices():
                xyz=(v.X,v.Y,v.Z);idx=next((i for i,n in enumerate(nodes) if math.dist(n,xyz)<1e-6),None)
                if idx is None:idx=len(nodes);nodes.append(xyz);degree.append(0)
                degree[idx]+=1
        ends=[nodes[i] for i,d in enumerate(degree) if d==1]
        if len(ends)!=2 or any(d not in [1,2] for d in degree):raise ValueError('imported curve-edge endpoint connectivity changed')
        for expected in [r['A_moved_endpoint_xyz_mm'],r['B_unchanged_endpoint_xyz_mm']]:
            if not any(math.dist(expected,end)<1e-6 for end in ends):raise ValueError('actual path endpoint moved')
        if sha(p)!=before:raise ValueError('path STEP bytes changed')
        rows.append({'path':str(p.relative_to(ROOT)),'sha256':before,'whole_raw_hierarchy':counts,'actual_edge_count':len(edges),'actual_imported_length_mm':length,
          'actual_endpoint_xyz_mm':ends,'endpoint_coordinate_matching_tolerance_mm':1e-6,'manufacturing_solid':False})
    result={'host':platform.node(),'CadQuery':cq.__version__,'builder_imported':False,'rows':rows,'actual_path_only_STEP_count':len(rows),
      'finite_FPC_and_continuous_motion_qualified':False,'manufacturing_go':False}
    (ROOT/'independent_path_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'actual_path_only_STEP_count':len(rows),'manufacturing_go':False}))
if __name__=='__main__':run()
