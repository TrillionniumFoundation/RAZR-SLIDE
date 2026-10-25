"""Pure fake-child regressions for the exact SLIDE supervisor functions.

No actual Popen, CAD import, process signal, production inputs or factorization.
Only the named source functions are compiled from their AST into a fake runtime.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest


HERE = Path(__file__).resolve().parent
HEAD = '042b768903cccbd7a0995317c8598401e0318e2a'


class FakeChild:
    pid = 424242

    def __init__(self):
        self.returncode = None
        self.wait_calls = 0
        self.wait_outcomes = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls += 1
        if self.wait_outcomes:
            result = self.wait_outcomes.pop(0)
            if isinstance(result, BaseException):
                raise result
            self.returncode = result
        if self.returncode is None:
            raise AssertionError('a live fake child was not stopped before wait')
        return self.returncode


class FakeRun:
    def __init__(self, folder, *, source=None, popen_error=None,
                 first_child_save_error=None, runtime_error=None,
                 after_spawn_error=None, handshake_error=None, sample_error=None):
        self.source = Path(source) if source else HERE/'supervise_slide_native.py'
        self.folder = folder
        self.output = folder/'output'
        self.child = FakeChild()
        self.popen_error = popen_error
        self.first_child_save_error = first_child_save_error
        self.runtime_error = runtime_error
        self.after_spawn_error = after_spawn_error
        self.handshake_error = handshake_error
        self.sample_error = sample_error
        self.popen_calls = 0
        self.signals = []
        self.controller_saves = 0
        self.resource_calls = 0
        self.saved_controllers = []
        run = self
        class FakeChannel:
            pass_fds = (10, 11)
            def __init__(self, path):
                self.descriptors = {10, 11, 12, 13}
                self.closed = False
                run.channel = self
            def child_env(self, env):
                return env
            def after_spawn(self):
                if run.after_spawn_error is not None:
                    raise run.after_spawn_error
            def accept(self, child, timeout_seconds, poll_callback):
                poll_callback(None)
                if run.handshake_error is not None:
                    raise run.handshake_error
                memory = {'VmRSS': 1024, 'VmHWM': 1024}
                poll_callback(memory)
                return {'packet': {}, 'initial_memory': memory}
            def sample(self, child):
                if run.sample_error is not None:
                    raise run.sample_error
                return {'VmRSS': 1024, 'VmHWM': 1024}
            def close(self):
                self.descriptors.clear()
                self.closed = True
        sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        worker = types.SimpleNamespace(
            HERE=self.source.parent, ROOT=folder/'fake-repository', DEFAULT_HEAD=HEAD,
            evidence=types.SimpleNamespace(require=require, FALSE_FLAGS=(
                'canonical_execution_checks_passed', 'complete_G2_qualification')),
            source_identity=lambda: {str(self.source): sha(self.source)},
            sha=sha, atomic_json=self.atomic_json, resource_snapshot=self.resources)
        fake_subprocess = types.SimpleNamespace(
            Popen=self.popen, STDOUT=subprocess.STDOUT,
            TimeoutExpired=subprocess.TimeoutExpired,
            check_output=lambda argv, **kwargs: HEAD+'\n' if 'rev-parse' in argv else '')
        functions = [node for node in ast.parse(self.source.read_text()).body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.namespace = {
            '__file__': str(self.source), 'argparse': argparse, 'dt': datetime,
            'json': json, 'os': types.SimpleNamespace(environ={}, killpg=self.killpg),
            'Path': Path, 'signal': signal, 'subprocess': fake_subprocess,
            'sys': sys, 'time': time, 'worker': worker,
            'owned_process': types.SimpleNamespace(OwnedChildChannel=FakeChannel,
                OwnedChildExited=type('OwnedChildExited', (RuntimeError,), {})),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(self.source), 'exec'), self.namespace)

    def atomic_json(self, path, value):
        if path.name == 'controller.json':
            self.controller_saves += 1
            if self.controller_saves == 2 and self.first_child_save_error is not None:
                raise self.first_child_save_error
            self.saved_controllers.append(json.loads(json.dumps(value)))
        path.write_text(json.dumps(value))

    def resources(self, folder):
        self.resource_calls += 1
        if self.resource_calls > 1 and self.runtime_error is not None:
            raise self.runtime_error
        return {'f_bavail_bytes': 500*2**20,
                'estimated_unreclaimable_bytes': 2*2**30,
                'peak_RSS_bytes': 0}

    def popen(self, *args, **kwargs):
        self.popen_calls += 1
        if self.popen_error is not None:
            raise self.popen_error
        return self.child

    def killpg(self, pid, value):
        if pid != self.child.pid:
            raise AssertionError('attempted to signal a different fake process group')
        self.signals.append(value)
        self.child.returncode = -int(value)

    def run(self):
        return self.namespace['main'](['--output', str(self.output), '--expected-head', HEAD])


class SupervisorLifecycleTests(unittest.TestCase):
    def scenario(self, **kwargs):
        temporary = tempfile.TemporaryDirectory(prefix='razr-slide-lifecycle-test-', dir='/tmp')
        self.addCleanup(temporary.cleanup)
        return FakeRun(Path(temporary.name), **kwargs)

    def assert_stopped_original_error(self, run, error):
        with self.assertRaises(type(error)) as caught:
            run.run()
        self.assertIs(caught.exception, error)
        self.assertEqual(run.popen_calls, 1)
        self.assertEqual(run.signals, [signal.SIGTERM])
        self.assertGreaterEqual(run.child.wait_calls, 1)
        self.assertIsNotNone(run.child.returncode)
        final = run.saved_controllers[-1]
        self.assertTrue(final['worker_started'])
        self.assertEqual(final['worker_pid'], run.child.pid)
        self.assertFalse(final['completed'])
        self.assertEqual(final['execution_failure'], type(error).__name__+': '+str(error))
        self.assertTrue(run.channel.closed)
        self.assertFalse(run.channel.descriptors)

    def test_initial_child_receipt_OSError_stops_and_reaps(self):
        error = OSError('first post-Popen receipt failed')
        self.assert_stopped_original_error(self.scenario(first_child_save_error=error), error)

    def test_initial_child_receipt_KeyboardInterrupt_stops_and_reaps(self):
        error = KeyboardInterrupt('first post-Popen receipt interrupted')
        self.assert_stopped_original_error(self.scenario(first_child_save_error=error), error)

    def test_Popen_failure_does_not_record_started_or_PID(self):
        error = OSError('Popen refused')
        run = self.scenario(popen_error=error)
        with self.assertRaises(OSError) as caught:
            run.run()
        self.assertIs(caught.exception, error)
        self.assertEqual(run.signals, [])
        self.assertEqual(run.child.wait_calls, 0)
        final = run.saved_controllers[-1]
        self.assertFalse(final['worker_started'])
        self.assertNotIn('worker_pid', final)
        self.assertFalse(final['completed'])
        self.assertEqual(final['execution_failure'], 'OSError: Popen refused')
        self.assertTrue(run.channel.closed)

    def test_runtime_resource_OSError_preserves_cleanup(self):
        error = OSError('resource snapshot failed')
        self.assert_stopped_original_error(self.scenario(runtime_error=error), error)

    def test_runtime_KeyboardInterrupt_preserves_cleanup(self):
        error = KeyboardInterrupt('runtime interrupted')
        self.assert_stopped_original_error(self.scenario(runtime_error=error), error)

    def test_post_Popen_pipe_close_error_stops_and_reaps(self):
        error = OSError('parent pipe close failed')
        self.assert_stopped_original_error(self.scenario(after_spawn_error=error), error)

    def test_handshake_timeout_stops_reaps_and_closes_all_owned_FDs(self):
        error = TimeoutError('no verified worker packet')
        self.assert_stopped_original_error(self.scenario(handshake_error=error), error)

    def test_alive_unreadable_RSS_stops_reaps_and_closes_all_owned_FDs(self):
        error = FileNotFoundError('owned procfs disappeared while child is alive')
        self.assert_stopped_original_error(self.scenario(sample_error=error), error)

    def test_TERM_exit_race_still_waits_and_reaps(self):
        run = self.scenario()
        def already_exited(pid, value):
            self.assertEqual(pid, run.child.pid)
            run.signals.append(value)
            run.child.returncode = 0
            raise ProcessLookupError('already exited')
        run.namespace['os'].killpg = already_exited
        run.namespace['terminate_group'](run.child)
        self.assertEqual(run.signals, [signal.SIGTERM])
        self.assertEqual(run.child.wait_calls, 1)
        self.assertEqual(run.child.returncode, 0)

    def test_KILL_exit_race_still_reaps_after_TERM_timeout(self):
        run = self.scenario()
        run.child.wait_outcomes = [subprocess.TimeoutExpired('fake child', 5), 0]
        def exits_before_kill(pid, value):
            self.assertEqual(pid, run.child.pid)
            run.signals.append(value)
            if value == signal.SIGKILL:
                raise ProcessLookupError('exited during grace interval')
        run.namespace['os'].killpg = exits_before_kill
        run.namespace['terminate_group'](run.child)
        self.assertEqual(run.signals, [signal.SIGTERM, signal.SIGKILL])
        self.assertEqual(run.child.wait_calls, 2)
        self.assertEqual(run.child.returncode, 0)


if __name__ == '__main__':
    unittest.main()
