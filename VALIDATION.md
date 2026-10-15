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
