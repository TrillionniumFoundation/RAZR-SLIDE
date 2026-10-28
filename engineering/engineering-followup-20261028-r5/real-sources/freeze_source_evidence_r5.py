"""Freeze R5 documentary reception, unchanged intake inputs and focused actual controls."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
WORKSPACE = str(ROOT.parent)

def ident_bytes(b):
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def identity(p):
    return ident_bytes(p.read_bytes())

def sanitize(value):
    if isinstance(value, str):
        return value.replace(WORKSPACE, '<WORKSPACE>')
    if isinstance(value, list):
        return [sanitize(x) for x in value]
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    return value

def main():
    public = ROOT / 'public'
    if list(public.iterdir()):
        raise FileExistsError('fresh public projection required')
    copies = [*ROOT.glob('*.py'), ROOT / 'README_R5_SOURCE_AND_FIELD_DELIVERY.md',
        *sorted((ROOT / 'intake').glob('*')),
        *[ROOT / 'actual' / name for name in ('R5_OFFICIAL_PDF_RECEPTION.json',
          'R5_OFFICIAL_QUICK_GUIDE_APPLICABILITY.json', 'R5_BOUNDED_RECOVERY_SUMMARY.json',
          'R5_WEB_DISCOVERY_REFERENCES.json', 'R5_ACTUAL_MODEL_LITERATURE_INVENTORY.json')],
        ROOT / 'actual' / 'receipt-controls' / 'R5_RECEIPT_BOUNDARY_CONTROLS.json']
    for directory in ('empty-reception', 'model-literature-reception'):
        copies.extend(sorted((ROOT / 'actual' / directory).glob('*.json')))
    mapping = []
    for p in copies:
        rel = p.relative_to(ROOT)
        target = public / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = p.read_bytes()
        if p.suffix == '.json':
            data = json.loads(raw)
            projected = sanitize(data)
            b = raw if projected == data else (json.dumps(projected, ensure_ascii=False, indent=2) + '\n').encode()
        else:
            b = raw.replace(WORKSPACE.encode(), b'<WORKSPACE>')
        target.write_bytes(b)
        mapping.append({'path': rel.as_posix(), 'source_identity': ident_bytes(raw),
                        'public_identity': ident_bytes(b), 'exact_original_bytes': raw == b})
    public_map = {'schema': 'razr-r5-source-public-projection-map-v1',
        'files': mapping, 'projection_only_replaces_workspace_prefix': True,
        'third_party_complete_PDF_or_text_or_images_included': False,
        'original_228_fact_values_supplied': 0, 'new_physical_passes': 0}
    (public / 'R5_PUBLIC_PROJECTION_MAP.json').write_text(json.dumps(public_map, indent=2) + '\n')
    excluded = []
    science_paths = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() and not p.is_symlink():
            continue
        rel = p.relative_to(ROOT)
        if rel.parts[0] in ('private-inputs', 'public') or '__pycache__' in rel.parts:
            continue
        if p.suffix == '.zip' or p.name in ('R5_SOURCE_SCIENCE_MANIFEST.json', 'R5_SOURCE_SCIENCE_ARCHIVE_RECEIPT.json'):
            continue
        if p.is_symlink():
            excluded.append({'path': rel.as_posix(), 'type': 'synthetic_control_symlink',
                'link_target': str(p.readlink()), 'reason': 'Recreated by preserved control source; archive contains no executable symlink.'})
            continue
        science_paths.append(p)
    manifest = {'schema': 'razr-r5-source-scientific-manifest-v1',
        'files': [{'path': p.relative_to(ROOT).as_posix(), **identity(p)} for p in science_paths],
        'excluded_symlinks': excluded,
        'third_party_full_documents_excluded_from_this_archive': True,
        'separate_received_OEM_document': {'path': 'xt2551_3_official_quick_guide.pdf',
            **identity(ROOT / 'private-inputs' / 'xt2551_3_official_quick_guide.pdf')},
        'physical_qualification_granted': False}
    manifest_path = ROOT / 'R5_SOURCE_SCIENCE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    archive = ROOT / 'RAZR-R5-official-source-reception-and-field-intake-evidence-20261028.zip'
    if archive.exists():
        raise FileExistsError(archive)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in [*science_paths, manifest_path]:
            z.write(p, p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('archive CRC failure')
        for row in manifest['files']:
            if ident_bytes(z.read(row['path'])) != {k: row[k] for k in ('bytes', 'sha256')}:
                raise ValueError('archive full-byte identity mismatch:' + row['path'])
    receipt = {'schema': 'razr-r5-source-archive-actual-v1',
        'archive_name': archive.name, **identity(archive), 'manifest_identity': identity(manifest_path),
        'manifest_members': len(science_paths), 'zip_members': len(science_paths) + 1,
        'all_members_CRC_and_manifest_bytes_verified': True,
        'public_file_count': len(mapping) + 1, 'public_projection_map_identity': identity(public / 'R5_PUBLIC_PROJECTION_MAP.json'),
        'all_public_outputs_written': True, 'physical_passes': {'G3': False, 'G4': False, 'G5': False}}
    (ROOT / 'R5_SOURCE_SCIENCE_ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
