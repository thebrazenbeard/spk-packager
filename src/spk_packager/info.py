from __future__ import annotations

from collections.abc import Mapping

from .model import Manifest


_RESERVED = {
    "package", "version", "displayname", "os_min_ver", "os_max_ver", "description",
    "maintainer", "arch", "thirdparty", "precheckstartstop", "ctl_stop",
}


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_info(manifest: Manifest) -> bytes:
    pkg = manifest.package
    fields: list[tuple[str, str]] = [
        ("package", pkg.package_id),
        ("version", pkg.version),
    ]
    if pkg.display_name:
        fields.append(("displayname", pkg.display_name))
    fields.extend([
        ("os_min_ver", pkg.os_min_ver),
        ("description", pkg.description),
        ("maintainer", pkg.maintainer),
        ("arch", " ".join(pkg.arch)),
        ("thirdparty", "yes" if pkg.thirdparty else "no"),
        ("precheckstartstop", "yes" if pkg.precheckstartstop else "no"),
    ])
    if pkg.os_max_ver:
        fields.append(("os_max_ver", pkg.os_max_ver))
    if pkg.ctl_stop is not None:
        fields.append(("ctl_stop", "yes" if pkg.ctl_stop else "no"))

    for key in manifest.info_extra:
        if key in _RESERVED:
            raise ValueError(f"info.extra may not override reserved INFO field {key!r}")
    fields.extend((key, manifest.info_extra[key]) for key in sorted(manifest.info_extra))

    return "".join(f"{key}={_quote(value)}\n" for key, value in fields).encode("utf-8")


def parse_info(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"INFO line {line_number} is not key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if key in result:
            raise ValueError(f"duplicate INFO field {key!r}")
        result[key] = value
    return result


def render_properties(fields: Mapping[str, str]) -> bytes:
    return "".join(f"{key}={_quote(str(value))}\n" for key, value in fields.items()).encode("utf-8")
