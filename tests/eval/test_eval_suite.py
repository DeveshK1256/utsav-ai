"""
Evaluation Suite Test Runner
Validates the 35 Golden Sample Events against core system invariants.
"""

import json
import os
import pytest

EVAL_PATH = os.path.join(os.path.dirname(__file__), "sample_events.json")

def load_golden_events():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_golden_events_count_and_invariants():
    events = load_golden_events()
    assert len(events) >= 30, "Evaluation suite must contain at least 30 golden events"

    for ev in events:
        assert ev["guest_count"] > 0
        assert ev["budget_envelope"] > 0
        assert ev["city_tier"] in ["tier_1", "tier_2", "tier_3"]
        assert ev["expected_min_sub_events"] >= 1
        if ev["event_type"] == "wedding":
            assert ev["requires_muhurat_anchor"] is True
