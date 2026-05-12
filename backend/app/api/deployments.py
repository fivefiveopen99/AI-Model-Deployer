import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from app.models.database import get_db, AIModel, Deployment, DeployStatus, ModelStatus, async_session_maker
from app.models.schemas import (
    DeploymentCreate, DeploymentUpdate, DeploymentResponse, DeploymentList, TaskStatus, InferenceRunRequest
)
from app.services.k8s_service import K8sExecError, k8s_service
from app.services.nfs_service import NFSDiscoveryError, discover_nfs_config
from app.core.config import settings
from app.services.inference_service import (
    build_empty_inference_result,
    build_result_digest,
    find_result_file,
    get_media_type,
    merge_inference_result,
    normalize_inference_config,
    parse_template_variables,
    render_command_template,
    resolve_mount_file_path,
    resolve_mount_result_root,
    scan_mount_result_files,
    select_generated_files,
)

router = APIRouter(prefix="/deployments", tags=["deployments"])
ACTIVE_INFERENCE_TASKS = set()


def _has_active_inference_task(deployment_id: int) -> bool:
    if deployment_id not in ACTIVE_INFERENCE_TASKS:
        return False

    from app.core.websocket import manager

    latest = manager.latest_progress.get(f"infer-{deployment_id}")
    if not latest:
        ACTIVE_INFERENCE_TASKS.discard(deployment_id)
        return False

    progress = int(latest.get("progress") or 0)
    has_error = bool((latest.get("data") or {}).get("error"))
    if progress >= 100 or has_error:
        ACTIVE_INFERENCE_TASKS.discard(deployment_id)
        return False

    return True


def serialize_deployment(deployment: Deployment) -> Dict[str, Any]:
    return {
        "id": deployment.id,
        "name": deployment.name,
        "model_id": deployment.model_id,
        "source_type": deployment.source_type or "model",
        "image": deployment.image,
        "port": deployment.port or 8000,
        "namespace": deployment.namespace,
        "replicas": deployment.replicas,
        "resources": deployment.resources or {},
        "env_vars": deployment.env_vars or {},
        "mount_config": deployment.mount_config or {},
        "command": deployment.command,
        "inference_config": normalize_inference_config(deployment.source_type, deployment.inference_config),
        "last_inference_result": deployment.last_inference_result or build_empty_inference_result(),
        "status": deployment.status.value if hasattr(deployment.status, "value") else deployment.status,
        "status_message": deployment.status_message,
        "k8s_deployment_name": deployment.k8s_deployment_name,
        "k8s_service_name": deployment.k8s_service_name,
        "endpoint": deployment.endpoint,
        "created_at": deployment.created_at,
        "updated_at": deployment.updated_at,
    }


def normalize_registry_image(image: str) -> str:
    image = (image or "").strip()
    if not image:
        return image

    first_segment = image.split("/", 1)[0]
    if "." in first_segment or ":" in first_segment or first_segment == "localhost":
        return image

    registry_url = settings.DOCKER_REGISTRY_URL.rstrip("/")
    parsed = urlparse(f"http://{registry_url}")
    registry_host = parsed.netloc
    if not registry_host:
        return image
    return f"{registry_host}/{image}"


