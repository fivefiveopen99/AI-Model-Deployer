from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Dict, Any
import os
import shutil
import aiofiles
import zipfile
import tarfile
import subprocess

from app.models.database import get_db, AIModel, ModelStatus
from app.models.schemas import (
    ModelCreate, ModelUpdate, ModelResponse, ModelList,
    BuildRequest, BuildResponse, TaskStatus
)
from app.services.docker_service import docker_service
from app.core.config import settings

router = APIRouter(prefix="/models", tags=["models"])


def extract_archive(archive_path: str, extract_to: str):
    """解压压缩文件"""
    if archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    elif archive_path.endswith(('.tar.gz', '.tgz')):
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_to)
    elif archive_path.endswith('.tar'):
        with tarfile.open(archive_path, 'r') as tar_ref:
            tar_ref.extractall(extract_to)


def find_model_files(directory: str) -> dict:
    """在目录中查找模型文件"""
    model_files = {
        'weights': None,
        'config': None,
        'requirements': None,
        'inference_script': None
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_lower = file.lower()
            filepath = os.path.join(root, file)
            
            # 查找权重文件
            if file_lower.endswith(('.pt', '.pth', '.onnx', '.engine', '.weights', '.safetensors')):
                if model_files['weights'] is None:
                    model_files['weights'] = filepath
            
            # 查找配置文件
            elif file_lower.endswith(('.yaml', '.yml', '.json')) and 'config' in file_lower:
                if model_files['config'] is None:
                    model_files['config'] = filepath
            
            # 查找 requirements.txt
            elif file_lower == 'requirements.txt':
                model_files['requirements'] = filepath
            
            # 查找推理脚本
            elif file_lower in ['detect.py', 'predict.py', 'inference.py', 'run.py']:
                if model_files['inference_script'] is None:
                    model_files['inference_script'] = filepath
    
    return model_files


def has_git_lfs_files(directory: str) -> bool:
    """检查仓库是否声明了 Git LFS 管理的文件。"""
    for root, _, files in os.walk(directory):
        if ".gitattributes" not in files:
            continue

        attributes_path = os.path.join(root, ".gitattributes")
        try:
            with open(attributes_path, "r", encoding="utf-8", errors="ignore") as f:
                if "filter=lfs" in f.read():
                    return True
        except OSError:
            continue

    return False


def is_git_lfs_pointer(file_path: str) -> bool:
    """判断模型权重是否还是 Git LFS 指针文件。"""
    try:
        if os.path.getsize(file_path) > 1024:
            return False

        with open(file_path, "rb") as f:
            header = f.read(256)
        return header.startswith(b"version https://git-lfs.github.com/spec")
    except OSError:
        return False


def find_git_lfs_pointers(directory: str) -> List[str]:
    """找出仍未被 Git LFS 替换成真实内容的模型文件。"""
    pointer_files = []
    model_exts = (".pt", ".pth", ".onnx", ".engine", ".weights", ".safetensors")

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.lower().endswith(model_exts):
                continue

            file_path = os.path.join(root, file)
            if is_git_lfs_pointer(file_path):
                pointer_files.append(os.path.relpath(file_path, directory))

    return pointer_files


def ensure_git_lfs_files(clone_dir: str):
    """如果仓库使用 Git LFS，拉取真实大文件并校验权重不再是指针。"""
    if not has_git_lfs_files(clone_dir):
        return

    lfs_version = subprocess.run(
        ["git", "lfs", "version"],
        capture_output=True,
        text=True,
        timeout=30
    )
    if lfs_version.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail="该仓库使用 Git LFS 管理模型权重，但后端环境未安装 git-lfs，无法拉取真实权重文件"
        )

    subprocess.run(
        ["git", "lfs", "install", "--local"],
        cwd=clone_dir,
        capture_output=True,
        text=True,
        timeout=30
    )

    lfs_pull = subprocess.run(
        ["git", "lfs", "pull"],
        cwd=clone_dir,
        capture_output=True,
        text=True,
        timeout=600
    )
    if lfs_pull.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Git LFS 权重拉取失败: {lfs_pull.stderr or lfs_pull.stdout}"
        )

    pointer_files = find_git_lfs_pointers(clone_dir)
    if pointer_files:
        raise HTTPException(
            status_code=400,
            detail=(
                "Git LFS 拉取完成后仍存在占位权重文件: "
                f"{', '.join(pointer_files)}。请确认仓库 LFS 文件可访问，或上传包含真实权重的压缩包"
            )
        )


