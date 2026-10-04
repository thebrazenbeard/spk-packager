# Hostile review

> **Challenge:** “DSM 7.2.2+” sounds like a promise that unknown later DSM releases work.
>
> **Resolution:** The profile means a 7.2.2 source baseline with no upper install bound. Later runtime compatibility is explicitly unverified until tested. Future changed contracts get new profiles.

> **Challenge:** A hand-built tarball can drift from Synology's official Package Toolkit.
>
> **Resolution:** The repository validates documented package structure and reproducibility, and records the official toolkit as the authoritative compilation/packing reference. It does not claim byte-equivalence to `PkgCreate.py`. NAS installation remains a separate gate.

> **Challenge:** Searching a shell script for `prestart)` is not semantic verification.
>
> **Resolution:** Static verification is only one layer. Generated lifecycle behavior is also executed in a POSIX regression harness: prestart -> stopped status 3 -> start -> running status 0 -> stop -> stopped status 3.

> **Challenge:** ELF `e_machine=40` does not prove an ARM binary will run on DS216.
>
> **Resolution:** The check is labelled a machine-class sanity check only. Toolchain/ABI and live target execution remain separate evidence.

> **Challenge:** Auto-generated placeholder icons could encourage shipping ugly packages.
>
> **Resolution:** Scaffolding creates deterministic valid placeholders so the package structure is complete. Production projects should replace them; visual polish is not confused with package correctness.

> **Challenge:** Root execution is sometimes legitimately required.
>
> **Resolution:** Synology's DSM 7 guidance says packages should explicitly lower privilege, and unsigned root packages require a separate development-token/signing path. The strict profile therefore rejects root; `strict=false` leaves an explicit warning for controlled privileged-development cases.

> **Challenge:** A generic lifecycle wrapper can mishandle daemons that fork, double-fork, manage their own PID file, or exit after spawning children.
>
> **Resolution:** v0.1's generated service mode is explicitly a foreground-process-becomes-background-via-shell model. Daemons with different lifecycle semantics need a custom lifecycle script rather than pretending the generic PID contract applies.

> **Challenge:** A stale PID file plus Linux PID reuse could cause a stop operation to signal an unrelated process.
>
> **Resolution:** Generated lifecycle scripts bind the PID to the process start-time value from `/proc/<pid>/stat`. Status and stop require both PID and start-time to match; a mismatch is treated as stale state and is cleaned without signalling the PID. Linux CI exercises this fail-safe path.

> **Challenge:** Static lifecycle lint can reject valid shell such as `prestart|prestop|start|stop)`, or accept text that merely contains an action name in a comment.
>
> **Resolution:** v0.1 recognizes grouped shell-case labels instead of literal `prestart)` substrings, and Linux CI executes the generated lifecycle through the actual POSIX harness. This is still bounded validation, not a general shell parser; custom scripts remain subject to live DSM qualification.

> **Challenge:** Requiring `arch=noarch` to contain no native binaries rejects a legitimate packaging pattern used by packages that bundle several native architectures and dispatch at runtime.
>
> **Resolution:** Native ELF under `noarch` remains rejected by default. A project may explicitly opt into `allow_noarch_native_bundle=true`, but the service entrypoint must be a non-ELF portable dispatcher and structural verification still surfaces every native machine class. This records the exception without turning `noarch` into a silent architecture bypass.

> **Challenge:** Adding `checksum`, `extractsize`, USTAR, and INFO-first rules because public repos do it risks cargo-culting implementation folklore.
>
> **Resolution:** `checksum` and `extractsize` are documented Synology INFO fields; public repositories provide corroborating and real-hardware failure evidence. USTAR/INFO-first/PAX rejection are packaging hardening derived from multiple independent working packers. They remain source/package checks, not claims of DSM runtime qualification.

> **Challenge:** A privilege helper feature can quietly recreate root-equivalent packaging.
>
> **Resolution:** `[[privilege.tool]]` follows the documented DSM schema: the target must exist in the payload, user/group remain `package`, permissions are constrained, and Linux capabilities are explicit. Whole-package root remains rejected by the strict profile.
