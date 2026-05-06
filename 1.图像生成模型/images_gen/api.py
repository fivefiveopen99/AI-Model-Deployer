import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional

import torch
from diffusers import AutoPipelineForText2Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pipeline = None
pipeline_lock = None

BASE_MODEL_ID = os.getenv("BASE_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-v1-5")
MODEL_DIR = os.getenv("MODEL_DIR")
LORA_WEIGHT_NAME = os.getenv("LORA_WEIGHT_NAME", "pytorch_lora_weights.safetensors")
DEVICE_TYPE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "4"))
MAX_PIXELS = int(os.getenv("MAX_PIXELS", str(1024 * 1024)))
DEFAULT_NEGATIVE_PROMPT = (
    "Text, blurry, out of focus, complex, color, noisy, multiple patterns, low quality, "
    "photo, realistic, messy, hand drawn, watercolor, text, noise, low resolution."
)


class GenerateRequest(BaseModel):
    position: Literal["center", "side"] = "center"
    class_name: str = Field(default="unknown", min_length=1, max_length=80)
    width: int = Field(default=128, ge=64, le=1024)
    height: int = Field(default=128, ge=64, le=1024)
    num_inference_steps: int = Field(default=50, ge=10, le=100)
    num_images: int = Field(default=1, ge=1)
    negative_prompt: str = Field(default=DEFAULT_NEGATIVE_PROMPT, max_length=1000)
    seed: Optional[int] = Field(default=None, ge=0)

    @field_validator("width", "height")
    @classmethod
    def validate_dimension(cls, value: int) -> int:
        if value % 8 != 0:
            raise ValueError("width and height must be multiples of 8")
        return value

    @field_validator("num_images")
    @classmethod
    def validate_num_images(cls, value: int) -> int:
        if value > MAX_IMAGES:
            raise ValueError(f"num_images must be <= {MAX_IMAGES}")
        return value


class PredictRequest(BaseModel):
    inputs: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(BaseModel):
    filename: str
    content_type: str = "image/png"
    base64: str


class GenerateResponse(BaseModel):
    success: bool
    model_type: str = "image_generation"
    prompt: str
    images: List[GeneratedImage]


def get_prompt(position: str, class_name: str) -> str:
    class_prompt = "" if class_name == "unknown" else f"inspired by the shapes of {class_name}, "
    prompt_template = (
        "A pattern design at {} position, {}graphic design, black and white, "
        "minimalistic, sharp lines, vector art, high contrast, industrial design, clean and organized."
    )
    return prompt_template.format(position, class_prompt)


def encode_png(image, filename: str) -> GeneratedImage:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return GeneratedImage(filename=filename, base64=base64.b64encode(buffer.getvalue()).decode("utf-8"))


def resolve_model_dir() -> str:
    candidates = [MODEL_DIR, "/app/model", "/app/lora_patch_1112"]
    for candidate in candidates:
        if candidate and os.path.exists(os.path.join(candidate, LORA_WEIGHT_NAME)):
            return candidate

    for root, dirs, files in os.walk("/app"):
        dirs[:] = [name for name in dirs if not name.startswith(".") and name not in {"__pycache__", "outputs"}]
        if LORA_WEIGHT_NAME in files:
            return root

    return MODEL_DIR or "/app/model"


def load_pipeline():
    model_dir = resolve_model_dir()
    weight_path = os.path.join(model_dir, LORA_WEIGHT_NAME)
    if not os.path.exists(weight_path):
        raise RuntimeError(f"LoRA weight file not found: {weight_path}")

    dtype = torch.float16 if DEVICE_TYPE.startswith("cuda") else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(
        BASE_MODEL_ID,
        torch_dtype=dtype,
        safety_checker=None,
    )
    pipe.load_lora_weights(model_dir, weight_name=LORA_WEIGHT_NAME)
    pipe = pipe.to(DEVICE_TYPE)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def run_generation(request: GenerateRequest) -> GenerateResponse:
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if request.width * request.height * request.num_images > MAX_PIXELS * MAX_IMAGES:
        raise HTTPException(status_code=413, detail="Requested image batch is too large")

    prompt = get_prompt(request.position, request.class_name)
    generator = None
    if request.seed is not None:
        generator = torch.Generator(device=DEVICE_TYPE).manual_seed(request.seed)

    with torch.inference_mode():
        result = pipeline(
            prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            num_images_per_prompt=request.num_images,
            generator=generator,
        )

    return GenerateResponse(
        success=True,
        prompt=prompt,
        images=[encode_png(image, f"image_{index}.png") for index, image in enumerate(result.images)],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, pipeline_lock

    import asyncio

    logger.info("Loading image generation pipeline from %s", resolve_model_dir())
    pipeline = await run_in_threadpool(load_pipeline)
    pipeline_lock = asyncio.Lock()
    logger.info("Image generation pipeline loaded")
    yield


app = FastAPI(title="LoRA Image Generation Service", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"service": "LoRA Image Generation Service", "model_loaded": pipeline is not None}


@app.get("/health")
async def health():
    loaded = pipeline is not None
    return {
        "status": "healthy" if loaded else "model_not_loaded",
        "model_loaded": loaded,
        "model_type": "image_generation",
        "base_model": BASE_MODEL_ID,
        "device": DEVICE_TYPE,
        "model_dir": resolve_model_dir(),
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    async with pipeline_lock:
        return await run_in_threadpool(run_generation, request)


@app.post("/predict")
async def predict(request: PredictRequest):
    payload = {}
    if request.inputs:
        payload.update(request.inputs)
    payload.update(request.parameters)

    response = await generate(GenerateRequest(**payload))
    return {
        "success": True,
        "model_type": "image_generation",
        "result": response.model_dump(),
    }
