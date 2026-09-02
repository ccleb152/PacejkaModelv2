"""Ensures the repo root (and therefore the `pacejka` package) is importable
when running `pytest` from any working directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
