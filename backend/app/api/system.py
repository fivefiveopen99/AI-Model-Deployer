from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
import os
import tempfile
import aiofiles
import uuid

from app.models.database import get_db, AIModel, Deployment, DeployStatus
from app.models.schemas import SystemStatus, BuildResponse
from app.services.docker_service import docker_service
from app.services.k8s_service import k8s_service
from app.services.nfs_service import (
    NFSDiscoveryError,
    discover_nfs_config,
    get_nfs_browse_root,
    resolve_nfs_browse_path,
)

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


@router.get("/nfs/directories")
async def list_nfs_directories(path: str = ""):
    """列出 NFS 导出目录下的子目录。"""
    try:
        nfs_config = discover_nfs_config()
        root = get_nfs_browse_root()
        current_dir = resolve_nfs_browse_path(path)
    except NFSDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    directories = []
    for name in sorted(os.listdir(current_dir)):
        full_path = os.path.join(current_dir, name)
        if not os.path.isdir(full_path):
            continue
        relative_item_path = os.path.relpath(full_path, root).replace("\\", "/")
        directories.append({
            "name": name,
            "path": "" if relative_item_path == "." else relative_item_path
        })

    current_relative_path = os.path.relpath(current_dir, root).replace("\\", "/")
    current_relative_path = "" if current_relative_path == "." else current_relative_path
    parent_path = None
    if current_dir != root:
        parent_relative_path = os.path.relpath(os.path.dirname(current_dir), root).replace("\\", "/")
        parent_path = "" if parent_relative_path == "." else parent_relative_path

    return {
        "root_path": root,
        "server": nfs_config["server"],
        "export_root": nfs_config["export_root"],
        "showmount_host": nfs_config["showmount_host"],
        "discovery_source": nfs_config["source"],
        "current_path": current_relative_path,
        "parent_path": parent_path,
        "directories": directories
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


@router.post("/registry-images/build", response_model=BuildResponse)
async def build_registry_image(
    background_tasks: BackgroundTasks,
    dockerfile_content: str = Form(...)
):
    """直接根据 Dockerfile 构建镜像并推送到私有仓库，不创建模型记录。"""
    if not dockerfile_content.strip():
        raise HTTPException(status_code=400, detail="Dockerfile 不能为空")
    if not docker_service.is_connected:
        raise HTTPException(status_code=503, detail="Docker service not available")

    task_id = f"registry-build-{uuid.uuid4().hex[:12]}"
    background_tasks.add_task(
        run_registry_build_task,
        task_id=task_id,
        dockerfile_content=dockerfile_content
    )

    return BuildResponse(
        task_id=task_id,
        message="Registry image build task started, please check progress via WebSocket"
    )


async def run_registry_build_task(task_id: str, dockerfile_content: str):
    from app.core.websocket import manager

    try:
        async def progress_callback(progress: int, message: str, data: dict = None, persist_status: bool = True):
            await manager.send_progress(task_id, progress, message, data)

        await progress_callback(5, "Starting Dockerfile build...")
        build_result = await docker_service.build_model_image(
            model_id=0,
            model_name="dockerfile-build",
            model_type="custom",
            source_path="",
            source_type="file",
            config={
                "runtime_spec": {
                    "dockerfile_content": dockerfile_content
                }
            },
            progress_callback=progress_callback
        )

        await progress_callback(85, "Build completed, publishing image to registry...")

        push_result = await docker_service.push_image_to_registry(
            build_result["image_tag"],
            progress_callback=progress_callback
        )
        registry_image = push_result["registry_image"]
        await progress_callback(100, "Build and registry push completed!", {
            "registry_image": registry_image,
            "image_tag": build_result["image_tag"]
        })
    except Exception as e:
        await manager.send_progress(task_id, 0, f"Build failed: {str(e)}", {"error": True})
