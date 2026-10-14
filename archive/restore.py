#!/usr/bin/env python3
"""Verify exact originals; restore with verified, atomic, no-clobber publication.

Restore requires POSIX directory-fd/no-follow operations. All destination path
components must be real directories (use the physical path on macOS). Existing
identical regular files are accepted without writing; different files, symlinks
and special files are refused. A failed operation may leave empty directories;
an unclean process/power failure may leave a private .restore-*.tmp file, but
never publishes an unverified or partial original. This is not a sandbox against
an administrator or another actor able to rename the opened destination tree.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Iterator

MAX_SEGMENT_BYTES = 1024 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value: object) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ValueError("Invalid SHA-256")
    return value


def _size(value: object, *, maximum: int | None = None) -> int:
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        raise ValueError("Invalid byte length")
    return value


def _relative_original(value: object) -> tuple[str, ...]:
    if not isinstance(value, str) or "\\" in value or "\0" in value:
        raise ValueError("Unsafe original path")
    # Original Library paths use one leading '/'; they are rooted below destination.
    relative = value[1:] if value.startswith("/") else value
    parts = tuple(relative.split("/"))
    if any(p in ("", ".", "..") for p in parts) or re.match(r"^[A-Za-z]:", parts[0]):
        raise ValueError("Unsafe original path")
    return parts


def _require_secure_fs() -> None:
    if (os.name != "posix" or not hasattr(os, "O_NOFOLLOW")
            or not hasattr(os, "O_DIRECTORY")
            or any(f not in os.supports_dir_fd for f in (os.open, os.mkdir, os.stat, os.link, os.unlink))):
        raise RuntimeError("Secure restore needs POSIX dir_fd and O_NOFOLLOW support")


@contextmanager
def _directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Walk from '/' with no-follow handles; never resolve through a symlink."""
    _require_secure_fs()
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Parent traversal is not allowed in a restore/store root")
    path = path if path.is_absolute() else Path.cwd() / path
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _child_directories(parent: int, parts: tuple[str, ...], *, create: bool = False) -> Iterator[int]:
    fd = os.dup(parent)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd
    finally:
        os.close(fd)


def _read_regular(parent: int, name: str, size: int) -> bytes:
    # O_NONBLOCK prevents a malicious FIFO from hanging before fstat rejects it.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size != size:
            raise ValueError("Expected an exact-length regular file: " + name)
        data = stream.read(size + 1)
    if len(data) != size:
        raise ValueError("File changed or has incorrect length: " + name)
    return data


def _same_existing(parent: int, name: str, size: int, digest: str) -> bool:
    """Stream an existing original, never open it for writing or follow links."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != size:
            return False
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        return (stat.S_ISREG(named.st_mode) and identity(before) == identity(after)
                == identity(named) and actual == digest)


def _reconstruct_to_stream(root: Path, segments: list[tuple[str, int]], expected_size: int,
                           expected_sha: str, stream=None) -> int:
    whole = hashlib.sha256()
    total = 0
    with _directory(root / "blobs") as store:
        for digest, size in segments:
            with _child_directories(store, (digest[:2],)) as bucket:
                data = _read_regular(bucket, digest, size)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("Corrupt segment: " + digest)
            whole.update(data)
            total += len(data)
            if stream is not None:
                stream.write(data)
    if total != expected_size or whole.hexdigest() != expected_sha:
        raise ValueError("Original reconstruction mismatch")
    return total


def reconstruct(root: Path, record: dict, destination: Path | None = None) -> int:
    """Preserve historical API and verified-byte return value; never overwrite."""
    relative = _relative_original(record["original_library_path"])
    size, digest = _size(record["size_bytes"]), _sha(record["sha256"])
    segments = [(_sha(h), _size(n, maximum=MAX_SEGMENT_BYTES)) for h, n in record["segments"]]
    if sum(n for _, n in segments) != size:
        raise ValueError("Segment lengths do not sum to original size")
    if destination is None:
        return _reconstruct_to_stream(Path(root), segments, size, digest)
    with _directory(Path(destination), create=True) as dest:
        with _child_directories(dest, relative[:-1], create=True) as parent:
            temporary = ".restore-" + secrets.token_hex(16) + ".tmp"
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    total = _reconstruct_to_stream(Path(root), segments, size, digest, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    # Atomic name creation; unlike rename/replace, cannot clobber.
                    os.link(temporary, relative[-1], src_dir_fd=parent,
                            dst_dir_fd=parent, follow_symlinks=False)
                    os.fsync(parent)
                except FileExistsError:
                    if not _same_existing(parent, relative[-1], size, digest):
                        raise FileExistsError("Destination differs; no overwrite: " + relative[-1])
                return total
            finally:
                os.unlink(temporary, dir_fd=parent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--restore", metavar="NAME_OR_LIBRARY_ID")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    records = json.loads((root / "manifest.json").read_text())["files"]
    if args.list:
        for record in records:
            print(record["sha256"], record["size_bytes"], record["disposition"], record["name"])
        return
    if args.restore:
        if args.destination is None:
            parser.error("--restore requires --destination")
        records = [r for r in records if args.restore in (r["name"], r["library_file_id"])]
        if len(records) != 1:
            parser.error("Select one exact original filename or Library ID")
        if records[0]["disposition"] != "allowed":
            parser.error("Original bytes excluded; inspect exclusions.json")
    else:
        records = [r for r in records if r["disposition"] == "allowed"]
    total = sum(reconstruct(root, r, args.destination if args.restore else None) for r in records)
    print(json.dumps({"verified_originals": len(records), "verified_bytes": total,
                      "manufacturing_go": False}))


if __name__ == "__main__":
    main()
