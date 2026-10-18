from pathlib import Path
import ast,json,subprocess,hashlib
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
p=R/'engineering/consistent-load-20261017/surface_archive.py'
s=p.read_text();s+='''\n\ndef checked_external_load_scale(value=None):\n    """Research load/Epanel amplitude; zero is an unloaded assembly reference.\n\n    Does not convert the normalized problem to actual Newtons or set preload.\n    Omitting this option preserves the historical 1e-5 value exactly.\n    """\n    if value is None:\n        return 1e-5\n    if type(value) not in (int, float) or not np.isfinite(value) or value < 0:\n        raise ValueError('external normalized load scale must be nonnegative and finite')\n    return float(value)\n''';ast.parse(s);p.write_text(s)
p=R/'engineering/trace-enrichment-20261017/solve_trace_probe.py';s=p.read_text()
print('IMPORT_CONTROLS',[x for x in s.splitlines() if 'import checked' in x or 'import Surface' in x])
s=s.replace('from surface_archive import checked_study_controls, frozen_faces', 'from surface_archive import checked_study_controls, frozen_faces, checked_external_load_scale') if 'from surface_archive import checked_study_controls, frozen_faces' in s else s
# Match the actual existing import without altering unrelated imports.
lines=s.splitlines()
for i,l in enumerate(lines):
 if l.startswith('from surface_archive import') and 'checked_study_controls' in l and 'checked_external_load_scale' not in l:lines[i]=l+', checked_external_load_scale'
s='\n'.join(lines)+'\n'
old="    case,target,load_index,spring_initial=checked_study_controls(getattr(a,'case',6),getattr(a,'gap_tolerance',TOL))"
assert s.count(old)==1;s=s.replace(old,old+"\n    external_scale=checked_external_load_scale(getattr(a,'external_load_scale',None))")
a="    external=np.r_[P['F'][:,load_index]*1e-5,P['Fb'][:,load_index]*1e-5,np.zeros(nF)]"
assert s.count(a)==1;s=s.replace(a,"    external=np.r_[P['F'][:,load_index]*external_scale,P['Fb'][:,load_index]*external_scale,np.zeros(nF)]")
a="        if not qp['passed']:dump(out/'failed-qp.json',qp);break"
b="""        if not qp['passed']:
            dump(out/'failed-qp.json',qp)
            dump(out/'report.json',{'passed':False,'case':case,'load_index':load_index,
                'external_load_scale_over_Epanel_mm2':external_scale,'spring_initial_over_Epanel_mm2':spring_initial,
                'status':'finite_contact_QP_failed','qp_status':qp.get('status'),'history':history,
                'gap_tolerance_mm':target,'no_final_field_qualification':True,
                'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False})
            return False"""
