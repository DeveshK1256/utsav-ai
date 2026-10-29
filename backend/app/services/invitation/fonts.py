import logging
from pathlib import Path

from PIL import ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Path to bundled Noto Sans Devanagari fonts
FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
FONT_REGULAR_PATH = str(FONTS_DIR / "NotoSansDevanagari-Regular.ttf")
FONT_BOLD_PATH = str(FONTS_DIR / "NotoSansDevanagari-Bold.ttf")


def hex_to_rgb(
    hex_str: str | None, default: tuple[int, int, int] = (180, 83, 9)
) -> tuple[int, int, int]:
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


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    except (OSError, RuntimeError) as exc:
        logger.debug("Failed loading primary font %s: %s", path, exc)
    try:
        if Path(FONT_REGULAR_PATH).exists():
            return ImageFont.truetype(FONT_REGULAR_PATH, size)
    except (OSError, RuntimeError) as exc:
        logger.debug("Failed loading bundled regular font: %s", exc)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, RuntimeError) as exc:
        logger.debug("Failed loading system fallback font: %s", exc)
        return ImageFont.load_default()


def is_devanagari_text(text: str | None) -> bool:
    """
    Returns True if text contains characters in the Unicode Devanagari block (U+0900..U+097F).
    """
    if not text:
        return False
    return any(0x0900 <= ord(c) <= 0x097F for c in text)


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
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


def truncate_with_ellipsis(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> str:
    """Truncates text with ellipsis if it exceeds max_width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if (bbox[2] - bbox[0]) <= max_width:
        return text
    ellipsis = "..."
    truncated = text
    while (
        truncated
        and (
            draw.textbbox((0, 0), truncated + ellipsis, font=font)[2]
            - draw.textbbox((0, 0), truncated + ellipsis, font=font)[0]
        )
        > max_width
    ):
        truncated = truncated[:-1]
    return (truncated.strip() + ellipsis) if truncated else ellipsis
