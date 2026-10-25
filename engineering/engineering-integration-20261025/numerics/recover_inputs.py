"""Recover only named exact original FE mesh/load members, without extracting paths."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import tarfile

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_SHA256 = '9e9cf5e61ce6b5f15ec6194361ec3c12d74897614ad8154ba469f01ee8f69f08'
EXPECTED = {
    'panel/mesh.npz': (744696, '310152fc64af21451cc5ea4be683a73075109ed7e6ec588a6e8bcacf4979ac34'),
    'panel/loads.npz': (48176390, '811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'),
    'frame/mesh.npz': (980129, 'fc0eeecf966eda3bf242b0abd90f5603132f47d5235fcf81ea7238c1faf33132'),
    'frame/loads.npz': (51275438, 'eb2b180696785a77b71412506760df974fbf54c800090e36f027f2aaf70135a3'),
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main(args):
    archive = ROOT/'engineering/spatial-contact-integration-20261015/frozen-elastic-inputs.tar.gz'
    if sha(archive) != ARCHIVE_SHA256:
        raise ValueError('original archive digest differs')
    out = args.output.resolve()/args.body
    out.mkdir(parents=True, exist_ok=False)
    wanted = {name: value for name, value in EXPECTED.items() if name.startswith(args.body+'/')}
    rows = []
    with tarfile.open(archive, 'r:gz') as source:
        members = source.getmembers()
        for name, (size, digest) in wanted.items():
            selected = [member for member in members if member.name == name]
            if len(selected) != 1 or not selected[0].isfile() or selected[0].size != size:
                raise ValueError('missing, duplicate or invalid exact member: '+name)
            target = out/Path(name).name
            temporary = target.with_name(target.name+'.writing')
            with source.extractfile(selected[0]) as original, temporary.open('xb') as output:
                while data := original.read(1024*1024):
                    output.write(data)
            if temporary.stat().st_size != size or sha(temporary) != digest:
                raise ValueError('extracted original bytes differ: '+name)
            os.replace(temporary, target)
            rows.append({'member': name, 'path': str(target), 'bytes': size, 'sha256': digest})
    if sha(archive) != ARCHIVE_SHA256:
        raise ValueError('original archive changed during recovery')
    report = {'schema': 'razr-exact-original-fe-input-recovery-v1', 'body': args.body,
              'archive': str(archive), 'archive_sha256': ARCHIVE_SHA256,
              'archive_verified_before_and_after': True, 'files': rows,
              'source_sha256': sha(Path(__file__)), 'exact_original_mesh_and_loads_recovered': True,
              'historical_K_recovered': False, 'historical_H_recovered': False}
    (out/'recovery.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body', choices=('panel', 'frame'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
