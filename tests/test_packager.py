from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tarfile
import tempfile
import unittest

from spk_packager.arch import expected_elf_machines
from spk_packager.archive import ArchiveFile, deterministic_tar, deterministic_tgz
from spk_packager.build import build_spk
from spk_packager.info import parse_info, render_properties
from spk_packager.lifecycle import render_start_stop_status
from spk_packager.lint import has_errors, lint_manifest
from spk_packager.model import load_manifest
from spk_packager.scaffold import scaffold
from spk_packager.verify import verify_spk
from spk_packager.versioning import validate_package_version


def _outer_files(path: Path) -> list[ArchiveFile]:
    files: list[ArchiveFile] = []
    with tarfile.open(path, "r:") as tf:
        for member in tf.getmembers():
            handle = tf.extractfile(member)
            assert handle is not None
            files.append(ArchiveFile(member.name, handle.read(), member.mode))
    return files


def _write_outer(path: Path, files: list[ArchiveFile]) -> None:
    path.write_bytes(deterministic_tar(files, first_member="INFO"))


def _compat_style_spk(source: Path, output: Path) -> None:
    outer_files = _outer_files(source)
    package_item = next(item for item in outer_files if item.name == "package.tgz")

    payload_entries: list[tuple[str, bytes, int]] = []
    with tarfile.open(fileobj=io.BytesIO(package_item.data), mode="r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            handle = tf.extractfile(member)
            assert handle is not None
            payload_entries.append((member.name, handle.read(), member.mode))

    inner_buffer = io.BytesIO()
    with tarfile.open(
        fileobj=inner_buffer,
        mode="w:gz",
        format=tarfile.USTAR_FORMAT,
    ) as tf:
        directory = tarfile.TarInfo("./bin")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        directory.uid = directory.gid = 1000
        directory.mtime = 123
        tf.addfile(directory)
        for name, data, mode in payload_entries:
            member = tarfile.TarInfo("./" + name)
            member.size = len(data)
            member.mode = mode
            member.uid = member.gid = 1000
            member.mtime = 123
            tf.addfile(member, io.BytesIO(data))
    package_bytes = inner_buffer.getvalue()

    by_name = {item.name: item for item in outer_files}
    info_fields = parse_info(by_name["INFO"].data)
    info_fields["checksum"] = hashlib.md5(
        package_bytes,
        usedforsecurity=False,
    ).hexdigest()
    info_fields["extractsize"] = "1024"
    by_name["INFO"] = ArchiveFile(
        "INFO",
        render_properties(info_fields),
        by_name["INFO"].mode,
    )
    by_name["package.tgz"] = ArchiveFile(
        "package.tgz",
        package_bytes,
        by_name["package.tgz"].mode,
    )

    order = ["INFO", "package.tgz"]
    remaining = [
        name
        for name in by_name
        if name not in {"INFO", "package.tgz"}
    ]

    outer_buffer = io.BytesIO()
    with tarfile.open(
        fileobj=outer_buffer,
        mode="w:",
        format=tarfile.USTAR_FORMAT,
    ) as tf:
        for name in order:
            item = by_name[name]
            member = tarfile.TarInfo(name)
            member.size = len(item.data)
            member.mode = item.mode
            member.uid = member.gid = 1000
            member.mtime = 123
            tf.addfile(member, io.BytesIO(item.data))

        for dirname in ("conf", "scripts"):
            member = tarfile.TarInfo(dirname)
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
            member.uid = member.gid = 1000
            member.mtime = 123
            tf.addfile(member)

        for name in remaining:
            item = by_name[name]
            member = tarfile.TarInfo(name)
            member.size = len(item.data)
            member.mode = item.mode
            member.uid = member.gid = 1000
            member.mtime = 123
            tf.addfile(member, io.BytesIO(item.data))

    output.write_bytes(outer_buffer.getvalue())


class PackagerTests(unittest.TestCase):
    def test_deterministic_tgz_uses_host_independent_stored_deflate(self) -> None:
        files = [ArchiveFile("fixture.bin", b"A" * 8192)]
        blob = deterministic_tgz(files)
        self.assertEqual(blob[:3], b"\x1f\x8b\x08")
        self.assertEqual(blob[9], 255)
        self.assertEqual((blob[10] >> 1) & 0x03, 0)
        self.assertEqual(gzip.decompress(blob), deterministic_tar(files))

    def test_scaffold_build_verify_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "DemoService", "Demo Service", "tester")
            manifest = load_manifest(manifest_path)
            issues = lint_manifest(manifest)
            self.assertFalse(has_errors(issues), issues)

            first = build_spk(manifest, root / "dist" / "a.spk")
            second = build_spk(manifest, root / "dist" / "b.spk")
            self.assertEqual(first.sha256, second.sha256)

            report = verify_spk(first.output)
            self.assertTrue(report.ok, report.as_dict())
            self.assertEqual(report.details["info"]["os_min_ver"], "7.2-72806")
            self.assertEqual(report.details["info"]["precheckstartstop"], "yes")
            self.assertRegex(report.details["info"]["checksum"], r"^[0-9a-f]{32}$")
            self.assertGreaterEqual(int(report.details["info"]["extractsize"]), 1)
            self.assertEqual(
                report.details["info"]["checksum"],
                report.details["package_tgz_md5"],
            )
            with tarfile.open(first.output, "r:") as tf:
                members = tf.getmembers()
                self.assertEqual(members[0].name, "INFO")
                self.assertTrue(all(not member.pax_headers for member in members))
                package_bytes = tf.extractfile("package.tgz").read()
            self.assertEqual(
                hashlib.md5(package_bytes, usedforsecurity=False).hexdigest(),
                report.details["info"]["checksum"],
            )

    def test_generated_lifecycle_encodes_tattler_regression_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = scaffold(Path(tmp) / "demo", "Demo", "Demo", "tester")
            manifest = load_manifest(manifest_path)
            text = render_start_stop_status(manifest).decode("utf-8")
            self.assertIn("prestart)", text)
            self.assertIn("prestop)", text)
            self.assertIn("status)", text)
            self.assertIn("exit 3", text)
            self.assertIn("SYNOPKG_TEMP_LOGFILE", text)
            self.assertIn('"${20}"', text)
            self.assertNotIn('"$20"', text)
            self.assertNotIn(r"\${SYNOPKG_PKGVAR}", text)

    def test_noarch_rejects_native_elf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "NativeDemo", "Native Demo", "tester")
            elf = bytearray(64)
            elf[:4] = b"\x7fELF"
            elf[4] = 1
            elf[5] = 1
            elf[18:20] = struct.pack("<H", 40)
            (root / "payload" / "bin" / "example-service").write_bytes(elf)
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(any(i.code == "NOARCH_NATIVE_BINARY" for i in issues), issues)

    def test_noarch_native_bundle_requires_explicit_portable_dispatcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "BundleDemo", "Bundle Demo", "tester")
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                "precheckstartstop = true\n",
                "precheckstartstop = true\nallow_noarch_native_bundle = true\n",
            )
            for name, machine in (("armv7", 40), ("x86_64", 62)):
                data = bytearray(64)
                data[:4] = b"\x7fELF"
                data[4] = 1
                data[5] = 1
                data[18:20] = struct.pack("<H", machine)
                path = root / "payload" / "bin" / name
                path.write_bytes(data)
                manifest_text += (
                    "\n[[payload.files]]\n"
                    f'source = "payload/bin/{name}"\n'
                    f'destination = "bin/{name}"\n'
                    'mode = "0755"\n'
                )
            manifest_path.write_text(manifest_text, encoding="utf-8")
            manifest = load_manifest(manifest_path)
            issues = lint_manifest(manifest)
            self.assertFalse(has_errors(issues), issues)
            self.assertTrue(
                any(i.code == "NOARCH_NATIVE_BUNDLE_EXPLICIT" for i in issues),
                issues,
            )
            result = build_spk(manifest, root / "dist" / "bundle.spk")
            denied = verify_spk(result.output)
            self.assertFalse(denied.ok)
            allowed = verify_spk(
                result.output,
                allow_noarch_native_bundle=True,
            )
            self.assertTrue(allowed.ok, allowed.as_dict())

    def test_privilege_tool_is_serialized_and_target_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "ToolDemo", "Tool Demo", "tester")
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n[[privilege.tool]]\n"
                    'relpath = "bin/example-service"\n'
                    'user = "package"\n'
                    'group = "package"\n'
                    'permission = "0755"\n'
                    'capabilities = "cap_net_raw"\n'
                )
            manifest = load_manifest(manifest_path)
            issues = lint_manifest(manifest)
            self.assertFalse(has_errors(issues), issues)
            result = build_spk(manifest, root / "dist" / "tool.spk")
            report = verify_spk(result.output)
            self.assertTrue(report.ok, report.as_dict())
            with tarfile.open(result.output, "r:") as tf:
                privilege = json.loads(tf.extractfile("conf/privilege").read())
            self.assertEqual(
                privilege["tool"],
                [{
                    "capabilities": "cap_net_raw",
                    "group": "package",
                    "permission": "0755",
                    "relpath": "bin/example-service",
                    "user": "package",
                }],
            )

    def test_privilege_ctrl_script_and_executable_are_not_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(
                root,
                "PrivilegeDemo",
                "Privilege Demo",
                "tester",
            )
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n[[privilege.ctrl_script]]\n"
                    'action = "start"\n'
                    'run_as = "package"\n'
                    "\n[[privilege.executable]]\n"
                    'relpath = "bin/example-service"\n'
                    'run_as = "package"\n'
                )
            manifest = load_manifest(manifest_path)
            issues = lint_manifest(manifest)
            self.assertFalse(has_errors(issues), issues)

            result = build_spk(
                manifest,
                root / "dist" / "privilege.spk",
            )
            report = verify_spk(result.output)
            self.assertTrue(report.ok, report.as_dict())

            with tarfile.open(result.output, "r:") as tf:
                privilege = json.loads(
                    tf.extractfile("conf/privilege").read()
                )
            self.assertEqual(
                privilege["ctrl-script"],
                [{"action": "start", "run-as": "package"}],
            )
            self.assertEqual(
                privilege["executable"],
                [{
                    "relpath": "bin/example-service",
                    "run-as": "package",
                }],
            )

    def test_strict_profile_rejects_privilege_root_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(
                root,
                "PrivilegeRootDemo",
                "Privilege Root Demo",
                "tester",
            )
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n[[privilege.ctrl_script]]\n"
                    'action = "start"\n'
                    'run_as = "root"\n'
                    "\n[[privilege.executable]]\n"
                    'relpath = "bin/example-service"\n'
                    'run_as = "root"\n'
                )
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(
                any(
                    i.code == "ROOT_PRIVILEGE_OVERRIDE"
                    and i.severity == "error"
                    for i in issues
                ),
                issues,
            )

    def test_armada38x_machine_hint(self) -> None:
        machines, warnings = expected_elf_machines(("armada38x",))
        self.assertEqual(machines, {40})
        self.assertEqual(warnings, [])

    def test_info_round_trip_preserves_quotes_and_backslashes(self) -> None:
        value = 'prefix\\path"quoted"\\tail'
        encoded = render_properties({"sample": value})
        self.assertEqual(parse_info(encoded)["sample"], value)
        with self.assertRaises(ValueError):
            parse_info(b'bad-key!="value"\n')
        with self.assertRaises(ValueError):
            parse_info(b'sample="unterminated\n')

    def test_scaffold_quotes_toml_values_and_validates_package_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(
                root,
                "QuotedDemo",
                'Display "Name"\nLine',
                'Maintainer "Quoted"',
            )
            manifest = load_manifest(manifest_path)
            self.assertEqual(manifest.package.display_name, 'Display "Name"\nLine')
            self.assertEqual(manifest.package.maintainer, 'Maintainer "Quoted"')

            with self.assertRaisesRegex(ValueError, "package.id"):
                scaffold(Path(tmp) / "bad", "..", "Bad", "tester")

    def test_manifest_rejects_ambiguous_types_and_arch_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "ManifestDemo", "Manifest Demo", "tester")
            original = manifest_path.read_text(encoding="utf-8")

            manifest_path.write_text(
                original.replace("strict = true", 'strict = "false"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "TOML boolean"):
                load_manifest(manifest_path)

            manifest_path.write_text(
                original.replace('arch = ["noarch"]', 'arch = ["noarch", "armada38x"]'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "may not combine noarch"):
                load_manifest(manifest_path)

            manifest_path.write_text(
                original.replace('id = "ManifestDemo"', 'id = "."'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "package.id"):
                load_manifest(manifest_path)

    def test_service_state_paths_cannot_collide_with_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "StateDemo", "State Demo", "tester")
            original = manifest_path.read_text(encoding="utf-8")

            manifest_path.write_text(
                original.replace(
                    'log_file = "example-service.log"',
                    'log_file = "example-service.pid/log"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "parent/child"):
                load_manifest(manifest_path)

            manifest_path.write_text(
                original.replace(
                    'state_dirs = ["state"]',
                    'state_dirs = ["example-service.pid/child"]',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "state directory"):
                load_manifest(manifest_path)

    def test_external_payload_source_requires_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "demo"
            outside = base / "outside-service"
            outside.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            manifest_path = scaffold(root, "ExternalDemo", "External Demo", "tester")
            text = manifest_path.read_text(encoding="utf-8").replace(
                'source = "payload/bin/example-service"',
                f'source = "{outside.as_posix()}"',
            )
            manifest_path.write_text(text, encoding="utf-8")

            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(
                any(i.code == "EXTERNAL_SOURCE_PATH" and i.severity == "error" for i in issues),
                issues,
            )

            manifest_path.write_text(
                text.replace(
                    "strict = true",
                    "strict = true\nallow_external_sources = true",
                ),
                encoding="utf-8",
            )
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertFalse(
                any(i.code == "EXTERNAL_SOURCE_PATH" for i in issues),
                issues,
            )

    def test_archive_paths_must_be_canonical(self) -> None:
        with self.assertRaises(ValueError):
            deterministic_tar([ArchiveFile("./INFO", b"x")])
        with self.assertRaises(ValueError):
            deterministic_tar([ArchiveFile("bad\\name", b"x")])
        with self.assertRaises(ValueError):
            deterministic_tar([ArchiveFile("bad\nname", b"x")])

    def test_compat_only_accepts_valid_noncanonical_external_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "CompatDemo", "Compat Demo", "tester")
            built = build_spk(
                load_manifest(manifest_path),
                root / "dist" / "canonical.spk",
            )
            external = root / "dist" / "external-style.spk"
            _compat_style_spk(built.output, external)

            strict_report = verify_spk(external)
            self.assertFalse(strict_report.ok)

            compat_report = verify_spk(external, strict=False)
            self.assertTrue(compat_report.ok, compat_report.as_dict())
            self.assertTrue(
                any("not reproducible" in warning for warning in compat_report.warnings),
                compat_report.as_dict(),
            )

    def test_verifier_rejects_extractsize_lie_and_nonexec_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "VerifyDemo", "Verify Demo", "tester")
            built = build_spk(
                load_manifest(manifest_path),
                root / "dist" / "good.spk",
            )

            lie_files = _outer_files(built.output)
            for index, item in enumerate(lie_files):
                if item.name == "INFO":
                    fields = parse_info(item.data)
                    fields["extractsize"] = "0"
                    lie_files[index] = ArchiveFile(
                        item.name,
                        render_properties(fields),
                        item.mode,
                    )
            lie_path = root / "dist" / "extractsize-lie.spk"
            _write_outer(lie_path, lie_files)
            lie_report = verify_spk(lie_path)
            self.assertFalse(lie_report.ok)
            self.assertTrue(
                any("extractsize is below" in error for error in lie_report.errors),
                lie_report.as_dict(),
            )

            mode_files = _outer_files(built.output)
            for index, item in enumerate(mode_files):
                if item.name == "scripts/start-stop-status":
                    mode_files[index] = ArchiveFile(item.name, item.data, 0o644)
            mode_path = root / "dist" / "nonexec-script.spk"
            _write_outer(mode_path, mode_files)
            mode_report = verify_spk(mode_path)
            self.assertFalse(mode_report.ok)
            self.assertTrue(
                any("not executable" in error for error in mode_report.errors),
                mode_report.as_dict(),
            )

    def test_verifier_rejects_nondeterministic_gzip_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "GzipDemo", "Gzip Demo", "tester")
            built = build_spk(
                load_manifest(manifest_path),
                root / "dist" / "good.spk",
            )
            files = _outer_files(built.output)

            package_index = next(
                i for i, item in enumerate(files) if item.name == "package.tgz"
            )
            package = bytearray(files[package_index].data)
            package[4:8] = (123).to_bytes(4, "little")
            files[package_index] = ArchiveFile(
                "package.tgz",
                bytes(package),
                files[package_index].mode,
            )
            checksum = hashlib.md5(
                bytes(package),
                usedforsecurity=False,
            ).hexdigest()

            info_index = next(i for i, item in enumerate(files) if item.name == "INFO")
            fields = parse_info(files[info_index].data)
            fields["checksum"] = checksum
            files[info_index] = ArchiveFile(
                "INFO",
                render_properties(fields),
                files[info_index].mode,
            )

            bad_path = root / "dist" / "gzip-mtime.spk"
            _write_outer(bad_path, files)
            report = verify_spk(bad_path)
            self.assertFalse(report.ok)
            self.assertTrue(
                any("gzip mtime is nonzero" in error for error in report.errors),
                report.as_dict(),
            )

    def test_extended_synology_architecture_hints(self) -> None:
        machines, warnings = expected_elf_machines(
            ("armada370", "evansport", "aarch64", "qoriq", "r1000")
        )
        self.assertEqual(machines, {3, 20, 40, 62, 183})
        self.assertEqual(warnings, [])

    def test_package_version_component_ceiling(self) -> None:
        validate_package_version("1.2.3-2147483647")
        with self.assertRaises(ValueError):
            validate_package_version("1.2.3-2147483648")

    def test_strict_profile_rejects_root_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "RootDemo", "Root Demo", "tester")
            text = manifest_path.read_text(encoding="utf-8").replace(
                'run_as = "package"', 'run_as = "root"'
            )
            manifest_path.write_text(text, encoding="utf-8")
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(any(
                i.code == "ROOT_PRIVILEGE_REQUESTED" and i.severity == "error"
                for i in issues
            ), issues)

    def test_payload_file_parent_conflict_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "PathDemo", "Path Demo", "tester")
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    '\n[[payload.files]]\n'
                    'source = "payload/bin/example-service"\n'
                    'destination = "bin/example-service/config"\n'
                    'mode = "0644"\n'
                )
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(any(i.code == "PAYLOAD_PATH_CONFLICT" for i in issues), issues)

    def test_custom_lifecycle_requires_precheck_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "CustomDemo", "Custom Demo", "tester")
            scripts = root / "custom"
            scripts.mkdir()
            custom = scripts / "start-stop-status"
            custom.write_text(
                "#!/bin/sh\ncase \"$1\" in\nstatus) exit 3 ;;\nesac\n",
                encoding="utf-8",
                newline="\n",
            )
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write('\n[scripts]\nstart_stop_status = "custom/start-stop-status"\n')
            issues = lint_manifest(load_manifest(manifest_path))
            self.assertTrue(any(i.code == "PRECHECK_HANDLER_MISSING" for i in issues), issues)

    def test_builder_uses_valid_custom_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            manifest_path = scaffold(root, "CustomBuild", "Custom Build", "tester")
            scripts = root / "custom"
            scripts.mkdir()
            custom = scripts / "start-stop-status"
            body = (
                "#!/bin/sh\ncase \"$1\" in\n"
                "prestart|prestop|start|stop) exit 0 ;;\n"
                "status) exit 3 ;;\n"
                "*) exit 1 ;;\nesac\n"
            )
            custom.write_text(body, encoding="utf-8", newline="\n")
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write('\n[scripts]\nstart_stop_status = "custom/start-stop-status"\n')
            manifest = load_manifest(manifest_path)
            result = build_spk(manifest, root / "dist" / "custom.spk")
            with tarfile.open(result.output, "r:") as tf:
                installed = tf.extractfile("scripts/start-stop-status")
                self.assertIsNotNone(installed)
                self.assertEqual(installed.read().decode("utf-8"), body)