assert s.count(a)==1;s=s.replace(a,b)
a="'gap_tolerance_mm':target,'load_index':load_index,'spring_initial_over_Epanel_mm2':spring_initial,"
assert s.count(a)==1;s=s.replace(a,a+"\n        'external_load_scale_over_Epanel_mm2':external_scale,'unloaded_assembly_reference':external_scale==0,\n        'initial_spring_force_not_equilibrated_installed_preload':True,")
a="    p.add_argument('--rank-fallback',choices=('svd','qr','qr_pivot'),default='svd')"
assert s.count(a)==1;s=s.replace(a,a+"\n    p.add_argument('--external-load-scale',type=float,default=None)")
ast.parse(s);assert 'checked_external_load_scale' in s.split('def run')[0];p.write_text(s)
test='''from pathlib import Path
import ast, sys, unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from surface_archive import checked_external_load_scale, checked_study_controls

class LoadCaseDefinitionTests(unittest.TestCase):
    def test_omitted_scale_preserves_original_value(self):
        self.assertEqual(checked_external_load_scale(), 1e-5)
    def test_zero_is_unloaded_not_default(self):
        self.assertEqual(checked_external_load_scale(0),0.)
    def test_positive_scale_preserved(self):
        for x in [1e-6,1e-5,2e-5,1]:self.assertEqual(checked_external_load_scale(x),float(x))
    def test_negative_scale_rejected(self):
        with self.assertRaises(ValueError):checked_external_load_scale(-1e-10)
    def test_nonfinite_scale_rejected(self):
        for x in [float('nan'),float('inf'),float('-inf')]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_boolean_scale_rejected(self):
        for x in [True,False]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_string_scale_rejected(self):
        with self.assertRaises(ValueError):checked_external_load_scale('0')
    def test_nonscalar_scale_rejected(self):
        for x in [[0],{},np.array([0.])]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_case_matrix_preserves_four_positions_and_two_initial_states(self):
        for case in range(8):
            c,t,idx,initial=checked_study_controls(case,1e-7)
            self.assertEqual((c,t,idx,initial),(case,1e-7,case%4,0. if case<4 else 2e-4))
    def test_unloaded_scale_does_not_change_case_or_initial_force(self):
        self.assertEqual(checked_external_load_scale(0),0.)
        self.assertEqual(checked_study_controls(6,1e-7)[3],2e-4)
    def test_failed_QP_returns_false_before_field_use(self):
        tree=ast.parse((ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text())
        candidates=[x for x in ast.walk(tree) if isinstance(x,ast.If) and ast.unparse(x.test)=="not qp['passed']"]
        self.assertEqual(len(candidates),1)
        self.assertTrue(any(isinstance(x,ast.Return) and isinstance(x.value,ast.Constant) and x.value.value is False for x in candidates[0].body))
    def test_driver_parses_optional_explicit_load_scale(self):
        s=(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()
        self.assertIn("p.add_argument('--external-load-scale',type=float,default=None)",s)
        self.assertIn("P['F'][:,load_index]*external_scale",s)
'''
ast.parse(test);(R/'integration/manufacturing-tests/test_loadcase_definition.py').write_text(test)
p=R/'tools/test_suites.json';m=json.loads(p.read_text());assert m['minimum_total_tests']==1137;m['minimum_total_tests']+=12
for row in m['suites']:
 if row['id']=='manufacturing-fit':row['minimum_tests']+=12
p.write_text(json.dumps(m,indent=2)+'\n')
E=R/'engineering/loadcases-20261018';E.mkdir()
frozen=R/'engineering/joint-sensitivity-20261017/frozen-selection.json'
plan={'schema':'razr-loadcase-study-v1','base_main':'15d3286e0eff22eaa717993eef0c3736bb9ecc93','frozen_selection_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
 'scope':'original four lateral load positions with zero/2e-4 initial spring parameter, plus unloaded assembly reference; not actual materials or preload',
 'circle_sides':512,'gap_tolerance_mm':1e-7,'volume_level':2,'selected_faces':86,'new_trace_dofs':258,
 'rank_fallback':'qr_pivot','max_exchanges':40,'max_points':6500,
 'cases':[{'id':'case-'+str(i),'case':i,'external_load_scale_over_Epanel_mm2':1e-5,'load_index':i%4,'initial_spring_force_over_Epanel_mm2':0. if i<4 else 2e-4} for i in range(8)]+[{'id':'assembly-reference','case':6,'external_load_scale_over_Epanel_mm2':0.,'load_index':2,'initial_spring_force_over_Epanel_mm2':2e-4}],
 'same_physical_model_except_stated_load_and_initial_force':True,'no_new_real_material_support_preload_inputs':True,'failure_or_compressive_bolt_branch_not_forced_pass':True,
 'all_5255_regions_and_independent_full_field_required':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(E/'EXPERIMENT_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
cmd=[str(R/'.venv/bin/python'),'-B','-m','unittest','discover','-s',str(R/'integration/manufacturing-tests'),'-p','test_loadcase_definition.py','-v']
with (O/'new12.log').open('w') as log:r=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
(O/'new12.exit').write_text(str(r.returncode)+'\n');print('NEW_TESTS_EXIT',r.returncode);r.check_returncode()
subprocess.run(['git','add','--','engineering/consistent-load-20261017/surface_archive.py','engineering/trace-enrichment-20261017/solve_trace_probe.py','integration/manufacturing-tests/test_loadcase_definition.py','tools/test_suites.json','engineering/loadcases-20261018/EXPERIMENT_PLAN.json'],cwd=R,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=R,check=True)
subprocess.run(['git','commit','-m','feat: explicit unloaded assembly reference for original loadcase study'],cwd=R,check=True)
print('FUNCTIONAL',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),flush=True)
