import io
import logging
import re
from typing import Any

from PIL import Image

from backend.app.services.invitation.classic_royal import ClassicRoyalLayout
from backend.app.services.invitation.floral_festive import FloralFestiveLayout
from backend.app.services.invitation.fonts import (
    hex_to_rgb,
)
from backend.app.services.invitation.modern_minimal import ModernMinimalLayout
from backend.app.services.invitation.pdf_export import LosslessPDFExporter

logger = logging.getLogger(__name__)


class InvitationCardRenderer:
    """
    Server-side deterministic invitation card composition using Pillow (DEC-028).
    Supports multiple layout variants (classic_royal, modern_minimal, floral_festive),
    theme palette binding, muhurat indicators, and guest personalization (DEC-029).
    Exports both PNG and PDF from single composition pipeline (DEC-030).
    """

    WIDTH = 1200
    HEIGHT = 1800

    @staticmethod
    def _sanitize_font_text(text: str | None) -> str:
        """
        Scrubs curly template brackets and replaces unicode symbols not present
        in the Noto Sans Devanagari font (stars, bullets, box characters)
        to prevent FreeType .notdef missing glyph tofu square boxes.
        """
        if not text:
            return ""
        clean = re.sub(r"\{.*?\}", "", text)
        replacements = {
            "★": "",
            "☆": "",
            "•": " | ",
            "·": " - ",
            "▪": " | ",
            "▫": " | ",
            "◆": " | ",
            "◇": " | ",
            "✓": "",
            "✔": "",
            "□": "",
            "■": "",
        }
        for bad, good in replacements.items():
            clean = clean.replace(bad, good)
        clean = re.sub(r" +", " ", clean)
        return clean.strip()

    @classmethod
    def _sanitize_render_inputs(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str | None,
        wording_text: str,
        muhurat_time: str | None,
        ceremony_names: list[str] | None,
        guest_name: str | None,
    ) -> dict[str, Any]:
        clean_event = cls._sanitize_font_text(event_name) or "Celebration"
        clean_host = cls._sanitize_font_text(host_name)
        clean_date = cls._sanitize_font_text(date_str) or "Date to be confirmed"
        clean_venue = cls._sanitize_font_text(venue_str) or "Venue to be confirmed"
        clean_wording = (
            cls._sanitize_font_text(wording_text)
            or "You are cordially invited to celebrate with us."
        )
        clean_guest = cls._sanitize_font_text(guest_name) if guest_name else None
        clean_muhurat = cls._sanitize_font_text(muhurat_time) if muhurat_time else None
        clean_ceremonies = None
        if ceremony_names:
            clean_ceremonies = [cls._sanitize_font_text(c) for c in ceremony_names]

        return {
            "event_name": clean_event,
            "host_name": clean_host,
            "date_str": clean_date,
            "venue_str": clean_venue,
            "wording": clean_wording,
            "guest": clean_guest,
            "muhurat": clean_muhurat,
            "ceremonies": clean_ceremonies,
        }

    @classmethod
    def _resolve_palette_colors(
        cls, palette: list[str] | None
    ) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        raw = palette or ["#B45309", "#991B1B", "#FEF3C7", "#1E3A8A", "#D97706"]
        c1 = raw[0] if len(raw) > 0 else None
        c2 = raw[1] if len(raw) > 1 else None
        c3 = raw[2] if len(raw) > 2 else None
        return (
            hex_to_rgb(c1, (180, 83, 9)),
            hex_to_rgb(c2, (153, 27, 27)),
            hex_to_rgb(c3, (217, 119, 6)),
        )

    @classmethod
    def _dispatch_layout(
        cls,
        layout_variant: str,
        clean: dict[str, Any],
        guest_diet: str | None,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> Image.Image:
        primary, secondary, accent = colors
        args = (
            clean["event_name"],
            clean["host_name"],
            clean["date_str"],
            clean["venue_str"],
            clean["wording"],
            clean["muhurat"],
            clean["ceremonies"],
            clean["guest"],
            guest_diet,
            primary,
            secondary,
            accent,
        )
        if layout_variant == "modern_minimal":
            return cls._render_modern_minimal(*args)
        if layout_variant == "floral_festive":
            return cls._render_floral_festive(*args)
        return cls._render_classic_royal(*args)

    @classmethod
    def render_card(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str | None,
        wording_text: str,
        muhurat_time: str | None = None,
        ceremony_names: list[str] | None = None,
        guest_name: str | None = None,
        guest_diet: str | None = None,
        palette: list[str] | None = None,
        layout_variant: str = "classic_royal",
    ) -> tuple[bytes, bytes]:
        """
        Renders invitation card and returns (png_bytes, pdf_bytes).
        Strict Rule: ZERO raw template placeholders ({host_name}, {date}, etc.) in output.
        """
        clean = cls._sanitize_render_inputs(
            event_name,
            host_name,
            date_str,
            venue_str,
            wording_text,
            muhurat_time,
            ceremony_names,
            guest_name,
        )
        colors = cls._resolve_palette_colors(palette)
        image = cls._dispatch_layout(layout_variant, clean, guest_diet, colors)

        # Export to PNG and PDF
        png_io = io.BytesIO()
        image.save(png_io, format="PNG", optimize=True)
        png_bytes = png_io.getvalue()

        # Lossless PDF export (FlateDecode / zip compression) for true 300 DPI print quality
        pdf_bytes = cls._image_to_lossless_pdf(image, dpi=300.0)

        return png_bytes, pdf_bytes


    @classmethod
    def _image_to_lossless_pdf(cls, image: Image.Image, dpi: float = 300.0) -> bytes:
        return LosslessPDFExporter.image_to_lossless_pdf(image, dpi=dpi)

    @classmethod
    def _render_classic_royal(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str,
        wording: str,
        muhurat: str | None,
        ceremonies: list[str] | None,
        guest_name: str | None,
        guest_diet: str | None,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        return ClassicRoyalLayout._render_classic_royal(
            event_name,
            host_name,
            date_str,
            venue_str,
            wording,
            muhurat,
            ceremonies,
            guest_name,
            guest_diet,
            primary,
            secondary,
            accent,
        )

    @classmethod
    def _render_modern_minimal(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str,
        wording: str,
        muhurat: str | None,
        ceremonies: list[str] | None,
        guest_name: str | None,
        guest_diet: str | None,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        return ModernMinimalLayout._render_modern_minimal(
            event_name,
            host_name,
            date_str,
            venue_str,
            wording,
            muhurat,
            ceremonies,
            guest_name,
            guest_diet,
            primary,
            secondary,
            accent,
        )

    @classmethod
    def _render_floral_festive(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str,
        wording: str,
        muhurat: str | None,
        ceremonies: list[str] | None,
        guest_name: str | None,
        guest_diet: str | None,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        return FloralFestiveLayout._render_floral_festive(
            event_name,
            host_name,
            date_str,
            venue_str,
            wording,
            muhurat,
            ceremonies,
            guest_name,
            guest_diet,
            primary,
            secondary,
            accent,
        )
