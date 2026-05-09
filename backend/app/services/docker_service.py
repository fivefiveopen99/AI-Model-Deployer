import os
import shutil
import subprocess
import json
import socket
from typing import Optional, Dict, Any, Callable
import asyncio
from datetime import datetime

from app.core.config import settings
from app.services.model_service_template import MODEL_SERVICE_TEMPLATE


PLATE_SERVICE_API = r'''import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from ultralytics import YOLO

from plate_recognition.double_plate_split_merge import get_split_merge
from plate_recognition.plate_rec import get_plate_result, init_model


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

detect_model = None
plate_rec_model = None
device = None

DETECT_MODEL_PATH = os.getenv("DETECT_MODEL", "weights/yolo26s-plate-detect.pt")
REC_MODEL_PATH = os.getenv("REC_MODEL", "weights/plate_rec_color.pth")
DEVICE_TYPE = os.getenv("DEVICE", "cpu")


class PredictRequest(BaseModel):
    image: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PlateResult(BaseModel):
    plate_no: str
    plate_color: str
    plate_type: str
    detect_conf: float
    color_conf: float
    bbox: List[int]
    landmarks: List[List[int]]


class RecognitionResponse(BaseModel):
    success: bool
    message: str
    count: int
    plates: List[PlateResult]
    processed_image: Optional[str] = None


def four_point_transform(image, pts):
    rect = pts.astype(np.float32)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b), 1)

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b), 1)

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def detect_and_recognize(img_ori, conf=0.3, iou=0.5):
    global detect_model, plate_rec_model, device

    if detect_model is None or plate_rec_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    result_list = []
    results = detect_model(img_ori, conf=conf, iou=iou, verbose=False)

    for result in results:
        boxes = result.boxes
        keypoints = result.keypoints
        if len(boxes) == 0 or keypoints is None:
            continue

        kpts_xy = keypoints.xy
        num_det = min(len(boxes), len(kpts_xy))
        for idx in range(num_det):
            box = boxes.xyxy[idx].cpu().numpy()
            det_conf = float(boxes.conf[idx])
            plate_type = int(boxes.cls[idx])

            landmarks = kpts_xy[idx].cpu().numpy().astype(np.int64)
            roi_img = four_point_transform(img_ori, landmarks)
            if plate_type == 1:
                roi_img = get_split_merge(roi_img)

            plate_number, _, plate_color, color_conf = get_plate_result(
                roi_img, device, plate_rec_model, is_color=True
            )

            result_list.append({
                "plate_no": plate_number,
                "plate_color": plate_color,
                "plate_type": "double" if plate_type == 1 else "single",
                "detect_conf": round(det_conf, 4),
                "color_conf": round(float(color_conf), 4),
                "bbox": [int(v) for v in box],
                "landmarks": landmarks.tolist(),
            })

    return result_list


def draw_results(image, results):
    img = image.copy()
    for i, r in enumerate(results, 1):
        x1, y1, x2, y2 = r["bbox"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        for j, (px, py) in enumerate(r["landmarks"]):
            color = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)][j]
            cv2.circle(img, (px, py), 5, color, -1)
        cv2.putText(img, f"{i}. {r['plate_no']} {r['plate_color']}", (x1, max(y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return img


@asynccontextmanager
async def lifespan(app: FastAPI):
    global detect_model, plate_rec_model, device

    logger.info("Loading plate models...")
    device = torch.device(DEVICE_TYPE)
    detect_model = YOLO(DETECT_MODEL_PATH)
    detect_model.to(device)
    detect_model.eval()

    plate_rec_model = init_model(device, REC_MODEL_PATH, is_color=True)
    plate_rec_model.eval()
    logger.info("Plate models loaded")
    yield


app = FastAPI(title="YOLO26 Plate Service", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"service": "YOLO26 Plate Service", "model_loaded": detect_model is not None and plate_rec_model is not None}


@app.get("/health")
async def health():
    loaded = detect_model is not None and plate_rec_model is not None
    return {
        "status": "healthy" if loaded else "model_not_loaded",
        "model_loaded": loaded,
        "model_type": "plate_detection",
        "device": str(device) if device else None,
    }


@app.post("/recognize", response_model=RecognitionResponse)
async def recognize_plate(
    file: UploadFile = File(...),
    conf: float = Form(0.3),
    iou: float = Form(0.5),
    return_image: bool = Form(False),
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    plates = detect_and_recognize(img, conf=conf, iou=iou)
    processed_image = None
    if return_image:
        drawn = draw_results(img, plates)
        ok, buffer = cv2.imencode(".jpg", drawn)
        if ok:
            processed_image = base64.b64encode(buffer).decode("utf-8")

    return RecognitionResponse(
        success=True,
        message=f"Detected {len(plates)} plate(s)",
        count=len(plates),
        plates=plates,
        processed_image=processed_image,
    )


@app.post("/recognize/base64", response_model=RecognitionResponse)
async def recognize_plate_base64(request: PredictRequest):
    if not request.image:
        raise HTTPException(status_code=400, detail="image is required")

    image_data = base64.b64decode(request.image)
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    conf = request.parameters.get("conf", 0.3)
    iou = request.parameters.get("iou", 0.5)
    plates = detect_and_recognize(img, conf=conf, iou=iou)
    return RecognitionResponse(success=True, message=f"Detected {len(plates)} plate(s)", count=len(plates), plates=plates)


@app.post("/predict")
async def predict(request: PredictRequest):
    response = await recognize_plate_base64(request)
    return {"result": response.model_dump(), "model_type": "plate_detection", "success": True}


@app.post("/predict/image")
async def predict_image(
    file: UploadFile = File(...),
    conf: float = Form(0.3),
    iou: float = Form(0.5),
):
    return await recognize_plate(file=file, conf=conf, iou=iou, return_image=False)
'''


