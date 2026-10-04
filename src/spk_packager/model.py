from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any

from .profiles import get_profile
from .versioning import DSMVersion, validate_package_version

_SAFE_PACKAGE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_SCRIPT_NAMES = (
    "start_stop_status",
    "preinst",
    "postinst",
    "preuninst",
    "postuninst",
    "preupgrade",
    "postupgrade",
)


@dataclass(frozen=True)
class PayloadFile:
    source: Path
    destination: PurePosixPath
    mode: int = 0o644
    expected_elf_machine: int | None = None


@dataclass(frozen=True)
class PackageConfig:
    package_id: str
    version: str
    description: str
    maintainer: str
    arch: tuple[str, ...]
    os_min_ver: str
    display_name: str | None = None
    os_max_ver: str | None = None
    thirdparty: bool = True
    precheckstartstop: bool = True
    ctl_stop: bool | None = None
    allow_noarch_native_bundle: bool = False


@dataclass(frozen=True)
class ServiceConfig:
    enabled: bool = True
    command: str | None = None
    args: tuple[str, ...] = ()
    pid_file: str = "service.pid"
    log_file: str = "service.log"
    state_dirs: tuple[str, ...] = ()
    start_probe_seconds: int = 1
    stop_timeout_seconds: int = 10


@dataclass(frozen=True)
class PrivilegeTool:
    relpath: PurePosixPath
    user: str = "package"
    group: str = "package"
    permission: str = "0700"
    capabilities: str | None = None


@dataclass(frozen=True)
class PrivilegeConfig:
    run_as: str = "package"
    username: str | None = None
    groupname: str | None = None
    tools: tuple[PrivilegeTool, ...] = ()


@dataclass(frozen=True)
class AssetsConfig:
    icon64: Path | None = None
    icon256: Path | None = None
    license_file: Path | None = None
    wizard_dir: Path | None = None
    resource_file: Path | None = None


@dataclass(frozen=True)
class ScriptsConfig:
    start_stop_status: Path | None = None
    preinst: Path | None = None
    postinst: Path | None = None
    preuninst: Path | None = None
    postuninst: Path | None = None
    preupgrade: Path | None = None
    postupgrade: Path | None = None

    def as_dict(self) -> dict[str, Path | None]:
        return {name: getattr(self, name) for name in _SCRIPT_NAMES}


@dataclass(frozen=True)
class Manifest:
    path: Path
    profile_id: str
    strict: bool
    package: PackageConfig
    service: ServiceConfig
    privilege: PrivilegeConfig
    assets: AssetsConfig
    scripts: ScriptsConfig
    payload_files: tuple[PayloadFile, ...]
    info_extra: dict[str, str] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self.path.parent


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"[{name}] must be a table")
    return value


