# Count correction to the retained execution basis

The execution basis said "There are 1,640 roots." That was a hand-added arithmetic
error. Direct counting of the unchanged complete 16 original certificates yields
**1,537 original roots**, with counts in original frame order:

169, 184, 131, 135, 85, 85, 90, 71, 1, 1, 128, 119, 205, 131, 1, 1.

The 44 non-tiny-root count is correct. The driver never uses the incorrect prose
count: it enumerates every root in every original certificate, records the
individual frame counts, and tests all 44 roots above the unchanged tiny rule.
The saved independent reader requires exact root count, order and identity in
every frame. The execution basis is retained byte-for-byte under its recorded
hash so that this correction does not rewrite the input to the actual run.
