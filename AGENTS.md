# Project Context for Codex

This repository is an AI model packaging and deployment platform. Use this file as the first project map in future conversations.

## Overview

- Product: AI Model Deployer, a web platform for uploading or importing AI models, building Docker images for them, exporting images, and deploying them to Kubernetes.
- Backend: FastAPI async API in `backend/app`.
- Frontend: Vue 3 + Vite + Pinia + Element Plus in `frontend`.
- Runtime orchestration: `docker-compose.yml` starts backend, frontend, and Redis.
- Data directory: `data/` stores SQLite DB, uploaded/extracted models, build artifacts, and image tar files. Treat it as runtime/generated data and avoid broad scans or edits unless the task is explicitly about model assets.

## Important Paths

- `backend/app/main.py`: FastAPI app creation, CORS, startup DB initialization, API router registration.
- `backend/app/core/config.py`: environment-backed settings and storage path creation.
- `backend/app/models/database.py`: SQLAlchemy async engine, ORM tables, status enums.
- `backend/app/models/schemas.py`: Pydantic request/response schemas.
- `backend/app/api/models.py`: model CRUD, upload/import, build task orchestration, status/reset/delete endpoints.
- `backend/app/api/deployments.py`: deployment CRUD, K8s deploy/scale/log/sync/delete endpoints.
- `backend/app/api/system.py`: system health/status.
- `backend/app/api/websocket.py` and `backend/app/core/websocket.py`: task progress WebSocket plumbing.
- `backend/app/api/proxy.py`: proxy routes for deployed model services.
- `backend/app/services/docker_service.py`: Docker availability, model type detection, build context generation, image build/publish/export, embedded service templates for YOLO plate recognition, RCAN, and Real-ESRGAN.
- `backend/app/services/k8s_service.py`: Kubernetes client connection, Deployment/Service creation, rollout wait, scale, logs, delete, list.
- `frontend/src/api/index.js`: Axios client and API wrappers.
- `frontend/src/stores/`: Pinia stores for models, deployments, system status, and build/progress state.
- `frontend/src/views/`: UI pages for dashboard, model management/detail/playground, deployments/detail.
- `docker-compose.yml`: container wiring, ports, volumes, Redis, Docker socket, kube/ssh mounts, and key environment variables.

## Local Development

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Full stack:

```bash
docker compose up -d
```

Default URLs:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/api/v1/docs`

## Configuration Notes

- `.env.example` documents expected environment variables; `.env` may contain machine-specific values and should not be casually rewritten.
- Main backend defaults are in `backend/app/core/config.py`.
- SQLite DB default: `sqlite+aiosqlite:///./data/models.db`.
- Model storage default: `./data/models`.
- Build context default: `./data/builds`.
- Local image tar storage default: `./data/images`.
- Image distribution exports a tar and imports it into K8s nodes over SSH/SCP.
- Kubernetes config comes from `K8S_CONFIG_PATH`, in-cluster config, or default kube config.

## Behavioral Notes

- Model statuses include `pending`, `uploading`, `uploaded`, `building`, `built`, `pushing`, `ready`, and `failed`.
- Deployment statuses include `pending`, `deploying`, `running`, `failed`, and `stopped`.
- Models must be `ready` and have Docker image metadata before deployments can be created.
- Long-running builds and deployments are started as FastAPI background tasks; progress is sent over WebSocket using task IDs such as `build-{model_id}` and `deploy-{deployment_id}`.
- Uploaded archives can be `.zip`, `.tar.gz`, `.tgz`, or `.tar`; extraction and model file auto-detection happen in `backend/app/api/models.py`.
- GitHub URL import uses shallow `git clone`; repositories with Git LFS require `git-lfs` in the backend environment.
- K8s deployments create a Deployment plus a NodePort Service and use `/health` probes.
- Generated model service images are expected to expose FastAPI endpoints such as `/health`, `/predict`, and often `/predict/image`.

## Development Guidance

- Prefer existing backend patterns: FastAPI routers under `backend/app/api`, async SQLAlchemy sessions from `get_db`, and Pydantic schemas in `backend/app/models/schemas.py`.
- Prefer existing frontend patterns: API wrappers in `frontend/src/api/index.js`, Pinia stores in `frontend/src/stores`, Vue views under `frontend/src/views`, Element Plus components/icons.
- Be careful with `data/`: it contains large model archives, extracted third-party repos, weights, images, and the SQLite database.
- Avoid editing vendored or extracted model repositories under `data/models/*/extracted` unless the task explicitly targets them.
- The workspace currently may not be a Git repository; check before relying on git commands.
- Do not assume Docker, Kubernetes, or network access is available in the current environment without checking.
- If changing build/deploy behavior, inspect both backend task orchestration and the frontend progress/status UI.
