# Project Documentation Report
# AkshayKala AI Studio: Generative AI Engine for Studio-Quality Jewelry Mockups

---

## Table of Contents

1. Executive Summary
2. Problem Statement
3. Project Objectives
4. Technology Stack
5. System Architecture
6. Development Journey
7. Key Challenges and Solutions
8. Final Pipeline Features
9. Results and Business Impact
10. Conclusion

---

## 1. Executive Summary

This report documents the end-to-end development of the AkshayKala AI Studio pipeline — a fully containerized, automated generative AI system designed to produce professional, studio-quality jewelry mockups for e-commerce applications.

The system replaces traditional, expensive fashion model photoshoots with a three-output automated pipeline. From a single ZIP file of raw earring product images, the pipeline generates white studio mockups, brand-specific abstract background composites, and photorealistic on-model fashion mockups. The entire system is deployable on Mac and Windows with a single double-click, with no manual configuration required beyond entering an API key.

---

## 2. Problem Statement

The traditional workflow for producing jewelry e-commerce photography presented four significant challenges for AkshayKala:

**High Cost.** Professional studio photography for jewelry requires paid fashion models, lighting equipment, studio rentals, and a dedicated photography team. For a brand with hundreds of SKUs, this cost becomes prohibitive.

**Logistical Friction.** Coordinating a photoshoot for each new product involves scheduling models, booking studios, managing revisions, and waiting on post-production editing — a process that can take days or weeks per batch.

**Visual Inconsistency.** Human-driven photoshoots produce variations in lighting, angle, skin tone, and background that make it difficult to maintain a uniform and professional brand identity across a product catalogue.

**Scalability Gap.** As the product catalogue grows, the cost and effort of traditional photography scales linearly. There was no scalable, automated system that could produce consistent, high-quality imagery at the speed of a software pipeline.

---

## 3. Project Objectives

The project set out to achieve four core technical objectives:

1. Automate high-precision background removal and transparent mask generation using advanced computer vision models, with no manual editing required.

2. Programmatically composite white studio and abstract brand backgrounds with physically accurate drop shadows and ambient occlusion effects.

3. Leverage a generative AI API to synthesize photorealistic on-model fashion images, while strictly preserving the jewelry's original scale, shape, color, and texture.

4. Deliver all of the above as a containerized, full-stack web application capable of batch-processing entire product catalogues with a single-click operation.

---

## 4. Technology Stack

**Frontend Layer**
The user interface is built with the Gradio Blocks framework, styled with a custom CSS design system using the Google Inter typeface and a corporate blue color palette. The interface is entirely browser-based and requires no separate frontend installation.

**Backend Processing Layer**
The core processing engine is written in Python 3.12. Image manipulation is handled by Pillow and OpenCV. NumPy is used for all numerical array operations including shadow map computations, alpha channel manipulation, and ambient occlusion blending.

**Computer Vision**
Background removal and transparent mask generation is performed by the ISNet general-use model via the Rembg library. This model was selected for its superior edge preservation on fine, complex shapes such as jewelry hooks and chains, outperforming the standard U-2-Net model used in earlier versions.

**Generative AI**
On-model fashion image synthesis is powered by the Claid.ai Fashion Models API. The system sends the extracted transparent earring alongside a reference model image and a set of strict directional prompts to the API endpoint, then polls for the asynchronously generated result.

**Infrastructure**
The entire application is containerized using Docker with a Debian slim base image. This ensures a fully portable, reproducible environment that runs identically across Mac and Windows without any manual dependency installation.

**Data Management**
API credentials are stored in a local JSON database file. The active key is loaded at runtime via python-dotenv. This approach keeps credentials secure, version-control-safe, and manageable through the UI.

---

## 5. System Architecture

The pipeline follows a four-tier architecture:

**Client Tier:** The user interacts with the system through a standard web browser at http://localhost:7860. No special client software is required.

**Application Tier (Docker Container):** Inside the Docker container, a Gradio web server listens on port 7860. All user requests are routed to the Python processing engine, which orchestrates the computer vision module and all three output generators.

**Local Storage Tier:** The application reads and writes to two local files — api_keys.json for credential and credit storage, and .env for the active API key. These files persist on the host machine through Docker volume mounting.

**External Cloud API Tier:** The on-model generator communicates with two external services over HTTPS. The transparent earring image is first uploaded to Uguu.se temporary object storage to obtain a public URL, which is then passed to the Claid.ai API along with the model image URL and generation parameters.

---

## 6. Development Journey

**Versions 1 and 2: Proof of Concept**
Development began with standalone command-line Python scripts. The Rembg library with the U-2-Net model was integrated for initial background removal. This phase established the foundational compositing logic for white backgrounds and proved the technical feasibility of the approach.

