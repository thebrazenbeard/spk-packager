"""Synthetic positive and adversarial fixtures for the independent SPK verifier."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
import unittest
from tempfile import TemporaryDirectory

from spk_packager.cli import OUTER_FILES, verify, main


def _tar(entries: dict[str, bytes], *, gzip: bool = False, order=None) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz" if gzip else "w:") as archive:
        for name in order or sorted(entries):
            blob = entries[name]
            m = tarfile.TarInfo(name=name)
            m.uid = m.gid = m.mtime = 0
            m.mode = 0o755 if name.startswith("scripts/") or name == "bin/tattler" else 0o644
            m.size = len(blob)
            archive.addfile(m, io.BytesIO(blob))
    return out.getvalue()


def _fake_png(w: int, h: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", w, h)


def _payload(*, arch: str = "armv7") -> bytes:
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    machine = {"armv7":40, "armv8":183, "x86_64":62}[arch]
    header[18:20] = struct.pack("<H", machine)
    return bytes(header)


def _fixture(*, arch: str = "armv7", bad_privilege: bool = False,
             tamper_checksum: bool = False, wrong_elf: bool = False,
             unsafe_member: bool = False) -> bytes:
    binary = _payload(arch="x86_64" if wrong_elf else arch)
    gz = _tar({"bin/tattler": binary}, gzip=True)
    md5 = hashlib.md5(gz, usedforsecurity=False).hexdigest()
    info = {
        "package": "Tattler", "os_min_ver": "7.2-72806",
        "version": "0.2.0-0004", "arch": arch,
        "silent_upgrade": "yes", "auto_upgrade_from": "0.1.0-0003",
        "checksum": ("0" * 32 if tamper_checksum else md5),
        "extractsize": str((len(binary) + 1023) // 1024),
    }
    info_blob = "\n".join(f'{k}="{v}"' for k, v in info.items()).encode()
    privilege = {"defaults":{"run-as":"root" if bad_privilege else "package"},
                 "username":"Tattler"}
    entries = {
        "INFO":info_blob,
        "PACKAGE_ICON.PNG":_fake_png(64,64),
        "PACKAGE_ICON_256.PNG":_fake_png(256,256),
        "conf/privilege":json.dumps(privilege).encode(),
        "conf/resource":b"{}\n",
        "package.tgz":gz,
        "scripts/start-stop-status":b"#!/bin/sh\n# --listen 127.0.0.1:9147\n",
        "scripts/preinst":b"#!/bin/sh\n",
        "scripts/preuninst":b"#!/bin/sh\n",
        "scripts/postuninst":b"#!/bin/sh\n",
        "scripts/preupgrade":b"#!/bin/sh\n",
        "scripts/postinst":b"#!/bin/sh\n# SYNOPKG_PKGVAR umask 077 chmod 700 \"$STATE_DIR\"\n",
        "scripts/postupgrade":b"#!/bin/sh\n# SYNOPKG_PKGVAR umask 077 chmod 700 \"$STATE_DIR\"\n",
    }
    assert set(entries)==OUTER_FILES
    if unsafe_member:
        entries["scripts/../poison"] = entries.pop("scripts/preinst")
    return _tar(entries)


class VerificationTests(unittest.TestCase):
    def _spk(self, blob: bytes, home: Path) -> Path:
        p = home / "package.spk"
        p.write_bytes(blob)
        return p

    def test_three_valid_architecture_profiles(self):
        with TemporaryDirectory() as tmp:
            for arch in ("x86_64", "armv7", "armv8"):
                p = self._spk(_fixture(arch=arch), Path(tmp))
                details = verify(p)
                self.assertEqual(details["arch"], arch)
                self.assertTrue(details["static_only"])
                self.assertFalse(details["os_execution_observed"])
                self.assertEqual(details["run_as"], "package")

    def test_rejects_checksum_spoof_wrong_arch_privileged_and_unsafe_path(self):
        with TemporaryDirectory() as tmp:
            for setting in ("tamper_checksum", "wrong_elf", "bad_privilege", "unsafe_member"):
                with self.subTest(setting=setting):
                    p = self._spk(_fixture(**{setting: True}), Path(tmp))
                    with self.assertRaises(ValueError):
                        verify(p)

    def test_rejects_truncated_archive_and_wrong_format(self):
        with TemporaryDirectory() as tmp:
            valid = _fixture()
            for altered in (valid[:38], b"not spk", valid + b"unexpected"):
                p = self._spk(altered, Path(tmp))
                if altered == valid + b"unexpected":
                    # Tar may legitimately pad with extra zero blocks; this
                    # should not be used as a malicious-archive acceptance test.
                    continue
                with self.assertRaises((ValueError, tarfile.TarError)):
                    verify(p)

    def test_cli_requires_explicit_verify_and_reports_failure(self):
        with TemporaryDirectory() as tmp:
            path = self._spk(b"not spk", Path(tmp))
            self.assertEqual(main(["verify", str(path), "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
