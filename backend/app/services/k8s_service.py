from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
from typing import Optional, Dict, Any, List
import asyncio

from app.core.config import settings


class K8sService:
    def __init__(self):
        self.core_api = None
        self.apps_api = None
        self._connected = False
        self._connect()
    
    def _connect(self):
        try:
            # 尝试加载配置
            if settings.K8S_CONFIG_PATH and os.path.exists(settings.K8S_CONFIG_PATH):
                config.load_kube_config(config_file=settings.K8S_CONFIG_PATH)
            else:
                # 尝试从环境变量或默认位置加载
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()
            
            self.core_api = client.CoreV1Api()
            self.apps_api = client.AppsV1Api()
            
            # 测试连接
            self.core_api.list_namespace()
            self._connected = True
            print("Kubernetes connected successfully")
        except Exception as e:
            print(f"Kubernetes connection failed: {e}")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """同步方式检查连接状态（用于快速检查）"""
        return self._connected
    
    async def check_connection_async(self) -> bool:
        """异步方式检查连接状态（用于详细检查）"""
        # 如果已经连接过，直接返回缓存状态（避免频繁检查）
        if self._connected and self.core_api:
            return True
            
        # 尝试重新连接
        try:
            loop = asyncio.get_event_loop()
            # 使用线程池执行同步调用，避免阻塞事件循环
            await loop.run_in_executor(None, self._reconnect)
            return self._connected
        except Exception as e:
            print(f"K8s connection check failed: {e}")
            return False
    
    def _reconnect(self):
        """重新连接 K8s"""
        try:
            # 尝试加载配置
            if settings.K8S_CONFIG_PATH and os.path.exists(settings.K8S_CONFIG_PATH):
                config.load_kube_config(config_file=settings.K8S_CONFIG_PATH)
            else:
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()
            
            self.core_api = client.CoreV1Api()
            self.apps_api = client.AppsV1Api()
            
            # 测试连接
            self.core_api.list_namespace()
            self._connected = True
            print("Kubernetes reconnected successfully")
        except Exception as e:
            print(f"Kubernetes reconnect failed: {e}")
            self._connected = False
    
    async def deploy_model(
        self,
        deployment_name: str,
        model_id: int,
        image_tag: str,
        namespace: str = "default",
        replicas: int = 1,
        resources: Dict[str, Any] = None,
        env_vars: Dict[str, str] = None,
        port: int = 8000,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        resources = resources or {}
        env_vars = env_vars or {}
        
        k8s_deployment_name = f"model-{model_id}-{deployment_name.lower().replace(' ', '-')}"
        k8s_service_name = f"{k8s_deployment_name}-svc"
        
        # 确保namespace存在
        await self._ensure_namespace(namespace)
        
        try:
            if progress_callback:
                await progress_callback(30, "Creating deployment...")
            
            # 创建Deployment
            deployment = self._create_deployment_object(
                name=k8s_deployment_name,
                image_tag=image_tag,
                replicas=replicas,
                resources=resources,
                env_vars=env_vars,
                port=port
            )
            
            loop = asyncio.get_event_loop()
            
            # 检查是否已存在
            try:
                existing = await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.read_namespaced_deployment(
                        name=k8s_deployment_name,
                        namespace=namespace
                    )
                )
                # 更新
                await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.replace_namespaced_deployment(
                        name=k8s_deployment_name,
                        namespace=namespace,
                        body=deployment
                    )
                )
            except ApiException as e:
                if e.status == 404:
                    # 创建新的
                    await loop.run_in_executor(
                        None,
                        lambda: self.apps_api.create_namespaced_deployment(
                            namespace=namespace,
                            body=deployment
                        )
                    )
                else:
                    raise
            
            if progress_callback:
                await progress_callback(50, "Creating service...")
            
            # 创建Service
            service = self._create_service_object(
                name=k8s_service_name,
                selector={"app": k8s_deployment_name},
                port=port
            )
            
            try:
                existing_svc = await loop.run_in_executor(
                    None,
                    lambda: self.core_api.read_namespaced_service(
                        name=k8s_service_name,
                        namespace=namespace
                    )
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.core_api.replace_namespaced_service(
                        name=k8s_service_name,
                        namespace=namespace,
                        body=service
                    )
                )
            except ApiException as e:
                if e.status == 404:
                    await loop.run_in_executor(
                        None,
                        lambda: self.core_api.create_namespaced_service(
                            namespace=namespace,
                            body=service
                        )
                    )
                else:
                    raise
            
            if progress_callback:
                await progress_callback(80, "Waiting for rollout...")
            
            # 等待部署完成
            endpoint = await self._wait_for_deployment(
                k8s_deployment_name, namespace, port
            )
            
            if progress_callback:
                await progress_callback(100, "Deployment completed")
            
            return {
                "success": True,
                "deployment_name": k8s_deployment_name,
                "service_name": k8s_service_name,
                "namespace": namespace,
                "endpoint": endpoint,
                "replicas": replicas
            }
            
        except Exception as e:
            raise Exception(f"Deployment failed: {str(e)}")
    
    def _create_deployment_object(
        self,
        name: str,
        image_tag: str,
        replicas: int,
        resources: Dict[str, Any],
        env_vars: Dict[str, str],
        port: int
    ) -> client.V1Deployment:
        
        # 构建资源限制
        resource_requirements = client.V1ResourceRequirements()
        if resources:
            if "limits" in resources:
                resource_requirements.limits = resources["limits"]
            if "requests" in resources:
                resource_requirements.requests = resources["requests"]
        
        # 构建环境变量
        env = []
        for key, value in env_vars.items():
            env.append(client.V1EnvVar(name=key, value=str(value)))
        
        # 添加默认环境变量
        env.append(client.V1EnvVar(name="PORT", value=str(port)))
        env.append(client.V1EnvVar(name="MODEL_NAME", value=name))
        
        container = client.V1Container(
            name="model",
            image=image_tag,
            image_pull_policy="Never" if image_tag.startswith("ai-model:") else "IfNotPresent",
            ports=[client.V1ContainerPort(container_port=port)],
            resources=resource_requirements,
            env=env,
            liveness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/health",
                    port=port
                ),
                initial_delay_seconds=0,
                period_seconds=30,
                timeout_seconds=10,
                failure_threshold=20
            ),
            readiness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/health",
                    port=port
                ),
                initial_delay_seconds=5,
                period_seconds=10,
                timeout_seconds=5,
                failure_threshold=3
            ),
            startup_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/health",
                    port=port
                ),
                initial_delay_seconds=10,
                period_seconds=10,
                timeout_seconds=5,
                failure_threshold=60
            )
        )
        
        image_pull_secrets = None
        if settings.K8S_IMAGE_PULL_SECRET_NAME:
            image_pull_secrets = [
                client.V1LocalObjectReference(name=settings.K8S_IMAGE_PULL_SECRET_NAME)
            ]

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(
                containers=[container],
                image_pull_secrets=image_pull_secrets
            )
        )
        
        spec = client.V1DeploymentSpec(
            replicas=replicas,
            selector={"matchLabels": {"app": name}},
            template=template
        )
        
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"app": name, "managed-by": "ai-model-deployer"}
            ),
            spec=spec
        )
        
        return deployment
    
    def _create_service_object(
        self,
        name: str,
        selector: Dict[str, str],
        port: int
    ) -> client.V1Service:

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"managed-by": "ai-model-deployer"}
            ),
            spec=client.V1ServiceSpec(
                selector=selector,
                ports=[client.V1ServicePort(
                    port=port,
                    target_port=port,
                    protocol="TCP",
                    node_port=None  # 让 Kubernetes 自动分配 NodePort
                )],
                type="NodePort"
            )
        )

        return service
    
    async def _ensure_namespace(self, namespace: str):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.core_api.read_namespace(name=namespace)
            )
        except ApiException as e:
            if e.status == 404:
                ns = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=namespace)
                )
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.core_api.create_namespace(body=ns)
                )
    
    async def _wait_for_deployment(
        self,
        name: str,
        namespace: str,
        port: int,
        timeout: int = 300
    ) -> str:
        import time
        start_time = time.time()

        loop = asyncio.get_event_loop()

        while time.time() - start_time < timeout:
            try:
                deployment = await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.read_namespaced_deployment(
                        name=name,
                        namespace=namespace
                    )
                )

                if deployment.status.ready_replicas == deployment.spec.replicas:
                    # 获取service信息
                    service = await loop.run_in_executor(
                        None,
                        lambda: self.core_api.read_namespaced_service(
                            name=f"{name}-svc",
                            namespace=namespace
                        )
                    )

                    # 获取 NodePort
                    node_port = None
                    if service.spec.ports and len(service.spec.ports) > 0:
                        node_port = service.spec.ports[0].node_port

                    if node_port:
                        # 获取任意一个工作节点的 IP
                        nodes = await loop.run_in_executor(
                            None,
                            lambda: self.core_api.list_node()
                        )
                        for node in nodes.items:
                            # 排除 master 节点
                            labels = node.metadata.labels or {}
                            if not any(key.startswith('node-role.kubernetes.io/master') or
                                       key.startswith('node-role.kubernetes.io/control-plane')
                                       for key in labels.keys()):
                                # 获取节点内部 IP
                                for addr in node.status.addresses:
                                    if addr.type == "InternalIP":
                                        return f"http://{addr.address}:{node_port}"

                    # 如果找不到工作节点，返回 service 信息
                    return f"NodePort service created, port: {node_port}"

            except:
                pass

            await asyncio.sleep(5)

        return f"Deployment ready, check NodePort service for access"
    
    async def get_deployment_status(
        self,
        name: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")

        try:
            loop = asyncio.get_event_loop()

            # 获取 deployment 状态
            deployment = await loop.run_in_executor(
                None,
                lambda: self.apps_api.read_namespaced_deployment(
                    name=name,
                    namespace=namespace
                )
            )

            # 获取 pod 状态
            pod_status = "Unknown"
            pod_message = ""
            try:
                pods = await loop.run_in_executor(
                    None,
                    lambda: self.core_api.list_namespaced_pod(
                        namespace=namespace,
                        label_selector=f"app={name}"
                    )
                )

                if pods.items:
                    pod = pods.items[0]
                    pod_status = pod.status.phase

                    # 检查容器状态
                    if pod.status.container_statuses:
                        container = pod.status.container_statuses[0]
                        if container.state.waiting:
                            pod_status = container.state.waiting.reason or "Waiting"
                            pod_message = container.state.waiting.message or ""
                        elif container.state.terminated:
                            pod_status = container.state.terminated.reason or "Terminated"
                            pod_message = container.state.terminated.message or ""

            except Exception as e:
                pod_status = "NotFound"
                pod_message = str(e)

            return {
                "name": name,
                "namespace": namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "pod_status": pod_status,
                "pod_message": pod_message,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "message": c.message
                    }
                    for c in (deployment.status.conditions or [])
                ]
            }
        except ApiException as e:
            if e.status == 404:
                return {"error": "Deployment not found", "pod_status": "NotFound"}
            raise
    
    async def scale_deployment(
        self,
        name: str,
        namespace: str,
        replicas: int
    ) -> bool:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            # 获取当前deployment
            deployment = await loop.run_in_executor(
                None,
                lambda: self.apps_api.read_namespaced_deployment(
                    name=name,
                    namespace=namespace
                )
            )
            
            # 更新replicas
            deployment.spec.replicas = replicas
            
            await loop.run_in_executor(
                None,
                lambda: self.apps_api.replace_namespaced_deployment(
                    name=name,
                    namespace=namespace,
                    body=deployment
                )
            )
            
            return True
        except Exception as e:
            print(f"Scale failed: {e}")
            return False
    
    async def delete_deployment(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            # 删除deployment
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.delete_namespaced_deployment(
                        name=name,
                        namespace=namespace,
                        body=client.V1DeleteOptions(propagation_policy='Foreground')
                    )
                )
                print(f"Deleted deployment: {name}")
            except Exception as e:
                if "NotFound" in str(e):
                    print(f"Deployment {name} not found, may already deleted")
                else:
                    raise e
            
            # 删除service
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.core_api.delete_namespaced_service(
                        name=f"{name}-svc",
                        namespace=namespace
                    )
                )
                print(f"Deleted service: {name}-svc")
            except Exception as e:
                if "NotFound" in str(e):
                    print(f"Service {name}-svc not found, may already deleted")
                else:
                    print(f"Failed to delete service: {e}")
            
            return True
        except Exception as e:
            print(f"Delete failed: {e}")
            raise e
    
    async def list_deployments(
        self,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            if namespace:
                deployments = await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.list_namespaced_deployment(
                        namespace=namespace,
                        label_selector="managed-by=ai-model-deployer"
                    )
                )
            else:
                deployments = await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.list_deployment_for_all_namespaces(
                        label_selector="managed-by=ai-model-deployer"
                    )
                )
            
            result = []
            for dep in deployments.items:
                result.append({
                    "name": dep.metadata.name,
                    "namespace": dep.metadata.namespace,
                    "replicas": dep.spec.replicas,
                    "ready_replicas": dep.status.ready_replicas or 0,
                    "created_at": dep.metadata.creation_timestamp.isoformat() if dep.metadata.creation_timestamp else None
                })
            
            return result
        except Exception as e:
            print(f"List deployments failed: {e}")
            return []
    
    async def get_pod_logs(
        self,
        deployment_name: str,
        namespace: str = "default",
        tail_lines: int = 100
    ) -> str:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            # 获取pods
            pods = await loop.run_in_executor(
                None,
                lambda: self.core_api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"app={deployment_name}"
                )
            )
            
            if not pods.items:
                return "No pods found"
            
            # 获取第一个pod的日志
            pod_name = pods.items[0].metadata.name
            logs = await loop.run_in_executor(
                None,
                lambda: self.core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=tail_lines
                )
            )
            
            return logs
        except Exception as e:
            return f"Failed to get logs: {str(e)}"
    
    async def get_worker_nodes(self) -> List[Dict[str, Any]]:
        """获取所有工作节点（role=worker）"""
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            nodes = await loop.run_in_executor(
                None,
                lambda: self.core_api.list_node()
            )
            
            worker_nodes = []
            for node in nodes.items:
                labels = node.metadata.labels or {}
                
                # 检查是否为工作节点（通过 role 标签或排除 master）
                is_worker = False
                
                # 检查是否有 worker 角色标签
                if labels.get('kubernetes.io/role') == 'worker':
                    is_worker = True
                elif labels.get('node-role.kubernetes.io/worker') == 'true':
                    is_worker = True
                # 或者检查是否不是 master 节点
                elif not any(key.startswith('node-role.kubernetes.io/master') or 
                           key.startswith('node-role.kubernetes.io/control-plane')
                           for key in labels.keys()):
                    is_worker = True
                
                if is_worker:
                    # 获取节点内部 IP
                    internal_ip = None
                    for addr in node.status.addresses:
                        if addr.type == "InternalIP":
                            internal_ip = addr.address
                            break
                    
                    worker_nodes.append({
                        "name": node.metadata.name,
                        "internal_ip": internal_ip,
                        "labels": labels
                    })
            
            return worker_nodes
        except Exception as e:
            print(f"Get worker nodes failed: {e}")
            return []
    
k8s_service = K8sService()
