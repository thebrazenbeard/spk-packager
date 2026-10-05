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
> **Resolution:** The manifest models Synology's documented `ctrl-script`, `executable`, and `tool` privilege entries and the builder must serialize all three; regression tests fail if any declared entry is silently dropped. Payload-targeted entries must resolve to packaged files. Strict mode rejects whole-package and per-entry root escalation; compatibility mode surfaces it as a warning.

> **Challenge:** A manifest-controlled path can be syntactically safe as an archive name and still execute shell syntax when interpolated into a generated lifecycle script.
>
> **Resolution:** Generated runtime paths are shell-quoted as literals after the DSM root variable. Linux CI includes a path containing command substitution syntax and proves that start/status/stop never create the sentinel file.

> **Challenge:** A live PID plus a missing or mismatched start-time receipt could make `start` launch a second service instance.
>
> **Resolution:** Generated `start` now refuses to launch while the PID file still names any live process unless the recorded `/proc/<pid>/stat` start-time identity matches. It fails closed rather than deleting the evidence and spawning a duplicate.

> **Challenge:** A green builder test does not prove the standalone verifier catches malformed third-party SPKs.
>
> **Resolution:** Regression fixtures mutate INFO `extractsize`, lifecycle executable bits, gzip metadata, INFO escaping, archive path forms, and architecture metadata. Strict verification rejects those defects while `--compat-only` relaxes only reproducibility-oriented differences needed to inspect otherwise safe external packages.


> **Challenge:** Fixing gzip `mtime=0` and tar metadata does not make gzip bytes host-independent if compression is delegated to the platform zlib.
>
> **Resolution:** OCD exposed this directly: identical tar/payload bytes built on Windows and Linux produced different `package.tgz` and SPK hashes. The packager now emits a standards-compliant gzip stream using repository-owned DEFLATE stored blocks, fixed header bytes, explicit CRC32, and explicit ISIZE. CI compares the self-test SPK SHA from Windows and Linux; same-host double builds alone no longer establish the strongest reproducibility claim.
