# AkshayKala AI Studio
**Generative AI Engine for Fashion Mockup Synthesis**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

A production-grade, containerized web application that automates the generation of professional jewelry mockups. The system replaces expensive fashion model photoshoots with an end-to-end automated pipeline powered by advanced Computer Vision and Generative AI.

---

## ⚡ How It Works

**Input:** A `.zip` file containing raw earring product photographs.  
**Engine:** A single-pass ISNet extraction, custom shadow compositing, and Claid.ai's fashion generative model.  
**Output:** Three professional mockups per earring in under 30 seconds.

| Output 1 | Output 2 | Output 3 |
|:---:|:---:|:---:|
| **White Studio Background** | **Abstract Brand Composite** | **Photorealistic On-Model** |
| Clean e-commerce standard with dynamic drop shadows. | Harmonized color blending and ambient occlusion on custom surfaces. | AI-generated fashion model with strict anatomical scaling. |

---

## 🚀 Quick Start (Docker)

The entire application runs inside a portable Docker container with no manual dependency installation required.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AkshayKala-AI-Studio.git
   cd AkshayKala-AI-Studio
   ```

2. **Launch the Interface:**
   - **Mac/Linux:** Double-click `scripts/run_mac.command` or run `./scripts/run_mac.command`
   - **Windows:** Double-click `scripts/run_windows.bat`

3. **Open the Studio:**
   Navigate to `http://localhost:7860` in your web browser.

> [!NOTE]
> To use the On-Model mockup feature, you will need a [Claid.ai](https://claid.ai) API key. You can add and manage your keys securely within the Gradio web interface under **System Settings**.

---

## 🏗️ Project Structure

This repository contains the final production system (`app.py`) along with standalone reference modules (`core/`) that break down the technical logic for educational and portfolio review purposes.

```text
AkshayKala-AI-Studio/
├── app.py                      # Main Gradio application & unified pipeline
├── Dockerfile                  # Container definition
├── scripts/                    # Cross-platform Docker launchers
├── core/                       # Standalone reference implementations
│   ├── segmentation.py             # ISNet extraction & alpha matting
│   ├── white_studio_generator.py   # Output 1 logic
│   ├── abstract_background_generator.py # Output 2 logic
│   └── on_model_generator.py       # Output 3 logic
├── docs/                       # Technical documentation
│   ├── Project_Report.md           # Full engineering whitepaper
│   ├── Architecture.md             # System architecture diagram
│   └── Development_Journey.md      # Iterative changelog (v1 to v5)
└── examples/                   # Sample inputs and outputs
```

---

## 🛠️ Technology Stack

| Category | Technology |
|---|---|
| **Frontend UI** | Gradio Blocks (Custom Corporate Theme) |
| **Backend Engine** | Python 3.12 |
| **Computer Vision** | OpenCV, Pillow, Numpy |
| **Background Matting** | ISNet general-use (via Rembg) |
| **Generative AI** | Claid.ai Fashion Models API |
| **Infrastructure** | Docker |

---

## 📖 Documentation

For a deep dive into the engineering decisions, memory optimization (solving OOM crashes), and prompt engineering (solving anatomical scaling anomalies), please refer to the [Project Report](docs/Project_Report.md).

---

## 🤝 Acknowledgements
Developed by **Sankalp Samarth** for the AkshayKala AI Studio.
