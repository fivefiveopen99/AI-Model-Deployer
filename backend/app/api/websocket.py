from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid

from app.core.websocket import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket):
    """
    WebSocket 连接用于接收任务进度
    
    连接后发送: {"action": "subscribe", "task_id": "build-123"}
    接收进度: {"type": "progress", "task_id": "build-123", "progress": 50, "message": "Building..."}
    """
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            action = data.get("action")
            task_id = data.get("task_id")
            
            if action == "subscribe" and task_id:
                # 订阅任务进度
                await manager.subscribe_to_task(client_id, task_id)
                await manager.send_message(client_id, {
                    "type": "subscribed",
                    "task_id": task_id,
                    "message": f"Subscribed to task {task_id}"
                })
            
            elif action == "unsubscribe" and task_id:
                # 取消订阅
                manager.unsubscribe_from_task(client_id, task_id)
                await manager.send_message(client_id, {
                    "type": "unsubscribed",
                    "task_id": task_id
                })
            
            elif action == "ping":
                # 心跳响应
                await manager.send_message(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)
