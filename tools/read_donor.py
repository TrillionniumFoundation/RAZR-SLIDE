#!/usr/bin/env python3
"""Read a connected Motorola donor's software identity without changing it.

This does not infer panel labels, connector pinouts, individual cells or CAD
dimensions from Android properties. Use an explicitly selected serial when
more than one authorized Motorola device is connected. Raw serials are not
written to the evidence file.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PROPERTIES = (
    'ro.product.manufacturer', 'ro.product.brand', 'ro.product.model',
    'ro.product.device', 'ro.product.board', 'ro.product.name',
    'ro.boot.hardware.sku', 'ro.boot.hwrev', 'ro.build.fingerprint',
    'ro.build.version.release', 'ro.build.version.security_patch',
    'sys.usb.config', 'sys.usb.state',
)


def command(adb: str, args: list[str]) -> str:
    proc = subprocess.run([adb, *args], capture_output=True, text=True, timeout=15)
    if proc.returncode:
        raise RuntimeError(f'adb command failed ({proc.returncode}); no identity inferred')
    return proc.stdout.strip()


def connected_devices(text: str) -> list[tuple[str, str]]:
    result = []
    for line in text.splitlines():
        row = line.split()
        if len(row) >= 2 and row[0] not in ('List', '*'):
            result.append((row[0], row[1]))
    if len({serial for serial, _ in result}) != len(result):
        raise ValueError('duplicate ADB serial in inventory')
    return result


def select_donor(adb: str, devices: list[tuple[str, str]], serial: str | None) -> str | None:
    authorized = [item for item, state in devices if state == 'device']
    if serial is not None:
        if serial not in authorized:
            raise ValueError('selected device is not connected and authorized')
        candidates = [serial]
    else:
        candidates = authorized
    motorola = []
    for item in candidates:
        brand = command(adb, ['-s', item, 'shell', 'getprop', 'ro.product.brand'])
        maker = command(adb, ['-s', item, 'shell', 'getprop', 'ro.product.manufacturer'])
        if 'motorola' in (brand + ' ' + maker).lower():
            motorola.append(item)
    if serial is not None and not motorola:
        raise ValueError('selected device does not identify as Motorola; no donor inference')
    if len(motorola) > 1:
        raise ValueError('multiple Motorola devices connected; select one with --serial')
    return motorola[0] if motorola else None


def capture(adb: str, serial: str | None = None) -> dict:
    devices = connected_devices(command(adb, ['devices', '-l']))
    selected = select_donor(adb, devices, serial)
    report = {
        'schema': 'razr-donor-readback-v1',
        'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'read-only Android software identity, not physical part verification',
        'device_inventory': [
            {'serial_sha256': hashlib.sha256(s.encode()).hexdigest(), 'state': state}
            for s, state in devices
        ],
        'selected_donor_connected': selected is not None,
        'physical_module_identified': False,
        'physical_board_revision': None,
        'physical_panel_label': None,
        'physical_cell_labels': None,
        'connector_pinmap': None,
        'dimensions_measured': False,
        'phone_function_verified': False,
    }
    if selected is not None:
        report['selected_serial_sha256'] = hashlib.sha256(selected.encode()).hexdigest()
        report['properties'] = {
            key: command(adb, ['-s', selected, 'shell', 'getprop', key]) or None
            for key in PROPERTIES
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=shutil.which('adb'))
    parser.add_argument('--serial')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.adb:
        parser.error('adb is not available; provide its existing executable with --adb')
    if args.output.exists():
        parser.error('use a new output filename to retain previous observations')
    result = capture(args.adb, args.serial)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(args.output),
                      'selected_donor_connected': result['selected_donor_connected']}))
    raise SystemExit(0 if result['selected_donor_connected'] else 2)


if __name__ == '__main__':
    main()
