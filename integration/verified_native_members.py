"""Explicit original-member input for EP5 when the historical tar container is absent.
Default archive consumers remain unchanged. Acceptance requires exact committed
STEP bytes for every member, never volume/bounds substitution or missing parts.
"""
from pathlib import Path
import hashlib
import json
import re

MOUNTED_MANIFEST = 'engineering/mounted-mechanism-20261015/geometry-manifest.json'
MOUNTED_MANIFEST_SHA256 = '8ded7e01f06ebcfbb47a2be307cfca3db468b6d6323473e6f2fc661836a26452'
MEMBER_COUNT = 64

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def verify_member_directory(directory, manifest_path, expected_count):
    raw_dir = Path(directory).absolute()
    require(not any(p.is_symlink() for p in (raw_dir,*raw_dir.parents)), 'symbolic directory path refused')
    directory = raw_dir.resolve(strict=True)
    manifest_path = Path(manifest_path).resolve(strict=True)
    require(directory.is_dir(), 'member directory required')
    manifest = json.loads(manifest_path.read_text())
    records = manifest.get('files')
    require(isinstance(records,list) and len(records)==expected_count, 'complete member inventory required')
    expected = {}
    for record in records:
        name = record.get('path')
        require(isinstance(name,str) and Path(name).name==name and not Path(name).is_absolute()
                and name.endswith('.step') and name not in ('.','..'), 'unsafe member name')
        require(name not in expected, 'duplicate manifest member')
        require(type(record.get('bytes')) is int and record['bytes']>0, 'invalid member size')
        require(isinstance(record.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',record['sha256']),
                'invalid member digest')
        expected[name] = record
    children = list(directory.iterdir())
    require({p.name for p in children}==set(expected), 'missing or extra directory member')
    observed = {}
    for path in sorted(children):
        require(not path.is_symlink() and path.is_file() and path.resolve().parent==directory,
                'member is not a regular in-directory file')
        data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest(); record = expected[path.name]
        require(len(data)==record['bytes'] and digest==record['sha256'], 'original member bytes differ: '+path.name)
        observed[path.name] = {'path':str(path),'bytes':len(data),'sha256':digest}
    return {'directory':str(directory),'manifest':str(manifest_path),'manifest_sha256':sha(manifest_path),
            'expected_member_count':expected_count,'actual_member_count':len(observed),'members':observed,
            'all_original_member_bytes_verified':True,'original_archive_sha256_claimed_recovered':False}

def verify_mounted_members(directory, repository_root):
    manifest = Path(repository_root)/MOUNTED_MANIFEST
    require(sha(manifest)==MOUNTED_MANIFEST_SHA256,'committed mounted manifest identity differs')
    result = verify_member_directory(directory,manifest,MEMBER_COUNT)
    receipt = Path(result['directory']).parent/'all-members-result.json'
    require(not receipt.is_symlink() and receipt.is_file(), 'recovery receipt missing or symbolic')
    record = json.loads(receipt.read_text())
    require(record.get('schema')=='razr-mounted-exact-STEP-member-recovery-v1', 'unknown recovery receipt')
    require(record.get('original_geometry_manifest_sha256')==MOUNTED_MANIFEST_SHA256,
            'receipt original manifest differs')
    require(record.get('recovered_exact_members')==record.get('expected_members')==MEMBER_COUNT,
            'incomplete recovery receipt')
    require(record.get('original_tar_bytes_recovered') is False, 'receipt must not claim an unrecovered container')
    rows = record.get('members')
    require(isinstance(rows,list) and len(rows)==MEMBER_COUNT, 'receipt member inventory differs')
    require(len({r.get('member') for r in rows})==MEMBER_COUNT, 'duplicate receipt member')
    for row in rows:
        name = row.get('member')
        require(name in result['members'], 'unknown receipt member')
        actual = result['members'][name]
        require(row.get('bytes')==actual['bytes'] and row.get('original_expected_sha256')==actual['sha256']
                and row.get('exact_original_sha256_match') is True, 'receipt member identity differs')
    result.update(recovery_receipt=str(receipt), recovery_receipt_sha256=sha(receipt),
                  artifact_sha256=record.get('artifact_sha256'),
                  declared_original_tar_sha256=json.loads(manifest.read_text())['archive_sha256'],
                  scope='all 64 original STEP member bytes; the original tar container is not recovered')
    result['source_sha256'] = {str(manifest):sha(manifest),str(receipt):sha(receipt),
                              **{r['path']:r['sha256'] for r in result['members'].values()}}
    return result
