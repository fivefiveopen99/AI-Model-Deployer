# Real-ESRGAN 超分模型上传与平台构建说明

本文说明 `Real-ESRGAN.zip` 在 AI Model Deployer 中的上传、自动构建和预测接口行为。后续用户只需要通过前端 UI 上传压缩包，不需要手动修改压缩包里的 Dockerfile，也不需要自行添加 FastAPI 入口。

## 压缩包要求

当前模型包：

```text
2.超分模型/
  Real-ESRGAN.zip
```

解压后应包含一个 Real-ESRGAN 项目目录，关键文件如下：

```text
Real-ESRGAN/
  setup.py
  requirements.txt
  inference_realesrgan.py
  realesrgan/
  experiments/
    RealESRGAN_x4plus.pth
  weights/
```

平台构建适配器会用这些标记识别 Real-ESRGAN 项目：

```text
realesrgan/
inference_realesrgan.py
setup.py
experiments/RealESRGAN_x4plus.pth
```

权重也可以放在：

```text
weights/RealESRGAN_x4plus.pth
```

如果权重是 Git LFS 指针文件，构建会失败并提示重新拉取真实 `.pth` 文件后再打包上传。

## 前端上传流程

1. 进入“模型管理”页面。
2. 选择“上传模型”。
3. 上传 `Real-ESRGAN.zip`。
4. 模型类型可保持 `custom`，构建阶段会自动识别为 Real-ESRGAN。
5. 上传完成后点击“构建镜像”。
6. 基础镜像保持默认即可；Real-ESRGAN 适配器会自动使用 CUDA PyTorch 运行镜像，除非显式传入其他基础镜像。

构建时平台会自动完成：

- 解压用户上传的 zip。
- 检测 Real-ESRGAN 项目结构和权重文件。
- 生成平台兼容的 `api.py`。
- 生成 Dockerfile。
- 安装 FastAPI、Uvicorn、OpenCV、BasicSR、Real-ESRGAN 相关依赖。
- 执行 `docker build -t ai-model:{build_id}`。
- 导出镜像 tar，并按当前平台设计分发到 Kubernetes worker 节点。

## 生成服务接口

构建后的镜像会暴露平台统一推理接口：

```text
GET  /
GET  /health
POST /predict/image
POST /predict
```

`POST /predict/image` 使用 `multipart/form-data`：

```text
file: image file
outscale: float, default 4
tile: int, default 256
```

`POST /predict` 使用 JSON：

```json
{
  "image": "base64-encoded-image",
  "parameters": {
    "outscale": 4,
    "tile": 256
  }
}
```

响应会返回 base64 PNG：

```json
{
  "success": true,
  "model_type": "realesrgan",
  "task": "image_super_resolution",
  "super_resolution_image": "...",
  "processed_image": "...",
  "original_size": {"width": 640, "height": 480},
  "output_size": {"width": 2560, "height": 1920},
  "scale": 4,
  "tile": 256
}
```

`processed_image` 是为了兼容前端 playground 的统一图片显示逻辑。

## 运行参数

生成服务支持以下环境变量：

```text
REALESRGAN_WEIGHT=experiments/RealESRGAN_x4plus.pth
MODEL_PATH=experiments/RealESRGAN_x4plus.pth
REALESRGAN_MODEL_NAME=RealESRGAN_x4plus
DEVICE=cpu
GPU_ID=0
REALESRGAN_OUTSCALE=4
REALESRGAN_TILE=256
TILE=256
MAX_INPUT_PIXELS=4194304
```

说明：

- `REALESRGAN_WEIGHT` 优先级高于 `MODEL_PATH`。
- `REALESRGAN_TILE` 优先级高于 `TILE`。
- `DEVICE=cpu` 是默认值，适合无 GPU 的构建验证和小图测试。
- Kubernetes 侧如果要用 GPU，需要部署资源和节点运行时同时具备 GPU 能力，再设置 `DEVICE=cuda` 和 `GPU_ID=0`。
- 不建议设置多个 Uvicorn worker；每个 worker 都会单独加载一份模型。

## 本地接口测试

健康检查：

```bash
curl http://localhost:8000/health
```

图片推理：

```bash
curl -X POST http://localhost:8000/predict/image \
  -F "file=@input.png" \
  -F "outscale=4" \
  -F "tile=256"
```

平台前端的模型 playground 会调用 `/api/v1/proxy/deployments/{id}/predict/image`，不需要用户直接访问容器内部端口。
