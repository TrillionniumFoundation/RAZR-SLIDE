#!/usr/bin/env python3
"""Actual STEP-edge high precision length probe; no geometry modification."""
from pathlib import Path
import hashlib,json,platform,sys,traceback
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_AbscissaPoint
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def point(p):return [p.X(),p.Y(),p.Z()]
def run():
    records=json.loads((ROOT/'corner_bay_followup_receipt.json').read_text())['rows'];rows=[]
    for r in records:
        path=ROOT/r['path_only_STEP']['path'];before=sha(path);raw=cq.importers.importStep(str(path)).vals();edges=[]
        def visit(s):
            if not s.isValid():raise ValueError('invalid complete path payload')
            if s.ShapeType()=='Edge':edges.append(s)
            elif s.ShapeType() in ['Compound','Wire']:
                for child in s:visit(child)
            else:raise ValueError('unexpected raw path topology '+s.ShapeType())
        for root in raw:visit(root)
        if len(edges)!=9:raise ValueError('actual STEP curve-edge count differs')
        per=[]
        for i,e in enumerate(edges):
            adaptor=BRepAdaptor_Curve(e.wrapped);a,b=adaptor.FirstParameter(),adaptor.LastParameter()
            d={'index':i,'OCC_curve_type':str(adaptor.GetType()),'first_parameter':a,'last_parameter':b,'start_xyz_mm':point(adaptor.Value(a)),
              'mid_parameter_xyz_mm':point(adaptor.Value((a+b)/2)),'end_xyz_mm':point(adaptor.Value(b)),'default_CadQuery_Length_mm':e.Length()}
            try:d['actual_GCPnts_1e_minus10_length_mm']=GCPnts_AbscissaPoint.Length_s(adaptor,a,b,1e-10)
            except Exception as exc:d['actual_exception']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            per.append(d)
        high=None if any('actual_exception' in p for p in per) else sum(p['actual_GCPnts_1e_minus10_length_mm'] for p in per)
        rows.append({'pose':r['pose'],'path':str(path.relative_to(ROOT)),'sha256_before':before,'sha256_after':sha(path),'actual_edge_count':len(per),'edges':per,
          'default_reimport_length_mm':sum(p['default_CadQuery_Length_mm'] for p in per),'high_precision_actual_reimport_length_mm':high,
          'source_native_default_length_mm':r['actual_path_length_mm'],'analytic_target_mm':r['fixed_material_length_mm'],
          'high_precision_minus_analytic_mm':None if high is None else high-r['fixed_material_length_mm'],
          'high_precision_unchanged_1um_threshold_passed':False if high is None else abs(high-r['fixed_material_length_mm'])<=1e-6,
          'original_default_1um_failure_retained':r['pose']=='STOW','candidate_route_accepted':False})
        if before!=sha(path):raise ValueError('actual STEP bytes changed')
    result={'host':platform.node(),'CadQuery':cq.__version__,'builder_imported':False,'method':'GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(edge),first,last,1e-10)',
      'actual_integral_requested_tolerance_mm':1e-10,'material_length_acceptance_threshold_not_relaxed_mm':1e-6,'rows':rows,
      'requested_numerical_tolerance_is_certified_error_bound':False,'original_failed_default_length_check_retained':True,
      'original_invalid_common_and_volume_differences_retained':True,'manufacturing_go':False}
    (ROOT/'path_length_precision_probe.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps([{'pose':r['pose'],'high_precision_length_mm':r['high_precision_actual_reimport_length_mm'],'difference_mm':r['high_precision_minus_analytic_mm']} for r in rows]))
if __name__=='__main__':run()
