#!/usr/bin/env python3
"""Read a connected Motorola donor's software identity without changing it.

This does not infer panel labels, connector pinouts, individual cells or CAD
dimensions from Android properties. Use an explicitly selected serial when
more than one authorized Motorola device is connected. Raw serials are not
written to the evidence file. Select the existing local ADB server explicitly
with --adb-server-port; this collector sends no server restart or port-scan commands.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'integration'))
from product_interfaces import interface_contract_sha256
DESIGN_FILES = ('design/product_geometry.json', 'design/product_interfaces.json')
DEFAULT_ADB_SERVER_PORT = 5037
ADB_SERVER_HOST = '127.0.0.1'

PROPERTIES = (
    'ro.product.manufacturer', 'ro.product.brand', 'ro.product.model',
    'ro.product.device', 'ro.product.board', 'ro.product.name',
    'ro.boot.hardware.sku', 'ro.boot.hwrev', 'ro.build.fingerprint',
    'ro.build.version.release', 'ro.build.version.security_patch',
    'sys.usb.config', 'sys.usb.state',
)


class AdbCommandError(RuntimeError):
    def __init__(self, returncode, stdout='', stderr='', timed_out=False):
        super().__init__('adb command failed; no identity inferred')
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr
        self.timed_out = timed_out


class CommandOutput(str):
    """Keep the existing text API while retaining successful process stderr."""
    def __new__(cls, stdout, stderr):
        value = super().__new__(cls, stdout)
        value.stderr = stderr
        return value


def port_number(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).isascii() or not str(value).isdecimal():
        raise ValueError('ADB server port must be an integer from 1 to 65535')
    port = int(value)
    if not 1 <= port <= 65535:
        raise ValueError('ADB server port must be an integer from 1 to 65535')
    return port


def adb_global_args(adb_server_port: int) -> list[str]:
    # An explicit host also prevents ANDROID_ADB_SERVER_ADDRESS from silently
    # sending a requested local port to a different host.
    return ['-H', ADB_SERVER_HOST, '-P', str(port_number(adb_server_port))]


def adb_transport_identity(adb: str, adb_server_port: int) -> dict:
    resolved = shutil.which(adb)
    result = {'adb_executable_requested': str(adb), 'adb_executable_path': None,
              'adb_executable_sha256': None, 'server_host': ADB_SERVER_HOST,
              'server_port': port_number(adb_server_port),
              'global_args': adb_global_args(adb_server_port),
              'selected_transport_id_before': None,
              'selected_transport_id_after': None,
              'selected_transport_id_unchanged': None}
    if resolved is not None:
        path = Path(resolved).resolve()
        result['adb_executable_path'] = str(path)
        try:
            result['adb_executable_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            result['adb_executable_hash_error'] = type(exc).__name__
    return result


def command(adb: str, args: list[str], *, adb_server_port: int = DEFAULT_ADB_SERVER_PORT) -> str:
    try:
        proc = subprocess.run([adb, *adb_global_args(adb_server_port), *args],
                              capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired as exc:
        # TimeoutExpired may carry bytes even when subprocess.run used text=True.
        def text_value(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
        raise AdbCommandError(None, text_value(exc.stdout), text_value(exc.stderr), timed_out=True) from exc
    if proc.returncode:
        raise AdbCommandError(proc.returncode, proc.stdout, proc.stderr)
    return CommandOutput(proc.stdout, proc.stderr)


def commit_design_sha256(root: Path, commit: str) -> dict:
    result = {}
    for name in DESIGN_FILES:
        value = subprocess.run(['git', '-C', str(root), 'show', commit+':'+name],
                               capture_output=True, timeout=10)
        result[name] = hashlib.sha256(value.stdout).hexdigest() if value.returncode == 0 else None
    return result


def design_identity(root: Path = ROOT) -> dict:
    """Record exact inputs; a missing Git checkout is reported rather than invented."""
    root = Path(root).resolve()
    files = {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
             for name in DESIGN_FILES if (root/name).is_file()}
    try:
        head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, timeout=10)
        commit = head.stdout.strip() if head.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    try:
        committed = commit_design_sha256(root, commit) if commit else {}
    except (OSError, subprocess.TimeoutExpired):
        committed = {}
    try:
        contract = interface_contract_sha256(json.loads((root/'design/product_interfaces.json').read_text()))
    except (OSError, ValueError, TypeError):
        contract = None
    return {'git_commit': commit, 'files_sha256': files,
            'commit_files_sha256': committed, 'inputs_match_commit': files == committed if committed else None,
            'interface_contract_sha256': contract,
            'interface_contract_source_sha256': hashlib.sha256((ROOT/'integration/product_interfaces.py').read_bytes()).hexdigest(),
            'complete': commit is not None and len(files) == len(DESIGN_FILES) and contract is not None}


def connected_devices(text: str) -> list[tuple[str, str]]:
    result = []
    for line in text.splitlines():
        row = line.split()
        if len(row) >= 2 and row[0] not in ('List', '*'):
            result.append((row[0], row[1]))
    if len({serial for serial, _ in result}) != len(result):
        raise ValueError('duplicate ADB serial in inventory')
    return result


def inventory_transport_ids(text: str) -> dict[str, str | None]:
    """Retain inventory identifiers as reported, without inferring USB hardware."""
    result = {}
    for line in text.splitlines():
        row = line.split()
        if len(row) >= 2 and row[0] not in ('List', '*'):
            ids = [value.split(':', 1)[1] for value in row[2:] if value.startswith('transport_id:')]
            if len(ids) > 1 or (ids and (not ids[0].isascii() or not ids[0].isdecimal() or int(ids[0]) == 0)):
                raise ValueError('invalid or repeated ADB transport ID in inventory')
            result[row[0]] = ids[0] if ids else None
    return result


def select_donor(adb: str, devices: list[tuple[str, str]], serial: str | None, run=None,
                 *, adb_server_port: int = DEFAULT_ADB_SERVER_PORT) -> str | None:
    run = run or (lambda args: command(adb, args, adb_server_port=adb_server_port))
    authorized = [item for item, state in devices if state == 'device']
    if serial is not None:
        if serial not in authorized:
            raise ValueError('selected device is not connected and authorized')
        candidates = [serial]
    else:
        candidates = authorized
    motorola = []
    for item in candidates:
        brand = run(['-s', item, 'shell', 'getprop', 'ro.product.brand']).strip().lower()
        maker = run(['-s', item, 'shell', 'getprop', 'ro.product.manufacturer']).strip().lower()
        if brand == 'motorola' or maker in ('motorola', 'motorola mobility', 'motorola mobility llc', 'motorola mobility, llc'):
            motorola.append(item)
    if serial is not None and not motorola:
        raise ValueError('selected device does not identify as Motorola; no donor inference')
    if len(motorola) > 1:
        raise ValueError('multiple Motorola devices connected; select one with --serial')
    return motorola[0] if motorola else None


def capture(adb: str, serial: str | None = None, root: Path = ROOT,
            specimen_id: str | None = None,
            *, adb_server_port: int = DEFAULT_ADB_SERVER_PORT) -> dict:
    adb_server_port = port_number(adb_server_port)
    transport = adb_transport_identity(adb, adb_server_port)
    records, devices = [], []

    def run(args):
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        tick = time.monotonic()
        # Keep v2 logical args compatible with the existing evidence importer;
        # global args document the actual subprocess prefix separately.
        entry = {'args': args, 'adb_global_args': adb_global_args(adb_server_port),
                 'started_utc': started}
        try:
            result = command(adb, args, adb_server_port=adb_server_port)
            entry.update(returncode=0, stdout_text=result, stderr_text=getattr(result, 'stderr', ''), timed_out=False)
            return result
        except (OSError, RuntimeError) as exc:
            entry.update(returncode=getattr(exc, 'returncode', None),
                         stdout_text=getattr(exc, 'stdout', ''),
                         stderr_text=getattr(exc, 'stderr', ''),
                         error_type=type(exc).__name__,
                         timed_out=getattr(exc, 'timed_out', False))
            raise
        finally:
            entry['elapsed_seconds'] = time.monotonic()-tick
            records.append(entry)

    before = design_identity(root)
    report = {
        'schema': 'razr-donor-readback-v2',
        'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'read-only Android software identity, not physical part verification',
        'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'adb_transport': transport,
        'design_binding': before,
        'specimen_id': specimen_id,
        'device_inventory': [],
        'device_inventory_after': None,
        'selected_donor_connected': False,
        'software_identity_complete': False,
        'physical_module_identified': False,
        'physical_board_revision': None,
        'physical_panel_label': None,
        'physical_cell_labels': None,
        'connector_pinmap': None,
        'dimensions_measured': False,
        'phone_function_verified': False,
    }
    selected = None
    try:
        initial_inventory = run(['devices', '-l'])
        devices = connected_devices(initial_inventory)
        initial_transport_ids = inventory_transport_ids(initial_inventory)
        report['device_inventory'] = [
            {'serial_sha256': hashlib.sha256(s.encode()).hexdigest(), 'state': state,
             'transport_id': initial_transport_ids.get(s)}
            for s, state in devices]
        selected = select_donor(adb, devices, serial, run, adb_server_port=adb_server_port)
        report['capture_status'] = 'no_authorized_motorola' if selected is None else 'reading'
        if selected is not None:
            report['selected_serial_sha256'] = hashlib.sha256(selected.encode()).hexdigest()
            transport['selected_transport_id_before'] = initial_transport_ids.get(selected)
            report['properties'] = {}
            for key in PROPERTIES:
                report['properties'][key] = run(['-s', selected, 'shell', 'getprop', key]).strip() or None
            final_inventory = run(['devices', '-l'])
            final_devices = connected_devices(final_inventory)
            final_transport_ids = inventory_transport_ids(final_inventory)
            report['device_inventory_after'] = [
                {'serial_sha256': hashlib.sha256(s.encode()).hexdigest(), 'state': state,
                 'transport_id': final_transport_ids.get(s)}
                for s, state in final_devices]
            transport['selected_transport_id_after'] = final_transport_ids.get(selected)
            if transport['selected_transport_id_before'] is not None and transport['selected_transport_id_after'] is not None:
                transport['selected_transport_id_unchanged'] = (transport['selected_transport_id_before'] == transport['selected_transport_id_after'])
            report['selected_donor_connected'] = (selected, 'device') in final_devices
            # End-of-read inventory must be retained and redacted as well.
            devices = list(dict.fromkeys(devices + final_devices))
            report['software_identity_complete'] = (report['selected_donor_connected']
                and transport['selected_transport_id_unchanged'] is not False) and all(
                report['properties'].get(k) for k in ('ro.product.model', 'ro.build.fingerprint'))
            report['capture_status'] = 'complete' if report['software_identity_complete'] else 'incomplete_or_disconnected'
            if transport['selected_transport_id_unchanged'] is False:
                report['capture_status'] = 'transport_changed_during_capture'
    except (OSError, RuntimeError, ValueError) as exc:
        report['capture_status'] = 'capture_error'
        report['error_type'] = type(exc).__name__
        report['failure_reason'] = str(exc) if isinstance(exc, ValueError) else 'ADB command failed; inspect the redacted command record'
        # Error messages from ADB can contain a serial or host path. The command
        # transcript retains redacted process output; no unfiltered exception text.
    report['design_inputs_unchanged'] = design_identity(root) == before
    sensitive = {s for s, _ in devices}
    if serial:
        sensitive.add(serial)
    for record in records:
        for key in ('stdout_text', 'stderr_text'):
            value = record[key]
            # An inventory failure may still emit serials before selection.
            if key == 'stdout_text' and record['args'] == ['devices', '-l']:
                # Redaction must still work when a duplicate inventory caused
                # the stricter identity parser to reject the observation.
                sensitive.update(row[0] for line in value.splitlines()
                                 if len(row := line.split()) >= 2 and row[0] not in ('List', '*'))
            for raw in sorted(sensitive, key=len, reverse=True):
                value = value.replace(raw, 'sha256:'+hashlib.sha256(raw.encode()).hexdigest())
            record[key] = value
        record['args'] = [
            'sha256:'+hashlib.sha256(value.encode()).hexdigest() if i and record['args'][i-1] == '-s' else value
            for i, value in enumerate(record['args'])]
    report['command_records'] = records
    report['transcript_redaction'] = 'ADB serials replaced with SHA256; retained stdout text is otherwise unparsed command output'
    report['completed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=shutil.which('adb'))
    parser.add_argument('--adb-server-port', type=port_number, default=DEFAULT_ADB_SERVER_PORT,
                        help='existing local ADB server port; default 5037, no fallback port scan')
    parser.add_argument('--serial')
    parser.add_argument('--repo-root', type=Path, default=ROOT)
    parser.add_argument('--specimen-id', help='operator label for this physical specimen; not a part identity claim')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.adb:
        parser.error('adb is not available; provide its existing executable with --adb')
    if args.output.exists():
        parser.error('use a new output filename to retain previous observations')
    result = capture(args.adb, args.serial, args.repo_root, args.specimen_id,
                     adb_server_port=args.adb_server_port)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(args.output),
                      'selected_donor_connected': result['selected_donor_connected']}))
    raise SystemExit(0 if result['software_identity_complete'] and result['design_inputs_unchanged'] else 2)


if __name__ == '__main__':
    main()
