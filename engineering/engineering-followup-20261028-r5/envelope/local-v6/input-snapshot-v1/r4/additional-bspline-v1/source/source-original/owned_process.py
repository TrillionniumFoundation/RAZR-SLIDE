"""Bind one owned Popen child to its actual procfs identity before CAD starts.

The procfs PID is read only. All termination and reaping remain the caller's
responsibility through its original Popen handle. Missing or unstable memory
observations are errors, never a zero-RSS observation. This stdlib module is
shared byte-for-byte by the SLIDE and SEATING scratch supervisors.
"""
from __future__ import annotations

import errno
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import select
import time


READY_FD = 'RAZR_OWNED_PROCESS_READY_FD'
RELEASE_FD = 'RAZR_OWNED_PROCESS_RELEASE_FD'
NONCE = 'RAZR_OWNED_PROCESS_NONCE'
KIND = 'razr_owned_child_identity_v1'
MAX_PACKET_BYTES = 4096


class OwnedChildExited(RuntimeError):
    """The original Popen handle observed termination during a sample."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'regular worker source required')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integer(value, name, minimum=1):
    require(type(value) is int and value >= minimum, 'invalid '+name)
    return value


def decimal(text, name, minimum=1):
    require(type(text) is str and text.isascii() and text.isdecimal(), 'invalid '+name)
    value = int(text)
    require(str(value) == text and value >= minimum, 'invalid '+name)
    return value


def parse_status(text):
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition(':')
        if key not in ('Pid', 'PPid', 'NSpid', 'VmRSS', 'VmHWM'):
            continue
        require(separator and key not in result, 'duplicate or malformed procfs '+key)
        parts = value.split()
        if key == 'NSpid':
            require(bool(parts), 'empty procfs namespace PID chain')
            result[key] = [decimal(item, 'namespace PID') for item in parts]
        elif key in ('VmRSS', 'VmHWM'):
            require(len(parts) == 2 and parts[1] == 'kB', 'unexpected procfs memory unit')
            result[key] = decimal(parts[0], key)*1024
        else:
            require(len(parts) == 1, 'invalid procfs '+key)
            result[key] = decimal(parts[0], key, 0 if key == 'PPid' else 1)
    return result


def parse_stat(text):
    left, right = text.find('('), text.rfind(')')
    require(left > 0 and right > left, 'invalid procfs stat record')
    fields = text[right+1:].split()
    require(len(fields) >= 20, 'short procfs stat record')
    return {'pid': decimal(text[:left].strip(), 'stat PID'),
            'ppid': decimal(fields[1], 'stat PPID', 0),
            'starttime_ticks': decimal(fields[19], 'stat starttime')}


def proc_identity(prefix):
    """Read only self or the already reported numeric owned-child path."""
    prefix = Path(prefix)
    status = parse_status((prefix/'status').read_text())
    return {'status': {key: status[key] for key in ('Pid', 'PPid', 'NSpid')},
            'stat': parse_stat((prefix/'stat').read_text()),
            'pid_namespace': os.readlink(prefix/'ns/pid'),
            'pid_for_children_namespace': os.readlink(prefix/'ns/pid_for_children')}


def check_identity(identity, visible_pid):
    require(type(identity) is dict and set(identity) == {
        'status', 'stat', 'pid_namespace', 'pid_for_children_namespace'},
        'incomplete procfs identity')
    status, stat = identity['status'], identity['stat']
    require(type(status) is dict and set(status) == {'Pid', 'PPid', 'NSpid'}
            and type(stat) is dict and set(stat) == {'pid', 'ppid', 'starttime_ticks'},
            'incomplete procfs PID fields')
    for key in ('Pid', 'PPid'):
        integer(status[key], 'status '+key, 0 if key == 'PPid' else 1)
    for key in ('pid', 'ppid', 'starttime_ticks'):
        integer(stat[key], 'stat '+key, 0 if key == 'ppid' else 1)
    chain = status['NSpid']
    require(type(chain) is list and bool(chain), 'missing namespace PID chain')
    for pid in chain:
        integer(pid, 'namespace PID')
    require(status['Pid'] == stat['pid'] == visible_pid == chain[0]
            and status['PPid'] == stat['ppid'], 'inconsistent procfs PID identity')
    for key in ('pid_namespace', 'pid_for_children_namespace'):
        value = identity[key]
        require(type(value) is str and value.startswith('pid:[') and value.endswith(']'),
                'invalid PID namespace link')
        decimal(value[5:-1], 'PID namespace inode')
    return identity


def own_identity():
    visible = os.readlink('/proc/self')
    number = decimal(visible, 'own visible PID')
    actual = check_identity(proc_identity('/proc/self'), number)
    pid, ppid = os.getpid(), os.getppid()
    require(actual['status']['NSpid'][-1] == pid, 'own namespace PID is inconsistent')
    return {'os_getpid': pid, 'os_getppid': ppid, 'proc_self_visible_pid': visible, **actual}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate handshake JSON key')
        result[key] = value
    return result


def _read_line(fd, deadline, callback=None):
    value = bytearray()
    while b'\n' not in value:
        if callback is not None:
            callback()
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('owned child handshake timed out')
        ready, _, _ = select.select([fd], [], [], min(.1, remaining))
        if not ready:
            continue
        data = os.read(fd, MAX_PACKET_BYTES)
        require(bool(data), 'owned child pipe closed before a complete line')
        value.extend(data)
        require(len(value) < MAX_PACKET_BYTES, 'owned child packet is too large')
    require(value.count(b'\n') == 1 and value.endswith(b'\n'),
            'exactly one complete owned child packet required')
    return bytes(value[:-1]).decode('utf-8')


def _write_line(fd, value):
    line = (value+'\n').encode('utf-8')
    require(len(line) < MAX_PACKET_BYTES, 'owned child packet is too large')
    require(os.write(fd, line) == len(line), 'owned child pipe write was incomplete')


def announce_worker_from_environment(source_path):
    """Worker-side handshake; returns only after its parent verifies and releases it."""
    ready = decimal(os.environ.get(READY_FD), 'ready FD', 3)
    release = decimal(os.environ.get(RELEASE_FD), 'release FD', 3)
    require(ready != release, 'distinct ready and release descriptors required')
    nonce = os.environ.get(NONCE)
    require(type(nonce) is str and len(nonce) == 64
            and all(ch in '0123456789abcdef' for ch in nonce), 'invalid handshake nonce')
    try:
        packet = {'kind': KIND, 'nonce': nonce, 'source_sha256': sha(source_path), **own_identity()}
        _write_line(ready, json.dumps(packet, separators=(',', ':'), allow_nan=False))
        os.close(ready); ready = None
        require(_read_line(release, time.monotonic()+10.) == nonce,
                'parent did not send the matching release nonce')
    finally:
        for fd in (ready, release):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as exc:
                    if exc.errno != errno.EBADF:
                        raise


class OwnedChildChannel:
    """Dedicated ready/release pipes and verified RSS sampler for one Popen child."""

    def __init__(self, worker_source_path):
        self.source_path = Path(worker_source_path).resolve()
        self.source_sha256 = sha(self.source_path)
        self.parent = own_identity()
        self.nonce = secrets.token_hex(32)
        self.descriptors = set()
        self.binding = None
        self.packet = None
        self.child_pid = None
        try:
            self.ready_read, self.ready_write = os.pipe()
            self.descriptors.update((self.ready_read, self.ready_write))
            self.release_read, self.release_write = os.pipe()
            self.descriptors.update((self.release_read, self.release_write))
        except BaseException:
            self.close()
            raise

    @property
    def pass_fds(self):
        require({self.ready_write, self.release_read} <= self.descriptors,
                'owned child channels are already closed')
        return (self.ready_write, self.release_read)

    def child_env(self, environment):
        return {**environment, READY_FD: str(self.ready_write),
                RELEASE_FD: str(self.release_read), NONCE: self.nonce}

    def _close(self, fd):
        if fd in self.descriptors:
            try:
                os.close(fd)
            finally:
                self.descriptors.remove(fd)

    def after_spawn(self):
        self._close(self.ready_write)
        self._close(self.release_read)

    def close(self):
        first_error = None
        for fd in tuple(self.descriptors):
            try:
                self._close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF and first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    def _validate_packet(self, packet, child):
        fields = {'kind', 'nonce', 'source_sha256', 'os_getpid', 'os_getppid',
                  'proc_self_visible_pid', 'status', 'stat',
                  'pid_namespace', 'pid_for_children_namespace'}
        require(type(packet) is dict and set(packet) == fields, 'incomplete owned child packet')
        require(packet['kind'] == KIND and packet['nonce'] == self.nonce
                and packet['source_sha256'] == self.source_sha256
                and sha(self.source_path) == self.source_sha256,
                'owned child source or nonce differs')
        integer(packet['os_getpid'], 'child namespace PID')
        integer(packet['os_getppid'], 'child namespace PPID')
        require(packet['os_getpid'] == child.pid and packet['os_getppid'] == self.parent['os_getpid'],
                'packet does not belong to the owned Popen child')
        visible = decimal(packet['proc_self_visible_pid'], 'child visible PID')
        binding = {key: packet[key] for key in ('status', 'stat', 'pid_namespace', 'pid_for_children_namespace')}
        check_identity(binding, visible)
        require(binding['status']['PPid'] == int(self.parent['proc_self_visible_pid'])
                and binding['status']['NSpid'][-1] == child.pid
                and binding['pid_namespace'] == self.parent['pid_namespace']
                and binding['pid_for_children_namespace'] == self.parent['pid_for_children_namespace'],
                'child procfs parent or namespace does not match this supervisor')
        return binding

    def accept(self, child, timeout_seconds=10, poll_callback=None):
        require(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
                and 0 < timeout_seconds <= 10, 'bounded handshake timeout required')
        require(self.binding is None and self.ready_read in self.descriptors,
                'owned child handshake has already been consumed')
        def poll():
            if child.poll() is not None:
                raise OwnedChildExited('owned child exited before its handshake completed')
            if poll_callback is not None:
                poll_callback(None)
        line = _read_line(self.ready_read, time.monotonic()+timeout_seconds, poll)
        self._close(self.ready_read)
        packet = json.loads(line, object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite handshake JSON')))
        self.binding = self._validate_packet(packet, child)
        self.packet, self.child_pid = packet, child.pid
        memory = self.sample(child)
        if poll_callback is not None:
            poll_callback(memory)
        _write_line(self.release_write, self.nonce)
        self._close(self.release_write)
        return {'packet': packet, 'parent_identity': self.parent,
                'verified_binding': self.binding, 'initial_memory': memory}

    def sample(self, child):
        require(self.binding is not None and self.child_pid == child.pid,
                'unverified or different Popen child cannot be sampled')
        if child.poll() is not None:
            raise OwnedChildExited('owned child exited before memory sampling')
        prefix = Path('/proc')/self.packet['proc_self_visible_pid']
        try:
            before = proc_identity(prefix)
            require(before == self.binding, 'owned child identity changed before RSS sampling')
            status = parse_status((prefix/'status').read_text())
            memory = {key: status[key] for key in ('VmRSS', 'VmHWM')}
            require(0 < memory['VmRSS'] <= memory['VmHWM'], 'missing or inconsistent positive child RSS')
            after = proc_identity(prefix)
            require(after == self.binding, 'owned child identity changed after RSS sampling')
            if child.poll() is not None:
                raise OwnedChildExited('owned child exited during memory sampling')
            return memory
        except (OSError, KeyError, ValueError) as exc:
            if child.poll() is not None:
                raise OwnedChildExited('owned child exited while procfs was being read') from exc
            raise
