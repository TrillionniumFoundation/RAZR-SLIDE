#!/usr/bin/env python3
"""Bounded, unauthenticated reads of two observed public manual URLs.

Downloaded third-party material is a private analysis input, not a public
repository or user-delivery member. Authentication walls are recorded, not
circumvented. Only exact observed URLs are requested.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUTS = [
    ("ifixit_l2", "https://documents.cdn.ifixit.com/IxsugLCmhuNaPpYx.pdf"),
    ("replacebase_l2", "https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/XT2551-X_Moto_razr_60_ultra_razr_ultra_Service_and_Repair_Manual_V1.0.pdf"),
]
MAX_BYTES = 25 * 1024 * 1024
MAX_NON_PDF_BYTES = 65536
WALL_SECONDS = 45.0


def read_one(name: str, url: str) -> dict:
    start = time.monotonic()
    row = {
        "name": name, "requested_url": url,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "max_pdf_bytes": MAX_BYTES, "wall_budget_seconds": WALL_SECONDS,
        "credentials_or_cookies_provided": False,
        "explicit_access_bypass_attempted": False,
        "complete_pdf_acquired": False,
    }
    data = bytearray()
    out = ROOT / "private-inputs"
    out.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "RAZR-evidence-reader/1.0", "Accept": "application/pdf"})
        with urllib.request.urlopen(request, timeout=15) as response:
            row["http_status"] = response.status
            row["effective_url"] = response.geturl()
            row["headers"] = {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Disposition"]}
            first = response.read(8192)
            data.extend(first)
            pdf_header = bytes(data).lstrip().startswith(b"%PDF-")
            row["pdf_header_detected"] = pdf_header
            limit = MAX_BYTES if pdf_header else MAX_NON_PDF_BYTES
            eof = False
            while len(data) < limit:
                if time.monotonic() - start > WALL_SECONDS:
                    raise TimeoutError("bounded manual-read wall budget exceeded")
                chunk = response.read(min(65536, limit - len(data)))
                if not chunk:
                    eof = True
                    break
                data.extend(chunk)
            row["reached_eof"] = eof
            row["limit_reached"] = not eof
            row["complete_pdf_acquired"] = bool(pdf_header and eof)
            row["outcome"] = "COMPLETE_PDF_READ" if row["complete_pdf_acquired"] else "NON_PDF_OR_INCOMPLETE_RESPONSE"
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code, effective_url=exc.geturl(), error_type=type(exc).__name__, error=str(exc), outcome="HTTP_READ_FAILED")
    except Exception as exc:
        row.update(error_type=type(exc).__name__, error=str(exc), outcome="TRANSPORT_OR_BUDGET_FAILED")
    row["seconds"] = time.monotonic() - start
    row["received_bytes"] = len(data)
    row["received_sha256"] = hashlib.sha256(data).hexdigest()
    if data:
        filename = name + (".pdf" if row["complete_pdf_acquired"] else ".response-prefix.bin")
        path = out / filename
        path.write_bytes(data)
        row["private_input_relative_path"] = "private-inputs/" + filename
    row["third_party_full_document_in_public_delivery"] = False
    return row


def main() -> None:
    source = Path(__file__).read_bytes()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: read_one(*pair), INPUTS))
    report = {
        "schema": "razr-r4-public-manual-actual-reads-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "source_identity": {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()},
        "results": results,
        "read_only_requests": True,
        "network_authentication_bypass_attempted": False,
        "same_specimen_or_physical_qualification_inferred": False,
    }
    (ROOT / "R4_PUBLIC_MANUAL_ACTUAL_READS.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
