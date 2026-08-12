#!/usr/bin/env python3
"""
Legacy CLI Batch Processor for AkshayKala AI Studio.

Note: This is the original command-line interface version of the pipeline.
The production application uses app.py (Gradio web interface) instead.
This file is retained as a reference for the CLI-based workflow.

Key difference from app.py: This version runs ISNet extraction separately
for each output type, whereas app.py uses an optimized single-pass approach.

Usage:
    python generate_all_mockups.py <input_zip> [abstract_bg_img]
"""
import os
import sys
import time
import zipfile
import shutil
import requests
from PIL import Image, ImageFilter
import numpy as np
import cv2
import gc
from rembg import remove, new_session
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
CLAID_API_KEY  = os.environ.get("CLAID_API_KEY", "")
CLAID_ENDPOINT = "https://api.claid.ai/v1/image/ai-fashion-models"
BACKGROUND     = "soft neutral studio background, professional jewelry photography, ultra high quality output. Make the fashion model wear the provided earring on only ONE ear (the ear that is most clearly visible). Keep the other ear bare or out of focus. High-end editorial style. The characteristics of the hook and earring must not alter at all; preserve exact shape, texture, and color. Ensure the jewelry is scaled to a realistic, delicate size relative to the human earlobe. Do not oversize or magnify the earring. Maintain natural physical proportions between the jewelry and human anatomy."
POSE           = "portrait, close-up, angled slightly so only one ear is prominently visible, wearing an earring on the fully visible ear. Produce high quality output and ensure the earring and hook characteristics (shape, color, scale) are strictly preserved without alteration. The earring must appear naturally sized on the earlobe. Strictly preserve the original scale and dimensions; it should not look unnaturally large."

# Load rembg session once
try:
    print("Loading advanced ISNet model for jewelry extraction...")
    heavy_session = new_session("isnet-general-use")
except Exception as e:
    print(f"[!] Warning: Could not load rembg session: {e}")
    heavy_session = None

def upload_to_uguu(file_path: str) -> str:
    print(f"[*] Uploading {os.path.basename(file_path)} to temporary host...")
    with open(file_path, "rb") as f:
        files = {"files[]": f}
        r = requests.post("https://uguu.se/upload.php", files=files, timeout=60)
    data = r.json()
    if data.get("success"):
        return data["files"][0]["url"]
    else:
        raise Exception(f"Upload failed: {r.text}")

def call_claid_api(model_url: str, earring_url: str) -> str:
    headers = {
        "Authorization": f"Bearer {CLAID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "model": model_url,
            "clothing": [earring_url]
        },
        "output": {
            "format": "jpeg",
            "number_of_images": 1
        },
        "options": {
            "background": BACKGROUND,
            "pose": POSE
        }
    }
    response = requests.post(CLAID_ENDPOINT, json=payload, headers=headers, timeout=60)
    if response.status_code not in [200, 201, 202]:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    data = response.json()
    job_id = data.get("id") or data.get("data", {}).get("id")
    if not job_id:
        raise Exception(f"Failed to get job ID: {data}")
    return job_id

def poll_for_result(job_id: str) -> str:
    headers = {"Authorization": f"Bearer {CLAID_API_KEY}"}
    poll_url = f"{CLAID_ENDPOINT}/{job_id}"
    for _ in range(60):
        time.sleep(5)
        r = requests.get(poll_url, headers=headers, timeout=30)
        data = r.json()
        status = data.get("data", {}).get("status") or "unknown"
        if status in ["succeeded", "completed", "done", "DONE"]:
            result_data = data.get("data", {}).get("result", {})
            output_objects = result_data.get("output_objects", [])
            tmp_url = output_objects[0].get("tmp_url") if output_objects else None
            output_url = tmp_url or result_data.get("url") or data.get("data", {}).get("url")
            if output_url:
                return output_url
        if status in ["failed", "error"]:
            raise Exception(f"Claid job failed: {data}")
    raise Exception("Timed out waiting for Claid result.")