def _relative_posix(value: str, field_name: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or str(path) in {"", "."}:
        raise ValueError(f"{field_name} must be a safe relative POSIX path")
    return path


def _mode(value: Any) -> int:
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        result = int(value, 8)
    else:
        raise ValueError("payload file mode must be an integer or octal string")
    if result < 0 or result > 0o7777:
        raise ValueError(f"invalid file mode: {result:o}")
    return result


def _local_path(base: Path, value: Any) -> Path:
    return (base / str(value)).resolve()


def load_manifest(path: str | Path) -> Manifest:
    manifest_path = Path(path).resolve()
    with manifest_path.open("rb") as handle:
        raw = tomllib.load(handle)

    compatibility = _section(raw, "compatibility")
    profile_id = str(compatibility.get("profile", "dsm-7.2.2+"))
    get_profile(profile_id)
    strict = bool(compatibility.get("strict", True))

    pkg = _section(raw, "package")
    package_id = str(pkg.get("id", ""))
    if not package_id or not _SAFE_PACKAGE_ID.fullmatch(package_id):
        raise ValueError("package.id must use only letters, digits, '.', '_' or '-'")
    version = str(pkg.get("version", ""))
    validate_package_version(version)

    arch_raw = pkg.get("arch", ["noarch"])
    if isinstance(arch_raw, str):
        arch = (arch_raw,)
    elif isinstance(arch_raw, list) and all(isinstance(x, str) and x for x in arch_raw):
        arch = tuple(arch_raw)
    else:
        raise ValueError("package.arch must be a string or list of strings")

    os_min_ver = str(pkg.get("os_min_ver", ""))
    DSMVersion.parse(os_min_ver)
    os_max_ver = pkg.get("os_max_ver")
    if os_max_ver is not None:
        os_max_ver = str(os_max_ver)
        DSMVersion.parse(os_max_ver)

    package = PackageConfig(
        package_id=package_id,
        display_name=str(pkg["display_name"]) if "display_name" in pkg else None,
        version=version,
        description=str(pkg.get("description", "")),
        maintainer=str(pkg.get("maintainer", "")),
        arch=arch,
        os_min_ver=os_min_ver,
        os_max_ver=os_max_ver,
        thirdparty=bool(pkg.get("thirdparty", True)),
        precheckstartstop=bool(pkg.get("precheckstartstop", True)),
        ctl_stop=(bool(pkg["ctl_stop"]) if "ctl_stop" in pkg else None),
        allow_noarch_native_bundle=bool(pkg.get("allow_noarch_native_bundle", False)),
    )
    if not package.description:
        raise ValueError("package.description is required")
    if not package.maintainer:
        raise ValueError("package.maintainer is required")

    svc = _section(raw, "service")
    enabled = bool(svc.get("enabled", True))
    command = str(svc["command"]) if "command" in svc else None
    if enabled and not command:
        raise ValueError("service.command is required when service.enabled=true")
    if command is not None:
        _relative_posix(command, "service.command")

    args = svc.get("args", [])
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("service.args must be an array of strings")
    if any("\x00" in x or "\n" in x or "\r" in x for x in args):
        raise ValueError("service.args may not contain NUL, newline, or carriage return")
    state_dirs = svc.get("state_dirs", [])
    if not isinstance(state_dirs, list) or not all(isinstance(x, str) for x in state_dirs):
        raise ValueError("service.state_dirs must be an array of strings")
    for item in state_dirs:
        _relative_posix(item, "service.state_dirs[]")

    pid_file = str(svc.get("pid_file", "service.pid"))
    log_file = str(svc.get("log_file", "service.log"))
    _relative_posix(pid_file, "service.pid_file")
    _relative_posix(log_file, "service.log_file")
    service = ServiceConfig(
        enabled=enabled,
        command=command,
        args=tuple(args),
        pid_file=pid_file,
        log_file=log_file,
        state_dirs=tuple(state_dirs),
        start_probe_seconds=int(svc.get("start_probe_seconds", 1)),
        stop_timeout_seconds=int(svc.get("stop_timeout_seconds", 10)),
    )
    if service.start_probe_seconds < 0 or service.stop_timeout_seconds < 1:
        raise ValueError("service timing values are out of range")

    priv = _section(raw, "privilege")
    raw_tools = priv.get("tool", [])
    if not isinstance(raw_tools, list):
        raise ValueError("[[privilege.tool]] must be an array of tables")
    privilege_tools: list[PrivilegeTool] = []
    capability_re = re.compile(r"^cap_[a-z0-9_]+(?:,cap_[a-z0-9_]+)*$")
    permission_re = re.compile(r"^[0-7]{4}$")
    for index, item in enumerate(raw_tools):
        if not isinstance(item, dict):
            raise ValueError(f"privilege.tool[{index}] must be a table")
        relpath = _relative_posix(
            str(item.get("relpath", "")),
            f"privilege.tool[{index}].relpath",
        )
        user = str(item.get("user", "package"))
        group = str(item.get("group", "package"))
        permission = str(item.get("permission", "0700"))
        capabilities = (
            str(item["capabilities"]) if "capabilities" in item else None
        )
        if user != "package" or group != "package":
            raise ValueError("privilege.tool user and group must both be 'package'")
        if not permission_re.fullmatch(permission):
            raise ValueError(
                f"privilege.tool[{index}].permission must be four octal digits"
            )
        if capabilities is not None and not capability_re.fullmatch(capabilities):
            raise ValueError(
                f"privilege.tool[{index}].capabilities must be comma-separated cap_* names"
            )
        privilege_tools.append(
            PrivilegeTool(
                relpath=relpath,
                user=user,
                group=group,
                permission=permission,
                capabilities=capabilities,
            )
        )

    privilege = PrivilegeConfig(
        run_as=str(priv.get("run_as", "package")),
        username=str(priv["username"]) if "username" in priv else None,
        groupname=str(priv["groupname"]) if "groupname" in priv else None,
        tools=tuple(privilege_tools),
    )
    if privilege.run_as not in {"package", "root"}:
        raise ValueError("privilege.run_as must be 'package' or 'root'")

    assets_raw = _section(raw, "assets")
    def asset(key: str) -> Path | None:
        return _local_path(manifest_path.parent, assets_raw[key]) if key in assets_raw else None

    assets = AssetsConfig(
        icon64=asset("icon64"),
        icon256=asset("icon256"),
        license_file=asset("license"),
        wizard_dir=asset("wizard_dir"),
        resource_file=asset("resource"),
    )

    scripts_raw = _section(raw, "scripts")
    scripts_kwargs: dict[str, Path | None] = {}
    for name in _SCRIPT_NAMES:
        scripts_kwargs[name] = (
            _local_path(manifest_path.parent, scripts_raw[name])
            if name in scripts_raw else None
        )
    scripts = ScriptsConfig(**scripts_kwargs)

    payload = _section(raw, "payload")
    entries = payload.get("files", [])
    if not isinstance(entries, list):
        raise ValueError("[[payload.files]] entries are required")
    payload_files: list[PayloadFile] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"payload.files[{index}] must be a table")
        source_value = str(entry.get("source", ""))
        if not source_value:
            raise ValueError(f"payload.files[{index}].source is required")
        source = _local_path(manifest_path.parent, source_value)
        destination = _relative_posix(
            str(entry.get("destination", "")),
            f"payload.files[{index}].destination",
        )
        expected = entry.get("expected_elf_machine")
        payload_files.append(
            PayloadFile(
                source=source,
                destination=destination,
                mode=_mode(entry.get("mode", "0644")),
                expected_elf_machine=(int(expected) if expected is not None else None),
            )
        )
    if not payload_files:
        raise ValueError("at least one [[payload.files]] entry is required")

    info = _section(raw, "info")
    extra = info.get("extra", {})
    if not isinstance(extra, dict):
        raise ValueError("[info.extra] must be a table")
    info_extra = {str(k): str(v) for k, v in extra.items()}

    return Manifest(
        path=manifest_path,
        profile_id=profile_id,
        strict=strict,
        package=package,
        service=service,
        privilege=privilege,
        assets=assets,
        scripts=scripts,
        payload_files=tuple(payload_files),
        info_extra=info_extra,
    )
