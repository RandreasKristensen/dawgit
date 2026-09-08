# Rust Core — MVP

## Purpose

Before any networking, cloud, or UI work happens, answer the one question the whole
platform depends on: **can real, mostly-binary DAW project files be versioned
usefully with a content-addressed, git-like model?** This MVP is a local-only,
single-user command-line tool whose sole job is to answer that question against
real project files, as cheaply and quickly as possible.

Everything in this MVP runs on one machine, offline, with one user. No sync, no
cloud, no UI, no cryptographic identity beyond content hashing. See
[Requirements.md](Requirements.md) for what comes after, and the [architecture
reference](../.docs/ARCHITECTURE.md) for how this fits the full platform.

## In scope

- **Repository initialization.** Turn a directory containing DAW project files
  (and their audio/samples) into a versioned repository, in place.
- **Content-addressed object store.** Store file contents as immutable blobs,
  addressed by a cryptographic hash of their content, on local disk.
- **Tree and commit objects.** Represent a directory snapshot as a tree of
  blobs/subtrees, and a point-in-time snapshot of the whole project as a commit
  referencing a root tree, matching the model in
  [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#rust-core).
- **Linear history only.** A single reference (`HEAD`) that moves forward one
  commit at a time. No branching, no merging — those are explicitly out of scope
  until [Requirements.md](Requirements.md) settles how binary merge should work.
- **Working tree status.** Report which tracked files changed since the last
  commit (changed/unchanged per file is enough; byte-level diff of binary content
  is not required for the MVP).
- **Checkout / restore.** Materialize any prior commit back onto disk, byte-for-byte
  identical to what was committed.
- **History listing.** List commits in order with their message and timestamp.
- **CLI-only interface.** A single command-line binary. No daemon, no FFI surface,
  no background file watcher — commits are explicit and user-triggered.

Suggested command surface:

```
gfm init                  # start versioning the current directory
gfm status                 # what changed since the last commit
gfm commit -m "<message>"  # snapshot the current working tree
gfm log                    # list commit history
gfm checkout <commit-id>   # restore a prior snapshot
```

## Out of scope for this MVP

- Networking, P2P sync, and the cloud coordination layer entirely.
- Device identity, keypairs, signing, and encrypted transport.
- Angular UI, C++/JUCE shell, and the C-compatible FFI boundary.
- Branching, merging, or any conflict resolution.
- Chunking, deduplication, or packfile/compression of stored objects.
- Cross-platform packaging or installers.
- Multi-user or multi-device scenarios of any kind.

## Success criteria

- `gfm init` on a folder containing a real DAW project (e.g. an Ableton Live set,
  or an equivalent project from another DAW) succeeds and starts tracking it.
- Editing and saving the project in the DAW, then running `gfm commit`, produces a
  new commit whose stored objects, when checked out, are byte-identical to the
  saved file.
- `gfm log` shows an accurate, ordered history after several real editing sessions.
- `gfm checkout` to an earlier commit restores a working, openable project file in
  the DAW that used to produce it.
- The measured on-disk growth per commit for a real project (including audio) is
  known and recorded — this number directly informs whether chunking/deduplication
  needs to move up in priority (see the storage-growth question in
  [Requirements.md](Requirements.md#open-questions)).

## Non-goals

Performance at scale, multi-gigabyte sample library handling, and packaging for
distribution are all deferred. The MVP only needs to work correctly, once, on the
kind of project files the platform is meant to version — it does not need to be
fast, small, or installable by anyone but the person building it.
