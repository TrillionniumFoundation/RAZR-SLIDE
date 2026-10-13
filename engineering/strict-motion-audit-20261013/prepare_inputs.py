"""Restore the verified CAD source chain in an isolated cache, never in baselines."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import shutil
import stat
import zipfile


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_extract(archive, target, expected_sha, expected_members):
    """Reject symlinks, duplicate paths, traversal, bad CRC and changed cache files."""
    target = Path(target).resolve()
    payload = archive if isinstance(archive, bytes) else Path(archive).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha:
        raise ValueError("Immutable ancestor SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as package:
        if len(package.infolist()) != expected_members or package.testzip() is not None:
            raise ValueError("Ancestor count or CRC mismatch")
        names = set()
        for entry in package.infolist():
            pure = PurePosixPath(entry.filename)
            if (pure.is_absolute() or ".." in pure.parts or "\\" in entry.filename
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError("Unsafe archive member")
            destination = (target / entry.filename).resolve()
            if not destination.is_relative_to(target) or destination in names:
                raise ValueError("Unsafe or duplicate archive path")
            names.add(destination)
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            content = package.read(entry)
            if destination.exists():
                if destination.read_bytes() != content:
                    raise ValueError("Modified restored ancestor: " + entry.filename)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
    return {"sha256": expected_sha, "members": expected_members}


def prepare(baseline, cache):
    baseline, cache = Path(baseline).resolve(), Path(cache).resolve()
    if cache == baseline or cache.is_relative_to(baseline):
        raise ValueError("Cache must not be inside immutable baseline")
    cache.mkdir(parents=True, exist_ok=True)
    # The root scripts are needed as imports; historical evidence stays in baselines.
    for original in baseline.glob("*.py"):
        copied = cache / original.name
        if copied.exists() and digest(original) != digest(copied):
            raise ValueError("Modified restored R44 script")
        if not copied.exists():
            shutil.copyfile(original, copied)
    r43 = cache / "base_R43"
    ancestry = [safe_extract(
        baseline / "baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip", r43,
        "d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0", 33)]
    r42 = r43 / "parent_R42"
    ancestry.append(safe_extract(r43 / "baseline/RAZR_SLIDE_R42_FPC_full_verified_20261013.zip", r42,
        "4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513", 56))
    r41 = r42 / "parent_R41"
    ancestry.append(safe_extract(r42 / "baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip", r41,
        "f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6", 57))
    r40 = r41 / "baseline_R40"
    ancestry.append(safe_extract(r41 / "baseline/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip", r40,
        "8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec", 57))
    r39_zip = r40 / "baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip"
    if digest(r39_zip) != "6eb43c691f7ec900f63006f837667c55cbf9137ac0a49067a93e61f12e14a4fd":
        raise ValueError("R39 SHA mismatch")
    with zipfile.ZipFile(r39_zip) as package:
        if len(package.infolist()) != 37 or package.testzip() is not None:
            raise ValueError("R39 count or CRC mismatch")
        r38_zip = package.read("baseline/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip")
    ancestry.append({"sha256": digest(r39_zip), "members": 37})
    ancestry.append(safe_extract(r38_zip, r40 / "baseline_R38",
        "649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6", 1094))
    return ancestry
