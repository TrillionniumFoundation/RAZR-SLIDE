# Frozen own-child helper: one actual stdlib smoke

This separate diagnostic executes the final `owned_process.py` helper itself. It does not execute SLIDE, SEATING, CAD or FE, and it does not change any native guard. The prior failed probe and successful protocol probe remain separate unchanged evidence.

Exactly one child was started with `-I -S -B`, a 128 MiB address-space limit, a 2 second CPU limit, a less-than-32 MiB RSS target, and a 9 second total wall budget. It completed in 0.22976586199729354 seconds with exit code 0 and was reaped. The helper observed RSS/HWM of 13,803,520 bytes before release and 13,828,096 bytes after release. The child's separately measured final self peak was 13,762,560 bytes. These different measurements are retained as observed. All dedicated parent and child descriptors closed.

The original Popen namespace PID was 5, while the child's procfs-visible PID was 434508. Its parent was namespace PID 2 / procfs PID 434505. Nonce, source SHA, namespace, NSpid, parent and starttime bindings matched. Only these owned/self procfs paths were read. No privilege or access-control changes, other process scanning, or retry occurred.

The raw result, exact executed source/helper bytes, child argv, stdout, stderr, cleanup and before/after source hashes are under `executed-attempt/`. `independent-source-review.json` separately records the static helper and SLIDE wiring review. No new pure test matrix was run by this reviewer; the single real smoke addressed the specific previously unverified implementation/environment risk.

The executed command was:

```sh
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -I -S -B \
  /workspace/scratch/95cd2986fdf2/gates_audit/owned-process-helper-smoke/smoke_owned_process.py \
  --helper /workspace/scratch/95cd2986fdf2/g2_slide_r3/owned_process.py \
  --output /workspace/scratch/95cd2986fdf2/gates_audit/owned-process-helper-smoke/executed-attempt
```

The command requires a fresh output directory and never retries. The actual helper SHA is `db92c8ceb3c39cd5843d96d042f0202915937abdc2a919d5854e71de4a4c0b25`; the smoke source SHA is `3131812ab81366303d5ef2ef3628d1171c73ccc07a5985c003afd178f5bf96a8`. This result demonstrates a working mapping and sampler for one small child, not completion or qualification of an as-yet-unrun native r3 workload.
