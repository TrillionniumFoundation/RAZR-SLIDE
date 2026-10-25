"""Durable raw SLIDE pair starts/completions; never a resume certificate.

Only the complete report, journal final commit, atomic index and independent
original geometric/source postguard can qualify a completed diagnostic.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import secrets

SCHEMA = 'razr-slide-pair-journal-r3'
INDEX_SCHEMA = 'razr-slide-pair-journal-index-r3'
CONSTRUCTION = ('native_scene_metadata', 'profiles', 'native_slot_halfwidth_mm',
                'rigid_motion_laws', 'base_spring_records', 'construction',
                'construction_probes_complete', 'native_checks_executed')
POSTFLIGHT = ('identity_after', 'scratch_source_sha256_after', 'execution_completed',
              'construction_probes_complete', 'complete_native_diagnostic_executed',
              'whole_declared_slide_external_pair_domain_clear', 'all_unordered_pairs_present_once',
              'source_bytes_and_locked_environment_unchanged', 'evaluation_failure_count',
              'raw_evidence_validation_failure_count', 'pending_pair_count',
              'recursive_pending_or_budget_node_count', 'terminal_failure', 'postflight_failure',
              'checkpoint_write_failure')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode()


def normalized(value):
    return json.loads(canonical(value))


def object_sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON object key')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))


def selected(report, keys):
    return normalized({key: report.get(key) for key in keys})


def inventory(context):
    names, order = context.get('participant_names'), context.get('pair_visit_order')
    require(isinstance(names, list) and len(names) >= 2 and all(type(n) is str for n in names)
            and names == sorted(set(names)), 'complete unique sorted participant names required')
    pairs = list(itertools.combinations(names, 2))
    require(isinstance(order, list) and all(type(i) is int for i in order)
            and sorted(order) == list(range(len(pairs)))
            and type(context.get('expected_pair_count')) is int
            and context['expected_pair_count'] == len(pairs), 'visit order is not the whole pair permutation')
    return pairs, order


def context_record(head, domain, names, order, sources, identity, limits, report_filename):
    require(type(report_filename) is str and Path(report_filename).name == report_filename
            and report_filename not in ('', '.', '..', 'pairs.jsonl', 'checkpoint-index.json'),
            'same-directory report filename required')
    result = normalized({'schema': 'razr-slide-pair-context-r3', 'expected_head': head,
        'domain': domain, 'participant_names': names, 'expected_pair_count': len(order),
        'pair_visit_order': order, 'raw_report_pair_order': 'lexicographic unordered combinations',
        'visit_order_rule': 'nonflexible pairs first, then original raw pair index',
        'scratch_source_sha256_before': sources, 'identity_before': identity,
        'execution_limits': limits, 'report_filename': report_filename,
        'durability': {'flush_each_record': True, 'fsync_each_pair_start': True,
                       'fsync_completed_pair_batch': 16, 'fsync_phase_boundaries': True},
        'pair_start_means_selected_immediately_before_evaluation_not_proof_of_kernel_entry': True,
        'partial_checkpoint_is_never_a_complete_or_resume_certificate': True})
    inventory(result)
    return result


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_bytes(path, raw):
    path = Path(path)
    temporary = path.with_name(path.name + '.checkpoint-writing')
    require(not path.exists() and not temporary.exists(), 'refusing to replace existing final index/evidence')
    with temporary.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


class PairJournal:
    def __init__(self, path, context):
        self.path = Path(path).resolve()
        require(self.path.name == 'pairs.jsonl', 'fixed same-directory journal name required')
        self.context = normalized(context)
        self.pairs, self.order = inventory(self.context)
        self.context_sha = object_sha(self.context)
        self.run_id = secrets.token_hex(16)
        self.sequence = self.completed = 0
        self.previous = None
        self.active = None
        self.constructed = self.interrupted = self.postflight = self.committed = self.broken = False
        self.stream = self.path.open('xb')
        self.stream_hash = hashlib.sha256()
        try:
            self.append('header', self.context, force=True)
            sync_directory(self.path.parent)
        except BaseException:
            self.broken = True
            self.stream.close()
            raise

    def append(self, kind, payload, force=False):
        require(not self.broken and not self.committed and not self.stream.closed, 'journal is not appendable')
        row = {'schema': SCHEMA, 'sequence': self.sequence, 'kind': kind,
               'run_id': self.run_id, 'context_sha256': self.context_sha,
               'previous_record_sha256': self.previous, 'payload': normalized(payload)}
        digest = object_sha(row)
        raw = canonical({**row, 'record_sha256': digest}) + b'\n'
        try:
            require(self.stream.write(raw) == len(raw), 'short journal write')
            self.stream.flush()
            if force or kind == 'pair_complete' and (self.completed + 1) % 16 == 0:
                os.fsync(self.stream.fileno())
        except BaseException:
            self.broken = True
            raise
        self.stream_hash.update(raw)
        self.previous = digest
        self.sequence += 1

    def record_construction(self, report):
        require(not self.constructed and not self.interrupted and not self.postflight and not self.completed,
                'construction must precede every pair')
        require(report.get('construction_probes_complete') is True and report.get('native_checks_executed') is True,
                'actual complete construction required')
        self.append('construction', selected(report, CONSTRUCTION), force=True)
        self.constructed = True

    def record_start(self, raw_index, row):
        require(self.constructed and not self.interrupted and not self.postflight and self.active is None,
                'pair start lies outside the open constructed phase')
        require(type(raw_index) is int and self.completed < len(self.order)
                and raw_index == self.order[self.completed], 'pair start skips or repeats the source visit order')
        require((row.get('a'), row.get('b')) == self.pairs[raw_index], 'pair start participants differ')
        payload = {'visit_index': self.completed, 'raw_pair_index': raw_index,
                   'a': row['a'], 'b': row['b'], 'pair_class': row['pair_class']}
        self.append('pair_start', payload, force=True)
        self.active = payload

    def record_complete(self, raw_index, row):
        require(self.active is not None and not self.interrupted and not self.postflight,
                'completion has no matching active pair')
        require(type(raw_index) is int and raw_index == self.active['raw_pair_index']
                and (row.get('a'), row.get('b')) == self.pairs[raw_index]
                and row.get('pair_class') == self.active['pair_class'], 'completed pair differs from its start')
        self.append('pair_complete', {'visit_index': self.completed, 'raw_pair_index': raw_index,
                                     'raw_evidence': row})
        self.completed += 1
        self.active = None

    def record_interruption(self, reason, raw=None):
        require(not self.interrupted and not self.postflight, 'only one terminal interruption is allowed')
        if raw is not None:
            require(self.active is not None and (raw.get('a'), raw.get('b')) ==
                    self.pairs[self.active['raw_pair_index']]
                    and raw.get('pair_class') == self.active['pair_class'],
                    'partial raw evidence differs from the active pair')
        self.append('interruption', {'reason': str(reason), 'completed_pair_records': self.completed,
                                    'active_pair_start': self.active, 'raw_interrupted_pair': raw}, force=True)
        self.interrupted = True

    def record_postflight(self, report):
        require(not self.postflight, 'duplicate postflight')
        self.append('postflight', selected(report, POSTFLIGHT), force=True)
        self.postflight = True

    def anchor(self):
        return {'journal_filename': 'pairs.jsonl', 'index_filename': 'checkpoint-index.json',
                'run_id': self.run_id, 'context_sha256': self.context_sha,
                'records_before_final_commit': self.sequence,
                'last_record_before_final_commit_sha256': self.previous,
                'stream_before_final_commit_sha256': self.stream_hash.hexdigest(),
                'completed_pair_records': self.completed, 'expected_pair_records': len(self.order),
                'active_pair_start': self.active, 'final_commit_and_atomic_index_required': True}

    def publish_report(self, path, report):
        path = Path(path).resolve()
        require(path.parent == self.path.parent and path.name == self.context['report_filename']
                and self.postflight and not self.broken, 'healthy same-directory final publication required')
        if self.completed != len(self.order) or self.active is not None or self.interrupted:
            require(report.get('complete_native_diagnostic_executed') is False
                    and report.get('whole_declared_slide_external_pair_domain_clear') is False,
                    'an incomplete journal cannot publish a completed diagnostic')
        index_path = path.parent / 'checkpoint-index.json'
        require(not index_path.exists(), 'final index already exists')
        anchor = self.anchor(); report['checkpoint'] = anchor
        raw = json.dumps(report, separators=(',', ':'), allow_nan=False).encode() + b'\n'
        digest = hashlib.sha256(raw).hexdigest()
        temporary = path.with_name(path.name + '.checkpoint-writing')
        require(not temporary.exists(), 'final staging file already exists')
        previous_report_sha = sha(path) if path.exists() else None
        with temporary.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        self.append('final_commit', {'report_filename': path.name, 'report_sha256': digest,
            'report_bytes': len(raw), 'checkpoint_anchor': anchor,
            'reported_complete_native_diagnostic_executed': report.get('complete_native_diagnostic_executed')}, force=True)
        self.committed = True; self.close()
        require((sha(path) if path.exists() else None) == previous_report_sha, 'prior worker report changed before publication')
        os.replace(temporary, path)
        sync_directory(path.parent)
        index = {'schema': INDEX_SCHEMA, 'journal_filename': 'pairs.jsonl', 'report_filename': path.name,
            'run_id': self.run_id, 'context_sha256': self.context_sha, 'journal_sha256': self.stream_hash.hexdigest(),
            'report_sha256': digest, 'report_bytes': len(raw), 'final_record_sha256': self.previous,
            'completed_pair_records': self.completed, 'original_geometric_and_source_postguard_required': True}
        atomic_bytes(index_path, canonical(index) + b'\n')
        return index

    def close(self):
        if not self.stream.closed:
            try:
                if not self.broken:
                    self.stream.flush(); os.fsync(self.stream.fileno())
            finally:
                self.stream.close()


def read_journal(path, expected_context=None, allow_truncated_tail=True):
    path = Path(path)
    digest = hashlib.sha256()
    context = run = context_sha = previous = None
    sequence = completed = tail = 0
    construction = interruption = postflight = commit = active = anchor = None
    rows = []; starts = []
    pairs = order = []
    with path.open('rb') as stream:
        for raw in stream:
            prefix_sha = digest.hexdigest(); digest.update(raw)
            if not raw.endswith(b'\n'):
                require(allow_truncated_tail, 'truncated final journal record')
                tail = len(raw); break
            item = parse(raw)
            require(isinstance(item, dict) and set(item) == {'schema', 'sequence', 'kind', 'run_id',
                    'context_sha256', 'previous_record_sha256', 'payload', 'record_sha256'}, 'wrong record envelope')
            row_sha = item.pop('record_sha256')
            require(item['schema'] == SCHEMA and type(item['sequence']) is int and item['sequence'] == sequence
                    and row_sha == object_sha(item) and item['previous_record_sha256'] == previous,
                    'record is changed, duplicated, reordered, or omitted')
            kind, payload = item['kind'], item['payload']
            require(isinstance(payload, dict), 'record payload must be an object')
            if sequence == 0:
                require(kind == 'header', 'source-bound header required first')
                context, run, context_sha = payload, item['run_id'], item['context_sha256']
                require(isinstance(run, str) and re.fullmatch('[0-9a-f]{32}', run) is not None
                        and context_sha == object_sha(context), 'invalid run/context identity')
                pairs, order = inventory(context)
                if expected_context is not None:
                    require(context == normalized(expected_context), 'source/domain/runtime context differs')
            else:
                require(item['run_id'] == run and item['context_sha256'] == context_sha and commit is None,
                        'cross-run record or record after final commit')
                if kind == 'construction':
                    require(construction is None and completed == 0 and active is None and interruption is None
                            and postflight is None and payload.get('construction_probes_complete') is True
                            and payload.get('native_checks_executed') is True
                            and set(payload) == set(CONSTRUCTION), 'construction phase differs')
                    construction = payload
                elif kind == 'pair_start':
                    require(construction is not None and interruption is None and postflight is None and active is None
                            and completed < len(order) and type(payload.get('visit_index')) is int
                            and payload['visit_index'] == completed and type(payload.get('raw_pair_index')) is int
                            and payload['raw_pair_index'] == order[completed], 'pair start skips, repeats, or overlaps')
                    require(set(payload) == {'visit_index', 'raw_pair_index', 'a', 'b', 'pair_class'}
                            and (payload['a'], payload['b']) == pairs[order[completed]], 'started pair identity differs')
                    active = payload; starts.append(payload)
                elif kind == 'pair_complete':
                    require(active is not None and interruption is None and postflight is None
                            and set(payload) == {'visit_index', 'raw_pair_index', 'raw_evidence'}
                            and type(payload.get('visit_index')) is int and payload['visit_index'] == completed
                            and type(payload.get('raw_pair_index')) is int and payload['raw_pair_index'] == order[completed],
                            'completed pair has no matching current start')
                    row = payload.get('raw_evidence')
                    require(isinstance(row, dict) and (row.get('a'), row.get('b')) == pairs[order[completed]]
                            and row.get('pair_class') == active['pair_class'], 'completed pair identity changed')
                    rows.append(payload); completed += 1; active = None
                elif kind == 'interruption':
                    require(interruption is None and postflight is None
                            and set(payload) == {'reason', 'completed_pair_records', 'active_pair_start', 'raw_interrupted_pair'}
                            and type(payload.get('reason')) is str
                            and type(payload.get('completed_pair_records')) is int
                            and payload.get('completed_pair_records') == completed
                            and payload.get('active_pair_start') == active, 'interruption state differs')
                    row = payload.get('raw_interrupted_pair')
                    if row is not None:
                        require(isinstance(row, dict) and active is not None
                                and (row.get('a'), row.get('b')) == pairs[active['raw_pair_index']]
                                and row.get('pair_class') == active['pair_class'],
                                'interrupted raw evidence differs from active pair')
                    interruption = payload
                elif kind == 'postflight':
                    require(postflight is None and set(payload) == set(POSTFLIGHT), 'duplicate or invalid postflight')
                    postflight = payload
                elif kind == 'final_commit':
                    require(postflight is not None and set(payload) == {'report_filename', 'report_sha256',
                            'report_bytes', 'checkpoint_anchor', 'reported_complete_native_diagnostic_executed'},
                            'final commit precedes postflight or has unknown fields')
                    anchor = {'journal_filename': 'pairs.jsonl', 'index_filename': 'checkpoint-index.json',
                        'run_id': run, 'context_sha256': context_sha, 'records_before_final_commit': sequence,
                        'last_record_before_final_commit_sha256': previous,
                        'stream_before_final_commit_sha256': prefix_sha, 'completed_pair_records': completed,
                        'expected_pair_records': len(order), 'active_pair_start': active,
                        'final_commit_and_atomic_index_required': True}
                    require(payload.get('checkpoint_anchor') == anchor, 'final commit prefix anchor differs')
                    commit = payload
                else:
                    raise ValueError('unknown record kind or repeated header')
            previous = row_sha; sequence += 1
    require(context is not None, 'no intact source-bound header')
    return {'context': context, 'run_id': run, 'context_sha256': context_sha, 'journal_sha256': digest.hexdigest(),
        'last_record_sha256': previous, 'complete_records': sequence, 'completed_pair_records': completed,
        'expected_pair_records': len(order), 'completed_pairs': rows, 'pair_starts': starts,
        'active_pair_start': active, 'construction': construction, 'interruption': interruption,
        'postflight': postflight, 'final_commit': commit, 'checkpoint_anchor': anchor, 'truncated_tail_bytes': tail,
        'complete_native_diagnostic_executed': False, 'whole_declared_slide_external_pair_domain_clear': False,
        'partial_or_seal_alone_is_never_a_complete_or_resume_certificate': True}


def validate_published(report_path, expected_context):
    path = Path(report_path).resolve()
    raw = path.read_bytes(); report_sha = hashlib.sha256(raw).hexdigest(); report = parse(raw)
    journal_path, index_path = path.parent/'pairs.jsonl', path.parent/'checkpoint-index.json'
    journal = read_journal(journal_path, expected_context, allow_truncated_tail=False)
    index_raw = index_path.read_bytes(); index_sha = hashlib.sha256(index_raw).hexdigest(); index = parse(index_raw)
    commit = journal['final_commit']
    require(isinstance(commit, dict) and report.get('checkpoint') == journal['checkpoint_anchor'], 'final commit absent or anchor differs')
    require(commit.get('report_filename') == path.name == expected_context['report_filename']
            and commit.get('report_sha256') == report_sha and commit.get('report_bytes') == len(raw)
            and commit.get('reported_complete_native_diagnostic_executed') == report.get('complete_native_diagnostic_executed'),
            'final commit does not bind the actual full report')
    require(index == {'schema': INDEX_SCHEMA, 'journal_filename': 'pairs.jsonl', 'report_filename': path.name,
        'run_id': journal['run_id'], 'context_sha256': journal['context_sha256'],
        'journal_sha256': journal['journal_sha256'], 'report_sha256': report_sha, 'report_bytes': len(raw),
        'final_record_sha256': journal['last_record_sha256'], 'completed_pair_records': journal['completed_pair_records'],
        'original_geometric_and_source_postguard_required': True}, 'atomic final index differs')
    rows = report.get('pairs')
    require(isinstance(rows, list), 'full report raw pair inventory absent')
    for item in journal['completed_pairs']:
        require(len(rows) > item['raw_pair_index'] and rows[item['raw_pair_index']] == item['raw_evidence'],
                'full report changed or lost an already completed pair')
    interrupted = journal['interruption']
    if interrupted is not None and interrupted['raw_interrupted_pair'] is not None:
        i = interrupted['active_pair_start']['raw_pair_index']
        require(len(rows) > i and rows[i] == interrupted['raw_interrupted_pair'], 'full report changed interrupted raw evidence')
    if journal['construction'] is not None:
        require(journal['construction'] == selected(report, CONSTRUCTION), 'construction snapshot differs')
    require(journal['postflight'] == selected(report, POSTFLIGHT), 'postflight snapshot differs')
    require(report.get('identity_before') == expected_context['identity_before']
            and report.get('scratch_source_sha256_before') == expected_context['scratch_source_sha256_before']
            and normalized(report.get('domain')) == expected_context['domain']
            and report.get('execution_limits') == expected_context['execution_limits'], 'final source/domain/limits differ')
    complete_pairs = (journal['completed_pair_records'] == journal['expected_pair_records']
                      and journal['active_pair_start'] is None and interrupted is None
                      and len(rows) == journal['expected_pair_records'])
    if not complete_pairs:
        require(report.get('complete_native_diagnostic_executed') is False
                and report.get('whole_declared_slide_external_pair_domain_clear') is False,
                'partial raw evidence cannot claim a whole diagnostic')
    require(sha(path) == report_sha and sha(journal_path) == journal['journal_sha256'] and sha(index_path) == index_sha,
            'publication files changed during independent readback')
    return {'report': report, 'journal': journal, 'all_expected_pair_records_present': complete_pairs,
            'publication_sha256': {str(path): report_sha, str(journal_path): journal['journal_sha256'],
                                   str(index_path): index_sha},
            'checkpoint_publication_chain_verified': True, 'complete_native_diagnostic_executed': False}
