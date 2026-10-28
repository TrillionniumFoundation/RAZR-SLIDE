"""Receive one publicly discovered OEM PDF; a document read is not native or physical qualification."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
URL = 'https://www.lenovocare.com.cn/ideaservice/535125b81e2f46eabffa9c1568443961.pdf'
CAP = 4 * 1024 * 1024
WALL = 45.0

def main():
    started = time.monotonic()
    row = {'schema': 'razr-r5-official-public-PDF-reception-v1',
           'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
           'requested_url': URL, 'discovery_reference': 'turn40search14 / turn41view0',
           'max_received_bytes': CAP, 'wall_budget_seconds': WALL,
           'scope': 'Public documentary reception only; not an original native-resource-gated job.',
           'credentials_supplied': False, 'authentication_bypassed': False,
           'original_native_resource_gates_passed': False,
           'same_specimen_qualification': False, 'physical_measurement_count': 0,
           'complete_PDF_received': False}
    target = ROOT / 'private-inputs' / 'xt2551_3_official_quick_guide.pdf'
    record = ROOT / 'actual' / 'R5_OFFICIAL_PDF_RECEPTION.json'
    if target.exists() or record.exists():
        raise FileExistsError('fresh input and record required')
    payload = bytearray()
    try:
        with urllib.request.urlopen(URL, timeout=15) as response:
            row.update(http_status=response.status, effective_url=response.url,
                       content_type=response.headers.get('Content-Type'),
                       content_length=response.headers.get('Content-Length'))
            while True:
                if time.monotonic() - started > WALL:
                    raise TimeoutError('document reception wall budget')
                chunk = response.read(min(65536, CAP + 1 - len(payload)))
                if not chunk:
                    row['http_read_completed'] = True
                    break
                payload.extend(chunk)
                if len(payload) > CAP:
                    raise ValueError('document exceeds bounded reception size')
        raw = bytes(payload)
        row.update(received_bytes=len(raw), received_sha256=hashlib.sha256(raw).hexdigest())
        if not raw.startswith(b'%PDF-') or b'%%EOF' not in raw[-1024:]:
            raise ValueError('PDF magic or terminal marker absent')
        if row['content_length'] is not None and int(row['content_length']) != len(raw):
            raise ValueError('content length mismatch')
        target.write_bytes(raw)
        readback = target.read_bytes()
        if readback != raw:
            raise ValueError('received file readback mismatch')
        row.update(complete_PDF_received=True, local_full_byte_readback=True,
                   local_path=str(target.relative_to(ROOT)), outcome='COMPLETE_PDF_RECEIVED')
    except Exception as exc:
        row.update(error_type=type(exc).__name__, error=str(exc), outcome='READ_FAILED',
                   received_bytes=len(payload), received_sha256=hashlib.sha256(payload).hexdigest())
    row['seconds'] = time.monotonic() - started
    row['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    record.write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(row, ensure_ascii=False))

if __name__ == '__main__':
    main()
