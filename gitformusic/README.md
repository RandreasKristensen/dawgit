# Git for Music

Git for Music is a cross-platform system for versioning and sharing music project files.

> We host the collaboration. You own the files.

## Current scope

This repository currently contains a single component: [`core`](core/README.md), the
Rust local versioning engine. Everything else in the platform's design — the Angular
frontend, the shared protocol, client infrastructure, and the proprietary C# cloud
backend — is deliberately not scaffolded here yet. See
[`.docs/ARCHITECTURE.md`](.docs/ARCHITECTURE.md#why-the-repository-is-scoped-to-core-right-now)
for why.

- [`core/MVP.md`](core/MVP.md) — the local, single-user, CLI-only slice being built
  first.
- [`core/Requirements.md`](core/Requirements.md) — settled long-term requirements
  for the core, and the open questions that still need deciding.
- [`.docs/ARCHITECTURE.md`](.docs/ARCHITECTURE.md) — the full platform architecture,
  including the components not yet present in this repository, with all diagrams.

## Build

There is not yet a buildable application in this checkout. [`core/README.md`](core/README.md)
describes the expected Rust build commands once a `Cargo.toml` and source exist.

Do not use the C# backend build steps here; that component is proprietary and
maintained in a separate repository.
