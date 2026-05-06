# Model Projects FastAPI and Docker Packaging Notes

This file is a model-readable summary of how the platform wraps known model projects as FastAPI services and packages them into Docker images.

Scope note: the current workspace does not contain the original uploaded model project directories under `data/models`, so this analysis is based on the platform's build adapters and generated service templates. The two detailed project adapters below are RCAN and Real-ESRGAN. The codebase also contains a YOLO plate-recognition adapter.

## Repository Context

- Platform: AI Model Deployer.
- Backend build entry: `backend/app/services/docker_service.py`.
- Build task orchestration: `backend/app/api/models.py`.
- Uploaded or imported model archives are copied into a temporary Docker build context under `data/builds/{build_id}`.
- Runtime model archives and extracted assets live under `data/`; avoid broad scans because this directory can contain large weights and generated artifacts.

## Build Pipeline

1. A user uploads or imports a model project through the backend model APIs.
2. `build_model_task()` in `backend/app/api/models.py` calls `docker_service.build_model_image()`.
3. `DockerService.build_model_image()` creates a build context:
   - `data/builds/{model_name}_{timestamp}/`
   - temporary source copy under `data/builds/{build_id}/model/`
4. `_prepare_model_files()` copies, extracts, or clones the source into the temporary model directory.
5. `detect_model_type()` performs generic model type detection.
6. `_select_build_adapter()` checks for specialized project adapters in this order:
   - user-provided FastAPI project with both `api.py` and `Dockerfile`
   - YOLO plate recognition project
   - RCAN super-resolution project
   - Real-ESRGAN super-resolution project
   - generic generated service fallback
7. If an adapter matches:
   - the original model project is copied to the build context root
   - generated `api.py` is written into the build context
   - generated `Dockerfile` is written into the build context
   - the temporary `model/` copy is removed
8. Docker builds the image with tag `ai-model:{build_id}`.
9. The image is exported to a local tar file in `data/images`.
10. If Kubernetes is connected, the image tar is imported to worker nodes over SSH/SCP.
11. The model database row is updated with image name, tag, and status.

## Adapter 1: RCAN Super Resolution

### Detection Rules

The RCAN adapter matches when a project directory contains all of these files:

```text
src/model/rcan.py
experiment/RCAN/model/model_best.pth
requirements.txt
```

The detector recursively searches inside the uploaded or extracted archive, so the project can be nested under a top-level folder.

### Validation

The adapter requires:

- `experiment/RCAN/model/model_best.pth` exists.
- The weight file is not a Git LFS pointer. Files smaller than 1024 bytes are checked for the `version https://git-lfs.github.com/spec` header.

If the weight is still a Git LFS pointer, the user must run `git lfs pull` before uploading the archive.

### Generated FastAPI Service

The adapter writes `api.py` from `RCAN_SERVICE_API`.

Service behavior:

- Imports the project from the container working directory with `sys.path.insert(0, os.getcwd())`.
- Imports RCAN code as `from src import model as rcan_model`.
- Loads the model during FastAPI lifespan startup.
- Uses environment variables:
  - `RCAN_WEIGHT`, default `experiment/RCAN/model/model_best.pth`
  - `DEVICE`, default `cpu`
  - `RCAN_SCALE`, default `4`
- Builds an `Args` object that matches the bundled RCAN architecture:
  - `n_resgroups = 10`
  - `n_resblocks = 20`
  - `n_feats = 64`
  - `reduction = 16`
  - `scale = RCAN_SCALE`
  - `n_colors = 3`
  - `rgb_range = 255`

Endpoints:

- `GET /`: returns service name and loaded state.
- `GET /health`: returns health, model type `rcan`, scale, and device.
- `POST /predict/image`: accepts multipart image field `file` and optional form field `sharpen`.
- `POST /predict`: accepts JSON with base64 `image` and optional `parameters.sharpen`.

Output:

- PNG image encoded as base64 in `super_resolution_image`.
- Same base64 output also appears as `processed_image` for frontend compatibility.
- Includes original and output image dimensions.

### Generated Dockerfile

The adapter writes a Dockerfile from `_generate_rcan_dockerfile()`.

Default base image:

```text
pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
```

The caller can override this by passing a non-default `base_image` or `config.rcan_base_image`.

Installed OS packages:

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

Installed Python packages:

```text
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
opencv-python-headless>=4.8.0
numpy>=1.23.0
pillow>=7.1.2
tqdm>=4.60.0
```

Runtime command:

```text
python -m uvicorn api:app --host 0.0.0.0 --port {port}
```

Healthcheck:

```text
curl -f http://localhost:{port}/health || exit 1
```

## Adapter 2: Real-ESRGAN Super Resolution

### Detection Rules

The Real-ESRGAN adapter matches when a project directory contains all of these markers:

```text
realesrgan/
inference_realesrgan.py
setup.py
experiments/RealESRGAN_x4plus.pth
```

The weight may also be accepted at:

```text
weights/RealESRGAN_x4plus.pth
```

