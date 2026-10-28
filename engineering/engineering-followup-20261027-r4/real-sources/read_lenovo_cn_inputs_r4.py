#!/usr/bin/env python3
"""Read exact-model consumer documents through observed public Lenovo links."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
REQUESTS = [
    ("xt2551_3_quick_guide", "pdf", "https://m.lenovocare.com.cn/Handler/Download.ashx?fileid=1762"),
    ("xt2551_3_combined_user_guides", "rar", "https://m.lenovocare.com.cn/Handler/Download.ashx?fileid=1766"),
]
MAX_BYTES = 20 * 1024 * 1024
WALL_SECONDS = 45.0


def acquire(request):
    name, expected_format, url = request
    start = time.monotonic()
    row = {"name": name, "requested_url": url, "expected_format": expected_format,
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "max_bytes": MAX_BYTES, "wall_budget_seconds": WALL_SECONDS,
           "credentials_or_cookies_provided": False,
           "authentication_or_access_controls_bypassed": False,
           "complete_expected_document_acquired": False}
    data = bytearray()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RAZR-evidence-reader/1.0", "Accept": "application/pdf,application/vnd.rar,application/octet-stream"})
        with urllib.request.urlopen(req, timeout=15) as response:
            row.update(http_status=response.status, effective_url=response.geturl())
            row["headers"] = {k: response.headers.get(k) for k in ["Content-Type", "Content-Length", "Content-Disposition", "ETag", "Last-Modified"]}
            data.extend(response.read(8192))
            signature = (data.startswith(b"%PDF-") if expected_format == "pdf" else data.startswith(b"Rar!\x1a\x07"))
            row["expected_magic_detected"] = signature
            limit = MAX_BYTES if signature else 65536
            eof = False
            while len(data) < limit:
                if time.monotonic() - start > WALL_SECONDS:
                    raise TimeoutError("bounded document-read wall budget exceeded")
                block = response.read(min(65536, limit - len(data)))
                if not block:
                    eof = True
                    break
                data.extend(block)
            row.update(reached_eof=eof, limit_reached=not eof,
                       complete_expected_document_acquired=bool(signature and eof))
            row["outcome"] = "COMPLETE_EXPECTED_DOCUMENT_READ" if row["complete_expected_document_acquired"] else "NONMATCHING_OR_INCOMPLETE_RESPONSE"
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code, effective_url=exc.geturl(), error_type=type(exc).__name__, error=str(exc), outcome="HTTP_READ_FAILED")
    except Exception as exc:
        row.update(error_type=type(exc).__name__, error=str(exc), outcome="TRANSPORT_OR_BUDGET_FAILED")
    row.update(seconds=time.monotonic() - start, received_bytes=len(data),
               received_sha256=hashlib.sha256(data).hexdigest())
    if data:
        suffix = "." + expected_format if row["complete_expected_document_acquired"] else ".response-prefix.bin"
        path = ROOT / "private-inputs" / (name + suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row["private_input_relative_path"] = "private-inputs/" + path.name
    row["full_third_party_document_in_public_delivery"] = False
    row["same_specimen_qualification_inferred"] = False
    return row


def main():
    source = Path(__file__).read_bytes()
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(acquire, REQUESTS))
    record = {"schema": "razr-r4-exact-model-consumer-document-actual-reads-v1",
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "source_identity": {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()},
              "results": rows, "physical_measurements_executed": 0,
              "service_manual_or_schematic_qualification_inferred": False}
    (ROOT / "R4_LENOVO_CN_DOCUMENT_ACTUAL_READS.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