RCAN_SERVICE_API = r'''import base64
import io
import logging
import os
import sys
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Dict, Optional

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

from src import model as rcan_model


model = None
device = None

WEIGHT_PATH = os.getenv("RCAN_WEIGHT", "experiment/RCAN/model/model_best.pth")
DEVICE_TYPE = os.getenv("DEVICE", "cpu")
SCALE = int(os.getenv("RCAN_SCALE", "4"))


class PredictRequest(BaseModel):
    image: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Args:
    n_resgroups = 10
    n_resblocks = 20
    n_feats = 64
    reduction = 16
    scale = SCALE
    n_colors = 3
    res_scale = 1
    shift_mean = True
    act = "relu"
    precision = "single"
    rgb_range = 255
    model = "RCAN"


def load_state_dict(path: str):
    try:
        return torch.load(path, map_location=device, weights_only=True)
    except Exception:
        return torch.load(path, map_location=device)


def run_super_resolution(img_bgr: np.ndarray, sharpen: bool = False) -> np.ndarray:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    img_tensor = torch.from_numpy(img_bgr.transpose((2, 0, 1))).float().unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(img_tensor).round()

    output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
    output = np.clip(output, 0, 255).astype(np.uint8)

    if sharpen:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        output = cv2.filter2D(output, -1, kernel)

    return output


def encode_png(img_bgr: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".png", img_bgr)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode output image")
    return base64.b64encode(buffer).decode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, device

    logger.info("Loading RCAN model...")
    device = torch.device(DEVICE_TYPE)
    model = rcan_model.RCAN(Args())
    state_dict = load_state_dict(WEIGHT_PATH)
    model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()
    logger.info("RCAN model loaded")
    yield


app = FastAPI(title="RCAN Super Resolution Service", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"service": "RCAN Super Resolution Service", "model_loaded": model is not None}


@app.get("/health")
async def health():
    loaded = model is not None
    return {
        "status": "healthy" if loaded else "model_not_loaded",
        "model_loaded": loaded,
        "model_type": "rcan",
        "scale": SCALE,
        "device": str(device) if device else None,
    }


@app.post("/predict/image")
async def predict_image(
    file: UploadFile = File(...),
    sharpen: bool = Form(False),
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    output = run_super_resolution(img, sharpen=sharpen)
    return {
        "success": True,
        "model_type": "rcan",
        "super_resolution_image": encode_png(output),
        "processed_image": encode_png(output),
        "original_size": {"width": img.shape[1], "height": img.shape[0]},
        "output_size": {"width": output.shape[1], "height": output.shape[0]},
        "scale": SCALE,
    }


@app.post("/predict")
async def predict(request: PredictRequest):
    if not request.image:
        raise HTTPException(status_code=400, detail="image is required")

    image_data = base64.b64decode(request.image)
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    output = run_super_resolution(img, sharpen=bool(request.parameters.get("sharpen", False)))
    return {
        "result": {
            "success": True,
            "super_resolution_image": encode_png(output),
            "processed_image": encode_png(output),
            "original_size": {"width": img.shape[1], "height": img.shape[0]},
            "output_size": {"width": output.shape[1], "height": output.shape[0]},
            "scale": SCALE,
        },
        "model_type": "rcan",
        "success": True,
    }
'''


