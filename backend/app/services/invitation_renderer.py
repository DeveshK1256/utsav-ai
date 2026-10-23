import io
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

# Path to bundled Noto Sans Devanagari fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
FONT_REGULAR_PATH = os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
FONT_BOLD_PATH = os.path.join(FONTS_DIR, "NotoSansDevanagari-Bold.ttf")


def hex_to_rgb(hex_str: Optional[str], default: Tuple[int, int, int] = (180, 83, 9)) -> Tuple[int, int, int]:
    if not hex_str or not isinstance(hex_str, str):
        return default
    clean = hex_str.lstrip("#").strip()
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) == 6:
        try:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
        except ValueError:
            return default
    return default


def get_font(path: str, size: int) -> ImageFont.ImageFont:
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    # System fallback or default
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text so no line exceeds max_width."""
    words = text.split()
    if not words:
        return []
    lines = []
    current_line = words[0]
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def truncate_with_ellipsis(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """Truncates text with ellipsis if it exceeds max_width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if (bbox[2] - bbox[0]) <= max_width:
        return text
    ellipsis = "..."
    truncated = text
    while truncated and (draw.textbbox((0, 0), truncated + ellipsis, font=font)[2] - draw.textbbox((0, 0), truncated + ellipsis, font=font)[0]) > max_width:
        truncated = truncated[:-1]
    return (truncated.strip() + ellipsis) if truncated else ellipsis


