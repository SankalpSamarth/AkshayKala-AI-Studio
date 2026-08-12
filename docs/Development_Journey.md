# Development Journey: v1 to v5

This document traces the iterative engineering decisions that shaped the AkshayKala AI Studio
from a proof-of-concept script to a production-grade containerized pipeline.

---

## Phase 1–2: Proof of Concept

Development began with standalone command-line Python scripts. The Rembg library with the
U-2-Net model was integrated for initial background removal. This phase established the
foundational compositing logic for white studio backgrounds and proved the technical
feasibility of automated jewelry mockup generation.

**Key decisions:**
- Pillow for image manipulation, OpenCV for computer vision operations
- U-2-Net for segmentation (later replaced by ISNet for better edge preservation)
- Shadow rendering via alpha channel manipulation and Gaussian blur

---

## Phase 3–4: Containerization and API Integration

The architecture was transitioned to Docker to resolve local dependency conflicts and
guarantee environment parity across operating systems. The Claid.ai Generative API was
integrated during this phase for on-model fashion mockup synthesis.

**Key challenges encountered:**
- Anatomical scaling anomalies: the generative model consistently produced oversized earrings
- Shape and texture hallucination on fine jewelry details (hooks, chains)
- Environment inconsistencies between macOS and Windows development machines

**Solutions implemented:**
- Engineered strict prompt constraints with lobe-relative scaling and single-ear visibility
- Containerized the entire stack with Docker for reproducible builds
- Implemented CDN staging via Uguu.se to provide public URLs to the API

---

## Phase 5: The Production Pipeline

The final version represents a complete architectural and UX overhaul:

- **Gradio Web Interface** replaced the CLI with a professional, browser-based application
- **Single-pass extraction** resolved memory exhaustion by running ISNet once per image
  instead of once per output type (3x reduction in model inference)
- **API Key Manager** with a local JSON database, masked key display, and credit tracking
- **Cross-platform launchers** for both macOS (.command) and Windows (.bat)
- **Aggressive garbage collection** after each image cycle to prevent OOM crashes in batch
  processing

---

## Architecture Evolution

| Version | Interface | Extraction | Deployment | API |
|---------|-----------|------------|------------|-----|
| v1–v2 | CLI | U-2-Net, multi-pass | Local Python | None |
| v3–v4 | CLI | ISNet, multi-pass | Docker | Claid.ai |
| v5 | Gradio Web | ISNet, single-pass | Docker | Claid.ai + Key Manager |
