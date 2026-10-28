import re
from collections import Counter
from typing import Any

from backend.app.schemas.vibe import SingleImageVibeSchema


def normalize_hex(color_str: str) -> str | None:
    """Normalizes hex color string to uppercase #RRGGBB format."""
    c = color_str.strip().upper()
    if not c.startswith("#"):
        c = "#" + c
    if re.match(r"^#[0-9A-F]{6}$", c):
        return c
    if re.match(r"^#[0-9A-F]{3}$", c):
        return f"#{c[1] * 2}{c[2] * 2}{c[3] * 2}"
    return None


class VibeAggregationEngine:
    """
    Pure Python deterministic aggregation engine for multi-image vision outputs.
    Zero LLM involvement. Easily unit-tested.
    """

    @classmethod
    def aggregate_vibe_profiles(
        cls,
        image_vibes: list[SingleImageVibeSchema],
        text_description: str | None = None,
        overall_mood_words: list[str] | None = None,
    ) -> dict[str, Any]:
        color_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        material_counter: Counter[str] = Counter()
        lighting_counter: Counter[str] = Counter()
        flower_counter: Counter[str] = Counter()

        for vibe in image_vibes:
            for hex_code in vibe.palette:
                norm = normalize_hex(hex_code)
                if norm:
                    color_counter[norm] += 1

            for tag in vibe.style_tags:
                clean_tag = tag.strip().lower().replace(" ", "_")
                if clean_tag:
                    tag_counter[clean_tag] += 1

            for mat in vibe.materials:
                clean_mat = mat.strip().lower().replace(" ", "_")
                if clean_mat:
                    material_counter[clean_mat] += 1

            if vibe.lighting_mood:
                lighting_counter[vibe.lighting_mood.strip().lower()] += 1

            for flower in vibe.flower_types:
                clean_fl = flower.strip().lower()
                if clean_fl:
                    flower_counter[clean_fl] += 1

        # Fallback default palette if no colors extracted
        default_palette = ["#E2725B", "#FFD700", "#FFF8DC", "#2E8B57", "#800020"]
        top_palette = [c for c, _ in color_counter.most_common(5)]
        if len(top_palette) < 5:
            for def_c in default_palette:
                if def_c not in top_palette:
                    top_palette.append(def_c)
                if len(top_palette) == 5:
                    break

        # Top 5-8 style tags
        top_tags = [t for t, _ in tag_counter.most_common(8)]
        if not top_tags:
            top_tags = ["traditional_indian", "vibrant_celebration", "floral_grandeur"]

        # Synthesize mood words from tags, lighting, materials, and overall mood keywords
        mood_words = []
        if overall_mood_words:
            for mw in overall_mood_words:
                mood_words.append(mw.strip().title())

        for tag in top_tags[:4]:
            tag_title = tag.replace("_", " ").title()
            if tag_title not in mood_words:
                mood_words.append(tag_title)
        for light, _ in lighting_counter.most_common(2):
            l_title = light.replace("_", " ").title()
            if l_title not in mood_words:
                mood_words.append(l_title)
        for mat, _ in material_counter.most_common(2):
            m_title = f"{mat.replace('_', ' ').title()} accents"
            if m_title not in mood_words:
                mood_words.append(m_title)

        if text_description:
            # Tokenize words from text description
            text_words = re.findall(r"\b[A-Za-z]{4,}\b", text_description)
            for w in text_words[:3]:
                if w.capitalize() not in mood_words:
                    mood_words.append(w.capitalize())

        return {
            "extracted_palette": top_palette[:5],
            "style_tags": top_tags,
            "materials": [m for m, _ in material_counter.most_common(5)],
            "flower_types": [f for f, _ in flower_counter.most_common(5)],
            "mood_words": list(dict.fromkeys(mood_words))[:8],
            "text_description": text_description,
        }

    @classmethod
    def aggregate(cls, payload: Any, text_description: str | None = None) -> dict[str, Any]:
        images = getattr(payload, "images", payload)
        overall_mood_words = getattr(payload, "overall_mood_words", None)
        return cls.aggregate_vibe_profiles(
            image_vibes=images,
            text_description=text_description,
            overall_mood_words=overall_mood_words,
        )
