# Gate closure execution — 2026-10-22

**EP5 passed its declared nominal three-pose native and independent STEP-readback checks on functional commit `0d97d8021dc508a40eb2565f6683c6dfba2659f4`. Complete validation and all six product gates remain open.** The complete unit attempt failed because required inputs and dependencies were unavailable; the EP4 finite scenes could not load their original mounted archive. No hardware, fabrication or manufacturing acceptance is granted.

The current results are recorded in [SUMMARY.json](SUMMARY.json), the actionable conditions in [BLOCKERS.json](BLOCKERS.json), and the next work in [WORK_PLAN_ZH.md](WORK_PLAN_ZH.md).

## Actual results on the functional commit

| Execution | Observed result | Evidence boundary |
| --- | --- | --- |
| EP5 local and complete native execution | **Execution checks passed**, 152.889 s. Local: 46 bodies at each pose, 3,105 unordered pair rows. Complete: 154/154/161 bodies at STOW/PREDOCK/OPEN, 36,442 pair rows, 2,333 native Common calls and 123 containment rows. Both independent STEP readers passed. | All declared finite-pose checks were clear. The containment domain is an optimistic outer union, not measured internal-channel clearance. Full continuous motion, actual-part fit and G2 acceptance remain open. |
| EP4 required native driver | Seven native regression groups passed; the three finite scenes failed to load `mounted-mechanism-20261015/native-geometry.tar.gz`. | `execution_checks_passed=false`; finite geometry was **not evaluated in this attempt**. Historical rejected EP4 results remain retained. |
| Complete unit attempt | All 36 suite commands completed: **25 passed, 11 failed; 1,251 tests ran**. There were 0 assertion failures and 16 errors: 12 class-initialization errors and 4 test-method errors. No tests were skipped. | The configured minimum is **1,461**, not an executed or passing count. Missing inputs/dependencies prevented some tests from starting. The checkout and runtime were incomplete. |
| Hosted research CI | At `2026-10-22T09:01:08.615Z`, run `39750350316` had **12 failed jobs, 1 queued job and 0 jobs with executed steps**. | No successful hosted execution was observed. Annotation bodies were unavailable through the connector, so the cause of these current failures was not verified. This is a retained observation, not a live status claim. |

Primary receipts: [EP5](native-0d97d80/ep5/report.json), [EP4](native-0d97d80/ep4/report.json), [complete unit report](full-unit-0d97d80/results/report.json), [unit summary](full-unit-0d97d80/summary.json), and [hosted observation](full-unit-0d97d80/actions-observation-final.json). The corresponding [GitHub Actions run](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39750350316) is bound to the same functional commit.

### Source, input and runtime identity

The native drivers bind selected working files to the real HEAD tree/blob identities and retain before/after SHA256 checks. EP5 additionally binds its declared actual input roles. This execution used **12 repository payload roles plus all 64 byte-identical original mounted STEP members**, with the recovery receipt checked before and after generation and by the independent reader. The original mounted tar itself was **not** recovered. The explicit member option is limited to the EP5 native path; it does not satisfy other suites' archive requirements.

The independent unit run used a physical `copy2` copy including `.git`, with no shared regular-file inodes. It ran the full verifier once. The actual HEAD, clean worktree and every present tracked file remained unchanged. These checks establish the executed source identity; they do not establish that every tracked historical file was present.

The runtime was Python 3.12.14, CadQuery 2.7.0, OCP 7.8.1.1.post1, NumPy 2.3.5 and SciPy 1.17.0, with Shapely absent. It did not reproduce `uv.lock`. This applies to the successful scoped EP5 execution as well as the failed complete-unit attempt.

Six required original archive inputs remained unavailable in this session:

| Original repository path | Observed role in the complete attempt |
| --- | --- |
| `engineering/mounted-mechanism-20261015/native-geometry.tar.gz` | Reached by failing unit traces and the EP4 finite-scene entry point. |
| `engineering/contact-motion-20261014/project-owned-native-geometry.tar.gz` | Required input still missing; its own failure was not reached after earlier initialization errors. |
| `engineering/cover-assembly-order-20261014/bench-geometry.tar.gz` | Reached by failing unit traces. |
| `engineering/cover-retention-and-space-20261015/capture-geometry.tar.gz` | Required input still missing; its own failure was not reached after earlier initialization errors. |
| `engineering/keycover-geometry-20261014/project-owned-geometry.tar.gz` | Reached by failing unit traces. |
| `engineering/thin-mechanism-20261015/native-geometry.tar.gz` | Reached by failing unit traces. |

See the [input inventory](input-availability/missing-unit-test-inputs.json) and unit summary for identities and exact failures. Original member recovery must retain its own identity and scope; it cannot be relabelled as recovery of an original tar.

## What this work closes

`G2-01` is verified **within the declared nominal research inventory**: the complete three finite poses, unordered pair inventory, optimistic outer-domain containment, actual input identities and independent readback. The remaining G2 work includes realizable control relations, the complete forward and return path, attachment installation/removal, actual parts, assembly access and measured tolerance margins. A finite-pose result and a local continuous enclosure do not establish those conditions. The [EP5 scope](../product-integration-20261018/phase5-20261022/README.md) states the geometry and motion boundaries.

The software corrections also provide:

