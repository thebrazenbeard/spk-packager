from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

from .arch import expected_elf_machines
from .assets import png_dimensions
from .elf import elf_machine
from .info import parse_info
from .lifecycle import handles_case_action
from .profiles import get_profile
from .versioning import DSMVersion, validate_package_version


@dataclass
class VerificationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


def _safe_members(tf: tarfile.TarFile, report: VerificationReport, layer: str) -> list[tarfile.TarInfo]:
    members = tf.getmembers()
    names = [m.name for m in members]
    if len(names) != len(set(names)):
        report.errors.append(f"{layer}: duplicate archive members")
    if names != sorted(names):
        report.errors.append(f"{layer}: archive members are not lexicographically sorted")
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            report.errors.append(f"{layer}: unsafe path {member.name!r}")
        if not member.isfile():
            report.errors.append(f"{layer}: non-file member {member.name!r}")
        if member.uid != 0 or member.gid != 0 or member.mtime != 0:
            report.errors.append(f"{layer}: non-deterministic metadata on {member.name!r}")
    return members


def verify_spk(path: Path, *, profile_id: str = "dsm-7.2.2+", strict: bool = True) -> VerificationReport:
    report = VerificationReport()
    path = path.resolve()
    profile = get_profile(profile_id)
    report.details["profile"] = profile_id
    report.details["spk"] = str(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        report.errors.append(f"cannot read SPK: {exc}")
        return report
    report.details["sha256"] = hashlib.sha256(raw).hexdigest()
    report.details["bytes"] = len(raw)
    try:
        outer_tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:")
    except Exception as exc:
        report.errors.append(f"outer archive is invalid: {exc}")
        return report
    info: dict[str, str] = {}
    package_bytes: bytes | None = None
    with outer_tf:
        outer_members = _safe_members(outer_tf, report, "outer")
        outer_names = {m.name for m in outer_members}
        report.details["outer_members"] = len(outer_members)
        required = {
            "INFO", "package.tgz", "conf/privilege", "scripts/start-stop-status",
            "scripts/preinst", "scripts/postinst", "scripts/preuninst", "scripts/postuninst",
            "scripts/preupgrade", "scripts/postupgrade",
        }
        if strict and profile.require_icons:
            required.update({"PACKAGE_ICON.PNG", "PACKAGE_ICON_256.PNG"})
        missing = sorted(required - outer_names)
        if missing:
            report.errors.append(f"missing outer members: {missing}")

        def read_outer(name: str) -> bytes | None:
            try:
                member = outer_tf.extractfile(name)
            except KeyError:
                return None
            return member.read() if member else None

        info_bytes = read_outer("INFO")
        if info_bytes is not None:
            try:
                info = parse_info(info_bytes)
            except Exception as exc:
                report.errors.append(f"INFO is invalid: {exc}")
        report.details["info"] = info

        privilege = read_outer("conf/privilege")
        if privilege is not None:
            try:
                parsed = json.loads(privilege)
                if not isinstance(parsed, dict):
                    raise ValueError("root must be a JSON object")
                run_as = parsed["defaults"]["run-as"]
                if run_as not in {"package", "root"}:
                    raise ValueError("defaults.run-as must be package or root")
                if run_as == "root":
                    message = "conf/privilege requests root execution; DSM 7 strict packaging expects package-user execution"
                    if strict:
                        report.errors.append(message)
                    else:
                        report.warnings.append(message)
            except Exception as exc:
                report.errors.append(f"conf/privilege is invalid: {exc}")

        resource = read_outer("conf/resource")
        if resource is not None:
            try:
                parsed_resource = json.loads(resource)
                if not isinstance(parsed_resource, dict):
                    raise ValueError("root must be a JSON object")
            except Exception as exc:
                report.errors.append(f"conf/resource is invalid: {exc}")

        license_bytes = read_outer("LICENSE")
        if license_bytes is not None and len(license_bytes) >= 1024 * 1024:
            report.errors.append("LICENSE must be smaller than 1 MiB")

        if any(name.startswith("WIZARD_UIFILES/") for name in outer_names) and not profile.wizard_uifiles_available:
            report.errors.append(f"WIZARD_UIFILES is not available in profile {profile_id}")

        if strict:
            for name, dims in (("PACKAGE_ICON.PNG", (64, 64)), ("PACKAGE_ICON_256.PNG", (256, 256))):
                data = read_outer(name)
                if data is not None:
                    try:
                        actual = png_dimensions(data)
                        if actual != dims:
                            report.errors.append(f"{name} dimensions {actual} != {dims}")
                    except Exception as exc:
                        report.errors.append(f"{name} invalid: {exc}")
        script = read_outer("scripts/start-stop-status")
        if script is not None:
            text = script.decode("utf-8", errors="replace")
            if not handles_case_action(text, "status"):
                report.errors.append("start-stop-status does not handle status")
            if info.get("precheckstartstop", "yes") == "yes":
                if not handles_case_action(text, "prestart") or not handles_case_action(text, "prestop"):
                    report.errors.append("precheckstartstop=yes but start-stop-status lacks prestart/prestop")
            if "exit 3" not in text:
                report.warnings.append("start-stop-status does not visibly contain DSM status code 3 for a stopped service")

        if info:
            necessary = ("package", "version", "os_min_ver", "description", "arch", "maintainer")
            missing_fields = [key for key in necessary if not info.get(key)]
            if missing_fields:
                report.errors.append(f"INFO missing necessary fields: {missing_fields}")
            try:
                validate_package_version(info.get("version", ""))
            except Exception as exc:
                report.errors.append(f"INFO version invalid: {exc}")
            try:
                min_os = DSMVersion.parse(info.get("os_min_ver", ""))
                if min_os < profile.minimum_os:
                    report.errors.append(f"os_min_ver {min_os} is below profile minimum {profile.minimum_os}")
                if info.get("os_max_ver"):
                    max_os = DSMVersion.parse(info["os_max_ver"])
                    if max_os < min_os:
                        report.errors.append("INFO os_max_ver is lower than os_min_ver")
            except Exception as exc:
                report.errors.append(f"INFO OS version range invalid: {exc}")
        package_bytes = read_outer("package.tgz")

    if package_bytes is None:
        return report
    try:
        inner_tf = tarfile.open(fileobj=io.BytesIO(package_bytes), mode="r:gz")
    except Exception as exc:
        report.errors.append(f"package.tgz is invalid: {exc}")
        return report

    with inner_tf:
        inner_members = _safe_members(inner_tf, report, "payload")
        report.details["payload_members"] = len(inner_members)
        arch_values = tuple(x for x in info.get("arch", "").split() if x)
        allowed_machines, warnings = expected_elf_machines(arch_values)
        report.warnings.extend(warnings)
        seen_elf: list[dict[str, object]] = []
        for member in inner_members:
            handle = inner_tf.extractfile(member)
            if handle is None:
                continue
            data = handle.read()
            machine = elf_machine(data)
            if machine is None:
                continue
            seen_elf.append({"path": member.name, "e_machine": machine})
            if "noarch" in arch_values:
                report.errors.append(f"payload {member.name} is ELF e_machine={machine} but INFO arch includes noarch")
            elif allowed_machines and machine not in allowed_machines:
                report.errors.append(f"payload {member.name} ELF e_machine={machine} does not match INFO arch machine hints {sorted(allowed_machines)}")
        report.details["elf_payloads"] = seen_elf
    return report
