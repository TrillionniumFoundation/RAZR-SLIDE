from pathlib import Path
import builtins, importlib.abc, json, runpy, sys, traceback
config=json.loads(Path(sys.argv[1]).read_text())
blocked=[]
forbidden={'cadquery','OCP','vtk','vtkmodules','numpy','scipy','shapely','casadi','nlopt'}
class NoNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in forbidden:
            blocked.append(fullname)
            raise RuntimeError('Pure stdlib rejection control prohibits native/numeric import: '+fullname)
sys.meta_path.insert(0,NoNative())
sys.argv=[config['script'],*config['arguments']]
result={'actual_source':config['script'],'actual_arguments':list(config['arguments']),
        'blocked_native_import_attempts':blocked,'exception':None}
code=2
try:
    runpy.run_path(config['script'],run_name='__main__')
    code=0
except SystemExit as exc:
    code=0 if exc.code is None else exc.code if isinstance(exc.code,int) else 2
    result['SystemExit_code']=code
except BaseException as exc:
    result['exception']={'type':type(exc).__name__,'message':str(exc)}
    traceback.print_exc()
finally:
    result['exit_code']=code
    result['native_numeric_modules_loaded']=sorted(n for n in sys.modules if n.split('.')[0] in forbidden)
    Path(config['audit']).write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(code)
