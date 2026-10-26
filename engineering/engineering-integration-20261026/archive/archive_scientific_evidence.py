"""Preserve only reviewed, hash-bound engineering ZIPs in an unpublished release.

This performs byte transfers and archive integrity checks, not native CAD/FE or
qualification. It cannot publish a release, delete an asset, overwrite an asset,
change repository settings, or copy unlisted runtime collections.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import http.client
import json
import os
import re
import resource
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = "TrillionniumFoundation/RAZR-SLIDE"
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
TAG = "evidence/engineering-sprint-20261026"
MARKER = "RAZR-SLIDE-SCIENTIFIC-EVIDENCE-20261026-v1"
TITLE = "2026-10-26 engineering evidence (unpublished; no product release)"
BODY = (MARKER + "\n\nScientific originals for the S4 engineering sprint and PR #39. "
        "Only explicitly reviewed engineering exports are retained. Original arrays, "
        "STEP/BREP materials, histories and engineering projections keep their exact bytes. "
        "Raw runtime collections are excluded. Failed and unresolved results remain failed "
        "or unresolved. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false. "
        "This draft is evidence preservation, not product publication or qualification.\n")
API = "https://api.github.com/repos/" + REPO
RESERVE = 2 * 1024**3
CHUNK = 1024**2


class ArchiveInvariantError(ValueError):
    """Only fixed, source-controlled gate descriptions can enter the receipt."""
    def __init__(self, gate):
        super().__init__(gate)
        self.gate = gate


def require(value, message):
    if not value:
        raise ArchiveInvariantError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stream_hash(stream):
    h = hashlib.sha256()
    count = 0
    for block in iter(lambda: stream.read(CHUNK), b""):
        count += len(block)
        h.update(block)
    return count, h.hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class Client:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def headers(self, accept="application/vnd.github+json"):
        return {"Authorization": "Bearer " + self.token, "Accept": accept,
                "X-GitHub-Api-Version": "2026-03-10", "User-Agent": MARKER}

    def json(self, suffix, payload=None):
        require(suffix.startswith("/") and ".." not in suffix, "invalid API suffix")
        data = None if payload is None else json.dumps(payload).encode()
        headers = self.headers()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(API + suffix, data=data, headers=headers,
                                         method="GET" if payload is None else "POST")
        with self.opener.open(request, timeout=60) as response:
            raw = response.read(8 * 1024**2 + 1)
        require(len(raw) <= 8 * 1024**2, "oversize API response")
        return json.loads(raw)

    def list_all(self, suffix):
        rows = []
        for page in range(1, 11):
            current = self.json(suffix + "?per_page=100&page=" + str(page))
            require(isinstance(current, list), "invalid paged collection")
            rows.extend(current)
            if len(current) < 100:
                return rows
        raise ValueError("collection exceeds declared pagination bound")

    def binary(self, suffix):
        # An authorization header is sent only to api.github.com. Redirected
        # signed transfer URLs are followed without any authorization header.
        if re.fullmatch(r"/actions/artifacts/[0-9]+/zip", suffix):
            accept = "application/vnd.github+json"
        elif re.fullmatch(r"/releases/assets/[0-9]+", suffix):
            accept = "application/octet-stream"
        else:
            raise ArchiveInvariantError("unrecognized binary API route")
        request = urllib.request.Request(API + suffix, headers=self.headers(accept))
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise
            location = error.headers.get("Location")
            error.close()
            require(isinstance(location, str), "binary redirect lacks location")
            parsed = urllib.parse.urlsplit(location)
            host = parsed.hostname or ""
            require(parsed.scheme == "https" and parsed.username is None and parsed.password is None
                    and (host.endswith(".blob.core.windows.net")
                         or host.endswith(".githubusercontent.com")), "unexpected binary transfer host")
            return self.opener.open(urllib.request.Request(location, headers={"User-Agent": MARKER}), timeout=60)
        require(response.status == 200, "unexpected binary status")
        return response

    def upload(self, release_id, path, content_type):
        require(re.fullmatch(r"[A-Za-z0-9._-]+", path.name), "invalid asset basename")
        suffix = "/repos/" + REPO + "/releases/" + str(release_id) + "/assets?" + urllib.parse.urlencode({"name": path.name})
        connection = http.client.HTTPSConnection("uploads.github.com", timeout=60)
        headers = self.headers()
        headers.update({"Content-Type": content_type, "Content-Length": str(path.stat().st_size)})
        try:
            with path.open("rb") as body:
                connection.request("POST", suffix, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read(8 * 1024**2 + 1)
            require(response.status == 201 and len(raw) <= 8 * 1024**2, "asset upload did not return bounded success")
            return json.loads(raw)
        finally:
            connection.close()


def verify_zip(path, binding):
    with path.open("rb") as stream:
        size, digest = stream_hash(stream)
    require(size == binding["zip_bytes"] and digest == binding["zip_sha256"], "original ZIP byte identity differs")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)), "duplicate ZIP entry")
        for info in infos:
            name = PurePosixPath(info.filename)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in info.filename
                    and not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16), "invalid scientific ZIP member")
        manifest_bytes = z.read(binding["manifest_name"])
        require(sha(manifest_bytes) == binding["manifest_sha256"], "reviewed scientific manifest differs")
        manifest = json.loads(manifest_bytes)
        if binding["manifest_layout"] == "flat":
            entries = manifest
        elif binding["manifest_layout"] == "F1_members":
            require(manifest["schema"] == "razr-F1-engineering-export-manifest-v1", "F1 engineering manifest schema differs")
            entries = manifest["members"]
        else:
            entries = manifest["exported_files"]
        require(isinstance(entries, dict) and len(entries) == binding["manifest_entries"], "manifest entry count differs")
        require(set(names) == set(entries) | {binding["manifest_name"]}, "ZIP contains unlisted or missing material")
        if binding["manifest_layout"] == "exported_files":
            require(manifest["complete_original_runtime_collection_exported"] is False
                    and manifest["raw_runtime_records_durable"] is False
                    and manifest["producer_originals_modified"] is False
                    and manifest["numerical_arrays_and_mathematical_histories_are_original_bytes"] is True,
                    "numeric original-byte or runtime exclusion contract differs")
        if binding["manifest_layout"] == "F1_members":
            scope = json.loads(z.read("EXPORT_SCOPE.json"))
            require(scope["schema"] == "razr-F1-engineering-export-scope-v1"
                    and scope["functional_source_commit"] == S4
                    and scope["raw_producer_reader_reports_modified"] is False
                    and scope["all_copied_original_bytes_verified"] is True
                    and scope["raw_runtime_durable_preservation_claimed"] is False
                    and scope["raw_runtime_location"] == "ephemeral runner only",
                    "F1 original-byte or runtime exclusion contract differs")
            require(all(entries.get(name) == identity for name, identity in scope["copied_originals"].items()),
                    "F1 copied scientific identity differs")
            require(all(set(item) == {"bytes", "category", "sha256"} for item in scope["omitted_runtime_file_hashes"]),
                    "F1 omitted-runtime inventory exposes unlisted fields")
        uncompressed_bytes = 0
        for name, expected in entries.items():
            with z.open(name) as stream:
                count, member_sha = stream_hash(stream)
            require(count == expected["bytes"] and member_sha == expected["sha256"], "scientific member identity differs")
            uncompressed_bytes += count
    return {"original_ZIP_sha256": digest, "original_ZIP_bytes": size,
            "reviewed_manifest_sha256": sha(manifest_bytes), "all_scientific_members_and_CRC_verified": True,
            "verified_manifest_entries": len(entries), "verified_uncompressed_member_bytes": uncompressed_bytes}


def validate_binding(binding):
    require(set(binding) == {"label", "run_id", "head_sha", "artifact_id", "artifact_name", "zip_bytes", "zip_sha256",
                             "manifest_name", "manifest_sha256", "manifest_layout", "manifest_entries", "asset_name"},
            "binding fields differ from archive allowlist")
    require(re.fullmatch(r"[A-Za-z0-9._-]+", binding["asset_name"]) and binding["asset_name"].endswith(".zip"), "invalid scientific asset name")
    require(all(type(binding[k]) is int and binding[k] > 0 for k in ("run_id", "artifact_id", "manifest_entries")), "invalid source identifiers or count")
    require(re.fullmatch(r"[A-Za-z0-9._-]+", binding["manifest_name"]), "invalid manifest basename")
    require(binding["manifest_layout"] in ("flat", "exported_files", "F1_members"), "unsupported reviewed manifest layout")
    require(re.fullmatch(r"[0-9a-f]{40}", binding["head_sha"]), "invalid immutable source identity")
    require(all(re.fullmatch(r"[0-9a-f]{64}", binding[k]) for k in ("zip_sha256", "manifest_sha256")), "invalid SHA binding")
    require(type(binding["zip_bytes"]) is int and 0 < binding["zip_bytes"] <= 768 * 1024**2, "artifact exceeds transfer budget")


def verify_asset(client, asset, size, digest):
    require(asset["state"] == "uploaded" and asset["size"] == size
            and asset["digest"] == "sha256:" + digest, "release asset metadata differs")
    with client.binary("/releases/assets/" + str(asset["id"])) as stream:
        count, readback_digest = stream_hash(stream)
    require(count == size and readback_digest == digest, "complete release asset byte readback differs")
    return {"asset_id": asset["id"], "name": asset["name"], "bytes": size, "sha256": digest,
            "complete_uploaded_asset_bytes_read_back_and_verified": True,
            "browser_download_url": asset["browser_download_url"]}


def require_owned_draft(client, release_id):
    release = client.json("/releases/" + str(release_id))
    require(release["draft"] is True and release["tag_name"] == TAG
            and release["name"] == TITLE and release["body"] == BODY
            and release["target_commitish"] == S4, "owned unpublished draft identity changed")
    return release


def main(args):
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"schema": "razr-reviewed-scientific-draft-archive-receipt-v1", "completed": False,
              "source_manifest_sha256": sha(args.manifest.read_bytes()), "archive_script_sha256": sha(Path(__file__).read_bytes()),
              "archive_execution_commit": os.environ["GITHUB_SHA"], "archive_workflow_run_id": os.environ["GITHUB_RUN_ID"],
              "native_CAD_or_numeric_execution": False, "raw_runtime_collections_included": False,
              "published_release_created": False, "existing_assets_overwritten_or_deleted": False,
              "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
              "assets": [], "phase": "validating_inputs"}
    def checkpoint():
        result["elapsed_seconds"] = time.monotonic() - started
        (args.output / "ARCHIVE_RECEIPT.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        require(os.environ.get("GITHUB_REPOSITORY") == REPO, "fixed repository required")
        require(os.environ.get("GITHUB_REF") == "refs/heads/diagnostic/scientific-archive-20261026", "fixed archival branch required")
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        bindings = json.loads(args.manifest.read_text())["artifacts"]
        require(1 <= len(bindings) <= 20, "bounded nonempty scientific selection required")
        for binding in bindings:
            validate_binding(binding)
        require(len({b["artifact_id"] for b in bindings}) == len(bindings)
                and len({b["asset_name"] for b in bindings}) == len(bindings), "duplicate selected artifact")
        require(sum(b["zip_bytes"] for b in bindings) <= 2 * 1024**3, "batch exceeds registered 2GiB transfer payload")
        fs = os.statvfs(args.output)
        require(fs.f_bavail * fs.f_frsize >= RESERVE + sum(b["zip_bytes"] for b in bindings), "ordinary disk reserve unavailable")
        client = Client(os.environ["GITHUB_TOKEN"])
        verified = []
        for binding in bindings:
            result["phase"] = "checking_reviewed_source_" + binding["label"]
            checkpoint()
            meta = client.json("/actions/artifacts/" + str(binding["artifact_id"]))
            require(meta["expired"] is False and meta["name"] == binding["artifact_name"]
                    and meta["size_in_bytes"] == binding["zip_bytes"]
                    and meta["digest"] == "sha256:" + binding["zip_sha256"]
                    and meta["workflow_run"]["id"] == binding["run_id"]
                    and meta["workflow_run"]["head_sha"] == binding["head_sha"], "source artifact metadata differs")
            result["phase"] = "downloading_reviewed_source_" + binding["label"]
            checkpoint()
            path = args.output / binding["asset_name"]
            total = 0
            with client.binary("/actions/artifacts/" + str(binding["artifact_id"]) + "/zip") as source, path.open("xb") as target:
                for block in iter(lambda: source.read(CHUNK), b""):
                    total += len(block)
                    require(total <= binding["zip_bytes"], "source archive exceeded frozen size")
                    fs = os.statvfs(args.output)
                    require(fs.f_bavail * fs.f_frsize >= RESERVE + len(block), "ordinary disk floor reached during transfer")
                    target.write(block)
            result["phase"] = "verifying_original_members_" + binding["label"]
            checkpoint()
            verified.append((binding, path, verify_zip(path, binding)))
        result["phase"] = "all_selected_originals_verified_before_external_archive_write"
        checkpoint()
        releases = [r for r in client.list_all("/releases") if r["tag_name"] == TAG]
        require(len(releases) <= 1, "ambiguous archive release")
        if releases:
            release = releases[0]
            require(release["draft"] is True and release["name"] == TITLE and release["body"] == BODY
                    and release["target_commitish"] == S4, "existing release is not this owned draft archive")
        else:
            release = client.json("/releases", {"tag_name": TAG, "target_commitish": S4, "name": TITLE,
                "body": BODY, "draft": True, "prerelease": True, "make_latest": "false", "generate_release_notes": False})
        require(release["draft"] is True, "archive must remain unpublished")
        result["release"] = {k: release[k] for k in ("id", "html_url", "tag_name", "draft", "target_commitish")}
        assets = client.list_all("/releases/" + str(release["id"]) + "/assets")
        by_name = {a["name"]: a for a in assets}
        require(len(by_name) == len(assets), "duplicate existing release asset name")
        for binding, path, verification in verified:
            result["phase"] = "archiving_" + binding["label"]
            checkpoint()
            require_owned_draft(client, release["id"])
            asset = by_name.get(path.name)
            reused = asset is not None
            if asset is None:
                asset = client.upload(release["id"], path, "application/zip")
            require(asset["name"] == path.name, "uploaded asset basename differs")
            receipt = verify_asset(client, asset, binding["zip_bytes"], binding["zip_sha256"])
            result["assets"].append({"source_artifact": binding, "source_verification": verification,
                                     "release_asset": receipt, "existing_identical_asset_reused": reused})
            checkpoint()
        require_owned_draft(client, release["id"])
        result["completed"] = True
        result["phase"] = "complete_all_scientific_assets_and_full_byte_readbacks"
        checkpoint()
        index = args.output / ("ARCHIVE_INDEX-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"] + ".json")
        index.write_bytes((args.output / "ARCHIVE_RECEIPT.json").read_bytes())
        require_owned_draft(client, release["id"])
        meta = client.upload(release["id"], index, "application/json")
        result["archive_index_asset"] = verify_asset(client, meta, index.stat().st_size, sha(index.read_bytes()))
        require_owned_draft(client, release["id"])
        checkpoint()
        print(json.dumps({"completed": True, "draft_release_id": release["id"], "archive_count": len(result["assets"]),
                          "all_asset_bytes_retrieved_and_verified": True, "published": False}))
        return 0
    except BaseException as error:
        result["completed"] = False
        result["error_type"] = type(error).__name__
        if isinstance(error, ArchiveInvariantError):
            result["failed_source_controlled_gate"] = error.gate
        if isinstance(error, urllib.error.HTTPError):
            result["HTTP_status"] = error.code
        # No raw exception text, request headers, API bodies or signed URLs.
        checkpoint()
        print(json.dumps({"completed": False, "phase": result["phase"], "error_type": result["error_type"],
                          "HTTP_status": result.get("HTTP_status"), "archived_before_failure": len(result["assets"])}))
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
