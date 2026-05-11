from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
import os
import shlex
import base64
from typing import Optional, Dict, Any, List, Callable
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
        source_type: str,
        image_tag: str,
        namespace: str = "default",
        replicas: int = 1,
        resources: Dict[str, Any] = None,
        env_vars: Dict[str, str] = None,
        mount_config: Dict[str, Any] = None,
        command: Optional[str] = None,
        port: int = 8000,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")
        
        resources = resources or {}
        env_vars = env_vars or {}
        mount_config = mount_config or {}
        create_service = source_type != "image"
        
        name_suffix = deployment_name.lower().replace(' ', '-')
        k8s_deployment_name = f"model-{model_id}-{name_suffix}" if model_id > 0 else f"image-{name_suffix}"
        k8s_service_name = f"{k8s_deployment_name}-svc"
        
        # 确保namespace存在
        await self._ensure_namespace(namespace)
        
        try:
            if progress_callback:
                await progress_callback(30, "Creating deployment...")
            
            # 创建Deployment
            deployment = self._create_deployment_object(
                name=k8s_deployment_name,
                source_type=source_type,
                image_tag=image_tag,
                replicas=replicas,
                resources=resources,
                env_vars=env_vars,
                mount_config=mount_config,
                command=command,
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
            
            if create_service:
                if progress_callback:
                    await progress_callback(50, "Creating service...")
                
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
                k8s_deployment_name, namespace, port, create_service=create_service
            )
            
            if progress_callback:
                await progress_callback(100, "Deployment completed")
            
            return {
                "success": True,
                "deployment_name": k8s_deployment_name,
                "service_name": k8s_service_name if create_service else None,
                "namespace": namespace,
                "endpoint": endpoint,
                "replicas": replicas
            }
            
        except Exception as e:
            raise Exception(f"Deployment failed: {str(e)}")
    
    def _create_deployment_object(
        self,
        name: str,
        source_type: str,
        image_tag: str,
        replicas: int,
        resources: Dict[str, Any],
        env_vars: Dict[str, str],
        mount_config: Dict[str, Any],
        command: Optional[str],
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

        volume_mounts = []
        volumes = []
        if mount_config.get("enabled"):
            volume_name = "mounted-storage"
            mount_path = mount_config["mount_path"]
            read_only = bool(mount_config.get("read_only"))
            sub_path = mount_config.get("sub_path") or None

            volume_mounts.append(client.V1VolumeMount(
                name=volume_name,
                mount_path=mount_path,
                read_only=read_only,
                sub_path=sub_path
            ))

            if mount_config.get("type") == "pvc":
                volumes.append(client.V1Volume(
                    name=volume_name,
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=mount_config["claim_name"],
                        read_only=read_only
                    )
                ))
            elif mount_config.get("type") == "nfs":
                volumes.append(client.V1Volume(
                    name=volume_name,
                    nfs=client.V1NFSVolumeSource(
                        server=mount_config["server"],
                        path=mount_config["path"],
                        read_only=read_only
                    )
                ))

        lifecycle = None
        container_command = None
        container_args = None
        liveness_probe = client.V1Probe(
            http_get=client.V1HTTPGetAction(
                path="/health",
                port=port
            ),
            initial_delay_seconds=0,
            period_seconds=30,
            timeout_seconds=10,
            failure_threshold=20
        )
        readiness_probe = client.V1Probe(
            http_get=client.V1HTTPGetAction(
                path="/health",
                port=port
            ),
            initial_delay_seconds=5,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3
        )
        startup_probe = client.V1Probe(
            http_get=client.V1HTTPGetAction(
                path="/health",
                port=port
            ),
            initial_delay_seconds=10,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=60
        )

        if source_type == "image":
            # Keep generic image deployments alive even when the image has no long-running foreground process.
            container_command = ["/bin/sh", "-c"]
            container_args = ["while true; do sleep 3600; done"]
            liveness_probe = None
            readiness_probe = None
            startup_probe = None
        elif command and command.strip():
            lifecycle = client.V1Lifecycle(
                post_start=client.V1LifecycleHandler(
                    _exec=client.V1ExecAction(
                        command=["/bin/sh", "-lc", command.strip()]
                    )
                )
            )
        
        container = client.V1Container(
            name="model",
            image=image_tag,
            image_pull_policy="Never" if image_tag.startswith("ai-model:") else "IfNotPresent",
            command=container_command,
            args=container_args,
            ports=None if source_type == "image" else [client.V1ContainerPort(container_port=port)],
            resources=resource_requirements,
            env=env,
            volume_mounts=volume_mounts or None,
            lifecycle=lifecycle,
            liveness_probe=liveness_probe,
            readiness_probe=readiness_probe,
            startup_probe=startup_probe
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
                volumes=volumes or None,
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
        create_service: bool = True,
        timeout: int = 300
    ) -> str:
        import time
        start_time = time.time()

        loop = asyncio.get_event_loop()
        last_error = None

        while time.time() - start_time < timeout:
            try:
                deployment = await loop.run_in_executor(
                    None,
                    lambda: self.apps_api.read_namespaced_deployment(
                        name=name,
                        namespace=namespace
                    )
                )

                pods = await loop.run_in_executor(
                    None,
                    lambda: self.core_api.list_namespaced_pod(
                        namespace=namespace,
                        label_selector=f"app={name}"
                    )
                )

                if pods.items and pods.items[0].status.container_statuses:
                    container = pods.items[0].status.container_statuses[0]
                    if container.state.waiting:
                        waiting_reason = container.state.waiting.reason or "Waiting"
                        waiting_message = container.state.waiting.message or ""
                        if waiting_reason in {"ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "CreateContainerConfigError", "CreateContainerError"}:
                            raise Exception(f"Pod failed: {waiting_reason} - {waiting_message}" if waiting_message else f"Pod failed: {waiting_reason}")
                    elif container.state.terminated:
                        terminated_reason = container.state.terminated.reason or "Terminated"
                        terminated_message = container.state.terminated.message or ""
                        raise Exception(f"Pod terminated: {terminated_reason} - {terminated_message}" if terminated_message else f"Pod terminated: {terminated_reason}")

                if deployment.status.ready_replicas == deployment.spec.replicas:
                    if not create_service:
                        return ""
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

            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                if any(keyword in error_text for keyword in [
                    "Pod failed:",
                    "Pod terminated:",
                    "CreateContainerConfigError",
                    "CreateContainerError",
                    "ImagePullBackOff",
                    "ErrImagePull",
                    "CrashLoopBackOff"
                ]):
                    raise

            await asyncio.sleep(5)

        if last_error:
            raise Exception(f"Deployment rollout timed out after {timeout}s: {last_error}")
        raise Exception(f"Deployment rollout timed out after {timeout}s")
    
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

    async def get_ready_pod_name(self, deployment_name: str, namespace: str = "default") -> str:
        if not self.is_connected:
            raise Exception("Kubernetes is not connected")

        loop = asyncio.get_event_loop()
        pods = await loop.run_in_executor(
            None,
            lambda: self.core_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )
        )

        for pod in pods.items:
            phase = pod.status.phase
            conditions = {condition.type: condition.status for condition in (pod.status.conditions or [])}
            if phase == "Running" and conditions.get("Ready") == "True":
                return pod.metadata.name

        raise Exception("No ready pod found for deployment")

    def _exec_in_pod_sync(self, pod_name: str, namespace: str, shell_command: str) -> Dict[str, Any]:
        wrapped_command = (
            "STDOUT_FILE=$(mktemp)\n"
            "STDERR_FILE=$(mktemp)\n"
            "(\n"
            f"{shell_command}\n"
            ") >\"$STDOUT_FILE\" 2>\"$STDERR_FILE\" &\n"
            "CMD_PID=$!\n"
            "while kill -0 \"$CMD_PID\" 2>/dev/null; do\n"
            "  printf '__CMD_KEEPALIVE__\\n'\n"
            "  sleep 10\n"
            "done\n"
            "wait \"$CMD_PID\"\n"
            "exit_code=$?\n"
            "printf '__CMD_STDOUT_BEGIN__\\n'\n"
            "cat \"$STDOUT_FILE\"\n"
            "printf '\\n__CMD_STDOUT_END__\\n__CMD_STDERR_BEGIN__\\n'\n"
            "cat \"$STDERR_FILE\"\n"
            "printf '\\n__CMD_STDERR_END__\\n__CMD_EXIT_CODE__=%s\\n' \"$exit_code\"\n"
            "rm -f \"$STDOUT_FILE\" \"$STDERR_FILE\"\n"
        )
        response = stream(
            self.core_api.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=["/bin/sh", "-lc", wrapped_command],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=True
        )

        payload = response if isinstance(response, str) else str(response or "")
        stdout = ""
        stderr = ""
        exit_code = 1

        stdout_marker_start = "__CMD_STDOUT_BEGIN__\n"
        stdout_marker_end = "\n__CMD_STDOUT_END__\n"
        stderr_marker_start = "__CMD_STDERR_BEGIN__\n"
        stderr_marker_end = "\n__CMD_STDERR_END__\n"
        exit_marker = "__CMD_EXIT_CODE__="

        if stdout_marker_start in payload and stdout_marker_end in payload:
            stdout = payload.split(stdout_marker_start, 1)[1].split(stdout_marker_end, 1)[0]
        if stderr_marker_start in payload and stderr_marker_end in payload:
            stderr = payload.split(stderr_marker_start, 1)[1].split(stderr_marker_end, 1)[0]
        if exit_marker in payload:
            try:
                exit_code = int(payload.rsplit(exit_marker, 1)[1].strip().splitlines()[0])
            except Exception:
                exit_code = 1
        elif payload.strip():
            stderr = payload.strip()
        return {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "exit_code": exit_code
        }

    def _clean_stream_chunk(self, chunk: str, marker: str) -> str:
        if not chunk:
            return ""
        return chunk.replace(f"{marker}\n", "").replace(marker, "")

    async def exec_in_pod(self, pod_name: str, namespace: str, shell_command: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._exec_in_pod_sync(pod_name, namespace, shell_command)
        )

    def _exec_in_pod_streaming_sync(
        self,
        pod_name: str,
        namespace: str,
        shell_command: str,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        heartbeat_marker = "__CMD_KEEPALIVE__"
        exit_marker = "__CMD_EXIT_CODE__="
        wrapped_command = (
            "(\n"
            "  while true; do\n"
            f"    printf '{heartbeat_marker}\\n' >&2\n"
            "    sleep 10\n"
            "  done\n"
            ") &\n"
            "HEARTBEAT_PID=$!\n"
            f"{shell_command}\n"
            "exit_code=$?\n"
            "kill \"$HEARTBEAT_PID\" >/dev/null 2>&1 || true\n"
            "wait \"$HEARTBEAT_PID\" 2>/dev/null || true\n"
            f"printf '\\n{exit_marker}%s\\n' \"$exit_code\"\n"
        )
        response = stream(
            self.core_api.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=["/bin/sh", "-lc", wrapped_command],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False
        )

        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        try:
            while response.is_open():
                response.update(timeout=1)
                if response.peek_stdout():
                    chunk = response.read_stdout()
                    if chunk:
                        stdout_chunks.append(chunk)
                        clean_chunk = chunk.split(exit_marker, 1)[0] if exit_marker in chunk else chunk
                        if clean_chunk and on_log:
                            on_log(clean_chunk)
                if response.peek_stderr():
                    chunk = response.read_stderr()
                    if chunk:
                        clean_chunk = self._clean_stream_chunk(chunk, heartbeat_marker)
                        if clean_chunk:
                            stderr_chunks.append(clean_chunk)
                            if on_log:
                                on_log(clean_chunk)
            response.close()
        except Exception as exc:
            response.close()
            joined_stdout = "".join(stdout_chunks)
            if exit_marker not in joined_stdout:
                raise exc

        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)
        exit_code = 1
        if exit_marker in stdout:
            stdout, _, tail = stdout.rpartition(exit_marker)
            try:
                exit_code = int(tail.strip().splitlines()[0])
            except Exception:
                exit_code = 1

        return {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "exit_code": exit_code
        }

    async def exec_in_pod_streaming(
        self,
        pod_name: str,
        namespace: str,
        shell_command: str,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._exec_in_pod_streaming_sync(pod_name, namespace, shell_command, on_log=on_log)
        )

    async def list_container_files(
        self,
        pod_name: str,
        namespace: str,
        result_path: str,
        allow_missing: bool = False
    ) -> List[Dict[str, Any]]:
        root_quoted = shlex.quote(result_path)
        missing_dir_command = "exit 0" if allow_missing else 'echo "Result directory not found: $ROOT" >&2; exit 11'
        command = (
            f"ROOT={root_quoted}; "
            f'if [ ! -d "$ROOT" ]; then {missing_dir_command}; fi; '
            'find "$ROOT" -type f -exec sh -c \'for f do rel="${f#"$1"/}"; size=$(wc -c < "$f" | tr -d " "); '
            'mtime=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0); '
            'printf "%s\\t%s\\t%s\\n" "$rel" "$size" "$mtime"; done\' sh "$ROOT" {} +'
        )
        result = await self.exec_in_pod(pod_name, namespace, command)
        if result["exit_code"] != 0:
            raise Exception(result["stderr"] or "Failed to list container result files")

        from app.services.inference_service import build_file_entry

        files = []
        for line in result["stdout"].splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            relative_path = parts[0]
            size = parts[1]
            mtime = parts[2] if len(parts) > 2 else "0"
            if not relative_path:
                continue
            try:
                files.append(build_file_entry(
                    relative_path.strip(),
                    int(size.strip() or "0"),
                    int(mtime.strip() or "0")
                ))
            except ValueError:
                continue
        return sorted(files, key=lambda item: item["relative_path"])

    async def read_container_file_bytes(self, pod_name: str, namespace: str, file_path: str) -> bytes:
        file_quoted = shlex.quote(file_path)
        command = (
            f'FILE={file_quoted}; '
            'if [ ! -f "$FILE" ]; then echo "Result file not found: $FILE" >&2; exit 12; fi; '
            'base64 "$FILE" | tr -d "\\n"'
        )
        result = await self.exec_in_pod(pod_name, namespace, command)
        if result["exit_code"] != 0:
            raise Exception(result["stderr"] or "Failed to read container file")
        return base64.b64decode(result["stdout"].encode("ascii"))

    async def read_container_text_file(
        self,
        pod_name: str,
        namespace: str,
        file_path: str,
        max_bytes: int = 1024 * 1024
    ) -> str:
        file_quoted = shlex.quote(file_path)
        command = (
            f'FILE={file_quoted}; '
            'if [ ! -f "$FILE" ]; then echo "Result file not found: $FILE" >&2; exit 12; fi; '
            f'head -c {max_bytes} "$FILE"'
        )
        result = await self.exec_in_pod(pod_name, namespace, command)
        if result["exit_code"] != 0:
            raise Exception(result["stderr"] or "Failed to read container text file")
        return result["stdout"]
    
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
