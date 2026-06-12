import os
from PIL import Image, ImageDraw, ImageFilter
import random
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_path = os.path.join(BASE_DIR, "assets", "backgrounds", "old_paper_texture.jpg")

def generate_ledger_paper(width=2000, height=3000):
    # Base cream/yellow vintage color
    img = Image.new('RGB', (width, height), color=(245, 235, 210))
    draw = ImageDraw.Draw(img)
    
    # 1. Add subtle paper noise/texture
    print("Adding texture noise...")
    for _ in range(50000):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        # Random darker spots for aging
        if random.random() > 0.9:
            color = (random.randint(180, 220), random.randint(170, 210), random.randint(140, 180))
            draw.point((x, y), fill=color)
            
    # Apply slight blur to soften noise
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    draw = ImageDraw.Draw(img)
    
    # 2. Add ruled horizontal lines (faded blue/grey)
    print("Drawing ruled lines...")
    line_spacing = 80
    start_y = 300
    line_color = (160, 180, 200) # Faded blue
    for y in range(start_y, height, line_spacing):
        # Draw line with slight variations in opacity
        draw.line([(0, y), (width, y)], fill=line_color, width=2)
        
    # 3. Add vertical margin line (faded red)
    print("Drawing margin lines...")
    margin_x1 = 250
    margin_x2 = 260
    margin_color = (200, 120, 120) # Faded red
    draw.line([(margin_x1, 0), (margin_x1, height)], fill=margin_color, width=3)
    draw.line([(margin_x2, 0), (margin_x2, height)], fill=margin_color, width=3)
    
    # 4. Add vignette (darker aged edges)
    print("Applying vignette...")
    pixels = img.load()
    center_x = width / 2
    center_y = height / 2
    max_dist = math.sqrt(center_x**2 + center_y**2)
    
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
            # Edge darkening factor
            factor = 1.0 - 0.4 * (dist / max_dist)**2
            
            # Additional darkening at the corners
            if dist > max_dist * 0.7:
                factor -= 0.2 * ((dist - max_dist * 0.7) / (max_dist * 0.3))
                
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                max(0, int(r * factor)),
                max(0, int(g * factor)),
                max(0, int(b * factor))
            )
            
    # 5. Add a few stains
    print("Adding stains...")
    for _ in range(8):
        stain_x = random.randint(100, width - 100)
        stain_y = random.randint(100, height - 100)
        stain_r = random.randint(40, 120)
        stain_color = (190, 170, 130) # Brownish stain
        draw.ellipse([stain_x - stain_r, stain_y - stain_r, stain_x + stain_r, stain_y + stain_r], fill=stain_color)
    
    # Blur again to blend stains and vignette
    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, quality=90)
    print(f"✅ Generated authentic ledger paper at {output_path}")

if __name__ == "__main__":
    generate_ledger_paper()