# ──────────────────────────────────────────────
# 1. THE WHITE BACKGROUND GENERATOR (from v1)
# ──────────────────────────────────────────────
def generate_white_bg_mockup(earring_path, output_path="white_mockup.png", canvas_size=4096, padding=0.28):
    earring_raw  = Image.open(earring_path).convert("RGBA")
    earring_nobg = remove(
        earring_raw, 
        session=heavy_session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=200, 
        alpha_matting_background_threshold=10,  
        alpha_matting_erode_size=0 
    )
    
    # Strict Bounding Box (fixes tiny scale issues)
    alpha_raw = np.array(earring_nobg.split()[3])
    coords = cv2.findNonZero((alpha_raw > 20).astype(np.uint8))
    if coords is not None:
        x, y, ew, eh = cv2.boundingRect(coords)
        earring_nobg = earring_nobg.crop((x, y, x+ew, y+eh))

    pad_px    = int(canvas_size * padding)
    max_space = canvas_size - (2 * pad_px)
    ratio     = min(max_space / earring_nobg.width, max_space / earring_nobg.height)
    target_w  = int(earring_nobg.width  * ratio)
    target_h  = int(earring_nobg.height * ratio)
    earring = earring_nobg.resize((target_w, target_h), Image.Resampling.LANCZOS)
    earring = earring.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
    alpha_np = np.array(earring.split()[3])
    
    # Create soft studio white canvas
    bg = Image.new("RGB", (canvas_size, canvas_size), (252, 252, 252))
    paste_x = (canvas_size - target_w) // 2
    paste_y = (canvas_size - target_h) // 2
    
    # Flat studio drop shadow (updated to match v3 heavier shadow)
    shadow_dark, shadow_blur, shadow_dx, shadow_dy = 0.75, 40, 45, 45
    s_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_img.putalpha(Image.fromarray(alpha_np).point(lambda p: int(p * shadow_dark)))
    
    shadow_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    shadow_layer.paste(s_img, (paste_x + shadow_dx, paste_y + shadow_dy), s_img)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, shadow_layer)
    bg.paste(earring, (paste_x, paste_y), earring)
    bg = bg.convert("RGB")
    
    bg.save(output_path, format="JPEG", quality=95)
    return output_path

# ──────────────────────────────────────────────
# 2. THE CUSTOM BACKGROUND GENERATOR (from v1)
# ──────────────────────────────────────────────
def auto_detect_plate(bg_path):
    bg_img = cv2.imread(bg_path)
    gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    h, w = bg_img.shape[:2]
    
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    edges = cv2.Canny(blurred, 30, 150)
    kernel = np.ones((9,9), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=3)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    image_center = (w/2, h/2)
    plate_width = w * 0.6 
    plate_cx, plate_cy = int(w/2), int(h/2)
    max_area = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > (w * h * 0.1): 
            x, y, cw, ch = cv2.boundingRect(cnt)
            if x < image_center[0] < x + cw and y < image_center[1] < y + ch:
                if area > max_area:
                    max_area = area
                    plate_width = cw
                    plate_cx, plate_cy = x + cw // 2, y + ch // 2
                    
    return plate_width, plate_cx, plate_cy, w

