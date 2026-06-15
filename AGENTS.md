# AGENTS.md

This file is the project-level context file for Codex and other coding agents. Read it before making changes.

## Project Summary

OG-MAP is a FastAPI + Vue application for managing AI model projects, packaging them into Docker images, pushing those images to the bundled Docker Registry service, and creating Kubernetes deployments for online inference.

Core goals:

- Register models from uploaded archives, GitHub repositories, direct URLs, or manually provided paths.
- Auto-detect model project files and build a Docker image that exposes a FastAPI inference service.
- Push built images to the bundled registry at `${REGISTRY_HOST_IP}:5000/ai-models`.
- Create Kubernetes Deployment and NodePort Service resources for model serving.
- Provide a web UI for model management, deployment management, logs, scaling, and prediction testing.

Important current design decision:

- Image distribution is done through the bundled `registry:2` service. The backend tags `ai-model:{build_id}` as `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:{build_id}` and pushes it.
- The model status value `pushing` is still used internally for registry push progress and backward compatibility.

## Repository Layout

```text
.
├── AGENTS.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── models/
│       └── services/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
└── docs/
    └── model-projects-fastapi-docker.md
```

Runtime/generated paths that should not be committed:

- `data/`: SQLite DB, uploaded archives, extracted model projects, Docker build contexts, image tar files, model weights.
- `.env`: local proxy, K8s, and registry configuration.
- `node_modules/`, `dist/`, `__pycache__/`, virtualenvs, and other caches.

## Technology Stack

Backend:

- Python 3.11
- FastAPI / Uvicorn
- SQLAlchemy async ORM
- SQLite via `aiosqlite`
- Docker CLI integration
- Kubernetes Python client
- HTTPX for outbound HTTP/proxy calls
- WebSocket progress updates

Frontend:

- Vue 3
- Vite
- Pinia
- Vue Router
- Axios
- Element Plus

Runtime:

- Docker Compose starts `backend`, `frontend`, and `redis`.
- Frontend production image serves static assets through nginx and proxies `/api` to `backend:8000`.
- Backend mounts Docker socket, Docker binary, kube config, and `./data`.

## Main Runtime Commands

Full stack:

```bash
docker compose up -d
```

Rebuild frontend image:

```bash
docker compose build frontend
```

Rebuild backend image:

```bash
docker compose build backend
```

Backend local development:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend local development:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Web UI: `http://localhost:5173`
- API docs: `http://localhost:8000/api/v1/docs`
- Root health-ish endpoint: `http://localhost:8000/`

## Configuration

Main config source:

- `backend/app/core/config.py`
- `.env.example`
- `docker-compose.yml`

Key backend settings:

- `DATABASE_URL`: default `sqlite+aiosqlite:///./data/models.db`
- `REGISTRY_HOST_IP`: deployment node IP reachable by Kubernetes nodes; set this per node before deployment.
- `DOCKER_REGISTRY_URL`: default `${REGISTRY_HOST_IP}:5000/ai-models`
- `DOCKER_REGISTRY_PUSH_URL`: default `localhost:5000/ai-models`
- `DOCKER_REGISTRY_USERNAME`: default empty for bundled registry
- `DOCKER_REGISTRY_PASSWORD`: default empty for bundled registry
- `MODEL_STORAGE_PATH`: default `./data/models`
- `BUILD_CONTEXT_PATH`: default `./data/builds`
- `K8S_CONFIG_PATH`: optional kube config path
- `K8S_NAMESPACE`: default `default`
- `K8S_IMAGE_PULL_SECRET_NAME`: default empty for bundled registry

Proxy environment:

- `BACKEND_HTTP_PROXY`, `BACKEND_HTTPS_PROXY`, `BACKEND_ALL_PROXY`, `BACKEND_NO_PROXY` are passed through Compose.
- Proxy routes use `httpx.AsyncClient(..., trust_env=False)` when calling deployed model services to avoid accidental proxy routing to internal NodePort endpoints.

## Backend Architecture

Entry point:

- `backend/app/main.py`
- Creates FastAPI app.
- Initializes DB tables on startup through `init_db()`.
- Registers routers under `settings.API_V1_STR`, currently `/api/v1`.
- Adds permissive CORS from `settings.CORS_ORIGINS`.
- Defines a broad exception handler, including custom 413-style large upload response.

Routers:

- `backend/app/api/models.py`: model CRUD, uploads, GitHub/URL import, image build, status/reset/delete.
- `backend/app/api/deployments.py`: deployment CRUD, deploy to K8s, sync K8s status, scale, logs, delete, direct K8s list.
- `backend/app/api/system.py`: Docker/K8s status and counts.
- `backend/app/api/websocket.py`: WebSocket progress subscription endpoint.
- `backend/app/api/proxy.py`: forwards health and prediction requests to deployed model services.

