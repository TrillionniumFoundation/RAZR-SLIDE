"""Explicit CLI for a new or checkpoint-resumed PR35 rigid-bearing run.

No run starts merely by importing this module. --source-preflight verifies source
availability only. Actual runs still require the original full FE inputs and the
normal PR35 dependency stack, including scikit-fem.
"""
from __future__ import annotations
import argparse
import functools
import importlib
import importlib.util
import json
from pathlib import Path
import sys

from bearing_checkpoint import FILES, HEX, SCHEMA, file_digest
from continuation_support import DEPENDENCIES, HEAD, HERE, verify_reference_sources, source_binding


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository-root', type=Path, default=HERE.parents[1])
    p.add_argument('--source-preflight', action='store_true')
    p.add_argument('--volume', type=Path)
    p.add_argument('--state', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--checkpoint-root', type=Path)
    p.add_argument('--resume-checkpoint', type=Path)
    p.add_argument('--checkpoint-sha256')
    p.add_argument('--faces-per-patch', type=int, default=2)
    p.add_argument('--max-exchanges', type=int, default=30)
    p.add_argument('--max-points', type=int, default=5500)
    p.add_argument('--surface-loads', type=Path)
    p.add_argument('--surface-load-mode', choices=('discrete', 'consistent'), default='discrete')
    p.add_argument('--load-face-cap', type=int, default=0)
    p.add_argument('--case', type=int, default=6)
    p.add_argument('--gap-tolerance', type=float, default=1e-7)
    p.add_argument('--frozen-selection', type=Path)
    p.add_argument('--rank-fallback', choices=('svd', 'qr', 'qr_pivot'), default='svd')
    p.add_argument('--external-load-scale', type=float, default=None)
    p.add_argument('--installation-control', type=Path)
    return p


def preflight(args):
    root = args.repository_root.resolve()
    sources = verify_reference_sources()
    missing = [str(root / name) for name in DEPENDENCIES if not (root / name).is_file()]
    if missing:
        raise ValueError('missing original runtime source files: ' + ', '.join(missing))
    sources.update({str(root / name): file_digest(root / name) for name in DEPENDENCIES})
    if args.source_preflight:
        return {'schema': 'razr-bearing-continuation-source-preflight-v1',
                'pr35_head': HEAD, 'file_sha256': sources,
                'full_FE_inputs_checked': False, 'checkpoint_restored': False,
                'new_QP_executed': False, 'physical_qualification': False}
    for name in ['volume', 'state', 'output', 'checkpoint_root', 'surface_loads', 'installation_control']:
        if getattr(args, name) is None:
            raise ValueError('--' + name.replace('_', '-') + ' is required for an actual run')
    if args.surface_load_mode != 'consistent' or args.external_load_scale != 0.:
        raise ValueError('original rigid comparator requires explicit consistent unloaded installation')
    if not 1 <= args.faces_per_patch <= 4 or args.max_exchanges <= 0 or args.max_points < 4000 or not 0 <= args.load_face_cap <= 4:
        raise ValueError('original driver argument limits violated')
    if args.output.exists():
        raise ValueError('output must be a new directory; old evidence is immutable')
    required = [args.installation_control,
                args.state / 'points.json', args.state / 'response.npz', args.state / 'manifest.json',
                args.surface_loads / 'manifest.json']
    required += [args.volume / body / 'level-2' / name
                 for body in ('panel', 'frame') for name in ('K.npz', 'loads.npz', 'mesh.npz', 'report.json')]
    required += [root / name for name in (
        'engineering/nested-contact-20261017/level-2/case-6/report.json.gz',
        'engineering/contact-field-20261015/common-cell-results.json.gz',
        'engineering/contact-field-20261015/coupled-field-audit.json.gz',
        'integration/assembly_inputs.json', 'integration/roof_joint_load_inputs.json',
        'integration/frame_thread_actual_inputs.json')]
    if args.frozen_selection is not None:
        required.append(args.frozen_selection)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError('missing original full-FE inputs: ' + ', '.join(missing))
    if (args.resume_checkpoint is None) != (args.checkpoint_sha256 is None):
        raise ValueError('resume generation and caller-held manifest digest must be supplied together')
    if args.resume_checkpoint is not None:
        folder = args.resume_checkpoint
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError('a retained field/NPZ is not a complete checkpoint directory')
        path = folder / 'manifest.json'
        if not isinstance(args.checkpoint_sha256, str) or not HEX.fullmatch(args.checkpoint_sha256) or not path.is_file() or file_digest(path) != args.checkpoint_sha256:
            raise ValueError('resume manifest identity missing or changed')
        data = json.loads(path.read_text())
        if data.get('schema') != SCHEMA or set(data.get('files', {})) != FILES:
            raise ValueError('incomplete/non-bearing checkpoint; do not use bearing-field-016')
        for name in FILES:
            member = folder / name
            if member.is_symlink() or not member.is_file() or file_digest(member) != data['files'][name].get('sha256'):
                raise ValueError('resume member missing or changed: ' + name)
    return None


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def execute(args):
    result = preflight(args)
    if result is not None:
        return result
    root = args.repository_root.resolve()
    # The source snapshots are verified before any of their code is executed.
    saved_path = sys.path[:]
    names = ('bearing_contact', 'rigid_bearing_probe', '_razr_pr35_trace_driver')
    prior = {name: sys.modules.get(name) for name in names}
    try:
        sys.path.insert(0, str(root / 'integration'))
        sys.path.insert(0, str(HERE))
        sys.path.insert(0, str(root / 'engineering/consistent-load-20261017'))
        _load('bearing_contact', HERE / 'reference/bearing_contact.py')
        adapter = _load('rigid_bearing_probe', HERE / 'continued_rigid_bearing_probe.py')
        adapter.run = functools.partial(adapter.run, checkpoint_root=args.checkpoint_root,
            resume_checkpoint=args.resume_checkpoint, expected_manifest_sha256=args.checkpoint_sha256)
        original = _load('_razr_pr35_trace_driver', HERE / 'reference/solve_trace_probe.py')
        original.ROOT = root
        for relative in DEPENDENCIES:
            importlib.import_module(Path(relative).stem)
        source_binding({'ROOT': root})
        args.rigid_bearing_contact = True
        # Original run() prepares the same FE/trace/load context; dispatch is the
        # single import of rigid_bearing_probe.run already present in PR35.
        return bool(original.run(args))
    finally:
        sys.path[:] = saved_path
        for name, module in prior.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        result = execute(args)
    except (ValueError, OSError) as error:
        p.exit(2, str(error) + '\n')
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    return 0 if result else 1


if __name__ == '__main__':
    raise SystemExit(main())
