# 使用与运维说明

本文档面向部署、使用和日常维护 OG-MAP 的人员，说明环境准备、启动配置、主要工作流和常见排障方式。

## 环境要求

基础运行：

- Docker
- Docker Compose
- 可访问的宿主机 Docker socket

使用 Kubernetes 部署功能还需要：

- Kubernetes 集群。
- 后端容器可读取 kubeconfig，或运行在集群内。
- Kubernetes 节点可以访问 `${REGISTRY_HOST_IP}:5000`。
- 节点容器运行时允许 `${REGISTRY_HOST_IP}:5000` 作为 HTTP insecure registry。

使用 NFS 命令推理还需要：

- 后端容器安装并可运行 `showmount`，镜像中已安装 `nfs-common`。
- 后端容器能浏览 NFS 导出目录，Compose 默认挂载 `/share:/share:ro`。
- Kubernetes 节点可挂载同一个 NFS server/export。

## 快速启动

1. 复制配置文件：

```bash
cp .env.example .env
```

2. 编辑 `.env`，至少确认：

```text
REGISTRY_HOST_IP=<Kubernetes 节点可访问的后端/Registry 宿主机 IP>
K8S_CONFIG_PATH=/root/.kube/config
K8S_NAMESPACE=default
```

3. 启动：

```bash
docker compose up -d
```

4. 访问：

- Web UI: `http://localhost:5173`
- API docs: `http://localhost:8000/api/v1/docs`
- Registry: `http://localhost:5000/v2/_catalog`

## 核心配置

### Registry

```text
REGISTRY_HOST_IP=127.0.0.1
DOCKER_REGISTRY_URL=${REGISTRY_HOST_IP}:5000/ai-models
DOCKER_REGISTRY_PUSH_URL=localhost:5000/ai-models
DOCKER_REGISTRY_USERNAME=
DOCKER_REGISTRY_PASSWORD=
```

- `DOCKER_REGISTRY_PUSH_URL`: 后端 Docker daemon 推送镜像使用。
- `DOCKER_REGISTRY_URL`: 存入数据库、交给 K8s 拉取使用。
- 内置 `registry:2` 默认无认证。
- 使用外部私有仓库时填写账号密码，并配置 K8s imagePullSecret。

### Kubernetes

```text
K8S_CONFIG_PATH=/root/.kube/config
K8S_NAMESPACE=default
K8S_IMAGE_PULL_SECRET_NAME=
```

- Compose 将宿主机 `~/.kube` 只读挂载到后端容器 `/root/.kube`。
- `K8S_IMAGE_PULL_SECRET_NAME` 默认留空，适合内置无认证 Registry。

### NFS

```text
K8S_NFS_SHOWMOUNT_HOST=
K8S_NFS_SERVER=
K8S_NFS_EXPORT_ROOT=
K8S_NFS_BROWSE_ROOT=
```

默认优先自动发现：

1. `K8S_NFS_SHOWMOUNT_HOST`
2. `K8S_NFS_SERVER`
3. Kubernetes control-plane 节点
4. `host.docker.internal`
5. `127.0.0.1`
6. `localhost`

如果自动发现失败，建议显式配置 `K8S_NFS_SERVER` 和 `K8S_NFS_EXPORT_ROOT`。

## 工作流一：上传模型并部署服务

1. 进入“模型管理”。
2. 选择 GitHub/URL 导入或压缩包上传。
3. 模型记录状态变为 `uploaded`。
4. 点击“构建”。
5. 后端会：
   - 创建临时 build context。
   - 复制/解压模型项目。
   - 选择特化适配器或生成通用 FastAPI 服务。
   - 执行 `docker build`。
   - 执行 `docker tag` 和 `docker push`。
   - 将模型状态更新为 `ready`。
6. 进入“部署管理”，创建“模型部署”。
7. 点击部署到 Kubernetes。
8. 部署成功后进入“交互测试”，调用 `/health`、`/predict` 或 `/predict/image`。

适配器和模型包装规则详见 `docs/model-projects-fastapi-docker.md`。

## 工作流二：使用已有镜像执行命令推理

适合已有镜像不提供 HTTP 服务、只提供命令行推理脚本的情况。

1. 进入“镜像仓库”。
2. 上传镜像：
   - 上传 `docker save` 导出的 `.tar`。
   - 或从后端 `data/images` 目录选择 `.tar`。
   - 或输入 Dockerfile 直接构建并推送。
3. 进入“部署管理”，创建“镜像部署”。
4. 选择 Registry 镜像。
5. 配置资源、环境变量和可选 NFS 挂载。
6. 配置命令模板，例如：

```bash
python infer.py --input {{input_path}} --output /data/results
```

7. 配置结果路径，例如：

```text
/data/results
```

8. 部署到 Kubernetes。
9. 进入“命令工作台”，填写模板变量并运行。
10. 查看流式日志、图片预览、文本预览，或下载结果文件。

如果结果路径位于 NFS 挂载目录内，后端会从宿主可见的 NFS browse root 读取结果；否则通过 Kubernetes exec 从容器读取结果。

## 工作流三：直接用 Dockerfile 构建 Registry 镜像

