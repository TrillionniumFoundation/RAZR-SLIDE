"""Pure source derivation; no supervisor execution."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'original-supervise_k3full.py').read_text()
s=s.replace('K3FULL external owned supervisor; preliminary complete factory and independent STEP readback each keep 1200 s / 1536 MiB finite guards. Original 90 s positive-only KEY reader is not used or claimed.','K4 external owned local-section supervisor. The exact original finite native guards and owned child lifecycle are retained; only arguments, evidence identity and a stricter output bound are added.')
s=s.replace('from full_stop_states import STATES\n','')
a=s.index("    parser.add_argument('--mode'");b=s.index('    args = parser.parse_args',a)
s=s[:a]+'''    parser.add_argument('--mode', required=True, choices=('producer', 'readback'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--sources-sha256', required=True)
    parser.add_argument('--producer', type=Path)
'''+s[b:]
s=s.replace("if args.mode == 'readback' and args.report is None:","if args.mode == 'readback' and args.producer is None:").replace("native = args.mode == 'factory'","native = args.mode == 'producer'")
a=s.index('    source = HERE/');b=s.index('    receipt = ',a)
s=s[:a]+'''    source = HERE/'k4_worker.py'
    command = [str(identity.ROOT/'.venv/bin/python'), '-B', str(source), '--mode', args.mode,
               '--output', str(out/'worker'), '--inputs', str(args.inputs.resolve()),
               '--sources', str(args.sources.resolve()), '--sources-sha256', args.sources_sha256]
    if not native:
        command += ['--producer', str(args.producer.resolve())]
    if identity.sha(args.sources) != args.sources_sha256:
        raise ValueError('frozen source manifest changed')
    bundle=json.loads(args.sources.read_text())
    own_sources = {str(Path(path).resolve()): identity.sha(path)
                   for path in [args.sources, identity.__file__, owned_process.__file__]+
                   [HERE/name for name in bundle['runtime_sources']]+
                   [HERE.parent/name for name in ('service-launch.py','host-cap.py','python-downloads.json')]}
    for name, ref in bundle['runtime_sources'].items():
        if own_sources[str((HERE/name).resolve())] != ref['sha256'] or (HERE/name).stat().st_size != ref['bytes']:
            raise ValueError('frozen runtime source differs')
'''+s[b:]
s=s.replace('razr-K3FULL-owned-finite-supervisor-20261026-v1','razr-K4-owned-finite-supervisor-20261027-v1')
s=s.replace("'new_complete_STEP_readback_budget_justification': '154/161 whole STEP imports, independent panel reconstruction and all 11781/12880 original pairs retain the original full finite guard; actual K2 full workers were 233-485 s and K3 pilot workers 68-139 s. Completion remains subject to unchanged hard gates.',", "'new_complete_STEP_readback_budget_justification': 'K4 uses three original whole STEP imports, 12 finite windows and 2 negative controls. Producer 38 and reader at most 190 Booleans retain the original 1200 s / 1536 MiB finite guard. The capacity contract is preregistration, not a measured K4 pass.',")
s=s.replace("               'resource_observations': []}","               'additional_output_limits': {'worker_directory_MiB':160,'scientific_directory_MiB':128,'single_worker_file_MiB':16},\n               'resource_observations': []}")
needle="        if reason or time.monotonic()-recorded >= 10:"
s=s.replace(needle,"        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) > 160*2**20:\n            reason = 'additional bounded worker output exceeded 160 MiB'\n"+needle)
s=s.replace("        receipt['finite_trial_clear'] = result.get('finite_pose_clear')\n        receipt['pilot_clear'] = result.get('pilot_clear')", "        receipt['local_material_targets_all_matched'] = result.get('local_material_targets_all_matched')\n        receipt['all_probes_evaluated'] = result.get('all_probes_evaluated')")
s=s.replace("'completed', 'worker_exit_code', 'finite_trial_clear',", "'completed', 'worker_exit_code', 'local_material_targets_all_matched',")
(p/'supervise_k4.py').write_text(s)
