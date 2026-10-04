# Tattler extraction

Donor subject:

`thebrazenbeard/tattler@c11ac394828a76b971a32e178632f81e8a08b237`

Donor branch:

`build/tattler-v1-sol-20261004`

## Generalized mechanisms

The following ideas were extracted and generalized:

- sorted deterministic tar members;
- uid/gid/mtime normalization;
- deterministic gzip `mtime=0`;
- safe archive path checks;
- ARM ELF machine sanity checking;
- `INFO` generation;
- required DSM Package Center icon presence and 64x64 / 256x256 dimension checks;
- `conf/privilege` with package-user execution;
- generated lifecycle scripts;
- DSM `prestart` / `prestop` handling;
- status code `3` for a cleanly stopped service;
- `SYNOPKG_TEMP_LOGFILE` startup diagnostics;
- source/build/package/runtime evidence separation;
- repeated build equality as reproducibility evidence.

## Deliberately not copied

SPK Packager does not embed:
- Tattler's network monitor;
- Tattler's diagnostics sampler;
- Tattler-specific ports, flags, state layout, or package identity;
- Tattler's package version;
- Tattler's application code.

The result is a package framework, not a renamed Tattler checkout.
