"""Fresh-process reader import regression; source guard only, no CAD or raw promotion.

Discovered by the canonical repository suite under tests/. Every subprocess
loads the actual repository SLIDE entrypoint and checks its original source guard.
No saved native report is requalified and no CAD operation is performed.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'engineering/engineering-integration-20261025/geometry/slide'
CHILD = r'''
import importlib,json,sys
from pathlib import Path
here=Path(sys.argv[1]).resolve()
entry,mode=sys.argv[2:]
if mode=='foreign-preloaded':
    sys.path.insert(0,str(here.parent/'seating'))
    import owned_process
sys.path.insert(0,str(here))
reader=importlib.import_module(entry)
worker=reader.worker
result={'entry':entry,'mode':mode,
        'actual_owned_process':str(Path(worker.owned_process.__file__).resolve()),
        'expected_owned_process':str(here/'owned_process.py')}
try:
    sources=worker.source_identity()
except ValueError as exc:
    result.update(source_identity_passed=False,error_type=type(exc).__name__,error=str(exc))
else:
    result.update(source_identity_passed=True,source_count=len(sources),source_sha256=sources)
result['CAD_imported']=any(n=='cadquery' or n=='OCP' or n.startswith('OCP.') for n in sys.modules)
print(json.dumps(result,sort_keys=True))
raise SystemExit(0 if result['source_identity_passed'] and not result['CAD_imported'] else 12)
'''

class SlideReaderFreshProcessTests(unittest.TestCase):
    def inspect(self, entry, foreign=False):
        mode='foreign-preloaded' if foreign else 'standalone'
        run=subprocess.run([sys.executable,'-I','-B','-c',CHILD,str(HERE),entry,mode],
                           text=True,capture_output=True,timeout=30,check=False)
        self.assertNotEqual(run.stdout.strip(),'',run.stderr)
        value=json.loads(run.stdout)
        self.assertFalse(value['CAD_imported'])
        return run,value

    def standalone(self, entry):
        run,value=self.inspect(entry)
        self.assertEqual(run.returncode,0,run.stderr+'\n'+run.stdout)
        self.assertTrue(value['source_identity_passed'])
        self.assertEqual(value['actual_owned_process'],value['expected_owned_process'])
        self.assertEqual(value['source_count'],17)

    def reject_foreign(self, entry):
        run,value=self.inspect(entry,foreign=True)
        self.assertEqual(run.returncode,12,run.stderr+'\n'+run.stdout)
        self.assertFalse(value['source_identity_passed'])
        self.assertEqual(value['error_type'],'ValueError')
        self.assertIn('executed scratch entrypoint/module differs',value['error'])
        self.assertEqual(Path(value['actual_owned_process']),HERE.parent/'seating/owned_process.py')

    def test_report_entry_standalone_uses_own_module(self):
        self.standalone('check_slide_report')

    def test_checkpoint_entry_standalone_uses_own_module(self):
        self.standalone('check_slide_checkpoint')

    def test_report_entry_rejects_foreign_preloaded_module(self):
        self.reject_foreign('check_slide_report')

    def test_checkpoint_entry_rejects_foreign_preloaded_module(self):
        self.reject_foreign('check_slide_checkpoint')

if __name__=='__main__':
    unittest.main(verbosity=2)
