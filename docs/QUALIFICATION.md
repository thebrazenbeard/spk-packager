# Qualification states

SPK Packager intentionally separates evidence classes.

## SOURCE_VALIDATED

Manifest parses, lint has no errors, unit tests pass, and generated scripts compile or parse where applicable.

## SPK_STRUCTURALLY_VERIFIED

The exact SPK opens safely, contains required metadata and lifecycle members, has deterministic normalized tar metadata, has valid privilege JSON, satisfies strict icon rules when enabled, passes known lifecycle static checks, and has payload paths and coarse architecture checks consistent with INFO.

## SPK_REPRODUCIBLE

Independent builds from the same exact source inputs produce the same SHA-256. For the current v0.1 qualification bar, this includes a Windows/Linux cross-host comparison; two rebuilds on one host are useful evidence but do not by themselves establish host-independent reproducibility.

## DSM_INSTALLED

Package Center accepted the exact SPK on an exact NAS/DSM subject.

## DSM_RUNTIME_VERIFIED

The installed package starts, stops, and restarts correctly and its service behavior is read back on the actual NAS.

## APPLICATION_BEHAVIOR_VERIFIED

The packaged application itself performs its intended function under representative workload.

No lower state implies a higher state.

Historical sections below predate the Windows/Linux cross-host gate. Their byte-identical double-build evidence establishes same-host reproducibility for those exact subjects, not the stronger cross-host claim introduced afterward.

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

## 2026-10-04 final hostile-hardening qualification

Implementation subject: `2f032d2f23fcbed1e7d3eae62da212a84d2a6528`.

Project Runner read back that exact GitHub branch head successfully. GitHub Actions
CI run #18 passed on Python 3.11, 3.12, 3.13, and 3.14. Every Linux matrix job ran
the complete 25-test suite, including the POSIX lifecycle harness and the
manifest-path command-substitution sentinel, then passed deterministic self-test,
generated-package verification, and generated-shell syntax validation.

The Windows-local suite passed all 23 platform-applicable tests; the two POSIX-only
lifecycle tests were skipped locally and executed successfully in GitHub's Linux
matrix. Deterministic self-test SHA-256 was
`4152D8926084B1E4F44829827CDB66BFC902C940DD931C9E443378744582C989`.

The current Tattler donor binary remained exactly
`C9C3CE1B3B1CB8222B8E8B5570B075D882358C2B0A57DC7F22609A9EF24EEAB8`.
The hardened packager produced the donor SPK twice byte-identically at SHA-256
`ABE93B507839238F8542EF92A5E1755BC7D9445FB9E32F4CE77D7B82100BDB1A`.
Strict verification read back `checksum=9e8377aa4d61fe1f1494e6a7ffb7c62a`,
`extractsize=5196`, `arch=armada38x`, payload bytes `5308551`, and payload
ELF `e_machine=40`.

This exact subject additionally qualifies the source/package behavior for canonical
archive paths, manifest input confinement with explicit external-source opt-in,
strict TOML type handling, INFO escaping/semantics, conservative deterministic
`extractsize`, gzip reproducibility metadata, expanded Synology architecture
families, live-PID duplicate-start fail-closed behavior, and the documented
`conf/privilege` `ctrl-script`, `executable`, and `tool` structures. Strict
mode rejects package-wide and per-entry root escalation.

It still does not establish `DSM_INSTALLED`, `DSM_RUNTIME_VERIFIED`, or
`APPLICATION_BEHAVIOR_VERIFIED` for the newly generated Tattler artifact.
