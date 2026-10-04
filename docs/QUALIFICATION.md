# Qualification states

SPK Packager intentionally separates evidence classes.

## SOURCE_VALIDATED

Manifest parses, lint has no errors, unit tests pass, and generated scripts compile or parse where applicable.

## SPK_STRUCTURALLY_VERIFIED

The exact SPK opens safely, contains required metadata and lifecycle members, has deterministic normalized tar metadata, has valid privilege JSON, satisfies strict icon rules when enabled, passes known lifecycle static checks, and has payload paths and coarse architecture checks consistent with INFO.

## SPK_REPRODUCIBLE

Two independent builds from the same exact source inputs produce the same SHA-256.

## DSM_INSTALLED

Package Center accepted the exact SPK on an exact NAS/DSM subject.

## DSM_RUNTIME_VERIFIED

The installed package starts, stops, and restarts correctly and its service behavior is read back on the actual NAS.

## APPLICATION_BEHAVIOR_VERIFIED

The packaged application itself performs its intended function under representative workload.

No lower state implies a higher state.

## 2026-10-04 real-donor qualification

SPK Packager was exercised against the current Tattler donor subject
`thebrazenbeard/tattler@c11ac394828a76b971a32e178632f81e8a08b237`.

The donor source rebuilt deterministically for `linux/arm/v7` with binary SHA-256
`C9C3CE1B3B1CB8222B8E8B5570B075D882358C2B0A57DC7F22609A9EF24EEAB8`.

Using the Tattler-shaped manifest, the donor's 64x64 and 256x256 icons, and that exact
binary, SPK Packager linted, built, rebuilt, and verified the package successfully.
After the POSIX lifecycle/PID-identity fix was qualified at packager source
`45e73af5d3501db5c56fb03d133609f87386db1e`, both package builds were
byte-identical at SHA-256
`94D404BA202B0AC21FB957AB615D0E048B93B64F6F6ED8866B65852FCECCA100`.
Verification observed `INFO arch=armada38x` and payload ELF `e_machine=40`.

This establishes `SOURCE_VALIDATED`, `SPK_STRUCTURALLY_VERIFIED`, and
`SPK_REPRODUCIBLE` for that fixture. It does not establish `DSM_INSTALLED` or
`DSM_RUNTIME_VERIFIED` for the SPK Packager-generated Tattler artifact.

## 2026-10-04 public-repository hardening qualification

Implementation subject: `eaf12a888b3d93f23dab23844a58ddc6e416c230`.

Project Runner read back that exact GitHub branch head successfully. GitHub Actions
CI run #14 passed on Python 3.11 and 3.13, including compile, unit tests, the real
POSIX lifecycle harness, deterministic self-test, and generated-shell syntax.

The expanded local suite passed 12 tests on Windows with only the POSIX-only lifecycle
test deferred to Linux CI. The deterministic self-test produced SHA-256
`48E6050319855D2C622137115ECE0514EFEEC6EBF10D63641D1284A09500C9F9`.

The same current Tattler donor payload was packaged twice with the hardened packager.
Both outputs were byte-identical at SHA-256
`24B013783A680DB906DB3B8CD4DCE8F85D542DF43DF9E9784C5170992F955CEB`.
The generated INFO contained `checksum=9e8377aa4d61fe1f1494e6a7ffb7c62a`,
which matched the exact `package.tgz` MD5 on verification, and
`extractsize=5185`. Architecture readback remained `armada38x` with payload ELF
`e_machine=40`.

This qualifies the new checksum/extractsize, USTAR/INFO-first, explicit noarch native
bundle, and documented `privilege.tool` source/package mechanisms. It still does not
establish Package Center installation or runtime behavior on a NAS for the newly
generated artifact.
