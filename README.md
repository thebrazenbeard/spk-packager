# SPK Packager

Bootstrap branch for a reusable Synology DSM 7.2.2+ SPK construction and validation toolkit.

Substantive implementation is developed on isolated feature branches and reviewed before integration.


## Workspace startup safety (source scope)

The concealed VS Code `folderOpen` task ran Node against `public/fonts/fa-solid-500.woff2`, a tracked 27 KB JavaScript executable disguised as a font. The task and pseudo-font were removed and automatic workspace tasks set to valid string `"off"`; static tests and read-only CI now check that specific path. Historical Git revisions retain provenance; do not execute the removed file. Source containment cannot establish whether any older checkout, host, editor extension, or user-level settings were clean.

## Editor startup containment — tracked source (2026-11-20)

The tracked `main` source formerly contained a concealed VS Code `folderOpen` task invoking obfuscated `.vscode/ini` through Node. The task list is now empty, `task.allowAutomaticTasks` is explicitly `"off"`, and the obfuscated file is removed from this source tree. Historical Git source remains for investigation.

**Limits:** This is source-only containment, not proof that older checkouts, editor extensions, user/global settings, local credentials, or any previous host execution are safe. Do not execute historical suspect assets.
