# 源代码说明

本文档面向需要阅读或修改 OG-MAP 代码的开发者，说明主要源码入口、职责边界和常见改动路径。运行数据、模型权重、构建产物和依赖目录不属于源码范围。

## 顶层入口

- `backend/`: FastAPI 后端，负责数据库状态、模型导入、镜像构建、Registry、Kubernetes、NFS 和代理转发。
- `frontend/`: Vue 3 前端，负责控制台页面、表单、长任务进度、部署管理和推理工作台。
- `docker-compose.yml`: 本地/服务器运行编排，启动 backend、frontend、redis、registry。
- `.env.example`: 运行配置模板，重点是 Registry、Kubernetes、NFS 和代理配置。
- `docs/`: 使用、运维、模型打包和源码说明文档。

## 后端结构

### 应用与配置

- `backend/app/main.py`
  - 创建 FastAPI 应用。
  - 初始化数据库表。
  - 注册 `models`、`deployments`、`system`、`proxy`、`websocket` 路由。
  - 配置 CORS 和全局异常处理。
- `backend/app/core/config.py`
  - 读取环境变量。
  - 维护数据库、Registry、Kubernetes、NFS、模型存储和构建目录配置。
- `backend/app/core/websocket.py`
  - 管理 WebSocket 客户端订阅。
  - 缓存任务最新进度和日志，供前端刷新后恢复。

### 数据模型

- `backend/app/models/database.py`
  - SQLAlchemy async engine/session。
  - 定义 `AIModel`、`Deployment`、`ModelStatus`、`DeployStatus`。
  - 启动时自动创建表，并为 SQLite 补齐新增列。
- `backend/app/models/schemas.py`
  - Pydantic 请求和响应模型。
  - 覆盖模型、部署、构建任务、命令推理和系统状态。

### API 路由

- `backend/app/api/models.py`
  - 模型创建、上传、URL/GitHub 导入。
  - 模型文件识别和 Git LFS 指针校验。
  - Docker 镜像构建、停止构建、重置状态、删除模型。
- `backend/app/api/deployments.py`
  - 创建模型部署或已有镜像部署。
  - 部署到 Kubernetes、扩缩容、日志、状态同步、删除。
  - 命令式推理、结果预览、单文件下载和结果打包下载。
- `backend/app/api/system.py`
  - 系统状态、健康检查、NFS 目录浏览。
  - Registry 镜像列表、删除、上传 tar、从本地包上传、Dockerfile 构建。
- `backend/app/api/proxy.py`
  - 将 playground 请求转发到已部署模型服务。
  - 转发健康检查、JSON 推理和图片推理。
- `backend/app/api/websocket.py`
  - 暴露 `/api/v1/ws/progress`。
  - 支持订阅、取消订阅和 ping。

### 服务层

- `backend/app/services/docker_service.py`
  - Docker CLI 检查。
  - 准备构建上下文、生成 Dockerfile 和服务包装代码。
  - 选择模型适配器并构建镜像。
  - 推送镜像到 Registry，查询/删除 Registry 镜像。
  - 上传镜像 tar 并重新打 tag 推送。
- `backend/app/services/k8s_service.py`
  - Kubernetes 连接和重连。
  - 创建/替换 Deployment 和 NodePort Service。
  - 扩缩容、读取日志、删除资源、列出托管部署。
  - 支持 Pod exec 和容器结果文件读取。
- `backend/app/services/inference_service.py`
  - 解析和渲染命令模板变量。
  - 规范化命令推理配置。
  - 扫描、分类、预览和定位结果文件。
- `backend/app/services/nfs_service.py`
  - 发现 NFS 配置。
  - 解析可浏览目录并做越界保护。
- `backend/app/services/model_service_template.py`
  - 通用 FastAPI 模型服务模板。
  - Docker fallback 构建路径会把它写入构建上下文。

## 前端结构

### 入口和布局

- `frontend/src/main.js`
  - 创建 Vue 应用。
  - 注册 Pinia、Vue Router、Element Plus 和图标库。
- `frontend/src/App.vue`
  - 根组件。
- `frontend/src/router/index.js`
  - 定义总览、模型、镜像、部署、详情、命令工作台和 playground 路由。
- `frontend/src/components/Layout.vue`
  - 主导航、顶部栏、移动端抽屉和 K8s 状态显示。

