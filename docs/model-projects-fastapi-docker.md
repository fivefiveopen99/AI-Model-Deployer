# 模型项目 FastAPI 和 Docker 打包说明

本文档说明平台如何将已知模型项目包装成 FastAPI 服务，并打包为 Docker 镜像。它面向需要接入、排查或维护模型适配器的开发和运维人员。

范围说明：当前工作区不包含用户曾经上传到 `data/models` 下的原始模型项目目录，因此本文主要根据平台现有构建适配器和生成服务模板整理。下文重点说明 RCAN 和 Real-ESRGAN 两个适配器；代码中还包含 YOLO 车牌识别适配器。

## 仓库上下文

- 平台名称：OG-MAP。
- 后端构建入口：`backend/app/services/docker_service.py`。
- 构建任务编排：`backend/app/api/models.py`。
- 上传或导入的模型项目会被复制到 `data/builds/{build_id}` 下的临时 Docker 构建上下文。
- 运行时模型归档、解压资产和权重文件位于 `data/`，该目录可能很大，排查时应避免无目的全量扫描。

## 构建流程

1. 用户通过模型 API 上传或导入模型项目。
2. `backend/app/api/models.py` 中的构建任务调用 `docker_service.build_model_image()`。
3. `DockerService.build_model_image()` 创建构建上下文：
   - `data/builds/{model_name}_{timestamp}/`
   - 临时源码副本：`data/builds/{build_id}/model/`
4. `_prepare_model_files()` 将源码复制、解压或克隆到临时模型目录。
5. `detect_model_type()` 执行通用模型类型检测。
6. `_select_build_adapter()` 按顺序检查特化适配器：
   - 用户自带 `api.py` 和 `Dockerfile` 的 FastAPI 项目。
   - YOLO 车牌识别项目。
   - RCAN 超分辨率项目。
   - Real-ESRGAN 超分辨率项目。
   - 通用生成服务 fallback。
7. 如果命中特化适配器：
   - 原始模型项目复制到构建上下文根目录。
   - 生成的 `api.py` 写入构建上下文。
   - 生成的 `Dockerfile` 写入构建上下文。
   - 删除临时 `model/` 副本。
8. Docker 使用 `ai-model:{build_id}` 作为 tag 构建镜像。
9. 镜像被重新标记为 `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:{build_id}`。
10. 后端将镜像推送到本地 Docker Registry 服务。
11. 模型数据库记录更新 Registry 镜像名、tag 和状态。

## 适配器 1：RCAN 超分辨率

### 识别规则

当项目目录同时包含以下文件时，RCAN 适配器会匹配：

```text
src/model/rcan.py
experiment/RCAN/model/model_best.pth
requirements.txt
```

检测逻辑会递归搜索上传或解压后的目录，因此项目可以位于压缩包内的顶层子目录中。

### 校验规则

适配器要求：

- `experiment/RCAN/model/model_best.pth` 必须存在。
- 权重文件不能是 Git LFS 指针。小于 1024 字节的权重文件会检查是否包含 `version https://git-lfs.github.com/spec` 头。

如果权重仍是 Git LFS 指针，用户需要先运行 `git lfs pull`，再上传包含真实权重的压缩包。

### 生成的 FastAPI 服务

适配器会根据 `RCAN_SERVICE_API` 生成 `api.py`。

服务行为：

- 通过 `sys.path.insert(0, os.getcwd())` 从容器工作目录导入项目。
- 使用 `from src import model as rcan_model` 导入 RCAN 代码。
- 在 FastAPI lifespan 启动阶段加载模型。
- 使用以下环境变量：
  - `RCAN_WEIGHT`, default `experiment/RCAN/model/model_best.pth`
  - `DEVICE`, default `cpu`
  - `RCAN_SCALE`, default `4`
- 构造匹配项目内 RCAN 架构的 `Args` 对象：
  - `n_resgroups = 10`
  - `n_resblocks = 20`
  - `n_feats = 64`
  - `reduction = 16`
  - `scale = RCAN_SCALE`
  - `n_colors = 3`
  - `rgb_range = 255`

