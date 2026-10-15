"""R42 full historical retest in an isolated test cell, not the source ZIP."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'parent_R41/baseline_R40'))
import r40_inherited
r40_inherited.CELL=ROOT/'verification/R42_fresh_R37_test_cell'
r40_inherited.OUT=ROOT/'verification/R42_parent_test_receipts'
r40_inherited.OUT.mkdir(exist_ok=True,parents=True)
r40_inherited.run()
