# Manifest v0.1

SPK Packager reads `spk-packager.toml`.

## compatibility

- `profile`: currently `dsm-7.2.2+`.
- `strict`: when true, documented Package Center icons are required and dimensions are checked.

## package

Required: `id`, `version`, `description`, `maintainer`, `arch`, and `os_min_ver`.

Optional: `display_name`, `os_max_ver`, `thirdparty`, `precheckstartstop`, and `ctl_stop`.

Package versions are constrained to numeric components separated by `.`, `-`, or `_`; each component must be at most `2^31-1`, matching Synology's documented field limit.

## service

For `enabled=true`, configure `command`, `args`, `pid_file`, `log_file`, `state_dirs`, `start_probe_seconds`, and `stop_timeout_seconds`.

Arguments may contain `{pkgdest}` and `{pkgvar}`, expanded at runtime to DSM's package target and variable directories.

The generic service contract assumes the launched command remains the process represented by the stored PID.

## privilege

`run_as = "package"` is the default. The strict DSM 7.2.2+ profile rejects `run_as = "root"`; `strict=false` downgrades that to a warning for explicitly managed privileged-development cases. `username` and `groupname` are optional.

## assets

Optional paths relative to the manifest are `icon64`, `icon256`, `license`, `wizard_dir`, and `resource`.

Strict `dsm-7.2.2+` requires 64x64 and 256x256 icons. `resource` must be a JSON object when supplied.

## scripts

Optional custom lifecycle scripts can override generated/default scripts:

- `start_stop_status`
- `preinst`
- `postinst`
- `preuninst`
- `postuninst`
- `preupgrade`
- `postupgrade`

Paths are relative to the manifest. When `precheckstartstop=true`, a custom `start_stop_status` must visibly handle both `prestart` and `prestop`. Custom scripts are packaged executable and are linted for missing files, missing shebangs, and CRLF line endings.

## payload.files

Each `[[payload.files]]` contains `source`, `destination`, `mode`, and optional `expected_elf_machine`.

Duplicate destinations, file-vs-parent path collisions, and path traversal are rejected.

## info.extra

`[info.extra]` may add INFO fields but cannot override fields SPK Packager owns.
