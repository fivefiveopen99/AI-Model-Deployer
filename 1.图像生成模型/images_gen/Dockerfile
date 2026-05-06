FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/hf_home \
    MODEL_DIR=/app/model \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libfontconfig1 \
        libxrender1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /hf_home

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir \
        fastapi==0.104.1 \
        "uvicorn[standard]==0.24.0" \
        pydantic==2.5.0 \
        python-multipart==0.0.6 \
        "diffusers[torch]" \
        transformers \
        accelerate \
        safetensors \
        peft \
        pillow \
        huggingface_hub

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