端点：

- `GET /`: 返回服务名称和加载状态。
- `GET /health`: 返回健康状态、模型类型 `rcan`、scale 和 device。
- `POST /predict/image`: 接收 multipart 图片字段 `file`，可选表单字段 `sharpen`。
- `POST /predict`: 接收 JSON，其中包含 base64 `image`，可选 `parameters.sharpen`。

输出：

- `super_resolution_image` 中返回 base64 编码的 PNG 图片。
- 为兼容前端，同一份 base64 输出也会出现在 `processed_image`。
- 返回原始图片和输出图片尺寸。

### 生成的 Dockerfile

适配器通过 `_generate_rcan_dockerfile()` 生成 Dockerfile。

默认基础镜像：

```text
pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
```

调用方可以通过非默认 `base_image` 或 `config.rcan_base_image` 覆盖基础镜像。

安装的系统包：

```text
gcc
g++
curl
libgl1
libglib2.0-0
libsm6
libxext6
libxrender1
libgomp1
```

安装的 Python 包：

```text
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
opencv-python-headless>=4.8.0
numpy>=1.23.0
pillow>=7.1.2
tqdm>=4.60.0
```

运行命令：

```text
python -m uvicorn api:app --host 0.0.0.0 --port {port}
```

健康检查：

```text
curl -f http://localhost:{port}/health || exit 1
```

## 适配器 2：Real-ESRGAN 超分辨率

### 识别规则

当项目目录包含以下标记时，Real-ESRGAN 适配器会匹配：

```text
realesrgan/
inference_realesrgan.py
setup.py
experiments/RealESRGAN_x4plus.pth
```

权重文件也可以位于：

```text
weights/RealESRGAN_x4plus.pth
```

检测逻辑会递归搜索上传或解压后的目录。

### 校验规则

适配器要求存在以下任一权重文件：

```text
experiments/RealESRGAN_x4plus.pth
weights/RealESRGAN_x4plus.pth
```

和 RCAN 一样，小文件会检查是否为 Git LFS 指针。请确保真实 `.pth` 权重已经存在后再上传压缩包。

### 生成的 FastAPI 服务

适配器会根据 `REALESRGAN_SERVICE_API` 生成 `api.py`。

服务行为：

- 从 `basicsr.archs.rrdbnet_arch` 导入 `RRDBNet`。
- 从 `realesrgan` 导入 `RealESRGANer`。
- 在 FastAPI lifespan 启动阶段加载模型。
- 使用 `run_in_threadpool()` 执行计算较重的推理。
- 当前生成服务仅支持 `MODEL_NAME = RealESRGAN_x4plus`。

环境变量：

- `REALESRGAN_WEIGHT`, default `experiments/RealESRGAN_x4plus.pth`
- `MODEL_PATH`, fallback alias for `REALESRGAN_WEIGHT`
- `REALESRGAN_MODEL_NAME`, default `RealESRGAN_x4plus`
- `DEVICE`, default `cpu`
- `GPU_ID`, optional CUDA device index when `DEVICE` starts with `cuda`
- `REALESRGAN_OUTSCALE`, default `4`
- `REALESRGAN_TILE`, default `256`
- `TILE`, fallback alias for `REALESRGAN_TILE`
- `MAX_INPUT_PIXELS`, default `4194304`

端点：

- `GET /`: 返回服务名称和加载状态。
- `GET /health`: 返回健康状态、模型类型 `realesrgan`、任务 `image_super_resolution`、模型名称和 device。
- `POST /predict/image`: 接收 multipart 图片字段 `file`，可选 `outscale` 和 `tile`。
- `POST /predict`: 接收 JSON，其中包含 base64 `image`，可选 `parameters.outscale` / `parameters.tile`。

输出：