Database:

- `backend/app/models/database.py`
- Uses SQLAlchemy async engine and `async_session_maker`.
- Tables:
  - `AIModel`
  - `Deployment`
- Tables are created automatically with `Base.metadata.create_all`; there is no migration system.

Schemas:

- `backend/app/models/schemas.py`
- Pydantic request/response models for model records, deployment records, task progress, and system status.

Services:

- `backend/app/services/docker_service.py`
- `backend/app/services/k8s_service.py`
- `backend/app/services/model_service_template.py`

## Model Lifecycle

Model sources:

- `POST /api/v1/models`: creates a record from explicit model metadata and source path.
- `POST /api/v1/models/upload`: accepts `.zip`, `.tar.gz`, `.tgz`, `.tar`, extracts to `data/models/{name}/extracted`.
- `POST /api/v1/models/from-url`: clones GitHub repositories or downloads direct URLs.

GitHub import behavior:

- GitHub URLs are cloned with `git clone --depth 1`.
- If `.gitattributes` declares Git LFS, the backend runs `git lfs pull`.
- If expected model weights are still Git LFS pointer files, the API returns a clear error.

Model file detection:

- `find_model_files()` searches recursively for:
  - weights: `.pt`, `.pth`, `.onnx`, `.engine`, `.weights`
  - config files containing `config` in filename
  - `requirements.txt`
  - inference scripts named `detect.py`, `predict.py`, `inference.py`, or `run.py`

Model statuses:

- `pending`
- `uploading`
- `uploaded`
- `building`
- `built`
- `pushing` - used as distributing/exporting/importing state
- `ready`
- `failed`

Do not rename `pushing` casually. Existing SQLite rows may contain this enum value.

## Build Pipeline

Build entry:

- API: `POST /api/v1/models/{model_id}/build`
- Task ID: `build-{model_id}`
- Background function: `run_build_task()` in `backend/app/api/models.py`
- Build implementation: `DockerService.build_model_image()`

Build steps:

1. Fetch model row.
2. Set status to `building`.
3. Create build context under `data/builds/{model_name}_{timestamp}`.
4. Copy model files into build context.
5. Detect model type.
6. Select a specialized build adapter, or fall back to generic generated FastAPI service.
7. Run `docker build -t ai-model:{build_id} {build_context}`.
8. Store Docker image metadata on the model row.
9. Set status to `pushing` while publishing to the registry.
10. Run `docker tag` and `docker push` to `localhost:5000/ai-models/ai-model:{build_id}`; store the deployable image as `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:{build_id}`.
11. Store registry image metadata on the model row.
12. Mark model as `ready` after the registry push succeeds; mark it `failed` if the push fails.

Build context cleanup:

- `DockerService.build_model_image()` removes the temporary build context in a `finally` block.

Image naming:

- Local built image tag format: `ai-model:{build_id}`.
- Registry image tag format: `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:{build_id}`.
- `docker_image` becomes `${REGISTRY_HOST_IP}:5000/ai-models/ai-model`.
- `docker_image_tag` becomes `{build_id}`.

Stored config values after build may include:

- `distribution_mode: "registry"`
- `registry_image`
- `push_result`

## Docker Service Details

File:

- `backend/app/services/docker_service.py`

Responsibilities:

- Check Docker CLI availability.
- Detect generic model type from project contents.
- Build image through Docker CLI.
- Push built images to the registry with Docker CLI.
- Remove images when model rows are deleted.
- Generate Dockerfiles and FastAPI service wrappers.

Specialized build adapters:

- User-provided FastAPI project with `api.py` and `Dockerfile`.
- YOLO plate recognition project.
- RCAN super-resolution project.
- Real-ESRGAN super-resolution project.
- Generic generated fallback service.

Embedded service templates:

- `PLATE_SERVICE_API`: YOLO26 plate detection and recognition service.
- `RCAN_SERVICE_API`: RCAN image super-resolution service.
- `REALESRGAN_SERVICE_API`: Real-ESRGAN image super-resolution service.
- Generic fallback uses `MODEL_SERVICE_TEMPLATE` from `backend/app/services/model_service_template.py`.

When adding a new model adapter:

1. Add a clear detector in `_select_build_adapter()`.
2. Validate required files and reject Git LFS pointer weights.
3. Add a dedicated generated service API string or reusable project file.
4. Add a generated Dockerfile function if dependencies differ from the generic Dockerfile.
5. Ensure generated service exposes `GET /health`, `POST /predict`, and where applicable `POST /predict/image`.
6. Keep output compatible with frontend playground fields such as `processed_image`.

