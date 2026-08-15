"""
===================================================================
ANTIGRAVITY GOLD ARENA MASTER RUNNER
===================================================================
Main entry point for running Antigravity's isolated GOLD Research Arena.
"""

import os
import sys

ANTIGRAVITY_DIR = os.path.dirname(os.path.abspath(__file__))
ALPHALAB_DIR = os.path.dirname(ANTIGRAVITY_DIR)
sys.path.insert(0, ALPHALAB_DIR)
sys.path.insert(0, ANTIGRAVITY_DIR)

from AlphaLab_Antigravity.src.gold_arena_engine import run_antigravity_gold_arena

if __name__ == "__main__":
    run_antigravity_gold_arena()
