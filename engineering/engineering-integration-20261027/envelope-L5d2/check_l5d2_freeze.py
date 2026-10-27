"""Check new L5d2 transport and failure retention only; no CAD or network."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import yaml

def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,gate):
    if not ok:raise ValueError(gate)
def block(run,marker):
    lines=run.splitlines();start=next(i for i,x in enumerate(lines) if "<<'"+marker+"'" in x)
    end=next(i for i in range(start+1,len(lines)) if lines[i]==marker)
    return '\n'.join(lines[start+1:end])+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--original-small-report',type=Path,required=True)
    ap.add_argument('--unchanged-source',type=Path,required=True)
    a=ap.parse_args();d=a.directory
    w=yaml.safe_load((d/'s4-l5d2-isolated-status-hosted.yml').read_text())
    steps=w['jobs']['diagnostic']['steps']
    install=block(steps[2]['run'],'L5D2_DIAGNOSTIC_SOURCES')
    binding=json.loads((d/'L5D2_INPUT_BINDING.json').read_text())
    original=a.original_small_report.read_bytes()
    require({'bytes':len(original),'sha256':sha(original)}==binding['source_manifest']['report.json'],
            'actual predecessor original report identity')
    result={'schema':'razr-L5d2-new-transport-export-and-null-branch-check-v1',
            'native_CAD_executed':False,'network_accessed':False,'old_tests_repeated':False,'controls':[]}
    with tempfile.TemporaryDirectory(prefix='L5d2-new-code-',dir=d) as tmp:
        t=Path(tmp);host=t/'host';case=t/'case'
        (host/'l5').mkdir(parents=True);(case/'source/l5').mkdir(parents=True)
        env={**os.environ,'HOST_ROOT':str(host),'CASE_DIR':str(case),'PYTHONDONTWRITEBYTECODE':'1'}
        run=subprocess.run([sys.executable,'-B','-c',install],env=env,capture_output=True,text=True)
        require(run.returncode==0,'actual inline diagnostic source installer')
        identity=json.loads((case/'L5D2_SOURCE_IDENTITY.json').read_text())
        for name,item in identity['sources'].items():
            expected=(d/name).read_bytes()
            for folder in (host/'l5',case/'source/l5'):
                data=(folder/name).read_bytes()
                require(data==expected and {'bytes':len(data),'sha256':sha(data)}==item,'actual installed byte identity')
        result['controls'].append({'name':'actual_inline_source_installation','passed':True,'copies_verified':10})
        sys.path[:0]=[str(d),str(a.unchanged_source)]
        spec=importlib.util.spec_from_file_location('L5d2_pure_exporter',d/'export_l5d2.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        fixtures=(('negative_and_null_failure_retained',False,False,False,0),
                  ('exact_actual_prior_failure_retained',True,False,False,0),
                  ('changed_prior_failure_report_rejected',True,True,False,2),
                  ('private_text_report_rejected',False,False,True,2),
                  ('unknown_filename_preserves_known_science',False,False,False,2))
        for label,prior,changed,private,wanted in fixtures:
            case=t/label;science=case/'l5d2/worker/science';science.mkdir(parents=True)
            record={'schema':'razr-L5d2-six-build-raw-Boolean-status-diagnosis-v1',
                    'fixture_not_native':True,'raw_mass_accessor_value':-2e-10,
                    'raw_Shape_IsNull':True,'original_material_guard_passed':False,
                    'legitimate_empty_material_proved':False,'original_null_failure_repaired':False}
            if private:record['unreviewed_locator']='/tmp/private-fixture-only'
            (science/'report.json').write_text(json.dumps(record)+'\n')
            if prior:
                data=original+b' ' if changed else original
                (science/'original-L5c-report.json').write_bytes(data)
            if label=='unknown_filename_preserves_known_science':
                (science/'unreviewed-private-name.fixture').write_bytes(b'unknown fixture')
            out=case/'publish';code=mod.execute(case,d,out)
            require(code==wanted,'exporter disposition')
            scope=json.loads((out/'EXPORT_SCOPE.json').read_text())
            require(all(set(x)=={'bytes','sha256','reason'} for x in scope['rejected_items']),
                    'unknown private basename or text exported')
            if private:require(not (out/'report.json').exists(),'private report retained')
            else:
                actual=json.loads((out/'report.json').read_text())
                require(actual['raw_mass_accessor_value']==-2e-10 and actual['raw_Shape_IsNull'] is True
                        and actual['legitimate_empty_material_proved'] is False,'failure changed or zeroed')
            if prior and not changed:
                require((out/'original-L5c-report.json').read_bytes()==original,'original predecessor report changed')
            if changed:require(not (out/'original-L5c-report.json').exists(),'changed predecessor report accepted')
            manifest=json.loads((out/'MANIFEST.json').read_text())
            require(set(p.name for p in out.iterdir())==set(manifest)|{'MANIFEST.json'},'exact retained manifest')
            result['controls'].append({'name':label,'passed':True,'exit_code':code,'fixture_not_native':True})
    tree=ast.parse((d/'run_l5d2.py').read_text())
    branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='null_ok and is_null')
    calls=[ast.unparse(n.func) for x in branch.body for n in ast.walk(x) if isinstance(n,ast.Call)]
    require(not any(x.endswith(('.cast','.Volume','.volume','.cut','.makeCompound')) or x=='keep' for x in calls),
            'null branch synthesized or accepted material')
    result['controls'].append({'name':'null_branch_has_no_cast_volume_cut_or_synthesized_empty',
                              'passed':True,'static_source_check_not_native':True})

    # Regression of the actual L5d failure: an unavailable method must be
    # recorded inside its checkpoint and cannot block the next known method.
    helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='checkpointed_native_method')
    namespace={}
    exec(compile(ast.Module(body=[helper],type_ignores=[]),'<new-checkpoint-helper>','exec'),namespace)
    sentinel=object()
    class MissingErrorsBinding:
        def IsDone(self):return True
        def Shape(self):return sentinel
    obj=MissingErrorsBinding();calls=[]
    def attempt(gate,fn):
        try:value=fn()
        except AttributeError:
            calls.append((gate,False));return False,None,{'status':'failed','failure_type':'AttributeError'}
        calls.append((gate,True));return True,value,{'status':'returned'}
    outcomes=[namespace['checkpointed_native_method'](attempt,name,obj,name)
              for name in ('IsDone','HasErrors','HasWarnings','GetReport','Shape')]
    require([v[0] for v in outcomes]==[True,False,False,False,True] and outcomes[-1][1] is sentinel,
            'missing status method blocked later Shape observation')
    require(len(calls)==5,'all status method attempts must be recorded')
    result['controls'].append({'name':'actual_missing_attribute_failure_is_checkpointed_and_later_Shape_runs',
                              'passed':True,'native_binding_fixture_not_CAD':True,'attempts':5})
    cast_branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='cast_ok')
    selected_false=[n for x in cast_branch.orelse for n in ast.walk(x)
                    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='selected'
                    and len(n.args)==2 and isinstance(n.args[1],ast.Constant) and n.args[1].value is False]
    require(selected_false,'non-null cast failure omitted from final original selected gates')
    result['controls'].append({'name':'non_null_cast_failure_is_fail_closed_in_final_original_gate',
                              'passed':True,'static_source_check_not_native':True})


    method_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
                  isinstance(n.func,ast.Name) and n.func.id=='checkpointed_native_method']
    require(not any(any(isinstance(a,ast.Constant) and a.value in ('Builder','DSFiller') for a in n.args)
                    for n in method_calls),'optional child pointer getter reintroduced')
    require('child_algorithm_observations' not in (d/'run_l5d2.py').read_text(),
            'previous child reporting block remains in isolated observer')
    result['controls'].append({'name':'optional_child_getter_calls_removed_from_this_observer',
                              'passed':True,'static_source_check_not_root_cause_proof':True})

    require(not any(k=='cadquery' or k=='OCP' or k.startswith('OCP.') for k in sys.modules),'local CAD import')
    result['all_controls_passed']=True
    result['workflow_sha256']=sha((d/'s4-l5d2-isolated-status-hosted.yml').read_bytes())
    result['script_sha256']=sha(Path(__file__).read_bytes())
    result['new_inline_input_verifier_full_geometry_fixture_executed']=False
    result['actual_52_original_input_member_verification_reference']='L5C_COMPLETE_MEMORY_READBACK.json, already actual; no local geometry expansion repeated'
    (d/'L5D2_NEW_CODE_CHECK.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'controls':len(result['controls']),'passed':True,'native_CAD_executed':False}))

if __name__=='__main__':main()
