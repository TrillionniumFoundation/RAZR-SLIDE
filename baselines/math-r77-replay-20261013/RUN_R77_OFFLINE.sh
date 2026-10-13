#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR_R77="$(mktemp -d -t r77-offline-XXXXXX)"
trap 'rm -rf "$TMPDIR_R77"' EXIT
python3 -m zipfile -e "$HERE/RAZR_SLIDE_R77_verified_incremental_hardgate_20261013.zip" "$TMPDIR_R77/release"
P="$HERE/parents"
export R77_R76_ZIP="$P/RAZR_SLIDE_R76_verified_incremental_hardgate_20261013.zip"
export R77_R75_ZIP="$P/RAZR_SLIDE_R75_verified_incremental_hardgate_20261013.zip"
export R77_R74_ZIP="$P/RAZR_SLIDE_R74_verified_incremental_hardgate_20261012.zip"
export R77_R41_OCC_SIDE_ZIP="$P/RAZR_SLIDE_R41_FPC_hardgate_delta_20261013.zip"
python3 "$TMPDIR_R77/release/R77_VERIFY_PACKAGE.py" "$HERE/RAZR_SLIDE_R77_verified_incremental_hardgate_20261013.zip"
python3 "$TMPDIR_R77/release/src/r77_scalar_envelope.py" \
  --r76 "$R77_R76_ZIP" --r75 "$R77_R75_ZIP" --r74 "$R77_R74_ZIP" --r41-occ-side "$R77_R41_OCC_SIDE_ZIP" --out "$TMPDIR_R77/recalc"
(cd "$TMPDIR_R77/release" && python3 -m unittest discover -s tests -p test_r77.py -v)
python3 - "$TMPDIR_R77" <<'PY'
from pathlib import Path
import hashlib,sys
p=Path(sys.argv[1]); a=p/'release/artifacts';b=p/'recalc'
for x in b.iterdir():
 assert x.read_bytes()==(a/x.name).read_bytes(),x.name
print('R77_OFFLINE_REPLAY_CHECK: results byte-identical, external parent ZIPs untouched')
PY
