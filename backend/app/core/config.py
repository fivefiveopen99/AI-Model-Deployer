from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Model Deployer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/models.db"
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Docker Registry Configuration
    DOCKER_REGISTRY_URL: str = "10.10.25.69:5000/ai-models"
    DOCKER_REGISTRY_PUSH_URL: Optional[str] = "localhost:5000/ai-models"
    DOCKER_REGISTRY_USERNAME: str = ""
    DOCKER_REGISTRY_PASSWORD: str = ""
    
    # Kubernetes
    K8S_CONFIG_PATH: Optional[str] = None
    K8S_NAMESPACE: str = "default"
    K8S_IMAGE_PULL_SECRET_NAME: Optional[str] = ""
    K8S_NFS_SERVER: str = ""
    K8S_NFS_EXPORT_ROOT: str = ""
    K8S_NFS_BROWSE_ROOT: str = ""
    K8S_NFS_SHOWMOUNT_HOST: str = ""
    
    # Model Storage
    MODEL_STORAGE_PATH: str = "./data/models"
    BUILD_CONTEXT_PATH: str = "./data/builds"
    LOCAL_IMAGE_ARCHIVE_PATH: str = "./data/images"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"


settings = Settings()

os.makedirs(settings.MODEL_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.BUILD_CONTEXT_PATH, exist_ok=True)
os.makedirs(settings.LOCAL_IMAGE_ARCHIVE_PATH, exist_ok=True)
