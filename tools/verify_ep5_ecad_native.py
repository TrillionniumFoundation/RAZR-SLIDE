#!/usr/bin/env python3
"""Execute native KiCad readback/DRC on the current 188 mm research artwork.

The generated board is a continuity research article.  Native DRC does not
assign OEM pins, qualify signal/power behavior, select a supplier stackup, or
authorize manufacture.  Every reported warning/exclusion remains a rejection.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integration'))
import product_ep5_ecad as artwork

HELPER = 'engineering/product-integration-20261018/electrical/verify_native_mini.py'
SOURCES = ('tools/verify_ep5_ecad_native.py', 'integration/product_ep5_ecad.py',
           'integration/product_interfaces.py', 'design/product_routing_ep5.json', HELPER)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_drc(document, exit_code, expected_board, expected_version):
    if not isinstance(document, dict):
        raise ValueError('native DRC object required')
    if document.get('source') not in (str(expected_board), Path(expected_board).name):
        raise ValueError('native DRC belongs to another board')
    if document.get('coordinate_units') != 'mm' or document.get('kicad_version') != expected_version:
        raise ValueError('native DRC units or KiCad version differ')
    counts = {}
    for key in ('violations', 'unconnected_items'):
        if not isinstance(document.get(key), list):
            raise ValueError('native DRC omitted ' + key)
        counts[key] = len(document[key])
    if 'schematic_parity' in document:
        if not isinstance(document['schematic_parity'], list):
            raise ValueError('invalid schematic parity result')
        counts['schematic_parity'] = len(document['schematic_parity'])
    if exit_code != 0 or any(counts.values()):
        raise ValueError('native DRC rejected: exit=' + str(exit_code) + ', counts=' + str(counts))
    return counts


def validate_readback(report, config, board_hashes):
    if report.get('inputs_sha256') != board_hashes or report.get('input_bytes_unchanged') is not True:
        raise ValueError('native board/project identities differ')
    if report.get('project_loaded') is not True:
        raise ValueError('native project settings were not loaded')
    sections = report.get('drc_sections')
    if (report.get('drc_zero_reported_items') is not True or
            report.get('drc_violation_types') != {} or
            not isinstance(sections,list) or not sections or
            any(not isinstance(s,dict) or type(s.get('count')) is not int or s['count'] != 0
                or not isinstance(s.get('kind'),str) or not s['kind'] for s in sections)):
        raise ValueError('the native readback DRC has rejected or incomplete observations')
    if report.get('tracks') != 130 or report.get('footprints') != 2:
        raise ValueError('native complete copper/endpoint inventory differs')
    thickness = report.get('declared_board_thickness_mm')
    if type(thickness) not in (int,float) or not math.isfinite(thickness) or abs(thickness - config['route']['thickness_assumption_mm']) > 1e-12:
        raise ValueError('native board thickness differs')
    sites = report.get('native_pad_readback', [])
    expected = {}
    for row in artwork.channels(config):
        for reference, index in (('JA', 0), ('JB', -1)):
            expected[(reference, row['pin'])] = (row['net'], row['points'][index])
    seen = set()
    for site in sites:
        key = (site.get('reference'), site.get('pad'))
        if key in seen or key not in expected:
            raise ValueError('duplicate or foreign native terminal')
        seen.add(key)
        net, position = expected[key]
        if site.get('net') != net or site.get('size_mm') != [.25, 4.]:
            raise ValueError('native terminal geometry/net differs')
        actual = site.get('position_mm')
        if not isinstance(actual, list) or len(actual) != 2 or any(type(a) not in (int,float) or not math.isfinite(a) or abs(a-b) > 1e-6 for a,b in zip(actual,position)):
            raise ValueError('native terminal position differs')
    if seen != set(expected):
        raise ValueError('native terminal inventory incomplete')
    return {'terminals': len(seen), 'tracks': 130, 'footprints': 2,
            'native_terminal_identities_and_coordinates_verified': True}


def execute(output, expected_head, kicad_python, kicad_cli):
    output = output.resolve()
    if output == ROOT or any((ROOT/name).resolve() == output or (ROOT/name).resolve() in output.parents
                             for name in ('engineering','design','tools','integration','tests','.git','.github','.venv','archive','baselines','docs')):
        raise ValueError('use a new output outside source/evidence directories')
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'schema':'razr-ep5-native-ecad-execution-v1', 'expected_head':expected_head,
              'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'commands':[],
              'passed':False, 'native_DRC_executed':False, 'schematic_ERC_executed':False,
              'schematic_parity_requested':False, 'OEM_assignment_qualified':False,
              'signal_integrity_or_power_qualified':False, 'dynamic_FPC_qualified':False,
              'supplier_stackup_selected':False, 'candidate_go':False,
              'fixture_fabrication_go':False, 'manufacturing_go':False,
              'scope':'native readback and all-severity PCB DRC of the owned 188 mm continuity research artwork',
              'github_run_id':os.environ.get('GITHUB_RUN_ID'),
              'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT')}
    before = {}

    def save():
        report['seconds'] = time.monotonic()-started
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

    def run(label, command, allow_nonzero=False):
        begin = time.monotonic()
        with (output/(label+'.log')).open('w') as stream:
            proc = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=300, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        report['commands'].append({'label':label,'argv':command,'exit_code':proc.returncode,
                                   'seconds':time.monotonic()-begin,'log_sha256':sha(output/(label+'.log'))})
        save()
        if proc.returncode and not allow_nonzero:
            raise RuntimeError(label+' failed with exit '+str(proc.returncode))
        return proc.returncode

    try:
        head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        if head != expected_head: raise ValueError('source HEAD differs from expected candidate')
        for name in SOURCES:
            raw = (ROOT/name).read_bytes()
            committed = subprocess.check_output(['git','show',head+':'+name],cwd=ROOT)
            if raw != committed: raise ValueError('source differs from committed bytes: '+name)
            before[name] = hashlib.sha256(raw).hexdigest()
        report['source_sha256_before'] = before
        result = artwork.export(output/'artwork')
        report['artwork_report_sha256'] = sha(output/'artwork/report.json')
        report['candidate_id'] = result['candidate_id']
        board = output/'artwork/ep5_continuity26.kicad_pcb'
        project = board.with_suffix('.kicad_pro')
        board_hashes = {p.name:sha(p) for p in (board,project)}
        run('kicad-version', [kicad_cli,'version'])
        run('native-readback', [kicad_python,'-B',str(ROOT/HELPER),
                               '--board',str(board),'--output',str(output/'native-readback')])
        native = json.loads((output/'native-readback/readback.json').read_text())
        if native.get('source_sha256') != before[HELPER]:
            raise ValueError('native readback producer identity differs')
        report['native_readback'] = validate_readback(native,artwork.route_input(),board_hashes)
        report['kicad_version'] = native['kicad_version']
        drc = output/'native-drc.json'
        code = run('native-drc',[kicad_cli,'pcb','drc','--format','json','--units','mm',
                    '--all-track-errors','--severity-all','--exit-code-violations','--output',str(drc),str(board)],True)
        report['native_DRC_executed'] = True
        if not drc.is_file(): raise ValueError('native DRC produced no JSON')
        report['native_DRC_sha256'] = sha(drc)
        report['native_DRC_counts'] = validate_drc(json.loads(drc.read_text()),code,board,native['kicad_version'])
        if {p.name:sha(p) for p in (board,project)} != board_hashes:
            raise ValueError('native execution changed original board/project')
        report['input_board_project_bytes_unchanged'] = True
        report['passed'] = True
    except Exception as exc:
        report['error'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        after = {name:sha(ROOT/name) for name in before}
        report['source_sha256_after'] = after
        report['source_bytes_unchanged'] = bool(before) and before == after
        report['source_head_after'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        report['passed'] &= report['source_bytes_unchanged'] and report['source_head_after'] == expected_head
        report['files_sha256'] = {str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*'))
                                 if p.is_file() and p != output/'report.json'}
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--kicad-python',default='/usr/bin/python3')
    parser.add_argument('--kicad-cli',default='kicad-cli')
    args = parser.parse_args()
    result = execute(args.output,args.expected_head,args.kicad_python,args.kicad_cli)
    print(json.dumps({k:result.get(k) for k in ('passed','native_DRC_executed','native_DRC_counts','error','seconds')},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