@router.post("", response_model=ModelResponse)
async def create_model(
    model: ModelCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新的模型记录"""
    db_model = AIModel(
        name=model.name,
        description=model.description,
        model_type=model.model_type.value,
        source_type=model.source_type.value,
        source_path=model.source_path,
        config=model.config,
        status=ModelStatus.PENDING
    )
    
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    
    return db_model


@router.post("/upload", response_model=ModelResponse)
async def upload_model(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    model_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传模型压缩包（支持 zip, tar.gz, tar）"""
    # 创建模型目录
    model_dir = os.path.join(settings.MODEL_STORAGE_PATH, name.replace(" ", "_"))
    os.makedirs(model_dir, exist_ok=True)
    
    # 保存压缩文件
    archive_path = os.path.join(model_dir, file.filename)
    async with aiofiles.open(archive_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    # 解压文件
    extract_dir = os.path.join(model_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        extract_archive(archive_path, extract_dir)
        
        # 查找模型文件
        model_files = find_model_files(extract_dir)
        
        # 创建数据库记录
        db_model = AIModel(
            name=name,
            description=description,
            model_type=model_type,
            source_type="file",
            source_path=extract_dir,
            config={
                "original_archive": archive_path,
                "model_files": model_files,
                "auto_detected": True
            },
            status=ModelStatus.UPLOADED
        )
        
        db.add(db_model)
        await db.commit()
        await db.refresh(db_model)
        
        return db_model
        
    except Exception as e:
        # 清理目录
        shutil.rmtree(model_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"解压失败: {str(e)}")


@router.post("/from-url", response_model=ModelResponse)
async def create_model_from_url(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    model_type: str = Form(...),
    url: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """从 GitHub URL 或其他 URL 下载模型代码"""
    import httpx
    
    # 创建模型目录
    model_dir = os.path.join(settings.MODEL_STORAGE_PATH, name.replace(" ", "_"))
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        # 如果是 GitHub 仓库，使用 git clone
        if "github.com" in url:
            clone_dir = os.path.join(model_dir, "repo")
            if os.path.exists(clone_dir):
                shutil.rmtree(clone_dir, ignore_errors=True)
            
            # 执行 git clone
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, clone_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise HTTPException(status_code=400, detail=f"Git clone 失败: {result.stderr}")

            ensure_git_lfs_files(clone_dir)
            
            # 查找模型文件
            model_files = find_model_files(clone_dir)
            
            # 创建数据库记录
            db_model = AIModel(
                name=name,
                description=description,
                model_type=model_type,
                source_type="url",
                source_path=clone_dir,
                config={
                    "github_url": url,
                    "model_files": model_files,
                    "auto_detected": True
                },
                status=ModelStatus.UPLOADED
            )
        
        # 如果是直接的文件下载链接
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=60)
                response.raise_for_status()
                
                filename = url.split('/')[-1] or 'download'
                
                file_path = os.path.join(model_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # 如果是压缩文件，解压
                if filename.endswith(('.zip', '.tar.gz', '.tgz', '.tar')):
                    extract_dir = os.path.join(model_dir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    extract_archive(file_path, extract_dir)
                    source_path = extract_dir
                    
                    # 查找模型文件
                    model_files = find_model_files(extract_dir)
                else:
                    source_path = model_dir
                    model_files = find_model_files(model_dir)
                
                # 创建数据库记录
                db_model = AIModel(
                    name=name,
                    description=description,
                    model_type=model_type,
                    source_type="url",
                    source_path=source_path,
                    config={
                        "download_url": url,
                        "model_files": model_files,
                        "auto_detected": True
                    },
                    status=ModelStatus.UPLOADED
                )
        
        db.add(db_model)
        await db.commit()
        await db.refresh(db_model)
        
        return db_model
        
    except httpx.HTTPError as e:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")
    except HTTPException:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("", response_model=ModelList)
async def list_models(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取模型列表"""
    query = select(AIModel)
    
    if status:
        query = query.where(AIModel.status == status)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取分页数据
    query = query.offset(skip).limit(limit).order_by(AIModel.created_at.desc())
    result = await db.execute(query)
    models = result.scalars().all()
    
    return ModelList(total=total, items=list(models))


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """获取模型详情"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return model


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int,
    model_update: ModelUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新模型信息"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model_update.name:
        model.name = model_update.name
    if model_update.description is not None:
        model.description = model_update.description
    if model_update.config:
        model.config = model_update.config
    
    await db.commit()
    await db.refresh(model)
    
    return model


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """删除模型"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 删除关联的文件
    if model.source_path and os.path.exists(model.source_path):
        if os.path.isdir(model.source_path):
            shutil.rmtree(model.source_path, ignore_errors=True)
        else:
            os.remove(model.source_path)
        
        # 删除模型的父目录（清理残留的空目录）
        try:
            parent_dir = os.path.dirname(model.source_path)
            if parent_dir and parent_dir != settings.MODEL_STORAGE_PATH and os.path.exists(parent_dir):
                # 检查目录是否为空或只包含已知文件
                if os.path.isdir(parent_dir):
                    shutil.rmtree(parent_dir, ignore_errors=True)
                    print(f"Deleted model parent directory: {parent_dir}")
        except Exception as e:
            print(f"Failed to delete model parent directory: {e}")
    
    # 删除原始压缩包（如果有）
    if model.config and isinstance(model.config, dict):
        original_archive = model.config.get("original_archive")
        if original_archive and os.path.exists(original_archive):
            try:
                os.remove(original_archive)
                print(f"Deleted original archive: {original_archive}")
            except Exception as e:
                print(f"Failed to delete original archive {original_archive}: {e}")
        
        # 删除GitHub克隆的仓库目录（如果有）
        github_url = model.config.get("github_url")
        if github_url and model.source_path:
            repo_dir = os.path.join(os.path.dirname(model.source_path), "repo")
            if os.path.exists(repo_dir) and os.path.isdir(repo_dir):
                try:
                    shutil.rmtree(repo_dir, ignore_errors=True)
                    print(f"Deleted repo directory: {repo_dir}")
                except Exception as e:
                    print(f"Failed to delete repo directory {repo_dir}: {e}")
    
    # 删除Docker镜像
    if model.docker_image and model.docker_image_tag:
        docker_service.remove_image(f"{model.docker_image}:{model.docker_image_tag}")

    if model.config and isinstance(model.config, dict):
        push_result = model.config.get("push_result") or {}
        source_image = push_result.get("source_image")
        registry_image = push_result.get("registry_image")
        if source_image and source_image != registry_image:
            docker_service.remove_image(source_image)
    
    await db.delete(model)
    await db.commit()
    
    return {"message": "Model deleted successfully"}


@router.post("/{model_id}/build", response_model=BuildResponse)
async def build_model_image(
    model_id: int,
    build_request: BuildRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """构建模型Docker镜像"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not docker_service.is_connected:
        raise HTTPException(status_code=503, detail="Docker service not available")
    
    # 生成任务ID
    task_id = f"build-{model_id}"
    
    # 更新状态为构建中
    model.status = ModelStatus.BUILDING
    model.status_message = "Build started..."
    await db.commit()
    
    # 在后台执行构建
    background_tasks.add_task(
        run_build_task,
        task_id=task_id,
        model_id=model_id,
        model_name=model.name,
        model_type=model.model_type,
        source_path=model.source_path,
        source_type=model.source_type,
        base_image=build_request.base_image,
        config=model.config
    )
    
    return BuildResponse(
        task_id=task_id,
        message="Build task started, please check progress via WebSocket"
    )


async def run_build_task(
    task_id: str,
    model_id: int,
    model_name: str,
    model_type: str,
    source_path: str,
    source_type: str,
    base_image: str,
    config: Dict[str, Any]
):
    """后台执行构建任务"""
    from app.core.websocket import manager
    from app.models.database import async_session_maker
    
    async with async_session_maker() as db:
        try:
            # 获取模型
            result = await db.execute(select(AIModel).where(AIModel.id == model_id))
            model = result.scalar_one_or_none()
            
            if not model:
                await manager.send_progress(task_id, 0, "Model not found", {"error": True})
                return
            
            # 发送进度回调（使用锁防止并发数据库操作）
            import asyncio
            db_lock = asyncio.Lock()
            
            async def progress_callback(progress: int, message: str, data: Dict[str, Any] = None, persist_status: bool = True):
                await manager.send_progress(task_id, progress, message, data)
                if not persist_status:
                    return
                # 更新数据库状态（加锁防止并发冲突）
                async with db_lock:
                    model.status_message = message
                    await db.commit()
            
            await progress_callback(5, "Starting build...")
            
            # 执行构建
            build_result = await docker_service.build_model_image(
                model_id=model_id,
                model_name=model_name,
                model_type=model_type,
                source_path=source_path,
                source_type=source_type,
                base_image=base_image,
                config=config,
                progress_callback=progress_callback
            )
            
            await progress_callback(85, "Build completed, publishing image to registry...")
            
            image_tag = build_result["image_tag"]
            model.status = ModelStatus.BUILT
            model.status_message = f"Image size: {build_result['size']} bytes"
            
            await db.commit()
            
            model.status = ModelStatus.PUSHING
            model.status_message = "Pushing image to Docker registry..."
            await db.commit()
            
            try:
                push_result = await docker_service.push_image_to_registry(
                    image_tag,
                    progress_callback=progress_callback
                )
                registry_image = push_result["registry_image"]
                registry_repo, registry_tag = registry_image.rsplit(":", 1)

                model.docker_image = registry_repo
                model.docker_image_tag = registry_tag
                model.status = ModelStatus.READY
                model.status_message = f"Image pushed to registry: {registry_image}"
                model.config = {
                    **(model.config or {}),
                    "distribution_mode": "registry",
                    "registry_image": registry_image,
                    "push_result": push_result
                }

                await progress_callback(100, "Build and registry push completed!")

            except Exception as e:
                model.status = ModelStatus.FAILED
                model.status_message = f"Image registry publish failed: {str(e)}"
                await manager.send_progress(task_id, 0, model.status_message, {"error": True})
            
            await db.commit()
            
        except Exception as e:
            import traceback
            error_detail = f"Build failed: {str(e)}"
            print(f"ERROR: {error_detail}")
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            # 更新模型状态为失败
            try:
                model.status = ModelStatus.FAILED
                model.status_message = error_detail
                await db.commit()
            except:
                pass
            
            # 发送错误进度
            await manager.send_progress(task_id, 0, error_detail, {"error": True})


@router.post("/{model_id}/stop-build")
async def stop_build_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """停止模型构建任务或重置卡住的构建状态"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 允许停止构建中、分发中、或者状态卡住的任务
    if model.status not in [ModelStatus.BUILDING, ModelStatus.PUSHING, ModelStatus.UPLOADING]:
        raise HTTPException(status_code=400, detail="Model is not in building, distributing or uploading status")

    # 更新模型状态为失败
    model.status = ModelStatus.FAILED
    model.status_message = "Build stopped by user"
    await db.commit()

    return {"message": "Build stopped successfully"}


@router.post("/{model_id}/reset-status")
async def reset_model_status(model_id: int, db: AsyncSession = Depends(get_db)):
    """重置模型状态（用于处理卡住的构建任务）"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 只允许重置处于构建中或分发中状态的任务
    if model.status not in [ModelStatus.BUILDING, ModelStatus.PUSHING]:
        raise HTTPException(status_code=400, detail="Only building or distributing status can be reset")

    # 重置状态为上传完成（可以重新构建）
    model.status = ModelStatus.UPLOADED
    model.status_message = "Status reset by user, ready to rebuild"
    await db.commit()

    return {"message": "Status reset successfully", "status": model.status.value}


@router.get("/{model_id}/status")
async def get_model_status(model_id: int, db: AsyncSession = Depends(get_db)):
    """获取模型构建状态"""
    result = await db.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "model_id": model_id,
        "status": model.status.value,
        "message": model.status_message,
        "docker_image": model.docker_image,
        "docker_tag": model.docker_image_tag
    }