REALESRGAN_SERVICE_API = r'''import base64
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import cv2
import numpy as np
from basicsr.archs.rrdbnet_arch import RRDBNet
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from realesrgan import RealESRGANer
from starlette.concurrency import run_in_threadpool


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upsampler = None
inference_lock = Lock()

MODEL_PATH = os.getenv("REALESRGAN_WEIGHT") or os.getenv("MODEL_PATH") or "experiments/RealESRGAN_x4plus.pth"
MODEL_NAME = os.getenv("REALESRGAN_MODEL_NAME", "RealESRGAN_x4plus")
DEVICE_TYPE = os.getenv("DEVICE", "cpu")
DEFAULT_OUTSCALE = float(os.getenv("REALESRGAN_OUTSCALE", "4"))
DEFAULT_TILE = int(os.getenv("REALESRGAN_TILE") or os.getenv("TILE") or "256")
GPU_ID = os.getenv("GPU_ID")
MAX_INPUT_PIXELS = int(os.getenv("MAX_INPUT_PIXELS", "4194304"))


class PredictRequest(BaseModel):
    image: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


def create_model():
    if MODEL_NAME == "RealESRGAN_x4plus":
        return RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4), 4
    raise RuntimeError(f"Unsupported Real-ESRGAN model: {MODEL_NAME}")


def encode_png(img_bgr: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".png", img_bgr)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode output image")
    return base64.b64encode(buffer).decode("utf-8")


def decode_image_bytes(contents: bytes) -> np.ndarray:
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    return img


def validate_input_size(img: np.ndarray):
    height, width = img.shape[:2]
    pixels = height * width
    if pixels > MAX_INPUT_PIXELS:
        max_megapixels = MAX_INPUT_PIXELS / 1_000_000
        actual_megapixels = pixels / 1_000_000
        raise HTTPException(
            status_code=413,
            detail=(
                f"Input image is too large for CPU Real-ESRGAN inference: "
                f"{width}x{height} ({actual_megapixels:.2f}MP). "
                f"Please use an image <= {max_megapixels:.2f}MP or deploy with GPU resources."
            ),
        )


def run_super_resolution(img: np.ndarray, outscale: float, tile: int) -> np.ndarray:
    global upsampler
    if upsampler is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        with inference_lock:
            upsampler.tile_size = tile
            output, _ = upsampler.enhance(img, outscale=outscale)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=f"Real-ESRGAN inference failed: {error}")

    return output


@asynccontextmanager
async def lifespan(app: FastAPI):
    global upsampler

    logger.info("Loading Real-ESRGAN model...")
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Weight file not found: {MODEL_PATH}")

    model, netscale = create_model()
    gpu_id = int(GPU_ID) if GPU_ID and DEVICE_TYPE.startswith("cuda") else None
    service_device = f"cuda:{gpu_id}" if gpu_id is not None else DEVICE_TYPE
    use_half = DEVICE_TYPE.startswith("cuda")
    upsampler = RealESRGANer(
        scale=netscale,
        model_path=MODEL_PATH,
        model=model,
        tile=DEFAULT_TILE,
        tile_pad=10,
        pre_pad=0,
        half=use_half,
        gpu_id=gpu_id,
        device=service_device,
    )
    logger.info("Real-ESRGAN model loaded")
    yield


app = FastAPI(title="Real-ESRGAN Super Resolution Service", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"service": "Real-ESRGAN Super Resolution Service", "model_loaded": upsampler is not None}


@app.get("/health")
async def health():
    loaded = upsampler is not None
    return {
        "status": "healthy" if loaded else "model_not_loaded",
        "model_loaded": loaded,
        "model_type": "realesrgan",
        "task": "image_super_resolution",
        "model_name": MODEL_NAME,
        "device": DEVICE_TYPE,
        "weight": MODEL_PATH,
        "tile": DEFAULT_TILE,
    }


@app.post("/predict/image")
async def predict_image(
    file: UploadFile = File(...),
    outscale: float = Form(DEFAULT_OUTSCALE),
    tile: int = Form(DEFAULT_TILE),
):
    contents = await file.read()
    img = decode_image_bytes(contents)
    validate_input_size(img)
    output = await run_in_threadpool(run_super_resolution, img, outscale, tile)
    return {
        "success": True,
        "model_type": "realesrgan",
        "task": "image_super_resolution",
        "super_resolution_image": encode_png(output),
        "processed_image": encode_png(output),
        "original_size": {"width": img.shape[1], "height": img.shape[0]},
        "output_size": {"width": output.shape[1], "height": output.shape[0]},
        "scale": outscale,
        "tile": tile,
    }


@app.post("/predict")
async def predict(request: PredictRequest):
    if not request.image:
        raise HTTPException(status_code=400, detail="image is required")

    image_data = base64.b64decode(request.image)
    img = decode_image_bytes(image_data)
    validate_input_size(img)
    outscale = float(request.parameters.get("outscale", DEFAULT_OUTSCALE))
    tile = int(request.parameters.get("tile", DEFAULT_TILE))
    output = await run_in_threadpool(run_super_resolution, img, outscale, tile)
    return {
        "result": {
            "success": True,
            "super_resolution_image": encode_png(output),
            "processed_image": encode_png(output),
            "original_size": {"width": img.shape[1], "height": img.shape[0]},
            "output_size": {"width": output.shape[1], "height": output.shape[0]},
            "scale": outscale,
            "tile": tile,
        },
        "model_type": "realesrgan",
        "success": True,
    }
'''


