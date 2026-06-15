# OG-MAP

AI模型打包部署平台 - 支持将AI模型打包成Docker镜像并部署到Kubernetes集群。

## 功能特性

- **模型管理**: 支持本地文件、URL、HuggingFace等多种模型来源
- **自动打包**: 自动构建Docker镜像，内置FastAPI服务模板
- **K8s部署**: 一键部署到Kubernetes，支持扩缩容
- **Web界面**: 直观的前端管理界面

## 项目结构

```
ai-model-deployer/
├── backend/              # FastAPI后端服务
│   ├── app/
│   │   ├── api/         # API路由
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   ├── services/    # 业务逻辑 (Docker/K8s)
│   │   └── main.py      # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # Vue3前端
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   ├── stores/      # Pinia状态管理
│   │   └── api/         # API接口
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml   # Docker Compose配置
└── README.md
```

## 用户文档

- [用户文档目录](docs/README.md): 面向项目使用者、部署人员和维护人员。
- [使用与运维说明](docs/usage-and-operations.md): 环境准备、启动配置、典型工作流、验证命令和常见排障。
- [源代码说明](docs/source-code-guide.md): 源码目录、模块职责、常见改动入口和维护边界。
- [模型项目 FastAPI/Docker 打包说明](docs/model-projects-fastapi-docker.md): 模型适配器、生成服务契约和最小上传结构，作为开发维护进阶参考。

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Kubernetes集群 (可选，用于部署功能)
- Python 3.11+ (本地开发)
- Node.js 18+ (本地开发)

### 2. 使用Docker Compose启动

```bash
# 克隆项目
cd ai-model-deployer

# 复制环境变量配置
cp .env.example .env
# 编辑 .env 文件，配置你的 K8s 和 Registry 参数

# 启动服务
docker-compose up -d

# 访问前端 http://localhost:5173
# API文档 http://localhost:8000/api/v1/docs
```

### 3. 本地开发

**后端:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

## 使用流程

1. **添加模型**: 在模型管理页面添加AI模型（支持文件上传、URL、HuggingFace）
2. **构建镜像**: 选择模型，点击构建，系统会自动生成Docker镜像
3. **创建部署**: 在部署管理页面创建部署配置
4. **部署到K8s**: 点击部署按钮，模型服务将部署到Kubernetes集群
5. **扩缩容**: 支持动态调整副本数

## API接口

### 模型管理
- `GET /api/v1/models` - 获取模型列表
- `POST /api/v1/models` - 创建模型
- `POST /api/v1/models/upload` - 上传模型文件
- `POST /api/v1/models/{id}/build` - 构建Docker镜像

### 部署管理
- `GET /api/v1/deployments` - 获取部署列表
- `POST /api/v1/deployments` - 创建部署
- `POST /api/v1/deployments/{id}/deploy` - 部署到K8s
- `PUT /api/v1/deployments/{id}/scale` - 扩缩容

### 系统状态
- `GET /api/v1/system/status` - 获取系统状态
- `GET /api/v1/system/health` - 健康检查

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| REGISTRY_HOST_IP | 部署节点对 Kubernetes 节点可访问的 IP，部署到不同节点时修改此值 | 127.0.0.1 |
| DOCKER_REGISTRY_URL | 内置 Docker Registry 仓库地址 | ${REGISTRY_HOST_IP}:5000/ai-models |
| DOCKER_REGISTRY_PUSH_URL | 后端 Docker daemon 推送地址 | localhost:5000/ai-models |
| DOCKER_REGISTRY_USERNAME | Registry 推送账号，内置 registry 默认留空 | 空 |
| DOCKER_REGISTRY_PASSWORD | Registry 推送密码，内置 registry 默认留空 | 空 |
| K8S_CONFIG_PATH | K8s配置文件路径 | ~/.kube/config |
| K8S_NAMESPACE | 默认命名空间 | default |
| K8S_IMAGE_PULL_SECRET_NAME | K8s 拉取私有镜像的 Secret 名称，内置 registry 默认留空 | 空 |

Compose 会启动一个 `registry:2` 服务并通过宿主机 `5000` 端口暴露。部署前在 `.env` 中设置 `REGISTRY_HOST_IP` 为当前部署节点对 Kubernetes 节点可访问的 IP。后端 Docker daemon 通过 `localhost:5000/ai-models` 推送镜像，模型部署记录使用 `${REGISTRY_HOST_IP}:5000/ai-models/ai-model:<build_id>`。这是 HTTP registry，K8s 节点的容器运行时需要把 `${REGISTRY_HOST_IP}:5000` 配置为 insecure registry。

## 支持的模型类型

- **LLaMA**: 大语言模型
- **GPT**: GPT系列模型
- **BERT**: BERT系列模型
- **Custom**: 自定义模型

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Docker SDK, Kubernetes Python Client
- **前端**: Vue3, Element Plus, Pinia, Axios
- **数据库**: SQLite (可扩展为PostgreSQL)
- **缓存**: Redis

## License

MIT
