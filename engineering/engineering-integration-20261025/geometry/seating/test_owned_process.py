"""Pure own-child identity/procfs/pipe negative controls; no subprocess or CAD."""
from __future__ import annotations

import copy
import errno
import json
import os
from pathlib import Path
import types
import unittest
from unittest import mock

import owned_process as process


def identity(pid=420005, ppid=420002, inner=5):
    return {'status': {'Pid': pid, 'PPid': ppid, 'NSpid': [pid, inner]},
            'stat': {'pid': pid, 'ppid': ppid, 'starttime_ticks': 123456},
            'pid_namespace': 'pid:[4026532277]',
            'pid_for_children_namespace': 'pid:[4026532277]'}


def parent():
    return {'os_getpid': 2, 'os_getppid': 1, 'proc_self_visible_pid': '420002',
            **identity(420002, 420001, 2)}


def status_text(rss='12 kB', hwm='16 kB'):
    lines = ['Pid:\t420005', 'PPid:\t420002', 'NSpid:\t420005\t5']
    if rss is not None:
        lines.append('VmRSS:\t'+rss)
    if hwm is not None:
        lines.append('VmHWM:\t'+hwm)
    return '\n'.join(lines)+'\n'


class OwnedProcessTests(unittest.TestCase):
    def channel(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(process, 'own_identity', return_value=parent()).start()
        mock.patch.object(process, 'sha', return_value='a'*64).start()
        channel = process.OwnedChildChannel(__file__)
        self.addCleanup(channel.close)
        child = types.SimpleNamespace(pid=5, poll=lambda: None)
        packet = {'kind': process.KIND, 'nonce': channel.nonce, 'source_sha256': 'a'*64,
                  'os_getpid': 5, 'os_getppid': 2, 'proc_self_visible_pid': '420005', **identity()}
        return channel, child, packet

    def bound(self):
        channel, child, packet = self.channel()
        channel.binding = channel._validate_packet(packet, child)
        channel.packet, channel.child_pid = packet, child.pid
        return channel, child, packet

    def test_valid_distinct_namespace_mapping_and_positive_memory(self):
        channel, child, packet = self.bound()
        with mock.patch.object(process, 'proc_identity', return_value=identity()) as lookup, \
             mock.patch.object(Path, 'read_text', return_value=status_text()) as read:
            self.assertEqual(channel.sample(child), {'VmRSS': 12288, 'VmHWM': 16384})
        self.assertEqual([str(call.args[0]) for call in lookup.call_args_list],
                         ['/proc/420005', '/proc/420005'])
        self.assertEqual(read.call_count, 1)
        self.assertNotEqual(child.pid, int(packet['proc_self_visible_pid']))

    def test_nonce_source_PID_parent_namespace_and_strict_scalar_tampering_rejected(self):
        channel, child, original = self.channel()
        mutations = (
            ('nonce', lambda p: p.update(nonce='0'*64)),
            ('source', lambda p: p.update(source_sha256='b'*64)),
            ('namespace PID', lambda p: p.update(os_getpid=6)),
            ('boolean PID', lambda p: p.update(os_getpid=True)),
            ('namespace PPID', lambda p: p.update(os_getppid=3)),
            ('path', lambda p: p.update(proc_self_visible_pid='../self')),
            ('noncanonical PID', lambda p: p.update(proc_self_visible_pid='0420005')),
            ('status PID', lambda p: p['status'].update(Pid=420006)),
            ('stat PID', lambda p: p['stat'].update(pid=420006)),
            ('visible parent', lambda p: (p['status'].update(PPid=420007), p['stat'].update(ppid=420007))),
            ('NSpid first', lambda p: p['status'].update(NSpid=[420006, 5])),
            ('NSpid last', lambda p: p['status'].update(NSpid=[420005, 6])),
            ('NSpid absent', lambda p: p['status'].update(NSpid=[])),
            ('starttime zero', lambda p: p['stat'].update(starttime_ticks=0)),
            ('PID namespace', lambda p: p.update(pid_namespace='pid:[9]')),
            ('children namespace', lambda p: p.update(pid_for_children_namespace='pid:[9]')),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                packet = copy.deepcopy(original); mutate(packet)
                with self.assertRaises(ValueError):
                    channel._validate_packet(packet, child)

    def test_worker_source_change_before_release_is_rejected(self):
        channel, child, packet = self.channel()
        with mock.patch.object(process, 'sha', return_value='b'*64), self.assertRaises(ValueError):
            channel._validate_packet(packet, child)

    def test_sample_rechecks_identity_before_and_after_memory(self):
        channel, child, _ = self.bound()
        for field in ('starttime', 'namespace', 'NSpid', 'PPid'):
            bad = identity()
            if field == 'starttime': bad['stat']['starttime_ticks'] += 1
            if field == 'namespace': bad['pid_namespace'] = 'pid:[9]'
            if field == 'NSpid': bad['status']['NSpid'][-1] = 6
            if field == 'PPid': bad['status']['PPid'] = 420001
            for observations in ([bad, identity()], [identity(), bad]):
                with self.subTest(field=field, changed_first=observations[0] == bad), \
                     mock.patch.object(process, 'proc_identity', side_effect=observations), \
                     mock.patch.object(Path, 'read_text', return_value=status_text()), \
                     self.assertRaises(ValueError):
                    channel.sample(child)

    def test_alive_missing_zero_negative_wrong_unit_or_inconsistent_RSS_is_error(self):
        channel, child, _ = self.bound()
        for rss, hwm in ((None, None), ('0 kB', '16 kB'), ('-1 kB', '16 kB'),
                         ('12 MB', '16 kB'), ('17 kB', '16 kB')):
            with self.subTest(rss=rss, hwm=hwm), \
                 mock.patch.object(process, 'proc_identity', return_value=identity()), \
                 mock.patch.object(Path, 'read_text', return_value=status_text(rss, hwm)), \
                 self.assertRaises((KeyError, ValueError)):
                channel.sample(child)

    def test_alive_unreadable_procfs_is_not_zero_memory(self):
        channel, child, _ = self.bound()
        with mock.patch.object(process, 'proc_identity', side_effect=FileNotFoundError('owned path vanished')), \
             self.assertRaises(FileNotFoundError):
            channel.sample(child)

    def test_confirmed_exit_during_procfs_read_has_explicit_exit_result(self):
        channel, child, _ = self.bound()
        child.poll = mock.Mock(side_effect=[None, 0])
        with mock.patch.object(process, 'proc_identity', side_effect=FileNotFoundError('exited')), \
             self.assertRaises(process.OwnedChildExited):
            channel.sample(child)

    def test_unverified_or_different_child_cannot_be_sampled(self):
        channel, child, packet = self.channel()
        with self.assertRaises(ValueError):
            channel.sample(child)
        channel.binding, channel.packet, channel.child_pid = identity(), packet, 5
        child.pid = 6
        with self.assertRaises(ValueError):
            channel.sample(child)

    def test_release_waits_for_identity_and_memory_budget_callback(self):
        channel, child, packet = self.channel(); channel.after_spawn()
        sequence = []
        def read(fd, deadline, callback):
            callback(); sequence.append('packet')
            return json.dumps(packet)
        def budget(memory):
            sequence.append('poll' if memory is None else 'memory_checked')
        with mock.patch.object(process, '_read_line', side_effect=read), \
             mock.patch.object(channel, 'sample', return_value={'VmRSS': 12288, 'VmHWM': 16384}), \
             mock.patch.object(process, '_write_line', side_effect=lambda fd, nonce: sequence.append('release')):
            result = channel.accept(child, poll_callback=budget)
        self.assertEqual(sequence, ['poll', 'packet', 'memory_checked', 'release'])
        self.assertEqual(result['packet'], packet)
        self.assertEqual(result['initial_memory']['VmHWM'], 16384)

    def test_failed_memory_budget_never_releases_child(self):
        channel, child, packet = self.channel(); channel.after_spawn()
        error = RuntimeError('original RSS guard exceeded')
        def budget(memory):
            if memory is not None: raise error
        with mock.patch.object(process, '_read_line', return_value=json.dumps(packet)), \
             mock.patch.object(channel, 'sample', return_value={'VmRSS': 12, 'VmHWM': 16}), \
             mock.patch.object(process, '_write_line') as write, self.assertRaises(RuntimeError) as caught:
            channel.accept(child, poll_callback=budget)
        self.assertIs(caught.exception, error); write.assert_not_called()

    def test_handshake_duplicate_JSON_and_wrong_packet_rejected_before_release(self):
        for line in ('{"nonce":"x","nonce":"y"}', '{}', 'NaN'):
            with self.subTest(line=line):
                channel, child, _ = self.channel(); channel.after_spawn()
                with mock.patch.object(process, '_read_line', return_value=line), \
                     mock.patch.object(process, '_write_line') as write, self.assertRaises(ValueError):
                    channel.accept(child)
                write.assert_not_called()

    def test_real_pipe_descriptors_closed_after_spawn_and_finally(self):
        channel, _, _ = self.channel()
        all_fds = set(channel.descriptors); passed = set(channel.pass_fds)
        self.assertEqual(len(all_fds), 4); self.assertEqual(len(passed), 2)
        env = channel.child_env({'OTHER': 'kept'})
        self.assertEqual(env['OTHER'], 'kept'); self.assertEqual(env[process.NONCE], channel.nonce)
        channel.after_spawn()
        self.assertEqual(channel.descriptors, all_fds-passed)
        channel.close(); channel.close()
        self.assertFalse(channel.descriptors)
        for fd in all_fds:
            with self.assertRaises(OSError) as caught: os.fstat(fd)
            self.assertEqual(caught.exception.errno, errno.EBADF)

    def test_bounded_single_line_pipe_framing(self):
        for payload, accepted in ((b'nonce\n', True), (b'one\ntwo\n', False),
                                  (b'no newline', False), (b'x'*4096+b'\n', False)):
            with self.subTest(length=len(payload)):
                read, write = os.pipe()
                try:
                    os.write(write, payload); os.close(write); write = None
                    if accepted:
                        self.assertEqual(process._read_line(read, process.time.monotonic()+1), 'nonce')
                    else:
                        with self.assertRaises(ValueError):
                            process._read_line(read, process.time.monotonic()+1)
                finally:
                    os.close(read)
                    if write is not None: os.close(write)

    def test_timeout_is_bounded_and_callback_exception_propagates(self):
        with self.assertRaises(TimeoutError):
            process._read_line(-1, process.time.monotonic()-1)
        error = KeyboardInterrupt('budget read interrupted')
        def interrupt(): raise error
        with self.assertRaises(KeyboardInterrupt) as caught:
            process._read_line(-1, process.time.monotonic()+1, interrupt)
        self.assertIs(caught.exception, error)

    def test_worker_announces_then_waits_and_closes_both_inherited_descriptors(self):
        nonce = 'a'*64; calls = []
        env = {process.READY_FD: '10', process.RELEASE_FD: '11', process.NONCE: nonce}
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(process, 'own_identity', return_value=parent()), \
             mock.patch.object(process, 'sha', return_value='b'*64), \
             mock.patch.object(process, '_write_line', side_effect=lambda fd, text: calls.append(('write', fd))), \
             mock.patch.object(process, '_read_line', side_effect=lambda fd, deadline: (calls.append(('read', fd)), nonce)[1]), \
             mock.patch.object(process.os, 'close', side_effect=lambda fd: calls.append(('close', fd))):
            process.announce_worker_from_environment(__file__)
        self.assertEqual(calls, [('write', 10), ('close', 10), ('read', 11), ('close', 11)])

    def test_worker_wrong_release_and_identity_failure_close_descriptors(self):
        env = {process.READY_FD: '10', process.RELEASE_FD: '11', process.NONCE: 'a'*64}
        for error in (None, OSError('self identity unreadable')):
            with self.subTest(error=error), mock.patch.dict(os.environ, env), \
                 mock.patch.object(process, 'own_identity', side_effect=error, return_value=parent()), \
                 mock.patch.object(process, 'sha', return_value='b'*64), \
                 mock.patch.object(process, '_write_line'), \
                 mock.patch.object(process, '_read_line', return_value='wrong'), \
                 mock.patch.object(process.os, 'close') as close, \
                 self.assertRaises(ValueError if error is None else OSError):
                process.announce_worker_from_environment(__file__)
            self.assertEqual(sorted(call.args[0] for call in close.call_args_list), [10, 11])

    def test_proc_stat_parsing_handles_spaces_and_parentheses_in_comm(self):
        fields = ['S', '420002']+['0']*17+['123456']
        self.assertEqual(process.parse_stat('420005 (python (owned) child) '+' '.join(fields)),
                         {'pid': 420005, 'ppid': 420002, 'starttime_ticks': 123456})
        with self.assertRaises(ValueError):
            process.parse_status('Pid: 5\nPid: 6\n')


if __name__ == '__main__':
    unittest.main()