The detector recursively searches inside the uploaded or extracted archive.

### Validation

The adapter requires one of these weight files:

```text
experiments/RealESRGAN_x4plus.pth
weights/RealESRGAN_x4plus.pth
```

As with RCAN, small files are checked for Git LFS pointer content. Upload the archive only after real `.pth` weights are present.

### Generated FastAPI Service

The adapter writes `api.py` from `REALESRGAN_SERVICE_API`.

Service behavior:

- Imports `RRDBNet` from `basicsr.archs.rrdbnet_arch`.
- Imports `RealESRGANer` from `realesrgan`.
- Loads the model during FastAPI lifespan startup.
- Uses `run_in_threadpool()` for CPU-heavy inference.
- Supports only `MODEL_NAME = RealESRGAN_x4plus` in the current generated service.

Environment variables:

- `REALESRGAN_WEIGHT`, default `experiments/RealESRGAN_x4plus.pth`
- `MODEL_PATH`, fallback alias for `REALESRGAN_WEIGHT`
- `REALESRGAN_MODEL_NAME`, default `RealESRGAN_x4plus`
- `DEVICE`, default `cpu`
- `GPU_ID`, optional CUDA device index when `DEVICE` starts with `cuda`
- `REALESRGAN_OUTSCALE`, default `4`
- `REALESRGAN_TILE`, default `256`
- `TILE`, fallback alias for `REALESRGAN_TILE`
- `MAX_INPUT_PIXELS`, default `4194304`

Endpoints:

- `GET /`: returns service name and loaded state.
- `GET /health`: returns health, model type `realesrgan`, task `image_super_resolution`, model name, and device.
- `POST /predict/image`: accepts multipart image field `file`, optional `outscale`, and optional `tile`.
- `POST /predict`: accepts JSON with base64 `image` and optional `parameters.outscale` / `parameters.tile`.

Output:

- PNG image encoded as base64 in `super_resolution_image`.
- Same base64 output also appears as `processed_image` for frontend compatibility.
- Includes original and output image dimensions, scale, and tile.
- The per-request `tile` value is applied before inference, so callers can use larger tiles for speed or smaller tiles for lower memory usage.

### Generated Dockerfile

The adapter writes a Dockerfile from `_generate_realesrgan_dockerfile()`.

Default base image:

```text
pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
```

The caller can override this by passing a non-default `base_image` or `config.realesrgan_base_image`.

Installed OS packages:

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

Installed Python packages:

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

The Dockerfile also:

- Installs the uploaded Real-ESRGAN project in editable mode with `pip install --no-cache-dir --no-deps -e .`.
- Creates `weights/` if missing.
- Copies `experiments/RealESRGAN_x4plus.pth` to `weights/RealESRGAN_x4plus.pth` when needed.
- Patches `basicsr/data/degradations.py` so `rgb_to_grayscale` is imported from `torchvision.transforms.functional`, which is compatible with newer torchvision versions.

For the sample archive under `2.超分模型/Real-ESRGAN.zip`, users should upload the zip directly from the frontend. They do not need to add `api.py`; the build adapter generates the platform-compatible FastAPI service during Docker image construction.

Runtime command:

```text
python -m uvicorn api:app --host 0.0.0.0 --port {port}
```

Healthcheck:

```text
curl -f http://localhost:{port}/health || exit 1
```

## User-Provided FastAPI Project Shortcut

If an uploaded project already includes both:

```text
api.py
Dockerfile
```

then the platform does not generate a wrapper. It copies that project as-is and uses the provided Dockerfile.

Expected contract:

- FastAPI app object should be `app` in `api.py`.
- The Dockerfile should expose the configured port.
- The service should provide `GET /health`.
- The service should provide either `POST /predict` or `POST /predict/image` for frontend and proxy compatibility.

## Standard Service Contract

Generated model services should expose:

- `GET /health`
- `POST /predict`
- `POST /predict/image` when the model is image-based

The platform and frontend expect:

- JSON responses.
- `success` boolean when possible.
- `model_type` string.
- For image-to-image tasks, base64 image output in `processed_image` and/or task-specific fields such as `super_resolution_image`.

## Important Caveats

- The current workspace has `data/models` empty, so no uploaded RCAN or Real-ESRGAN source project is available for direct inspection.
- Existing exported image tar files are under `data/images`, but the source projects used to create them are not present in `data/models`.
- Docker, Kubernetes, SSH, and network availability should be checked before assuming a build or deployment can run.
- Generated build contexts are removed after the Docker image build finishes, so inspect or preserve them during debugging if needed.
- Large weights should be real binary files, not Git LFS pointer files.

## Minimal Upload Layouts

RCAN archive layout:

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

Real-ESRGAN archive layout:

```text
Real-ESRGAN-project/
  realesrgan/
  inference_realesrgan.py
  setup.py
  experiments/
    RealESRGAN_x4plus.pth
```

Alternative Real-ESRGAN weight path:

```text
Real-ESRGAN-project/
  weights/
    RealESRGAN_x4plus.pth
```
