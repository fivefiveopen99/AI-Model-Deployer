from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any

from app.models.database import get_db, AIModel, Deployment, DeployStatus, ModelStatus, async_session_maker
from app.models.schemas import (
    DeploymentCreate, DeploymentUpdate, DeploymentResponse, DeploymentList, TaskStatus
)
from app.services.k8s_service import k8s_service

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新的部署"""
    # 检查模型是否存在且已就绪
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
    
    # 创建部署记录
    db_deployment = Deployment(
        name=deployment.name,
        model_id=deployment.model_id,
        namespace=deployment.namespace,
        replicas=deployment.replicas,
        resources=deployment.resources,
        env_vars=deployment.env_vars,
        status=DeployStatus.PENDING
    )
    
    db.add(db_deployment)
    await db.commit()
    await db.refresh(db_deployment)
    
    return db_deployment


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
    result = await db.execute(select(AIModel).where(AIModel.id == deployment.model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
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
        image_tag=f"{model.docker_image}:{model.docker_image_tag}",
        namespace=deployment.namespace,
        replicas=deployment.replicas,
        resources=deployment.resources,
        env_vars=deployment.env_vars,
        port=model.config.get("port", 8000) if model.config else 8000
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
    image_tag: str,
    namespace: str,
    replicas: int,
    resources: Dict[str, Any],
    env_vars: Dict[str, str],
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
                image_tag=image_tag,
                namespace=namespace,
                replicas=replicas,
                resources=resources,
                env_vars=env_vars,
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
    
    return DeploymentList(total=total, items=list(deployments))


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    """获取部署详情"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return deployment


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
