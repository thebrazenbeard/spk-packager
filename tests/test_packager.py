from __future__ import annotations

import os
from pathlib import Path
import stat
import struct
import subprocess
import tarfile
import tempfile
import unittest

from spk_packager.arch import expected_elf_machines
from spk_packager.build import build_spk
from spk_packager.lifecycle import render_start_stop_status
from spk_packager.lint import has_errors, lint_manifest
from spk_packager.model import load_manifest
from spk_packager.scaffold import scaffold
from spk_packager.verify import verify_spk


class PackagerTests(unittest.TestCase):
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

    def test_armada38x_machine_hint(self) -> None:
        machines, warnings = expected_elf_machines(("armada38x",))
        self.assertEqual(machines, {40})
        self.assertEqual(warnings, [])

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


if __name__ == "__main__":
    unittest.main()
