import os
import shutil
import subprocess
from typing import Any, Dict, List

from app.core.config import settings
from app.services.k8s_service import k8s_service


class NFSDiscoveryError(Exception):
    pass


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _get_control_plane_hosts() -> List[str]:
    if not k8s_service.is_connected or not k8s_service.core_api:
        return []

    try:
        nodes = k8s_service.core_api.list_node()
    except Exception:
        return []

    hosts = []
    for node in nodes.items:
        labels = node.metadata.labels or {}
        is_control_plane = any(
            key.startswith("node-role.kubernetes.io/master")
            or key.startswith("node-role.kubernetes.io/control-plane")
            for key in labels.keys()
        )
        if not is_control_plane:
            continue

        for address in node.status.addresses or []:
            if address.type == "InternalIP" and address.address:
                hosts.append(address.address)
                break

        if node.metadata.name:
            hosts.append(node.metadata.name)

    return _dedupe(hosts)


def _get_showmount_targets() -> List[str]:
    configured_host = (settings.K8S_NFS_SHOWMOUNT_HOST or "").strip()
    configured_server = (settings.K8S_NFS_SERVER or "").strip()
    candidates = [configured_host, configured_server]
    candidates.extend(_get_control_plane_hosts())
    candidates.extend(["host.docker.internal", "127.0.0.1", "localhost"])
    return _dedupe(candidates)


def _parse_showmount_output(output: str) -> List[str]:
    exports = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("export list for "):
            continue
        path = line.split()[0]
        if path.startswith("/"):
            exports.append(path.rstrip("/") or "/")
    return exports


def _run_showmount() -> Dict[str, Any]:
    binary = shutil.which("showmount")
    if not binary:
        raise NFSDiscoveryError("showmount command is not available in backend container")

    attempts = []
    for target in _get_showmount_targets():
        try:
            result = subprocess.run(
                [binary, "-e", target],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
        except Exception as exc:
            attempts.append(f"{target}: {exc}")
            continue

        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            attempts.append(f"{target}: {stderr or f'exit code {result.returncode}'}")
            continue

        exports = _parse_showmount_output(result.stdout or "")
        if exports:
            return {
                "target": target,
                "exports": exports
            }

        attempts.append(f"{target}: no exports found")

    raise NFSDiscoveryError("Unable to discover NFS exports via showmount. " + "; ".join(attempts))


def discover_nfs_config() -> Dict[str, Any]:
    configured_server = (settings.K8S_NFS_SERVER or "").strip()
    configured_export_root = (settings.K8S_NFS_EXPORT_ROOT or "").strip().rstrip("/")
    configured_browse_root = (settings.K8S_NFS_BROWSE_ROOT or "").strip()

    if configured_server and configured_export_root:
        export_root = configured_export_root or "/"
        return {
            "server": configured_server,
            "export_root": export_root or "/",
            "browse_root": configured_browse_root or export_root or "/",
            "showmount_host": None,
            "exports": [export_root or "/"],
            "source": "settings"
        }

    showmount_info = _run_showmount()
    control_plane_hosts = _get_control_plane_hosts()
    export_root = configured_export_root or showmount_info["exports"][0]
    server = configured_server or (control_plane_hosts[0] if control_plane_hosts else showmount_info["target"])

    return {
        "server": server,
        "export_root": export_root,
        "browse_root": configured_browse_root or export_root,
        "showmount_host": showmount_info["target"],
        "exports": showmount_info["exports"],
        "source": "showmount"
    }


def get_nfs_browse_root() -> str:
    browse_root = os.path.realpath(discover_nfs_config()["browse_root"])
    if not os.path.exists(browse_root):
        raise NFSDiscoveryError(
            f"NFS browse root does not exist in backend container: {browse_root}"
        )
    if not os.path.isdir(browse_root):
        raise NFSDiscoveryError(f"NFS browse root is not a directory: {browse_root}")
    return browse_root


def resolve_nfs_browse_path(relative_path: str = "") -> str:
    root = get_nfs_browse_root()
    normalized = (relative_path or "").replace("\\", "/").strip("/")
    candidate = os.path.realpath(os.path.join(root, normalized))
    if candidate != root and not candidate.startswith(f"{root}{os.sep}"):
        raise NFSDiscoveryError("Invalid NFS browse path")
    return candidate
