from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

from .info import render_info
from .lifecycle import NOOP_LIFECYCLE_NAMES, noop_script, render_start_stop_status
from .lint import has_errors, lint_manifest
from .model import Manifest


@dataclass(frozen=True)
class BuildResult:
    output: Path
    sha256: str
    outer_members: tuple[str, ...]
    payload_members: tuple[str, ...]


def _tarinfo(name: str, size: int, mode: int) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.size = size
    item.mode = mode
    item.uid = item.gid = 0
    item.uname = item.gname = ""
    item.mtime = 0
    return item


def _safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe archive path: {name!r}")
    return path.as_posix()


def _add_bytes(tf: tarfile.TarFile, name: str, data: bytes, mode: int) -> None:
    name = _safe_name(name)
    tf.addfile(_tarinfo(name, len(data), mode), io.BytesIO(data))


def _privilege_bytes(manifest: Manifest) -> bytes:
    payload: dict[str, object] = {"defaults": {"run-as": manifest.privilege.run_as}}
    if manifest.privilege.username:
        payload["username"] = manifest.privilege.username
    if manifest.privilege.groupname:
        payload["groupname"] = manifest.privilege.groupname
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _wizard_members(root: Path) -> list[tuple[str, bytes, int]]:
    result: list[tuple[str, bytes, int]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        result.append((f"WIZARD_UIFILES/{rel}", path.read_bytes(), 0o644))
    return result


def build_spk(manifest: Manifest, output: Path) -> BuildResult:
    issues = lint_manifest(manifest)
    if has_errors(issues):
        details = "; ".join(f"{i.code}: {i.message}" for i in issues if i.severity == "error")
        raise ValueError(f"manifest lint failed: {details}")

    payload_members: list[tuple[str, bytes, int]] = []
    for entry in manifest.payload_files:
        payload_members.append(
            (entry.destination.as_posix(), entry.source.read_bytes(), entry.mode)
        )
    payload_members.sort(key=lambda row: row[0])

    inner_raw = io.BytesIO()
    with tarfile.open(fileobj=inner_raw, mode="w:") as inner:
        for name, data, mode in payload_members:
            _add_bytes(inner, name, data, mode)

    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0, filename="", compresslevel=9) as gz:
        gz.write(inner_raw.getvalue())
    package_tgz = compressed.getvalue()

    outer: list[tuple[str, bytes, int]] = [
        ("INFO", render_info(manifest), 0o644),
        ("conf/privilege", _privilege_bytes(manifest), 0o644),
        ("package.tgz", package_tgz, 0o644),
        ("scripts/start-stop-status", render_start_stop_status(manifest), 0o755),
    ]
    for name in NOOP_LIFECYCLE_NAMES:
        outer.append((f"scripts/{name}", noop_script(), 0o755))

    if manifest.assets.resource_file is not None:
        outer.append(("conf/resource", manifest.assets.resource_file.read_bytes(), 0o644))
    if manifest.assets.license_file is not None:
        outer.append(("LICENSE", manifest.assets.license_file.read_bytes(), 0o644))
    if manifest.assets.icon64 is not None:
        outer.append(("PACKAGE_ICON.PNG", manifest.assets.icon64.read_bytes(), 0o644))
    if manifest.assets.icon256 is not None:
        outer.append(("PACKAGE_ICON_256.PNG", manifest.assets.icon256.read_bytes(), 0o644))
    if manifest.assets.wizard_dir is not None:
        outer.extend(_wizard_members(manifest.assets.wizard_dir))

    names = [name for name, _, _ in outer]
    if len(names) != len(set(names)):
        raise ValueError("duplicate outer archive member")
    outer.sort(key=lambda row: row[0])

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, mode="w:") as tf:
        for name, data, mode in outer:
            _add_bytes(tf, name, data, mode)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return BuildResult(
        output=output,
        sha256=digest,
        outer_members=tuple(name for name, _, _ in outer),
        payload_members=tuple(name for name, _, _ in payload_members),
    )