## Kubernetes Service Details

File:

- `backend/app/services/k8s_service.py`

Connection behavior:

- On service initialization, tries `K8S_CONFIG_PATH`, then in-cluster config, then default kube config.
- Caches connection state in `_connected`.
- `check_connection_async()` can reconnect and is used by system status and build distribution.

Deployment behavior:

- `deploy_model()` creates or replaces a Kubernetes Deployment and NodePort Service.
- K8s object names:
  - Deployment: `model-{model_id}-{deployment_name}`
  - Service: `{deployment_name}-svc` as created from the deployment name in `_wait_for_deployment`; actual service name returned is `model-{model_id}-{deployment_name}-svc`.
- Container name: `model`.
- Container image: `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:{build_id}` for new builds.
- `image_pull_policy` is `Never` when image starts with `ai-model:`, otherwise `IfNotPresent`.
- Pod specs include `imagePullSecrets` when `K8S_IMAGE_PULL_SECRET_NAME` is configured.
- Probes use `GET /health`.
- Service type is `NodePort`.
- Endpoint is built from the first non-control-plane node InternalIP and assigned NodePort.

Image distribution:

- New builds are pushed to the bundled registry and pulled by Kubernetes nodes.
- The bundled registry is unauthenticated by default, so no image pull secret is required unless an external private registry is configured.

Prerequisites for deployment:

- Backend container needs access to Docker socket and Docker CLI.
- Backend container needs kube config or in-cluster config.
- Backend host Docker daemon pushes through `localhost:5000`.
- K8s worker nodes need network access to `${REGISTRY_HOST_IP}:5000`.
- Because the bundled registry is HTTP, Kubernetes node Docker/containerd must allow `${REGISTRY_HOST_IP}:5000` as an insecure registry.

## Deployment Lifecycle

Deployment creation:

- API: `POST /api/v1/deployments`
- Requires model status `ready`.
- Requires `docker_image` and `docker_image_tag`.
- Creates a DB row only; it does not immediately create K8s resources.

Deploy to K8s:

- API: `POST /api/v1/deployments/{deployment_id}/deploy`
- Task ID: `deploy-{deployment_id}`
- Sets status `deploying`.
- Background function: `run_deploy_task()`.
- Calls `k8s_service.deploy_model()`.
- Updates DB with K8s Deployment name, Service name, endpoint, and status `running`.

Other deployment operations:

- `GET /api/v1/deployments/{id}/status`: live K8s status.
- `POST /api/v1/deployments/{id}/sync-status`: sync K8s pod status back to DB.
- `PUT /api/v1/deployments/{id}/scale?replicas=N`: scale K8s Deployment and update DB.
- `GET /api/v1/deployments/{id}/logs?tail_lines=N`: get first matching pod logs.
- `DELETE /api/v1/deployments/{id}`: delete DB row and best-effort delete K8s Deployment/Service.
- `GET /api/v1/deployments/k8s/list`: list K8s deployments managed by this app.

Deployment statuses:

- `pending`
- `deploying`
- `running`
- `failed`
- `stopped`

## WebSocket Progress

Backend:

- Endpoint: `/api/v1/ws/progress`
- Manager: `backend/app/core/websocket.py`
- Clients subscribe with:

```json
{"action": "subscribe", "task_id": "build-123"}
```

Messages:

```json
{
  "type": "progress",
  "task_id": "build-123",
  "progress": 50,
  "message": "Building Docker image...",
  "data": {}
}
```

The manager stores the latest progress per task, so late subscribers receive the current state immediately.

Frontend:

- `frontend/src/composables/useWebSocket.js`
- Connects to `/api/v1/ws/progress` using current page host.
- Reconnects automatically unless manually closed.
- Keeps a pending subscription set and resubscribes on reconnect.

## Proxy and Playground

Backend proxy:

- `GET /api/v1/proxy/deployments/{id}/health`
- `POST /api/v1/proxy/deployments/{id}/predict`
- `POST /api/v1/proxy/deployments/{id}/predict/image`

Proxy behavior:

- Reads deployment endpoint from DB.
- Forwards body and content type to deployed model service.
- Uses long timeout for prediction.
- Returns response content directly rather than forcing JSON parsing.

Frontend playground:

- `frontend/src/views/ModelPlayground.vue`
- Loads deployment and associated model.
- Chooses UI mode based on model type/name/source:
  - Image model mode for plate recognition and super-resolution.
  - Text mode for LLM-like types.
  - JSON mode fallback.
