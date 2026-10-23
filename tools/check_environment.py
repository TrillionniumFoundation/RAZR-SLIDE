#!/usr/bin/env python3
"""Fail-closed version check for this project's universal uv lock.

This verifies the interpreter, project/lock agreement and every locked registry
package's installed version. Artifact provenance still comes from ``uv sync
--locked`` and its installation log; matching metadata alone does not prove it.
Conditional/multiple-version locks need an explicit implementation update and
are rejected rather than silently checking only a convenient subset.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement(text: str) -> tuple[str, str]:
    match = re.fullmatch(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)\s*([^;\[\]@]*)", text)
    if not match:
        raise ValueError("unsupported conditional, URL or extra project requirement")
    name, specifier = match.groups()
    return normalized_name(name), re.sub(r"\s+", "", specifier)


def python_matches(specification: str, observed: tuple[int, int, int]) -> bool:
    """Interpret the comparison forms used by the project and universal lock."""
    for clause in specification.split(","):
        match = re.fullmatch(r"\s*(==|!=|>=|<=|>|<)\s*(\d+(?:\.\d+){0,2})(\.\*)?\s*", clause)
        if not match:
            raise ValueError("unsupported Python version constraint")
        operator, raw, wildcard = match.groups()
        parts = tuple(int(part) for part in raw.split("."))
        if wildcard:
            if operator not in ("==", "!="):
                raise ValueError("invalid wildcard Python version constraint")
            equal = observed[:len(parts)] == parts
            ok = equal if operator == "==" else not equal
        else:
            wanted = parts + (0,) * (3-len(parts))
            ok = {"==": observed == wanted, "!=": observed != wanted,
                  ">=": observed >= wanted, "<=": observed <= wanted,
                  ">": observed > wanted, "<": observed < wanted}[operator]
        if not ok:
            return False
    return True


def version_matches(version: str, specification: str) -> bool:
    """Check the exact pins and numeric release ranges used by this project.

    This is deliberately not a general PEP 440 implementation. An unfamiliar
    version/constraint combination fails closed instead of guessing an order.
    """
    if not specification:
        return True
    for clause in specification.split(','):
        match = re.fullmatch(r'(==|!=|>=|<=|>|<)([^\s,]+)', clause)
        if not match:
            raise ValueError('unsupported direct dependency version constraint')
        operator, wanted = match.groups()
        supported = r'\d+(?:\.\d+)*(?:\.post\d+)?'
        if not re.fullmatch(supported, version) or not re.fullmatch(supported, wanted):
            raise ValueError('unsupported dependency version syntax')
        if operator in ('==', '!=') and version == wanted:
            ok = operator == '=='
        elif re.fullmatch(r'\d+(?:\.\d+)*', version) and re.fullmatch(r'\d+(?:\.\d+)*', wanted):
            actual_parts, wanted_parts = tuple(map(int, version.split('.'))), tuple(map(int, wanted.split('.')))
            length = max(len(actual_parts), len(wanted_parts))
            actual_parts += (0,) * (length - len(actual_parts))
            wanted_parts += (0,) * (length - len(wanted_parts))
            ok = {'==': actual_parts == wanted_parts, '!=': actual_parts != wanted_parts,
                  '>=': actual_parts >= wanted_parts, '<=': actual_parts <= wanted_parts,
                  '>': actual_parts > wanted_parts, '<': actual_parts < wanted_parts}[operator]
        elif operator == '==' and '*' not in wanted:
            ok = False
        else:
            raise ValueError('unsupported ordered or wildcard dependency version constraint')
        if not ok:
            return False
    return True


def inspect_environment(root: Path = ROOT, *, installed: dict[str, str] | None = None,
                        python_version: tuple[int, int, int] | None = None) -> dict:
    root = Path(root)
    observed_python = tuple(python_version or sys.version_info[:3])
    result = {"schema": "razr-locked-version-check-v1", "passed": False,
              "python_version": ".".join(map(str, observed_python)),
              "checked_packages": {}, "errors": [],
              "scope": "interpreter and all registry package versions in the current universal lock",
              "installation_artifact_provenance_verified": False}
    try:
        project_path, lock_path = root / "pyproject.toml", root / "uv.lock"
        result.update(pyproject_sha256=digest(project_path), uv_lock_sha256=digest(lock_path))
        project = tomllib.loads(project_path.read_text())["project"]
        lock = tomllib.loads(lock_path.read_text())
        if lock.get("version") != 1 or lock.get("resolution-markers"):
            raise ValueError("unsupported conditional or non-v1 lock")
        for spec in (project["requires-python"], lock["requires-python"]):
            if not python_matches(spec, observed_python):
                result["errors"].append("Python version does not satisfy " + spec)
        packages = lock["package"]
        if not isinstance(packages, list) or not packages:
            raise ValueError("empty lock package inventory")
        by_name = {}
        for package in packages:
            name = normalized_name(package["name"])
            if name in by_name or package.get("resolution-markers"):
                raise ValueError("ambiguous or conditional locked package: " + name)
            for edge in package.get("dependencies", []):
                if any(key in edge for key in ("marker", "extras", "extra", "version", "source")):
                    raise ValueError("unsupported conditional or qualified dependency edge: " + name)
            by_name[name] = package
        own_name = normalized_name(project["name"])
        own = by_name.get(own_name)
        if not own or own.get("source") != {"virtual": "."}:
            raise ValueError("missing virtual root package in lock")
        if own.get("version") != project["version"]:
            raise ValueError("project version differs from lock root")
        wanted = [requirement(item) for item in project.get("dependencies", [])]
        locked = []
        for item in own.get("metadata", {}).get("requires-dist", []):
            if set(item) - {"name", "specifier"}:
                raise ValueError("unsupported root requirement metadata")
            locked.append((normalized_name(item["name"]), re.sub(r"\s+", "", item.get("specifier", ""))))
        if not wanted or len(set(wanted)) != len(wanted) or sorted(wanted) != sorted(locked):
            raise ValueError("project dependencies differ from lock root; regenerate uv.lock")
        if sorted(name for name, _ in wanted) != sorted(normalized_name(edge["name"]) for edge in own.get("dependencies", [])):
            raise ValueError("lock root dependency graph disagrees with declared requirements")
        for name, specification in wanted:
            if name not in by_name or not version_matches(by_name[name]["version"], specification):
                raise ValueError("resolved locked version violates project dependency: " + name + specification)
        reachable, pending = set(), [own_name]
        while pending:
            name = pending.pop()
            if name in reachable:
                continue
            if name not in by_name:
                raise ValueError("lock graph refers to an absent package: " + name)
            reachable.add(name)
            pending.extend(normalized_name(edge["name"]) for edge in by_name[name].get("dependencies", []))
        if reachable != set(by_name):
            raise ValueError("unreachable package entries require explicit lock scope handling")
        observed = {normalized_name(k): v for k, v in installed.items()} if installed is not None else None
        for name in sorted(reachable - {own_name}):
            package = by_name[name]
            if set(package.get("source", {})) != {"registry"} or not package["source"]["registry"]:
                raise ValueError("non-registry locked dependency: " + name)
            expected = package["version"]
            if not isinstance(expected, str) or not expected:
                raise ValueError("missing locked package version: " + name)
            if observed is None:
                try:
                    actual = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    actual = None
            else:
                actual = observed.get(name)
            match = actual == expected
            result["checked_packages"][name] = {"expected": expected, "observed": actual, "matches": match}
            if not match:
                result["errors"].append(name + ": expected " + expected + ", observed " + str(actual))
        result["checked_package_count"] = len(result["checked_packages"])
        result["passed"] = bool(result["checked_packages"]) and not result["errors"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result["errors"].append(type(exc).__name__ + ": " + str(exc))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect_environment(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
