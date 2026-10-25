# SPK Packager

Bootstrap branch for a reusable Synology DSM 7.2.2+ SPK construction and validation toolkit.

Substantive implementation is developed on isolated feature branches and reviewed before integration.


## Workspace startup safety (source scope)

The concealed VS Code `folderOpen` task ran Node against `public/fonts/fa-solid-500.woff2`, a tracked 27 KB JavaScript executable disguised as a font. The task and pseudo-font were removed and automatic workspace tasks set to valid string `"off"`; static tests and read-only CI now check that specific path. Historical Git revisions retain provenance; do not execute the removed file. Source containment cannot establish whether any older checkout, host, editor extension, or user-level settings were clean.
