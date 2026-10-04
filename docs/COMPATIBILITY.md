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
- ARMv5/ARMv7 -> 40;
- AArch64/armv8 -> 183.

Synology platform strings are mapped where the DSM 7.2.2 guide or the pinned SynoCommunity architecture reference supports a family. Current coarse mappings include x86_64 -> 62, evansport/i686 -> 3, ARMv5/ARMv7 platform families -> 40, and ARMv8/AArch64 -> 183. `armada38x -> 40` is additionally cross-checked against the DS216/Tattler donor.

This is not enough to prove libc version, kernel ABI, instruction-set extensions, dynamic loader, or external library compatibility.

## Toolchain boundary

SPK Packager packages binaries; it does not promise to compile them correctly for every Synology platform. For native code, use the correct Synology toolkit/toolchain or another cross-compiler whose output has been qualified for the target.

## Future profile rule

A future profile such as `dsm-7.3+` should be added only after current Synology documentation is reviewed, changed rules are encoded, regression fixtures are added, exact-source provenance is recorded, and at least one representative package is runtime-qualified on that DSM line.

Do not mutate the meaning of `dsm-7.2.2+` retroactively.
