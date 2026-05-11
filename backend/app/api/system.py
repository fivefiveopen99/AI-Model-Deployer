from fastapi import APIRouter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

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


@router.get("/build-nodes")
async def get_build_nodes():
    """获取可选构建节点，默认包含本机。"""
    nodes = [
        {
            "name": "local",
            "display_name": "本机",
            "type": "local",
            "internal_ip": None
        }
    ]

    k8s_connected = await k8s_service.check_connection_async()
    if not k8s_connected:
        return {"items": nodes}

    worker_nodes = await k8s_service.get_worker_nodes()
    for node in worker_nodes:
        nodes.append({
            "name": node["name"],
            "display_name": f"{node['name']} ({node.get('internal_ip') or 'no-ip'})",
            "type": "k8s-worker",
            "internal_ip": node.get("internal_ip")
        })

    return {"items": nodes}
