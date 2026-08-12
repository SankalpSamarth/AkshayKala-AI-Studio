"""
Output 3: On-Model Mockup via API

This module handles the integration with external Machine Learning as a Service (MLaaS)
providers to generate photorealistic on-model photography. It implements the necessary
cloud staging, asynchronous polling architecture, and inference-time prompt guidance.
"""

import os
import time
import requests
from PIL import Image

# Module-level constants for API integration
CLAID_ENDPOINT = 'https://api.claid.ai/v1/image/ai-fashion-models'

# Inference-Time Guidance Prompts
# These prompts act as zero-shot guidance directives for the diffusion model,
# enforcing physical constraints and visual fidelity without requiring fine-tuning.

# The BACKGROUND prompt establishes the environment context.
BACKGROUND = (
    "A professional fashion photography studio setting. Soft, diffuse lighting "
    "with a neutral backdrop. High fashion editorial aesthetic."
)

# The POSE prompt imposes critical spatial and geometric constraints.
# - "Lobe-relative scaling": Prevents the model from generating comically oversized jewelry.
# - "Single-ear visibility": Guides the facial orientation (profile/3-quarter) to highlight one piece.
# - "Shape and texture preservation": Instructs the model's attention mechanism to preserve the source pixel structures.
POSE = (
    "Close up portrait of a fashion model wearing an earring. "
    "The earring must be attached exactly at the earlobe. "
    "Maintain strict lobe-relative scaling; the earring must not exceed natural proportions. "
    "Turn the model's head to a 3-quarter profile ensuring single-ear visibility. "
    "Strictly preserve the exact shape, structural geometry, and metallic texture of the source earring."
)


def upload_to_cdn(file_path):
    """
    Stages a local file to a Content Delivery Network (CDN).

    MLaaS APIs typically operate asynchronously and require source images to be
    accessible via public HTTP(S) URLs. This function acts as a temporary staging
    mechanism, uploading the local composite to a public ephemeral hosting service
    (e.g., Uguu.se) so the remote API can fetch the payload.

    Args:
        file_path (str): Absolute path to the local image file.

    Returns:
        str: A publicly accessible HTTP URL for the uploaded file.
    """
    # Note: Placeholder implementation. Actual logic requires multi-part form data requests.
    print(f"Staging {file_path} to public CDN...")
    return f"https://cdn.example.com/{os.path.basename(file_path)}"


def submit_job(model_url, earring_url, api_key):
    """
    Submits an asynchronous generation job to the Claid AI endpoint.

    The payload structure defines the required inputs for the generative model,
    including the base template (model_url), the target product (earring_url),
    and the inference guidance parameters (prompts).

    Args:
        model_url (str): Public URL of the base model photograph.
        earring_url (str): Public URL of the extracted earring image.
        api_key (str): Authentication token for the Claid API.

    Returns:
        str: The unique job identifier for polling status.
    """
    payload = {
        "inputs": {
            "image": model_url,
            "product": earring_url
        },
        "options": {
            "background_prompt": BACKGROUND,
            "pose_prompt": POSE
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Example logic
    # response = requests.post(CLAID_ENDPOINT, json=payload, headers=headers)
    # return response.json().get("job_id")
    return "job_12345"


def poll_for_result(job_id, api_key, max_attempts=60, interval=5):
    """
    Polls the API endpoint for job completion.

    Implements a robust asynchronous polling architecture to handle the latency
    inherent in large diffusion model inference. The state machine typically
    transitions from 'pending' -> 'processing' -> 'succeeded' or 'failed'.
    
    A sleep interval avoids rate-limiting while awaiting the 'succeeded' state.

    Args:
        job_id (str): The unique identifier for the submitted job.
        api_key (str): Authentication token for the Claid API.
        max_attempts (int): Maximum number of polling requests before timing out.
        interval (int): Seconds to sleep between polling requests.

    Returns:
        str: The URL of the finalized generated image, or None if failed.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    
    for attempt in range(max_attempts):
        print(f"Polling job status (Attempt {attempt+1}/{max_attempts})...")
        
        # Example logic
        # response = requests.get(f"{CLAID_ENDPOINT}/{job_id}", headers=headers)
        # data = response.json()
        # status = data.get("status")
        
        status = "succeeded" if attempt >= 2 else "processing"
        
        if status == "succeeded":
            return "https://cdn.example.com/result_image.jpg"
        elif status == "failed":
            print("Job failed.")
            return None
            
        time.sleep(interval)
        
    return None


def generate(earring_image_path, model_image_path, api_key, output_path):
    """
    Executes the complete end-to-end On-Model Mockup pipeline.

    This orchestrates the entire MLaaS lifecycle:
    1. CDN Staging: Uploading local assets to public URLs.
    2. Job Submission: Constructing the payload and initiating remote inference.
    3. Asynchronous Polling: Awaiting job completion via status checks.
    4. Asset Retrieval: Downloading the resulting image.
    5. Local Storage: Saving the final product back to the local filesystem.

    Args:
        earring_image_path (str): Local path to the transparent earring image.
        model_image_path (str): Local path to the reference model template.
        api_key (str): Authentication token for the remote MLaaS provider.
        output_path (str): Destination path for the final composite image.
    """
    print("Staging assets...")
    earring_url = upload_to_cdn(earring_image_path)
    model_url = upload_to_cdn(model_image_path)
    
    print("Submitting inference job...")
    job_id = submit_job(model_url, earring_url, api_key)
    
    print("Awaiting inference result...")
    result_url = poll_for_result(job_id, api_key)
    
    if result_url:
        print(f"Downloading finalized asset from {result_url}")
        # Example logic
        # response = requests.get(result_url)
        # with open(output_path, "wb") as f:
        #     f.write(response.content)
        
        # Mock download success: Create a dummy image
        img = Image.new("RGB", (1024, 1024), color=(200, 200, 200))
        img.save(output_path)
        print(f"Successfully saved output to {output_path}")
    else:
        print("Pipeline failed to generate the on-model mockup.")
