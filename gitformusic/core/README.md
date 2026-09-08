# Rust Core

The Rust core is the local data-plane engine. It will own repository storage, content-addressed versioning, working-tree operations, cryptographic identity, and peer-to-peer synchronization. The C-compatible API is the boundary used by the future C++/JUCE desktop shell.

This is currently the only component in the repository. See:

- [MVP.md](MVP.md) — the local, single-user, CLI-only slice being built first, and why.
- [Requirements.md](Requirements.md) — settled long-term requirements, plus the open questions that still need deciding before the rest of the core can be designed with confidence.
- [Architecture reference](../.docs/ARCHITECTURE.md) — the full platform design these requirements are drawn from, including the cloud and desktop components not yet present here.

## Build

This directory currently contains documentation only: there is no `Cargo.toml` or Rust source to compile.

When the crate is added:

1. Install the stable Rust toolchain with `rustup`.
2. From this directory, run `cargo build` for a debug build.
3. Run `cargo test` for unit and integration tests.
4. Run `cargo build --release` for an optimized client build.

The future crate should expose a stable C-compatible API separately from its internal Rust modules. Platform-specific packaging and the C++/JUCE shell are outside this directory.