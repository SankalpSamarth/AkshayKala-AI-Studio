import os
import time
import zipfile
import shutil
import requests
from PIL import Image, ImageFilter
import numpy as np
import cv2
import gc
from rembg import remove, new_session
import gradio as gr
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- API KEY DATABASE LOGIC ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_keys.json")

def load_keys_db():
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except:
        return []

def save_keys_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

def get_email_list():
    return [k["email"] for k in load_keys_db()]

# --- CONFIG ---
def get_api_key():
    return os.environ.get("CLAID_API_KEY", "")

CLAID_ENDPOINT = "https://api.claid.ai/v1/image/ai-fashion-models"
BACKGROUND     = "soft neutral studio background, professional jewelry photography, ultra high quality output. Make the fashion model wear the provided earring on only ONE ear (the ear that is most clearly visible). Keep the other ear bare or out of focus. High-end editorial style. The characteristics of the hook and earring must not alter at all; preserve exact shape, texture, and color. Ensure the jewelry is scaled to a realistic, delicate size relative to the human earlobe. Do not oversize or magnify the earring. Maintain natural physical proportions between the jewelry and human anatomy."
POSE           = "portrait, close-up, angled slightly so only one ear is prominently visible, wearing an earring on the fully visible ear. Produce high quality output and ensure the earring and hook characteristics (shape, color, scale) are strictly preserved without alteration. The earring must appear naturally sized on the earlobe. Strictly preserve the original scale and dimensions; it should not look unnaturally large."

print("Loading advanced ISNet model for jewelry extraction...")
try:
    heavy_session = new_session("isnet-general-use")
except Exception as e:
    print(f"[!] Warning: Could not load rembg session: {e}")
    heavy_session = None

def upload_to_uguu(file_path: str) -> str:
    with open(file_path, "rb") as f:
        files = {"files[]": f}
        r = requests.post("https://uguu.se/upload.php", files=files, timeout=60)
    data = r.json()
    if data.get("success"):
        return data["files"][0]["url"]
    else:
        raise Exception(f"Upload failed: {r.text}")

def call_claid_api(model_url: str, earring_url: str) -> str:
    api_key = get_api_key()
    if not api_key:
        raise Exception("API Key is missing! Please configure it below.")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
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
    headers = {"Authorization": f"Bearer {get_api_key()}"}
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
# 1. THE WHITE BACKGROUND GENERATOR
# ──────────────────────────────────────────────
def generate_white_bg_mockup(earring_nobg, output_path="white_mockup.png", canvas_size=4096, padding=0.28):
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
    
    bg = Image.new("RGB", (canvas_size, canvas_size), (252, 252, 252))
    paste_x = (canvas_size - target_w) // 2
    paste_y = (canvas_size - target_h) // 2
    
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
# 2. THE CUSTOM BACKGROUND GENERATOR
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

def generate_smart_mockup_final(earring_nobg, bg_path, output_path="smart_mockup.jpg", plate_coverage=0.35): 
    bg = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg.size
    plate_w_px, plate_cx, plate_cy, total_w_px = auto_detect_plate(bg_path)
    
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

