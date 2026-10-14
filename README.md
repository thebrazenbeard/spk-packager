# SPK Packager

This repository contains a **bounded, read-only SPK verifier candidate** on
`feature/verify-dsm-packages-20261014-portal`. The canonical bootstrap
history is preserved. It does not yet contain a general-purpose SPK builder.

## Implemented verification profile

The source module `src/spk_packager/cli.py` independently inspects the
specific published **Tattler DSM 7.2.2+** package profile. It accepts
x86_64, armv7, and armv8 variants only. Inspection checks static tar
membership and traversal safety, deterministic metadata, DSM INFO
architecture and version, checksum and extracted-size consistency,
package-user privilege and state hooks, PNG header/dimensions, an
architecture-matching ELF payload, and loopback-only service markers.

It does not extract archives, execute scripts or binaries, install to a
Synology machine, assert DSM compatibility from hardware, or grant any
privilege. An `ok: true` report is **structural static evidence only**.

Example:

```sh
PYTHONPATH=src python -m spk_packager.cli verify path/to/Tattler-armv7.spk --json
PYTHONPATH=src python -m unittest discover -s tests -v
```

The tool exits nonzero for unsupported/malformed SPKs and prints an explicit
failure payload. Future generic SPK packaging support needs a separate
reviewed contract; do not infer it from the repository name.

## Qualification

Offline synthetic positive/adversarial tests validate the three supported
architectures, altered checksum, malformed archive, wrong ELF architecture,
privilege escalation, and unsafe member inventory. An independent Lappy
readback against all three existing public Tattler release files passed
using this exact source directory, rather than an installed Python package.

> **HOSTILE REVIEW — accepted:** Separate source and parser implementation
> reduces direct implementation coupling with Tattler's in-repo verifier,
> but is not an independent third-party security audit. The static
> shape/metadata checks cannot prove the service will run or remain safe
> on DSM. A real Synology acceptance run and separate external review
> remain outside this change.
