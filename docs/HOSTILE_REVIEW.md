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
> **Resolution:** v0.1's generated service mode is explicitly a foreground-process-becomes-background-via-shell model. Daemons with different lifecycle semantics need a custom template/profile rather than pretending the generic PID contract applies.