class InvitationCardRenderer:
    """
    Server-side deterministic invitation card composition using Pillow (DEC-028).
    Supports multiple layout variants (classic_royal, modern_minimal, floral_festive),
    theme palette binding, muhurat indicators, and guest personalization (DEC-029).
    Exports both PNG and PDF from single composition pipeline (DEC-030).
    """

    WIDTH = 1200
    HEIGHT = 1800

    @classmethod
    def render_card(
        cls,
        event_name: str,
        host_name: Optional[str],
        date_str: str,
        venue_str: Optional[str],
        wording_text: str,
        muhurat_time: Optional[str] = None,
        ceremony_names: Optional[List[str]] = None,
        guest_name: Optional[str] = None,
        guest_diet: Optional[str] = None,
        palette: Optional[List[str]] = None,
        layout_variant: str = "classic_royal"
    ) -> Tuple[bytes, bytes]:
        """
        Renders invitation card and returns (png_bytes, pdf_bytes).
        Strict Rule: ZERO raw template placeholders ({host_name}, {date}, etc.) in output.
        """
        # Sanitization: Ensure no literal curly-bracket placeholders leaked
        clean_event_name = re.sub(r"\{.*?\}", "", event_name).strip() or "Celebration"
        clean_host_name = re.sub(r"\{.*?\}", "", host_name or "").strip()
        clean_date_str = re.sub(r"\{.*?\}", "", date_str).strip() or "Date to be confirmed"
        clean_venue_str = re.sub(r"\{.*?\}", "", venue_str or "").strip() or "Venue to be confirmed"
        clean_wording = re.sub(r"\{.*?\}", "", wording_text).strip() or "You are cordially invited to celebrate with us."
        clean_guest = re.sub(r"\{.*?\}", "", guest_name or "").strip() if guest_name else None

        # Palette Extraction (default to Indian festive gold/vermilion/terracotta/cream)
        raw_palette = palette or ["#B45309", "#991B1B", "#FEF3C7", "#1E3A8A", "#D97706"]
        primary_color = hex_to_rgb(raw_palette[0] if len(raw_palette) > 0 else None, (180, 83, 9))
        secondary_color = hex_to_rgb(raw_palette[1] if len(raw_palette) > 1 else None, (153, 27, 27))
        accent_color = hex_to_rgb(raw_palette[2] if len(raw_palette) > 2 else None, (217, 119, 6))

        # Build image based on layout variant
        if layout_variant == "modern_minimal":
            image = cls._render_modern_minimal(
                clean_event_name, clean_host_name, clean_date_str, clean_venue_str,
                clean_wording, muhurat_time, ceremony_names, clean_guest, guest_diet,
                primary_color, secondary_color, accent_color
            )
        elif layout_variant == "floral_festive":
            image = cls._render_floral_festive(
                clean_event_name, clean_host_name, clean_date_str, clean_venue_str,
                clean_wording, muhurat_time, ceremony_names, clean_guest, guest_diet,
                primary_color, secondary_color, accent_color
            )
        else:  # default: classic_royal
            image = cls._render_classic_royal(
                clean_event_name, clean_host_name, clean_date_str, clean_venue_str,
                clean_wording, muhurat_time, ceremony_names, clean_guest, guest_diet,
                primary_color, secondary_color, accent_color
            )

        # Export to PNG and PDF
        png_io = io.BytesIO()
        image.save(png_io, format="PNG", optimize=True)
        png_bytes = png_io.getvalue()

        pdf_io = io.BytesIO()
        # Ensure RGB mode for PDF export
        rgb_image = image.convert("RGB")
        rgb_image.save(pdf_io, format="PDF", resolution=300.0)
        pdf_bytes = pdf_io.getvalue()

        return png_bytes, pdf_bytes

    @classmethod
    def _render_classic_royal(
        cls, event_name: str, host_name: str, date_str: str, venue_str: str,
        wording: str, muhurat: Optional[str], ceremonies: Optional[List[str]],
        guest_name: Optional[str], guest_diet: Optional[str],
        primary: Tuple[int, int, int], secondary: Tuple[int, int, int], accent: Tuple[int, int, int]
    ) -> Image.Image:
        bg_color = (255, 252, 245)  # Warm royal cream
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # 1. Ornate Borders
        # Outer border
        draw.rectangle([(40, 40), (cls.WIDTH - 40, cls.HEIGHT - 40)], outline=primary, width=6)
        # Inner thin border
        draw.rectangle([(55, 55), (cls.WIDTH - 55, cls.HEIGHT - 55)], outline=accent, width=2)
        # Corner accent squares
        for cx, cy in [(40, 40), (cls.WIDTH - 40, 40), (40, cls.HEIGHT - 40), (cls.WIDTH - 40, cls.HEIGHT - 40)]:
            draw.rectangle([(cx - 8, cy - 8), (cx + 8, cy + 8)], fill=secondary)

        # Fonts
        font_header_emblem = get_font(FONT_BOLD_PATH, 32)
        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_title = get_font(FONT_BOLD_PATH, 54)
        font_body = get_font(FONT_REGULAR_PATH, 30)
        font_badge = get_font(FONT_BOLD_PATH, 28)
        font_venue = get_font(FONT_REGULAR_PATH, 26)
        font_guest = get_font(FONT_BOLD_PATH, 34)
        font_sub = get_font(FONT_REGULAR_PATH, 24)

        # 2. Header Emblem
        emblem_text = "|| शुभ विवाह ||" if "vivah" in event_name.lower() or "wedding" in event_name.lower() else "|| श्री गणेशाय नमः ||"
        bbox = draw.textbbox((0, 0), emblem_text, font=font_header_emblem)
        w = bbox[2] - bbox[0]
        draw.text(((cls.WIDTH - w) // 2, 120), emblem_text, fill=secondary, font=font_header_emblem)

        # 3. Host Introduction
        cur_y = 200
        if host_name:
            host_intro = f"Together with their families\n{host_name}\nrequest the honor of your presence"
            for line in host_intro.split("\n"):
                b = draw.textbbox((0, 0), line, font=font_host)
                draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), line, fill=(70, 70, 70), font=font_host)
                cur_y += 40
        else:
            intro_line = "We cordially request the honor of your presence"
            b = draw.textbbox((0, 0), intro_line, font=font_host)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), intro_line, fill=(70, 70, 70), font=font_host)
            cur_y += 45

        cur_y += 30

        # 4. Event Title (Bold & prominent)
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 180, draw)
        for t_line in title_lines:
            b = draw.textbbox((0, 0), t_line, font=font_title)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), t_line, fill=primary, font=font_title)
            cur_y += 65

        cur_y += 20

        # 5. Wording Paragraph
        wording_lines = wrap_text(wording, font_body, cls.WIDTH - 240, draw)
        for w_line in wording_lines[:4]:  # max 4 lines
            b = draw.textbbox((0, 0), w_line, font=font_body)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), w_line, fill=(50, 50, 50), font=font_body)
            cur_y += 44

        cur_y += 40

        # 6. Date & Auspicious Muhurat Card/Pill
        box_w = 860
        box_h = 130 if muhurat else 90
        box_x1 = (cls.WIDTH - box_w) // 2
        box_y1 = cur_y
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + box_h
        draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill=(255, 245, 230), outline=accent, width=2)

        # Date text
        date_display = truncate_with_ellipsis(date_str, font_badge, box_w - 40, draw)
        b = draw.textbbox((0, 0), date_display, font=font_badge)
        draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, box_y1 + 18), date_display, fill=primary, font=font_badge)

        if muhurat:
            muhurat_text = f"★ Shubh Muhurat: {muhurat}"
            b = draw.textbbox((0, 0), muhurat_text, font=font_sub)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, box_y1 + 68), muhurat_text, fill=secondary, font=font_sub)

        cur_y = box_y2 + 45

        # 7. Ceremonies / Sub-events if provided
        if ceremonies and len(ceremonies) > 0:
            c_text = " • ".join(ceremonies[:4])
            c_disp = truncate_with_ellipsis(c_text, font_sub, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), c_disp, font=font_sub)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), c_disp, fill=accent, font=font_sub)
            cur_y += 45

        # 8. Venue Box
        draw.line([(cls.WIDTH // 2 - 120, cur_y), (cls.WIDTH // 2 + 120, cur_y)], fill=accent, width=2)
        cur_y += 25

        venue_intro = "VENUE"
        b = draw.textbbox((0, 0), venue_intro, font=font_sub)
        draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), venue_intro, fill=(100, 100, 100), font=font_sub)
        cur_y += 35

        venue_lines = wrap_text(venue_str, font_venue, cls.WIDTH - 240, draw)
        for v_line in venue_lines[:3]:
            b = draw.textbbox((0, 0), v_line, font=font_venue)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), v_line, fill=(40, 40, 40), font=font_venue)
            cur_y += 38

        # 9. Guest Personalization Footer (DEC-029)
        # Position at bottom
        footer_y = cls.HEIGHT - 220
        draw.line([(100, footer_y), (cls.WIDTH - 100, footer_y)], fill=(220, 215, 205), width=1)
        footer_y += 35

        if guest_name:
            guest_label = f"Specially Invited: {guest_name}"
            guest_disp = truncate_with_ellipsis(guest_label, font_guest, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), guest_disp, font=font_guest)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, footer_y), guest_disp, fill=secondary, font=font_guest)

            if guest_diet and guest_diet.lower() != "none":
                diet_line = f"Special Hospitality: {guest_diet.capitalize()}"
                b = draw.textbbox((0, 0), diet_line, font=font_sub)
                draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, footer_y + 50), diet_line, fill=(90, 90, 90), font=font_sub)
        else:
            generic_label = "Warmest Welcome to You and Your Family"
            b = draw.textbbox((0, 0), generic_label, font=font_guest)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, footer_y), generic_label, fill=primary, font=font_guest)

        return img

    @classmethod
    def _render_modern_minimal(
        cls, event_name: str, host_name: str, date_str: str, venue_str: str,
        wording: str, muhurat: Optional[str], ceremonies: Optional[List[str]],
        guest_name: Optional[str], guest_diet: Optional[str],
        primary: Tuple[int, int, int], secondary: Tuple[int, int, int], accent: Tuple[int, int, int]
    ) -> Image.Image:
        bg_color = (255, 255, 255)
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # Contemporary colored accent bars along left edge
        draw.rectangle([(0, 0), (28, cls.HEIGHT)], fill=primary)
        draw.rectangle([(28, 0), (38, cls.HEIGHT)], fill=accent)

        font_label = get_font(FONT_BOLD_PATH, 24)
        font_title = get_font(FONT_BOLD_PATH, 58)
        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_body = get_font(FONT_REGULAR_PATH, 32)
        font_meta = get_font(FONT_BOLD_PATH, 30)
        font_venue = get_font(FONT_REGULAR_PATH, 26)
        font_guest = get_font(FONT_BOLD_PATH, 36)
        font_sub = get_font(FONT_REGULAR_PATH, 22)

        start_x = 100
        cur_y = 120

        # Subtitle badge
        draw.text((start_x, cur_y), "CORDIAL INVITATION", fill=accent, font=font_label)
        cur_y += 50

        # Event Title
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 200, draw)
        for t_line in title_lines:
            draw.text((start_x, cur_y), t_line, fill=primary, font=font_title)
            cur_y += 70

        cur_y += 30

        # Host
        if host_name:
            draw.text((start_x, cur_y), f"Hosted by {host_name}", fill=(100, 100, 100), font=font_host)
            cur_y += 50

        cur_y += 20
        # Horizontal divider
        draw.line([(start_x, cur_y), (cls.WIDTH - 100, cur_y)], fill=(230, 230, 230), width=2)
        cur_y += 40

        # Wording text
        wording_lines = wrap_text(wording, font_body, cls.WIDTH - 200, draw)
        for w_line in wording_lines[:4]:
            draw.text((start_x, cur_y), w_line, fill=(40, 40, 40), font=font_body)
            cur_y += 48

        cur_y += 50

        # Date & Time block
        draw.text((start_x, cur_y), "WHEN", fill=accent, font=font_label)
        cur_y += 35
        draw.text((start_x, cur_y), date_str, fill=secondary, font=font_meta)
        cur_y += 45

        if muhurat:
            draw.text((start_x, cur_y), f"Auspicious Muhurat Window: {muhurat}", fill=primary, font=font_sub)
            cur_y += 40

        cur_y += 30

        # Venue block
        draw.text((start_x, cur_y), "WHERE", fill=accent, font=font_label)
        cur_y += 35
        venue_lines = wrap_text(venue_str, font_venue, cls.WIDTH - 200, draw)
        for v_line in venue_lines[:3]:
            draw.text((start_x, cur_y), v_line, fill=(50, 50, 50), font=font_venue)
            cur_y += 38

        # Guest personalization at bottom
        footer_y = cls.HEIGHT - 220
        draw.line([(start_x, footer_y), (cls.WIDTH - 100, footer_y)], fill=(230, 230, 230), width=2)
        footer_y += 40

        if guest_name:
            draw.text((start_x, footer_y), f"Guest of Honor: {guest_name}", fill=primary, font=font_guest)
            if guest_diet:
                draw.text((start_x, footer_y + 55), f"Preference: {guest_diet.capitalize()}", fill=(120, 120, 120), font=font_sub)
        else:
            draw.text((start_x, footer_y), "A Warm Welcome Awaits You", fill=primary, font=font_guest)

        return img

    @classmethod
    def _render_floral_festive(
        cls, event_name: str, host_name: str, date_str: str, venue_str: str,
        wording: str, muhurat: Optional[str], ceremonies: Optional[List[str]],
        guest_name: Optional[str], guest_diet: Optional[str],
        primary: Tuple[int, int, int], secondary: Tuple[int, int, int], accent: Tuple[int, int, int]
    ) -> Image.Image:
        # Festive light marigold background
        bg_color = (255, 250, 240)
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # Ornate double framing with scalloped effect
        draw.rectangle([(50, 50), (cls.WIDTH - 50, cls.HEIGHT - 50)], outline=secondary, width=4)
        draw.rectangle([(68, 68), (cls.WIDTH - 68, cls.HEIGHT - 68)], outline=accent, width=2)

        # Top decorative banner
        draw.rectangle([(150, 40), (cls.WIDTH - 150, 110)], fill=primary)
        font_badge = get_font(FONT_BOLD_PATH, 30)
        festive_banner = "UTSAHAM • CELEBRATION"
        bbox = draw.textbbox((0, 0), festive_banner, font=font_badge)
        draw.text(((cls.WIDTH - (bbox[2] - bbox[0])) // 2, 58), festive_banner, fill=(255, 255, 255), font=font_badge)

        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_title = get_font(FONT_BOLD_PATH, 52)
        font_body = get_font(FONT_REGULAR_PATH, 30)
        font_meta = get_font(FONT_BOLD_PATH, 32)
        font_sub = get_font(FONT_REGULAR_PATH, 24)
        font_guest = get_font(FONT_BOLD_PATH, 34)

        cur_y = 170

        # Host line
        if host_name:
            h_line = f"With the blessings of elders & family, {host_name}"
            h_wrapped = wrap_text(h_line, font_host, cls.WIDTH - 240, draw)
            for hl in h_wrapped:
                b = draw.textbbox((0, 0), hl, font=font_host)
                draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), hl, fill=(70, 60, 50), font=font_host)
                cur_y += 40
        else:
            hl = "With joy and gratitude, we invite you to join"
            b = draw.textbbox((0, 0), hl, font=font_host)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), hl, fill=(70, 60, 50), font=font_host)
            cur_y += 40

        cur_y += 20

        # Title
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 200, draw)
        for t_line in title_lines:
            b = draw.textbbox((0, 0), t_line, font=font_title)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), t_line, fill=secondary, font=font_title)
            cur_y += 65

        cur_y += 30

        # Wording
        w_lines = wrap_text(wording, font_body, cls.WIDTH - 240, draw)
        for wl in w_lines[:4]:
            b = draw.textbbox((0, 0), wl, font=font_body)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), wl, fill=(50, 45, 40), font=font_body)
            cur_y += 44

        cur_y += 50

        # Festive Date Centerpiece Cartouche
        cart_w = 880
        cart_h = 130 if muhurat else 85
        cx1 = (cls.WIDTH - cart_w) // 2
        cy1 = cur_y
        draw.rectangle([(cx1, cy1), (cx1 + cart_w, cy1 + cart_h)], fill=(255, 235, 210), outline=primary, width=2)

        b = draw.textbbox((0, 0), date_str, font=font_meta)
        draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cy1 + 16), date_str, fill=primary, font=font_meta)

        if muhurat:
            muh_txt = f"Auspicious Shubh Muhurat: {muhurat}"
            b = draw.textbbox((0, 0), muh_txt, font=font_sub)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cy1 + 72), muh_txt, fill=secondary, font=font_sub)

        cur_y = cy1 + cart_h + 40

        # Venue
        v_title = "— CELEBRATION VENUE —"
        b = draw.textbbox((0, 0), v_title, font=font_sub)
        draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), v_title, fill=accent, font=font_sub)
        cur_y += 35

        v_lines = wrap_text(venue_str, font_body, cls.WIDTH - 240, draw)
        for vl in v_lines[:3]:
            b = draw.textbbox((0, 0), vl, font=font_body)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), vl, fill=(40, 40, 40), font=font_body)
            cur_y += 40

        # Guest footer
        footer_y = cls.HEIGHT - 210
        draw.line([(120, footer_y), (cls.WIDTH - 120, footer_y)], fill=accent, width=1)
        footer_y += 35

        if guest_name:
            g_txt = f"Invited with Love: {guest_name}"
            g_disp = truncate_with_ellipsis(g_txt, font_guest, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), g_disp, font=font_guest)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, footer_y), g_disp, fill=secondary, font=font_guest)
        else:
            g_txt = "Blessings and Presence of You & Your Family Requested"
            b = draw.textbbox((0, 0), g_txt, font=font_guest)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, footer_y), g_txt, fill=primary, font=font_guest)

        return img
