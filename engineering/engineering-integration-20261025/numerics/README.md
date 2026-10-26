# Exact-input numerical recovery, 2026-10-25

The panel L2 matrix was actually reconstructed and the original five inverse
probes were actually executed in three bounded strategies. **Every strategy
failed the unchanged original float64 gate on the all-ones probe.** The other
four probes passed. No panel H, H-action restore, new contact QP, or product
release is accepted by this work. Machine-readable results are in
`SUMMARY.json`; each evidence directory retains its executed source, report,
supervisor measurements, and log. The current helpers include two later
operational safeguards, tested separately below.

## Recovery and identity

`recover_inputs.py` reads only the exact original mesh/load archive members
after verifying the full frozen archive SHA-256
`9e9cf5e61ce6b5f15ec6194361ec3c12d74897614ad8154ba469f01ee8f69f08`.
It verifies both member hashes and verifies the archive again before publishing
a recovery receipt. The 43-package repository environment is checked strictly.

For the panel, 57,620 original tetrahedra and 344,103 original vector DOFs were
retained. L2 internal DOFs were statically condensed, with unchanged P2 surface
traces, original six constrained DOFs, material normalization E = 1 and
nu = 0.3, and element/COO accumulation order. In-memory element storage changed
the scratch storage method only. The resulting 285,135,469-byte K has
23,646,483 nonzeros and SHA-256
`80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb`.
This exactly reproduces the **2026-10-23 reconstruction**. It does not recover
the different historical 2026-10-17 volume-v3 matrix or certify its identity.

The assembly passed symmetry, five directional energy, six rigid-mode, and
mapping checks. Maximum energy discrepancy was 2.26731120252514e-14; maximum
rigid-mode action was 4.405364961712621e-13. Assembly took 34.83 seconds with a
measured worker high-water RSS of 1.72 GiB. These assembly checks are distinct
from inverse-operator qualification.

## Unchanged inverse acceptance and actual results

The original 3,885 ordered response points, force-map C, seed 73021, all-ones
direction, and four Rademacher directions were used. C reproduces SHA-256
`9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f`.
The acceptance calculation always uses the original float64 unscaled matrix:

```text
max(abs(Kff @ u - rhs_free)) / max(max(abs(rhs_free)), 1.0) <= 1e-7
```

| Executed strategy | Probe 0 baseline | Probe 0 final after four corrections | Other four | All five accepted |
| --- | ---: | ---: | --- | --- |
| Original MMD factor; extended-precision correction residual | 2.384908468e-7 | 1.760949857e-7 | Pass | No |
| Original MMD factor; float64 correction residual | 2.384908468e-7 | 2.065996289e-7 | Pass | No |
| Symmetric diagonal scaling; extended-precision correction residual | 3.466436727e-7 | 3.161390295e-7 | Pass | No |

The original all-ones residual numerator was 2.562999725341797e-6 and its
denominator was 10.746742525317169. The maximum occurred at original DOF 161396,
where RHS was zero; maximum solution magnitude was about 2.252576958e8.
All intermediate correction measurements, argmax DOFs, correction norms, RHS
hashes and iterate hashes are retained in the reports. Baseline and final full
solution arrays are retained; intermediate full solution arrays were not saved.
The common full five RHS arrays and directions were subsequently regenerated
and verified against the hashes from all three runs; their receipt is
`five-probe-rhs-retention.json`.

The bounded condition estimate was approximately 1.23e12. This is an estimate
from `onenormest`, not a certified eigenvalue analysis. The all-ones Rayleigh
quotient was approximately 6.33e-10 and its nonrigid/full least-squares L2 ratio
was approximately 0.240. These observations support a poorly conditioned,
nearly rigid response as an explanation for numerical sensitivity. They are
not a measurement of the actual product's physical displacement or stiffness:
the material is normalized and the load is a synthetic operator probe.

