from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchHint:
    family: str
    elf_machine: int | None
    evidence: str


_HINTS: dict[str, ArchHint] = {}

for name in (
    "x86_64", "apollolake", "avoton", "braswell", "broadwell", "broadwellnk",
    "broadwellntb", "broadwellntbap", "bromolow", "cedarview", "coffeelake",
    "denverton", "geminilake", "grantley", "kvmx64", "purley", "skylaked", "v1000",
):
    _HINTS[name] = ArchHint("x86_64", 62, "Synology DSM 7.2.2 platform/arch mapping")

for name in ("armv8", "rtd1296", "armada37xx", "rtd1619", "rtd1619b"):
    _HINTS[name] = ArchHint("armv8", 183, "Synology DSM 7.2.2 platform/arch mapping")

for name in ("armv7", "alpine", "alpine4k"):
    _HINTS[name] = ArchHint("armv7", 40, "Synology DSM 7.2.2 platform/arch mapping")

_HINTS["armada38x"] = ArchHint("arm32", 40, "Tattler DS216 ARMv7 qualified build donor")


def arch_hint(name: str) -> ArchHint | None:
    if name == "noarch":
        return ArchHint("noarch", None, "Synology noarch package semantics")
    return _HINTS.get(name)


def expected_elf_machines(arch_values: tuple[str, ...]) -> tuple[set[int], list[str]]:
    machines: set[int] = set()
    warnings: list[str] = []
    for value in arch_values:
        hint = arch_hint(value)
        if hint is None:
            warnings.append(f"no ELF-machine hint for Synology arch {value!r}")
            continue
        if hint.elf_machine is not None:
            machines.add(hint.elf_machine)
    return machines, warnings
