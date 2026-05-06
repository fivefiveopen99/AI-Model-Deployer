"""
模型服务代码模板
这个文件包含模型服务的代码模板，使用 %% 占位符来替换变量
"""

MODEL_SERVICE_TEMPLATE = '''import os
import sys
import json
import importlib.util
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
import uvicorn
import numpy as np
from PIL import Image
import io
import base64

app = FastAPI(title="AI Model Service", version="1.0.0")

# Global model instance and info
model = None
model_info = {
    "type": "%(model_type)s",
    "loaded": False,
    "path": "/app/model"
}

class PredictRequest(BaseModel):
    """通用预测请求"""
    text: Optional[str] = None
    image: Optional[str] = None  # base64 encoded image
    inputs: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PredictResponse(BaseModel):
    """通用预测响应"""
    result: Any
    model_type: str = "%(model_type)s"
    success: bool = True

class ModelInfo(BaseModel):
    """模型信息"""
    type: str
    loaded: bool
    path: str
    available_files: List[str] = []


def discover_model_files(model_path: str) -> Dict[str, List[str]]:
    """自动发现模型文件"""
    files = {
        'weights': [],
        'code': [],
        'config': [],
        'other': []
    }

    for root, dirs, filenames in os.walk(model_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, model_path)

            # 权重文件
            if filename.endswith(('.pt', '.pth', '.onnx', '.engine', '.weights', '.h5', '.pb', '.tflite')):
                files['weights'].append(rel_path)
            # Python代码
            elif filename.endswith('.py'):
                files['code'].append(rel_path)
            # 配置文件
            elif filename.endswith(('.yaml', '.yml', '.json', '.cfg')):
                files['config'].append(rel_path)
            else:
                files['other'].append(rel_path)

    return files


def four_point_transform(image, pts):
    """透视变换，将四边形区域转换为矩形"""
    import cv2
    import numpy as np

    rect = pts.astype(np.float32)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def load_model_from_code(model_path: str):
    """尝试从代码中加载模型"""
    # 查找常见的模型加载文件
    load_files = ['model.py', 'inference.py', 'predict.py', 'detect.py', 'run.py']

    for load_file in load_files:
        filepath = os.path.join(model_path, load_file)
        if os.path.exists(filepath):
            try:
                spec = importlib.util.spec_from_file_location("model_module", filepath)
                module = importlib.util.module_from_spec(spec)
                sys.modules["model_module"] = module
                spec.loader.exec_module(module)

                # 尝试查找模型类或函数
                if hasattr(module, 'load_model'):
                    return module.load_model(model_path)
                elif hasattr(module, 'model'):
                    return module.model
                elif hasattr(module, 'Model'):
                    return module.Model()
            except Exception as e:
                print(f"Failed to load from {load_file}: {e}")
                continue

    return None


@app.on_event("startup")
async def load_model():
    """启动时加载模型"""
    global model, model_info

    model_path = model_info["path"]

    if not os.path.exists(model_path):
        print(f"Model path does not exist: {model_path}")
        return

    # 发现模型文件
    files = discover_model_files(model_path)
    model_info["files"] = files

    print(f"Discovered files: {json.dumps(files, indent=2)}")

    try:
        # 根据模型类型加载
        model_type = "%(model_type)s"

        if model_type == "yolo" or model_type == "ultralytics":
            from ultralytics import YOLO
            import torch
            # 查找权重文件
            weight_files = files.get('weights', [])

            # 检查是否是车牌检测项目（通过检查是否有 plate_recognition 目录）
            # 递归查找 plate_recognition 目录（因为模型可能在子目录中）
            is_plate_project = False
            plate_recognition_path = None
            for root, dirs, files in os.walk(model_path):
                if 'plate_recognition' in dirs:
                    is_plate_project = True
                    plate_recognition_path = root
                    break

            if is_plate_project:
                # 车牌检测+识别项目
                print("Detected plate detection project")
                import sys
                # 使用实际找到的项目路径
                if plate_recognition_path and plate_recognition_path != model_path:
                    print(f"Using project path: {plate_recognition_path}")
                    sys.path.insert(0, plate_recognition_path)
                sys.path.insert(0, model_path)

                # 查找检测模型 (.pt 文件)
                # 使用实际的项目路径（可能在子目录中）
                actual_model_path = plate_recognition_path if plate_recognition_path else model_path
                detect_weight = None
                rec_weight = None
                for wf in weight_files:
                    if wf.endswith('.pt'):
                        detect_weight = os.path.join(model_path, wf)
                        # 如果文件不存在，尝试在项目路径下查找
                        if not os.path.exists(detect_weight) and plate_recognition_path:
                            detect_weight = os.path.join(plate_recognition_path, wf)
                    elif wf.endswith('.pth'):
                        rec_weight = os.path.join(model_path, wf)
                        # 如果文件不存在，尝试在项目路径下查找
                        if not os.path.exists(rec_weight) and plate_recognition_path:
                            rec_weight = os.path.join(plate_recognition_path, wf)

                # 加载检测模型
                if detect_weight:
                    detect_model = YOLO(detect_weight)
                    print(f"Loaded detection model from {detect_weight}")
                else:
                    raise Exception("No detection model (.pt) found")

                # 加载识别模型
                if rec_weight:
                    from plate_recognition.plate_rec import init_model
                    rec_model = init_model('cpu', rec_weight, is_color=True)
                    print(f"Loaded recognition model from {rec_weight}")
                else:
                    rec_model = None
                    print("Warning: No recognition model (.pth) found")

                # 组合模型
                model = {
                    "detect_model": detect_model,
                    "rec_model": rec_model,
                    "is_plate": True
                }
                model_info["type"] = "plate_detection"

            elif weight_files:
                # 优先查找 .pt 文件，如果没有则使用 .pth 或其他权重文件
                pt_files = [f for f in weight_files if f.endswith('.pt')]
                pth_files = [f for f in weight_files if f.endswith('.pth')]
                
                if pt_files:
                    weight_path = os.path.join(model_path, pt_files[0])
                elif pth_files:
                    weight_path = os.path.join(model_path, pth_files[0])
                else:
                    weight_path = os.path.join(model_path, weight_files[0])
                
                print(f"Loading YOLO model from {weight_path}")
                print(f"Weight files found: {weight_files}")
                
                try:
                    model = YOLO(weight_path)
                    print(f"Loaded YOLO model successfully")
                except Exception as e:
                    print(f"Failed to load with YOLO: {e}")
                    # 尝试用 torch 直接加载
                    import torch
                    model = torch.load(weight_path, map_location='cpu')
                    print(f"Loaded model with torch instead")
            else:
                print("Warning: No weight files found, using default yolov8n.pt")
                model = YOLO('yolov8n.pt')  # 默认模型

        elif model_type == "transformers" or model_type == "huggingface":
            from transformers import AutoModel, AutoTokenizer
            model = AutoModel.from_pretrained(model_path)
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = {"model": model, "tokenizer": tokenizer}

        elif model_type == "sklearn":
            import joblib
            weight_files = [f for f in files.get('weights', []) if f.endswith('.pkl') or f.endswith('.joblib')]
            if weight_files:
                model = joblib.load(os.path.join(model_path, weight_files[0]))
            else:
                # 尝试从代码加载
                model = load_model_from_code(model_path)

        elif model_type == "pytorch":
            import torch
            weight_files = [f for f in files.get('weights', []) if f.endswith('.pt') or f.endswith('.pth')]
            if weight_files:
                # 检查是否是 RCAN 模型（通过检查 src/model/rcan.py 或 src/model/enhance_rcan.py）
                rcan_files = ['src/model/rcan.py', 'src/model/enhance_rcan.py', 'model/rcan.py']
                is_rcan = any(os.path.exists(os.path.join(model_path, f)) for f in rcan_files)

                if is_rcan:
                    # RCAN 模型特殊加载
                    print("Detected RCAN model, using custom loading logic")
                    import sys
                    sys.path.insert(0, model_path)

                    # 导入 RCAN 模型类
                    try:
                        from src.model.rcan import RCAN
                    except:
                        from model.rcan import RCAN

                    # 创建默认参数
                    class Args:
                        n_resgroups = 10
                        n_resblocks = 20
                        n_feats = 64
                        reduction = 16
                        scale = [4]
                        n_colors = 3
                        res_scale = 1
                        shift_mean = True
                        act = 'relu'
                        precision = 'single'
                        rgb_range = 255
                        model = 'RCAN'

                    args = Args()
                    model_instance = RCAN(args)

                    # 加载权重
                    weight_path = os.path.join(model_path, weight_files[0])
                    state_dict = torch.load(weight_path, map_location='cpu', weights_only=True)
                    model_instance.load_state_dict(state_dict)
                    model_instance.eval()

                    model = model_instance
                    model_info["type"] = "rcan"
                    print(f"Loaded RCAN model from {weight_path}")
                else:
                    # 普通 PyTorch 模型
                    model = torch.load(os.path.join(model_path, weight_files[0]), map_location='cpu')
            else:
                model = load_model_from_code(model_path)

        elif model_type == "tensorflow":
            import tensorflow as tf
            model = tf.keras.models.load_model(model_path)

        else:
            # 通用加载：尝试从代码加载
            model = load_model_from_code(model_path)

            # 如果失败，尝试加载权重文件
            if model is None:
                import pickle
                weight_files = [f for f in files.get('weights', []) if f.endswith('.pkl') or f.endswith('.bin')]
                if weight_files:
                    with open(os.path.join(model_path, weight_files[0]), 'rb') as f:
                        model = pickle.load(f)

        model_info["loaded"] = model is not None

        if model_info["loaded"]:
            print(f"Model loaded successfully from {model_path}")
        else:
            print(f"Warning: Could not load model from {model_path}")
            print("The model files are present but automatic loading failed.")
            print("You may need to customize the model loading logic.")

    except Exception as e:
        print(f"Error loading model: {e}")
        import traceback
        traceback.print_exc()
        # 记录详细的错误信息到 model_info
        model_info["load_error"] = str(e)
        model_info["traceback"] = traceback.format_exc()


@app.get("/health")
async def health():
    """健康检查"""
    response = {
        "status": "healthy" if model_info["loaded"] else "model_not_loaded",
        "model_loaded": model_info["loaded"],
        "model_type": model_info["type"],
        "model_path": model_info.get("path"),
        "files_discovered": model_info.get("files", {})
    }
    
    # 如果加载失败，返回错误信息
    if not model_info["loaded"]:
        if "load_error" in model_info:
            response["error"] = model_info["load_error"]
        if "traceback" in model_info:
            response["traceback"] = model_info["traceback"]
    
    return response


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "AI Model Service",
        "version": "1.0.0",
        "model_type": model_info["type"],
        "model_loaded": model_info["loaded"]
    }


@app.get("/info", response_model=ModelInfo)
async def info():
    """获取模型信息"""
    return ModelInfo(
        type=model_info["type"],
        loaded=model_info["loaded"],
        path=model_info["path"],
        available_files=model_info.get("files", {})
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """通用预测接口"""
    if not model_info["loaded"]:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        result = None
        model_type = "%(model_type)s"

        # YOLO 模型推理
        if model_type in ["yolo", "ultralytics"]:
            if request.image:
                # 处理图片
                image_data = base64.b64decode(request.image)

                # 检查是否是车牌检测项目
                if isinstance(model, dict) and model.get("is_plate"):
                    # 车牌检测+识别
                    import cv2
                    import numpy as np
                    import torch
                    from PIL import Image

                    # 使用 cv2 读取图片
                    nparr = np.frombuffer(image_data, np.uint8)
                    img_ori = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if img_ori is None:
                        result = {"error": "Failed to decode image"}
                    else:
                        detect_model = model["detect_model"]
                        rec_model = model["rec_model"]
                        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

                        # 移动模型到设备
                        detect_model.to(device)
                        if rec_model:
                            rec_model.to(device)

                        # 运行检测
                        conf = request.parameters.get("conf", 0.3)
                        iou = request.parameters.get("iou", 0.5)
                        results = detect_model(img_ori, conf=conf, iou=iou, verbose=False)

                        # 处理结果
                        result_list = []
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

                                # 透视变换获取车牌 ROI
                                roi_img = four_point_transform(img_ori, landmarks)

                                # 双层车牌处理
                                if plate_type == 1 and rec_model:
                                    from plate_recognition.double_plate_split_merge import get_split_merge
                                    roi_img = get_split_merge(roi_img)

                                # 识别车牌
                                if rec_model:
                                    from plate_recognition.plate_rec import get_plate_result
                                    plate_number, _, plate_color, color_conf = get_plate_result(
                                        roi_img, device, rec_model, is_color=True
                                    )
                                else:
                                    plate_number = ""
                                    plate_color = ""
                                    color_conf = 0.0

                                result_list.append({
                                    "plate_no": plate_number,
                                    "plate_color": plate_color,
                                    "rect": [int(v) for v in box],
                                    "detect_conf": det_conf,
                                    "landmarks": landmarks.tolist(),
                                    "color_conf": color_conf,
                                    "plate_type": "double" if plate_type == 1 else "single"
                                })

                        result = {"plates": result_list, "count": len(result_list)}
                else:
                    # 普通 YOLO 推理
                    image = Image.open(io.BytesIO(image_data))

                    # 运行推理
                    results = model(image, **request.parameters)

                    # 解析结果
                    detections = []
                    for r in results:
                        boxes = r.boxes
                        for box in boxes:
                            detection = {
                                "box": box.xyxy[0].tolist(),
                                "confidence": float(box.conf),
                                "class": int(box.cls),
                                "class_name": model.names[int(box.cls)] if hasattr(model, 'names') else None
                            }
                            detections.append(detection)

                    result = {"detections": detections, "count": len(detections)}
            else:
                result = {"message": "Image required for YOLO prediction"}

        # Transformers 模型推理
        elif model_type in ["transformers", "huggingface", "bert", "llama", "gpt"]:
            if request.text:
                tokenizer = model.get("tokenizer")
                m = model.get("model")

                inputs = tokenizer(request.text, return_tensors="pt", truncation=True, max_length=512)

                # 根据模型类型选择推理方式
                if "%(model_type)s" in ["llama", "gpt"]:
                    outputs = m.generate(**inputs, max_length=100, **request.parameters)
                    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
                else:
                    outputs = m(**inputs)
                    result = outputs.last_hidden_state.mean(dim=1).tolist()
            else:
                result = {"message": "Text required for transformers prediction"}

        # RCAN 超分辨率推理
        elif model_type == "rcan" or (model_info.get("type") == "rcan"):
            if request.image:
                # 处理图片
                image_data = base64.b64decode(request.image)
                import cv2
                import numpy as np
                import torch

                # 使用 cv2 读取图片
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is None:
                    result = {"error": "Failed to decode image"}
                else:
                    # 转换为 RGB 并归一化
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img = img.astype(np.float32) / 255.0

                    # 转换为 tensor
                    img_tensor = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).float()

                    # 推理
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    model_device = model.to(device)
                    img_tensor = img_tensor.to(device)

                    with torch.no_grad():
                        output = model_device(img_tensor)

                    # 处理输出
                    output = output.squeeze(0).cpu().numpy()
                    output = output.transpose(1, 2, 0)
                    output = (output * 255.0).clip(0, 255).astype(np.uint8)

                    # 转换回 BGR
                    output = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

                    # 编码为 base64
                    _, buffer = cv2.imencode('.png', output)
                    img_base64 = base64.b64encode(buffer).decode('utf-8')

                    result = {
                        "super_resolution_image": img_base64,
                        "original_size": {"width": img.shape[1], "height": img.shape[0]},
                        "output_size": {"width": output.shape[1], "height": output.shape[0]},
                        "scale": 4
                    }
            else:
                result = {"message": "Image required for RCAN super resolution"}

        # 通用推理
        else:
            if hasattr(model, 'predict'):
                # sklearn style
                if request.inputs:
                    result = model.predict([request.inputs]).tolist()
                elif request.text:
                    result = model.predict([request.text]).tolist()
                else:
                    result = {"message": "Inputs required for prediction"}
            elif hasattr(model, '__call__'):
                # PyTorch style
                import torch
                if request.inputs:
                    with torch.no_grad():
                        result = model(torch.tensor(request.inputs)).tolist()
                else:
                    result = {"message": "Inputs required for prediction"}
            else:
                result = {"message": "Model inference not implemented. Please customize the predict function."}

        return PredictResponse(result=result, success=True)

    except Exception as e:
        import traceback
        error_detail = str(e) + "\\n" + traceback.format_exc()
        print(f"Prediction error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    """图片预测接口（直接上传文件）"""
    if not model_info["loaded"]:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        contents = await file.read()
        model_type = "%(model_type)s"

        # YOLO 推理
        if model_type in ["yolo", "ultralytics"]:
            # 检查是否是车牌检测项目
            if isinstance(model, dict) and model.get("is_plate"):
                # 车牌检测+识别
                import cv2
                import numpy as np
                import torch

                # 使用 cv2 读取图片
                nparr = np.frombuffer(contents, np.uint8)
                img_ori = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img_ori is None:
                    return {"error": "Failed to decode image"}

                detect_model = model["detect_model"]
                rec_model = model["rec_model"]
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

                # 移动模型到设备
                detect_model.to(device)
                if rec_model:
                    rec_model.to(device)

                # 运行检测
                results = detect_model(img_ori, conf=0.3, iou=0.5, verbose=False)

                # 处理结果
                result_list = []
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

                        # 透视变换获取车牌 ROI
                        roi_img = four_point_transform(img_ori, landmarks)

                        # 双层车牌处理
                        if plate_type == 1 and rec_model:
                            from plate_recognition.double_plate_split_merge import get_split_merge
                            roi_img = get_split_merge(roi_img)

                        # 识别车牌
                        if rec_model:
                            from plate_recognition.plate_rec import get_plate_result
                            plate_number, _, plate_color, color_conf = get_plate_result(
                                roi_img, device, rec_model, is_color=True
                            )
                        else:
                            plate_number = ""
                            plate_color = ""
                            color_conf = 0.0

                        result_list.append({
                            "plate_no": plate_number,
                            "plate_color": plate_color,
                            "rect": [int(v) for v in box],
                            "detect_conf": det_conf,
                            "landmarks": landmarks.tolist(),
                            "color_conf": color_conf,
                            "plate_type": "double" if plate_type == 1 else "single"
                        })

                return {"plates": result_list, "count": len(result_list)}
            else:
                # 普通 YOLO 推理
                image = Image.open(io.BytesIO(contents))
                results = model(image)

                detections = []
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        detection = {
                            "box": box.xyxy[0].tolist(),
                            "confidence": float(box.conf),
                            "class": int(box.cls),
                            "class_name": model.names[int(box.cls)] if hasattr(model, 'names') else None
                        }
                        detections.append(detection)

                return {"detections": detections, "count": len(detections)}

        # RCAN 图片上传预测
        elif model_type == "rcan" or (model_info.get("type") == "rcan"):
            import cv2
            import numpy as np
            import torch

            # 使用 cv2 读取图片
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return {"error": "Failed to decode image"}

            # 转换为 RGB 并归一化
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_rgb = img_rgb.astype(np.float32) / 255.0

            # 转换为 tensor
            img_tensor = torch.from_numpy(img_rgb.transpose(2, 0, 1)).unsqueeze(0).float()

            # 推理
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model_device = model.to(device)
            img_tensor = img_tensor.to(device)

            with torch.no_grad():
                output = model_device(img_tensor)

            # 处理输出
            output = output.squeeze(0).cpu().numpy()
            output = output.transpose(1, 2, 0)
            output = (output * 255.0).clip(0, 255).astype(np.uint8)

            # 转换回 BGR
            output_bgr = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

            # 编码为 base64
            _, buffer = cv2.imencode('.png', output_bgr)
            img_base64 = base64.b64encode(buffer).decode('utf-8')

            return {
                "super_resolution_image": img_base64,
                "original_size": {"width": img.shape[1], "height": img.shape[0]},
                "output_size": {"width": output_bgr.shape[1], "height": output_bgr.shape[0]},
                "scale": 4
            }

        else:
            return {"message": "Image prediction not supported for this model type"}

    except Exception as e:
        import traceback
        error_detail = str(e) + "\\n" + traceback.format_exc()
        print(f"Predict image error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=%(port)d)
'''