For the scaled final solution, extended-precision residual accumulation gave
4.333045909e-8 while the original float64 evaluation gave 3.161390295e-7.
This exposes accumulation/cancellation sensitivity, but the original gate still
fails. Extended residuals are diagnostic only. Run 1 did not retain a separate
extended-residual comparison; runs 2 and 3 retain baseline/final comparisons.
No inference of five-probe acceptance, complete H, or H-action acceptance is
made from the extended result or from four passing probes.

## Resource bounds and reproduction

Heavy workers ran sequentially in the task-specific tmpfs
`/dev/shm/razr-integration-20261025-fea78049c104`, with an 8 GiB shared cgroup.
The supervisor preserved at least 500 MiB filesystem reserve and limited the
shared measured nonreclaimable budget to 6.8 GiB, defined as anon + shmem +
kernel stacks + page tables + sockets + unreclaimable slab. Total cgroup memory
and reclaimable file cache are recorded separately. The three probe workers
peaked at 2.55, 2.55, and 2.82 GiB RSS and took approximately 18.79, 22.04, and
22.82 seconds. None was stopped by a resource limit. Exit code 2 records the
failed original five-probe gate. Logical payload accounting can count hardlinks
twice; measured filesystem availability and cgroup shmem are retained separately.

Use the repository's locked `.venv/bin/python`. The exact executed commands
are recorded in each `evidence/*/supervisor.json`, and the corresponding source
versions are retained beside them. New runs must use fresh output directories.
For example, with a separately authorized task directory and exclusive memory
window:

```bash
.venv/bin/python -B engineering/engineering-integration-20261025/numerics/recover_inputs.py --help
.venv/bin/python -B engineering/engineering-integration-20261025/numerics/assemble_l2.py --help
.venv/bin/python -B engineering/engineering-integration-20261025/numerics/probe_original_actions.py --help
```

Wrap heavy commands with `run_bounded.py`, passing `--task-directory`, new
`--log`, new `--report`, and a bounded `--seconds`. The assembly entry now
rejects optimized Python, so its numerical assertions cannot silently disappear.
The supervisor now terminates its child process group and writes a failure
receipt if sampling raises. A real injected sampling exception terminated the
sleeping child with SIGTERM in 0.004 seconds and returned failure; an actual
`python -O` assembly invocation was rejected. These controls and source hashes
are retained under `evidence/supervisor-failure-control`. All four current
helpers passed AST parsing. The earlier numerical executions retain their
earlier exact sources; the new safeguards are not retroactively attributed to
those runs.

## Remaining numerical work

The original frozen frame mesh/load members are available and hash-verifiable.
The next independent step is frame L2 reconstruction and the same five probes,
after the coordinated CAD compute window. Frame assembly is expected to need
roughly 2.4 GiB RSS and about one minute, but must be measured. Its inverse
factorization memory is not established; it must run under a separate bounded
window. No frame computation is claimed by this report.

Only a fresh response whose columns and probes use the same accepted numerical
strategy may proceed to all 3,885 columns and original H-action restore checks.
The present panel failures block combined panel/frame/trace restore and the
original full-domain contact continuation. Bounds, constraints, K, RHS, point
ordering and the 1e-7 acceptance threshold were not relaxed. Candidate,
fixture-fabrication and manufacturing decisions remain false.

## Frame follow-on completed before candidate publication

The same original frame K was actually rebuilt: 79,628 tetrahedra, 474,726 DOFs, 394,530,277 bytes, SHA256 `e077f8d0176c041041b984b5dbb016e140219b34223d235ac739978b1dddd95d`. The 5 GiB and separately identified 6 GiB address-space attempts both stopped inside SuperLU allocation before any of the five RHS were solved. This supersedes the earlier preparation-stage statement that frame had not yet executed. It is a factorization resource failure, not a residual rejection or a passing response. The final attempt measured 4.18 GiB worker RSS and 4.73 GiB shared nonreclaimable peak; the shared 6.8 GiB guard was unchanged. No third attempt, full H, trace, or contact restore was executed.

See [frame summary](evidence/frame-rebuild-and-factorization/FRAME_SUMMARY.json) and [complete retained receipts](evidence/frame-rebuild-and-factorization/frame-exact-rebuild-and-bounded-factorization.tar.gz).
