# Native checkpoint transport

The original public checkpoint ZIP is 16,468,003 bytes, SHA-256 `b5a51bb87abc2d84be10bd24b0f7a1a8f20aa23bcc84666ecc9c9aeeaf97d6e7`. Its first base64 Git blob request exceeded the connector's observed 16 MiB request-body limit. The exact rejection is preserved separately. This was a transport failure; it did not change scientific results or move a branch.

The two `.zip.part-000` and `.zip.part-001` files are exact contiguous original bytes. Each part has its own SHA-256 and Git blob identity in `EXACT_ZIP_TRANSPORT_PARTS_V1.json`. Concatenation in that order has been checked byte-for-byte against the unchanged, fully member-verified original ZIP.

Run `python3 reassemble_native_evidence_zip_v1.py` from this directory, or give the directory as its sole argument. The script checks both parts and the full ZIP before creating a new ZIP exclusively. It refuses an existing output file.

The public checkpoint contains 1,909 selected original files: 452 are individually readable at their repository paths; 1,457 larger or geometry/binary originals are lossless ZIP members at their repository-relative paths. The ZIP's `ORIGINAL_FILE_MANIFEST.json` and `PUBLIC_NATIVE_ORIGINALS_PLAN_V1.json` bind all 1,909 paths, sizes and hashes. The complete native80, Near and Far scientific archives, including all prerequisites and original geometry, are separately bound and linked in `../NATIVE_FINITE_WITNESSES.md`.

Neither part is a separate scientific result. Publication does not claim that the specifically requested unavailable `a11b00f71231ef3516d2a79c73fa441c375ac755` has been pushed.
