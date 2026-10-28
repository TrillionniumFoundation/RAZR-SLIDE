from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import resource
import time
import zipfile

ROOT = Path(__file__).resolve().parent
plan = json.loads((ROOT / 'R5_N15_READONLY_RECEPTION_PLAN.json').read_text())
start = time.monotonic()
source = ROOT / 'RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip'

def guard():
    assert time.monotonic() - start <= plan['wall_budget_seconds'], 'Archive-read wall budget exceeded'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= plan['RSS_budget_bytes'], 'Archive-read RSS budget exceeded'

digest = hashlib.sha256()
with source.open('rb') as stream:
    while chunk := stream.read(plan['stream_chunk_bytes']):
        digest.update(chunk)
        guard()
assert source.stat().st_size == plan['expected_zip_bytes']
assert digest.hexdigest() == plan['expected_zip_sha256']
rows = []
selected = []
selected_bytes = 0
with zipfile.ZipFile(source) as archive:
    assert len(archive.namelist()) == len(set(archive.namelist()))
    for member in archive.infolist():
        name = PurePosixPath(member.filename)
        assert not name.is_absolute() and '..' not in name.parts
        if member.is_dir():
            continue
        md = hashlib.sha256()
        size = 0
        with archive.open(member) as stream:
            while chunk := stream.read(plan['stream_chunk_bytes']):
                md.update(chunk)
                size += len(chunk)
                guard()
        assert size == member.file_size
        row = {'path': member.filename, 'bytes': size, 'sha256': md.hexdigest()}
        rows.append(row)
        if name.suffix == '.json' and size <= plan['select_json_maximum_member_bytes']:
            selected_bytes += size
            assert selected_bytes <= plan['maximum_selected_json_output_bytes']
            data = archive.read(member)
            json.loads(data)
            target = ROOT / 'original-records' / str(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
            selected.append(row)
report = {
    'schema': 'r5-n15-original-h-restore-full-archive-reception-v1',
    'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'zip_name': source.name, 'zip_bytes': source.stat().st_size,
    'zip_sha256': digest.hexdigest(), 'all_member_CRC_verified': True,
    'members': rows, 'selected_original_json': selected,
    'selected_original_json_bytes': selected_bytes,
    'seconds': time.monotonic() - start,
    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    'new_numeric_execution': False, 'native_import': False,
    'full_H_column_K_products_recomputed': False,
    'current_geometry_FE_qualification': False,
}
guard()
(ROOT / 'R5_N15_READONLY_RECEPTION_ACTUAL.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'members': len(rows), 'selected_json': len(selected), 'selected_json_bytes': selected_bytes,
                  'seconds': report['seconds'], 'peak_RSS_bytes': report['peak_RSS_bytes'],
                  'selected_report_paths': [r['path'] for r in selected if any(s in r['path'].lower() for s in ('report', 'summary', 'capacity', 'qualification'))]}))
