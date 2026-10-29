from PIL import Image, ImageDraw, ImageFont

from backend.app.services.invitation.fonts import (
    FONT_BOLD_PATH,
    FONT_REGULAR_PATH,
    get_font,
    is_devanagari_text,
    truncate_with_ellipsis,
    wrap_text,
)


class FloralFestiveLayout:
    WIDTH = 1200
    HEIGHT = 1800

    @classmethod
    def _draw_floral_framing(
        cls,
        draw: ImageDraw.ImageDraw,
        is_dev: bool,
        font_badge: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        draw.rectangle([(50, 50), (cls.WIDTH - 50, cls.HEIGHT - 50)], outline=secondary, width=4)
        draw.rectangle([(68, 68), (cls.WIDTH - 68, cls.HEIGHT - 68)], outline=accent, width=2)
        draw.rectangle([(150, 40), (cls.WIDTH - 150, 110)], fill=primary)
        festive_banner = "उत्सव — आनंद सोहळा" if is_dev else "UTSAHAM — CELEBRATION"
        bbox = draw.textbbox((0, 0), festive_banner, font=font_badge)
        draw.text(
            ((cls.WIDTH - (bbox[2] - bbox[0])) // 2, 58),
            festive_banner,
            fill=(255, 255, 255),
            font=font_badge,
        )

    @classmethod
    def _draw_floral_host(
        cls,
        draw: ImageDraw.ImageDraw,
        host_name: str | None,
        is_dev: bool,
        font_host: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        cur_y: int,
    ) -> int:
        if host_name:
            h_line = (
                f"ज्येष्ठांच्या आशीर्वादाने, {host_name}"
                if is_dev
                else f"With the blessings of elders & family, {host_name}"
            )
            h_wrapped = wrap_text(h_line, font_host, cls.WIDTH - 240, draw)
            for hl in h_wrapped:
                b = draw.textbbox((0, 0), hl, font=font_host)
                draw.text(
                    ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), hl, fill=(70, 60, 50), font=font_host
                )
                cur_y += 40
        else:
            hl = (
                "सस्नेह निमंत्रणपूर्वक आपणास आग्रहाचे आमंत्रण"
                if is_dev
                else "With joy and gratitude, we invite you to join"
            )
            b = draw.textbbox((0, 0), hl, font=font_host)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), hl, fill=(70, 60, 50), font=font_host
            )
            cur_y += 40
        return cur_y

    @classmethod
    def _draw_floral_cartouche(
        cls,
        draw: ImageDraw.ImageDraw,
        date_str: str,
        muhurat: str | None,
        is_dev: bool,
        font_meta: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        cur_y: int,
    ) -> int:
        cart_w = 880
        cart_h = 130 if muhurat else 85
        cx1 = (cls.WIDTH - cart_w) // 2
        cy1 = cur_y
        draw.rectangle(
            [(cx1, cy1), (cx1 + cart_w, cy1 + cart_h)],
            fill=(255, 235, 210),
            outline=primary,
            width=2,
        )

        b = draw.textbbox((0, 0), date_str, font=font_meta)
        draw.text(
            ((cls.WIDTH - (b[2] - b[0])) // 2, cy1 + 16), date_str, fill=primary, font=font_meta
        )

        if muhurat:
            muh_prefix = "शुभ मुहूर्त: " if is_dev else "Auspicious Shubh Muhurat: "
            muh_txt = f"{muh_prefix}{muhurat}"
            b = draw.textbbox((0, 0), muh_txt, font=font_sub)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cy1 + 72), muh_txt, fill=secondary, font=font_sub
            )

        return cy1 + cart_h + 40

    @classmethod
    def _draw_floral_venue(
        cls,
        draw: ImageDraw.ImageDraw,
        venue_str: str,
        is_dev: bool,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_body: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        accent: tuple[int, int, int],
        cur_y: int,
    ) -> None:
        v_title = "— स्थळ —" if is_dev else "— CELEBRATION VENUE —"
        b = draw.textbbox((0, 0), v_title, font=font_sub)
        draw.text(((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), v_title, fill=accent, font=font_sub)
        cur_y += 35

        v_lines = wrap_text(venue_str, font_body, cls.WIDTH - 240, draw)
        for vl in v_lines[:3]:
            b = draw.textbbox((0, 0), vl, font=font_body)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), vl, fill=(40, 40, 40), font=font_body
            )
            cur_y += 40

    @classmethod
    def _draw_floral_guest_footer(
        cls,
        draw: ImageDraw.ImageDraw,
        guest_name: str | None,
        guest_diet: str | None,
        is_dev: bool,
        font_guest: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_sub: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        footer_y = cls.HEIGHT - 210
        draw.line([(120, footer_y), (cls.WIDTH - 120, footer_y)], fill=accent, width=1)
        footer_y += 35

        if guest_name:
            g_prefix = "यजमानांतर्फे निमंत्रक: " if is_dev else "Invited with Love: "
            g_txt = f"{g_prefix}{guest_name}"
            g_disp = truncate_with_ellipsis(g_txt, font_guest, cls.WIDTH - 200, draw)
            b = draw.textbbox((0, 0), g_disp, font=font_guest)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, footer_y),
                g_disp,
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
            g_txt = (
                "आपले व आपल्या परिवाराचे सहर्ष स्वागत"
                if is_dev
                else "Blessings and Presence of You & Your Family Requested"
            )
            b = draw.textbbox((0, 0), g_txt, font=font_guest)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, footer_y), g_txt, fill=primary, font=font_guest
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
        _ceremonies: list[str] | None,
        guest_name: str | None,
        guest_diet: str | None,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        bg_color = (255, 250, 240)
        img = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        is_dev = (
            is_devanagari_text(event_name)
            or is_devanagari_text(host_name)
            or is_devanagari_text(wording)
        )

        font_badge = get_font(FONT_BOLD_PATH, 30)
        cls._draw_floral_framing(draw, is_dev, font_badge, primary, secondary, accent)

        font_host = get_font(FONT_REGULAR_PATH, 28)
        font_title = get_font(FONT_BOLD_PATH, 52)
        font_body = get_font(FONT_REGULAR_PATH, 30)
        font_meta = get_font(FONT_BOLD_PATH, 32)
        font_sub = get_font(FONT_REGULAR_PATH, 24)
        font_guest = get_font(FONT_BOLD_PATH, 34)

        cur_y = cls._draw_floral_host(draw, host_name, is_dev, font_host, 170)
        cur_y += 20

        # Title
        title_lines = wrap_text(event_name, font_title, cls.WIDTH - 200, draw)
        for t_line in title_lines:
            b = draw.textbbox((0, 0), t_line, font=font_title)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), t_line, fill=secondary, font=font_title
            )
            cur_y += 65
        cur_y += 30

        # Wording
        w_lines = wrap_text(wording, font_body, cls.WIDTH - 240, draw)
        for wl in w_lines[:4]:
            b = draw.textbbox((0, 0), wl, font=font_body)
            draw.text(
                ((cls.WIDTH - (b[2] - b[0])) // 2, cur_y), wl, fill=(50, 45, 40), font=font_body
            )
            cur_y += 44
        cur_y += 50

        cur_y = cls._draw_floral_cartouche(
            draw, date_str, muhurat, is_dev, font_meta, font_sub, primary, secondary, cur_y
        )
        cls._draw_floral_venue(draw, venue_str, is_dev, font_sub, font_body, accent, cur_y)
        cls._draw_floral_guest_footer(
            draw, guest_name, guest_diet, is_dev, font_guest, font_sub, primary, secondary, accent
        )
        return img