@unittest.skipUnless(os.name == "posix", "lifecycle harness requires POSIX /bin/sh")
class LifecycleHarnessTests(unittest.TestCase):
    def test_precheck_start_status_stop_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            manifest_path = scaffold(project, "LifecycleDemo", "Lifecycle Demo", "tester")
            manifest = load_manifest(manifest_path)

            pkgdest = root / "target"
            pkgvar = root / "var"
            (pkgdest / "bin").mkdir(parents=True)
            pkgvar.mkdir()
            binary = pkgdest / "bin" / "example-service"
            binary.write_text(
                "#!/bin/sh\ntrap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n",
                encoding="utf-8",
            )
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

            lifecycle = root / "start-stop-status"
            lifecycle.write_bytes(render_start_stop_status(manifest))
            lifecycle.chmod(lifecycle.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["SYNOPKG_PKGDEST"] = str(pkgdest)
            env["SYNOPKG_PKGVAR"] = str(pkgvar)
            env["SYNOPKG_TEMP_LOGFILE"] = str(root / "dsm-message.log")

            def run(action: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["/bin/sh", str(lifecycle), action],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )

            self.assertEqual(run("prestart").returncode, 0)
            self.assertEqual(run("prestop").returncode, 0)
            self.assertEqual(run("status").returncode, 3)
            self.assertEqual(run("start").returncode, 0)
            self.assertEqual(run("status").returncode, 0)
            self.assertEqual(run("stop").returncode, 0)
            self.assertEqual(run("status").returncode, 3)

            # A PID file is not enough identity: if the recorded process start time
            # no longer matches, stop must fail safe instead of signalling that PID.
            self.assertEqual(run("start").returncode, 0)
            pid_file = pkgvar / "example-service.pid"
            start_file = Path(str(pid_file) + ".start")
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            start_file.write_text("0\n", encoding="utf-8")
            self.assertEqual(run("status").returncode, 1)
            self.assertEqual(run("start").returncode, 1)
            os.kill(pid, 0)
            self.assertEqual(run("stop").returncode, 0)
            os.kill(pid, 0)
            os.kill(pid, 15)

    def test_generated_paths_do_not_execute_shell_substitutions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            manifest_path = scaffold(
                project,
                "QuotedPathDemo",
                "Quoted Path Demo",
                "tester",
            )
            dangerous = "bin/service$(touch PWNED)"
            text = manifest_path.read_text(encoding="utf-8")
            text = text.replace(
                'command = "bin/example-service"',
                f'command = "{dangerous}"',
            ).replace(
                'destination = "bin/example-service"',
                f'destination = "{dangerous}"',
            )
            manifest_path.write_text(text, encoding="utf-8")
            manifest = load_manifest(manifest_path)

            pkgdest = root / "target"
            pkgvar = root / "var"
            (pkgdest / "bin").mkdir(parents=True)
            pkgvar.mkdir()
            binary = pkgdest / dangerous
            binary.write_text(
                "#!/bin/sh\ntrap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n",
                encoding="utf-8",
            )
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

            lifecycle = root / "start-stop-status"
            lifecycle.write_bytes(render_start_stop_status(manifest))
            lifecycle.chmod(lifecycle.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["SYNOPKG_PKGDEST"] = str(pkgdest)
            env["SYNOPKG_PKGVAR"] = str(pkgvar)
            env["SYNOPKG_TEMP_LOGFILE"] = str(root / "dsm-message.log")

            def run(action: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["/bin/sh", str(lifecycle), action],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )

            self.assertEqual(run("prestart").returncode, 0)
            self.assertFalse((root / "PWNED").exists())
            self.assertEqual(run("start").returncode, 0)
            self.assertFalse((root / "PWNED").exists())
            self.assertEqual(run("status").returncode, 0)
            self.assertEqual(run("stop").returncode, 0)
            self.assertFalse((root / "PWNED").exists())


if __name__ == "__main__":
    unittest.main()
