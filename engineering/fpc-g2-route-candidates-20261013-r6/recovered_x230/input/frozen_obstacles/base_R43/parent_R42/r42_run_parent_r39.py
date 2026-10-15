"""R42 R39 independent source retest using a private test cell."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'parent_R41/baseline_R40'))
import r40_retest_r39
r40_retest_r39.CELL=ROOT/'verification/R42_fresh_R39_test_cell'
r40_retest_r39.run()