**Versions 3 and 4: Containerization and API Integration**
The architecture was transitioned to Docker to resolve local operating system dependency conflicts and ensure that the application could be reliably shared across different machines. The Claid.ai Generative AI API was integrated during this phase. Initial testing revealed significant anatomical scaling anomalies, where the AI was generating oversized earrings and distorting their shape.

**Version 5: The Final Master Pipeline**
This final version represented a complete architectural and UX overhaul. The command-line interface was replaced with a professional Gradio web application. The computer vision processing was refactored to a single-pass extraction model to resolve memory exhaustion issues. A full API Key Manager with a local credit tracker was implemented. Cross-platform launchers for both Mac and Windows were created.

---

## 7. Key Challenges and Solutions

**Challenge 1: Anatomical Scaling Anomalies**

During initial testing of the Claid.ai integration, the generative model consistently produced images where the earring appeared disproportionately large relative to the human model's ear. Additionally, the structural details of the hook and chain were sometimes altered.

The solution was to engineer a comprehensive set of directional constraints within the API prompt payload. These constraints explicitly instructed the model to use the earlobe as a proportional reference, to preserve the exact shape, texture, and color of the provided jewelry, and to render only a single ear prominently in the frame. This approach brought the anatomical accuracy of the results to an acceptable production standard.

**Challenge 2: Memory Exhaustion and System Instability**

When processing a ZIP containing multiple product images, the pipeline was crashing with Out-Of-Memory errors. Profiling revealed that the heavy ISNet computer vision model was being loaded and run once for each of the three output types per image, tripling the memory footprint of each processing cycle.

The architecture was refactored to a single-pass extraction model. ISNet now runs exactly once per image, storing the resulting transparent mask in memory. This cached mask is then passed to all three generators as an argument. Combined with explicit Python garbage collection calls after each image cycle, this eliminated the OOM crashes entirely.

**Challenge 3: Credential Security and Management**

The initial implementation stored the API key as a hardcoded string in the source code, which presented a serious security vulnerability and made it impossible to rotate keys or manage multiple accounts.

A dedicated API Key Manager was designed and implemented. Credentials are stored in a structured JSON database file that is excluded from version control via .gitignore. The Gradio UI provides a full dashboard to add, view (with masked keys), and delete credentials. A local credit tracking system was also integrated, which automatically deducts 2 credits per successful model generation and enforces a strict pre-generation validation check to prevent failed API calls due to insufficient credits.

---

## 8. Final Pipeline Features

The completed v5 pipeline delivers the following capabilities:

**Three Output Types Per Image:** Each earring image produces a white studio mockup, an abstract brand-background composite, and an AI-generated on-model fashion mockup — all from a single batch operation.

**Single-Pass Computer Vision:** The ISNet extraction runs once per image, with the transparent mask reused by all three generators, maximising both speed and memory efficiency.

**Secure API Key Manager:** A full-featured credential management dashboard supporting multiple API keys with email tracking, masked key display, and deletion.

**Local Credit Tracker:** Automatically tracks and deducts API credits after each successful generation. Blocks execution with a clear error message if the available balance is insufficient for the requested batch size.

**Batch Processing and ZIP Output:** The user uploads a ZIP of product images and downloads a complete ZIP of all generated mockups at the end of the run.

**Cross-Platform Deployment:** The system ships with both a Mac .command launcher and a Windows .bat launcher. Docker handles all environment setup automatically on either operating system.

---

## 9. Results and Business Impact

The completed pipeline successfully achieves its four core objectives. The system generates three distinct categories of professional imagery per product with no manual editing. A batch of earring images can be processed in a fraction of the time required for a traditional photoshoot.

The business impact for AkshayKala is significant. The cost of producing professional product imagery is reduced from the full overhead of a studio photoshoot to a minor API credit expenditure. The visual consistency of the output is guaranteed by the standardized compositing logic, ensuring a uniform brand identity across the entire catalogue. As the product catalogue grows, the pipeline scales with no additional cost or logistical complexity.

---

## 10. Conclusion

This project delivered a production-ready, containerized Generative AI pipeline that transforms raw jewelry product images into three categories of professional mockups automatically and in a single batch operation. The system integrates advanced computer vision, a custom generative AI compositing engine, a secure multi-credential management database, and a cross-platform deployment architecture.

The development journey involved solving non-trivial engineering challenges in generative AI prompt engineering, computer vision memory management, and secure credential handling. The final product is a stable, secure, and immediately deployable tool that provides genuine commercial value to AkshayKala's e-commerce operations.

---

*Report prepared by: Sankalp Samarth*
*Project: AkshayKala AI Studio Internship*
*Year: 2026*