def process_pipeline(input_zip, bg_file, model_file, do_white, do_abstract, do_model, progress=gr.Progress()):
    if not input_zip:
        return [], None, "No input ZIP provided."
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "gradio_temp")
    output_dir = os.path.join(temp_dir, "outputs")
    extract_dir = os.path.join(temp_dir, "extracted")
    
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(extract_dir)
    os.makedirs(output_dir)
    
    with zipfile.ZipFile(input_zip.name, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    images = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.'):
                images.append(os.path.join(root, f))
                
    if not images:
        return [], None, "No images found in ZIP."
        
    model_path = model_file.name if model_file else os.path.join(base_dir, "default_model.jpeg")
    abstract_bg = bg_file.name if bg_file else None

    # Strict Local Credit Check
    active_email = None
    if do_model:
        active_key = get_api_key()
        keys = load_keys_db()
        available_credits = 0
        for k in keys:
            if k["key"] == active_key:
                active_email = k["email"]
                available_credits = k.get("credits", 0)
                break
        
        credits_needed = len(images) * 2
        if active_email and available_credits < credits_needed:
            return [], None, f"🔴 Not enough credits! You need {credits_needed} credits, but {active_email} only has {available_credits} left. Update your API key in Settings."

    # Only upload the model to Uguu if the user requested the model mockup
    model_url = None
    if do_model:
        progress(0, desc="Uploading model template...")
        try:
            model_url = upload_to_uguu(model_path)
        except Exception as e:
            return [], None, f"Model upload failed: {str(e)}"
    
    gallery_images = []
    
    total = len(images)
    for idx, img_path in enumerate(images):
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        progress((idx) / total, desc=f"Processing: {base_name}")
        
        # Extract ONCE per image
        earring_raw = Image.open(img_path).convert("RGBA")
        earring_nobg = remove(
            earring_raw, 
            session=heavy_session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=200, 
            alpha_matting_background_threshold=10,  
            alpha_matting_erode_size=0 
        )
        
        if do_white:
            out_white = os.path.join(output_dir, f"{base_name}_white.jpg")
            generate_white_bg_mockup(earring_nobg.copy(), output_path=out_white)
            gallery_images.append(out_white)
            
        if do_abstract:
            out_abstract = os.path.join(output_dir, f"{base_name}_abstract.jpg")
            if abstract_bg and os.path.exists(abstract_bg):
                generate_smart_mockup_final(earring_nobg.copy(), bg_path=abstract_bg, output_path=out_abstract)
            else:
                # Default behavior if abstract checked but no custom bg provided
                generate_white_bg_mockup(earring_nobg.copy(), output_path=out_abstract)
            gallery_images.append(out_abstract)
            
        if do_model and model_url:
            out_claid = os.path.join(output_dir, f"{base_name}_model.jpg")
            transparent_earring_path = os.path.join(output_dir, f"{base_name}_transparent_temp.png")
            
            alpha_raw = np.array(earring_nobg.split()[3])
            coords = cv2.findNonZero((alpha_raw > 20).astype(np.uint8))
            if coords is not None:
                x, y, ew, eh = cv2.boundingRect(coords)
                earring_nobg_cropped = earring_nobg.crop((x, y, x+ew, y+eh))
            else:
                earring_nobg_cropped = earring_nobg
                
            earring_nobg_cropped.save(transparent_earring_path, format="PNG")
            
            try:
                earring_url = upload_to_uguu(transparent_earring_path)
                job_id = call_claid_api(model_url, earring_url)
                res_url = poll_for_result(job_id)
                r = requests.get(res_url)
                with open(out_claid, "wb") as f:
                    f.write(r.content)
                gallery_images.append(out_claid)
                
                # Deduct 2 credits locally
                if active_email:
                    db_keys = load_keys_db()
                    for dk in db_keys:
                        if dk["email"] == active_email:
                            dk["credits"] = max(0, dk.get("credits", 0) - 2)
                            break
                    save_keys_db(db_keys)
            except Exception as e:
                print(f"Error on Claid step for {base_name}: {e}")
                
        # GC
        try:
            del earring_raw
            del earring_nobg
        except:
            pass
        gc.collect()

    progress(1.0, desc="Packaging outputs...")
    final_zip_name = "Final_Mockups.zip"
    final_zip_path = os.path.join(base_dir, final_zip_name) # save in base dir so it persists
    if os.path.exists(final_zip_path):
        os.remove(final_zip_path)

    with zipfile.ZipFile(final_zip_path, 'w') as zipf:
        for f in os.listdir(output_dir):
            if f.endswith("_transparent_temp.png"):
                continue
            zipf.write(os.path.join(output_dir, f), f)
            
    return gallery_images, final_zip_path, "Processing complete!"

def set_active_key(email):
    if not email:
        return "Please select an email."
    keys = load_keys_db()
    for k in keys:
        if k["email"] == email:
            os.environ["CLAID_API_KEY"] = k["key"].strip()
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            with open(env_path, "w") as f:
                f.write(f"CLAID_API_KEY={k['key'].strip()}\n")
            return f"Active API Key set to: {email} ✅"
    return "Error: Email not found."

def add_new_key(email, key, credits):
    email = email.strip()
    key = key.strip()
    if not email or not key:
        return "Email and Key are required.", gr.update(), gr.update()
    
    keys = load_keys_db()
    for k in keys:
        if k["email"] == email:
            k["key"] = key
            k["credits"] = int(credits)
            save_keys_db(keys)
            set_active_key(email)
            return f"Updated key for {email} ✅", gr.update(choices=get_email_list(), value=email), gr.update(choices=get_email_list())
            
    keys.append({"email": email, "key": key, "credits": int(credits)})
    save_keys_db(keys)
    set_active_key(email) # Auto set new key as active
    return f"Added new key for {email} ✅", gr.update(choices=get_email_list(), value=email), gr.update(choices=get_email_list())

def view_keys(show_full=False):
    keys = load_keys_db()
    if show_full:
        return [[k["email"], k["key"], k.get("credits", 0)] for k in keys]
    else:
        # Mask the key, only showing the last 4 characters for security
        return [[k["email"], "•" * 24 + k["key"][-4:] if len(k["key"]) >= 4 else "••••••••", k.get("credits", 0)] for k in keys]

def delete_key(email):
    if not email:
        return "Please select an email to delete.", gr.update(), gr.update()
    keys = load_keys_db()
    keys = [k for k in keys if k["email"] != email]
    save_keys_db(keys)
    return f"Deleted key for {email} 🗑️", gr.update(choices=get_email_list()), gr.update(choices=get_email_list())

# --- GRADIO UI ---
theme = gr.themes.Base(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="gray",
    font=gr.themes.GoogleFont("Inter"),
).set(
    body_background_fill="#F0F4F8",
    block_background_fill="#FFFFFF",
    button_primary_background_fill="#1E40AF",
    button_primary_background_fill_hover="#1D4ED8",
    button_primary_text_color="#FFFFFF",
    button_secondary_background_fill="#E2E8F0",
    button_secondary_text_color="#1E293B",
    input_background_fill="#FFFFFF",
    input_border_color="#94A3B8",        # Darker border so it's clearly visible
    input_border_color_focus="#1E40AF",
    input_border_width="1px",            # Explicit border width to create the rounded square box
    body_text_color="#1E293B",
    block_title_text_color="#0F172A",
    block_label_text_color="#475569",
    block_shadow="0 1px 3px rgba(0,0,0,0.08)",
    block_border_color="#E2E8F0",
    block_radius="8px",
    input_radius="6px",
    button_large_radius="6px",
)

with gr.Blocks(theme=theme, title="AkshayKala AI Studio") as demo:
    gr.Markdown("# AkshayKala AI Studio - Earring Mockup Engine")
    gr.Markdown("Professional automated batch processing for Studio, Abstract, and On-Model jewelry mockups.")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Input Settings")
            input_zip = gr.File(label="Upload Earring ZIP", file_types=[".zip"])
            bg_file = gr.File(label="Abstract Background Template (Optional)", file_types=["image"])
            model_file = gr.File(label="Fashion Model Template (Optional)", file_types=["image"])
            
            gr.Markdown("### Output Variations")
            do_white = gr.Checkbox(label="White Background", value=True)
            do_abstract = gr.Checkbox(label="Abstract Background", value=True)
            do_model = gr.Checkbox(label="Model Mockup (Uses API Credits)", value=True)
            
            submit_btn = gr.Button("Generate Mockups", variant="primary")
            status_text = gr.Textbox(label="Status", interactive=False)
            
        with gr.Column(scale=2):
            gr.Markdown("### Results Gallery")
            gallery = gr.Gallery(label="Generated Variations", columns=3, height="auto")
            download_zip = gr.File(label="Download Full Batch (ZIP)", interactive=False)

    submit_btn.click(
        fn=process_pipeline,
        inputs=[input_zip, bg_file, model_file, do_white, do_abstract, do_model],
        outputs=[gallery, download_zip, status_text]
    )
    
    gr.Markdown("---")
    with gr.Accordion("⚙️ System Settings (API Key Manager)", open=False):
        gr.Markdown("Manage your Claid.ai API keys and track which email they belong to.")
        
        with gr.Row():
            active_key_dropdown = gr.Dropdown(label="Select Active API Key (by Email)", choices=get_email_list(), scale=3)
            active_status = gr.Textbox(label="Status", interactive=False, scale=1)
            active_key_dropdown.change(fn=set_active_key, inputs=active_key_dropdown, outputs=active_status)
            
        with gr.Tabs():
            with gr.Tab("Add New Key"):
                new_email = gr.Textbox(label="Email Address", placeholder="user@example.com")
                new_key = gr.Textbox(label="Claid.ai API Key", type="password")
                new_credits = gr.Number(label="Starting Credits", value=50, precision=0)
                add_btn = gr.Button("Save Key", variant="primary")
                add_status = gr.Textbox(label="Status", interactive=False)
                
            with gr.Tab("View Saved Keys"):
                with gr.Row():
                    view_btn = gr.Button("Refresh List")
                    show_keys_checkbox = gr.Checkbox(label="👁️ Reveal Full API Keys", value=False)
                keys_table = gr.Dataframe(headers=["Email", "API Key", "Credits Remaining"], type="array")
                
                # Update table on button click OR checkbox toggle
                view_btn.click(fn=view_keys, inputs=[show_keys_checkbox], outputs=keys_table)
                show_keys_checkbox.change(fn=view_keys, inputs=[show_keys_checkbox], outputs=keys_table)
                
            with gr.Tab("Delete Key"):
                delete_dropdown = gr.Dropdown(label="Select Email to Delete", choices=get_email_list())
                delete_btn = gr.Button("Delete Key", variant="stop")
                delete_status = gr.Textbox(label="Status", interactive=False)
                
        # Connect Actions
        add_btn.click(
            fn=add_new_key, 
            inputs=[new_email, new_key, new_credits], 
            outputs=[add_status, active_key_dropdown, delete_dropdown]
        )
        delete_btn.click(
            fn=delete_key, 
            inputs=delete_dropdown, 
            outputs=[delete_status, active_key_dropdown, delete_dropdown]
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
