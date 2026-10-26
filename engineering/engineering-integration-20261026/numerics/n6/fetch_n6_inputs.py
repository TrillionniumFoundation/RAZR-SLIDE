"""Read-only, bounded transfer of one already reviewed scientific draft asset."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import resource
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from n6_evidence_io import (AuditGateError, CHUNK, K_BYTES, K_SHA, MANIFEST_BYTES,
                            MANIFEST_SHA, S4, ZIP_BYTES, ZIP_SHA, require)

API = "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE"
RELEASE = 423900341
ASSET = 677184053
ASSET_NAME = "N5a-scientific-40276429821.zip"
MAX_TRANSFER = 768 * 1024**2
RESERVE = 500 * 1024**2


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class ReadOnlyClient:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, suffix, binary=False):
        require(suffix in ("/releases/" + str(RELEASE), "/releases/assets/" + str(ASSET)), "read_only_API_route")
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "RAZR-N6-row-audit-read-only"}
        try:
            return self.opener.open(urllib.request.Request(API + suffix, headers=headers, method="GET"), timeout=60)
        except urllib.error.HTTPError as e:
            if not binary or e.code not in (301, 302, 303, 307, 308):
                raise
            destination = e.headers.get("Location")
            e.close()
            require(isinstance(destination, str), "binary_redirect_present")
            parsed = urllib.parse.urlsplit(destination)
            host = parsed.hostname or ""
            require(parsed.scheme == "https" and parsed.username is None and parsed.password is None
                    and (host.endswith(".githubusercontent.com") or host.endswith(".blob.core.windows.net")),
                    "binary_redirect_host")
            # The scoped credential is never sent to the transfer host.
            return self.opener.open(urllib.request.Request(destination, headers={"User-Agent": "RAZR-N6-row-audit-read-only"}), timeout=60)

    def json(self, suffix):
        with self.request(suffix) as f:
            raw = f.read(2 * CHUNK + 1)
        require(len(raw) <= 2 * CHUNK, "API_response_budget")
        return json.loads(raw)


def transfer(args):
    start = time.monotonic()
    receipt = {"schema": "razr-N6-reviewed-input-transfer-v1", "completed": False,
               "release_id": RELEASE, "asset_id": ASSET, "asset_name": ASSET_NAME,
               "transport_cap_bytes": MAX_TRANSFER, "native_sparse_solve_executed": False,
               "diagnostic_arithmetic_executed": False, "raw_API_or_credentials_exported": False,
               "input_asset_modified": False}
    args.output.mkdir(parents=True, exist_ok=False)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    def save():
        receipt["seconds"] = time.monotonic() - start
        args.receipt.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    try:
        require(os.environ.get("GITHUB_REPOSITORY") == "TrillionniumFoundation/RAZR-SLIDE", "same_repository_required")
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
        require(ZIP_BYTES <= MAX_TRANSFER, "registered_transport_size")
        fs = os.statvfs(args.output)
        require(fs.f_bavail * fs.f_frsize >= RESERVE + ZIP_BYTES + K_BYTES + 32 * CHUNK, "transfer_disk_reserve")
        client = ReadOnlyClient(os.environ["GITHUB_TOKEN"])
        release = client.json("/releases/" + str(RELEASE))
        require(release["id"] == RELEASE and release["draft"] is True
                and release["tag_name"] == "evidence/engineering-sprint-20261026"
                and release["target_commitish"] == S4, "owned_scientific_draft_identity")
        asset = client.json("/releases/assets/" + str(ASSET))
        require(asset["id"] == ASSET and asset["name"] == ASSET_NAME and asset["state"] == "uploaded"
                and asset["size"] == ZIP_BYTES and asset["digest"] == "sha256:" + ZIP_SHA,
                "frozen_scientific_asset_identity")
        require(any(a.get("id") == ASSET for a in release["assets"]), "asset_belongs_to_frozen_draft")
        h, count = hashlib.sha256(), 0
        path = args.output / "N5a-scientific.zip"
        with client.request("/releases/assets/" + str(ASSET), binary=True) as f, path.open("xb") as out:
            for block in iter(lambda: f.read(CHUNK), b""):
                count += len(block)
                require(count <= ZIP_BYTES <= MAX_TRANSFER, "stream_transport_cap")
                require(time.monotonic() - start < 180, "transport_wall_limit")
                out.write(block)
                h.update(block)
        require(count == ZIP_BYTES and h.hexdigest() == ZIP_SHA, "downloaded_asset_exact")
        receipt["original_ZIP"] = {"bytes": count, "sha256": h.hexdigest()}
        with zipfile.ZipFile(path) as z:
            raw = z.read("EXPORT_MANIFEST.json")
            require(len(raw) == MANIFEST_BYTES and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA, "downloaded_manifest_exact")
            manifest = json.loads(raw)
            require(len(manifest["exported_files"]) == 371 and len(z.namelist()) == 372
                    and len(set(z.namelist())) == 372
                    and set(z.namelist()) == set(manifest["exported_files"]) | {"EXPORT_MANIFEST.json"}, "downloaded_member_set")
            name = "volume/panel/level-2/K.npz"
            require(manifest["exported_files"][name] == {"bytes": K_BYTES, "sha256": K_SHA}, "downloaded_K_manifest")
            h, count = hashlib.sha256(), 0
            with z.open(name) as f, (args.output / "original-K.npz").open("xb") as out:
                for block in iter(lambda: f.read(CHUNK), b""):
                    count += len(block)
                    require(count <= K_BYTES, "extracted_K_cap")
                    out.write(block)
                    h.update(block)
            require(count == K_BYTES and h.hexdigest() == K_SHA, "extracted_K_exact_and_CRC")
        receipt.update(completed=True, original_K={"bytes": count, "sha256": h.hexdigest()},
                       manifest_sha256=MANIFEST_SHA, manifest_bytes=MANIFEST_BYTES,
                       original_ZIP_member_count=372, all_used_members_to_be_checked_by_row_workers=True,
                       full_archive_member_readback_previously_completed_by_run=40277185712)
        save()
        return 0
    except BaseException as e:
        receipt["failure_type"] = type(e).__name__
        if isinstance(e, AuditGateError):
            receipt["failure_gate"] = str(e)
        save()
        return 2


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    raise SystemExit(transfer(p.parse_args()))
