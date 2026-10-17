# Exact-response continuation candidate — 2026-10-16

Base main: `ab8e32acf4d6dc0510e45838ec03458f4de28363`. This is a draft performance/continuation increment, not a completed original-device contact repair.

## Delivered source

`integration/contact_exchange.py` keeps sparse point-force maps and the exact complementary-energy response matrix, without retaining a complete displacement vector for each contact column. A checkpoint is bound to immutable input identities and checked by full-operator actions. Only new point columns require new responses. Complete displacement reconstruction uses one solve for the combined load, then the explicit rigid field. No new constraint, penalty stiffness, mean-pressure approximation or changed gap tolerance is introduced.

The same module batches every original floating-point quadratic-extremum candidate: vertices, valid edge stationary points and feasible interior stationary points. It does not clamp negative gaps. Worst-gap witness selection is deterministic and balanced across patches; unlike the prior 0.08 mm selection spacing, it does not discard distinct nearby violating points. Old contact constraints remain present. This is a proposed efficiency change, not a convergence-rate guarantee.

`engineering/preload-resume-20261016/resume_original.py` is the explicit original-model adapter. It retains complete sparse K, the original gauges and frame fixture, original loads and bolt branch, and the 1e-7 mm threshold. It loads the existing bounded point checkpoint rather than recreating old per-column displacement arrays. It has been syntax-checked, NOT run on the original device. Every returned field still requires an independent original-model tetrahedral force/gap audit and mesh/contact convergence. Do not merge on isolated tests alone.

## Actually completed this turn

On the authorized desktop, the old spatial-integration temporary folder was absent. The repository's frozen mesh/load archive was verified and used to reconstruct both complete stiffness matrices in `/tmp/razr-preload-contact-20261016/elastic`. Both jobs exited zero and produced byte-identical original K hashes: panel 6144f7694493f5d0922d56db2ad5447145f24e252adb65c5b8d2ef1a5b5cff86; frame b9ee0416ee1a888f6b5ba992eb57b964dc28843bdfa4ac38ec9c8ad02fabf19c. This restores the energy input, not a contact solution.

A subsequent remote process-start request was safety-blocked. No alternate remote execution route was used; already launched restoration jobs were only read to terminal. All new helper validation afterward ran in the isolated conversation container.

Forty new unit tests passed. Eight manufactured full-3D P2 problems passed checkpoint restoration/extension and combined-load field reconstruction against the existing primal solver and independent full sparse K. Maximum displacement difference was about 2.22e-16; maximum relative free residual about 3.84e-15. These are known-solution calibration problems, NOT the phone and NOT an actual deformation accuracy claim.

A separate single timing run on 5255 synthetic convex cells gave approximately 0.00762 s batched versus 1.04078 s original scalar audit, excluding batch setup. Min/max differences were below 1.56e-14 and candidate counts matched. These are not the original 5255 phone cells and not a native full-solver speed claim.

At 2197 force columns and 818829 displacement DOFs, the old per-column displacement arrays alone account for 14,391,738,504 bytes; the dense H alone is 38,614,472 bytes. The new cache still needs sparse force maps, K, factorizations, temporary fields and QP workspace. This is storage accounting, not measured total peak memory.

## Not completed

Original case4 remains rejected in the inherited report (2193 contacts; 2261 negative cells; minimum -6.8900578e-7 mm). Cases5..7 have not been rerun with this adapter. All 913 configured tests/31 suites have NOT been run. The previous 873-test success is not reused. No native CAD change, physical-input update, dependency/workflow change or hardware action occurred.

The exact isolated validation runner, reference P2 fixture, logs and fields are in the conversation evidence package `RAZR_SLIDE_preload_resume_candidate_20261016.zip`; they are not claimed as original phone fields. Reproduce the 40 repository helper tests with:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest discover \
  -s integration/manufacturing-tests -p test_contact_exchange.py -v
```

The package also provides `engineering/preload-resume-20261016/run_validation.py --output NEW_DIRECTORY` for the eight manufactured replays. The adapter takes `--inputs RESTORED_ELASTIC_DIR --output NEW_DIRECTORY --cases 4 5 6 7`; use the original authorized execution environment and complete independent validation before assigning any new result.

All candidate/fixture/manufacturing go flags remain false. Initial spring force is not installed preload; point reaction is not area pressure; no new mesh convergence, force rating, torque, machining or procurement is claimed.
