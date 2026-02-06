#!/usr/bin/env python3
"""
Stitch together the 6 images (3 originals + 3 transitions) into one seamless rim_wall texture.

The order is:
1. rim_wall1
2. transition_1_to_2 (cropped to remove overlapping edges)
3. rim_wall2
4. transition_2_to_3 (cropped to remove overlapping edges)
5. rim_wall3
6. transition_3_to_1 (cropped to remove overlapping edges)

This creates a circular seamless pattern.
"""

from pathlib import Path
from PIL import Image

# Configuration
TEXTURES_DIR = Path(__file__).parent.parent / "textures"
INPAINT_DIR = TEXTURES_DIR / "inpaint_work"
OUTPUT_PATH = TEXTURES_DIR / "rim_wall_seamless.png"

# Transition images have 100px overlap on each side (400px total)
# We need to crop to just the center 200px (the inpainted region)
EDGE_WIDTH = 100  # pixels to crop from each side of transitions

# Images to stitch in order
IMAGES_TO_STITCH = [
    (TEXTURES_DIR / "rim_wall1.png", False),  # (path, is_transition)
    (INPAINT_DIR / "transition_1_to_2_inpainted.png", True),
    (TEXTURES_DIR / "rim_wall2.png", False),
    (INPAINT_DIR / "transition_2_to_3_inpainted.png", True),
    (TEXTURES_DIR / "rim_wall3.png", False),
    (INPAINT_DIR / "transition_3_to_1_inpainted.png", True),
]


def main():
    """Stitch all images together horizontally."""
    print("Loading images...")
    images = []
    total_width = 0
    max_height = 0
    
    for img_path, is_transition in IMAGES_TO_STITCH:
        print(f"  Loading {img_path.name}...")
        img = Image.open(img_path).convert("RGB")
        
        # Crop transitions to remove overlapping edges
        if is_transition:
            original_width = img.width
            # Crop: remove 100px from left and 100px from right
            # Keep only the center 200px (the inpainted region)
            img = img.crop((EDGE_WIDTH, 0, img.width - EDGE_WIDTH, img.height))
            print(f"    Cropped from {original_width}px to {img.width}px (removed {EDGE_WIDTH}px from each side)")
        
        images.append(img)
        total_width += img.width
        max_height = max(max_height, img.height)
        print(f"    Final size: {img.size}")
    
    print(f"\nCreating stitched image: {total_width}x{max_height} pixels")
    
    # Create the final stitched image
    stitched = Image.new("RGB", (total_width, max_height))
    
    # Paste each image
    x_offset = 0
    for i, (img_path, _) in enumerate(IMAGES_TO_STITCH):
        print(f"  Pasting {img_path.name} at x={x_offset}")
        stitched.paste(images[i], (x_offset, 0))
        x_offset += images[i].width
    
    # Save the result
    print(f"\nSaving stitched image to: {OUTPUT_PATH}")
    stitched.save(OUTPUT_PATH)
    print(f"Done! Created seamless rim_wall texture: {total_width}x{max_height} pixels")
    
    # Also create a preview with all images side by side vertically for inspection
    preview_path = INPAINT_DIR / "stitching_preview.png"
    print(f"\nCreating preview: {preview_path}")
    
    preview_height = sum(img.height for img in images) + (len(images) - 1) * 10  # 10px spacing
    preview = Image.new("RGB", (max(img.width for img in images), preview_height), (50, 50, 50))
    
    y_offset = 0
    for img in images:
        preview.paste(img, (0, y_offset))
        y_offset += img.height + 10
    
    preview.save(preview_path)
    print(f"Preview saved: {preview_path}")


if __name__ == "__main__":
    main()
