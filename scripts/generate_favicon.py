import os
from PIL import Image, ImageDraw

def generate_icons():
    output_dir = "frontend/public"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate high-res 512x512 master image
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Coordinates in 512x512 space
    # Golden glow / halo
    for r in range(220, 160, -8):
        alpha = int(25 * (1 - (r - 160) / 60))
        draw.ellipse(
            [256 - r, 240 - r, 256 + r, 240 + r],
            fill=(244, 180, 26, alpha)
        )
        
    # Diya bowl (Kumkum crimson #8B1E28 with golden rim)
    # Bowl shape: smooth crescent at the bottom
    # Bottom arc
    bowl_bbox = [100, 270, 412, 440]
    draw.pieslice(bowl_bbox, start=0, end=180, fill=(139, 30, 40, 255))
    
    # Diya Rim / Lip (Marigold gold #F4B41A)
    draw.ellipse([92, 260, 420, 296], fill=(244, 180, 26, 255), outline=(180, 120, 10, 255), width=4)
    # Inner bowl shadow
    draw.ellipse([110, 266, 402, 290], fill=(100, 20, 28, 255))

    # Diya spout / tip
    spout = [(256, 250), (220, 280), (292, 280)]
    draw.polygon(spout, fill=(244, 180, 26, 255))

    # Flame outer (Radiant Gold #FFD54F)
    # Teardrop flame: bezier-like polygon
    flame_outer = [
        (256, 70),   # Flame tip
        (295, 130),  # Right upper swell
        (325, 200),  # Right belly
        (300, 260),  # Right base
        (256, 272),  # Bottom center at wick
        (212, 260),  # Left base
        (187, 200),  # Left belly
        (217, 130),  # Left upper swell
    ]
    draw.polygon(flame_outer, fill=(255, 193, 7, 255))
    
    # Flame inner core (Brilliant white-gold glow #FFF9C4)
    flame_inner = [
        (256, 120),
        (280, 170),
        (292, 215),
        (275, 255),
        (256, 262),
        (237, 255),
        (220, 215),
        (232, 170),
    ]
    draw.polygon(flame_inner, fill=(255, 250, 210, 255))

    # Flame pure white wick highlight
    draw.ellipse([246, 220, 266, 255], fill=(255, 255, 255, 240))

    # Save 512x512 icon
    master_png_path = os.path.join(output_dir, "icon-512.png")
    apple_icon_path = os.path.join(output_dir, "apple-touch-icon.png")
    img.save(master_png_path, "PNG")
    
    # For apple-touch-icon, render on a rich dark-gold rounded background
    apple_img = Image.new("RGBA", (180, 180), (26, 15, 10, 255))
    apple_diya = img.resize((150, 150), Image.Resampling.LANCZOS)
    apple_img.paste(apple_diya, (15, 15), apple_diya)
    apple_img.save(apple_icon_path, "PNG")
    
    # Generate multi-res favicon.ico (16x16, 32x32, 48x48)
    sizes = [(16, 16), (32, 32), (48, 48)]
    resized_imgs = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    
    ico_path = os.path.join(output_dir, "favicon.ico")
    resized_imgs[0].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        append_images=resized_imgs[1:]
    )

    # Also save 32x32 and 16x16 standalone png
    resized_imgs[0].save(os.path.join(output_dir, "favicon-16x16.png"), "PNG")
    resized_imgs[1].save(os.path.join(output_dir, "favicon-32x32.png"), "PNG")

    # Generate clean SVG favicon
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <!-- Diya Glow -->
  <circle cx="16" cy="14" r="11" fill="#F4B41A" fill-opacity="0.18"/>
  <!-- Diya Bowl -->
  <path d="M6 18 C6 27, 26 27, 26 18 Z" fill="#8B1E28"/>
  <ellipse cx="16" cy="18" rx="10" ry="2.2" fill="#F4B41A" stroke="#C69214" stroke-width="0.75"/>
  <ellipse cx="16" cy="18" rx="8" ry="1.2" fill="#6B121A"/>
  <!-- Outer Flame -->
  <path d="M16 4 C18.5 8, 20.5 12, 20 15 C19.5 17.5, 18 18.5, 16 18.5 C14 18.5, 12.5 17.5, 12 15 C11.5 12, 13.5 8, 16 4 Z" fill="#F4B41A"/>
  <!-- Inner Flame -->
  <path d="M16 8 C17.2 11, 18.5 13.5, 18 15.5 C17.6 17, 16.8 17.5, 16 17.5 C15.2 17.5, 14.4 17, 14 15.5 C13.5 13.5, 14.8 11, 16 8 Z" fill="#FFF8E1"/>
</svg>"""
    with open(os.path.join(output_dir, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(svg_content)

    print("Generated favicon.ico, icon.svg, apple-touch-icon.png, and icon-512.png successfully!")

if __name__ == "__main__":
    generate_icons()
