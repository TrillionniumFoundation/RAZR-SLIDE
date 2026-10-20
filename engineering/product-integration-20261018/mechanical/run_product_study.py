"""Reproduce targeted checks and three complete native product study exports.

Use a new external output directory. STEP readback is intentionally a separate
process in verify_product_exports.py, without importing any candidate builder.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'integration'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('use a new output directory outside the source tree')
    output.mkdir(parents=True)
    import product_assembly as assembly
    import product_motion as motion
    import oled_storage as oled
    sources = ['integration/product_assembly.py', 'integration/product_motion.py',
               'integration/oled_storage.py', 'design/product_geometry.json',
               'integration/product-study-tests/test_product_geometry.py',
               str(Path(__file__).relative_to(ROOT))]
    hashes = {path: assembly.sha(ROOT / path) for path in sources}
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / 'integration/product-study-tests'), pattern='test_product_geometry.py')
    stream = io.StringIO()
    print('TARGETED_TESTS_START', flush=True)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (output / 'targeted-tests.txt').write_text(stream.getvalue())
    print(stream.getvalue(), flush=True)
    test_record = {'tests': result.testsRun, 'failures': len(result.failures),
                   'errors': len(result.errors), 'skipped': len(result.skipped),
                   'passed': result.wasSuccessful(), 'source_sha256': hashes}
    (output / 'targeted-tests.json').write_text(json.dumps(test_record, indent=2) + '\n')
    if not result.wasSuccessful():
        raise SystemExit('targeted product tests failed')
    print('PRODUCT_FULL_MOTION_START', flush=True)
    mechanical = motion.verify()
    (output / 'product-motion-report.json').write_text(json.dumps(mechanical, indent=2) + '\n')
    print('PRODUCT_FULL_MOTION_RESULT', mechanical['all_requested_geometry_checks_nonpenetrating'], flush=True)
    print('OLED_FULL_MOTION_START', flush=True)
    screen = oled.verify_motion()
    (output / 'oled-motion-report.json').write_text(json.dumps(screen, indent=2) + '\n')
    print('OLED_FULL_MOTION_RESULT', screen['all_declared_enclosures_clear'], flush=True)
    exports = {}
    for name, s, d, u, accessories in (
        ('STOW', 0., 0., 0., False),
        ('PREDOCK', 79.75, 0., 3., False),
        ('OPEN', 79.75, 8.2, 3., True),
    ):
        print('NATIVE_EXPORT_START', name, flush=True)
        record = assembly.export_product_scene(
            output / name, slide_mm=s, descent_mm=d, left_tab_mm=u,
            right_tab_mm=u, open_hold=accessories, open_support=accessories)
        exports[name] = {'participants': len(record['exports']),
                         'manifest_sha256': assembly.sha(output / name / 'manifest.json')}
        print('NATIVE_EXPORT_FINISHED', name, len(record['exports']), flush=True)
    if any(assembly.sha(ROOT / path) != expected for path, expected in hashes.items()):
        raise ValueError('study source or configuration changed during the run')
    summary = {'schema': 'razr-product-study-run-v1', 'source_sha256': hashes,
               'targeted_tests': test_record,
               'nominal_mechanical_geometry_nonpenetrating': mechanical['all_requested_geometry_checks_nonpenetrating'],
               'OLED_motion_report': 'oled-motion-report.json',
               'exports': exports, 'elapsed_seconds': time.monotonic() - started,
               'independent_STEP_readback_still_required': True,
               'physical_hardware_cycle_completed': False,
               'candidate_go': False, 'fixture_fabrication_go': False,
               'manufacturing_go': False}
    (output / 'run-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
