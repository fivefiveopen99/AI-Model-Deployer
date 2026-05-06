FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel

RUN apt-get update \
    && apt-get install -y vim git libgl1-mesa-glx libsm6 libxext6 libfontconfig1 libxrender1 libglib2.0-0

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install packaging ninja
RUN MAX_JOBS=4 pip install flash_attn==2.8.2 --no-build-isolation

ENV HF_ENDPOINT="https://hf-mirror.com"
RUN mkdir /hf_home
ENV HF_HOME="/hf_home"

RUN pip install torch==2.8.0 diffusers["torch"]==0.35.2 transformers==4.57.1 bitsandbytes datasets xformers peft tensorboard opencv-python pytorch-lightning controlnet_aux basicsr
RUN python - <<'PY'
import site
from pathlib import Path

paths = [Path(p) / "basicsr" / "data" / "degradations.py" for p in site.getsitepackages()]
target = next((p for p in paths if p.exists()), None)

if target is None:
    raise SystemExit("basicsr/data/degradations.py not found")

text = target.read_text()
old = "from torchvision.transforms.functional_tensor import rgb_to_grayscale"
new = "from torchvision.transforms.functional import rgb_to_grayscale"

if old in text:
    target.write_text(text.replace(old, new))
    print(f"patched {target}")
else:
    print(f"no patch needed: {target}")
PY
RUN pip install gradio
RUN pip install huggingface_hub[cli]
