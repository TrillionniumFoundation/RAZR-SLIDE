"""Verify direct worker imports without unittest discovery's module cache."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT/'engineering/engineering-integration-20261025/geometry'
PROBE = '''
import importlib
import json
from pathlib import Path
import sys
folder = Path(sys.argv[1]).resolve()
phase = sys.argv[2]
sys.path.insert(0, str(folder))
worker = importlib.import_module('verify_'+phase+'_native')
supervisor = importlib.import_module('supervise_'+phase+'_native')
identity = worker.source_identity() if phase == 'slide' else worker.adapter_identity()
print(json.dumps({'identity_count': len(identity),
    'worker_owned_helper': str(Path(worker.owned_process.__file__).resolve()),
    'supervisor_owned_helper': str(Path(supervisor.owned_process.__file__).resolve()),
    'CAD_imported': any(name == 'cadquery' or name.startswith('OCP') for name in sys.modules)}))
'''


class GeometryPortableEntrypointTests(unittest.TestCase):
    def check_fresh_entrypoint(self, phase, expected_source_count):
        folder = GEOMETRY/phase
        run = subprocess.run([sys.executable, '-B', '-c', PROBE, str(folder), phase],
                             cwd=ROOT, text=True, capture_output=True, timeout=30,
                             env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                                  'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                                  'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'})
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        result = json.loads(run.stdout)
        expected = str((folder/'owned_process.py').resolve())
        self.assertEqual(result['worker_owned_helper'], expected)
        self.assertEqual(result['supervisor_owned_helper'], expected)
        self.assertEqual(result['identity_count'], expected_source_count)
        self.assertFalse(result['CAD_imported'])

    def test_slide_direct_entrypoint_owns_its_helper_in_fresh_process(self):
        self.check_fresh_entrypoint('slide', 17)

    def test_seating_direct_entrypoint_owns_its_helper_in_fresh_process(self):
        self.check_fresh_entrypoint('seating', 13)


if __name__ == '__main__':
    unittest.main()
