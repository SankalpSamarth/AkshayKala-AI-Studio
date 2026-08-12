"""
Output 1: White Studio Background Generator

This module handles the generation of standard e-commerce white background
product imagery, complete with simulated studio lighting and drop shadows.
"""

import numpy as np
import cv2
from PIL import Image, ImageFilter

def generate(earring_nobg, output_path, canvas_size=4096, padding=0.28):
    """
    Generates a high-resolution white studio background composite.

    This function processes the transparent foreground object to fit optimally
    within a standardized canvas suitable for e-commerce cataloging.

    Image Resampling:
    Scaling operations utilize Lanczos resampling. The Lanczos filter is a windowed
    sinc filter that theoretically provides the optimal reconstruction of the continuous
    signal from its discrete samples. In practice, it significantly preserves edge
    sharpness during resizing compared to simpler methods like nearest-neighbor or
    bilinear interpolation.

    Image Enhancement:
    Following the downscaling process, Unsharp Masking is applied. This technique
    recovers micro-details and edge contrast inherently softened during resampling.
    A slightly blurred version of the image is subtracted from the original to create
    a 'mask' that highlights edges. This mask is then added back, resulting in a sharper
    appearance. (radius=1.2 controls the blur size, percent=100 controls the intensity,
    threshold=3 prevents noise amplification in flat regions).

    Canvas Compositing:
    The background canvas is filled with RGB(252, 252, 252) rather than pure white
    (255, 255, 255). Pure white can induce harsh, unnatural contrast and can cause
    visual bleeding on some displays. The slight off-white tone provides a more
    natural, softer backdrop that accurately simulates a physical white sweep.

    Drop Shadow Simulation:
    The generation of a synthetic drop shadow models physical lighting behavior:
    1. The object's alpha channel is extracted and multiplied by a darkness factor (0.75)
       to simulate the occlusion of light.
    2. A directional offset (dx=45, dy=45) is applied, simulating a primary light source
       positioned to the top-left of the scene.
    3. A Gaussian blur (radius=40) softens the shadow, modeling the diffusion of light
       over distance and the size of the simulated light source.
    4. This shadow layer is composited beneath the sharp object layer.

    Args:
        earring_nobg (PIL.Image.Image): The transparent RGBA earring image.
        output_path (str): The destination path for the generated JPEG.
        canvas_size (int): The width and height of the square output canvas.
        padding (float): The percentage of the canvas to reserve as padding.
    """
    # 1. Bounding box cropping is assumed to be handled upstream or via the passed image
    
    # 2. Aspect-ratio-preserving scaling using Lanczos resampling
    target_width = int(canvas_size * (1 - padding))
    target_height = int(canvas_size * (1 - padding))
    
    img_w, img_h = earring_nobg.size
    scale = min(target_width / img_w, target_height / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    resized_earring = earring_nobg.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # 3. Unsharp masking
    sharpened_earring = resized_earring.filter(
        ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3)
    )
    
    # 4. Canvas compositing on RGB(252,252,252)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (252, 252, 252, 255))
    
    # Calculate centering coordinates
    paste_x = (canvas_size - new_w) // 2
    paste_y = (canvas_size - new_h) // 2
    
    # 5. Drop shadow simulation
    # Extract alpha channel to create a shadow mask
    shadow_mask = sharpened_earring.split()[3]
    
    # Apply darkness factor
    shadow_mask = shadow_mask.point(lambda p: int(p * 0.75))
    
    # Create black image with the shadow mask as alpha
    shadow_layer = Image.new("RGBA", sharpened_earring.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_mask)
    
    # Create a full-canvas shadow layer to allow blurring outside object bounds
    full_shadow_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    
    # Apply directional offset (dx=45, dy=45)
    shadow_x = paste_x + 45
    shadow_y = paste_y + 45
    full_shadow_canvas.paste(shadow_layer, (shadow_x, shadow_y), shadow_layer)
    
    # Apply Gaussian blur for soft shadow effect
    blurred_shadow = full_shadow_canvas.filter(ImageFilter.GaussianBlur(radius=40))
    
    # Composite shadow beneath the object
    canvas = Image.alpha_composite(canvas, blurred_shadow)
    
    # Composite the object on top
    canvas.paste(sharpened_earring, (paste_x, paste_y), sharpened_earring)
    
    # 6. Save as JPEG quality=95
    final_output = canvas.convert("RGB")
    final_output.save(output_path, "JPEG", quality=95)
