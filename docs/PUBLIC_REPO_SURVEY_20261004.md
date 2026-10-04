# Public repository survey — 2026-10-04

This survey records public Synology packaging mechanisms reviewed while extending SPK Packager beyond the original Tattler donor. It is a broad GitHub code/repository sweep, not a mathematically exhaustive scan of every public repository.

Evidence classes stay separate:
- **OFFICIAL-DOC MIRROR**: public repository copy of Synology documentation with its original source URL recorded.
- **REFERENCE SOURCE**: implementation/source code that demonstrates a packaging mechanism.
- **EMPIRICAL REPORT**: maintainer report tied to stated real DSM hardware/runtime observations.
- **PROJECT DECISION**: behavior admitted into SPK Packager after comparison against stronger evidence.

## Synology documentation mirror

`EIGHTfs/DeepSeekHarness-NAS@d6369f4ed1a4a069e5875a1dc7644b6278ea664e`

Reviewed mirrors whose headers identify `help.synology.com/developer-guide/...` as their source:
- `docs/官方文档/spk/synology_package__INFO_optional_fields.md`
- `docs/官方文档/spk/synology_package__introduction.md`
- `docs/官方文档/spk/privilege__privilege_config.md`

Useful rules:
- `checksum` is the MD5 string for `package.tgz`.
- `extractsize` is the minimum install-space hint; DSM 6.0+ interprets it in KB.
- DSM 7 Package Center icon dimensions are 64x64 and 256x256.
- `LICENSE`, when present, must be smaller than 1 MB.
- `conf/privilege.tool` can set ownership/mode for a target-relative file; documented `user` and `group` are both `package`.
- `tool.capabilities` is available from DSM 7.0-40656 and accepts capability names without `+-=eip` symbols.
- `WIZARD_UIFILES` is available from DSM 7.2.2.

## SynoSmartInfo

`PeterSuh-Q3/SynoSmartInfo@cc83dd7529655aec35aa0f9e76b3a8c4de57f7f8`

Reviewed `docs/synology-spk-build-notes.md` and `build-spk.sh`.

The maintainer reports real DSM 7.4.1 manual-install observations, including rejection when `INFO.checksum` is missing and the importance of live Package Center/synopkg qualification. The build script emits `checksum`, `extractsize`, normalized ownership metadata, and a plain outer tar.

**Project decision:** SPK Packager now emits and verifies `checksum` and `extractsize`. The checksum is package-integrity metadata, not a cryptographic trust claim.

**Conflict preserved:** the empirical notes show a `privilege.tool` example with `user: root`; the mirrored official privilege schema says `tool.user` and `tool.group` must both be `package`. SPK Packager follows the official schema until live evidence and authoritative documentation resolve otherwise.

## synology-github-backup

`marvingerstner/synology-github-backup@fe61ad564bd3ee9ed722ec6cc380995ab7c4bd7b`

Reviewed `build.sh`.

Useful mechanisms:
- explicitly writes ustar instead of host-default pax;
- rejects PAX headers and `./`-prefixed paths;
- puts `INFO` first in the outer SPK;
- normalizes ownership metadata;
- packages multiple native CPU binaries behind a portable dispatcher.

**Project decision:** SPK Packager emits ustar, forces `INFO` first, rejects PAX/`./` paths, and supports native multi-architecture `noarch` bundles only through explicit opt-in plus a non-ELF service dispatcher.

## iroh-share

`n0-computer/iroh-share@4be9a5f67294d24cffe01b696af96190c724922a`

Reviewed `packaging/synology/build.py`.

Useful mechanism: a single `noarch` package contains architecture-specific native binaries and a portable runtime selector. This independently falsifies the naive rule that any ELF inside an `arch=noarch` SPK is necessarily invalid.

## nzbfast

`nzbfast/nzbfast@370da775361e29a9fb0d490f4750df899ea56c92`

Reviewed `packaging/synology/make-spk.sh`.

Useful mechanisms:
- release binaries are checksum-verified before packaging;
- multiple architecture binaries are carried in one `noarch` package;
- inner and outer tar ownership is normalized;
- ustar is explicitly requested;
- the payload contents, not a wrapping directory, become `target/`.

The upstream-artifact checksum workflow is useful but is outside SPK Packager's current boundary: the packager verifies the bytes it is given rather than fetching releases itself.

## Other packagers inspected

- `tomgrv/synology-package-builder@8ec13cd020fa6c48edde25e4ecd8c6381e2b690c`
- `rednoah/ant-spk@c45566ef692f1653a1cff7a69de24db3c116755d`
- `vletroye/Mods@60fdc435adb10ed73996dd227cf2d6126fa6f260`
- `SynoCommunity/spksrc@00052786a00a4c3cc6b1eaaf7bf7495031bba1bb`
- `SynologyOpenSource/ExamplePackages@d2849c6fcf14ce72007d14e99a362c3d4f23be0a`

These remain reference sources. SPK Packager does not vendor their implementations.

## Admission rule

A public-repository mechanism is not admitted merely because another project uses it. Prefer, in order:
1. current Synology documentation;
2. multiple independent implementations consistent with that documentation;
3. explicit real-DSM empirical evidence;
4. a regression test that encodes the adopted behavior;
5. live NAS qualification for claims about installation/runtime behavior.

Where sources conflict, preserve the conflict and follow the stronger authority rather than averaging them.
