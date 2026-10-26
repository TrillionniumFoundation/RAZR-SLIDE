"""Restore only the exact archived research frame K, with original SHA identity.

No solver is started and no external service is contacted. Supply the already-saved exact frame archive after an authorized read/download.
Metadata existence alone is not a fresh archive byte verification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import tarfile
import tempfile

DEFAULT_ARCHIVE = Path('/tmp/razr-fe-20261023/archives/frame-full-L2-rebuild-20261023.tar.xz')
DESTINATION = Path('/tmp/razr-fe-20261023/volume-rebuild/frame/level-2/K.npz')
MEMBER = 'frame/level-2/K.npz'
ARCHIVE_SHA256 = '1c41ae773f93e7259293e3e09db78099f4dce574c05cdc2c5d46b093ad36d90b'
K_SHA256 = 'e077f8d0176c041041b984b5dbb016e140219b34223d235ac739978b1dddd95d'
K_BYTES = 394530277


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', required=True)
    parser.add_argument('--archive', type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    ARCHIVE = args.archive.absolute()
    if ARCHIVE.is_symlink() or sha(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError('the complete retained archive does not match its frozen SHA256')
    if DESTINATION.exists():
        if DESTINATION.is_symlink() or DESTINATION.stat().st_size != K_BYTES or sha(DESTINATION) != K_SHA256:
            raise ValueError('an existing raw file is not the exact archived operator; no overwrite')
        print(json.dumps({'raw_materialized': True, 'already_exact': True, 'sha256': K_SHA256}))
        return
    stat = os.statvfs(DESTINATION.parent)
    if stat.f_bavail * stat.f_frsize < K_BYTES + 500 * 2**20:
        raise RuntimeError('restoration requires the raw bytes plus unchanged 500MiB available-disk reserve')
    temporary = None
    try:
        with tarfile.open(ARCHIVE, 'r|xz') as archive:
            matches = 0
            for member in archive:
                if member.name != MEMBER:
                    continue
                matches += 1
                if matches != 1 or not member.isfile() or member.size != K_BYTES:
                    raise ValueError('invalid/duplicate archived operator member')
                with tempfile.NamedTemporaryFile(dir=DESTINATION.parent,
                        prefix='K.restore-', suffix='.partial', delete=False) as output:
                    temporary = Path(output.name)
                    stream = archive.extractfile(member)
                    h = hashlib.sha256(); count = 0
                    while block := stream.read(2**20):
                        available = os.statvfs(DESTINATION.parent)
                        if available.f_bavail * available.f_frsize < 500 * 2**20 + len(block):
                            raise RuntimeError('500MiB nonprivileged disk reserve reached during restoration')
                        output.write(block); h.update(block); count += len(block)
                    output.flush(); os.fsync(output.fileno())
                if count != K_BYTES or h.hexdigest() != K_SHA256:
                    raise ValueError('restored raw bytes failed their original SHA256')
            if matches != 1:
                raise ValueError('the exact operator archive member is absent')
        if sha(ARCHIVE) != ARCHIVE_SHA256 or sha(temporary) != K_SHA256:
            raise ValueError('archive or completed extraction changed during restoration')
        # An exclusive hard link avoids overwriting a concurrently restored path.
        os.link(temporary, DESTINATION)
        temporary.unlink(); temporary = None
        print(json.dumps({'raw_materialized': True, 'already_exact': False,
                          'path': str(DESTINATION), 'bytes': K_BYTES, 'sha256': K_SHA256,
                          'no_solver_started': True, 'no_external_upload': True}))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    main()
