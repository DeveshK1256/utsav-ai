"""
Unit Tests for Foundation Core Deterministic Engines
Covers: Budget scaling, E.164 phone normalization, DAG dependency cycles, and seating constraints.
"""

import re
import pytest
from typing import List, Dict, Any


from backend.app.services.budget_engine import BudgetScalingEngine, load_city_tiers_config

# --- 1. Deterministic Budget Scaling Engine ---
def compute_budget_breakdown(envelope: float, city_tier: str = "tier_1") -> Dict[str, float]:
    items = BudgetScalingEngine.compute_budget_allocation(envelope, "wedding", "mumbai" if city_tier == "tier_1" else ("jaipur" if city_tier == "tier_2" else "rural"), 350)
    return {item["category"]: item["planned_amount"] for item in items}


def test_budget_scaling_allocation_sums_to_total():
    envelope = 3500000.0  # ₹35 Lakhs
    breakdown = compute_budget_breakdown(envelope, city_tier="tier_1")
    total_allocated = sum(breakdown.values())
    assert abs(total_allocated - envelope) < 0.01
    assert breakdown["catering"] > breakdown["decor"]
    assert breakdown["venue"] > breakdown["photography"]


def test_budget_scaling_tier_multipliers():
    envelope = 1000000.0  # ₹10 Lakhs
    cfg = load_city_tiers_config()
    m = cfg["multipliers"]
    
    t1_expected = envelope * m["tier_1"]
    t2_expected = envelope * m["tier_2"]
    t3_expected = envelope * m["tier_3"]

    t1 = sum(compute_budget_breakdown(envelope, "tier_1").values())
    t2 = sum(compute_budget_breakdown(envelope, "tier_2").values())
    t3 = sum(compute_budget_breakdown(envelope, "tier_3").values())

    assert abs(t1 - t1_expected) < 0.01
    assert abs(t2 - t2_expected) < 0.01
    assert abs(t3 - t3_expected) < 0.01


# --- 2. Phone Number E.164 Normalization ---
def normalize_indian_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
    else:
        digits = cleaned

    if len(digits) != 10 or not digits.isdigit() or digits[0] not in "6789":
        raise ValueError(f"Invalid Indian mobile number: {phone}")

    return f"+91{digits}"


def test_phone_normalization_formats():
    assert normalize_indian_phone("+91 98765 43210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("+91-98765-43210") == "+919876543210"

    with pytest.raises(ValueError):
        normalize_indian_phone("12345")

    with pytest.raises(ValueError):
        normalize_indian_phone("5432167890")  # Invalid starting digit


# --- 3. DAG Task Dependency Scheduler & Cycle Detection ---
class DAGScheduler:
    def __init__(self):
        self.adj: Dict[str, List[str]] = {}

    def add_task(self, task_id: str, dependencies: List[str] = None):
        if task_id not in self.adj:
            self.adj[task_id] = []
        if dependencies:
            for dep in dependencies:
                if dep not in self.adj:
                    self.adj[dep] = []
                self.adj[dep].append(task_id)

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.adj:
            if node not in visited:
                if dfs(node):
                    return True
        return False


def test_dag_scheduler_valid_and_cyclic():
    dag = DAGScheduler()
    dag.add_task("book_venue", [])
    dag.add_task("finalize_caterer", ["book_venue"])
    dag.add_task("print_invites", ["finalize_caterer"])
    assert not dag.has_cycle()

    # Seed an illegal circular dependency
    dag.add_task("book_venue", ["print_invites"])
    assert dag.has_cycle()


# --- 4. Seating Constraint Checker ---
def validate_seating_allocation(tables: Dict[str, int], assignments: Dict[str, str], hard_conflicts: List[tuple]) -> bool:
    counts: Dict[str, int] = {}
    for guest, table in assignments.items():
        counts[table] = counts.get(table, 0) + 1
        if counts[table] > tables.get(table, 0):
            return False  # Table capacity exceeded

    for guest_a, guest_b in hard_conflicts:
        if guest_a in assignments and guest_b in assignments:
            if assignments[guest_a] == assignments[guest_b]:
                return False  # Hard conflict placed at same table

    return True


def test_seating_constraint_rules():
    tables = {"T1": 8, "T2": 8}
    assignments = {f"guest_{i}": "T1" for i in range(8)}
    hard_conflicts = [("guest_0", "guest_1")]

    # Fails because guest_0 and guest_1 are both at T1
    assert not validate_seating_allocation(tables, assignments, hard_conflicts)

    # Move guest_1 to T2 -> Valid
    assignments["guest_1"] = "T2"
    assert validate_seating_allocation(tables, assignments, hard_conflicts)
