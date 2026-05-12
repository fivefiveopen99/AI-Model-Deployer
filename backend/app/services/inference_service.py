import base64
import hashlib
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.services.nfs_service import NFSDiscoveryError, discover_nfs_config, get_nfs_browse_root


TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".jfif", ".avif"}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log"}
PDF_EXTENSIONS = {".pdf"}
OFFICE_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx"}


def parse_template_variables(command_template: str) -> List[str]:
    seen = set()
    variables = []
    for match in TEMPLATE_VAR_RE.finditer(command_template or ""):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        variables.append(name)
    return variables


def normalize_inference_config(
    source_type: str,
    inference_config: Optional[Dict[str, Any]],
    mount_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    source_type = (source_type or "").strip().lower()
    if source_type != "image":
        return {}

    config = dict(inference_config or {})
    command_template = (config.get("command_template") or "").strip()
    result_path = (config.get("result_path") or "").strip()
    enabled = bool(command_template and result_path)
    result_source = "container"
    mount_path = (mount_config or {}).get("mount_path") or ""
    mount_enabled = bool((mount_config or {}).get("enabled")) and bool(mount_path and result_path)
    normalized_mount_path = mount_path.rstrip("/")
    normalized_result_path = result_path.rstrip("/")
    if mount_enabled and (
        normalized_result_path == normalized_mount_path
        or normalized_result_path.startswith(f"{normalized_mount_path}/")
    ):
        result_source = "mount"

    variable_names = parse_template_variables(command_template)
    configured_names = [
        str(name).strip() for name in (config.get("variable_names") or []) if str(name).strip()
    ]
    if configured_names:
        merged = []
        seen = set()
        for name in configured_names + variable_names:
            if name and name not in seen:
                seen.add(name)
                merged.append(name)
        variable_names = merged

    return {
        "enabled": enabled,
        "command_template": command_template,
        "variable_names": variable_names,
        "result_source": result_source,
        "result_path": result_path,
    }


def render_command_template(command_template: str, variables: Dict[str, Any], variable_names: List[str]) -> str:
    values = {key: "" if value is None else str(value) for key, value in (variables or {}).items()}
    missing = [name for name in variable_names if not values.get(name, "").strip()]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing inference variables: {', '.join(missing)}")

    def replacer(match: re.Match[str]) -> str:
        name = match.group(1)
        return values.get(name, "")

    rendered = TEMPLATE_VAR_RE.sub(replacer, command_template or "")
    return rendered.strip()


def build_file_key(relative_path: str) -> str:
    encoded = base64.urlsafe_b64encode(relative_path.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_file_key(file_key: str) -> str:
    padding = "=" * (-len(file_key) % 4)
    return base64.urlsafe_b64decode(f"{file_key}{padding}".encode("ascii")).decode("utf-8")


def classify_file(relative_path: str) -> Tuple[str, bool]:
    extension = Path(relative_path).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image", True
    if extension in TEXT_EXTENSIONS:
        return "text", True
    if extension in PDF_EXTENSIONS:
        return "pdf", True
    if extension in OFFICE_EXTENSIONS:
        return "office", False
    guessed_type, _ = mimetypes.guess_type(relative_path)
    if guessed_type and guessed_type.startswith("image/"):
        return "image", True
    return "other", False


def build_file_entry(relative_path: str, size: int, mtime: Optional[int] = None) -> Dict[str, Any]:
    kind, previewable = classify_file(relative_path)
    item = {
        "file_key": build_file_key(relative_path),
        "name": os.path.basename(relative_path),
        "relative_path": relative_path.replace("\\", "/"),
        "kind": kind,
        "size": int(size),
        "previewable": previewable,
        "downloadable": True,
    }
    if mtime is not None:
        item["mtime"] = int(mtime)
    return item


def normalize_relative_path(root_path: str, target_path: str) -> str:
    root = os.path.realpath(root_path)
    target = os.path.realpath(target_path)
    if target != root and not target.startswith(f"{root}{os.sep}"):
        raise HTTPException(status_code=400, detail="Result path escapes configured root")
    rel = os.path.relpath(target, root).replace("\\", "/")
    return "" if rel == "." else rel


def resolve_mount_result_root(mount_config: Dict[str, Any], inference_config: Dict[str, Any]) -> str:
    if not mount_config.get("enabled"):
        raise HTTPException(status_code=400, detail="Deployment has no mounted storage configured")
    if mount_config.get("type") != "nfs":
        raise HTTPException(status_code=400, detail="Mount result browsing currently supports NFS mounts only")

    container_mount_path = (mount_config.get("mount_path") or "").rstrip("/")
    result_path = (inference_config.get("result_path") or "").rstrip("/")
    if not container_mount_path or not result_path:
        raise HTTPException(status_code=400, detail="Mount path or result path is missing")
    if result_path != container_mount_path and not result_path.startswith(f"{container_mount_path}/"):
        raise HTTPException(status_code=400, detail="Result path must be inside the configured mount path")

    try:
        nfs_config = discover_nfs_config()
        browse_root = get_nfs_browse_root()
    except NFSDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    export_root = nfs_config["export_root"].rstrip("/") or "/"
    mount_export_path = (mount_config.get("path") or "").rstrip("/")
    if mount_export_path != export_root and not mount_export_path.startswith(f"{export_root}/"):
        raise HTTPException(status_code=400, detail="Mounted NFS path is outside the discovered export root")

    mount_rel = os.path.relpath(mount_export_path, export_root).replace("\\", "/")
    result_rel = os.path.relpath(result_path, container_mount_path).replace("\\", "/")
    parts = [browse_root]
    if mount_rel != ".":
        parts.append(mount_rel)
    if result_rel != ".":
        parts.append(result_rel)
    return os.path.realpath(os.path.join(*parts))


def scan_mount_result_files(result_root: str) -> List[Dict[str, Any]]:
    if not os.path.exists(result_root):
        raise HTTPException(status_code=400, detail=f"Result path does not exist: {result_root}")
    if not os.path.isdir(result_root):
        raise HTTPException(status_code=400, detail=f"Result path is not a directory: {result_root}")

    files = []
    for current_root, _, filenames in os.walk(result_root):
        for filename in sorted(filenames):
            full_path = os.path.join(current_root, filename)
            relative_path = normalize_relative_path(result_root, full_path)
            files.append(build_file_entry(
                relative_path,
                os.path.getsize(full_path),
                int(os.path.getmtime(full_path))
            ))

    return sorted(files, key=lambda item: item["relative_path"])


def resolve_mount_file_path(result_root: str, relative_path: str) -> str:
    relative = (relative_path or "").replace("\\", "/").strip("/")
    candidate = os.path.realpath(os.path.join(result_root, relative))
    root = os.path.realpath(result_root)
    if candidate != root and not candidate.startswith(f"{root}{os.sep}"):
        raise HTTPException(status_code=400, detail="Invalid result file path")
    if not os.path.exists(candidate):
        raise HTTPException(status_code=404, detail="Result file not found")
    if os.path.isdir(candidate):
        raise HTTPException(status_code=400, detail="Result file path points to a directory")
    return candidate


def find_result_file(files: List[Dict[str, Any]], file_key: str) -> Dict[str, Any]:
    for item in files or []:
        if item.get("file_key") == file_key:
            return item
    raise HTTPException(status_code=404, detail="Result file not found")


def build_empty_inference_result() -> Dict[str, Any]:
    return {
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "files": [],
        "result_digest": "",
    }


def merge_inference_result(previous: Dict[str, Any], latest: Dict[str, Any]) -> Dict[str, Any]:
    previous = dict(previous or {})
    merged = dict(previous)
    merged.update(latest)
    if latest.get("files"):
        merged["files"] = latest["files"]
    else:
        merged["files"] = previous.get("files", [])
    return merged


def get_media_type(file_name: str) -> str:
    media_type, _ = mimetypes.guess_type(file_name)
    return media_type or "application/octet-stream"


def build_result_digest(command_template: str, variables: Dict[str, Any], result_path: str) -> str:
    digest_source = f"{command_template}|{variables}|{result_path}"
    return hashlib.sha1(digest_source.encode("utf-8")).hexdigest()


def select_generated_files(before_files: List[Dict[str, Any]], after_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    before_index = {
        item["relative_path"]: (int(item.get("size", 0)), int(item.get("mtime", 0)))
        for item in (before_files or [])
    }
    generated = []
    for item in after_files or []:
        signature = (int(item.get("size", 0)), int(item.get("mtime", 0)))
        if before_index.get(item["relative_path"]) != signature:
            generated.append(item)
    if generated:
        return generated
    if before_files:
        return []
    return list(after_files or [])
