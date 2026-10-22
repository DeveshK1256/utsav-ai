import io
import math
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont


def hex_to_rgb(hex_str: str) -> tuple:
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) == 6:
        return tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    return (226, 114, 91)  # terracotta default


class MoodboardCollageGenerator:
    """
    Code-side mood board collage generator using Pillow (DEC-022).
    Composites uploaded inspiration images with the extracted color palette
    and theme typography without calling external image generation APIs.
    """

    @classmethod
    def generate_collage(
        cls,
        image_bytes_list: List[bytes],
        palette: List[str],
        theme_name: str = "Cultural Celebration Theme",
        style_tags: Optional[List[str]] = None
    ) -> bytes:
        canvas_width = 1200
        canvas_height = 800
        bg_color = (250, 248, 245)  # Warm ivory

        collage = Image.new("RGB", (canvas_width, canvas_height), bg_color)
        draw = ImageDraw.Draw(collage)

        # 1. Header Banner
        header_height = 90
        header_color = (45, 30, 20)  # Dark bronze
        draw.rectangle([(0, 0), (canvas_width, header_height)], fill=header_color)

        # Draw Title
        title_text = f"UTSAV VIBE-TO-PLAN: {theme_name.upper()}"
        draw.text((30, 20), title_text, fill=(255, 215, 0))  # Gold

        tags_str = " • ".join((style_tags or ["Traditional", "Vibrant", "Celebration"])[:5])
        draw.text((30, 52), f"Aesthetic Tags: {tags_str}", fill=(230, 230, 230))

        # 2. Right Palette Sidebar
        sidebar_width = 220
        sidebar_x = canvas_width - sidebar_width
        sidebar_top = header_height
        draw.rectangle([(sidebar_x, sidebar_top), (canvas_width, canvas_height)], fill=(240, 236, 230))

        draw.text((sidebar_x + 20, sidebar_top + 20), "COLOR PALETTE", fill=(70, 50, 35))

        swatch_top = sidebar_top + 55
        swatch_height = 90
        swatch_spacing = 15
        for idx, hex_code in enumerate((palette or ["#E2725B", "#FFD700", "#FFF8DC", "#2E8B57", "#800020"])[:5]):
            y1 = swatch_top + idx * (swatch_height + swatch_spacing)
            y2 = y1 + swatch_height
            color_rgb = hex_to_rgb(hex_code)

            # Draw swatch rectangle
            draw.rectangle([(sidebar_x + 20, y1), (canvas_width - 20, y2)], fill=color_rgb, outline=(200, 195, 185), width=2)
            # Label hex
            draw.rectangle([(sidebar_x + 20, y2 - 24), (sidebar_x + 105, y2)], fill=(255, 255, 255, 200))
            draw.text((sidebar_x + 26, y2 - 20), hex_code.upper(), fill=(20, 20, 20))

        # 3. Main Image Grid (Left Area)
        grid_width = sidebar_x - 30
        grid_height = canvas_height - header_height - 30
        grid_x_start = 20
        grid_y_start = header_height + 15

        num_images = len(image_bytes_list)
        if num_images == 0:
            # Draw empty aesthetic placeholder
            draw.rectangle([(grid_x_start, grid_y_start), (grid_x_start + grid_width, grid_y_start + grid_height)], fill=(245, 240, 235), outline=(220, 215, 205), width=2)
            draw.text((grid_x_start + 150, grid_y_start + grid_height // 2), "Inspiration Moodboard generated from text vibe description", fill=(120, 110, 100))
        else:
            # Determine grid cols and rows (max 6 images displayed cleanly)
            max_tiles = min(num_images, 6)
            cols = 3 if max_tiles > 2 else max_tiles
            rows = math.ceil(max_tiles / cols)

            tile_w = (grid_width - (cols - 1) * 15) // cols
            tile_h = (grid_height - (rows - 1) * 15) // rows

            for i in range(max_tiles):
                c = i % cols
                r = i // cols
                tx = grid_x_start + c * (tile_w + 15)
                ty = grid_y_start + r * (tile_h + 15)

                try:
                    img = Image.open(io.BytesIO(image_bytes_list[i])).convert("RGB")
                    # Center crop and resize to tile_w, tile_h
                    img_ratio = img.width / img.height
                    target_ratio = tile_w / tile_h

                    if img_ratio > target_ratio:
                        new_width = int(img.height * target_ratio)
                        offset = (img.width - new_width) // 2
                        img_cropped = img.crop((offset, 0, offset + new_width, img.height))
                    else:
                        new_height = int(img.width / target_ratio)
                        offset = (img.height - new_height) // 2
                        img_cropped = img.crop((0, offset, img.width, offset + new_height))

                    img_resized = img_cropped.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
                    collage.paste(img_resized, (tx, ty))
                    draw.rectangle([(tx, ty), (tx + tile_w, ty + tile_h)], outline=(220, 215, 205), width=2)
                except Exception:
                    # In case of decode error, draw neutral swatch
                    draw.rectangle([(tx, ty), (tx + tile_w, ty + tile_h)], fill=(230, 225, 215), outline=(200, 195, 185))

        out_io = io.BytesIO()
        collage.save(out_io, format="JPEG", quality=92)
        return out_io.getvalue()