def normalize_mount_config(mount_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(mount_config or {})
    mount_type = (config.get("type") or "").strip().lower()
    enabled = bool(config.get("enabled")) and bool(mount_type)

    if not enabled:
        return {}

    mount_path = (config.get("mount_path") or "").strip()
    if not mount_path:
        raise HTTPException(status_code=400, detail="Mount path is required")

    normalized = {
        "enabled": True,
        "type": mount_type,
        "mount_path": mount_path,
        "sub_path": (config.get("sub_path") or "").strip() or None,
        "read_only": bool(config.get("read_only"))
    }

    if mount_type == "pvc":
        claim_name = (config.get("claim_name") or "").strip()
        if not claim_name:
            raise HTTPException(status_code=400, detail="PVC claim name is required")
        normalized["claim_name"] = claim_name
    elif mount_type == "nfs":
        directory = (config.get("directory") or "").strip().strip("/")
        if not directory:
            raise HTTPException(status_code=400, detail="NFS directory is required")
        try:
            nfs_config = discover_nfs_config()
        except NFSDiscoveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        export_root = nfs_config["export_root"].rstrip("/")
        normalized["server"] = nfs_config["server"]
        normalized["directory"] = directory
        normalized["path"] = f"{export_root}/{directory}" if directory else export_root
    else:
        raise HTTPException(status_code=400, detail="Unsupported mount type")

    return normalized


@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新的部署"""
    source_type = (deployment.source_type or "model").strip().lower()
    model = None
    model_id = 0
    image = deployment.image.strip() if deployment.image else None
    port = deployment.port
    mount_config = normalize_mount_config(deployment.mount_config)
    inference_config = normalize_inference_config(source_type, deployment.inference_config)

    if source_type == "model":
        if not deployment.model_id:
            raise HTTPException(status_code=400, detail="Model is required")

        result = await db.execute(select(AIModel).where(AIModel.id == deployment.model_id))
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        if model.status != ModelStatus.READY:
            raise HTTPException(
                status_code=400,
                detail=f"Model is not ready. Current status: {model.status.value}"
            )

        if not model.docker_image or not model.docker_image_tag:
            raise HTTPException(status_code=400, detail="Model has no Docker image")

        model_id = model.id
        image = f"{model.docker_image}:{model.docker_image_tag}"
        port = model.config.get("port", deployment.port) if model.config else deployment.port
    elif source_type == "image":
        if not image:
            raise HTTPException(status_code=400, detail="Image is required")
        image = normalize_registry_image(image)
        port = 8000
    else:
        raise HTTPException(status_code=400, detail="Unsupported deployment source type")
    
    # 创建部署记录
    db_deployment = Deployment(
        name=deployment.name,
        model_id=model_id,
        source_type=source_type,
        image=image,
        port=port,
        namespace=deployment.namespace,
        replicas=deployment.replicas,
        resources=deployment.resources,
        env_vars=deployment.env_vars,
        mount_config=mount_config,
        command=None,
        inference_config=inference_config,
        last_inference_result=build_empty_inference_result(),
        status=DeployStatus.PENDING
    )
    
    db.add(db_deployment)
    await db.commit()
    await db.refresh(db_deployment)
    
    return serialize_deployment(db_deployment)


@router.post("/{deployment_id}/deploy", response_model=TaskStatus)
async def deploy_to_k8s(
    deployment_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """部署到Kubernetes（后台任务，支持进度跟踪）"""
    # 先获取部署
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # 再获取关联的模型
    model = None
    image_tag = normalize_registry_image(deployment.image) if deployment.image else None
    port = deployment.port or 8000

    if deployment.source_type == "model":
        result = await db.execute(select(AIModel).where(AIModel.id == deployment.model_id))
        model = result.scalar_one_or_none()
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        image_tag = f"{model.docker_image}:{model.docker_image_tag}"
        port = model.config.get("port", deployment.port or 8000) if model.config else (deployment.port or 8000)

    if not image_tag:
        raise HTTPException(status_code=400, detail="Deployment has no image")
    
    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")
    
    # 生成任务ID
    task_id = f"deploy-{deployment_id}"
    
    # 更新状态为部署中
    deployment.status = DeployStatus.DEPLOYING
    deployment.status_message = "Deployment started..."
    await db.commit()
    
    # 在后台执行部署
    background_tasks.add_task(
        run_deploy_task,
        task_id=task_id,
        deployment_id=deployment_id,
        deployment_name=deployment.name,
        model_id=deployment.model_id,
        source_type=deployment.source_type,
        image_tag=image_tag,
        namespace=deployment.namespace,
        replicas=deployment.replicas,
        resources=deployment.resources,
        env_vars=deployment.env_vars,
        mount_config=deployment.mount_config,
        command=None,
        port=port
    )
    
    return TaskStatus(
        task_id=task_id,
        status="deploying",
        progress=0,
        message="Deployment task started, please check progress via WebSocket"
    )


async def run_deploy_task(
    task_id: str,
    deployment_id: int,
    deployment_name: str,
    model_id: int,
    source_type: str,
    image_tag: str,
    namespace: str,
    replicas: int,
    resources: Dict[str, Any],
    env_vars: Dict[str, str],
    mount_config: Dict[str, Any],
    command: Optional[str],
    port: int
):
    """后台执行部署任务"""
    from app.core.websocket import manager
    
    async with async_session_maker() as db:
        try:
            # 获取部署
            result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                await manager.send_progress(task_id, 0, "Deployment not found", {"error": True})
                return
            
            # 发送进度回调
            async def progress_callback(progress: int, message: str):
                await manager.send_progress(task_id, progress, message)
                # 更新数据库状态
                deployment.status_message = message
                await db.commit()
            
            await progress_callback(5, "Starting deployment...")
            
            # 执行部署
            deploy_result = await k8s_service.deploy_model(
                deployment_name=deployment_name,
                model_id=model_id,
                source_type=source_type,
                image_tag=image_tag,
                namespace=namespace,
                replicas=replicas,
                resources=resources,
                env_vars=env_vars,
                mount_config=mount_config,
                command=None,
                port=port,
                progress_callback=progress_callback
            )
            
            # 更新部署信息
            deployment.k8s_deployment_name = deploy_result["deployment_name"]
            deployment.k8s_service_name = deploy_result["service_name"]
            deployment.endpoint = deploy_result["endpoint"]
            deployment.status = DeployStatus.RUNNING
            deployment.status_message = "Deployment successful"
            
            await db.commit()
            
            await progress_callback(100, "Deployment completed successfully!")
            
        except Exception as e:
            import traceback
            error_detail = f"Deployment failed: {str(e)}"
            print(f"ERROR: {error_detail}")
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            # 更新部署状态为失败
            try:
                deployment.status = DeployStatus.FAILED
                deployment.status_message = error_detail
                await db.commit()
            except:
                pass
            
            # 发送错误进度
            await manager.send_progress(task_id, 0, error_detail, {"error": True})


@router.get("", response_model=DeploymentList)
async def list_deployments(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取部署列表"""
    query = select(Deployment)
    
    if status:
        query = query.where(Deployment.status == status)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取分页数据
    query = query.offset(skip).limit(limit).order_by(Deployment.created_at.desc())
    result = await db.execute(query)
    deployments = result.scalars().all()
    
    return DeploymentList(total=total, items=[serialize_deployment(deployment) for deployment in deployments])


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    """获取部署详情"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return serialize_deployment(deployment)


def _get_deployment_inference_config(deployment: Deployment) -> Dict[str, Any]:
    config = normalize_inference_config(deployment.source_type, deployment.inference_config)
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="Inference command is not configured for this deployment")
    return config


def _raise_result_file_http_error(exc: Exception, fallback_message: str = "读取结果文件失败"):
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, K8sExecError):
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    raise HTTPException(status_code=502, detail=f"{fallback_message}: {str(exc)}") from exc


async def _list_result_files_for_deployment(
    deployment: Deployment,
    inference_config: Dict[str, Any],
    pod_name: Optional[str] = None
) -> Dict[str, Any]:
    result_source = inference_config.get("result_source", "container")
    result_path = inference_config.get("result_path", "")

    if result_source == "mount":
        mount_root = resolve_mount_result_root(deployment.mount_config or {}, inference_config)
        return {
            "files": scan_mount_result_files(mount_root),
            "mount_root": mount_root
        }

    if not pod_name:
        pod_name = await k8s_service.get_ready_pod_name(deployment.k8s_deployment_name, deployment.namespace)
    files = await k8s_service.list_container_files(pod_name, deployment.namespace, result_path)
    return {
        "files": files,
        "pod_name": pod_name
    }


@router.post("/{deployment_id}/run-inference", response_model=TaskStatus)
async def run_inference(
    deployment_id: int,
    request: InferenceRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if deployment.source_type != "image":
        raise HTTPException(status_code=400, detail="Inference command is only available for image deployments")
    if not deployment.k8s_deployment_name:
        raise HTTPException(status_code=400, detail="Deployment has not been deployed to Kubernetes")
    if _has_active_inference_task(deployment_id):
        raise HTTPException(status_code=409, detail="Inference task is already running for this deployment")

    inference_config = _get_deployment_inference_config(deployment)
    command_template = inference_config["command_template"]
    variable_names = inference_config.get("variable_names") or parse_template_variables(command_template)
    final_command = render_command_template(command_template, request.variables, variable_names)
    task_id = f"infer-{deployment_id}"

    ACTIVE_INFERENCE_TASKS.add(deployment_id)
    background_tasks.add_task(
        run_inference_task,
        task_id=task_id,
        deployment_id=deployment_id,
        variables=request.variables,
        final_command=final_command
    )
    return TaskStatus(
        task_id=task_id,
        status="running",
        progress=0,
        message="Inference task started, please check progress via WebSocket"
    )


async def run_inference_task(task_id: str, deployment_id: int, variables: Dict[str, str], final_command: str):
    from app.core.websocket import manager

    async with async_session_maker() as db:
        deployment = None
        started_at = datetime.utcnow().isoformat()
        loop = asyncio.get_running_loop()
        try:
            result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
            deployment = result.scalar_one_or_none()
            if not deployment:
                await manager.send_progress(task_id, 0, "Deployment not found", {"error": True})
                return

            inference_config = _get_deployment_inference_config(deployment)

            await manager.send_progress(task_id, 10, "Selecting ready pod...")
            pod_name = await k8s_service.get_ready_pod_name(deployment.k8s_deployment_name, deployment.namespace)
            before_files = await k8s_service.list_container_files(
                pod_name,
                deployment.namespace,
                inference_config["result_path"],
                allow_missing=True
            )

            await manager.send_progress(task_id, 40, "Running inference command...")
            def on_log(chunk: str):
                asyncio.run_coroutine_threadsafe(
                    manager.send_progress(
                        task_id,
                        40,
                        "Running inference command...",
                        {"log": chunk}
                    ),
                    loop
                )

            execution = await k8s_service.exec_in_pod_streaming(
                pod_name,
                deployment.namespace,
                final_command,
                on_log=on_log
            )

            await manager.send_progress(task_id, 75, "Collecting result files...")
            files_payload = await _list_result_files_for_deployment(deployment, inference_config, pod_name=pod_name)
            result_files = select_generated_files(before_files, files_payload["files"])

            latest_result = {
                "started_at": started_at,
                "finished_at": datetime.utcnow().isoformat(),
                "exit_code": execution["exit_code"],
                "stdout": execution["stdout"],
                "stderr": execution["stderr"],
                "files": result_files,
                "result_source": inference_config["result_source"],
                "result_path": inference_config["result_path"],
                "result_digest": build_result_digest(
                    inference_config["command_template"],
                    variables,
                    inference_config["result_path"]
                )
            }
            deployment.last_inference_result = merge_inference_result(deployment.last_inference_result or {}, latest_result)
            await db.commit()

            if execution["exit_code"] != 0:
                await manager.send_progress(
                    task_id,
                    100,
                    "Inference finished with errors",
                    {"error": True, "exit_code": execution["exit_code"], "files": result_files}
                )
                return

            await manager.send_progress(
                task_id,
                100,
                "Inference completed successfully",
                {"exit_code": 0, "files": result_files}
            )
        except HTTPException as exc:
            if deployment:
                failure_result = merge_inference_result(deployment.last_inference_result or {}, {
                    "started_at": started_at,
                    "finished_at": datetime.utcnow().isoformat(),
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": exc.detail,
                    "files": []
                })
                deployment.last_inference_result = failure_result
                await db.commit()
            await manager.send_progress(task_id, 0, exc.detail, {"error": True})
        except Exception as exc:
            if deployment:
                failure_result = merge_inference_result(deployment.last_inference_result or {}, {
                    "started_at": started_at,
                    "finished_at": datetime.utcnow().isoformat(),
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": str(exc),
                    "files": []
                })
                deployment.last_inference_result = failure_result
                await db.commit()
            await manager.send_progress(task_id, 0, f"Inference failed: {str(exc)}", {"error": True})
        finally:
            ACTIVE_INFERENCE_TASKS.discard(deployment_id)


@router.get("/{deployment_id}/inference-result")
async def get_inference_result(deployment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return deployment.last_inference_result or build_empty_inference_result()


@router.get("/{deployment_id}/inference-files/{file_key}/preview")
async def preview_inference_file(deployment_id: int, file_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    inference_config = _get_deployment_inference_config(deployment)
    result_data = deployment.last_inference_result or build_empty_inference_result()
    file_info = find_result_file(result_data.get("files", []), file_key)
    if not file_info.get("previewable"):
        raise HTTPException(status_code=400, detail="This file type does not support preview")

    result_path = inference_config["result_path"].rstrip("/")
    if inference_config.get("result_source") == "mount":
        mount_root = resolve_mount_result_root(deployment.mount_config or {}, inference_config)
        file_path = resolve_mount_file_path(mount_root, file_info["relative_path"])
        if file_info["kind"] == "text":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return PlainTextResponse(f.read())
        return FileResponse(file_path, media_type=get_media_type(file_info["name"]))

    try:
        pod_name = await k8s_service.get_ready_pod_name(deployment.k8s_deployment_name, deployment.namespace)
        container_file_path = f"{result_path}/{file_info['relative_path']}".replace("//", "/")
        if file_info["kind"] == "text":
            content = await k8s_service.read_container_text_file(pod_name, deployment.namespace, container_file_path)
            return PlainTextResponse(content)

        content = await k8s_service.read_container_file_bytes(pod_name, deployment.namespace, container_file_path)
        return Response(content=content, media_type=get_media_type(file_info["name"]))
    except Exception as exc:
        _raise_result_file_http_error(exc, "预览结果文件失败")


@router.get("/{deployment_id}/inference-files/{file_key}/download")
async def download_inference_file(deployment_id: int, file_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    inference_config = _get_deployment_inference_config(deployment)
    result_data = deployment.last_inference_result or build_empty_inference_result()
    file_info = find_result_file(result_data.get("files", []), file_key)
    result_path = inference_config["result_path"].rstrip("/")

    if inference_config.get("result_source") == "mount":
        mount_root = resolve_mount_result_root(deployment.mount_config or {}, inference_config)
        file_path = resolve_mount_file_path(mount_root, file_info["relative_path"])
        return FileResponse(
            file_path,
            media_type=get_media_type(file_info["name"]),
            filename=file_info["name"]
        )

    try:
        pod_name = await k8s_service.get_ready_pod_name(deployment.k8s_deployment_name, deployment.namespace)
        container_file_path = f"{result_path}/{file_info['relative_path']}".replace("//", "/")
        content = await k8s_service.read_container_file_bytes(pod_name, deployment.namespace, container_file_path)
        headers = {"Content-Disposition": f'attachment; filename="{file_info["name"]}"'}
        return Response(content=content, media_type=get_media_type(file_info["name"]), headers=headers)
    except Exception as exc:
        _raise_result_file_http_error(exc, "下载结果文件失败")


@router.get("/{deployment_id}/status")
async def get_deployment_status(
    deployment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取部署在K8s中的状态"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.k8s_deployment_name:
        return {"status": "Not deployed to Kubernetes yet"}
    
    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")
    
    try:
        k8s_status = await k8s_service.get_deployment_status(
            deployment.k8s_deployment_name,
            deployment.namespace
        )
        return k8s_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/sync-status")
async def sync_deployment_status(
    deployment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """同步部署状态从 K8s 到数据库"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if not deployment.k8s_deployment_name:
        return {"message": "Not deployed to K8s yet", "status": deployment.status}

    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")

    try:
        # 从 K8s 获取实际状态
        k8s_status = await k8s_service.get_deployment_status(
            deployment.k8s_deployment_name,
            deployment.namespace
        )

        # 根据 K8s 状态更新数据库
        pod_status = k8s_status.get("pod_status", "")
        pod_message = k8s_status.get("pod_message", "")

        if pod_status == "Running":
            deployment.status = DeployStatus.RUNNING
            deployment.status_message = "Deployment is running"
        elif pod_status in ["Pending", "ContainerCreating"]:
            deployment.status = DeployStatus.DEPLOYING
            deployment.status_message = f"Pod is {pod_status}"
        elif pod_status in ["CrashLoopBackOff", "Error", "Failed", "ImagePullBackOff", "ErrImagePull", "ImagePullBackOff"]:
            deployment.status = DeployStatus.FAILED
            deployment.status_message = f"Pod failed: {pod_status} - {pod_message}" if pod_message else f"Pod failed: {pod_status}"
        elif pod_status == "NotFound":
            # Pod 不存在了，可能是被删除了
            deployment.status = DeployStatus.FAILED
            deployment.status_message = "Pod not found in K8s"
        else:
            deployment.status_message = f"Pod status: {pod_status}"

        await db.commit()

        return {
            "message": "Status synchronized",
            "database_status": deployment.status,
            "k8s_status": k8s_status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: int,
    replicas: int,
    db: AsyncSession = Depends(get_db)
):
    """扩缩容部署"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.k8s_deployment_name:
        raise HTTPException(status_code=400, detail="Deployment not in Kubernetes")
    
    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")
    
    success = await k8s_service.scale_deployment(
        deployment.k8s_deployment_name,
        deployment.namespace,
        replicas
    )
    
    if success:
        deployment.replicas = replicas
        await db.commit()
        return {"message": f"Scaled to {replicas} replicas"}
    else:
        raise HTTPException(status_code=500, detail="Scale failed")


@router.get("/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: int,
    tail_lines: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取部署日志"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.k8s_deployment_name:
        raise HTTPException(status_code=400, detail="Deployment not in Kubernetes")
    
    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")
    
    logs = await k8s_service.get_pod_logs(
        deployment.k8s_deployment_name,
        deployment.namespace,
        tail_lines
    )
    
    return {"logs": logs}


@router.delete("/{deployment_id}")
async def delete_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    """删除部署"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    k8s_delete_error = None

    # 如果已部署到K8s，先删除K8s资源
    if deployment.k8s_deployment_name:
        try:
            # 使用异步方式检查连接并删除
            is_connected = await k8s_service.check_connection_async()
            if is_connected:
                await k8s_service.delete_deployment(
                    deployment.k8s_deployment_name,
                    deployment.namespace
                )
            else:
                k8s_delete_error = "Kubernetes not connected"
        except Exception as e:
            k8s_delete_error = str(e)
            print(f"Warning: Failed to delete K8s resources: {e}")
            # 继续删除数据库记录

    await db.delete(deployment)
    await db.commit()

    if k8s_delete_error:
        return {
            "message": "Deployment deleted from database, but K8s resources may still exist",
            "warning": f"K8s delete failed: {k8s_delete_error}"
        }

    return {"message": "Deployment deleted successfully"}


@router.get("/k8s/list")
async def list_k8s_deployments(namespace: Optional[str] = None):
    """直接从K8s获取部署列表"""
    if not k8s_service.is_connected:
        raise HTTPException(status_code=503, detail="Kubernetes service not available")
    
    deployments = await k8s_service.list_deployments(namespace)
    return {"deployments": deployments}
