from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
import os
import tempfile
import aiofiles

from app.models.database import get_db, AIModel, Deployment, DeployStatus
from app.models.schemas import SystemStatus
from app.services.docker_service import docker_service
from app.services.k8s_service import k8s_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """获取系统状态"""
    # 获取统计数据
    models_result = await db.execute(select(func.count()).select_from(AIModel))
    total_models = models_result.scalar()
    
    deployments_result = await db.execute(select(func.count()).select_from(Deployment))
    total_deployments = deployments_result.scalar()
    
    running_result = await db.execute(
        select(func.count()).select_from(Deployment).where(Deployment.status == DeployStatus.RUNNING)
    )
    running_deployments = running_result.scalar()
    
    # 异步检查 K8s 连接，避免阻塞
    k8s_connected = await k8s_service.check_connection_async()
    
    return SystemStatus(
        docker_connected=docker_service.is_connected,
        k8s_connected=k8s_connected,
        total_models=total_models,
        total_deployments=total_deployments,
        running_deployments=running_deployments
    )


@router.get("/health")
async def health_check():
    """健康检查"""
    # 异步检查 K8s 连接
    k8s_connected = await k8s_service.check_connection_async()
    return {
        "status": "healthy",
        "docker": docker_service.is_connected,
        "kubernetes": k8s_connected
    }


@router.get("/registry-images")
async def get_registry_images():
    """获取私有仓库中的全部镜像列表。"""
    try:
        return await docker_service.list_registry_images()
    except Exception as e:
        return {
            "registry_url": "",
            "registry_host": "",
            "namespace_prefix": None,
            "total_repositories": 0,
            "total_tags": 0,
            "items": [],
            "error": str(e)
        }


@router.delete("/registry-images")
async def delete_registry_image(repository: str, tag: str):
    """删除私有仓库中的单个镜像标签。"""
    try:
        return await docker_service.delete_registry_image(repository, tag)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/registry-images/upload")
async def upload_registry_image(
    repository: str = Form(...),
    tag: str = Form(...),
    file: UploadFile = File(...)
):
    """上传本地 docker save 导出的镜像 tar 并推送到私有仓库。"""
    suffix = os.path.splitext(file.filename or "image.tar")[1] or ".tar"
    fd, temp_path = tempfile.mkstemp(prefix="registry-upload-", suffix=suffix)
    os.close(fd)

    try:
        async with aiofiles.open(temp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        return await docker_service.upload_image_tar_to_registry(
            tar_path=temp_path,
            repository=repository,
            tag=tag
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


@router.get("/registry-images/local-packages")
async def list_local_registry_image_packages(path: str = ""):
    """列出后端可见目录下的本地镜像包。"""
    try:
        return await docker_service.list_local_image_archives(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/registry-images/upload-local")
async def upload_local_registry_image(
    repository: str = Form(...),
    tag: str = Form(...),
    package_path: str = Form(...)
):
    """将后端可见目录中的镜像包直接推送到私有仓库。"""
    try:
        return await docker_service.upload_local_image_archive_to_registry(
            package_path=package_path,
            repository=repository,
            tag=tag
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
