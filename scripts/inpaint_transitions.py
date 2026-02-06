#!/usr/bin/env python3
"""
Script to create seamless transitions between rim_wall textures using inpainting.

Creates composite images with:
- 100 pixels from the right of image A (left side of composite)
- 200 blank pixels in the middle (to be inpainted)
- 100 pixels from the left of image B (right side of composite)

Uses HuggingFace Diffusers with Stable Diffusion Inpainting for the transition zone.
"""

import os
import torch
from pathlib import Path
from PIL import Image

# Diffusers for inpainting
from diffusers import AutoPipelineForInpainting

# Configuration
TEXTURES_DIR = Path(__file__).parent.parent / "textures"
OUTPUT_DIR = TEXTURES_DIR / "inpaint_work"

EDGE_WIDTH = 100  # pixels to take from each edge
GAP_WIDTH = 200   # pixels to inpaint in the middle

# Pairs to process: (source_right, source_left, output_name)
PAIRS = [
    ("rim_wall1.png", "rim_wall2.png", "transition_1_to_2"),
    ("rim_wall2.png", "rim_wall3.png", "transition_2_to_3"),
    ("rim_wall3.png", "rim_wall1.png", "transition_3_to_1"),
]


def load_image(path: Path) -> Image.Image:
    """Load an image from disk."""
    return Image.open(path).convert("RGB")


def create_composite_and_mask(
    img_left: Image.Image, 
    img_right: Image.Image
) -> tuple[Image.Image, Image.Image]:
    """
    Create a composite image and mask for inpainting.
    
    Args:
        img_left: Image to take right edge from (goes on left of composite)
        img_right: Image to take left edge from (goes on right of composite)
    
    Returns:
        Tuple of (composite_image, mask_image)
        - Composite: RGB image with edges and gradient fill in middle
        - Mask: L-mode image where WHITE (255) = inpaint, BLACK (0) = keep
    """
    # Get dimensions
    height = img_left.height
    composite_width = EDGE_WIDTH + GAP_WIDTH + EDGE_WIDTH  # 400 total
    
    # Create composite image (RGB)
    composite = Image.new("RGB", (composite_width, height), (128, 128, 128))
    
    # Extract right edge of left image (rightmost 100 pixels)
    left_edge = img_left.crop((
        img_left.width - EDGE_WIDTH,  # left
        0,                             # top
        img_left.width,                # right
        height                         # bottom
    ))
    
    # Extract left edge of right image (leftmost 100 pixels)
    right_edge = img_right.crop((
        0,          # left
        0,          # top
        EDGE_WIDTH, # right
        height      # bottom
    ))
    
    # Paste edges onto composite
    composite.paste(left_edge, (0, 0))
    composite.paste(right_edge, (EDGE_WIDTH + GAP_WIDTH, 0))
    
    # Fill the middle gap with a gradient blend for better inpainting context
    for x in range(GAP_WIDTH):
        alpha = x / GAP_WIDTH  # 0 at left edge, 1 at right edge
        for y in range(height):
            left_pixel = left_edge.getpixel((EDGE_WIDTH - 1, y))
            right_pixel = right_edge.getpixel((0, y))
            # Blend pixels (RGB only, 3 channels)
            blended = tuple(int(left_pixel[i] * (1 - alpha) + right_pixel[i] * alpha) for i in range(3))
            composite.putpixel((EDGE_WIDTH + x, y), blended)
    
    # Create mask - Diffusers convention: WHITE (255) = inpaint, BLACK (0) = keep
    mask = Image.new("L", (composite_width, height), 0)  # Start with all black (keep)
    
    # Make the middle section white (to be inpainted)
    # Add a small buffer overlap for smoother blending
    buffer = 10
    for x in range(GAP_WIDTH + buffer * 2):
        for y in range(height):
            x_pos = EDGE_WIDTH - buffer + x
            if 0 <= x_pos < composite_width:
                mask.putpixel((x_pos, y), 255)  # White = inpaint
    
    return composite, mask


