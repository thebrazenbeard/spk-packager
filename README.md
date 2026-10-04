# SPK Packager

SPK Packager is a small, deterministic construction and validation toolkit for Synology packages targeting the **known DSM 7.2.2 package contract and later DSM versions that remain compatible with that contract**.

It was extracted from the Tattler DS216 packaging work while investigating a real DSM 7.2.2 startup failure. Source review exposed an easy-to-miss lifecycle rule: when `precheckstartstop="yes"`, Package Center invokes `prestart` / `prestop` around ordinary start/stop operations. SPK Packager encodes that rule so future packages do not have to rediscover the contract on a NAS. The startup failure and the lifecycle defect are preserved as separate evidence until the corrected package is live-qualified.

## What it does

- scaffolds a buildable DSM 7.2.2 package project;
- generates deterministic `INFO`, `conf/privilege`, lifecycle scripts, icons, and `package.tgz`;
- packs byte-reproducible `.spk` archives;
- validates DSM 7 privilege and lifecycle requirements;
- catches `precheckstartstop` / `prestart` / `prestop` mismatches;
- uses DSM status code `3` for a cleanly stopped service;
- checks archive traversal, duplicates, ordering, uid/gid/mtime normalization, icon dimensions, and payload layout;
- performs ELF machine-class sanity checks against known Synology architecture/platform families;
- rejects `arch=noarch` when a native ELF payload is present;
- explains the compatibility profile and the sources from which its rules were derived.

It intentionally does **not** replace Synology's compiler toolchains. Compile your Go/Rust/C/C++/other native application with the appropriate target toolchain, then let SPK Packager build and verify the DSM package around the resulting payload.

## Quick start

Requires Python 3.11+ and no runtime third-party dependencies.

```bash
python -m pip install -e .
spk-packager init demo --package-id DemoService
spk-packager lint demo/spk-packager.toml
spk-packager build demo/spk-packager.toml
spk-packager verify demo/dist/DemoService-noarch-0.1.0-0001.spk
spk-packager selftest
```

To inspect the encoded DSM contract:

```bash
spk-packager explain dsm-7.2.2+
```

## Manifest

A package is described by `spk-packager.toml`.

```toml
[compatibility]
profile = "dsm-7.2.2+"
strict = true

[package]
id = "MyPackage"
display_name = "My Package"
version = "1.0.0-0001"
description = "My DSM package."
maintainer = "me"
arch = ["armada38x"]
os_min_ver = "7.2-72806"
thirdparty = true
precheckstartstop = true

[service]
enabled = true
command = "bin/my-service"
args = ["--state-dir", "{pkgvar}/state"]
pid_file = "my-service.pid"
log_file = "my-service.log"
state_dirs = ["state"]

[privilege]
run_as = "package"
username = "MyPackage"

[assets]
icon64 = "assets/PACKAGE_ICON.PNG"
icon256 = "assets/PACKAGE_ICON_256.PNG"

[[payload.files]]
source = "dist/my-service"
destination = "bin/my-service"
mode = "0755"
expected_elf_machine = 40
```

Runtime argument placeholders `{pkgdest}` and `{pkgvar}` are expanded to DSM's `SYNOPKG_PKGDEST` and `SYNOPKG_PKGVAR` variables inside the generated lifecycle script.

See [docs/MANIFEST.md](docs/MANIFEST.md) for the full v0.1 surface.

## DSM 7.2.2+ means a baseline, not prophecy

The current profile is grounded in Synology's DSM 7.2.2 Developer Guide. It deliberately omits `os_max_ver`, so a package can install on later DSM releases if Synology preserves compatibility. That is **not** a claim that an unknown future DSM release has been runtime-qualified.

The evidence states remain separate:

`SOURCE_VALIDATED != SPK_STRUCTURALLY_VERIFIED != DSM_INSTALLED != DSM_RUNTIME_VERIFIED`

See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) and [docs/QUALIFICATION.md](docs/QUALIFICATION.md).

## Provenance

The first implementation generalizes mechanisms from:

- `thebrazenbeard/tattler@c11ac394828a76b971a32e178632f81e8a08b237` (lifecycle fix plus required Package Center icons);
- Synology's DSM 7.2.2 Developer Guide;
- `SynologyOpenSource/ExamplePackages@d2849c6fcf14ce72007d14e99a362c3d4f23be0a`;
- `SynoCommunity/spksrc@00052786a00a4c3cc6b1eaaf7bf7495031bba1bb`.

No Synology or SynoCommunity implementation is vendored. The package builder is a clean Python standard-library implementation informed by the documented contract and the Tattler regression.

See [docs/TATTLER_EXTRACTION.md](docs/TATTLER_EXTRACTION.md) and [docs/SOURCES.json](docs/SOURCES.json).

## Status

V0.1 is intended to establish reusable source/package qualification. A generated SPK still needs installation and runtime qualification on the actual NAS model/DSM build before it is called operational.
