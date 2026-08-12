FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests pillow "rembg[cpu]" numpy opencv-python-headless gradio python-dotenv

# Pre-download the U-2-Net model for rembg to save time on first run
RUN python -c "from rembg import new_session; new_session('isnet-general-use')"

EXPOSE 7860

COPY . .

CMD ["python", "app.py"]
