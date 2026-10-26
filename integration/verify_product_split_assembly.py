"""Independently read delivered common split-assembly STEP without builders."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, b, False, False)
    xmin, ymin, zmin, xmax, ymax, zmax = b.Get()
    return [xmin, xmax, ymin, ymax, zmin, zmax]


def verify(directory, output):
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise ValueError('new readback output required')
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 'razr-common-split-assembly-v1':
        raise ValueError('wrong split-assembly manifest')
    if set(manifest.get('poses', {})) != {'STOW', 'PREDOCK', 'OPEN'}:
        raise ValueError('all three declared states are required')
    rows = []
    for label, pose in manifest['poses'].items():
        expected = pose.get('parts')
        if not isinstance(expected, dict) or not expected:
            raise ValueError('each state must declare its complete participant set')
        count = len(expected)
        if pose.get('total_participants') != count or pose.get('combined', {}).get('expected_solids') != count:
            raise ValueError('participant counts disagree within the manifest')
        for name, part in expected.items():
            bb, volume = part.get('bounds_mm'), part.get('volume_mm3')
            if (not isinstance(name, str) or not name or not isinstance(bb, list) or len(bb) != 6
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in bb)
                    or type(volume) not in (int, float) or not math.isfinite(volume) or volume <= 0
                    or any(bb[i] >= bb[i+1] for i in (0, 2, 4))):
                raise ValueError('invalid declared geometry signature')
        rel = Path(pose['combined']['file'])
        if rel.name != str(rel):
            raise ValueError('STEP must be a direct regular-file member')
        path = directory/rel
        if path.is_symlink() or sha(path) != pose['combined']['sha256']:
            raise ValueError('STEP identity changed')
        imported = cq.importers.importStep(str(path))
        roots = imported.vals()
        solids = [solid for root in roots for solid in root.Solids()]
        if len(solids) != len(expected) or len(solids) != pose['combined']['expected_solids']:
            raise ValueError('participant count mismatch')
        unmatched = dict(expected)
        matches = []
        for solid in solids:
            if not solid.isValid() or not math.isfinite(solid.Volume()) or solid.Volume() <= 0:
                raise ValueError('invalid or nonpositive STEP solid')
            bb, volume = bounds(solid), solid.Volume()
            candidates = [name for name, part in unmatched.items()
                          if abs(volume-part['volume_mm3']) <= max(1e-7, part['volume_mm3']*1e-8)
                          and max(abs(a-b) for a,b in zip(bb, part['bounds_mm'])) <= 1e-6]
            if not candidates:
                raise ValueError('STEP contains a solid absent from the declared geometry signatures')
            name = sorted(candidates)[0]
            unmatched.pop(name)
            matches.append(name)
        if unmatched:
            raise ValueError('declared participant was not reread')
        rows.append({'pose': label, 'file': rel.name, 'sha256': sha(path),
                     'valid_positive_solids': len(solids), 'matched_participants': sorted(matches),
                     'all_declared_volume_and_bounds_signatures_match': True})
    result = {'schema': 'razr-common-split-step-readback-v1',
              'reader_sha256': sha(__file__), 'manifest_sha256': sha(manifest_path),
              'builder_modules_imported': False, 'independent_CAD_kernel': False,
              'runtime_cadquery': cq.__version__, 'poses': rows,
              'scope': 'independent STEP parse, solid validity, count, volume and exact-shape bounds; no material/load qualification',
              'passed': True, 'manufacturing_go': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    r = verify(args.directory, args.output)
    print(json.dumps({'passed': r['passed'], 'solid_counts': {p['pose']:p['valid_positive_solids'] for p in r['poses']}}))