1. 进入“镜像仓库”。
2. 点击上传/构建。
3. 选择 Dockerfile 构建。
4. 填写 Dockerfile。
5. 提交后通过 WebSocket 查看构建日志。
6. 构建完成后镜像会推送到 Registry，并可用于镜像部署。

该流程不创建 `AIModel` 记录，适合已有工程镜像化或工具镜像准备。

## 本地开发

后端：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

Vite dev server 代理 `/api` 到 `http://localhost:8000`。

## 验证命令

后端语法检查：

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
  backend/app/services/inference_service.py \
  backend/app/services/nfs_service.py \
  backend/app/services/model_service_template.py
```

Compose 配置：

```bash
docker compose config
docker compose config --services
```

前端生产构建：

```bash
docker compose build frontend
```

本地前端构建：

```bash
cd frontend
npm run build
```

本地构建需要已安装 `frontend/node_modules`。

## 常见排障

### Docker 不可用

现象：

- 系统状态 Docker 离线。
- 构建接口返回 `Docker service not available`。

检查：

```bash
docker compose exec backend docker version
```

确认：

- `/var/run/docker.sock` 已挂载。
- `/usr/bin/docker` 已挂载且可执行。
- 后端容器有权限访问 Docker socket。

### Registry 推送失败

现象：

- 模型状态变为 `failed`。
- 状态消息包含 `Docker push failed` 或 Registry host 无法解析。

检查：

```bash
docker compose ps registry
curl http://localhost:5000/v2/_catalog
```

确认：

- `DOCKER_REGISTRY_PUSH_URL` 对后端 Docker daemon 可达。
- `DOCKER_REGISTRY_URL` 中的主机名/IP 对 Kubernetes 节点可达。
- 如果使用域名，后端容器能解析该域名。

### Kubernetes 拉取镜像失败

现象：

- 部署状态为 `ImagePullBackOff` 或 `ErrImagePull`。

确认：

- K8s 节点可以访问 `${REGISTRY_HOST_IP}:5000`。
- 节点容器运行时配置了 insecure registry。
- Deployment 中镜像地址是 `${REGISTRY_HOST_IP}:5000/ai-models/...`，不是仅容器内可访问的 `localhost`。
- 私有仓库认证场景已配置 `K8S_IMAGE_PULL_SECRET_NAME`。

### GitHub 导入后权重不可用

现象：

- API 返回 Git LFS 相关错误。
- 构建时权重文件非常小且内容是 LFS pointer。

处理：

- 确认后端镜像中有 git-lfs，当前 Dockerfile 已安装。
- 确认仓库 LFS 文件对当前网络和凭证可访问。
- 或上传已经包含真实权重文件的压缩包。

### NFS 目录发现失败

现象：

- 创建镜像部署时选择 NFS 目录失败。
- 返回 `Unable to discover NFS exports via showmount`。

处理：

- 显式配置 `K8S_NFS_SERVER` 和 `K8S_NFS_EXPORT_ROOT`。
- 确认后端容器内 `showmount -e <host>` 可执行。
- 确认 Compose 中后端能浏览对应目录，例如 `/share`。
- 确认 Kubernetes 节点也可以挂载该 NFS 导出。

### 命令推理没有结果文件

确认：

- 命令模板渲染后的路径正确。
- `result_path` 是推理命令实际写入的目录。
- 如果 `result_path` 在 NFS 挂载内，挂载目录和 NFS browse root 映射一致。
- 如果通过容器读取，镜像内有 `find`、`stat`、`wc`、`base64` 等基础命令。

### WebSocket 进度不更新

确认：

- 前端 nginx 配置代理了 `/api/v1/ws`。
- 浏览器连接的是当前 host 的 `/api/v1/ws/progress`。
- 任务 ID 是否正确：`build-{id}`、`deploy-{id}`、`infer-{id}` 或 `registry-build-{uuid}`。
- 后台任务是否已经失败，可查看后端日志。

## 数据备份和清理

需要备份：

- `data/models.db`
- `data/models/`
- `data/images/`
- Docker Registry volume `registry_data`

清理原则：

- 不要直接删除 `data/models/` 中仍被数据库引用的模型目录。
- 删除模型优先使用前端或 API，它会尝试清理源文件和 Docker 镜像。
- 删除部署优先使用前端或 API，它会尝试删除 K8s Deployment 和 Service。
- Registry 删除 tag 后，实际磁盘释放取决于 Registry 垃圾回收。

## 维护注意事项

- 修改模型状态枚举时，要兼容 SQLite 既有值，尤其是 `pushing`。
- 修改镜像分发逻辑时，同时检查 `backend/app/api/models.py` 和 `backend/app/services/docker_service.py`。
- 修改部署对象时，同时检查 `backend/app/services/k8s_service.py` 和前端部署表单。
- 修改命令推理结果格式时，同时检查 `backend/app/services/inference_service.py`、`backend/app/api/deployments.py` 和 `frontend/src/views/DeploymentInference.vue`。
- 新增模型适配器时，确保生成服务暴露 `/health`、`/predict`，图片模型暴露 `/predict/image`。
- 不要把 `data/`、模型权重、镜像 tar、依赖目录或构建产物提交到 Git。
