# P0 safe restoration and reproducible unit entry

Actual qian-qi run: 272 tests, 17 groups, zero skips or failed assertions.
The first 262-test run stopped the material group at missing Shapely; its
original failure log is retained. The locked environment now supplies both
SciPy and Shapely; the ten material tests and twelve G2 tests actually run.
This is not a full motion, PCB ERC/DRC, supplier or physical qualification.

The archive utility now verifies before atomic no-clobber publication and
walks roots with no-follow directory descriptors. Twenty-two recovery tests
cover corruption, path/symlink/FIFO, target conflict, interruption and races.
A real 1,216-byte R50 Markdown original was fetched by exact Git blob and
segment SHA and restored through the CLI twice; identical destination inode
and mtime stayed unchanged, and a bad whole-file SHA did not alter it.
All 728 original metadata records fit the strict path/size rules; all 728
original byte streams were NOT reconstructed this run. Original archive
chunks and historical baseline/evidence bytes remain unchanged.

Eight runner tests reject zero discovery, omissions, skips, import errors,
expected failures and protected output paths. Root discovery covers new
repository tests; tools/verify.py is the full current-group entry.
