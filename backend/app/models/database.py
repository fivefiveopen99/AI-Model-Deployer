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
    model_id = Column(Integer, nullable=False)
    
    # K8s配置
    namespace = Column(String(100), default="default")
    replicas = Column(Integer, default=1)
    resources = Column(JSON, default=dict)  # CPU, Memory, GPU配置
    env_vars = Column(JSON, default=dict)
    
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


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
