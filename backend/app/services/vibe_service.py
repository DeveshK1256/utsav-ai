import logging
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.models.models import (
    BudgetItem,
    DecorItem,
    Event,
    EventLog,
    StyleProfile,
    Task,
    ThemeProposal,
    UploadedImage,
    generate_uuid,
)
from backend.app.services.decor_cost_engine import DecorCostEngine
from backend.app.services.llm_provider import (
    get_theme_generation_provider,
    get_vibe_extraction_provider,
)
from backend.app.services.moodboard_generator import MoodboardCollageGenerator
from backend.app.services.vibe_aggregation_engine import VibeAggregationEngine

logger = logging.getLogger(__name__)


class VibeService:
    @classmethod
    def _read_and_validate_images(
        cls, files: list[UploadFile]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if len(files) > 10:
            raise HTTPException(
                status_code=400, detail="Maximum 10 images allowed per style profile"
            )

        image_records = []
        raw_images_for_provider: list[dict[str, Any]] = []
        max_image_size_bytes = 5 * 1024 * 1024  # 5 MB limit per image

        for f in files:
            content = f.file.read()
            if not content:
                continue
            if len(content) > max_image_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Image '{f.filename or 'upload'}' exceeds 5MB limit ({len(content)} bytes)"
                    ),
                )
            m_type = f.content_type or "image/jpeg"
            raw_images_for_provider.append(
                {"bytes": content, "mime_type": m_type, "file_name": f.filename or "image.jpg"}
            )
            image_records.append(
                {"id": generate_uuid(), "content_type": m_type, "image_data": content}
            )

        return image_records, raw_images_for_provider

    @classmethod
    def upload_vibe_and_extract(
        cls,
        db: Session,
        event_id: str,
        files: list[UploadFile],
        text_description: str | None = None,
    ) -> StyleProfile:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        image_records, raw_images_for_provider = cls._read_and_validate_images(files)

        # Call extraction provider (real Gemini batched call or deterministic stub)
        provider = get_vibe_extraction_provider()
        extraction_res = provider.extract_vibe_from_images(
            images=raw_images_for_provider, text_description=text_description
        )

        # Aggregate palette and tags across images deterministically
        aggregated = VibeAggregationEngine.aggregate(
            payload=extraction_res, text_description=text_description
        )

        # Create StyleProfile record
        profile_id = generate_uuid()
        image_ids = [rec["id"] for rec in image_records]

        profile = StyleProfile(
            id=profile_id,
            event_id=event_id,
            uploaded_image_refs=image_ids,
            extracted_palette=aggregated["extracted_palette"],
            style_tags=aggregated["style_tags"],
            mood_words=aggregated["mood_words"],
            text_description=text_description,
        )
        db.add(profile)

        # Persist uploaded images (bytea per DEC-017)
        for rec in image_records:
            uploaded_img = UploadedImage(
                id=rec["id"],
                style_profile_id=profile_id,
                image_data=rec["image_data"],
                content_type=rec["content_type"],
            )
            db.add(uploaded_img)

        # Log event
        log = EventLog(
            event_id=event_id,
            action_type="style_profile_created",
            diff_payload={
                "style_profile_id": profile_id,
                "image_count": len(image_records),
                "palette": aggregated["extracted_palette"],
                "style_tags": aggregated["style_tags"],
            },
        )
        db.add(log)

        db.commit()
        db.refresh(profile)
        return profile

    @classmethod
    def generate_theme(cls, db: Session, event_id: str, profile_id: str) -> ThemeProposal:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        profile = (
            db.query(StyleProfile)
            .filter(StyleProfile.id == profile_id, StyleProfile.event_id == event_id)
            .first()
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Style profile not found")

        style_profile_dict = {
            "extracted_palette": profile.extracted_palette,
            "style_tags": profile.style_tags,
            "mood_words": profile.mood_words,
            "text_description": profile.text_description,
        }

        event_details_dict = {
            "event_type": event.event_type or "Wedding",
            "city": event.city or "Jaipur",
            "guest_count": event.guest_count or 250,
            "total_budget": float(event.total_budget or 1500000.0),
        }

        provider = get_theme_generation_provider()
        proposal_payload = provider.generate_theme_proposal(style_profile_dict, event_details_dict)

        provider_used = getattr(provider, "last_provider_used", "gemini-3-flash-preview")
        fallback_warning = getattr(provider, "last_fallback_warning", None)

        theme_id = generate_uuid()
        theme_record = ThemeProposal(
            id=theme_id,
            style_profile_id=profile_id,
            theme_name=proposal_payload.theme_name,
            palette=proposal_payload.palette,
            menu_direction=proposal_payload.menu_direction,
            playlist_genres=proposal_payload.playlist_genres,
            dress_code_suggestion=proposal_payload.dress_code_suggestion,
            invitation_design_brief=proposal_payload.invitation_design_brief,
            status="proposed",
            provider_used=provider_used,
            fallback_warning=fallback_warning,
        )
        db.add(theme_record)

        # Resolve quantities and cost ranges deterministically via DecorCostEngine
        guest_count = event.guest_count or 250
        city = event.city or "Jaipur"

        for item_data in proposal_payload.decor_items:
            qty = DecorCostEngine.resolve_quantity_formula(
                item_data.quantity_formula, guest_count=guest_count
            )
            cost_low, cost_high = DecorCostEngine.calculate_cost_range(
                category=item_data.category,
                cost_tier=item_data.cost_tier,
                quantity=qty,
                city=city,
                formula_str=item_data.quantity_formula,
            )

            decor_rec = DecorItem(
                id=generate_uuid(),
                theme_proposal_id=theme_id,
                category=item_data.category,
                name=item_data.name,
                quantity_formula=item_data.quantity_formula,
                computed_quantity=qty,
                cost_tier=item_data.cost_tier,
                cost_range_low=cost_low,
                cost_range_high=cost_high,
                sourcing_type=item_data.sourcing_type,
                status="proposed",
                reasoning=item_data.reasoning,
            )
            db.add(decor_rec)

        log = EventLog(
            event_id=event_id,
            action_type="theme_proposal_generated",
            diff_payload={
                "theme_id": theme_id,
                "theme_name": proposal_payload.theme_name,
                "item_count": len(proposal_payload.decor_items),
                "provider_used": provider_used,
            },
        )
        db.add(log)

        db.commit()
        db.refresh(theme_record)
        return theme_record

    @classmethod
    def get_moodboard(cls, db: Session, profile_id: str) -> bytes:
        profile = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Style profile not found")

        images = db.query(UploadedImage).filter(UploadedImage.style_profile_id == profile_id).all()
        image_bytes_list = [img.image_data for img in images if img.image_data]

        latest_theme = (
            db.query(ThemeProposal)
            .filter(ThemeProposal.style_profile_id == profile_id)
            .order_by(ThemeProposal.created_at.desc())
            .first()
        )

        theme_name = latest_theme.theme_name if latest_theme else "Wedding Vibe Moodboard"

        return MoodboardCollageGenerator.generate_collage(
            image_bytes_list=image_bytes_list,
            palette=profile.extracted_palette,
            theme_name=theme_name,
            style_tags=profile.style_tags,
        )

    @classmethod
    def accept_decor_item(cls, db: Session, item_id: str) -> DecorItem:
        item = db.query(DecorItem).filter(DecorItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Decor item not found")

        if item.status == "accepted":
            return item

        theme = db.query(ThemeProposal).filter(ThemeProposal.id == item.theme_proposal_id).first()
        if not theme:
            raise HTTPException(status_code=404, detail="Theme proposal not found")
        profile = db.query(StyleProfile).filter(StyleProfile.id == theme.style_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Style profile not found")
        event_id = profile.event_id

        # 1. Map to BudgetItem
        budget_item_id = generate_uuid()
        budget_item = BudgetItem(
            id=budget_item_id,
            event_id=event_id,
            category="decor",
            name=f"{item.name} ({item.computed_quantity} units)",
            scaling_rule="fixed",
            planned_amount=item.cost_range_high,
            actual_amount=0.0,
            is_paid=False,
            reasoning_spec={
                "vibe_to_plan": True,
                "formula": item.quantity_formula,
                "quantity": item.computed_quantity,
                "sourcing_type": item.sourcing_type,
                "cost_tier": item.cost_tier,
            },
        )
        db.add(budget_item)

        # 2. Map to Task
        task_id = generate_uuid()
        task = Task(
            id=task_id,
            event_id=event_id,
            title=f"Source {item.name} ({item.sourcing_type.upper()})",
            description=(
                f"Quantity: {item.computed_quantity}. Estimated Cost: "
                f"₹{item.cost_range_low:,.0f} - ₹{item.cost_range_high:,.0f} "
                f"({item.sourcing_type.upper()})"
            ),
            status="pending",
        )
        db.add(task)

        # 3. Update DecorItem
        item.budget_item_id = budget_item_id
        item.task_id = task_id
        item.status = "accepted"

        # Log
        log = EventLog(
            event_id=event_id,
            action_type="decor_item_accepted",
            diff_payload={
                "decor_item_id": item.id,
                "name": item.name,
                "budget_item_id": budget_item_id,
                "task_id": task_id,
                "allocated_amount": float(item.cost_range_high),
            },
        )
        db.add(log)

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def reject_decor_item(cls, db: Session, item_id: str) -> DecorItem:
        item = db.query(DecorItem).filter(DecorItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Decor item not found")

        item.status = "rejected"
        db.commit()
        db.refresh(item)
        return item
