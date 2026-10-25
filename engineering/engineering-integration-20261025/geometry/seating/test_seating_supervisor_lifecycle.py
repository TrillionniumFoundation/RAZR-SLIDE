"""Exact supervisor AST with synthetic children; never starts CAD or Popen.

The shared helper's independent tests cover namespace identities. These cases
cover this SEATING adapter's cleanup and original-limit release decisions.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent
HEAD = '042b768903cccbd7a0995317c8598401e0318e2a'


class FakeExited(RuntimeError):
    pass


class FakeChild:
    pid = 424242

    def __init__(self):
        self.returncode = None
        self.wait_count = 0
        self.wait_outcomes = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_count += 1
        if self.wait_outcomes:
            result = self.wait_outcomes.pop(0)
            if isinstance(result, BaseException):
                raise result
            self.returncode = result
        if self.returncode is None:
            raise AssertionError('live fake child was not stopped before wait')
        return self.returncode


class FakeChannel:
    pass_fds = (101, 102)

    def __init__(self, run):
        self.run = run
        self.closed = self.after_spawn_called = self.released = False
        self.sample_count = 0

    def child_env(self, env):
        return {**env, 'SYNTHETIC_OWNED_CHILD_CHANNEL': 'true'}

    def after_spawn(self):
        self.after_spawn_called = True

    def accept(self, child, timeout_seconds, poll_callback):
        if self.run.mapping_error is not None:
            raise self.run.mapping_error
        poll_callback(None)
        memory = {'VmRSS': self.run.initial_rss, 'VmHWM': self.run.initial_rss}
        poll_callback(memory)
        self.released = True
        return {'packet': {'synthetic': True}, 'parent_identity': {'synthetic': True},
                'verified_binding': {'synthetic': True}, 'initial_memory': memory}

    def sample(self, child):
        self.sample_count += 1
        if self.run.exit_race:
            child.returncode = 0
            raise FakeExited('synthetic child exited during bound sample')
        if self.run.sample_error is not None:
            raise self.run.sample_error
        raise AssertionError('test must end the synthetic live monitoring loop')

    def close(self):
        self.closed = True


class FakeRun:
    def __init__(self, folder, *, mapping_error=None, sample_error=None,
                 first_child_save_error=None, popen_error=None, resource_error=None,
                 initial_rss=32*2**20, exit_race=False):
        self.folder, self.output = folder, folder/'output'
        self.mapping_error, self.sample_error = mapping_error, sample_error
        self.first_child_save_error, self.popen_error = first_child_save_error, popen_error
        self.resource_error, self.initial_rss, self.exit_race = resource_error, initial_rss, exit_race
        self.child, self.channel = FakeChild(), FakeChannel(self)
        self.signals = []; self.saves = []; self.resource_calls = self.launches = 0
        self.injected_save_error = False
        fixture = folder/'synthetic-source'; fixture.mkdir()
        source = fixture/'supervise_seating_native.py'
        source.write_bytes((HERE/'supervise_seating_native.py').read_bytes())
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        self.manifest = folder/'manifest.json'
        sources = {source.name: sha(source)}
        self.manifest.write_text(json.dumps({name: {'sha256': digest} for name, digest in sources.items()}))
        self.manifest_sha = sha(self.manifest)
        worker = SimpleNamespace(HERE=fixture, ROOT=folder/'fake-repository', DEFAULT_HEAD=HEAD,
            adapter_identity=lambda: sources,
            postguard=SimpleNamespace(check_environment=SimpleNamespace(inspect_environment=lambda root:
                {'passed': True, 'checked_package_count': 43, 'synthetic': True})))
        functions = [node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef)]
        fake_os = SimpleNamespace(environ={}, killpg=self.killpg, fsync=os.fsync, replace=os.replace)
        fake_subprocess = SimpleNamespace(Popen=self.launch, STDOUT=subprocess.STDOUT,
            TimeoutExpired=subprocess.TimeoutExpired,
            check_output=lambda command, **kwargs: HEAD+'\n' if 'rev-parse' in command else '')
        fake_owned = SimpleNamespace(__file__=str(fixture/'owned_process.py'), OwnedChildExited=FakeExited,
                                     OwnedChildChannel=lambda path: self.channel)
        self.namespace = {'argparse': argparse, 'dt': datetime, 'hashlib': hashlib, 'json': json,
            'os': fake_os, 'Path': Path, 'signal': signal, 'subprocess': fake_subprocess, 'time': time,
            'worker': worker, 'reader': SimpleNamespace(), 'owned_process': fake_owned,
            '__file__': str(source)}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), self.namespace)
        original_save = self.namespace['save']
        def save(path, state):
            if (path.name == 'controller.json' and state.get('worker_started') is True
                    and not self.injected_save_error and self.first_child_save_error is not None):
                self.injected_save_error = True
                raise self.first_child_save_error
            if path.name == 'controller.json':
                self.saves.append(json.loads(json.dumps(state)))
            original_save(path, state)
        self.namespace['save'] = save
        self.namespace['snapshot'] = self.snapshot

    def snapshot(self, path):
        self.resource_calls += 1
        if self.resource_calls == 2 and self.resource_error is not None:
            raise self.resource_error
        return {'f_bavail_bytes': 1024*2**20, 'estimated_unreclaimable_bytes': 2*2**30}

    def launch(self, *args, **kwargs):
        self.launches += 1
        if self.popen_error is not None:
            raise self.popen_error
        if kwargs.get('pass_fds') != self.channel.pass_fds:
            raise AssertionError('owned pipe descriptors were not passed to the intended child')
        return self.child

    def killpg(self, pid, value):
        if pid != self.child.pid:
            raise AssertionError('signal targets an unrelated synthetic process group')
        self.signals.append(value)
        self.child.returncode = -int(value)

    def run(self):
        return self.namespace['main'](['--output-directory', str(self.output), '--expected-head', HEAD,
            '--prepared-manifest', str(self.manifest), '--prepared-sha256', self.manifest_sha])


class SeatingSupervisorLifecycleTests(unittest.TestCase):
    def scenario(self, **kwargs):
        temporary = tempfile.TemporaryDirectory(prefix='razr-seating-r3-lifecycle-', dir='/tmp')
        self.addCleanup(temporary.cleanup)
        return FakeRun(Path(temporary.name), **kwargs)

    def require_stopped(self, run, error, reason='supervisor_exception_cleanup'):
        self.assertEqual(run.run(), 2)
        state = run.saves[-1]
        self.assertFalse(state['completed'])
        self.assertEqual(state['resource_stop_reason'], reason)
        self.assertEqual(state['supervisor_exception'], {'type': type(error).__name__, 'message': str(error)})
        self.assertEqual(run.launches, 1)
        self.assertEqual(run.signals, [signal.SIGTERM])
        self.assertGreaterEqual(run.child.wait_count, 1)
        self.assertTrue(run.channel.closed)
        return state

    def test_mapping_rejection_stops_before_native_release(self):
        error = ValueError('synthetic nonce/PID/starttime identity mismatch')
        run = self.scenario(mapping_error=error)
        state = self.require_stopped(run, error)
        self.assertFalse(run.channel.released)
        self.assertFalse(state['owned_child_identity_verified'])
        self.assertEqual(run.channel.sample_count, 0)

    def test_live_worker_lost_RSS_or_changed_identity_cleans_up(self):
        for error in (OSError('synthetic live child RSS unreadable'),
                      ValueError('synthetic PID/starttime identity changed'),
                      FakeExited('synthetic exit claim while child is still alive')):
            with self.subTest(error=str(error)):
                run = self.scenario(sample_error=error)
                state = self.require_stopped(run, error)
                self.assertTrue(state['owned_child_identity_verified'])
                self.assertTrue(run.channel.released)

    def test_first_post_Popen_receipt_failure_cleans_up(self):
        for error in (OSError('synthetic first child receipt write failed'),
                      KeyboardInterrupt('synthetic first child receipt interrupted')):
            with self.subTest(error=type(error).__name__):
                run = self.scenario(first_child_save_error=error)
                self.require_stopped(run, error)
                self.assertFalse(run.channel.released)

    def test_Popen_failure_closes_owned_descriptors_without_started_child(self):
        run = self.scenario(popen_error=OSError('synthetic Popen refused'))
        self.assertEqual(run.run(), 2)
        state = run.saves[-1]
        self.assertFalse(state['worker_started'])
        self.assertFalse(state['completed'])
        self.assertNotIn('pid', state)
        self.assertEqual(run.signals, [])
        self.assertEqual(run.child.wait_count, 0)
        self.assertTrue(run.channel.closed)

    def test_handshake_resource_telemetry_failure_cleans_up(self):
        for error in (OSError('synthetic resource telemetry failed'),
                      KeyboardInterrupt('synthetic monitored interruption')):
            with self.subTest(error=type(error).__name__):
                run = self.scenario(resource_error=error)
                self.require_stopped(run, error)
                self.assertFalse(run.channel.released)

    def test_original_RSS_limit_applies_before_native_release(self):
        run = self.scenario(initial_rss=1536*2**20+1)
        self.assertEqual(run.run(), 2)
        state = run.saves[-1]
        self.assertFalse(state['completed'])
        self.assertEqual(state['resource_stop_reason'], 'worker_peak_RSS_guard')
        self.assertFalse(state['owned_child_identity_verified'])
        self.assertFalse(run.channel.released)
        self.assertEqual(run.signals, [signal.SIGTERM])
        self.assertTrue(run.channel.closed)

    def test_actual_exit_race_is_reaped_but_never_promoted_without_full_report(self):
        run = self.scenario(exit_race=True)
        self.assertEqual(run.run(), 2)
        state = run.saves[-1]
        self.assertIsNone(state['resource_stop_reason'])
        self.assertEqual(state['worker_exit_code'], 0)
        self.assertFalse(state['completed'])
        self.assertEqual(run.signals, [])
        self.assertTrue(run.channel.closed)

    def test_TERM_KILL_exit_races_are_reaped(self):
        run = self.scenario()
        run.child.wait_outcomes = [subprocess.TimeoutExpired('synthetic child', 5), 0]
        def disappeared(pid, value):
            self.assertEqual(pid, run.child.pid)
            run.signals.append(value)
            raise ProcessLookupError('synthetic process already exited')
        run.namespace['os'].killpg = disappeared
        self.assertEqual(run.namespace['terminate'](run.child), 0)
        self.assertEqual(run.signals, [signal.SIGTERM, signal.SIGKILL])
        self.assertEqual(run.child.wait_count, 2)


if __name__ == '__main__':
    unittest.main()
