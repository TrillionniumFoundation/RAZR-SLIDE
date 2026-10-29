"""Bind the independently reviewed completed method checkpoint to a new Git tree."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'engineering/engineering-followup-20261028-r7/'
PARENT = '34764db3c8d61d6e53ea22da8caf4dc57b931463'
BASE_TREE = '1195ca799d551a53f7c27b8ff3a175cca19cb8fb'
TARGET = ROOT / 'r7-publication/R7_METHOD_CHECKPOINT_GIT_TREE_REQUEST_V1.json'


def identity(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob_sha': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def main():
    assert not TARGET.exists()
    directory = ROOT / 'r7-publication/method-checkpoint-v2'
    prepared = json.loads((directory / 'MANIFEST.json').read_text())
    assert identity(directory / 'MANIFEST.json')['sha256'] == '19c591f3f48af446215a79852149e75be14d9e0a73bfebc3f4db10f5a68f5872'
    selected = {}
    for row in prepared['files']:
        assert identity(Path(row['original_path'])) == row['original_identity']
        p = Path(row['transport_path'])
        assert identity(p) == row['transport_identity']
        selected[row['repository_path']] = p
    extras = (
        (directory / 'MANIFEST.json', 'publication/METHOD_COMPLETED_PAYLOAD_MANIFEST_V2.json'),
        (directory / 'PREPARATION_SEAL.json', 'publication/METHOD_COMPLETED_PREPARATION_SEAL_V2.json'),
        (ROOT / 'r7-publication/R7_METHOD_BINARY_PUBLICATION_RECEIPTS_V1.json', 'publication/R7_METHOD_BINARY_PUBLICATION_RECEIPTS_V1.json'),
        (ROOT / 'r7-publication/R7_METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V2.md', 'METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V2.md'),
        (ROOT / 'r7-publication/R7_METHOD_SCOPE_WORDING_CORRECTION_V2.json', 'publication/R7_METHOD_SCOPE_WORDING_CORRECTION_V2.json'),
        (Path(__file__), 'publication/' + Path(__file__).name),
    )
    for p, destination in extras:
        assert PREFIX + destination not in selected
        selected[PREFIX + destination] = p
    review = ROOT / 'r7-audit/method-publication-v2-review'
    assert identity(review / 'MANIFEST.json')['sha256'] == '2abafce175d221aa2128bd31d5cd4fa4417d67da33d2f2382ea807e2505adda8'
    assert identity(review / 'R7_METHOD_CHECKPOINT_INDEPENDENT_REVIEW_V1.json')['sha256'] == '8893bb0c69bd3dadc9cd2bb85eeb0c432f1658f2a92f35923cff1d484cc208a9'
    for p in sorted(review.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            destination = PREFIX + 'independent-review/method-publication-v2-review/' + p.relative_to(review).as_posix()
            assert destination not in selected
            selected[destination] = p
    prior = json.loads((ROOT / 'r7-publication/R7_NATIVE_FINITE_REMOTE_SUBTREE_READBACK_V1.json').read_text())
    old = {PREFIX + row['path']: row for row in prior['tree'] if row['type'] == 'blob'}
    assert len(old) == 767 and not prior['truncated']
    known = {row['sha'] for row in old.values()}
    receipts = json.loads((ROOT / 'r7-publication/R7_METHOD_BINARY_PUBLICATION_RECEIPTS_V1.json').read_text())
    assert receipts['all_expected_sha_match']
    known.update(row['returned_sha'] for row in receipts['files'])
    rows = []; elements = []
    for destination, p in sorted(selected.items()):
        assert destination not in old
        assert p.is_file() and not p.is_symlink()
        assert '.private.' not in p.name and 'r7-private-helpers' not in p.parts
        ident = identity(p)
        row = {'repository_path': destination, 'local_path': str(p), **ident}
        rows.append(row)
        item = {'path': destination, 'type': 'blob', 'mode': '100644'}
        if ident['git_blob_sha'] in known:
            item['sha'] = ident['git_blob_sha']
        else:
            text = p.read_text()
            assert '\0' not in text
            item['content'] = text
        elements.append(item)
    manifest = {'schema': 'razr-r7-completed-method-final-publication-manifest-v1',
                'parent_commit': PARENT, 'base_tree': BASE_TREE, 'files': rows,
                'independently_reviewed_payload_count': 151, 'all_prior_767_R7_blobs_unchanged': True,
                'only_new_R7_paths_added': True, 'workflows_or_RUN_REQUEST_modified': False,
                'exact_a11_requested_push_fulfilled': False, 'full_continuous_G2': False,
                'all_blockers_closed': False}
    content = json.dumps(manifest, indent=2) + '\n'
    manifest_path = ROOT / 'r7-publication/R7_METHOD_CHECKPOINT_PUBLICATION_MANIFEST_V1.json'
    assert not manifest_path.exists(); manifest_path.write_text(content)
    destination = PREFIX + 'R7_METHOD_CHECKPOINT_PUBLICATION_MANIFEST_V1.json'
    elements.append({'path': destination, 'mode': '100644', 'type': 'blob', 'content': content})
    expected = rows + [{'repository_path': destination, 'local_path': str(manifest_path), **identity(manifest_path)}]
    expected_path = ROOT / 'r7-publication/R7_METHOD_CHECKPOINT_EXPECTED_REMOTE_BLOBS_V1.json'
    assert not expected_path.exists(); expected_path.write_text(json.dumps(expected, indent=2) + '\n')
    request = {'repository_full_name': 'TrillionniumFoundation/RAZR-SLIDE',
               'base_tree_sha': BASE_TREE, 'tree_elements': elements}
    encoded = json.dumps(request, ensure_ascii=True, separators=(',', ':')) + '\n'
    assert len(encoded.encode()) < 14 * 1024 * 1024
    TARGET.write_text(encoded)
    print(json.dumps({'request': {'path': str(TARGET), **identity(TARGET)},
                      'new_blobs': len(elements), 'new_text_entries': sum('content' in r for r in elements),
                      'known_blob_entries': sum('sha' in r for r in elements),
                      'parent_commit': PARENT, 'base_tree': BASE_TREE, 'ref_mutated': False}))


if __name__ == '__main__':
    main()
