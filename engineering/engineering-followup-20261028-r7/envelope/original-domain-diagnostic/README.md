# Completed original Line-plane source diagnosis

This directory preserves both actual diagnostic attempts. It is a source
diagnosis, with no CAD operation, new exterior-channel search, clearance
qualification, or physical pass.

Attempt 1 failed before reading the native inventory. Its code incorrectly
compared the original R4 report's raw gzip SHA with the recovered public
gzip SHA. The frozen public-input bridge maps the two byte identities and
records identical decoded JSON. This is a real input-binding preparation
failure, preserved in `attempt-1`.

Version 2 adds the original bridge as a bound input and checks the original
raw identity, the recovered public identity, the empty changed-string list,
and the exact decoded canonical JSON hash. All exact domain computations
and the 60-second / 536870912-byte address-space budget remain unchanged.
Its actual run completed in 1.3438780260003114 seconds with 241602560 bytes
reported peak RSS. The original six inputs remained unchanged.

The original R3E producer and independent reader agree on the complete
selected material metadata, whole-boundary hashes, and full original face
records. Case-028 material 3 faces 27 and 42 contain fourteen and four
Line occurrences. Material 1 is retained as provenance only.

Face 27's surface U upper interval excludes a small part of an original
Line support. The surface-only forward box differs from the inherited
R4 box at exactly three endpoints: x lower, y upper, and z upper. Taking
the hull of the original surface intervals and every full Line support
makes all six exact endpoints agree with the inherited box after adding
the whole original displacement D. Face 42 already agrees under either
domain. Two independent exact affine formulations, all four UV corners
and interval-support sums, agree.

The original exact fractions, individual Line endpoints, complete source
records, and output projection are in `attempt-2`. The displayed small
differences are not used as a tolerance; equality of all six rational
endpoints remains mandatory. This result justifies a new named source
model revision. It does not establish an actual new UV proof, native
bounded-face membership, a whole continuous-envelope pass, or G2.

The missing unpublished V8 sources and output bytes were not reconstructed
or reclassified. This diagnosis starts from the recovered original R3E,
R4 and V7 evidence.

`MANIFEST.json` lists every regular member other than itself with its byte
size and SHA-256. Source, contract, budget, failure and success records are
separate members. Root's independent static review is retained separately
under `r7-audit/envelope-domain-review`.