def generate_smart_mockup_final(earring_path, bg_path, output_path="smart_mockup.jpg", plate_coverage=0.35): 
    bg = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg.size
    plate_w_px, plate_cx, plate_cy, total_w_px = auto_detect_plate(bg_path)
    earring_scale = (plate_w_px / total_w_px) * plate_coverage

    earring_raw  = Image.open(earring_path).convert("RGBA")
    earring_nobg = remove(
        earring_raw, 
        session=heavy_session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=200, 
        alpha_matting_background_threshold=10,  
        alpha_matting_erode_size=0 
    )
    
    alpha_raw = np.array(earring_nobg.split()[3])
    coords = cv2.findNonZero((alpha_raw > 20).astype(np.uint8))
    if coords is not None:
        x, y, ew, eh = cv2.boundingRect(coords)
        earring_nobg = earring_nobg.crop((x, y, x+ew, y+eh))

    max_box_size = (plate_w_px / total_w_px) * plate_coverage * bg_w
    ratio = min(max_box_size / earring_nobg.width, max_box_size / earring_nobg.height)
    target_w = int(earring_nobg.width * ratio)
    target_h = int(earring_nobg.height * ratio)
    earring  = earring_nobg.resize((target_w, target_h), Image.Resampling.LANCZOS)
    earring  = earring.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
    
    alpha_np = np.array(earring.split()[3])
    kernel = np.ones((3,3), np.uint8)
    eroded_alpha = cv2.erode(alpha_np, kernel, iterations=1)
    edge_mask = cv2.subtract(alpha_np, eroded_alpha).astype(np.float32) / 255.0
    
    bg_rgb = bg.convert("RGB")
    bg_np  = np.array(bg_rgb, dtype=np.float32)
    cx, cy = plate_cx, plate_cy
    
    y1, y2 = max(0, cy-150), min(bg_h, cy+150)
    x1, x2 = max(0, cx-150), min(bg_w, cx+150)
    bg_avg = np.median(bg_np[y1:y2, x1:x2], axis=(0,1))

    blend = 0.15  
    earring_np = np.array(earring.convert("RGB"), dtype=np.float32)
    for i in range(3): 
        earring_np[:,:,i] = np.clip(earring_np[:,:,i] + (bg_avg[i] - 200.0) * blend, 0, 255)
        earring_np[:,:,i] = earring_np[:,:,i] * (1 - (edge_mask * 0.35)) 

    paste_x, paste_y = cx - target_w // 2, cy - target_h // 2
    bg_patch = bg_np[paste_y:paste_y+target_h, paste_x:paste_x+target_w]
    
    if bg_patch.shape[0] == target_h and bg_patch.shape[1] == target_w:
        lum = 0.299 * bg_patch[:,:,0] + 0.587 * bg_patch[:,:,1] + 0.114 * bg_patch[:,:,2]
        bright_level = np.percentile(lum, 90)
        shadow_map = np.clip(lum / (bright_level + 1e-5), 0.35, 1.0)
        sm_img = Image.fromarray((shadow_map * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.5))
        shadow_map = np.array(sm_img, dtype=np.float32) / 255.0
        for i in range(3): earring_np[:,:,i] *= shadow_map

    earring = Image.fromarray(earring_np.astype(np.uint8), "RGB")
    earring.putalpha(Image.fromarray(alpha_np)) 

    s_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_img.putalpha(Image.fromarray(alpha_np).point(lambda p: int(p * 0.75)))
    s_layer = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
    s_layer.paste(s_img, (paste_x + 15, paste_y + 15), s_img)
    s_layer = s_layer.filter(ImageFilter.GaussianBlur(radius=12))

    ao_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    ao_img.putalpha(Image.fromarray(alpha_np).point(lambda p: int(p * 0.60))) 
    ao_layer = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
    ao_layer.paste(ao_img, (paste_x, paste_y + 2), ao_img) 
    ao_layer = ao_layer.filter(ImageFilter.GaussianBlur(radius=2)) 

    result = bg.copy()
    result = Image.alpha_composite(result, s_layer)
    result = Image.alpha_composite(result, ao_layer)
    result.paste(earring, (paste_x, paste_y), earring)

    final = result.convert("RGB")
    final.save(output_path, format="JPEG", quality=95)
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_all_mockups.py <input_zip> [abstract_bg_img]")
        sys.exit(1)
        
    input_zip = sys.argv[1]
    abstract_bg = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_zip):
        print(f"[!] Error: {input_zip} not found.")
        sys.exit(1)
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "temp_processing")
    output_dir = os.path.join(temp_dir, "outputs")
    extract_dir = os.path.join(temp_dir, "extracted")
    
    # Cleanup previous runs
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(extract_dir)
    os.makedirs(output_dir)
    
    print(f"\n[*] Extracting {input_zip}...")
    with zipfile.ZipFile(input_zip, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    images = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.'):
                images.append(os.path.join(root, f))
                
    if not images:
        print("[!] No images found in ZIP.")
        sys.exit(1)
        
    print(f"[*] Found {len(images)} earrings to process.")
    
    # Upload default model once for all
    model_path = os.path.join(base_dir, "default_model.jpeg")
    if not os.path.exists(model_path):
        print(f"[!] Error: default_model.jpeg not found in {base_dir}")
        sys.exit(1)
    
    print("\n--- INITIALIZING CLAID AI MODEL ---")
    model_url = upload_to_uguu(model_path)
    
    for img_path in images:
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        out_white = os.path.join(output_dir, f"{base_name}.1.jpg")
        out_abstract = os.path.join(output_dir, f"{base_name}.2.jpg")
        out_claid = os.path.join(output_dir, f"{base_name}.3.jpg")
        
        print(f"\n--- PROCESSING: {base_name} ---")
        
        # 1. White Background
        print("[*] Generating White Studio Background (.1)...")
        generate_white_bg_mockup(img_path, output_path=out_white)
        
        # 2. Abstract Background
        if abstract_bg and os.path.exists(abstract_bg):
            print("[*] Generating Abstract Background (.2)...")
            generate_smart_mockup_final(img_path, bg_path=abstract_bg, output_path=out_abstract)
        else:
            print("[*] Generating Default White Studio Background (.2)...")
            generate_white_bg_mockup(img_path, output_path=out_abstract)
            
        # 3. Claid On-Model
        print("[*] Generating Claid On-Model (.3)...")
        # Extract the pure transparent earring to send to Claid (prevents hallucinating different earrings)
        transparent_earring_path = os.path.join(output_dir, f"{base_name}_transparent_temp.png")
        earring_raw = Image.open(img_path).convert("RGBA")
        earring_nobg = remove(
            earring_raw, 
            session=heavy_session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=200, 
            alpha_matting_background_threshold=10,  
            alpha_matting_erode_size=0 
        )
        alpha_raw = np.array(earring_nobg.split()[3])
        coords = cv2.findNonZero((alpha_raw > 20).astype(np.uint8))
        if coords is not None:
            x, y, ew, eh = cv2.boundingRect(coords)
            earring_nobg = earring_nobg.crop((x, y, x+ew, y+eh))
        earring_nobg.save(transparent_earring_path, format="PNG")
        
        earring_url = upload_to_uguu(transparent_earring_path)
        job_id = call_claid_api(model_url, earring_url)
        res_url = poll_for_result(job_id)
        print(f"[*] Downloading final image...")
        r = requests.get(res_url)
        with open(out_claid, "wb") as f:
            f.write(r.content)
        
        # Explicitly flush RAM to prevent batch memory accumulation
        try:
            del earring_raw
            del earring_nobg
        except:
            pass
        gc.collect()
            
    print("\n--- PACKAGING OUTPUTS ---")
    final_zip_name = os.path.basename(input_zip).replace(".zip", "_Final_Mockups.zip")
    final_zip_path = os.path.join(os.path.dirname(input_zip), final_zip_name)
    
    with zipfile.ZipFile(final_zip_path, 'w') as zipf:
        for f in os.listdir(output_dir):
            if f.endswith("_transparent_temp.png"):
                continue
            zipf.write(os.path.join(output_dir, f), f)
            
    # Cleanup
    shutil.rmtree(temp_dir)
    print(f"\n[SUCCESS] Final Mockups saved to: {final_zip_path}")

if __name__ == "__main__":
    main()
