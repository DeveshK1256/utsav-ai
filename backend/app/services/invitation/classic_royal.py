from PIL import Image, ImageDraw, ImageFont

from backend.app.services.invitation.fonts import (
    FONT_BOLD_PATH,
    FONT_REGULAR_PATH,
    get_font,
    is_devanagari_text,
    truncate_with_ellipsis,
    wrap_text,
)


class ClassicRoyalLayout:
    WIDTH = 1200
    HEIGHT = 1800

    @classmethod
    def _draw_classic_borders(
        cls,
        draw: ImageDraw.ImageDraw,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        draw.rectangle([(40, 40), (cls.WIDTH - 40, cls.HEIGHT - 40)], outline=primary, width=6)
        draw.rectangle([(55, 55), (cls.WIDTH - 55, cls.HEIGHT - 55)], outline=accent, width=2)
        for cx, cy in [
            (40, 40),
            (cls.WIDTH - 40, 40),
            (40, cls.HEIGHT - 40),
            (cls.WIDTH - 40, cls.HEIGHT - 40),
        ]:
            draw.rectangle([(cx - 8, cy - 8), (cx + 8, cy + 8)], fill=secondary)

    @classmethod
    def _draw_classic_host(
        cls,
        draw: ImageDraw.ImageDraw,
        host_name: str | None,
        is_dev: bool,
        font_host: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        cur_y: int,
    ) -> int:
        if host_name:
            if is_dev:
                host_intro_lines = ["सस्नेह निमंत्रण", host_name, "आपल्या उपस्थितीचे नम्र आवाहन"]
            else:
                host_intro_lines = [
                    "Together with their families",
                    host_name,
                    "request the honor of your presence",
                ]
            for line in host_intro_lines:
                b = draw.textbbox((0, 0), line, font=font_host)
                draw.text(
                    ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y),
                    line,
                    fill=(70, 70, 70),
                    font=font_host,
                )
                cur_y += 40
        else:
            intro_line = (
                "आपणास व आपल्या परिवारास सस्नेह निमंत्रण"
                if is_dev
                else "We cordially request the honor of your presence"
            )
            b = draw.textbbox((0, 0), intro_line, font=font_host)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y),
                intro_line,
                fill=(70, 70, 70),
                font=font_host,
            )
            cur_y += 45
        return cur_y

    @classmethod
    def _draw_classic_date_muhurat(
        cls,
        draw: ImageDraw.ImageDraw,
        date_str: str,
        muhurat: str | None,
        is_dev: bool,
        font_badge: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        cur_y: int,
    ) -> int:
        box_w = 860
        box_h = 130 if muhurat else 90
        box_x1 = (cls.WIDTH - box_w) // 2
        box_y1 = cur_y
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + box_h
        draw.rectangle(
            [(box_x1, box_y1), (box_x2, box_y2)], fill=(255, 245, 230), outline=accent, width=2
        )

        date_display = truncate_with_ellipsis(date_str, font_badge, box_w - 40, draw)
        b = draw.textbbox((0, 0), date_display, font=font_badge)
        draw.text(
            ((cls.WIDTH - (b[2] - b[0])) // 2, box_y1 + 18),
            date_display,
            fill=primary,
            font=font_badge,
        )

        if muhurat:
            muhurat_prefix = "शुभ मुहूर्त: " if is_dev else "Shubh Muhurat: "
            muhurat_text = f"{muhurat_prefix}{muhurat}"
            b = draw.textbbox((0, 0), muhurat_text, font=font_sub)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, box_y1 + 68),
                muhurat_text,
                fill=secondary,
                font=font_sub,
            )

        return box_y2 + 45

    @classmethod
    def _draw_classic_venue(
        cls,
        draw: ImageDraw.ImageDraw,
        venue_str: str,
        is_dev: bool,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_venue: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        accent: tuple[int, int, int],
        cur_y: int,
    ) -> None:
        draw.line(
            [(cls.WIDTH // 2 - 120, cur_y), (cls.WIDTH // 2 + 120, cur_y)], fill=accent, width=2
        )
        cur_y += 25

        venue_intro = "स्थळ" if is_dev else "VENUE"
        b = draw.textbbox((0, 0), venue_intro, font=font_sub)
        draw.text(
            ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y),
            venue_intro,
            fill=(100, 100, 100),
            font=font_sub,
        )
        cur_y += 35

        venue_lines = wrap_text(venue_str, font_venue, cls.WIDTH - 240, draw)
        for v_line in venue_lines[:3]:
            b = draw.textbbox((0, 0), v_line, font=font_venue)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y),
                v_line,
                fill=(40, 40, 40),
                font=font_venue,
            )
            cur_y += 38

    @classmethod
    def _draw_classic_guest_footer(
        cls,
        draw: ImageDraw.ImageDraw,
        guest_name: str | None,
        guest_diet: str | None,
        is_dev: bool,
        font_guest: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
    ) -> None:
        footer_y = cls.HEIGHT - 220
        draw.line([(100, footer_y), (cls.WIDTH - 100, footer_y)], fill=(220, 215, 205), width=1)
        footer_y += 35

        if guest_name:
            guest_prefix = "यजमानांतर्फे निमंत्रक: " if is_dev else "Specially Invited: "
            guest_label = f"{guest_prefix}{guest_name}"
            guest_disp = truncate_with_ellipsis(guest_label, font_guest, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), guest_disp, font=font_guest)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, footer_y),
                guest_disp,
                fill=secondary,
                font=font_guest,
            )

            if guest_diet and guest_diet.lower() != "none":
                diet_prefix = "विशेष आदरातिथ्य: " if is_dev else "Special Hospitality: "
                diet_line = f"{diet_prefix}{guest_diet}"
                b = draw.textbbox((0, 0), diet_line, font=font_sub)
                draw.text(
                    ((cls.WIDTH - (b[2] - b[0])) // 2, footer_y + 50),
                    diet_line,
                    fill=(90, 90, 90),
                    font=font_sub,
                )
        else:
            generic_label = (
                "आपले व आपल्या परिवाराचे सहर्ष स्वागत"
                if is_dev
                else "Warmest Welcome to You and Your Family"
            )
            b = draw.textbbox((0, 0), generic_label, font=font_guest)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, footer_y),
                generic_label,
                fill=primary,
                font=font_guest,
            )

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
        bg_color = (255, 252, 245)  # Warm royal cream
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        cls._draw_classic_borders(draw, primary, secondary, accent)

        # Fonts - All text elements strictly map to the two bundled Noto Sans Devanagari fonts
        font_header_emblem = get_font(FONT_BOLD_PATH, 32)
        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_title = get_font(FONT_BOLD_PATH, 54)
        font_body = get_font(FONT_REGULAR_PATH, 30)
        font_badge = get_font(FONT_BOLD_PATH, 28)
        font_venue = get_font(FONT_REGULAR_PATH, 26)
        font_guest = get_font(FONT_BOLD_PATH, 34)
        font_sub = get_font(FONT_REGULAR_PATH, 24)

        is_dev = (
            is_devanagari_text(event_name)
            or is_devanagari_text(host_name)
            or is_devanagari_text(wording)
        )

        # Header Emblem
        emblem_text = (
            "|| शुभ विवाह ||"
            if "vivah" in event_name.lower() or "wedding" in event_name.lower()
            else "|| श्री गणेशाय नमः ||"
        )
        bbox = draw.textbbox((0, 0), emblem_text, font=font_header_emblem)
        w = bbox[2] - bbox[0]
        draw.text(((cls.WIDTH - w) // 2, 120), emblem_text, fill=secondary, font=font_header_emblem)

        # Host Introduction
        cur_y = cls._draw_classic_host(draw, host_name, is_dev, font_host, 200)
        cur_y += 30

        # Event Title
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 180, draw)
        for t_line in title_lines:
            b = draw.textbbox((0, 0), t_line, font=font_title)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), t_line, fill=primary, font=font_title
            )
            cur_y += 65
        cur_y += 20

        # Wording Paragraph
        wording_lines = wrap_text(wording, font_body, cls.WIDTH - 240, draw)
        for w_line in wording_lines[:4]:  # max 4 lines
            b = draw.textbbox((0, 0), w_line, font=font_body)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), w_line, fill=(50, 50, 50), font=font_body
            )
            cur_y += 44
        cur_y += 40

        # Date & Auspicious Muhurat Card/Pill
        cur_y = cls._draw_classic_date_muhurat(
            draw, date_str, muhurat, is_dev, font_badge, font_sub, primary, secondary, accent, cur_y
        )

        # Ceremonies / Sub-events if provided
        if ceremonies:
            c_text = " | ".join(ceremonies[:4])
            c_disp = truncate_with_ellipsis(c_text, font_sub, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), c_disp, font=font_sub)
            draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), c_disp, fill=accent, font=font_sub)
            cur_y += 45

        cls._draw_classic_venue(draw, venue_str, is_dev, font_sub, font_venue, accent, cur_y)
        cls._draw_classic_guest_footer(
            draw, guest_name, guest_diet, is_dev, font_guest, font_sub, primary, secondary
        )
        return img

    # ---------------------------------------------------------
    # Modern Minimal Helpers
    # ---------------------------------------------------------
