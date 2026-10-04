# Compatibility model

## Current profile

`dsm-7.2.2+` means:

1. package structure and lifecycle are validated against the known DSM 7.2.2 contract;
2. `os_min_ver` must be at least `7.2-72806`;
3. `os_max_ver` is not added by default, so DSM may consider later compatible releases installable;
4. future DSM behavior is not silently treated as verified.

The plus sign therefore means **open upper install range**, not **future runtime certification**.

## Architecture checks

SPK Packager uses ELF `e_machine` only as a coarse sanity check:

- x86_64 -> 62;
- i686 -> 3;
- ARMv5/ARMv7/ARMv7L -> 40;
- AArch64/armv8 -> 183;
- PowerPC/QorIQ -> 20.

Synology platform strings are mapped where the DSM 7.2.2 guide or the pinned SynoCommunity architecture reference supports a family. The table covers current/legacy x64, evansport/i686, DSM ARMv5/ARMv7/ARMv7L, AArch64/ARMv8, and PowerPC/QorIQ families. `armada38x -> 40` is additionally cross-checked against the DS216/Tattler donor. Unknown architecture strings remain warnings for script/data-only payloads but become strict errors when native ELF is present because the machine-class check cannot then establish compatibility.

This is not enough to prove libc version, kernel ABI, instruction-set extensions, dynamic loader, or external library compatibility.

A `noarch` package normally may not contain native ELF payloads. The explicit `allow_noarch_native_bundle=true` mode exists for the documented-in-the-wild pattern where a portable dispatcher selects among several bundled native binaries. That mode is an exception with visible warnings, not a weakening of the default architecture check.

## Archive and INFO compatibility hardening

The strict profile emits and verifies Synology's documented `checksum=MD5(package.tgz)` field, emits a deterministic conservative `extractsize`, writes deterministic USTAR archives with `INFO` first, and rejects PAX/`./` archive artifacts. Standalone verification also checks lifecycle script executability, gzip timestamp/metadata fields, INFO semantics, payload lower-bound size, privilege targets, and native architecture mappings. `--compat-only` relaxes reproducibility-only constraints for inspecting third-party packages without silently weakening path traversal, checksum, or semantic safety checks.

## Toolchain boundary

SPK Packager packages binaries; it does not promise to compile them correctly for every Synology platform. For native code, use the correct Synology toolkit/toolchain or another cross-compiler whose output has been qualified for the target.

## Future profile rule

A future profile such as `dsm-7.3+` should be added only after current Synology documentation is reviewed, changed rules are encoded, regression fixtures are added, exact-source provenance is recorded, and at least one representative package is runtime-qualified on that DSM line.

Do not mutate the meaning of `dsm-7.2.2+` retroactively.
