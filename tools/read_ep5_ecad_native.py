"""Native KiCad 9 EP5 continuity-board readback, owned libraries and DRC.

Successor of engineering/product-integration-20261018/electrical/verify_native_mini.py
with predecessor SHA256 f8f337d12fdc57620c79970a7592434682750300cc48a4c634c49cf1fef06273.
The historical file remains unchanged. KiCad 9 requires an explicit
PCB_IO_KICAD_SEXPR writer for a new empty library and EDA_UNITS_MM.
All project loading, native terminal readback, DRC and unchanged input-byte
checks from the predecessor are retained. No OEM, power, signal-integrity,
dynamic flex or product assembly qualification is implied.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import pcbnew

    board_path = args.board.resolve()
    project = board_path.with_suffix('.kicad_pro')
    before = {p.name: sha(p) for p in (board_path, project)}
    started = time.monotonic()
    manager = pcbnew.GetSettingsManager()
    loaded = manager.LoadProject(str(project))
    if not loaded:
        raise RuntimeError('native KiCad could not load the declared project')
    board = pcbnew.LoadBoard(str(board_path))
    board.SetProject(manager.Prj())
    libraries, exported, sites = {}, [], []
    for footprint in board.GetFootprints():
        identifier = footprint.GetFPID()
        library = str(identifier.GetLibNickname())
        item = str(identifier.GetLibItemName())
        if not library or not item or any('/' in s or '\\' in s for s in (library, item)):
            raise ValueError('a local named footprint library is required')
        directory = board_path.parent / (library + '.pretty')
        directory.mkdir(exist_ok=True)
        libraries[library] = directory.name
        target = directory / (item + '.kicad_mod')
        if not target.exists():
            # KiCad 7 FootprintSave preserves a footprint rule area's absolute
            # board coordinates. Move an independent loaded copy to the
            # library origin first; do not alter the analysis board or its
            # frozen embedded J1 footprint. This includes every keepout point.
            export_board = pcbnew.LoadBoard(str(board_path))
            export_footprint = next(f for f in export_board.GetFootprints()
                                    if f.GetReference() == footprint.GetReference())
            export_footprint.SetPosition(pcbnew.VECTOR2I(0, 0))
            pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(str(directory), export_footprint)
        if not target.is_file():
            raise RuntimeError('native footprint export missing: ' + str(target))
        exported.append({'reference': footprint.GetReference(),
                         'library_id': library + ':' + item,
                         'library_file': str(target.relative_to(board_path.parent)),
                         'sha256': sha(target)})
        for pad in footprint.Pads():
            position, size = pad.GetPosition(), pad.GetSize()
            sites.append({'reference': footprint.GetReference(),
                          'pad': pad.GetNumber(), 'net': pad.GetNetname(),
                          'position_mm': [pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)],
                          'size_mm': [pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)],
                          'drill_mm': [pcbnew.ToMM(pad.GetDrillSize().x), pcbnew.ToMM(pad.GetDrillSize().y)]})
    table = '(fp_lib_table\n' + ''.join(
        '  (lib (name "' + name + '")(type "KiCad")(uri "${KIPRJMOD}/' + path + '")(options "")(descr "Owned research geometry exported by native KiCad"))\n'
        for name, path in sorted(libraries.items())) + ')\n'
    (board_path.parent / 'fp-lib-table').write_text(table)
    args.output.mkdir(parents=True, exist_ok=False)
    drc_path = args.output / (board_path.stem + '-drc.txt')
    wrote = pcbnew.WriteDRCReport(board, str(drc_path), pcbnew.EDA_UNITS_MM, True)
    if not wrote or not drc_path.is_file():
        raise RuntimeError('native DRC did not produce a report')
    drc = drc_path.read_text()
    counts = re.findall(r'\*\* Found (\d+) ([^\n]+)', drc)
    violations = collections.Counter(re.findall(r'^\[([^\]]+)\]', drc, re.M))
    report = {'scope': 'native KiCad 9 EP5 flat continuity-board readback and DRC only',
              'kicad_version': pcbnew.GetBuildVersion(),
              'kicad_release': pcbnew.Version(),
              'source_sha256': sha(Path(__file__)),
              'inputs_sha256': before, 'project_loaded': bool(loaded),
              'input_bytes_unchanged': before == {p.name: sha(p) for p in (board_path, project)},
              'seconds': time.monotonic() - started,
              'tracks': len(list(board.GetTracks())),
              'declared_board_thickness_mm': pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness()),
              'footprints': len(list(board.GetFootprints())),
              'native_pad_objects': len(sites),
              'unique_connected_terminals': len({(x['reference'], x['pad']) for x in sites if x['net']}),
              'electrical_nets': sorted({x['net'] for x in sites if x['net']}),
              'drc_sections': [{'count': int(n), 'kind': kind} for n, kind in counts],
              'drc_violation_types': dict(violations),
              'drc_zero_reported_items': bool(counts) and all(int(n) == 0 for n, _ in counts),
              'drc_report_sha256': sha(drc_path),
              'exported_footprints': exported, 'native_pad_readback': sites,
              'product_motion_or_OEM_qualification': False}
    (args.output / 'readback.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in (
        'kicad_version', 'input_bytes_unchanged', 'tracks', 'footprints',
        'native_pad_objects', 'unique_connected_terminals', 'drc_sections',
        'drc_violation_types', 'drc_zero_reported_items', 'seconds')}))


if __name__ == '__main__':
    main()
