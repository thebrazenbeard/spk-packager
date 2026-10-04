# Tattler-like manifest

This is the direct conceptual migration of the Tattler v0002 package into SPK Packager's manifest model.

It is intentionally not a build fixture because the Tattler ARMv7 binary and final artwork belong to the Tattler repository/build pipeline. Copy this manifest into a Tattler checkout (or adjust the source paths), provide 64x64 and 256x256 icons, and point `source` at the exact ARMv7 build artifact.

The important regression-bearing fields are:

- `precheckstartstop = true`;
- package-user privilege;
- `armada38x` plus ELF machine 40;
- state under `SYNOPKG_PKGVAR`;
- a generated lifecycle script that implements `prestart`, `prestop`, and status code 3 when stopped.