- Separate required EP4 and EP5 CI jobs, exact HEAD/blob checks and independent readers. Research execution success is distinct from a candidate's geometric acceptance; a fully recorded geometric rejection remains a valid research result.
- An unpowered-motion qualification contract binding specimen, design, plan, acquisition, calibration and raw records, with uncertainty-aware pass/fail/unknown outcomes. Known failures survive incomplete observations, and caller-supplied reviewer attestations do not authenticate reviewer identity or independence.
- Atomic complete C/H, ordered-descriptor and exchange-state checkpoints for the original bearing study, with reconstructed C columns, the unchanged five operator probes and original clipped-domain checks. The actual large FE/QP and original restart were not executed; a retained displacement field is not a complete checkpoint.

The complete run's existing logs include 15 EP4-driver tests, 19 EP5-driver tests, 31 bearing-continuation tests, 51 qualification-contract tests and 9 acquisition tests without errors in those classes; the separate EP5 routing suite passed all 21 tests. These observations are already part of the 1,251-test attempt and must not be added again to its total. Independent review counts are separate evidence, not additional configured unit passes.

## Reproduce the fixed functional source

Use a dedicated, complete checkout with all original inputs available at their tracked paths. Use Python 3.12 and the committed `uv.lock`; the workflow selects uv 0.10.10. A missing input or failed locked dependency installation must remain a failure. Do not weaken fixture requirements to reproduce a passing result.

Run this setup from the repository root. The output directory is newly created **outside** the checkout:

```sh
RAZR_SOURCE_SHA=0d97d8021dc508a40eb2565f6683c6dfba2659f4
git switch --detach "$RAZR_SOURCE_SHA"
test "$(git rev-parse HEAD)" = "$RAZR_SOURCE_SHA"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
uv sync --locked

RAZR_EVIDENCE_DIR="$(mktemp -d /tmp/razr-gate-validation.XXXXXX)"
mkdir "$RAZR_EVIDENCE_DIR/tmp"
export TMPDIR="$RAZR_EVIDENCE_DIR/tmp"
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
```

Run each validation separately and retain its exit status and output, including failures:

```sh
uv run --locked python -B tools/verify.py \
  --output "$RAZR_EVIDENCE_DIR/unit"
```

```sh
uv run --locked python -B tools/verify_product_native.py \
  --expected-head "$RAZR_SOURCE_SHA" \
  --output "$RAZR_EVIDENCE_DIR/ep4" \
  --timeout-seconds 1200
```

```sh
uv run --locked python -B tools/verify_product_ep5_native.py \
  --expected-head "$RAZR_SOURCE_SHA" \
  --output "$RAZR_EVIDENCE_DIR/ep5" \
  --timeout-seconds 3000
```

These are the standard original-input commands; the last two also invoke their independent readers. The [workflow](../../.github/workflows/research-ci.yml) additionally requires its existing native-study matrix and aggregate `current-suites` job for hosted closure.

For the explicitly scoped EP5 recovery route only, use a new output directory and add `--verified-mounted-members /absolute/path/to/verified-original-members` to the EP5 command. That directory must contain the complete original 64-member set and the required sibling receipt; arbitrary exported or regenerated STEP files are rejected. See [EP5 driver documentation](../../tools/PRODUCT_EP5_NATIVE_VALIDATION.md). Default CI continues to require the original mounted tar. No corresponding fallback is claimed for EP4 or the complete unit verifier.

## Gate ledger and next work

| Gate | Current status | Remaining acceptance evidence |
| --- | --- | --- |
| G0 — reliable research baseline | Blocked | Complete required original inputs, locked execution, all configured suites and required native jobs on an identified commit, and actual successful hosted runner steps. Original FE/restart inputs are a separately identified numerical dependency. |
| G1 — real inputs frozen | Blocked | Same-donor identity and dimensions, seven part roles, twelve terminal bindings, actual OLED/COF and FPC limits, complete battery packs and actual process/tolerance definitions. |
| G2 — geometry and motion | Blocked; nominal `G2-01` subitem verified | Mechanically realizable continuous forward/return paths, attachment installation/removal and tool access, actual-part fit and measured tolerance margins. |
| G3 — unpowered assembly | Blocked | Identified physical specimen, preregistered applicable criteria and complete original assembly/motion/retention/relock records. |
| G4 — functional prototype | Blocked | Same-version protected power, charging, USB, display and touch results at rest and during motion, with raw observations. |
| G5 — manufacturing release | Blocked | Qualification of the selected geometry and real load/contact/material model, physical durability, process stability, inspection and traceability. |

The [Chinese work plan](WORK_PLAN_ZH.md) assigns owner roles, prerequisites and acceptance evidence to the P0/P1/P2 packages. The [remaining-boundaries review](remaining-closure-boundaries-0d97d80.json) retains detailed physical and numerical dependencies. Its earlier “suite results pending” wording describes its own review time; the completed attempt above and `SUMMARY.json` are the final execution results.

## Evidence publication and retained history

All current execution receipts describe functional commit **`0d97d8021dc508a40eb2565f6683c6dfba2659f4`**. The later commit containing these reports, state updates and this work plan is an **evidence publication commit**. Publishing evidence does not claim that validation was rerun at that later HEAD.

The [archive index](archives/ARCHIVES.json) describes the three retained evidence bundles and their identities; [reassemble_base64_archive.py](archives/reassemble_base64_archive.py) reconstructs those indexed packages. Individual report links remain the direct entry points for results and limitations.

The earlier [e25 baseline attempt](baseline-e25/report.json), targeted development runs, rejected EP4 candidate and R4 geometry evidence remain historical records. R4's top-level input snapshot omitted a consumed gzip JSON; the final input-closure repair and the committed-source EP5 execution supersede that limitation for the new receipt without rewriting R4. No prior test total, publication HEAD, hardware observation or original bearing result is silently promoted to a current pass.
