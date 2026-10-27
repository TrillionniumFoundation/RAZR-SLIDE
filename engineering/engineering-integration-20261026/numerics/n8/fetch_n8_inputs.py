"""Read-only original N7 scientific artifact, with complete frozen identity checks.

The prior failed N7 result is preserved. This transfer reads its last accepted
chronological state and the original K/C/RHS; it does not execute numerical work.
"""
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
from n8_contract import (GateError, CHUNK, MANIFEST_BYTES, MANIFEST_SHA, S4, ZIP_BYTES, ZIP_SHA, require)

API = "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE"
RELEASE = 423900341
ASSET = None
ASSET_NAME = None
ARTIFACT = 12633916809
ARTIFACT_NAME = "s4-panel-coordinate-N7-engineering-40285015238-1"
ORIGINAL_RUN = 40285015238
ORIGINAL_HEAD = "7de04d5570ce3fdce2e220a8e0db9eaab2d37812"
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
        require(suffix in ("/actions/artifacts/" + str(ARTIFACT), "/actions/artifacts/" + str(ARTIFACT) + "/zip"), "read_only_API_route")
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "RAZR-N8-frozen-original-input"}
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
            return self.opener.open(urllib.request.Request(destination, headers={"User-Agent": "RAZR-N8-frozen-original-input"}), timeout=60)

    def json(self, suffix):
        with self.request(suffix) as f:
            raw = f.read(2 * CHUNK + 1)
        require(len(raw) <= 2 * CHUNK, "API_response_budget")
        return json.loads(raw)


def transfer(args):
    from n8_contract import (load_frozen_contract, OUTPUT_BYTES, sha_file, write_json, GateError)
    start = time.monotonic()
    receipt = {"schema": "razr-N8-frozen-input-transfer-v1", "completed": False,
               "source_artifact_id": ARTIFACT, "source_run_id": ORIGINAL_RUN,
               "source_head_sha": ORIGINAL_HEAD, "source_durable_asset_id": ASSET,
               "source_ZIP_sha256": ZIP_SHA, "source_ZIP_bytes": ZIP_BYTES,
               "native_numeric_execution": False, "input_bytes_modified": False,
               "transport_cap_bytes": MAX_TRANSFER, "selected_members": {},
               "phase": "capacity_preflight"}
    args.download.mkdir(parents=True, exist_ok=False)
    frozen = args.case / "frozen"
    frozen.mkdir(parents=True, exist_ok=False)
    def save():
        receipt["seconds"] = time.monotonic() - start
        write_json(args.case / "N8-input-transfer.json", receipt)
    try:
        require(os.environ.get("GITHUB_REPOSITORY") == "TrillionniumFoundation/RAZR-SLIDE",
                "same_repository_required")
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
        c = load_frozen_contract()
        fs = os.statvfs(args.case)
        # CASE payload plus separate reviewed export plus original input ZIP.
        required = RESERVE + ZIP_BYTES + 2 * OUTPUT_BYTES + 64 * CHUNK
        require(fs.f_bavail * fs.f_frsize >= required, "staged_scientific_disk_capacity")
        receipt["preflight_required_free_bytes"] = required
        client = ReadOnlyClient(os.environ["GITHUB_TOKEN"])
        receipt["phase"] = "original_Actions_metadata"; save()
        a = client.json("/actions/artifacts/" + str(ARTIFACT))
        require(a["id"] == ARTIFACT and a["name"] == ARTIFACT_NAME and a["expired"] is False
                and a["size_in_bytes"] == ZIP_BYTES and a["digest"] == "sha256:" + ZIP_SHA
                and a["workflow_run"]["id"] == ORIGINAL_RUN
                and a["workflow_run"]["head_sha"] == ORIGINAL_HEAD
                and a["workflow_run"]["repository_id"] == a["workflow_run"]["head_repository_id"] == 1416401103,
                "original_run_head_artifact_identity")
        receipt["metadata_HTTP_status"] = 200
        receipt["phase"] = "original_ZIP_stream"; save()
        archive = args.download / "N7-scientific.zip"
        h, count = hashlib.sha256(), 0
        with client.request("/actions/artifacts/" + str(ARTIFACT) + "/zip", True) as f, archive.open("xb") as out:
            for block in iter(lambda: f.read(CHUNK), b""):
                count += len(block)
                require(count <= ZIP_BYTES <= MAX_TRANSFER, "transfer_byte_cap")
                require(time.monotonic() - start < 180, "transfer_wall_cap")
                out.write(block); h.update(block)
        require(count == ZIP_BYTES and h.hexdigest() == ZIP_SHA, "original_ZIP_bytes")
        receipt["phase"] = "manifest_and_selected_original_members"; save()
        with zipfile.ZipFile(archive) as z:
            raw = z.read("EXPORT_MANIFEST.json")
            require(len(raw) == MANIFEST_BYTES and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA,
                    "original_manifest_identity")
            manifest = json.loads(raw)["exported_files"]
            require(len(manifest) == 129 and len(z.namelist()) == 130 and len(set(z.namelist())) == 130
                    and set(z.namelist()) == set(manifest) | {"EXPORT_MANIFEST.json"}, "original_member_set")
            (frozen / "EXPORT_MANIFEST.json").write_bytes(raw)
            for name, identity in c["members"].items():
                require(manifest[name] == identity, "selected_member_manifest_identity")
                p = frozen / name
                require(p.resolve().is_relative_to(frozen.resolve()), "selected_member_relative")
                p.parent.mkdir(parents=True, exist_ok=True)
                temporary = p.with_name(p.name + ".writing")
                h, count = hashlib.sha256(), 0
                with z.open(name) as inp, temporary.open("xb") as out:
                    for block in iter(lambda: inp.read(CHUNK), b""):
                        count += len(block)
                        require(count <= identity["bytes"], "selected_member_size_cap")
                        require(time.monotonic() - start < 180, "transfer_wall_cap")
                        out.write(block); h.update(block)
                require({"bytes": count, "sha256": h.hexdigest()} == identity, "selected_member_hash_and_CRC")
                os.replace(temporary, p)
                receipt["selected_members"][name] = identity
                save()
        receipt.update(completed=True, phase="complete_22_original_scientific_members",
                       original_manifest_sha256=MANIFEST_SHA, original_manifest_bytes=MANIFEST_BYTES,
                       selected_original_bytes=c["all_selected_original_input_bytes"],
                       whole_source_ZIP_SHA_verified=True, all_selected_members_CRC_verified=True,
                       source_full_archive_previously_read_back_by_run=None,
                       source_full_archive_independent_byte_readback_sha256="8d23a2a4764bfa2db00bf6996560e8a579907eaa0a98e7b4d144bf8919ad33d0")
        save()
        return 0
    except BaseException as e:
        receipt["failure_type"] = type(e).__name__
        if isinstance(e, GateError): receipt["failure_gate"] = str(e)
        if isinstance(e, urllib.error.HTTPError): receipt["failure_HTTP_status"] = int(e.code)
        save()
        return 2

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--download", type=Path, required=True)
    p.add_argument("--case", type=Path, required=True)
    raise SystemExit(transfer(p.parse_args()))
