from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import json

from app.models.database import get_db, Deployment

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.get("/deployments/{deployment_id}/health")
async def proxy_health_check(
    deployment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """代理健康检查请求到部署的模型服务"""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.endpoint:
        raise HTTPException(status_code=400, detail="Deployment has no endpoint")
    
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(f"{deployment.endpoint}/health")
            return {
                "status": response.status_code,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to model service: {str(e)}")


@router.post("/deployments/{deployment_id}/predict")
async def proxy_predict(
    deployment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """代理预测请求到部署的模型服务"""
    import traceback
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.endpoint:
        raise HTTPException(status_code=400, detail="Deployment has no endpoint")
    
    try:
        # 读取请求体
        body = await request.body()
        content_type = request.headers.get('content-type', 'application/json')
        
        print(f"Proxy predict: endpoint={deployment.endpoint}, content_type={content_type}, body_size={len(body)}")
        
        async with httpx.AsyncClient(timeout=600.0, trust_env=False) as client:
            headers = {'content-type': content_type}
            response = await client.post(
                f"{deployment.endpoint}/predict",
                content=body,
                headers=headers
            )
            
            print(f"Proxy predict response: status={response.status_code}")
            
            # 返回响应 - 直接透传，不做JSON解析
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"content-type": response.headers.get("content-type", "application/json")}
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        error_detail = f"Failed to connect to model service: {str(e)}\n{traceback.format_exc()}"
        print(f"Proxy predict error: {error_detail}")
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/deployments/{deployment_id}/predict/image")
async def proxy_predict_image(
    deployment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """代理图片预测请求到部署的模型服务"""
    import traceback
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if not deployment.endpoint:
        raise HTTPException(status_code=400, detail="Deployment has no endpoint")
    
    try:
        # 读取请求体（multipart/form-data）
        body = await request.body()
        content_type = request.headers.get('content-type', 'multipart/form-data')
        
        print(f"Proxy predict image: endpoint={deployment.endpoint}, content_type={content_type}, body_size={len(body)}")
        
        async with httpx.AsyncClient(timeout=600.0, trust_env=False) as client:
            headers = {'content-type': content_type}
            response = await client.post(
                f"{deployment.endpoint}/predict/image",
                content=body,
                headers=headers
            )
            
            print(f"Proxy predict image response: status={response.status_code}")
            
            # 返回响应 - 直接透传
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"content-type": response.headers.get("content-type", "application/json")}
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        error_detail = f"Failed to connect to model service: {str(e)}\n{traceback.format_exc()}"
        print(f"Proxy predict image error: {error_detail}")
        raise HTTPException(status_code=503, detail=str(e))
