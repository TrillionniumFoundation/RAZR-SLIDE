"""Configured manufacturing-suite bridge for the new checkpoint contract tests."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'integration'))
sys.path.insert(0, str(ROOT/'engineering/bearing-continuation-20261022'))
from continuation_test_cases import BearingContinuationTests
