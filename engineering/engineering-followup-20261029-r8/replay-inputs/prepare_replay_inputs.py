"""Restore exact R8 execution inputs from this Git checkout, without a network."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(data, expected):
    require(len(data) == expected['bytes'], 'input byte count differs')
    require(hashlib.sha256(data).hexdigest() == expected['sha256'], 'input SHA256 differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(Path(__file__).with_name('INPUT_MAP.json').read_text())
    require(not args.output.exists(), 'choose a new output directory')
    args.output.mkdir(parents=True)
    for record in spec['files']:
        name = Path(record['output_path'])
        require(not name.is_absolute() and '..' not in name.parts, 'unsafe output path')
        source_name = Path(record['repository_path'])
        require(not source_name.is_absolute() and '..' not in source_name.parts, 'unsafe repository path')
        data = (args.repo_root / source_name).read_bytes()
        verify(data, record['stored'])
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == record['git_blob_sha1'], 'input Git blob differs')
        require(record['encoding'] in ('identity', 'gzip'), 'unknown transport')
        decoded = gzip.decompress(data) if record['encoding'] == 'gzip' else data
        verify(decoded, record['decoded'])
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(decoded)
    receipt = {'schema': 'razr-r8-portable-input-replay-receipt-v1', 'files': len(spec['files']),
               'all_complete_inputs_verified': True, 'network_access': False,
               'decoded_bytes': sum(r['decoded']['bytes'] for r in spec['files']),
               'input_map_sha256': hashlib.sha256(Path(__file__).with_name('INPUT_MAP.json').read_bytes()).hexdigest()}
    (args.output / 'INPUT_REPLAY_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
