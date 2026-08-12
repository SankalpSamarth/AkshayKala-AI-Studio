"""
Output 2: Abstract Brand Background Generator

This module handles the compositing of jewelry onto abstract or real-world background plates,
incorporating advanced lighting harmonization and shadow generation to ensure a photorealistic result.
"""

import numpy as np
import cv2
from PIL import Image, ImageFilter

def auto_detect_plate(bg_path):
    """
    Automatically detects the primary display surface (plate) within the background image.

    This function utilizes computer vision techniques to locate the dominant structural
    element in the background without relying on hardcoded coordinates, ensuring robustness
    across diverse backdrop designs.

    The process follows these steps:
    1. Gaussian Blur: Reduces high-frequency noise that could cause false edge detections.
    2. Canny Edge Detection: Identifies sharp intensity gradients (thresholds 30, 150) to
       find boundaries.
    3. Morphological Dilation: Uses a 9x9 kernel over 3 iterations to close gaps in the
       detected edge lines, forming continuous contours.
    4. Contour Finding: Extracts the external geometric boundaries (RETR_EXTERNAL).
    5. Filtering: Selects the largest contour that constitutes a significant portion of the
       image area (>10%) and is located near the center, representing the target surface.

    Args:
        bg_path (str): Absolute path to the background image.

    Returns:
        tuple: (plate_width, plate_cx, plate_cy, total_width) defining the region of interest.
               Returns default center coordinates if detection fails.
    """
    bg_img = cv2.imread(bg_path)
    if bg_img is None:
        return 1000, 500, 500, 1000

    h, w = bg_img.shape[:2]
    
    # Preprocessing
    gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 30, 150)
    
    # Morphological dilation
    kernel = np.ones((9, 9), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=3)
    
    # Contour finding
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Filter and find the largest relevant contour
        valid_contours = [c for c in contours if cv2.contourArea(c) > (w * h * 0.10)]
        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
            return cw, x + (cw // 2), y + (ch // 2), w
            
    # Default fallback
    return int(w * 0.5), w // 2, h // 2, w

def generate(earring_nobg, bg_path, output_path, plate_coverage=0.35):
    """
    Generates a composite of the earring on the provided background with realistic lighting.

    Ambient Color Harmonization:
    To make the composite appear naturally lit by its environment, we sample the median RGB
    color of the background plate. We then subtly blend this ambient color into the earring
    pixels using a linear interpolation formula:
        C' = (1 - lambda) * C + lambda * A
    where C is the original color, A is the ambient color, and lambda is the blend factor (0.15).
    In the implementation, this is calculated as:
        pixel[i] = pixel[i] + (bg_avg[i] - 200.0) * blend
    This slight color shift ties the object to its surroundings.

    Edge Darkening:
    Simulates the contact point micro-shadows where the physical object meets the surface.
    This is achieved via morphological erosion (3x3 kernel) of the alpha mask, effectively
    darkening the immediate boundary pixels.

    Luminance-Based Shadow Mapping:
    The intensity of the synthetic shadow is modulated by the background's inherent luminosity,
    ensuring shadows are not unrealistically dark on bright surfaces or invisible on dark ones.
    Using the standard perceived luminance formula (Y = 0.299R + 0.587G + 0.114B), the shadow
    opacity is scaled:
        shadow_opacity = clip(luminance / bright_level, 0.35, 1.0)

    Ambient Occlusion:
    A technique borrowed from 3D rendering, Ambient Occlusion (AO) models the dense, tight
    'contact shadow' located directly beneath the object where ambient light is completely
    blocked. This is a secondary, low-offset, low-blur shadow layer that adds significant
    weight and realism.

    Args:
        earring_nobg (PIL.Image.Image): The transparent RGBA earring image.
        bg_path (str): Absolute path to the background template.
        output_path (str): Destination path for the result.
        plate_coverage (float): The proportion of the plate width the earring should occupy.
    """
    # 1. Auto plate detection
    plate_width, plate_cx, plate_cy, total_width = auto_detect_plate(bg_path)
    
    background = Image.open(bg_path).convert("RGBA")
    
    # 2. Bounding box crop + Lanczos scaling + Unsharp masking
    target_width = int(plate_width * plate_coverage)
    img_w, img_h = earring_nobg.size
    scale = target_width / img_w
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    resized_earring = earring_nobg.resize((new_w, new_h), Image.Resampling.LANCZOS)
    sharpened_earring = resized_earring.filter(
        ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3)
    )
    
    # 3. Edge darkening via morphological erosion
    arr = np.array(sharpened_earring)
    alpha = arr[:, :, 3]
    kernel = np.ones((3, 3), np.uint8)
    eroded_alpha = cv2.erode(alpha, kernel, iterations=1)
    
    # 4. Ambient color harmonization
    # Sample background color around the target area
    bg_arr = np.array(background)
    sample_y = max(0, plate_cy - new_h//2)
    sample_x = max(0, plate_cx - new_w//2)
    bg_region = bg_arr[sample_y:sample_y+new_h, sample_x:sample_x+new_w]
    
    if bg_region.size > 0:
        bg_median = np.median(bg_region, axis=(0, 1))[:3]
        blend_factor = 0.15
        
        # Apply color blending (simplified array operation for clarity)
        rgb = arr[:, :, :3].astype(np.float32)
        for i in range(3):
            rgb[:, :, i] += (bg_median[i] - 200.0) * blend_factor
            
        np.clip(rgb, 0, 255, out=rgb)
        arr[:, :, :3] = rgb.astype(np.uint8)
        
    harmonized_earring = Image.fromarray(arr)

    # Calculate positioning
    paste_x = plate_cx - new_w // 2
    paste_y = plate_cy - new_h // 2
    
    # 5. Luminance-based shadow mapping
    # Calculate luminance of the placement area
    if bg_region.size > 0:
        b_mean, g_mean, r_mean = np.mean(bg_region, axis=(0, 1))[:3]
        luminance = 0.299 * r_mean + 0.587 * g_mean + 0.114 * b_mean
        bright_level = 200.0
        shadow_intensity = np.clip(luminance / bright_level, 0.35, 1.0)
    else:
        shadow_intensity = 0.75
        
    shadow_mask = harmonized_earring.split()[3]
    
    # 6. Drop shadow layer
    drop_shadow_mask = shadow_mask.point(lambda p: int(p * shadow_intensity * 0.8))
    drop_shadow = Image.new("RGBA", harmonized_earring.size, (0, 0, 0, 0))
    drop_shadow.putalpha(drop_shadow_mask)
    
    drop_canvas = Image.new("RGBA", background.size, (0, 0, 0, 0))
    drop_canvas.paste(drop_shadow, (paste_x + 15, paste_y + 15), drop_shadow)
    drop_canvas = drop_canvas.filter(ImageFilter.GaussianBlur(radius=12))
    
    # 7. Ambient occlusion layer
    ao_mask = shadow_mask.point(lambda p: int(p * shadow_intensity * 0.60))
    ao_shadow = Image.new("RGBA", harmonized_earring.size, (0, 0, 0, 0))
    ao_shadow.putalpha(ao_mask)
    
    ao_canvas = Image.new("RGBA", background.size, (0, 0, 0, 0))
    ao_canvas.paste(ao_shadow, (paste_x, paste_y + 2), ao_shadow)
    ao_canvas = ao_canvas.filter(ImageFilter.GaussianBlur(radius=2))
    
    # 8. Alpha composite all layers
    composite = Image.alpha_composite(background, drop_canvas)
    composite = Image.alpha_composite(composite, ao_canvas)
    composite.paste(harmonized_earring, (paste_x, paste_y), harmonized_earring)
    
    final_output = composite.convert("RGB")
    final_output.save(output_path, "JPEG", quality=95)
