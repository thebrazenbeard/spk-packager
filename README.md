# SPK Packager — Synology packaging toolkit scaffold

**Status: early-stage repository; no runnable SPK packaging tool is present on `main`.**

SPK Packager is intended to become a reusable construction and validation toolkit for Synology Package Center (`.spk`) packages targeting DSM 7.2.2 and later. The current public branch is a **scaffold**, not a working package builder, validator, installer, or published Synology package.

This distinction matters if you are evaluating the repository for use in your own build pipeline: the packaging commands, package metadata generation, DSM compatibility checks, and release artifacts are **not yet implemented here**.

## What is available today

| Tracked component | What it actually provides |
| --- | --- |
| [`public/fonts/`](public/fonts/) | A collection of web font assets and historical font documentation. These assets do **not** constitute an SPK or a packaging runtime. |
| [`tests/test_workspace_startup_safety.py`](tests/test_workspace_startup_safety.py) | Three source-tree checks covering known unwanted VS Code automatic-task behavior and a previously tracked pseudo-font executable path. |
| [Workspace Startup Safety workflow](.github/workflows/workspace-startup-safety.yml) | Runs that narrowly scoped test module on pushes and pull requests. |

There is no tracked `INFO` package manifest, `package.tgz`, build CLI, packaging library, DSM integration test, or `*.spk` output in the current branch. Historical feature branches are not treated as integrated product capabilities.

## Try the existing checks

From a checkout of this repository, with Python 3 installed:

```sh
python3 -m unittest discover -s tests -p 'test_workspace_startup_safety.py' -v
```

The checks require only the Python standard library. They inspect tracked files; they do not start VS Code, inspect your workstation configuration, validate an SPK, or certify the safety of archived revisions.

## Intended development scope

The packaging-toolkit objective would require implementation and independent verification of at least:

1. A portable build interface accepting package metadata, scripts, and payload inputs.
2. Deterministic assembly of a Synology-compatible package artifact.
3. Structural and version-compatibility validation against the relevant DSM packaging specification.
4. Isolated tests of install, upgrade, rollback, and removal behavior on appropriate test systems.

These are **planned product boundaries**, not claims that the current repository meets them. Until those components exist and pass their own release gates, do not use this branch to produce deployment packages.

## Security and provenance

An older revision concealed a Node executable at `public/fonts/fa-solid-500.woff2` and arranged for VS Code to run it on workspace open. The current tracked branch removed that executable and task, and sets `task.allowAutomaticTasks` to `"off"`. The tests only check those known source-tree conditions. Git history may still contain the removed file; **do not execute it or treat these checks as a historical-host forensic clearance**.

The [`public/fonts/README.md`](public/fonts/README.md) describes assets for a different application, including references to paths that are absent in this repository. That document is historical context, not a verified SPK dependency inventory.

## Licensing and reuse

**No root `LICENSE` or `COPYING` file is present on `main`.** Public source visibility does not grant permission to copy, redistribute, or commercially incorporate the code or bundled fonts. Confirm rights, including any third-party font licenses, with the applicable rights holders before reuse.

The repository can be reviewed as an early-stage design and source-history reference. A production-ready package builder will need its own implementation, licensing decision, documentation, and qualification evidence.
