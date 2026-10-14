"""Standalone read-only DSM SPK verifier for a deliberately narrow Tattler profile.

Independent implementation: no imports from Tattler and no archive extraction.
A passing report is structural/static evidence, not a DSM runtime smoke test.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import tarfile

MAX_ARCHIVE_BYTES = 40_000_000
MAX_PAYLOAD_BYTES = 32_000_000
ARCH_MACHINE = {"x86_64": 62, "armv7": 40, "armv8": 183}
OUTER_FILES = frozenset({
    "INFO", "PACKAGE_ICON.PNG", "PACKAGE_ICON_256.PNG",
    "conf/privilege", "conf/resource", "package.tgz",
    "scripts/start-stop-status", "scripts/preinst", "scripts/postinst",
    "scripts/preuninst", "scripts/postuninst",
    "scripts/preupgrade", "scripts/postupgrade",
})
STATE_HOOKS = ("scripts/postinst", "scripts/postupgrade")


def _validated_members(archive: tarfile.TarFile, *, expected: frozenset[str]):
    items = archive.getmembers()
    names = [item.name for item in items]
    if len(names) != len(set(names)):
        raise ValueError("duplicate archive path")
    if set(names) != expected:
        raise ValueError("archive member inventory differs from reviewed profile")
    if names != sorted(names):
        raise ValueError("archive is not in canonical sorted order")
    for item in items:
        name = PurePosixPath(item.name)
        if (name.is_absolute() or ".." in name.parts
                or str(name) != item.name or not item.isfile()):
            raise ValueError("unsafe archive member type or path")
        if any((item.uid != 0, item.gid != 0, item.mtime != 0)):
            raise ValueError("nonreproducible archive ownership or timestamp")
        if item.size < 0 or item.size > MAX_PAYLOAD_BYTES:
            raise ValueError("archive member size exceeds budget")
    return {item.name: item for item in items}


def _member_bytes(archive: tarfile.TarFile, item: tarfile.TarInfo) -> bytes:
    stream = archive.extractfile(item)
    if stream is None:
        raise ValueError("archive member not readable")
    with stream:
        raw = stream.read(MAX_PAYLOAD_BYTES + 1)
    if len(raw) != item.size or len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("archive member read size mismatch")
    return raw


def _parse_info(raw: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("INFO line is not key=value")
        name, value = line.split("=", 1)
        if not re.fullmatch("[a-z_]+", name) or name in fields:
            raise ValueError("invalid or duplicate INFO field")
        fields[name] = value.strip().strip('"')
    return fields


def verify(path: Path) -> dict[str, object]:
    """Inspect one reviewed Tattler DSM SPK without extracting or executing it."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("SPK absent or exceeds archive budget")
    with tarfile.open(path, "r:") as outer:
        entries = _validated_members(outer, expected=OUTER_FILES)
        contents = {name: _member_bytes(outer, item)
                    for name, item in entries.items()}

    info = _parse_info(contents["INFO"])
    if info.get("package") != "Tattler" or info.get("os_min_ver") != "7.2-72806":
        raise ValueError("unsupported DSM package/profile/version")
    if info.get("silent_upgrade") != "yes":
        raise ValueError("unqualified upgrade policy")
    arch = info.get("arch")
    if arch not in ARCH_MACHINE:
        raise ValueError("unqualified architecture")
    if not re.fullmatch(r"\d+\.\d+\.\d+-\d{4}", info.get("version", "")):
        raise ValueError("unqualified version")
    if info.get("auto_upgrade_from") != "0.1.0-0003":
        raise ValueError("unqualified upgrade lineage")
    package = contents["package.tgz"]
    checksum = hashlib.md5(package, usedforsecurity=False).hexdigest()
    if checksum != info.get("checksum"):
        raise ValueError("package checksum mismatch")

    privilege = json.loads(contents["conf/privilege"])
    if privilege != {"defaults": {"run-as": "package"}, "username": "Tattler"}:
        raise ValueError("package privilege policy differs from package user")

    for name, dimensions in (("PACKAGE_ICON.PNG", (64, 64)),
                             ("PACKAGE_ICON_256.PNG", (256, 256))):
        icon = contents[name]
        if (icon[:8] != b"\x89PNG\r\n\x1a\n" or
                icon[12:16] != b"IHDR" or len(icon) < 24 or
                struct.unpack(">II", icon[16:24]) != dimensions):
            raise ValueError("package icon shape invalid")

    service = contents["scripts/start-stop-status"].decode("utf-8").lower()
    if "--listen 127.0.0.1:9147" not in service:
        raise ValueError("loopback-only service requirement missing")
    if any(flag in service for flag in (
        "sudo ", "run-as=root", "setcap ", "chmod u+s", "synosystemctl",
    )):
        raise ValueError("privileged service behavior is forbidden")
    for name in STATE_HOOKS:
        text = contents[name].decode("utf-8")
        if not all(marker in text for marker in (
            "SYNOPKG_PKGVAR", 'chmod 700 "$STATE_DIR"', "umask 077",
        )):
            raise ValueError("state hook lacks confinement markers")

    with tarfile.open(fileobj=io.BytesIO(package), mode="r:gz") as inner:
        inside = _validated_members(inner, expected=frozenset({"bin/tattler"}))
        binary_item = inside["bin/tattler"]
        if binary_item.mode & 0o777 != 0o755:
            raise ValueError("payload binary mode invalid")
        binary = _member_bytes(inner, binary_item)
    if len(binary) < 20 or binary[:4] != b"\x7fELF" or binary[5] not in (1, 2):
        raise ValueError("payload is not a recognized ELF executable")
    endian = "<" if binary[5] == 1 else ">"
    machine = struct.unpack(endian+"H", binary[18:20])[0]
    if machine != ARCH_MACHINE[arch]:
        raise ValueError("ELF architecture disagrees with DSM metadata")
    if int(info.get("extractsize", "-1")) != (len(binary) + 1023) // 1024:
        raise ValueError("declared extracted size does not match payload")
    return {
        "profile": "tattler-dsm-7.2.2-static-v1",
        "arch": arch, "version": info["version"], "elf_e_machine": machine,
        "payload_members": len(inside), "outer_members": len(entries),
        "run_as": "package",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "static_only": True,
        "os_execution_observed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify_cmd = commands.add_parser("verify", help="inspect one supported SPK")
    verify_cmd.add_argument("spk", type=Path)
    verify_cmd.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        details = verify(args.spk)
    except (OSError, ValueError, tarfile.TarError, UnicodeError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "errors": [f"{type(exc).__name__}: {exc}"],
                   "warnings": [], "details": {}}
        print(json.dumps(payload, sort_keys=True) if args.json else payload)
        return 1
    payload = {"ok": True, "errors": [], "warnings": [], "details": details}
    print(json.dumps(payload, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
