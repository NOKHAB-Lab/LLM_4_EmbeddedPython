"""Tests for ProgressManager: resume round-trip, corrupt-file safety, malformed input."""
import os, sys, glob, json
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from progress_manager import ProgressManager

def _rec(i):
    return {"metadata": {"id": f"{i:04d}", "category": "sensors", "subcategory": "temperature"},
            "complexity": "beginner"}

def test_resume_roundtrip(tmp_path):
    pm = ProgressManager(str(tmp_path), total_examples=10)
    pm.initialize(reset=True)
    for i in range(3):
        pm.record_completion(_rec(i), success=True)
    pm.save_progress()
    # a fresh instance must restore prior progress
    pm2 = ProgressManager(str(tmp_path), total_examples=10)
    pm2.initialize(reset=False)
    assert pm2.is_completed("0000") and pm2.is_completed("0002")
    assert not pm2.is_completed("0009")
    assert pm2.total_generated == 3

def test_corrupt_progress_file_is_not_silently_destroyed(tmp_path):
    pf = os.path.join(str(tmp_path), "generation_progress.json")
    with open(pf, "w", encoding="utf-8") as f:
        f.write("{ this is : not valid json ")
    pm = ProgressManager(str(tmp_path), total_examples=10)
    pm.initialize(reset=False)   # must detect corruption gracefully
    # the corrupt content must be backed up, not just overwritten with empty state
    backups = glob.glob(os.path.join(str(tmp_path), "*corrupt*"))
    assert backups, "corrupt progress file must be preserved (backed up), not silently destroyed"

def test_record_completion_tolerates_malformed_input(tmp_path):
    pm = ProgressManager(str(tmp_path), total_examples=10)
    pm.initialize(reset=True)
    # metadata missing 'subcategory' and no top-level 'complexity' -- must not raise
    pm.record_completion({"metadata": {"id": "0001", "category": "sensors"}}, success=True)

def test_atomic_save_leaves_no_tmp_file(tmp_path):
    pm = ProgressManager(str(tmp_path), total_examples=10)
    pm.initialize(reset=True)
    pm.record_completion(_rec(0), success=True)
    pm.save_progress()
    leftovers = glob.glob(os.path.join(str(tmp_path), "*.tmp"))
    assert not leftovers, f"temp files left behind: {leftovers}"
