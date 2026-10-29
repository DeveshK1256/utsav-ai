import re
from collections import Counter
from typing import Any, ClassVar

from backend.app.schemas.vibe import SingleImageVibeSchema, VibeExtractionPayloadSchema


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

    DEFAULT_PALETTE: ClassVar[list[str]] = ["#E2725B", "#FFD700", "#FFF8DC", "#2E8B57", "#800020"]

    @classmethod
    def _update_colors_and_tags(
        cls,
        vibe: SingleImageVibeSchema,
        color_counter: Counter[str],
        tag_counter: Counter[str],
    ) -> None:
        for hex_code in vibe.palette:
            norm = normalize_hex(hex_code)
            if norm:
                color_counter[norm] += 1
        for tag in vibe.style_tags:
            clean_tag = tag.strip().lower().replace(" ", "_")
            if clean_tag:
                tag_counter[clean_tag] += 1

    @classmethod
    def _update_single_vibe(
        cls,
        vibe: SingleImageVibeSchema,
        color_counter: Counter[str],
        tag_counter: Counter[str],
        material_counter: Counter[str],
        lighting_counter: Counter[str],
        flower_counter: Counter[str],
    ) -> None:
        cls._update_colors_and_tags(vibe, color_counter, tag_counter)
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

    @classmethod
    def _count_vibe_elements(
        cls, image_vibes: list[SingleImageVibeSchema]
    ) -> tuple[Counter[str], Counter[str], Counter[str], Counter[str], Counter[str]]:
        color_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        material_counter: Counter[str] = Counter()
        lighting_counter: Counter[str] = Counter()
        flower_counter: Counter[str] = Counter()

        for vibe in image_vibes:
            cls._update_single_vibe(
                vibe, color_counter, tag_counter, material_counter, lighting_counter, flower_counter
            )

        return color_counter, tag_counter, material_counter, lighting_counter, flower_counter

    @classmethod
    def _resolve_top_palette(cls, color_counter: Counter[str]) -> list[str]:
        top_palette = [c for c, _ in color_counter.most_common(5)]
        if len(top_palette) < 5:
            for def_c in cls.DEFAULT_PALETTE:
                if def_c not in top_palette:
                    top_palette.append(def_c)
                if len(top_palette) == 5:
                    break
        return top_palette[:5]

    @classmethod
    def _append_text_description_words(
        cls, mood_words: list[str], text_description: str | None
    ) -> None:
        if text_description:
            text_words = re.findall(r"\b[A-Za-z]{4,}\b", text_description)
            for w in text_words[:3]:
                cap = w.capitalize()
                if cap not in mood_words:
                    mood_words.append(cap)

    @classmethod
    def _synthesize_mood_words(
        cls,
        top_tags: list[str],
        lighting_counter: Counter[str],
        material_counter: Counter[str],
        overall_mood_words: list[str] | None,
        text_description: str | None,
    ) -> list[str]:
        mood_words = []
        if overall_mood_words:
            mood_words.extend([mw.strip().title() for mw in overall_mood_words])

        for tag in top_tags[:4]:
            t_title = tag.replace("_", " ").title()
            if t_title not in mood_words:
                mood_words.append(t_title)
        for light, _ in lighting_counter.most_common(2):
            l_title = light.replace("_", " ").title()
            if l_title not in mood_words:
                mood_words.append(l_title)
        for mat, _ in material_counter.most_common(2):
            m_title = f"{mat.replace('_', ' ').title()} accents"
            if m_title not in mood_words:
                mood_words.append(m_title)

        cls._append_text_description_words(mood_words, text_description)

        return list(dict.fromkeys(mood_words))[:8]

    @classmethod
    def aggregate_vibe_profiles(
        cls,
        image_vibes: list[SingleImageVibeSchema],
        text_description: str | None = None,
        overall_mood_words: list[str] | None = None,
    ) -> dict[str, Any]:
        colors, tags, materials, lighting, flowers = cls._count_vibe_elements(image_vibes)

        top_palette = cls._resolve_top_palette(colors)
        top_tags = [t for t, _ in tags.most_common(8)]
        if not top_tags:
            top_tags = ["traditional_indian", "vibrant_celebration", "floral_grandeur"]

        mood_words = cls._synthesize_mood_words(
            top_tags, lighting, materials, overall_mood_words, text_description
        )

        return {
            "extracted_palette": top_palette,
            "style_tags": top_tags,
            "materials": [m for m, _ in materials.most_common(5)],
            "flower_types": [f for f, _ in flowers.most_common(5)],
            "mood_words": mood_words,
            "text_description": text_description,
        }

    @classmethod
    def aggregate(
        cls,
        payload: VibeExtractionPayloadSchema | SingleImageVibeSchema | list[SingleImageVibeSchema],
        text_description: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(payload, VibeExtractionPayloadSchema):
            images: list[SingleImageVibeSchema] = payload.images
            overall_mood_words = payload.overall_mood_words
        elif isinstance(payload, list):
            images = payload
            overall_mood_words = None
        else:
            images = [payload]
            overall_mood_words = None

        return cls.aggregate_vibe_profiles(
            image_vibes=images,
            text_description=text_description,
            overall_mood_words=overall_mood_words,
        )
