from PIL import Image, ImageDraw, ImageFont

from backend.app.services.invitation.fonts import (
    FONT_BOLD_PATH,
    FONT_REGULAR_PATH,
    get_font,
    is_devanagari_text,
    wrap_text,
)


class ModernMinimalLayout:
    WIDTH = 1200
    HEIGHT = 1800

    @classmethod
    def _draw_modern_sidebar(
        cls,
        draw: ImageDraw.ImageDraw,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        draw.rectangle([(0, 0), (28, cls.HEIGHT)], fill=primary)
        draw.rectangle([(28, 0), (38, cls.HEIGHT)], fill=accent)

    @classmethod
    def _draw_modern_date_and_venue(
        cls,
        draw: ImageDraw.ImageDraw,
        date_str: str,
        muhurat: str | None,
        venue_str: str,
        is_dev: bool,
        font_label: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_meta: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_venue: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        start_x: int,
        cur_y: int,
    ) -> None:
        when_text = "दिनांक व वेळ" if is_dev else "WHEN"
        draw.text((start_x, cur_y), when_text, fill=accent, font=font_label)
        cur_y += 35
        draw.text((start_x, cur_y), date_str, fill=secondary, font=font_meta)
        cur_y += 45

        if muhurat:
            muh_prefix = "शुभ मुहूर्त: " if is_dev else "Auspicious Muhurat Window: "
            draw.text((start_x, cur_y), f"{muh_prefix}{muhurat}", fill=primary, font=font_sub)
            cur_y += 40

        cur_y += 30
        where_text = "स्थळ" if is_dev else "WHERE"
        draw.text((start_x, cur_y), where_text, fill=accent, font=font_label)
        cur_y += 35
        venue_lines = wrap_text(venue_str, font_venue, cls.WIDTH - 200, draw)
        for v_line in venue_lines[:3]:
            draw.text((start_x, cur_y), v_line, fill=(50, 50, 50), font=font_venue)
            cur_y += 38

    @classmethod
    def _draw_modern_guest_footer(
        cls,
        draw: ImageDraw.ImageDraw,
        guest_name: str | None,
        guest_diet: str | None,
        is_dev: bool,
        font_guest: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        start_x: int,
    ) -> None:
        footer_y = cls.HEIGHT - 220
        draw.line([(start_x, footer_y), (cls.WIDTH - 100, footer_y)], fill=(230, 230, 230), width=2)
        footer_y += 40

        if guest_name:
            guest_prefix = "यजमानांतर्फे निमंत्रक: " if is_dev else "Guest of Honor: "
            draw.text(
                (start_x, footer_y), f"{guest_prefix}{guest_name}", fill=primary, font=font_guest
            )
            if guest_diet:
                diet_prefix = "विशेष आदरातिथ्य: " if is_dev else "Preference: "
                diet_val = guest_diet if is_dev else guest_diet.capitalize()
                draw.text(
                    (start_x, footer_y + 55),
                    f"{diet_prefix}{diet_val}",
                    fill=(120, 120, 120),
                    font=font_sub,
                )
        else:
            gen_label = "आपले व आपल्या परिवाराचे सहर्ष स्वागत" if is_dev else "A Warm Welcome Awaits You"
            draw.text((start_x, footer_y), gen_label, fill=primary, font=font_guest)

    @classmethod
    def _render_modern_minimal(
        cls,
        event_name: str,
        host_name: str | None,
        date_str: str,
        venue_str: str,
        wording: str,
        muhurat: str | None,
        _ceremonies: list[str] | None,
        guest_name: str | None,
        guest_diet: str | None,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        bg_color = (255, 255, 255)
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        cls._draw_modern_sidebar(draw, primary, accent)

        font_label = get_font(FONT_BOLD_PATH, 24)
        font_title = get_font(FONT_BOLD_PATH, 58)
        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_body = get_font(FONT_REGULAR_PATH, 32)
        font_meta = get_font(FONT_BOLD_PATH, 30)
        font_venue = get_font(FONT_REGULAR_PATH, 26)
        font_guest = get_font(FONT_BOLD_PATH, 36)
        font_sub = get_font(FONT_REGULAR_PATH, 22)

        is_dev = (
            is_devanagari_text(event_name)
            or is_devanagari_text(host_name)
            or is_devanagari_text(wording)
        )

        start_x = 100
        cur_y = 120

        # Subtitle badge
        badge_text = "सस्नेह निमंत्रण" if is_dev else "CORDIAL INVITATION"
        draw.text((start_x, cur_y), badge_text, fill=accent, font=font_label)
        cur_y += 50

        # Event Title
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 200, draw)
        for t_line in title_lines:
            draw.text((start_x, cur_y), t_line, fill=primary, font=font_title)
            cur_y += 70
        cur_y += 30

        # Host
        if host_name:
            host_text = f"निमंत्रक: {host_name}" if is_dev else f"Hosted by {host_name}"
            draw.text((start_x, cur_y), host_text, fill=(100, 100, 100), font=font_host)
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

        cls._draw_modern_date_and_venue(
            draw,
            date_str,
            muhurat,
            venue_str,
            is_dev,
            font_label,
            font_meta,
            font_sub,
            font_venue,
            primary,
            secondary,
            accent,
            start_x,
            cur_y,
        )
        cls._draw_modern_guest_footer(
            draw, guest_name, guest_diet, is_dev, font_guest, font_sub, primary, start_x
        )
        return img

    # ---------------------------------------------------------
    # Floral Festive Helpers
    # ---------------------------------------------------------
