import asyncio
from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接 {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储任务相关的连接 {task_id: {client_id}}
        self.task_connections: Dict[str, Set[str]] = {}
        # 存储任务最后一次进度，客户端晚订阅时也能立刻恢复当前状态
        self.latest_progress: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        """断开 WebSocket 连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 从所有任务中移除
        for task_id, clients in self.task_connections.items():
            clients.discard(client_id)
    
    async def subscribe_to_task(self, client_id: str, task_id: str):
        """订阅任务进度"""
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(client_id)

        latest = self.latest_progress.get(task_id)
        if latest:
            await self.send_message(client_id, latest)
    
    def unsubscribe_from_task(self, client_id: str, task_id: str):
        """取消订阅任务进度"""
        if task_id in self.task_connections:
            self.task_connections[task_id].discard(client_id)
    
    async def send_progress(self, task_id: str, progress: int, message: str, data: dict = None):
        """发送进度更新到所有订阅该任务的客户端"""
        message_data = {
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "data": data or {}
        }

        self.latest_progress[task_id] = message_data
        
        if task_id not in self.task_connections:
            return
        
        # 获取所有订阅该任务的客户端
        client_ids = list(self.task_connections[task_id])
        
        # 发送给每个客户端
        for client_id in client_ids:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message_data)
                except Exception as e:
                    print(f"Failed to send progress to {client_id}: {e}")
    
    async def send_message(self, client_id: str, message: dict):
        """发送消息给指定客户端"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                print(f"Failed to send message to {client_id}: {e}")
    
    async def broadcast(self, message: dict):
        """广播消息给所有客户端"""
        for client_id in list(self.active_connections.keys()):
            await self.send_message(client_id, message)


# 全局连接管理器实例
manager = ConnectionManager()