def create_inpaint_pipeline():
    """
    Create and return the inpainting pipeline.
    Uses Stable Diffusion Inpainting model.
    """
    # Use Stable Diffusion Inpainting - specifically trained for this task
    # Options: 
    #   - "stable-diffusion-v1-5/stable-diffusion-inpainting" (512x512, faster)
    #   - "diffusers/stable-diffusion-xl-1.0-inpainting-0.1" (1024x1024, higher quality)
    
    pipeline = AutoPipelineForInpainting.from_pretrained(
        "stable-diffusion-v1-5/stable-diffusion-inpainting",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        variant="fp16" if torch.cuda.is_available() else None,
    )
    
    # Use MPS (Apple Silicon) if available, otherwise CUDA or CPU
    if torch.backends.mps.is_available():
        pipeline = pipeline.to("mps")
        print("  Using Apple Silicon MPS acceleration")
    elif torch.cuda.is_available():
        pipeline.enable_model_cpu_offload()
        print("  Using CUDA with CPU offload")
    else:
        print("  Using CPU (this will be slow)")
    
    return pipeline


def inpaint_with_diffusers(
    pipeline,
    composite: Image.Image, 
    mask: Image.Image,
    prompt: str,
) -> Image.Image:
    """
    Use Stable Diffusion Inpainting to fill the masked region.
    
    Args:
        pipeline: The inpainting pipeline
        composite: The composite image with edges
        mask: The mask (white = inpaint, black = keep)
        prompt: Description for the inpainting
    
    Returns:
        The inpainted image
    """
    # Generate with low strength to preserve as much as possible
    # and blend naturally with the existing content
    result = pipeline(
        prompt=prompt,
        image=composite,
        mask_image=mask,
        strength=0.99,  # High strength since we want to generate the middle
        guidance_scale=7.5,
        num_inference_steps=50,
    ).images[0]
    
    return result


def main():
    """Main processing function."""
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading source images...")
    
    # Load all source images
    images = {}
    for pair in PAIRS:
        for img_name in pair[:2]:
            if img_name not in images:
                img_path = TEXTURES_DIR / img_name
                print(f"  Loading {img_name}...")
                images[img_name] = load_image(img_path)
                print(f"    Size: {images[img_name].size}")
    
    print("\nLoading inpainting model...")
    pipeline = create_inpaint_pipeline()
    
    print(f"\nProcessing {len(PAIRS)} transition pairs...")
    
    for img_left_name, img_right_name, output_name in PAIRS:
        print(f"\n{'='*60}")
        print(f"Processing: {img_left_name} -> {img_right_name}")
        print(f"{'='*60}")
        
        img_left = images[img_left_name]
        img_right = images[img_right_name]
        
        # Create composite and mask
        print("Creating composite and mask...")
        composite, mask = create_composite_and_mask(img_left, img_right)
        
        # Save intermediate files for inspection
        composite_path = OUTPUT_DIR / f"{output_name}_composite.png"
        mask_path = OUTPUT_DIR / f"{output_name}_mask.png"
        
        composite.save(composite_path)
        mask.save(mask_path)
        print(f"  Saved composite: {composite_path}")
        print(f"  Saved mask: {mask_path}")
        
        # Inpaint using Stable Diffusion
        print("Running Stable Diffusion inpainting...")
        prompt = (
            "seamless photorealistic mining site, open pit mine, "
            "industrial mining equipment, excavators, dump trucks, "
            "rocky terrain, blue sky with clouds, natural lighting, "
            "continuous landscape, high quality photograph"
        )
        
        try:
            inpainted = inpaint_with_diffusers(pipeline, composite, mask, prompt)
            
            # Save result
            result_path = OUTPUT_DIR / f"{output_name}_inpainted.png"
            inpainted.save(result_path)
            print(f"  SUCCESS! Saved inpainted result: {result_path}")
            
        except Exception as e:
            print(f"  ERROR during inpainting: {e}")
            import traceback
            traceback.print_exc()
            print("  Saving composite without inpainting for manual processing...")
    
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"Output files are in: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