- Supports health check, JSON prediction, text prediction, image upload prediction, and displaying processed images.

## Frontend Architecture

Main files:

- `frontend/src/main.js`: Vue app setup.
- `frontend/src/App.vue`: root app wrapper.
- `frontend/src/router/index.js`: routes under `Layout`.
- `frontend/src/components/Layout.vue`: navigation shell and K8s connection display.
- `frontend/src/api/index.js`: Axios instance and API wrappers.
- `frontend/src/utils/formatters.js`: shared model/deployment status display and date formatting.

Views:

- `Dashboard.vue`: system counts, K8s state, quick actions, recent models.
- `Models.vue`: model listing, create/import/upload dialogs, build progress, reset/delete.
- `ModelDetail.vue`: single model details and config.
- `Deployments.vue`: deployment listing, create dialog, deploy progress, scale/delete.
- `DeploymentDetail.vue`: deployment details, endpoint, logs, status, scale, playground link.
- `ModelPlayground.vue`: inference testing for deployed model services.

Stores:

- `stores/models.js`: model list/detail/create/upload/build/delete/status/reset actions.
- `stores/deployments.js`: deployment list/detail/create/deploy/scale/delete/status/logs/K8s list actions.
- `stores/system.js`: system status and health.
- `stores/build.js`: build progress dialog/minimize state.

API client:

- Base URL: `/api/v1`.
- Upload/build/deploy operations use long timeouts.
- Multipart uploads use explicit `Content-Type: multipart/form-data`.

## Data and Artifact Handling

Treat `data/` as runtime state:

- `data/models.db`: SQLite database.
- `data/models/`: uploaded/extracted/imported model projects and weights.
- `data/builds/`: temporary Docker build contexts.
- `data/images/`: exported model image tar files.

Do not broadly scan or edit `data/` unless the user asks about a specific model asset. It can contain large archives, model weights, extracted third-party repositories, and generated images.

When deleting a model through the API:

- Source files are removed if they exist.
- Original archive is removed if present.
- GitHub clone parent directory is removed when applicable.
- Docker image is removed if image metadata is present.
- DB row is deleted.

## Git and Workspace Notes

Current environment caveat:

- `/root/new_demo/.git` may be a read-only tmpfs mount managed by the environment.
- Standard `git status` may fail if that mount is present.
- A previous push used `/tmp/new_demo_git` as Git metadata with `--git-dir=/tmp/new_demo_git --work-tree=/root/new_demo`.
- If normal Git operations fail with `.git` read-only errors, inspect with:

```bash
findmnt /root/new_demo/.git
```

Do not commit:

- `.env`
- `data/`
- model weights
- image tar files
- local caches
- dependency directories

`.gitignore` is already configured for these.

Remote used previously:

```text
git@github.com:fivefiveopen99/AI-Model-Deployer.git
```

## Verification Checklist

Backend syntax:

```bash
python3 -m py_compile \
  backend/app/main.py \
  backend/app/api/models.py \
  backend/app/api/deployments.py \
  backend/app/api/proxy.py \
  backend/app/api/system.py \
  backend/app/api/websocket.py \
  backend/app/core/config.py \
  backend/app/core/websocket.py \
  backend/app/models/database.py \
  backend/app/models/schemas.py \
  backend/app/services/docker_service.py \
  backend/app/services/k8s_service.py \
  backend/app/services/model_service_template.py
```

Compose config:

```bash
docker compose config
docker compose config --services
```

Frontend production build through Docker:

```bash
docker compose build frontend
```

Frontend local build:

```bash
cd frontend
npm install
npm run build
```

Note: local `npm run build` requires `frontend/node_modules`. In this workspace, Docker build has been the reliable validation path.

## Development Rules for Future Agents

- Read existing code paths before changing behavior.
- Prefer existing routers, services, schemas, stores, and formatters over introducing parallel abstractions.
- Keep model build and K8s deploy workflows consistent with WebSocket progress updates.
- If changing model statuses, account for existing SQLite enum values and frontend display mappings.
- If changing image distribution, inspect both `run_build_task()` and `DockerService.push_image_to_registry()`.
- If changing generated model services, verify they expose `/health` and compatible prediction endpoints.
- Do not reintroduce node-side image import distribution unless explicitly requested.
- Do not edit extracted third-party model repos under `data/models/*/extracted` unless the task explicitly targets them.
- Do not delete code only because it looks unused without checking references and runtime hooks.
- Ask before destructive cleanup of runtime artifacts, images, containers, volumes, or model data.
