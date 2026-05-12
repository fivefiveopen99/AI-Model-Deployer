from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ModelType(str, Enum):
    LLAMA = "llama"
    GPT = "gpt"
    BERT = "bert"
    CUSTOM = "custom"


class SourceType(str, Enum):
    FILE = "file"
    URL = "url"
    HUGGINGFACE = "huggingface"


class ModelStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    BUILDING = "building"
    BUILT = "built"
    PUSHING = "pushing"
    READY = "ready"
    FAILED = "failed"


class DeployStatus(str, Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model_type: ModelType
    source_type: SourceType
    source_path: str
    config: Dict[str, Any] = Field(default_factory=dict)


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ModelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    model_type: str
    source_type: str
    source_path: str
    config: Dict[str, Any]
    status: str
    status_message: Optional[str]
    docker_image: Optional[str]
    docker_image_tag: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelList(BaseModel):
    total: int
    items: List[ModelResponse]


class DeploymentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    model_id: Optional[int] = None
    source_type: str = Field(default="model")
    image: Optional[str] = None
    port: int = Field(default=8000, ge=1, le=65535)
    namespace: str = Field(default="default")
    replicas: int = Field(default=1, ge=1, le=100)
    resources: Dict[str, Any] = Field(default_factory=dict)
    env_vars: Dict[str, str] = Field(default_factory=dict)
    mount_config: Dict[str, Any] = Field(default_factory=dict)
    command: Optional[str] = None
    inference_config: Dict[str, Any] = Field(default_factory=dict)


class DeploymentUpdate(BaseModel):
    replicas: Optional[int] = Field(None, ge=0, le=100)
    resources: Optional[Dict[str, Any]] = None
    env_vars: Optional[Dict[str, str]] = None
    mount_config: Optional[Dict[str, Any]] = None
    command: Optional[str] = None
    inference_config: Optional[Dict[str, Any]] = None


class DeploymentResponse(BaseModel):
    id: int
    name: str
    model_id: Optional[int]
    source_type: str
    image: Optional[str]
    access_mode: str
    access_path: Optional[str]
    access_label: Optional[str]
    port: int
    namespace: str
    replicas: int
    resources: Dict[str, Any]
    env_vars: Dict[str, str]
    mount_config: Dict[str, Any]
    command: Optional[str]
    inference_config: Dict[str, Any]
    last_inference_result: Dict[str, Any]
    inference_runtime: Dict[str, Any] = Field(default_factory=dict)
    status: str
    status_message: Optional[str]
    k8s_deployment_name: Optional[str]
    k8s_service_name: Optional[str]
    endpoint: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentList(BaseModel):
    total: int
    items: List[DeploymentResponse]


class BuildRequest(BaseModel):
    base_image: Optional[str] = "python:3.11-slim"
    build_node: Optional[str] = "local"


class BuildResponse(BaseModel):
    task_id: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: Optional[str]
    result: Optional[Dict[str, Any]] = None


class InferenceRunRequest(BaseModel):
    variables: Dict[str, str] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    docker_connected: bool
    k8s_connected: bool
    total_models: int
    total_deployments: int
    running_deployments: int
