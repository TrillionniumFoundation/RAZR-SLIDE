# R9: executed readback of the original numerical qualification

The original N15 numerical qualification already existed. R9 recovered its
immutable evidence and executed new independent products on the observed
Python 3.12.14 / NumPy 2.3.5 / SciPy 1.17.0 runtime. It did not rerun a solver
or claim the original NumPy 2.5.4 / SciPy 1.18.1 environment.

`R9_NUMERICAL_SCOPE.json` is the controlling result and binds the result files.
`R9_NUMERICAL_READBACK_PLAN.json` records capacity, time and algorithm choices
before the numerical readbacks. Sparse products run serially; original CSC
buffers, full fields, RHS, operation order and the `1e-7` gate are unchanged.

## Executed results

| Check | Result |
| --- | --- |
| Panel original five | All five pass; maximum `9.983337773558199e-8`, byte-identical saved residuals. |
| Panel correction process | Unchanged original v3 reader executes 45 native gates, 1262 exact before/after equations, seven unchanged anchors and all 36180 candidate-table rows. |
| Frame original five | All five pass; maximum `5.659897926075834e-9`, byte-identical saved residuals. |
| Four original external loads | All scalar residuals and the genuine two-dimensional block residual match byte for byte; maximum `2.4101609596982598e-11`. |
| Complete saved H | Both bodies cover exactly 3885 unique columns; all 7770 basis RHS and saved projection hashes are recomputed. Raw and original-block-symmetrized H match the historical arrays. |
| Original cache restore | The unchanged `ExactResponseCache.restore` executes exactly five ordered SHA-bound saved full-field callbacks; maximum relative error `1.1659935073707673e-8`, under the original `2e-7` gate. |
| Input recovery | Nine immutable archive/matrix identities match; 908 indexed package members match their original byte lengths and SHA256. |

No full K products for all 7770 H columns are asserted. Their successful full
fields were not all retained historically. R9 verifies the recorded finite
basis evidence and saved H bytes; it does not manufacture the missing fields.

## Retained discrepancies and failures

The first four-load reader stopped on an incorrect JSON field name. Its source
and failed report remain. Version 2 reads the original `ratio` field and uses
the original `F_full` denominator.

The first H reader rejected the intentionally retained failed frame `8:520`
attempt. Version 2 selects exactly the report SHA roster bound by the original
successful reader. It explicitly retains and excludes the failed partial block.

The additional whole-seed replay stops on an actual cross-runtime discrepancy:
`G`, `qfree`, `initialgap`, combined C and H match bit for bit, while 9 of the 24
`loadG = R.T @ F` entries differ by at most `2.220446049250313e-16`. The exact
24-entry rational dot-product reference, original values and new values are
preserved in `R9_SEED_ROUNDING_DIAGNOSTIC.json` and `seed-rounding-arrays/`.
Whole-seed bitwise replay on this runtime remains false. No acceptance limit
was changed, and the historical source-bound N15 qualification is retained.

## Reproduction sources and input layout

The immutable archive names, sizes and hashes are listed in
`R9_ORIGINAL_ARCHIVE_IDENTITIES.json`. Recreate a private work directory with
the following extracted subdirectories:

- `n13/`: original N13 scientific ZIP; `n12/`: its unchanged nested N12 ZIP.
- `n14/`: original N14 frame checkpoint ZIP.
- `frame-volume/`: original frame L2 tar.xz, preserving `frame/level-2/`.
- `panel-h/`, `frame-h/`: the two original H checkpoint ZIPs.
- `seed/`: original N15 linear seed ZIP.
- A separately supplied N15 scientific directory with the four-load arrays,
  original combined-H report and original source identities.

The panel replay uses the unchanged `n13/source/current/readback_n13.py` with
`--input n12 --run n13/native/N13-v3 --output NEW_FILE`. The new
`read_saved_fields.py` accepts `frame-five` and `panel-four-loads` modes, with
explicit `--volume`, `--C`, `--report`, `--fields`, and fresh `--output` paths.
`read_saved_h_restore.py` takes the private work directory, N15 directory,
and the fresh panel/frame reports. `read_saved_seed.py` consumes its result
and the fresh four-load report. `diagnose_seed_rounding.py` performs the exact
24-dot-product investigation without replacing the failed replay result.

All numeric readers ran with `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and
the original external 180-second supervisor. The original supervisor samples
the launcher RSS in this nested runtime; its low leader RSS is not a numerical
worker peak. The actual reader `getrusage` peaks are recorded separately.
Original unprojected execution logs/commands are retained in the private R9
numeric evidence package; the public projection binds their SHA and length.

## Qualification boundary

This closes readback of the original finite numerical scope. It does not
qualify arbitrary-RHS inversion, a finite-QP checkpoint/resume, the current
K1/K3 structural geometry, physical specimen identity, or G3–G5. The saved
original input and every historical rejection remain unchanged.
