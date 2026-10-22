import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.decor_cost_engine import DecorCostEngine
from backend.app.services.vibe_aggregation_engine import VibeAggregationEngine
from backend.app.services.moodboard_generator import MoodboardCollageGenerator
from backend.app.schemas.vibe import VibeExtractionPayloadSchema, SingleImageVibeSchema

client = TestClient(app)


def create_dummy_image_bytes(color: str = "red", size: tuple = (200, 200)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_decor_cost_engine_formulas_and_ranges():
    # 1. Formula parsing tests
    assert DecorCostEngine.resolve_quantity_formula("1 fixed", guest_count=200) == 1
    assert DecorCostEngine.resolve_quantity_formula("2 units", guest_count=200) == 2
    assert DecorCostEngine.resolve_quantity_formula("1 per table", guest_count=200, table_size=10) == 20
    assert DecorCostEngine.resolve_quantity_formula("1 per 10 guests", guest_count=200) == 20
    assert DecorCostEngine.resolve_quantity_formula("1 per 25 guests", guest_count=250) == 10
    assert DecorCostEngine.resolve_quantity_formula("1 per 15 guests", guest_count=150) == 10
    assert DecorCostEngine.resolve_quantity_formula("invalid string", guest_count=200) == 1

    # 2. Cost range calculation tests
    # Tier 2 city (Jaipur: multiplier 0.68)
    cost_low, cost_high = DecorCostEngine.calculate_cost_range(
        category="stage_backdrop",
        cost_tier="medium",
        quantity=1,
        city="Jaipur"
    )
    assert cost_low == round(28000.0 * 0.68, 2)
    assert cost_high == round(45000.0 * 0.68, 2)
    assert cost_low < cost_high

    # Tier 1 city (Mumbai: multiplier 1.0)
    mumbai_low, mumbai_high = DecorCostEngine.calculate_cost_range(
        category="stage_backdrop",
        cost_tier="medium",
        quantity=1,
        city="Mumbai"
    )
    assert mumbai_low == 28000.0
    assert mumbai_high == 45000.0


def test_decor_base_rate_sanity_ceiling_regression():
    """
    Regression guard: Prevents order-of-magnitude typos or whole-package assumptions
    from being assigned to per-unit items.
    Asserts that no distributed medium-tier item resolves to > 3-5x another medium-tier item.
    """
    distributed_cats = DecorCostEngine.DISTRIBUTED_CATEGORIES
    structural_cats = DecorCostEngine.STRUCTURAL_CATEGORIES

    # 1. Distributed items ratio check within each tier
    for tier in ("low", "medium", "high"):
        lows = [DecorCostEngine.BASE_UNIT_COSTS[cat][tier][0] for cat in distributed_cats]
        highs = [DecorCostEngine.BASE_UNIT_COSTS[cat][tier][1] for cat in distributed_cats]

        ratio_low = max(lows) / min(lows)
        ratio_high = max(highs) / min(highs)

        # Sanity bound: max must not exceed 3.5x min across distributed items
        assert ratio_low <= 3.5, f"Tier '{tier}' low-bound ratio {ratio_low:.2f} exceeds 3.5x ceiling across distributed items"
        assert ratio_high <= 3.5, f"Tier '{tier}' high-bound ratio {ratio_high:.2f} exceeds 3.5x ceiling across distributed items"

    # 2. Structural installations ratio check within each tier
    for tier in ("low", "medium", "high"):
        lows = [DecorCostEngine.BASE_UNIT_COSTS[cat][tier][0] for cat in structural_cats]
        highs = [DecorCostEngine.BASE_UNIT_COSTS[cat][tier][1] for cat in structural_cats]

        ratio_low = max(lows) / min(lows)
        ratio_high = max(highs) / min(highs)

        assert ratio_low <= 4.0, f"Tier '{tier}' structural low ratio {ratio_low:.2f} exceeds 4.0x ceiling"
        assert ratio_high <= 4.0, f"Tier '{tier}' structural high ratio {ratio_high:.2f} exceeds 4.0x ceiling"

    # 3. Specific lighting sanity checks (the exact regression reported)
    lighting_medium = DecorCostEngine.BASE_UNIT_COSTS["lighting"]["medium"]
    assert lighting_medium[0] <= 1500.0, f"Lighting medium low-bound ₹{lighting_medium[0]} exceeds per-unit ceiling"
    assert lighting_medium[1] <= 2500.0, f"Lighting medium high-bound ₹{lighting_medium[1]} exceeds per-unit ceiling"

    # 4. End-to-end resolved comparison for 25 units in Jaipur (lighting vs table centerpiece)
    lighting_low, lighting_high = DecorCostEngine.calculate_cost_range(
        category="lighting",
        cost_tier="medium",
        quantity=25,
        city="Jaipur"
    )
    centerpiece_low, centerpiece_high = DecorCostEngine.calculate_cost_range(
        category="table_centerpiece",
        cost_tier="medium",
        quantity=25,
        city="Jaipur"
    )

    # Both must be in the sane ₹15k - ₹35k range, not ₹425k - ₹765k!
    assert 12000.0 <= lighting_low <= 25000.0, f"Lighting 25 units low was ₹{lighting_low:,.0f}, expected ₹12k - ₹25k"
    assert 22000.0 <= lighting_high <= 35000.0, f"Lighting 25 units high was ₹{lighting_high:,.0f}, expected ₹22k - ₹35k"

    # Sane parity: lighting and centerpiece for 25 units must be within 1.5x of each other
    assert 0.6 <= (lighting_low / centerpiece_low) <= 1.5
    assert 0.6 <= (lighting_high / centerpiece_high) <= 1.5


def test_vibe_aggregation_engine():
    payload = VibeExtractionPayloadSchema(
        images=[
            SingleImageVibeSchema(
                palette=["#FF9933", "#800020", "#FFD700", "#2E8B57", "#FFF8DC"],
                style_tags=["royal", "traditional", "palace"],
                materials=["brass", "silk"],
                flower_types=["marigold", "rose"]
            ),
            SingleImageVibeSchema(
                palette=["#FF9933", "#FFD700", "#D4AF37", "#800020", "#000000"],
                style_tags=["royal", "heritage", "grand"],
                materials=["brass", "terracotta"],
                flower_types=["marigold", "rajnigandha"]
            )
        ],
        overall_mood_words=["regal", "festive", "traditional"]
    )

    aggregated = VibeAggregationEngine.aggregate(payload=payload, text_description="Want regal royal atmosphere")
    assert len(aggregated["extracted_palette"]) == 5
    # #FF9933 and #FFD700 appeared in both images so should be dominant
    assert "#FF9933" in aggregated["extracted_palette"]
    assert "#FFD700" in aggregated["extracted_palette"]
    assert "royal" in aggregated["style_tags"]
    assert any(m.lower() == "regal" for m in aggregated["mood_words"])


def test_moodboard_collage_generator_pillow():
    img1 = create_dummy_image_bytes(color="#E2725B")
    img2 = create_dummy_image_bytes(color="#FFD700")
    img3 = create_dummy_image_bytes(color="#800020")

    collage_bytes = MoodboardCollageGenerator.generate_collage(
        image_bytes_list=[img1, img2, img3],
        palette=["#E2725B", "#FFD700", "#800020", "#2E8B57", "#FFF8DC"],
        theme_name="Royal Heritage Theme",
        style_tags=["Traditional", "Royal", "Festive"]
    )

    assert isinstance(collage_bytes, bytes)
    assert len(collage_bytes) > 1000

    # Verify image dimensions with Pillow
    result_img = Image.open(io.BytesIO(collage_bytes))
    assert result_img.size == (1200, 800)
    assert result_img.format in ("JPEG", "MPO")


def test_vibe_to_plan_stub_workflow_and_granular_acceptance():
    # 1. Create event
    intake_res = client.post(
        "/api/v1/events",
        json={
            "name": "Aarav & Ananya Wedding",
            "event_type": "Wedding",
            "city": "Jaipur",
            "guest_count": 250,
            "total_budget": 1500000.0,
            "host_name": "Aarav",
            "host_phone": "+919876543210"
        }
    )
    assert intake_res.status_code == 201
    event_id = intake_res.json()["id"]

    # 2. Upload vibe inspiration images + text description
    img_data1 = create_dummy_image_bytes(color="gold")
    img_data2 = create_dummy_image_bytes(color="maroon")

    files = [
        ("files", ("mood1.jpg", img_data1, "image/jpeg")),
        ("files", ("mood2.jpg", img_data2, "image/jpeg"))
    ]
    data = {
        "text_description": "Auspicious traditional Rajasthani palace wedding with heavy marigold and antique brass elements."
    }

    upload_res = client.post(
        f"/api/v1/events/{event_id}/vibe/upload",
        files=files,
        data=data
    )
    assert upload_res.status_code == 201
    profile = upload_res.json()
    assert profile["event_id"] == event_id
    assert profile["uploaded_image_count"] == 2
    assert len(profile["extracted_palette"]) == 5
    profile_id = profile["profile_id"]

    # 3. Generate Theme Proposal
    theme_res = client.post(
        f"/api/v1/events/{event_id}/vibe/{profile_id}/generate-theme"
    )
    assert theme_res.status_code == 201
    theme_data = theme_res.json()
    assert theme_data["theme_name"] != ""
    assert len(theme_data["palette"]) == 5
    assert len(theme_data["decor_items"]) >= 10
    assert theme_data["provider_used"] != ""

    # Verify decor items have positive computed quantities and ranges
    for item in theme_data["decor_items"]:
        assert item["computed_quantity"] >= 1
        assert item["cost_range_low"] > 0
        assert item["cost_range_high"] >= item["cost_range_low"]
        assert item["status"] == "proposed"
        assert item["sourcing_type"] in ("rent", "diy", "buy")

    # 4. Get Mood Board Image
    moodboard_res = client.get(
        f"/api/v1/events/{event_id}/vibe/{profile_id}/moodboard"
    )
    assert moodboard_res.status_code == 200
    assert moodboard_res.headers["content-type"] == "image/jpeg"
    assert len(moodboard_res.content) > 1000

    # 5. Accept an individual decor item (Granular acceptance)
    item_to_accept = theme_data["decor_items"][0]
    item_id = item_to_accept["id"]

    accept_res = client.post(
        f"/api/v1/events/{event_id}/vibe/decor-items/{item_id}/accept"
    )
    assert accept_res.status_code == 200
    accepted_data = accept_res.json()
    assert accepted_data["status"] == "accepted"
    assert accepted_data["budget_item_id"] is not None
    assert accepted_data["task_id"] is not None

    # Verify that the accepted item mapped into the event's master budget and tasks
    from backend.app.db.session import SessionLocal
    from backend.app.models.models import BudgetItem, Task

    with SessionLocal() as db_session:
        b_item = db_session.query(BudgetItem).filter(BudgetItem.id == accepted_data["budget_item_id"]).first()
        t_item = db_session.query(Task).filter(Task.id == accepted_data["task_id"]).first()

        assert b_item is not None
        assert b_item.category == "decor"
        assert float(b_item.planned_amount) == item_to_accept["cost_range_high"]

        assert t_item is not None
        assert t_item.title.startswith("Source")
        assert t_item.status == "pending"

    # 6. Reject another decor item
    item_to_reject = theme_data["decor_items"][1]
    reject_res = client.post(
        f"/api/v1/events/{event_id}/vibe/decor-items/{item_to_reject['id']}/reject"
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
