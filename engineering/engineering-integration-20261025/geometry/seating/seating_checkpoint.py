"""Append-only, source/domain/run-bound raw pair evidence for SEATING v2.

The journal preserves interrupted work; it is not a geometry certificate.
Only a complete raw report, a final journal commit, an atomic index, and the
independent geometric/source postguard can qualify a completed diagnostic.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import secrets

SCHEMA = 'razr-seating-pair-journal-v2'
INDEX_SCHEMA = 'razr-seating-pair-journal-index-v2'
FSYNC_PAIR_BATCH = 16
CONSTRUCTION_KEYS = ('native_scene_metadata', 'native_slot_halfwidth_mm', 'rigid_Z_laws',
                     'construction_probes', 'construction_completed', 'native_checks_executed')
POSTFLIGHT_KEYS = ('identity_after', 'adapter_source_sha256_after', 'construction_completed',
                  'complete_native_diagnostic_executed', 'whole_declared_seating_external_pair_domain_clear',
                  'all_unordered_pairs_present_once', 'source_bytes_unchanged',
                  'evaluation_failure_count', 'raw_evidence_validation_failure_count',
                  'resource_stop', 'execution_failure', 'post_execution_identity_failure',
                  'checkpoint_write_failure')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def normalized(value):
    return json.loads(canonical(value))


def object_sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(2**20):
            value.update(block)
    return value.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON object key')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))


def context_record(expected_head, domain, names, adapter_sources, identity_before, controls):
    return normalized({'schema': 'razr-seating-journal-context-v2',
        'expected_head': expected_head, 'domain': domain,
        'participant_names': names, 'expected_pair_count': math.comb(len(names), 2),
        'pair_order': 'lexicographic unordered combinations of complete sorted participant names',
        'adapter_source_sha256_before': adapter_sources, 'identity_before': identity_before,
        'execution_limits': controls,
        'durability': {'flush_each_record': True, 'fsync_pair_batch': FSYNC_PAIR_BATCH,
                       'fsync_header_construction_interruption_postflight_and_final_commit': True},
        'partial_checkpoint_can_qualify_complete_domain': False})


def selected(report, keys):
    return normalized({key: report.get(key) for key in keys})


def atomic_bytes(path, raw):
    path = Path(path)
    temporary = path.with_name(path.name + '.writing')
    require(not path.exists() and not temporary.exists(), 'refusing to replace existing evidence')
    with temporary.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


class PairJournal:
    def __init__(self, path, context):
        self.path = Path(path).resolve()
        self.context = normalized(context)
        names = self.context['participant_names']
        require(isinstance(names, list) and len(names) >= 2 and names == sorted(set(names)),
                'sorted complete unique participant names required')
        self.pairs = list(itertools.combinations(names, 2))
        require(self.context['expected_pair_count'] == len(self.pairs), 'pair count differs from inventory')
        self.run_id = secrets.token_hex(16)
        self.context_sha = object_sha(self.context)
        self.stream = self.path.open('xb')
        self.stream_hash = hashlib.sha256()
        self.sequence = 0
        self.last_sha = None
        self.completed_pairs = 0
        self.construction = self.interrupted = self.postflight = self.committed = False
        self.broken = False
        self._append('header', self.context, force=True)

    def _append(self, kind, payload, *, force=False):
        require(not self.broken and not self.stream.closed and not self.committed,
                'journal is closed, broken, or already committed')
        record = {'schema': SCHEMA, 'sequence': self.sequence, 'kind': kind,
                  'run_id': self.run_id, 'context_sha256': self.context_sha,
                  'previous_record_sha256': self.last_sha, 'payload': normalized(payload)}
        digest = object_sha(record)
        raw = canonical({**record, 'record_sha256': digest}) + b'\n'
        try:
            self.stream.write(raw)
            self.stream.flush()
            if force or kind == 'pair' and (self.completed_pairs + 1) % FSYNC_PAIR_BATCH == 0:
                os.fsync(self.stream.fileno())
        except BaseException:
            self.broken = True
            raise
        self.stream_hash.update(raw)
        self.sequence += 1
        self.last_sha = digest
        return digest

    def record_construction(self, report):
        require(not self.construction and not self.interrupted and not self.postflight
                and self.completed_pairs == 0, 'construction must precede every pair')
        require(report.get('construction_completed') is True, 'actual completed construction required')
        self._append('construction', selected(report, CONSTRUCTION_KEYS), force=True)
        self.construction = True

    def record_pair(self, index, row):
        require(self.construction and not self.interrupted and not self.postflight,
                'pair cannot precede construction or follow interruption/postflight')
        require(type(index) is int and index == self.completed_pairs and index < len(self.pairs),
                'pair records must form the unique original ordered prefix')
        require((row.get('a'), row.get('b')) == self.pairs[index], 'pair is duplicated or outside its original index')
        self._append('pair', {'pair_index': index, 'raw_evidence': row})
        self.completed_pairs += 1

    def record_interruption(self, reason, row=None):
        require(not self.interrupted and not self.postflight, 'only one terminal interruption is allowed')
        if row is not None:
            require(self.completed_pairs < len(self.pairs)
                    and (row.get('a'), row.get('b')) == self.pairs[self.completed_pairs],
                    'partial evidence must belong to the next uncommitted pair')
        self._append('interruption', {'reason': str(reason), 'next_pair_index': self.completed_pairs,
                                     'raw_interrupted_pair': row}, force=True)
        self.interrupted = True

    def record_postflight(self, report):
        require(not self.postflight, 'postflight cannot be appended twice')
        self._append('postflight', selected(report, POSTFLIGHT_KEYS), force=True)
        self.postflight = True

    def anchor(self):
        return {'journal_filename': self.path.name, 'index_filename': 'checkpoint-index.json',
                'run_id': self.run_id, 'context_sha256': self.context_sha,
                'records_before_final_commit': self.sequence,
                'last_record_before_final_commit_sha256': self.last_sha,
                'stream_before_final_commit_sha256': self.stream_hash.hexdigest(),
                'completed_pair_records': self.completed_pairs, 'expected_pair_records': len(self.pairs),
                'final_commit_and_atomic_index_required': True}

    def publish_report(self, path, report):
        path = Path(path).resolve()
        require(path.parent == self.path.parent and self.postflight and not self.broken,
                'a healthy postflight journal and same-directory final report are required')
        index_path = path.parent / 'checkpoint-index.json'
        require(not index_path.exists(), 'refusing to replace an existing checkpoint index')
        if self.completed_pairs != len(self.pairs) or self.interrupted:
            report['complete_native_diagnostic_executed'] = False
            report['whole_declared_seating_external_pair_domain_clear'] = False
        anchor = self.anchor()
        report['checkpoint'] = anchor
        raw = json.dumps(report, indent=2, allow_nan=False).encode('utf-8') + b'\n'
        report_sha = hashlib.sha256(raw).hexdigest()
        temporary = path.with_name(path.name + '.writing')
        require(not path.exists() and not temporary.exists(), 'refusing to replace a final or staged report')
        with temporary.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        self._append('final_commit', {'report_filename': path.name, 'report_sha256': report_sha,
            'report_bytes': len(raw), 'checkpoint_anchor': anchor,
            'reported_complete_native_diagnostic_executed': report.get('complete_native_diagnostic_executed')}, force=True)
        self.committed = True
        self.close()
        os.replace(temporary, path)
        index = {'schema': INDEX_SCHEMA, 'journal_filename': self.path.name, 'report_filename': path.name,
                 'run_id': self.run_id, 'context_sha256': self.context_sha,
                 'journal_sha256': self.stream_hash.hexdigest(), 'report_sha256': report_sha,
                 'report_bytes': len(raw), 'final_record_sha256': self.last_sha,
                 'completed_pair_records': self.completed_pairs,
                 'geometry_and_current_source_postguard_required': True}
        atomic_bytes(index_path, canonical(index) + b'\n')
        return index

    def close(self):
        if not self.stream.closed:
            if not self.broken:
                self.stream.flush(); os.fsync(self.stream.fileno())
            self.stream.close()


def read_journal(path, *, expected_context=None, allow_truncated_tail=True):
    """Read a valid prefix; neither a prefix nor a final commit grants clearance."""
    path = Path(path)
    whole_hash = hashlib.sha256()
    context = None
    run_id = context_sha = previous = None
    sequence = completed = 0
    expected_pairs = []
    rows = []
    construction = interruption = postflight = commit = None
    before_commit = None
    tail_bytes = 0
    with path.open('rb') as stream:
        for raw in stream:
            prefix_sha = whole_hash.hexdigest()
            whole_hash.update(raw)
            if not raw.endswith(b'\n'):
                require(allow_truncated_tail, 'truncated final JSONL record')
                tail_bytes = len(raw)
                break
            item = parse(raw)
            require(isinstance(item, dict) and set(item) == {'schema', 'sequence', 'kind', 'run_id',
                    'context_sha256', 'previous_record_sha256', 'payload', 'record_sha256'}, 'wrong record envelope')
            digest = item.pop('record_sha256')
            require(item['schema'] == SCHEMA and type(item['sequence']) is int and item['sequence'] == sequence,
                    'record schema or sequence differs')
            require(isinstance(digest, str) and digest == object_sha(item), 'record content SHA differs')
            require(item['previous_record_sha256'] == previous, 'record chain is reordered or broken')
            kind, payload = item['kind'], item['payload']
            if sequence == 0:
                require(kind == 'header' and isinstance(payload, dict), 'journal must start with exactly one header')
                context, run_id, context_sha = payload, item['run_id'], item['context_sha256']
                require(isinstance(run_id, str) and re.fullmatch('[0-9a-f]{32}', run_id) is not None,
                        'unique run identity is malformed')
                require(context_sha == object_sha(context), 'header context SHA differs')
                names = context.get('participant_names')
                require(isinstance(names, list) and len(names) >= 2 and names == sorted(set(names)),
                        'invalid complete participant inventory')
                expected_pairs = list(itertools.combinations(names, 2))
                require(context.get('expected_pair_count') == len(expected_pairs), 'header pair count differs')
                if expected_context is not None:
                    require(context == normalized(expected_context), 'journal source/domain/runtime context differs')
            else:
                require(item['run_id'] == run_id and item['context_sha256'] == context_sha,
                        'record belongs to another run or source/domain context')
                require(commit is None, 'record follows a final commit')
                if kind == 'construction':
                    require(construction is None and completed == 0 and interruption is None and postflight is None,
                            'construction record is duplicated or misplaced')
                    require(payload.get('construction_completed') is True, 'construction is not complete')
                    construction = payload
                elif kind == 'pair':
                    require(construction is not None and interruption is None and postflight is None,
                            'pair lies outside the construction-to-postflight interval')
                    index, row = payload.get('pair_index'), payload.get('raw_evidence')
                    require(type(index) is int and index == completed and index < len(expected_pairs),
                            'pair index is duplicated, omitted, or outside its inventory')
                    require(isinstance(row, dict) and (row.get('a'), row.get('b')) == expected_pairs[index],
                            'raw pair does not match its original participant index')
                    rows.append(row); completed += 1
                elif kind == 'interruption':
                    require(interruption is None and postflight is None and payload.get('next_pair_index') == completed,
                            'interruption is duplicated or misplaced')
                    row = payload.get('raw_interrupted_pair')
                    if row is not None:
                        require(completed < len(expected_pairs) and (row.get('a'), row.get('b')) == expected_pairs[completed],
                                'interrupted raw pair differs from the next uncommitted index')
                    interruption = payload
                elif kind == 'postflight':
                    require(postflight is None, 'duplicate postflight')
                    postflight = payload
                elif kind == 'final_commit':
                    require(postflight is not None, 'final commit precedes postflight')
                    before_commit = {'journal_filename': path.name, 'index_filename': 'checkpoint-index.json',
                        'run_id': run_id, 'context_sha256': context_sha, 'records_before_final_commit': sequence,
                        'last_record_before_final_commit_sha256': previous,
                        'stream_before_final_commit_sha256': prefix_sha,
                        'completed_pair_records': completed, 'expected_pair_records': len(expected_pairs),
                        'final_commit_and_atomic_index_required': True}
                    require(payload.get('checkpoint_anchor') == before_commit, 'final commit does not bind the exact durable prefix')
                    commit = payload
                else:
                    raise ValueError('unknown or repeated header record kind')
            previous = digest
            sequence += 1
    require(context is not None, 'journal has no intact source/domain header')
    return {'schema': 'razr-seating-journal-prefix-readback-v2', 'path': str(path), 'context': context,
            'run_id': run_id, 'context_sha256': context_sha, 'journal_sha256': whole_hash.hexdigest(),
            'last_record_sha256': previous, 'complete_records': sequence, 'completed_pair_records': completed,
            'expected_pair_records': len(expected_pairs), 'raw_pairs': rows, 'construction': construction,
            'interruption': interruption, 'postflight': postflight, 'final_commit': commit,
            'checkpoint_anchor': before_commit, 'truncated_tail_bytes': tail_bytes,
            'all_expected_pairs_recorded': completed == len(expected_pairs),
            'complete_native_diagnostic_executed': False,
            'whole_declared_seating_external_pair_domain_clear': False,
            'prefix_only_or_final_commit_alone_never_qualifies': True}


def validate_published(report_path, *, expected_context):
    """Bind all final bytes to the journal; geometry checks remain separate."""
    report_path = Path(report_path).resolve()
    raw = report_path.read_bytes()
    report_sha = hashlib.sha256(raw).hexdigest()
    report = parse(raw)
    anchor = report.get('checkpoint')
    require(isinstance(anchor, dict) and anchor.get('journal_filename') == 'pairs.jsonl'
            and anchor.get('index_filename') == 'checkpoint-index.json', 'complete checkpoint anchor absent')
    journal_path = report_path.parent / 'pairs.jsonl'
    index_path = report_path.parent / 'checkpoint-index.json'
    journal = read_journal(journal_path, expected_context=expected_context, allow_truncated_tail=False)
    index = parse(index_path.read_bytes())
    commit = journal['final_commit']
    require(isinstance(commit, dict) and journal['truncated_tail_bytes'] == 0, 'uncommitted or truncated journal')
    require(report['checkpoint'] == journal['checkpoint_anchor'], 'report checkpoint anchor differs')
    require(commit['report_filename'] == report_path.name and commit['report_sha256'] == report_sha
            and commit['report_bytes'] == len(raw), 'final commit does not bind actual final report bytes')
    require(index == {'schema': INDEX_SCHEMA, 'journal_filename': 'pairs.jsonl', 'report_filename': report_path.name,
            'run_id': journal['run_id'], 'context_sha256': journal['context_sha256'],
            'journal_sha256': journal['journal_sha256'], 'report_sha256': report_sha, 'report_bytes': len(raw),
            'final_record_sha256': journal['last_record_sha256'],
            'completed_pair_records': journal['completed_pair_records'],
            'geometry_and_current_source_postguard_required': True}, 'atomic final index differs from actual bytes')
    rows = report.get('pairs')
    require(isinstance(rows, list) and rows[:journal['completed_pair_records']] == journal['raw_pairs'],
            'final report changes or loses committed raw pair evidence')
    if journal['interruption'] and journal['interruption']['raw_interrupted_pair'] is not None:
        index = journal['completed_pair_records']
        require(len(rows) > index and rows[index] == journal['interruption']['raw_interrupted_pair'],
                'final report changes interrupted raw evidence')
    if journal['construction'] is not None:
        require(journal['construction'] == selected(report, CONSTRUCTION_KEYS), 'construction evidence differs')
    require(journal['postflight'] == selected(report, POSTFLIGHT_KEYS), 'postflight evidence differs')
    require(report.get('identity_before') == journal['context']['identity_before']
            and report.get('adapter_source_sha256_before') == journal['context']['adapter_source_sha256_before']
            and normalized(report.get('domain')) == journal['context']['domain'], 'report initial identity/domain differs')
    require(commit.get('reported_complete_native_diagnostic_executed') == report.get('complete_native_diagnostic_executed'),
            'report completion differs from its final commit')
    all_pairs = (journal['all_expected_pairs_recorded'] and journal['interruption'] is None
                 and len(rows) == journal['expected_pair_records'])
    if not all_pairs:
        require(report.get('complete_native_diagnostic_executed') is False
                and report.get('whole_declared_seating_external_pair_domain_clear') is False,
                'a partial checkpoint cannot claim a complete native domain')
    require(sha(report_path) == report_sha and sha(journal_path) == journal['journal_sha256'],
            'checkpoint or report changed during readback')
    return {'report': report, 'journal': journal,
            'complete_publication_chain_verified': True,
            'all_expected_pair_records_present': all_pairs,
            'complete_native_diagnostic_executed': False,
            'geometry_and_current_source_postguard_still_required': True}
