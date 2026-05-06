# 图像生成模型上传、构建与部署说明

这个目录已经整理成 AI Model Deployer 可直接识别的 FastAPI 推理项目。用户后续通过前端上传包含 `images_gen/` 的压缩包后，后端构建流程会自动找到 `images_gen/api.py` 和 `images_gen/Dockerfile`，并直接使用该子目录构建镜像。

## 目录要求

推荐压缩包结构：

```text
图像生成模型.zip
  images_gen/
    api.py
    Dockerfile
    demo_lora.py
    test_lora_sd.py
    train_lora_sd.py
    lora_patch_1112/
      pytorch_lora_weights.safetensors
```

权重目录名称可以不是 `lora_patch_1112`。服务启动时会按下面顺序寻找 LoRA 权重：

1. 环境变量 `MODEL_DIR` 指向的目录。
2. `/app/model`。
3. `/app/lora_patch_1112`。
4. `/app` 下第一个包含 `pytorch_lora_weights.safetensors` 的目录。

必须包含的权重文件：

```text
pytorch_lora_weights.safetensors
```

## 上传和构建

前端操作流程：

1. 进入“模型管理”页面。
2. 上传包含 `images_gen/` 的 `.zip`、`.tar.gz`、`.tgz` 或 `.tar` 压缩包。
3. 模型类型可以选择 `custom` 或图像相关类型。
4. 上传完成后点击“构建镜像”。

后端构建流程会：

1. 解压压缩包。
2. 识别 `images_gen/api.py` 和 `images_gen/Dockerfile`。
3. 以 `images_gen/` 作为 Docker build context。
4. 构建 `ai-model:{build_id}` 镜像。
5. 导出 tar 包，并在 Kubernetes 可用时分发到 worker 节点。

## 服务接口

健康检查：

```http
GET /health
```

图像生成：

```http
POST /generate
```

平台通用预测接口：

```http
POST /predict
```

`/predict` 接受 AI Model Deployer playground 的通用 JSON 结构：

```json
{
  "inputs": {
    "position": "center",
    "class_name": "unknown"
  },
  "parameters": {
    "width": 128,
    "height": 128,
    "num_inference_steps": 30,
    "num_images": 1,
    "seed": 42
  }
}
```

也可以直接调用 `/generate`：

```json
{
  "position": "center",
  "class_name": "unknown",
  "width": 128,
  "height": 128,
  "num_inference_steps": 30,
  "num_images": 1,
  "seed": 42,
  "negative_prompt": "Text, blurry, out of focus, complex, color, noisy, multiple patterns, low quality, photo, realistic, messy, hand drawn, watercolor, text, noise, low resolution."
}
```

响应会返回 PNG 图片的 base64：

```json
{
  "success": true,
  "model_type": "image_generation",
  "prompt": "A pattern design at center position, graphic design...",
  "images": [
    {
      "filename": "image_0.png",
      "content_type": "image/png",
      "base64": "..."
    }
  ]
}
```

## 运行参数

Dockerfile 默认使用平台部署端口 `8000`。

常用环境变量：

```text
BASE_MODEL_ID=stable-diffusion-v1-5/stable-diffusion-v1-5
MODEL_DIR=/app/lora_patch_1112
LORA_WEIGHT_NAME=pytorch_lora_weights.safetensors
DEVICE=cuda
HF_HOME=/hf_home
HF_ENDPOINT=https://hf-mirror.com
MAX_IMAGES=4
MAX_PIXELS=1048576
```

说明：

- `width` 和 `height` 必须是 8 的倍数，范围是 `64..1024`。
- `num_images` 默认最多 `4`，可通过 `MAX_IMAGES` 调整。
- 服务启动时只加载一次 Stable Diffusion pipeline 和 LoRA 权重。
- 推理阶段使用单进程内锁串行执行，避免同一个 Diffusers pipeline 被并发调用导致显存异常。
- 不建议使用多个 uvicorn worker，因为每个 worker 都会加载一份模型。

## 本地 Docker 验证

进入项目目录：

```bash
cd "1.图像生成模型/images_gen"
```

构建：

```bash
docker build -t image-generation-api .
```

运行：

```bash
docker run --rm --gpus all \
  -p 8000:8000 \
  -e MODEL_DIR=/app/lora_patch_1112 \
  image-generation-api
```

健康检查：

```bash
curl http://localhost:8000/health
```

推理测试：

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs":{"position":"center","class_name":"unknown"},"parameters":{"width":128,"height":128,"num_inference_steps":30,"num_images":1}}'
```
