#!/usr/bin/env python3
"""Capture observed Lenovo model pages and extract visible page evidence.

Full third-party HTML remains private analysis input. Public claims are selected
separately and cannot qualify a specimen, a selected component revision or a
physical test. No forms, messages, device commands or login are submitted.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import json
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
PAGES = [
    ("product_1047", "https://m.lenovocare.com.cn/ProductDetail.aspx?id=1047"),
    ("downloads_1047", "https://m.lenovocare.com.cn/ProductDownloadList.aspx?productid=1047"),
    ("quick_guide_1762", "https://m.lenovocare.com.cn/DownloadDetail.aspx?id=1762"),
    ("user_guides_1766", "https://m.lenovocare.com.cn/DownloadDetail.aspx?id=1766"),
    ("usb_baseline_82351", "https://m.lenovocare.com.cn/ProductFaq.aspx?articleid=82351"),
]
MAX_BYTES = 512 * 1024


class VisiblePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.excluded_depth = 0
        self.text = []
        self.links = []
        self.active_link = None
        self.headings = []
        self.active_heading = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.excluded_depth += 1
        if self.excluded_depth:
            return
        attrs = dict(attrs)
        if tag == "a":
            self.active_link = {"href": attrs.get("href"), "text": []}
        if tag in {"h1", "h2", "h3", "h4"}:
            self.active_heading = {"tag": tag, "text": []}

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.excluded_depth = max(0, self.excluded_depth - 1)
            return
        if self.excluded_depth:
            return
        if tag == "a" and self.active_link:
            self.active_link["text"] = " ".join(self.active_link["text"])
            self.links.append(self.active_link)
            self.active_link = None
        if tag in {"h1", "h2", "h3", "h4"} and self.active_heading:
            self.active_heading["text"] = " ".join(self.active_heading["text"])
            self.headings.append(self.active_heading)
            self.active_heading = None

    def handle_data(self, data):
        if self.excluded_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.text.append(text)
        if self.active_link is not None:
            self.active_link["text"].append(text)
        if self.active_heading is not None:
            self.active_heading["text"].append(text)


def capture(page):
    name, url = page
    start = time.monotonic()
    row = {"id": name, "requested_url": url,
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "max_bytes": MAX_BYTES, "read_only_request": True,
           "credentials_or_cookies_provided": False, "complete_html_captured": False}
    private_dir = ROOT / "private-inputs" / "official-html"
    private_dir.mkdir(parents=True, exist_ok=True)
    data = b""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RAZR-evidence-reader/1.0", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=15) as response:
            row.update(http_status=response.status, effective_url=response.geturl(),
                       content_type=response.headers.get("Content-Type"))
            encoding = response.headers.get_content_charset() or "utf-8"
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("HTML input exceeds declared byte budget")
            row["complete_html_captured"] = True
            text = data.decode(encoding, errors="strict")
            parser = VisiblePage()
            parser.feed(text)
            visible = {"id": name, "effective_url": row["effective_url"],
                       "headings": parser.headings, "visible_text_segments": parser.text,
                       "links": [{"href": urljoin(row["effective_url"], r["href"]), "text": r["text"]}
                                 for r in parser.links if r["href"]]}
            extracted = (json.dumps(visible, ensure_ascii=False, indent=2) + "\n").encode()
            extracted_path = private_dir / (name + ".visible.json")
            extracted_path.write_bytes(extracted)
            row.update(visible_extraction_identity={"bytes": len(extracted), "sha256": hashlib.sha256(extracted).hexdigest()},
                       headings=parser.headings,
                       exact_model_token_present="XT2551-3" in " ".join(parser.text),
                       outcome="COMPLETE_HTML_AND_VISIBLE_PARSE")
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code, effective_url=exc.geturl(), error_type=type(exc).__name__, error=str(exc), outcome="HTTP_READ_FAILED")
    except Exception as exc:
        row.update(error_type=type(exc).__name__, error=str(exc), outcome="READ_OR_PARSE_FAILED")
    row.update(seconds=time.monotonic() - start, received_bytes=len(data), received_sha256=hashlib.sha256(data).hexdigest())
    if data:
        (private_dir / (name + ".html")).write_bytes(data)
    row["full_third_party_html_in_public_delivery"] = False
    return row


def main():
    source = Path(__file__).read_bytes()
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(capture, PAGES))
    record = {"schema": "razr-r4-actual-official-model-page-capture-v1",
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "source_identity": {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()},
              "records": rows,
              "specimen_or_electrical_qualification_granted": False,
              "physical_measurements_executed": 0,
              "forms_or_messages_submitted": 0}
    (ROOT / "R4_OFFICIAL_MODEL_PAGE_ACTUAL_CAPTURE.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
