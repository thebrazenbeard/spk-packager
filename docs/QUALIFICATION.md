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