- `super_resolution_image` 中返回 base64 编码的 PNG 图片。
- 为兼容前端，同一份 base64 输出也会出现在 `processed_image`。
- 返回原始图片尺寸、输出图片尺寸、scale 和 tile。
- 每次请求传入的 `tile` 会在推理前生效，调用方可用较大 tile 提升速度，或用较小 tile 降低显存/内存占用。

### 生成的 Dockerfile

适配器通过 `_generate_realesrgan_dockerfile()` 生成 Dockerfile。

默认基础镜像：

```text
pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
```

调用方可以通过非默认 `base_image` 或 `config.realesrgan_base_image` 覆盖基础镜像。

安装的系统包：

```text
gcc
g++
curl
libgl1
libglib2.0-0
libsm6
libxext6
libxrender1
libgomp1
```

安装的 Python 包：

```text
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
opencv-python-headless>=4.8.0
numpy>=1.23.0
pillow>=7.1.2
tqdm>=4.60.0
torchvision==0.20.1
basicsr==1.4.2
facexlib>=0.2.5
gfpgan>=1.3.5
```

Dockerfile 还会：

- 使用 `pip install --no-cache-dir --no-deps -e .` 以 editable 模式安装上传的 Real-ESRGAN 项目。
- 如果缺少 `weights/`，则创建该目录。
- 必要时将 `experiments/RealESRGAN_x4plus.pth` 复制到 `weights/RealESRGAN_x4plus.pth`。
- 修补 `basicsr/data/degradations.py`，让 `rgb_to_grayscale` 从 `torchvision.transforms.functional` 导入，以兼容较新的 torchvision。

对于示例压缩包 `2.超分模型/Real-ESRGAN.zip`，用户可以直接在前端上传 zip，不需要手动添加 `api.py`；构建适配器会在镜像构建阶段生成平台兼容的 FastAPI 服务。

运行命令：

```text
python -m uvicorn api:app --host 0.0.0.0 --port {port}
```

健康检查：

```text
curl -f http://localhost:{port}/health || exit 1
```

## 用户自带 FastAPI 项目

如果上传项目已经同时包含：

```text
api.py
Dockerfile
```

平台不会生成包装服务，而是原样复制该项目并使用用户提供的 Dockerfile。

期望契约：

- `api.py` 中的 FastAPI 应用对象应为 `app`。
- Dockerfile 应暴露配置的端口。
- 服务应提供 `GET /health`。
- 为兼容前端和后端代理，服务应提供 `POST /predict` 或 `POST /predict/image`。

## 标准服务契约

生成的模型服务应暴露：

- `GET /health`
- `POST /predict`
- `POST /predict/image` when the model is image-based

平台和前端期望：

- 返回 JSON。
- 尽可能包含 `success` 布尔值。
- 包含 `model_type` 字符串。
- 对图像到图像任务，在 `processed_image` 或任务特定字段中返回 base64 图片，例如 `super_resolution_image`。

## 注意事项

- 当前工作区的 `data/models` 为空，因此无法直接检查已上传的 RCAN 或 Real-ESRGAN 源项目。
- Registry 中已有镜像不一定在 `data/models` 下保留对应源码。
- 在判断构建或部署是否可运行前，应先检查 Docker、Kubernetes、Registry 和网络可用性。
- 生成的构建上下文会在 Docker 镜像构建完成后删除；排查构建问题时如需查看，应提前保留或临时调整逻辑。
- 大模型权重必须是真实二进制文件，不能是 Git LFS 指针文件。

## 最小上传结构

RCAN 压缩包结构：

```text
RCAN-project/
  src/
    model/
      rcan.py
  experiment/
    RCAN/
      model/
        model_best.pth
  requirements.txt
```

Real-ESRGAN 压缩包结构：

```text
Real-ESRGAN-project/
  realesrgan/
  inference_realesrgan.py
  setup.py
  experiments/
    RealESRGAN_x4plus.pth
```

Real-ESRGAN 可选权重路径：

```text
Real-ESRGAN-project/
  weights/
    RealESRGAN_x4plus.pth
```
