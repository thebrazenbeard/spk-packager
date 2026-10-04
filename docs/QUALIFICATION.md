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
Both package builds were byte-identical at SHA-256
`3814DFE40BD325313F7DB18EA907E04F590FDC70D5C9C943378F3E0F86E2B5E2`.
Verification observed `INFO arch=armada38x` and payload ELF `e_machine=40`.

This establishes `SOURCE_VALIDATED`, `SPK_STRUCTURALLY_VERIFIED`, and
`SPK_REPRODUCIBLE` for that fixture. It does not establish `DSM_INSTALLED` or
`DSM_RUNTIME_VERIFIED` for the SPK Packager-generated Tattler artifact.