class DockerService:
    def __init__(self):
        self._connected = False
        self._docker_available = False
        self._check_docker()

    def detect_model_type(self, model_path: str) -> str:
        """自动检测模型类型"""
        if not os.path.exists(model_path):
            return "custom"

        # 查找所有文件
        all_files = []
        for root, dirs, files in os.walk(model_path):
            for file in files:
                all_files.append(file.lower())

        # 检测 YOLO/Ultralytics
        yolo_indicators = ['.pt', 'yolo', 'ultralytics']
        if any(ind in ' '.join(all_files) for ind in yolo_indicators):
            # 检查是否有 YOLO 相关代码
            for file in all_files:
                if 'yolo' in file or file.endswith('.pt'):
                    return "yolo"

        # 检测 Transformers/HuggingFace
        transformers_indicators = ['config.json', 'pytorch_model.bin', 'model.safetensors']
        if any(ind in all_files for ind in transformers_indicators):
            return "transformers"

        # 检测 TensorFlow
        tf_indicators = ['.pb', 'saved_model.pb', '.h5']
        if any(ind in ' '.join(all_files) for ind in tf_indicators):
            return "tensorflow"

        # 检测 ONNX
        if '.onnx' in ' '.join(all_files):
            return "onnx"

        # 检测 Scikit-Learn
        sklearn_indicators = ['.pkl', '.joblib', 'sklearn', 'pickle']
        if any(ind in ' '.join(all_files) for ind in sklearn_indicators):
            return "sklearn"

        # 检测 PyTorch
        pytorch_indicators = ['.pth', '.pt', 'torch']
        if any(ind in ' '.join(all_files) for ind in pytorch_indicators):
            return "pytorch"

        return "custom"

    def _check_docker(self):
        """检查 Docker 是否可用（通过命令行）"""
        try:
            result = subprocess.run(
                ['docker', 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._docker_available = True
                self._connected = True
                print("Docker is available via command line")
            else:
                print(f"Docker check failed: {result.stderr}")
                self._connected = False
        except Exception as e:
            print(f"Docker not available: {e}")
            self._connected = False

    @property
    def is_connected(self) -> bool:
        if not self._docker_available:
            return False
        try:
            result = subprocess.run(
                ['docker', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    async def build_model_image(
        self,
        model_id: int,
        model_name: str,
        model_type: str,
        source_path: str,
        source_type: str,
        base_image: str = "python:3.11-slim",
        config: Dict[str, Any] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Docker is not connected")

        config = config or {}
        runtime_spec = config.get("runtime_spec") or {}
        custom_dockerfile = runtime_spec.get("dockerfile_content")
        build_id = f"{model_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        image_tag = f"ai-model:{build_id}"

        # 创建构建上下文目录
        build_context = os.path.join(settings.BUILD_CONTEXT_PATH, build_id)
        os.makedirs(build_context, exist_ok=True)

        try:
            if progress_callback:
                await progress_callback(10, "Preparing build context...")

            if custom_dockerfile:
                if progress_callback:
                    await progress_callback(20, "Preparing user-provided Dockerfile build context...")

                if source_path and os.path.exists(source_path):
                    await self._prepare_model_files(source_path, source_type, build_context, progress_callback)

                self._write_text(os.path.join(build_context, "Dockerfile"), custom_dockerfile)

                if progress_callback:
                    await progress_callback(35, "Using user-provided Dockerfile directly...")
            else:
                # 准备模型文件
                model_dir = os.path.join(build_context, "model")
                os.makedirs(model_dir, exist_ok=True)

                await self._prepare_model_files(source_path, source_type, model_dir, progress_callback)

                # 自动检测模型类型
                if progress_callback:
                    await progress_callback(20, "Detecting model type...")

                detected_type = self.detect_model_type(model_dir)
                if detected_type != "custom":
                    model_type = detected_type
                    if progress_callback:
                        await progress_callback(25, f"Detected model type: {model_type}")

                adapter = self._select_build_adapter(model_dir, base_image, config)

                if adapter:
                    if progress_callback:
                        await progress_callback(30, adapter["message"])

                    self._copy_project_to_context(adapter["project_dir"], build_context)
                    if adapter.get("api"):
                        self._write_text(os.path.join(build_context, "api.py"), adapter["api"])
                    if adapter.get("dockerfile"):
                        self._write_text(os.path.join(build_context, "Dockerfile"), adapter["dockerfile"])

                    shutil.rmtree(model_dir, ignore_errors=True)
                else:
                    # 使用自动生成的简单结构
                    if progress_callback:
                        await progress_callback(30, "Generating Dockerfile...")

                    # 生成Dockerfile
                    dockerfile_content = self._generate_dockerfile(model_type, base_image, config)
                    with open(os.path.join(build_context, "Dockerfile"), "w") as f:
                        f.write(dockerfile_content)

                    # 生成模型服务代码
                    if progress_callback:
                        await progress_callback(40, "Generating model service...")

                    service_code = self._generate_model_service(model_type, config)
                    with open(os.path.join(build_context, "model_service.py"), "w") as f:
                        f.write(service_code)

                    # 生成requirements.txt
                    requirements = self._generate_requirements(model_type, config)
                    with open(os.path.join(build_context, "requirements.txt"), "w") as f:
                        f.write(requirements)

            if progress_callback:
                await progress_callback(50, "Building Docker image...")

            # 使用异步命令行构建镜像
            await self._build_image_cmd_async(build_context, image_tag, progress_callback)

            if progress_callback:
                await progress_callback(90, "Finalizing...")

            # 获取镜像信息
            image_info = await self._get_image_info_async(image_tag)

            if progress_callback:
                await progress_callback(100, "Build completed")

            return {
                "success": True,
                "image_tag": image_tag,
                "image_id": image_info.get("Id", ""),
                "size": image_info.get("Size", 0),
                "build_context": build_id
            }

        finally:
            # 构建上下文只用于 docker build；镜像创建完成后可以安全删除。
            shutil.rmtree(build_context, ignore_errors=True)

    async def _build_image_cmd_async(self, build_context: str, tag: str, progress_callback=None):
        """使用命令行异步构建镜像，支持进度回调"""
        import asyncio

        # 使用 legacy builder 以兼容没有 buildx 组件的 Docker 环境。
        env = os.environ.copy()
        env['DOCKER_BUILDKIT'] = '0'
        
        process = await asyncio.create_subprocess_exec(
            'docker', 'build', '-t', tag, build_context,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        # 读取输出并发送进度
        step = 0
        error_lines = []
        
        async def read_stream(stream, is_stderr=False):
            nonlocal step
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str:
                    print(f"Docker build: {line_str}")
                    if is_stderr:
                        error_lines.append(line_str)
                    step += 1
                    if progress_callback:
                        progress = min(50 + step, 85)
                        await progress_callback(
                            progress,
                            line_str,
                            {"log": line_str, "stream": "stderr" if is_stderr else "stdout"},
                            persist_status=False
                        )
                    # 每10行输出更新一次进度 (50% -> 85%)
                    if progress_callback and step % 10 == 0:
                        progress = min(50 + step, 85)
                        await progress_callback(progress, f"Building Docker image... ({step} steps)")

        # 同时读取 stdout 和 stderr
        await asyncio.gather(
            read_stream(process.stdout, is_stderr=False),
            read_stream(process.stderr, is_stderr=True)
        )

        # 等待进程完成
        await process.wait()

        if process.returncode != 0:
            error_msg = "\n".join(error_lines[-10:]) if error_lines else "Docker build failed"
            raise Exception(f"Docker build failed: {error_msg}")

        print(f"Docker build completed successfully")
        return "Build completed"

    def _get_image_info_cmd(self, image_tag: str) -> Dict:
        """使用命令行获取镜像信息"""
        result = subprocess.run(
            ['docker', 'inspect', image_tag],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            if info:
                return {
                    "Id": info[0].get("Id", ""),
                    "Size": info[0].get("Size", 0)
                }
        return {"Id": "", "Size": 0}

    async def _get_image_info_async(self, image_tag: str) -> Dict:
        """异步获取镜像信息"""
        import asyncio
        process = await asyncio.create_subprocess_exec(
            'docker', 'inspect', image_tag,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            try:
                info = json.loads(stdout.decode('utf-8'))
                if info:
                    return {
                        "Id": info[0].get("Id", ""),
                        "Size": info[0].get("Size", 0)
                    }
            except:
                pass
        return {"Id": "", "Size": 0}

    async def push_image_to_registry(self, image_tag: str, progress_callback=None) -> Dict[str, Any]:
        """Tag and push a built image to the configured Docker registry."""
        registry_url = settings.DOCKER_REGISTRY_URL.rstrip("/")
        push_registry_url = (settings.DOCKER_REGISTRY_PUSH_URL or settings.DOCKER_REGISTRY_URL).rstrip("/")
        if not registry_url:
            raise Exception("DOCKER_REGISTRY_URL is not configured")

        if ":" not in image_tag:
            raise Exception(f"Invalid image tag: {image_tag}")

        image_name, tag = image_tag.rsplit(":", 1)
        registry_image = f"{registry_url}/{image_name}:{tag}"
        push_image = f"{push_registry_url}/{image_name}:{tag}"
        registry_host = push_registry_url.split("/", 1)[0]

        if progress_callback:
            await progress_callback(88, f"Logging in to registry {registry_host}...")

        self._ensure_registry_host_resolves(registry_host)

        if settings.DOCKER_REGISTRY_USERNAME and settings.DOCKER_REGISTRY_PASSWORD:
            await self._docker_login_async(
                registry_host,
                settings.DOCKER_REGISTRY_USERNAME,
                settings.DOCKER_REGISTRY_PASSWORD
            )

        if progress_callback:
            await progress_callback(90, f"Tagging image as {push_image}...")

        await self._run_docker_command_async(
            ["docker", "tag", image_tag, push_image],
            "Docker tag failed"
        )

        if progress_callback:
            await progress_callback(92, f"Pushing image to {push_registry_url}...")

        await self._run_docker_command_async(
            ["docker", "push", push_image],
            "Docker push failed",
            progress_callback=progress_callback,
            progress_start=92,
            progress_end=98
        )

        return {
            "success": True,
            "registry": registry_url,
            "push_registry": push_registry_url,
            "registry_host": registry_host,
            "source_image": image_tag,
            "push_image": push_image,
            "registry_image": registry_image
        }

    def _ensure_registry_host_resolves(self, registry_host: str):
        host = registry_host.split(":", 1)[0]
        try:
            socket.gethostbyname(host)
        except socket.gaierror as e:
            raise Exception(
                f"Registry host {host} cannot be resolved. "
                "Set DOCKER_REGISTRY_URL to a reachable registry address or configure DNS/hosts, "
                "then recreate the backend container."
            ) from e

    async def _docker_login_async(self, registry_host: str, username: str, password: str):
        process = await asyncio.create_subprocess_exec(
            "docker", "login", registry_host, "-u", username, "--password-stdin",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(f"{password}\n".encode("utf-8"))

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode("utf-8", errors="ignore")
            raise Exception(f"Docker login failed for {registry_host}: {error_msg.strip()}")

    async def _run_docker_command_async(
        self,
        command: list,
        error_prefix: str,
        progress_callback=None,
        progress_start: int = 0,
        progress_end: int = 100
    ):
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        output_lines = []
        line_count = 0

        async def read_stream(stream):
            nonlocal line_count
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="ignore").strip()
                if not line_str:
                    continue
                print(f"Docker command: {line_str}")
                output_lines.append(line_str)
                line_count += 1
                if progress_callback:
                    progress = min(progress_start + line_count, progress_end)
                    await progress_callback(
                        progress,
                        line_str,
                        {"log": line_str},
                        persist_status=line_count % 5 == 0
                    )

        await asyncio.gather(read_stream(process.stdout), read_stream(process.stderr))
        await process.wait()

        if process.returncode != 0:
            error_msg = "\n".join(output_lines[-10:]) if output_lines else "Unknown error"
            raise Exception(f"{error_prefix}: {error_msg}")

    async def _prepare_model_files(
        self,
        source_path: str,
        source_type: str,
        target_dir: str,
        progress_callback: Optional[Callable] = None
    ):
        # 转换相对路径为绝对路径
        if not os.path.isabs(source_path):
            source_path = os.path.abspath(source_path)

        if source_type == "file" or source_type == "url":
            # 本地文件或目录（GitHub 克隆的模型也是本地目录）
            if os.path.isdir(source_path):
                shutil.copytree(source_path, target_dir, dirs_exist_ok=True)
            elif os.path.isfile(source_path):
                shutil.copy2(source_path, target_dir)
            else:
                raise Exception(f"Source path does not exist: {source_path}")
        elif source_type == "download_url":
            # 下载文件（真正的 URL 下载）
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(source_path, follow_redirects=True)
                response.raise_for_status()
                filename = os.path.basename(source_path) or "model.bin"
                with open(os.path.join(target_dir, filename), "wb") as f:
                    f.write(response.content)
        elif source_type == "huggingface":
            # 使用huggingface_hub下载
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=source_path, local_dir=target_dir)

    def _generate_dockerfile(self, model_type: str, base_image: str, config: Dict[str, Any]) -> str:
        port = config.get("port", 8000)

        # 根据模型类型确定需要的系统依赖
        system_deps = "gcc g++"
        if model_type in ["yolo", "ultralytics", "pytorch", "rcan"]:
            # OpenCV 需要 libGL 等库
            system_deps += " libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1"

        return f"""FROM {base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    {system_deps} \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model files
COPY model/ /app/model/

# Copy service code
COPY model_service.py .

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

# Run service
CMD ["python", "model_service.py"]
"""

    def _write_text(self, path: str, content: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _copy_project_to_context(self, project_dir: str, build_context: str):
        for item in os.listdir(project_dir):
            src = os.path.join(project_dir, item)
            dst = os.path.join(build_context, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    def _find_provided_project_dir(self, model_dir: str) -> Optional[str]:
        """Find a user-supplied FastAPI project that already has api.py and Dockerfile."""
        has_api_py = os.path.exists(os.path.join(model_dir, "api.py"))
        has_dockerfile = os.path.exists(os.path.join(model_dir, "Dockerfile"))
        api_py_path = os.path.join(model_dir, "api.py") if has_api_py else None
        dockerfile_path = os.path.join(model_dir, "Dockerfile") if has_dockerfile else None

        if not has_api_py or not has_dockerfile:
            for root, dirs, files in os.walk(model_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                if not has_api_py and "api.py" in files:
                    api_py_path = os.path.join(root, "api.py")
                    has_api_py = True

                if not has_dockerfile and "Dockerfile" in files:
                    dockerfile_path = os.path.join(root, "Dockerfile")
                    has_dockerfile = True

                if has_api_py and has_dockerfile:
                    break

        if not (has_api_py and has_dockerfile):
            return None

        api_py_dir = os.path.dirname(api_py_path)
        dockerfile_dir = os.path.dirname(dockerfile_path)
        if api_py_dir == dockerfile_dir:
            return api_py_dir
        return model_dir

    def _select_build_adapter(self, model_dir: str, base_image: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the first matching build adapter.

        The order matters: user-provided FastAPI projects win, then known
        project adapters, then the generic generated service handles leftovers.
        """
        provided_project_dir = self._find_provided_project_dir(model_dir)
        if provided_project_dir:
            return {
                "name": "provided_fastapi_project",
                "project_dir": provided_project_dir,
                "message": "Using provided FastAPI project structure...",
            }

        plate_project_dir = self._find_plate_project_dir(model_dir)
        if plate_project_dir:
            return {
                "name": "yolo_plate",
                "project_dir": plate_project_dir,
                "message": "Detected YOLO plate project, generating FastAPI service wrapper...",
                "api": PLATE_SERVICE_API,
                "dockerfile": self._generate_plate_dockerfile(base_image, config),
            }

        rcan_project_dir = self._find_rcan_project_dir(model_dir)
        if rcan_project_dir:
            self._validate_rcan_project(rcan_project_dir)
            return {
                "name": "rcan",
                "project_dir": rcan_project_dir,
                "message": "Detected RCAN project, generating FastAPI service wrapper...",
                "api": RCAN_SERVICE_API,
                "dockerfile": self._generate_rcan_dockerfile(base_image, config),
            }

        realesrgan_project_dir = self._find_realesrgan_project_dir(model_dir)
        if realesrgan_project_dir:
            self._validate_realesrgan_project(realesrgan_project_dir)
            return {
                "name": "realesrgan",
                "project_dir": realesrgan_project_dir,
                "message": "Detected Real-ESRGAN project, generating FastAPI service wrapper...",
                "api": REALESRGAN_SERVICE_API,
                "dockerfile": self._generate_realesrgan_dockerfile(base_image, config),
            }

        return None

    def _find_plate_project_dir(self, model_dir: str) -> Optional[str]:
        """Find an uploaded YOLO plate project even when api.py/Dockerfile are absent."""
        for root, dirs, files in os.walk(model_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            has_plate_code = "plate_recognition" in dirs
            has_ultralytics_source = "ultralytics" in dirs
            has_pyproject = "pyproject.toml" in files
            weights_dir = os.path.join(root, "weights")
            has_weights = (
                os.path.isdir(weights_dir)
                and any(name.endswith(".pt") for name in os.listdir(weights_dir))
                and any(name.endswith(".pth") for name in os.listdir(weights_dir))
            )

            if has_plate_code and has_ultralytics_source and has_pyproject and has_weights:
                return root

        return None

    def _find_rcan_project_dir(self, model_dir: str) -> Optional[str]:
        """Find an uploaded RCAN super-resolution project inside extracted archives."""
        for root, dirs, files in os.walk(model_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            has_src_model = os.path.exists(os.path.join(root, "src", "model", "rcan.py"))
            has_weight = os.path.exists(os.path.join(root, "experiment", "RCAN", "model", "model_best.pth"))
            has_requirements = "requirements.txt" in files

            if has_src_model and has_weight and has_requirements:
                return root

        return None

    def _find_realesrgan_project_dir(self, model_dir: str) -> Optional[str]:
        """Find a Real-ESRGAN super-resolution project inside uploaded archives."""
        for root, dirs, files in os.walk(model_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            has_package = "realesrgan" in dirs
            has_inference = "inference_realesrgan.py" in files
            has_setup = "setup.py" in files
            has_weight = os.path.exists(os.path.join(root, "experiments", "RealESRGAN_x4plus.pth")) or os.path.exists(
                os.path.join(root, "weights", "RealESRGAN_x4plus.pth")
            )

            if has_package and has_inference and has_setup and has_weight:
                return root

        return None

    def _validate_rcan_project(self, project_dir: str):
        weight_path = os.path.join(project_dir, "experiment", "RCAN", "model", "model_best.pth")
        if not os.path.exists(weight_path):
            raise Exception("RCAN weight file not found: experiment/RCAN/model/model_best.pth")

        if os.path.getsize(weight_path) < 1024:
            with open(weight_path, "rb") as f:
                header = f.read(256)
            if header.startswith(b"version https://git-lfs.github.com/spec"):
                raise Exception(
                    "RCAN weight file is a Git LFS pointer, not the real model weights. "
                    "Please upload the archive after running `git lfs pull`, so "
                    "experiment/RCAN/model/model_best.pth contains the actual .pth file."
                )

    def _validate_realesrgan_project(self, project_dir: str):
        candidates = [
            os.path.join(project_dir, "experiments", "RealESRGAN_x4plus.pth"),
            os.path.join(project_dir, "weights", "RealESRGAN_x4plus.pth"),
        ]
        weight_path = next((path for path in candidates if os.path.exists(path)), None)
        if not weight_path:
            raise Exception("Real-ESRGAN weight file not found: experiments/RealESRGAN_x4plus.pth")

        if os.path.getsize(weight_path) < 1024:
            with open(weight_path, "rb") as f:
                header = f.read(256)
            if header.startswith(b"version https://git-lfs.github.com/spec"):
                raise Exception(
                    "Real-ESRGAN weight file is a Git LFS pointer, not the real model weights. "
                    "Please upload the archive after running `git lfs pull`, so "
                    "experiments/RealESRGAN_x4plus.pth contains the actual .pth file."
                )

    def _generate_plate_dockerfile(self, base_image: str, config: Dict[str, Any]) -> str:
        port = config.get("port", 8000)
        plate_base_image = config.get("plate_base_image")
        if not plate_base_image:
            if base_image and base_image != "python:3.11-slim":
                plate_base_image = base_image
            else:
                plate_base_image = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"

        return f"""FROM {plate_base_image}

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_BREAK_SYSTEM_PACKAGES=1 \\
    MKL_THREADING_LAYER=GNU \\
    OMP_NUM_THREADS=1 \\
    TF_CPP_MIN_LOG_LEVEL=3 \\
    TORCH_CPP_LOG_LEVEL=ERROR \\
    DEVICE=cpu \\
    PORT={port}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    git \\
    curl \\
    libgl1 \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender1 \\
    libgomp1 \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python -m pip install --upgrade pip && \\
    pip install --no-cache-dir \\
        fastapi==0.104.1 \\
        "uvicorn[standard]==0.24.0" \\
        python-multipart==0.0.6 \\
        "opencv-python-headless>=4.8.0" \\
        "numpy>=1.23.0" \\
        "pillow>=7.1.2" \\
        "pyyaml>=5.3.1" \\
        "requests>=2.23.0" \\
        "scipy>=1.4.1" \\
        "psutil>=5.8.0" \\
        "polars>=0.20.0" \\
        "ultralytics-thop>=2.0.18" \\
        "onnxruntime>=1.17,<1.20" \\
        "onnx>=1.17.0,<1.18.0" && \\
    pip install --no-cache-dir -e .

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

    def _generate_rcan_dockerfile(self, base_image: str, config: Dict[str, Any]) -> str:
        port = config.get("port", 8000)
        rcan_base_image = config.get("rcan_base_image")
        if not rcan_base_image:
            if base_image and base_image != "python:3.11-slim":
                rcan_base_image = base_image
            else:
                rcan_base_image = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"

        return f"""FROM {rcan_base_image}

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_BREAK_SYSTEM_PACKAGES=1 \\
    OMP_NUM_THREADS=1 \\
    DEVICE=cpu \\
    PORT={port}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    curl \\
    libgl1 \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender1 \\
    libgomp1 \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python -m pip install --upgrade pip && \\
    pip install --no-cache-dir \\
        fastapi==0.104.1 \\
        "uvicorn[standard]==0.24.0" \\
        python-multipart==0.0.6 \\
        "opencv-python-headless>=4.8.0" \\
        "numpy>=1.23.0" \\
        "pillow>=7.1.2" \\
        "tqdm>=4.60.0"

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

    def _generate_realesrgan_dockerfile(self, base_image: str, config: Dict[str, Any]) -> str:
        port = config.get("port", 8000)
        realesrgan_base_image = config.get("realesrgan_base_image")
        if not realesrgan_base_image:
            if base_image and base_image != "python:3.11-slim":
                realesrgan_base_image = base_image
            else:
                realesrgan_base_image = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"

        return f"""FROM {realesrgan_base_image}

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_BREAK_SYSTEM_PACKAGES=1 \\
    OMP_NUM_THREADS=1 \\
    DEVICE=cpu \\
    REALESRGAN_TILE=256 \\
    MAX_INPUT_PIXELS=4194304 \\
    PORT={port}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    curl \\
    libgl1 \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender1 \\
    libgomp1 \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python -m pip install --upgrade pip && \\
    pip install --no-cache-dir \\
        fastapi==0.104.1 \\
        "uvicorn[standard]==0.24.0" \\
        python-multipart==0.0.6 \\
        "opencv-python-headless>=4.8.0" \\
        "numpy>=1.23.0" \\
        "pillow>=7.1.2" \\
        "tqdm>=4.60.0" \\
        "torchvision==0.20.1" \\
        "basicsr==1.4.2" \\
        "facexlib>=0.2.5" \\
        "gfpgan>=1.3.5"

RUN pip install --no-cache-dir --no-deps -e . && \\
    mkdir -p weights && \\
    if [ -f experiments/RealESRGAN_x4plus.pth ] && [ ! -f weights/RealESRGAN_x4plus.pth ]; then \\
        cp experiments/RealESRGAN_x4plus.pth weights/RealESRGAN_x4plus.pth; \\
    fi

RUN find /opt/conda /usr/local -path '*/site-packages/basicsr/data/degradations.py' \\
    -exec sed -i 's/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/g' {{}} \\;

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

    def _generate_model_service(self, model_type: str, config: Dict[str, Any]) -> str:
        port = config.get("port", 8000)

        # 从模板文件加载
        return MODEL_SERVICE_TEMPLATE % {
            'model_type': model_type,
            'port': port
        }

    def _generate_requirements(self, model_type: str, config: Dict[str, Any] = None) -> str:
        """生成 requirements.txt，根据模型类型添加依赖"""
        config = config or {}

        # 基础依赖
        base_requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
numpy==1.24.3
pillow==10.1.0
"""

        # 根据模型类型添加依赖
        if model_type in ["yolo", "ultralytics"]:
            base_requirements += """torch==2.1.0
torchvision==0.16.0
ultralytics==8.3.0
opencv-python==4.8.1.78
"""
        elif model_type in ["transformers", "huggingface", "bert", "llama", "gpt"]:
            base_requirements += """torch==2.1.0
transformers==4.35.0
accelerate==0.24.0
sentencepiece==0.1.99
"""
        elif model_type == "pytorch":
            base_requirements += """torch==2.1.0
torchvision==0.16.0
opencv-python==4.8.1.78
"""
        elif model_type == "tensorflow":
            base_requirements += """tensorflow==2.14.0
"""
        elif model_type == "sklearn":
            base_requirements += """scikit-learn==1.3.2
joblib==1.3.2
"""
        elif model_type == "onnx":
            base_requirements += """onnx==1.15.0
onnxruntime==1.16.3
"""
        else:
            # 通用模型，包含常用依赖
            base_requirements += """torch==2.1.0
torchvision==0.16.0
transformers==4.35.0
ultralytics==8.3.0
opencv-python==4.8.1.78
scikit-learn==1.3.2
joblib==1.3.2
"""

        # 从配置中添加额外依赖
        extra_deps = config.get("extra_dependencies", [])
        for dep in extra_deps:
            base_requirements += f"{dep}\n"

        return base_requirements

    def remove_image(self, image_tag: str) -> bool:
        if not self.is_connected:
            return False

        try:
            result = subprocess.run(
                ['docker', 'rmi', '-f', image_tag],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False


docker_service = DockerService()
