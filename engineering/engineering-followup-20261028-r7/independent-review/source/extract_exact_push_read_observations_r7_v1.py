"""Expose only the two original public GitHub response values for this task.

The containing recovery record also has unrelated private recovery metadata;
that material is neither copied nor incorporated into the public ledger.
"""
from pathlib import Path
import datetime
import hashlib
import json

BASE = Path(__file__).resolve().parent.parent
source = BASE / 'r7-audit/R7_RECOVERY_READ_RECEIPTS_V1.private.json'
raw = source.read_bytes()
container = json.loads(raw)
wanted = ('exact_commit', 'original_branch')
selected = []
for name in wanted:
    hits = [row for row in container['observations']
            if row.get('status') == 'fulfilled' and row.get('value', {}).get('name') == name]
    assert len(hits) == 1
    observation = hits[0]['value']
    assert observation['result']['isError'] is True
    assert observation['result']['structuredContent']['error_data']['status'] == '404'
    selected.append(observation)
result = {
    'schema': 'razr-r7-exact-authorized-push-original-read-observations-public-subset-v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'read_only_extraction_no_new_network_query': True,
    'requested_repository': 'TrillionniumFoundation/RAZR-SLIDE',
    'requested_commit': 'a11b00f71231ef3516d2a79c73fa441c375ac755',
    'requested_branch': 'evidence/full-sprint-20261027-n13-l6',
    'requested_identifiers_come_from_the_user_task_and_named_query_context': True,
    'error_response_does_not_itself_echo_the_requested_commit_or_ref': True,
    'original_container_identity': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
    'extractor_identity': {'bytes': Path(__file__).stat().st_size,
                           'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    'original_tool_response_values_preserved': selected,
    'other_private_recovery_observations_included': False,
    'current_remote_global_absence_proved': False,
    'successful_exact_a11_push_receipt_obtained': False,
    'new_commit_substituted_for_authorized_a11': False,
    'interpretation': 'These are the two dated 404 observations, not a proof of global absence. Subsequent R7 commits on the separate R5 evidence branch do not establish the requested exact a11 push.',
}
assert source.read_bytes() == raw
out = BASE / 'r7-audit/blocker-ledger/R7_EXACT_AUTHORIZED_PUSH_ORIGINAL_READ_OBSERVATIONS_V1.json'
assert not out.exists()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
data = out.read_bytes()
print(json.dumps({'path': str(out.relative_to(BASE)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}))
