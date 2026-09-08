# Rust Core

The Rust core is the whole engine: repository storage, content-addressed versioning,
DAWproject format handling, working-tree operations, and — later — cryptographic
identity and peer-to-peer synchronization. It is an embeddable library with a CLI on
top.

The design decision to read first: DAWproject is not a supported format, it **is**
the repository format. A session's `.dawproject` is unpacked into per-entry blobs and
is the source of truth for history, diff, and merge; every other file in the
directory is tracked as an opaque blob with no special meaning. See
[the architecture reference](../.docs/ARCHITECTURE.md#dawproject-is-the-repository-format).

- [MVP.md](MVP.md) — the local, single-user, CLI-only slice being built first.
- [Requirements.md](Requirements.md) — settled long-term requirements, plus the open
  questions that still need deciding.
- [Architecture reference](../.docs/ARCHITECTURE.md) — the full design these
  requirements are drawn from.

## Build

This directory currently contains documentation only: there is no `Cargo.toml` or
Rust source to compile.

When the crate is added:

1. Install the stable Rust toolchain with `rustup`.
2. From this directory, run `cargo build` for a debug build.
3. Run `cargo test` for unit and integration tests.
4. Run `cargo build --release` for an optimized build.

The object model and storage layers stay format-agnostic — they see blobs and trees,
never DAW concepts. Format knowledge lives in one place and does not leak downward.
