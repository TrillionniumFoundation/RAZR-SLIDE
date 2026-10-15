"""Reproduce the actual failed global cam bracket without discarding later cases.

This is a bounded geometry diagnostic, not a new accepted trajectory, force
model, continuous proof, manufactured spring, or complete phone assembly.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GROUP = ROOT / 'engineering/passive-return-spring-recovery-20261013-r6'
SPLIT = GROUP / 'split-root-repair'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(); out = args.output.resolve()
    if ROOT == out or ROOT in out.parents:
        raise ValueError('Use a new external run directory, not a frozen repository')
    out.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads((GROUP / 'stable-snapshot.json').read_text())
    for entry in snapshot['files']:
        p = ROOT / entry['path']
        if sha(p) != entry['sha256']:
            raise ValueError('frozen spring snapshot mismatch: '+entry['path'])
    before = {str(p.relative_to(ROOT)): sha(p) for p in GROUP.rglob('*')
              if p.is_file() and p.suffix in ('.py', '.step', '.brep')}
    sys.path[:0] = [str(SPLIT), str(GROUP)]
    import split_root_cartridges_v9 as scene
    b = scene.b
    from strict_intersections import CheckedBody, Checker
    rows = []; failures = []; start = time.monotonic()
    # Reuse the rejected original *bracket* limits. Do not enlarge the allowed
    # travel or relax signed common checks to manufacture a successful bracket.
    for port in ('STOW', 'OPEN'):
        for side in 'LR':
            parts, _ = scene.scene(port, side)
            for q in (12., 8., 4., 2., 1.4, 1.2, 1., .8, .7, .4, .2, .1, .05, 0.):
                key = parts['KEY'].translate(b.identity.qvec(port, q))
                for i in range(2):
                    zero = parts['STOP_'+str(i)].translate(b.rvec(port, -1.14))
                    guard = Checker(); kb = CheckedBody(key)
                    def check(lift):
                        actual = guard.common(CheckedBody(zero.translate(b.rvec(port, lift))), kb)
                        return {'lift_mm': lift, **actual}
                    low = check(-.02); high = check(1.2)
                    failed = low['checked_common_mm3'] > 1e-10 and high['checked_common_mm3'] > 1e-10
                    row = {'port': port, 'side': side, 'key_translation_q_mm': q,
                           'stop_index': i, 'low': low, 'high': high,
                           'old_binary_search_upper_bracket_fails': failed,
                           'clear_bracket_does_not_prove_monotonicity': True}
                    if failed:
                        row['interior_samples'] = [check(j/10) for j in range(12)]
                        row['sampled_clear_lifts_mm'] = [v['lift_mm'] for v in row['interior_samples'] if v['checked_common_mm3'] <= 1e-10]
                        row['samples_are_not_a_continuous_trajectory'] = True
                        tag = f'{port}_{side}_q{q}_stop{i}'.replace('.', 'p')
                        p = out / (tag+'_UPPER_BRACKET_COUNTEREXAMPLE.step')
                        assembly = b.cq.Compound.makeCompound([key, zero.translate(b.rvec(port, 1.2))])
                        b.cq.exporters.export(assembly, str(p))
                        row['counterexample_STEP'] = {'path': p.name, 'sha256': sha(p), 'expected_solid_leaves': 2}
                        failures.append({k: row[k] for k in ('port','side','key_translation_q_mm','stop_index','sampled_clear_lifts_mm','counterexample_STEP')})
                    rows.append(row)
                    (out/'progress.json').write_text(json.dumps({'rows':rows,'failures':failures,'manufacturing_go':False},indent=2)+'\n')
            print(port, side, 'rows', len(rows), 'bad_upper_brackets',len(failures), flush=True)
    after = {p: sha(ROOT/p) for p in before}
    if before != after:
        raise ValueError('frozen spring input mutated')
    result = {'host':platform.node(),'CadQuery':b.cq.__version__, 'source_sha256':sha(__file__),
              'old_rejected_source_sha256':sha(SPLIT/'rejected-global-cam-bracket/final_sequence_gate.py'),
              'input_SHA256':before,'input_bytes_unchanged':True,'rows':rows,
              'checked_brackets':len(rows),'invalid_upper_brackets':len(failures),'failures':failures,
              'full_final_sequence_executed':False,'new_motion_or_force_model_accepted':False,
              'physical_qualification':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('checked_brackets','invalid_upper_brackets','manufacturing_go')}))
    # Exit zero means complete diagnostic capture. An invalid bracket is kept
    # explicit in the result, and is never interpreted as an accepted assembly.


if __name__ == '__main__':
    main()