### API、状态和实时进度

- `frontend/src/api/index.js`
  - Axios 实例。
  - 按 `modelsApi`、`deploymentsApi`、`systemApi` 分组封装后端接口。
- `frontend/src/stores/models.js`
  - 模型列表、详情、导入、上传、构建、停止、重置和删除。
- `frontend/src/stores/deployments.js`
  - 部署列表、详情、创建、部署、扩缩容、日志、命令推理和结果文件操作。
- `frontend/src/stores/system.js`
  - 系统状态。
- `frontend/src/stores/build.js`
  - 模型构建进度弹窗和刷新恢复状态。
- `frontend/src/stores/registryBuild.js`
  - Registry Dockerfile 构建进度弹窗和刷新恢复状态。
- `frontend/src/composables/useWebSocket.js`
  - 连接 `/api/v1/ws/progress`。
  - 自动重连并恢复任务订阅。

### 页面

- `frontend/src/views/Dashboard.vue`
  - 系统状态、统计信息、快速入口和近期记录。
- `frontend/src/views/Models.vue`
  - 模型导入、上传、构建、停止、重置和删除。
- `frontend/src/views/ModelDetail.vue`
  - 模型基础信息、镜像信息和配置 JSON。
- `frontend/src/views/RegistryImages.vue`
  - Registry 镜像列表、上传镜像包、本地镜像包推送、Dockerfile 构建和删除 tag。
- `frontend/src/views/Deployments.vue`
  - 创建模型服务部署或已有镜像部署，配置资源、环境变量、NFS 挂载和命令模板。
- `frontend/src/views/DeploymentDetail.vue`
  - 部署状态、入口、日志、扩缩容、资源和命令推理 API 示例。
- `frontend/src/views/DeploymentInference.vue`
  - 已有镜像部署的命令推理工作台，包含变量填写、流式日志、预览和下载。
- `frontend/src/views/ModelPlayground.vue`
  - 服务型模型的 HTTP 交互测试，支持 JSON、文本和图片请求。

### UI 辅助

- `frontend/src/components/ui/*.vue`
  - 页面标题、指标卡、面板、空状态和代码块。
- `frontend/src/utils/formatters.js`
  - 状态文本、状态标签、日期和镜像引用格式化。
- `frontend/src/styles/theme.css`
  - 全局主题变量、布局样式和 Element Plus 覆盖。

## 常见改动入口

- 修改模型导入或构建流程：
  - `backend/app/api/models.py`
  - `backend/app/services/docker_service.py`
  - `frontend/src/views/Models.vue`
  - `frontend/src/stores/models.js`
- 新增模型构建适配器：
  - `backend/app/services/docker_service.py`
  - `backend/app/services/model_service_template.py`
  - `docs/model-projects-fastapi-docker.md`
- 修改部署资源、服务或 K8s 行为：
  - `backend/app/api/deployments.py`
  - `backend/app/services/k8s_service.py`
  - `frontend/src/views/Deployments.vue`
  - `frontend/src/views/DeploymentDetail.vue`
- 修改命令式推理和结果文件处理：
  - `backend/app/api/deployments.py`
  - `backend/app/services/inference_service.py`
  - `backend/app/services/k8s_service.py`
  - `frontend/src/views/DeploymentInference.vue`
  - `frontend/src/stores/deployments.js`
- 修改 Registry 镜像管理：
  - `backend/app/api/system.py`
  - `backend/app/services/docker_service.py`
  - `frontend/src/views/RegistryImages.vue`
  - `frontend/src/stores/registryBuild.js`
- 修改系统状态或导航：
  - `backend/app/api/system.py`
  - `frontend/src/stores/system.js`
  - `frontend/src/components/Layout.vue`
  - `frontend/src/views/Dashboard.vue`

## 维护边界

- 不要把 `data/`、模型权重、镜像 tar、依赖目录和构建产物当作源码提交。
- 不要随意重命名模型状态，尤其是 `pushing`，已有 SQLite 数据可能依赖它。
- 改 Registry 分发逻辑时，同时检查构建任务和 Kubernetes 拉取镜像地址。
- 改生成的模型服务时，保持 `/health`、`/predict` 和图片场景的 `/predict/image` 兼容。
- 改长任务流程时，同步检查 WebSocket 进度消息和前端恢复逻辑。
