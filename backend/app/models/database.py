from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, JSON
from datetime import datetime
import enum

from app.core.config import settings

Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class ModelStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    BUILDING = "building"
    BUILT = "built"
    PUSHING = "pushing"
    READY = "ready"
    FAILED = "failed"


class DeployStatus(str, enum.Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


class AIModel(Base):
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model_type = Column(String(50), nullable=False)  # llama, gpt, custom, etc.
    source_type = Column(String(50), nullable=False)  # file, url, huggingface
    source_path = Column(String(500), nullable=False)  # 本地路径或URL
    
    # 配置
    config = Column(JSON, default=dict)  # 模型配置参数
    
    # 状态
    status = Column(Enum(ModelStatus), default=ModelStatus.PENDING)
    status_message = Column(Text, nullable=True)
    
    # Docker镜像信息
    docker_image = Column(String(255), nullable=True)
    docker_image_tag = Column(String(100), nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    model_id = Column(Integer, nullable=False, default=0)
    source_type = Column(String(50), nullable=False, default="model")
    image = Column(String(500), nullable=True)
    port = Column(Integer, nullable=False, default=8000)
    
    # K8s配置
    namespace = Column(String(100), default="default")
    replicas = Column(Integer, default=1)
    resources = Column(JSON, default=dict)  # CPU, Memory, GPU配置
    env_vars = Column(JSON, default=dict)
    mount_config = Column(JSON, default=dict)
    command = Column(Text, nullable=True)
    inference_config = Column(JSON, default=dict)
    last_inference_result = Column(JSON, default=dict)
    
    # 状态
    status = Column(Enum(DeployStatus), default=DeployStatus.PENDING)
    status_message = Column(Text, nullable=True)
    
    # K8s信息
    k8s_deployment_name = Column(String(255), nullable=True)
    k8s_service_name = Column(String(255), nullable=True)
    endpoint = Column(String(500), nullable=True)  # 访问地址
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.get_backend_name() == "sqlite":
            await _ensure_sqlite_columns(conn)


async def _ensure_sqlite_columns(conn):
    result = await conn.exec_driver_sql("PRAGMA table_info(deployments)")
    columns = {row[1] for row in result.fetchall()}

    if "source_type" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN source_type VARCHAR(50) NOT NULL DEFAULT 'model'")
    if "image" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN image VARCHAR(500)")
    if "port" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN port INTEGER NOT NULL DEFAULT 8000")
    if "mount_config" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN mount_config JSON")
    if "command" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN command TEXT")
    if "inference_config" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN inference_config JSON")
    if "last_inference_result" not in columns:
        await conn.exec_driver_sql("ALTER TABLE deployments ADD COLUMN last_inference_result JSON")


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
