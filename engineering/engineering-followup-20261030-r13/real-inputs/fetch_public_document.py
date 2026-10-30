"""Fetch one observed public OEM-distributor URL without auth or access bypass.

Full third-party response bytes are private analysis inputs, excluded from the
public source/metadata deliverable. TLS verification and inherited proxy stay on.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request


class TraceRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.redirects = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects.append({'status': code, 'url': req.full_url, 'location': newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        raise FileExistsError('New response and receipt paths required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    redirect = TraceRedirect()
    opener = urllib.request.build_opener(redirect)
    start = time.monotonic()
    report = {'schema': 'r13.public_document_download_attempt.v1',
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'requested_url': args.url, 'private_response_path': str(args.output),
              'same_specimen_applicability_established': False,
              'public_redistribution_of_response_performed': False,
              'authentication_attempted': False, 'access_control_bypass_attempted': False,
              'TLS_verification_enabled': True, 'inherited_proxy_preserved': True}
    try:
        with opener.open(args.url, timeout=45) as response:
            data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ValueError('Response exceeds 32 MiB private analysis limit')
            args.output.write_bytes(data)
            report.update(status=response.status, final_url=response.url,
                          content_type=response.headers.get('Content-Type'),
                          content_length_header=response.headers.get('Content-Length'),
                          bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          pdf_header=data.startswith(b'%PDF-'),
                          pdf_EOF_near_tail=b'%%EOF' in data[-2048:])
    except urllib.error.HTTPError as exc:
        data = exc.read(2 * 1024 * 1024)
        args.output.write_bytes(data)
        report.update(status=exc.code, final_url=exc.url,
                      content_type=exc.headers.get('Content-Type'),
                      bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                      pdf_header=data.startswith(b'%PDF-'),
                      pdf_EOF_near_tail=b'%%EOF' in data[-2048:],
                      error_type=type(exc).__name__, error=str(exc))
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc),
                      response_bytes_acquired=False)
    report['redirects'] = redirect.redirects
    report['seconds'] = time.monotonic() - start
    report['fetch_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
