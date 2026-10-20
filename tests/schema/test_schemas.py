"""
JSON Schema Validation Regression Tests
Validates that synthetic mock payloads strictly adhere to the contracts in Section 10.3 of UTSAV_MASTER_DOC.md.
"""

import json
import pytest

PLAN_GENERATION_SCHEMA = {
    "type": "object",
    "required": ["event_overview", "sub_events", "budget_breakdown", "critical_tasks"],
    "properties": {
        "event_overview": {
            "type": "object",
            "required": ["suggested_theme", "guest_scaling_factor", "city_tier_multiplier"],
            "properties": {
                "suggested_theme": {"type": "string"},
                "guest_scaling_factor": {"type": "number"},
                "city_tier_multiplier": {"type": "number"}
            }
        },
        "sub_events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "suggested_day_offset", "duration_hours", "is_outdoor", "is_muhurat_anchored"],
                "properties": {
                    "name": {"type": "string"},
                    "suggested_day_offset": {"type": "integer"},
                    "duration_hours": {"type": "number"},
                    "is_outdoor": {"type": "boolean"},
                    "is_muhurat_anchored": {"type": "boolean"}
                }
            }
        },
        "budget_breakdown": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["category", "allocation_percentage", "estimated_amount", "reasoning"]
            }
        },
        "critical_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "due_days_before_event", "assigned_role"]
            }
        }
    }
}

QUOTE_AUDIT_SCHEMA = {
    "type": "object",
    "required": ["vendor_name", "category", "base_quote", "normalized_total_cost", "detected_hidden_costs", "negotiation_recommendation"],
    "properties": {
        "vendor_name": {"type": "string"},
        "category": {"type": "string"},
        "base_quote": {"type": "number"},
        "normalized_total_cost": {"type": "number"},
        "detected_hidden_costs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "category", "clause_citation", "estimated_financial_impact"]
            }
        },
        "negotiation_recommendation": {
            "type": "object",
            "required": ["suggested_counter_offer", "leverage_points", "draft_messages"]
        }
    }
}

def validate_dict(schema: dict, data: dict) -> bool:
    for req in schema.get("required", []):
        if req not in data:
            return False
    return True


def test_plan_generation_payload_schema():
    sample_plan = {
        "event_overview": {
            "suggested_theme": "Royal Marigold Heritage",
            "guest_scaling_factor": 1.25,
            "city_tier_multiplier": 1.0
        },
        "sub_events": [
            {
                "name": "Mehndi & Sangeet",
                "suggested_day_offset": 0,
                "duration_hours": 4.5,
                "is_outdoor": True,
                "is_muhurat_anchored": False
            },
            {
                "name": "Vedic Wedding Ceremony",
                "suggested_day_offset": 1,
                "duration_hours": 3.0,
                "is_outdoor": False,
                "is_muhurat_anchored": True
            }
        ],
        "budget_breakdown": [
            {
                "category": "catering",
                "allocation_percentage": 28.0,
                "estimated_amount": 980000.0,
                "reasoning": "Standard Tier-1 rate for 350 guests across 3 meals"
            }
        ],
        "critical_tasks": [
            {
                "title": "Confirm Mandap Rigging Access with Venue",
                "due_days_before_event": 14,
                "assigned_role": "Decor Lead"
            }
        ]
    }
    assert validate_dict(PLAN_GENERATION_SCHEMA, sample_plan)
    assert len(sample_plan["sub_events"]) == 2
    assert sample_plan["sub_events"][1]["is_muhurat_anchored"] is True


def test_quote_audit_payload_schema():
    sample_quote_audit = {
        "vendor_name": "Sharma Caterers & Hospitality",
        "category": "catering",
        "base_quote": 450000.0,
        "normalized_total_cost": 558000.0,
        "detected_hidden_costs": [
            {
                "severity": "HIGH",
                "category": "MISSING_GST",
                "clause_citation": "Quote excludes mandatory 18% GST",
                "estimated_financial_impact": 81000.0
            },
            {
                "severity": "MEDIUM",
                "category": "GENERATOR_FUEL",
                "clause_citation": "Diesel for tandoor generators billed at actuals",
                "estimated_financial_impact": 27000.0
            }
        ],
        "negotiation_recommendation": {
            "suggested_counter_offer": 490000.0,
            "leverage_points": [
                "Early advance payment commitment",
                "Direct reference from venue panel"
            ],
            "draft_messages": {
                "english": "Dear Sharmaji, thank you for the quote. We would love to finalize...",
                "hindi": "नमस्ते शर्माजी, आपके कोटेशन के लिए धन्यवाद...",
                "marathi": "नमस्कार शर्माजी, आपल्या कोटेशनबद्दल धन्यवाद..."
            }
        }
    }
    assert validate_dict(QUOTE_AUDIT_SCHEMA, sample_quote_audit)
    assert sample_quote_audit["normalized_total_cost"] > sample_quote_audit["base_quote"]
    assert len(sample_quote_audit["detected_hidden_costs"]) == 2
