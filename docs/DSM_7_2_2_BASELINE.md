# DSM 7.2.2 baseline

This document records the known package contract encoded by the `dsm-7.2.2+` profile.

## Source-backed rules

Synology's DSM 7.2.2 Developer Guide establishes:

- an SPK contains `INFO`, `package.tgz`, lifecycle scripts, and `conf`; Package Center icons are part of the documented package structure;
- since DSM 7, `conf/privilege` is required and packages are expected to lower privilege explicitly;
- `conf/resource` is optional unless the package requests DSM-managed resources;
- `precheckstartstop=yes` causes `start-stop-status prestart` before `start`, and `prestop` before `stop`;
- package scripts receive DSM/package environment such as `SYNOPKG_PKGDEST`, `SYNOPKG_PKGVAR`, DSM version fields, arch, package status, and `SYNOPKG_TEMP_LOGFILE`;
- `WIZARD_UIFILES` is available from DSM 7.2.2;
- package signing is deprecated after DSM 7.0;
- `os_min_ver` uses `X.Y-BUILD`; this repository uses `7.2-72806` as the DS216/Tattler DSM 7.2.2 baseline.

Official sources:

- https://help.synology.com/developer-guide/
- https://help.synology.com/developer-guide/synology_package/introduction.html
- https://help.synology.com/developer-guide/synology_package/INFO.html
- https://help.synology.com/developer-guide/synology_package/INFO_necessary_fields.html
- https://help.synology.com/developer-guide/synology_package/INFO_optional_fields.html
- https://help.synology.com/developer-guide/synology_package/scripts.html
- https://help.synology.com/developer-guide/synology_package/conf.html
- https://help.synology.com/developer-guide/privilege/privilege_config.html
- https://help.synology.com/developer-guide/synology_package/script_env_var.html
- https://help.synology.com/developer-guide/toolkit/pack_stage.html
- https://help.synology.com/developer-guide/appendix/platarchs.html

## Project-derived rule: stopped status

The Tattler v0001 package installed on DSM 7.2.2 but failed to start. Independent source inspection then found two package-contract defects: it returned shell status 1 for a cleanly stopped state and declared `precheckstartstop=yes` without implementing `prestart` / `prestop`.

Those defects are concrete source findings and strong startup-failure candidates, but the original failure was not traced to a DSM log line proving either defect was the sole cause. The corrected lifecycle implements `prestart` / `prestop` and distinguishes:
- `0`: running;
- `1`: stale/dead PID state;
- `3`: cleanly not running.

SPK Packager keeps this distinction in the generated service template and regression tests. Live qualification of the corrected Tattler package remains a separate runtime gate.

## What is not established

This baseline does not establish that:
- every later DSM release preserves all 7.2.2 behavior;
- an ELF machine number proves ABI compatibility;
- a structurally valid SPK will run on a specific NAS;
- a package requesting root privilege is safe or necessary;
- every optional Synology integration is supported by SPK Packager v0.1.

Those remain separate qualification questions.
