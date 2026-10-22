# Product native research validation

The independent `native-product-ep4` job runs the current EP4 product scene at
PREDOCK, OPEN and STOW on the exact commit used by the other research jobs.
`current-suites` requires this job, the full unit suites and the existing native
study matrix to finish successfully. It is a research execution check.

## Reproduce one commit

Use the repository's locked Python 3.12 environment and a clean Git checkout.
The output must be a new directory outside the repository:

```sh
uv sync --locked
uv run --locked python -B tools/verify_product_native.py \
  --expected-head "$(git rev-parse HEAD)" \
  --output /absolute/new/path/razr-product-native \
  --timeout-seconds 1200
```

The driver first checks the generated product entry points, then runs the seven
native regression groups (including the retained 18 mm3 A33 negative control),
all three finite scenes in one generator invocation, and a separate STEP reader
process. It checks all 41 candidate bodies, all 113/120/113 external participants,
154/161/154 total bodies and the exact 15,886 declared pair inventory. Positive
Common material and its local context must be exported and independently read;
containment evaluation errors, missing pairs, duplicated pairs, missing body
comparisons and stale evidence fail execution.

The driver checks the full expected Git commit, clean worktree, required native
input hashes, native-report hash, reader source identity and source bytes before
and after execution. Every selected source file must match the actual HEAD tree's
Git blob identity, even if index flags hide a change from git status. Git replace
objects are disabled for identity checks and execution. It snapshots tracked Python, active design/integration JSON,
workflow, lock files and current product entry points. A sparse checkout may omit
archive blobs, but must retain these sources and every actual CAD/input fixture
used by the current suites. A source-only download is insufficient for native
execution; `design/product_geometry.json` and the existing readers identify the
required native template archives.

## Read the outcome

`report.json` separates these independent statements:

| Field | Meaning |
| --- | --- |
| `execution_checks_passed` | Every command, coverage check, identity check and independent readback completed. Exit zero means this field is true. |
| `finite_geometry` | `rejected`, `clear_at_selected_poses_only`, or `not_evaluated`. A completed rejected candidate is retained research evidence. |
| `physical_qualification` | Always `not_provided` by this workflow. |
| `candidate_go`, `fixture_fabrication_go`, `manufacturing_go` | Always false. This workflow does not grant release. |

A successful research job may therefore report `finite_geometry: rejected`.
An evaluation error is an execution failure; a measured positive Common with
complete diagnostics is a recorded geometric rejection. Passing finite scenes
does not prove continuous clearance, source material equivalence, STEP label
identity, supplier qualification or hardware operation.

Stage logs, native reports, complete STEP assemblies, positive Common contexts,
containment exports and independent readback remain in the output directory.
GitHub uploads this directory even when execution fails. A runner that never
starts has no execution evidence and cannot satisfy the required job.
