# Reproduce current research tests

Use Python 3.12 and uv. From the repository root: `uv sync --locked`, then
`uv run --locked python -B tools/verify.py` (or `make test`). Each historical
module runs in a separate process; R50 topology receives an explicit src path.
The locked environment supplies SciPy rather than changing any shared venv.

`tools/test_suites.json` lists the current suites, including recovered R6 G2.
Zero discovery, fewer tests than listed, import failure, skips, unexpected or
expected failures, timeout and modified source bytes are all failures.
`--suite ID` is diagnostic scope only. Reports include actual test IDs and
software versions in a NEW .runs directory; `--output` must also be new.
Frozen sources, rejected experiments and old receipts are not rewritten.

This entry does not run full motion grids, native KiCad ERC/DRC, supplier
qualification or physical tests. A passing run keeps candidate_go and
manufacturing_go false. Raw archive chunks are not needed for unit tests;
full `archive/restore.py --verify` needs every exact archive blob.

Safe restoration: POSIX directory-descriptor/no-follow operations are
required. Use real directory paths rather than symlinked /tmp on macOS.
Verified complete bytes are published atomically without overwriting; an
identical regular destination is accepted without mutation. Changed files,
symlinks, special files and unsafe paths are rejected. Power/process death
may leave a private temporary file, never a partially published original.
Directory rename by an administrator/noncooperating writer is outside this
restorer's confinement guarantee. No historical archive bytes are modified.


The Research validation workflow uses the same sparse source selection and
locked environment, runs every configured suite, and retains raw reports on
success or failure. It does not need archive blobs or rewrite frozen evidence.
The suite-total field is checked against the actual declared suite minima.

For the new empty-shell geometry study and builder-free native readback:

```sh
uv run --locked python -B integration/phone_layout.py --output /tmp/razr-layout-new
uv run --locked python -B integration/verify_phone_layout.py --report /tmp/razr-layout-new/report.json --output /tmp/razr-layout-new/readback.json
```

Use a new output directory. This creates project-owned study STEP, explicitly
retains the rectangular overlap negative control, and records the cost in
empty cavity space. It is not an OEM cavity, a selected phone assembly, a
battery-capacity estimate or physical qualification. Both programs use the
same native CAD kernel; independent readback is not cross-kernel validation.


The mounted-cartridge workflow additionally generates `mounted_mechanism.py`
and independently rereads it with `verify_mounted_mechanism.py`. It retains
all static pairs, cassette insertion, nominal screw and finite tool-shaft paths,
new local motion pairs, and the direct-rigid-coupling rejection. Shell clearance
through both complete translations is not coupled B-to-KEY operation.
