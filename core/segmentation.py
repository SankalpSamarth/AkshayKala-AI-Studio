"""
Shared Computer Vision Foundation: Segmentation and Matting

This module provides the shared first stage for all three output generators.
It handles the extraction of the earring from its original background using
a combination of deep learning-based salient object detection and alpha matting.
"""

import os
import numpy as np
import cv2
from PIL import Image
from rembg import remove, new_session

def extract_earring(image_path, session=None):
    """
    Extracts the earring from the background using ISNet and alpha matting.

    This function utilizes the ISNet (Image Segmentation Network) architecture
    rather than the standard U-2-Net. ISNet is chosen specifically for its
    superior edge preservation capabilities on highly intricate, fine-grained
    structures such as delicate metal chains and thin wire hooks commonly found
    in jewelry.

    The extraction process relies on Alpha Matting. Instead of generating a hard
    binary cutout (where a pixel is strictly either foreground or background),
    alpha matting computes a soft transparency mask. It models each pixel as a
    linear combination of foreground (F) and background (B):
        C = alpha * F + (1 - alpha) * B
    where C is the observed color and alpha (alpha channel) represents the opacity,
    ranging from 0.0 (fully transparent) to 1.0 (fully opaque). This allows for
    smooth transitions and semi-transparent regions.

    Parameters used for alpha matting:
        - alpha_matting_foreground_threshold=200: A high threshold ensures that only
          pixels with very high confidence of being part of the earring remain fully solid.
        - alpha_matting_background_threshold=10: An aggressive low threshold effectively
          removes background noise and shadows.
        - alpha_matting_erode_size=0: Erosion is disabled to prevent the algorithm from
          eating into the delicate structural edges of the jewelry.

    After background removal, a bounding box crop is performed. This operation locates
    the minimum bounding rectangle encompassing all non-transparent pixels, effectively
    discarding unnecessary transparent margins and centering the object of interest.

    Args:
        image_path (str): The absolute path to the source image.
        session (rembg.Session, optional): An existing ISNet session for reuse.

    Returns:
        PIL.Image.Image: The cropped, transparent RGBA image of the earring.
    """
    if session is None:
        session = new_session('isnet-general-use')

    # Open image and convert to RGBA
    img = Image.open(image_path).convert("RGBA")

    # Apply background removal with alpha matting parameters
    extracted_img = remove(
        img,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=200,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=0
    )

    # Convert to numpy array for OpenCV processing
    arr = np.array(extracted_img)
    
    # Extract the alpha channel
    alpha_channel = arr[:, :, 3]
    
    # Locate all non-fully-transparent pixels
    coords = cv2.findNonZero(alpha_channel)
    
    if coords is not None:
        # Calculate the bounding box for the visible object
        x, y, w, h = cv2.boundingRect(coords)
        
        # Crop the image to the bounding box
        cropped_img = extracted_img.crop((x, y, x + w, y + h))
        return cropped_img
    
    # Fallback to the original extracted image if no bounding box can be determined
    return extracted_img
