# Rust Core — Long-Term Requirements

## Purpose

This document captures the requirements for the Rust core that are already settled
— derived directly from the architecture diagrams in
[`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md) and considered concrete, well
thought out, or simply obvious given the product's premise. It describes where the
core is headed *after* [MVP.md](MVP.md). Anything not yet decided is listed in
[Open Questions](#open-questions) at the bottom, rather than asserted here as a
requirement — if it's in this list, it still needs a decision, a discussion, or
research before it can be built.

## Object model and storage

- Project content is represented with a content-addressed object model: blob
  (file contents), tree (directory structure), commit (project snapshot), and a
  reference manager for branches/HEAD/tags — mirroring Git's proven model.
- Objects are immutable and identified by a cryptographic hash of their content.
- The object store lives entirely on the local device; the cloud never receives or
  persists object content.
- The core must expose a garbage collection path that removes objects no longer
  reachable from any reference.
- A repository lock manager must protect the object store from concurrent,
  conflicting mutation (e.g. two processes committing at once).
- An object index is required for reasonable lookup performance once the object
  count is large.

## Working tree

- The core must be able to scan a project directory and build a manifest of its
  current state.
- The core must be able to compare the working tree manifest against the last
  committed tree to report status (changed/added/removed files).
- The core must be able to materialize (checkout) any historical commit back onto
  the filesystem, reproducing file contents exactly.
- A filesystem watcher is a reasonable future addition for detecting changes
  without polling, feeding the same manifest the scanner produces.

## Synchronization engine

- Synchronization is peer-to-peer: two Rust cores exchange only the objects one is
  missing relative to a target commit, verified by content hash before being
  stored, matching the sequence in
  [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#p2p-synchronization).
- A sync session requires: peer identity/authentication, inventory negotiation
  (what does each side already have), object transfer, and integrity verification
  of every received object before it is committed to local storage.
- The cloud coordinates *session setup* (permission checks, peer discovery,
  connection candidates) but is never a party to the object transfer itself and
  never persists transferred content.
- Reference updates (moving a branch/HEAD forward) are only applied after the
  referenced commit and its full object closure have been verified locally.

## Cryptography and identity

- Each device holds its own identity keypair, stored in an OS-protected key store,
  never transmitted to the cloud.
- The cloud coordinates identity (issuing session tokens, evaluating permissions)
  without ever possessing device private keys.
- Peer-to-peer sessions must be mutually authenticated and encrypted end-to-end;
  the cloud cannot observe P2P payload content.
- Commits and other trust-sensitive metadata should be signable with the device
  identity to support future provenance/verification needs.

## Networking and transport

- A plain TCP transport is sufficient for the initial networked version (post-MVP)
  and does not require NAT traversal or relay infrastructure to exist yet.
- Transport-level security (TLS or equivalent) and authenticated encryption of
  payloads are required before any real network sync ships, regardless of
  transport choice.
- QUIC, NAT traversal, and an encrypted relay fallback are acknowledged future
  needs for making P2P sync work across ordinary consumer networks, but are not
  required for the first networked milestone.

## Interfaces

- The core must expose its operations through more than one surface over time: a
  CLI (for scripting and the MVP), a C-compatible FFI API (for the C++/JUCE
  desktop shell), and eventually a local daemon for long-running services (e.g.
  watching the filesystem, holding a sync session open).
- The FFI surface must be stable and versioned independently of internal Rust
  module structure, since the desktop shell depends on it directly.
- The dependency direction is fixed: interface layer → application services →
  object model/storage and synchronization services → transport/cryptography.
  Higher layers may depend on lower layers; the reverse is not allowed.

## Non-functional

- The core is cross-platform (Windows, macOS, Linux) since the desktop shell it
  serves targets all three.
- The core owns project content exclusively; no other component (cloud, frontend)
  is a source of truth for file contents or version history.
- The core must be usable as a library embedded in a host process (the JUCE shell)
  as well as a standalone binary (the CLI) — it should not assume it owns the
  process it runs in.

## Open questions

These are the things this document deliberately does **not** answer yet. Each one
needs a decision, a discussion, or research before the corresponding part of the
core can be built with confidence. The MVP is partly designed to generate evidence
for these.

1. **Merge semantics for binary/proprietary DAW formats.** Git-style content
   addressing solves storage, not merging. Most DAW project files (Ableton, Logic,
   FL Studio, Cubase, etc.) are binary or opaque zipped-XML with no meaningful
   3-way merge. Does the product ever support merging two divergent edits, or is
   history strictly linear (last-commit-wins, pick-a-version, or an explicit
   locking model)? This decision shapes the object model, the sync protocol, and
   the UI, and should be made before real sync work starts.
2. **Large-file storage growth.** Full-blob content addressing means every changed
   version of a multi-gigabyte audio file is stored again in full. Is
   content-defined chunking/deduplication needed from the start, or can it wait
   until the MVP's measured on-disk growth (see
   [MVP.md](MVP.md#success-criteria)) shows it's actually a problem?
3. **Packfile/compression strategy.** Is a Git-style packfile layer needed for
   this workload (large binary/audio files compress differently than source code),
   or does raw per-object storage suffice for realistic project sizes?
4. **Offline/async sync model.** The current sync sequence assumes both peers are
   online simultaneously. Does the product need an async path (push to a relay or
   staging point, pull later) for the common case where collaborators are rarely
   online at the same time, and if so, does that content ever transiently touch
   cloud-controlled storage?
5. **NAT traversal and relay approach.** Most consumer networks sit behind NAT.
   What's the concrete plan for direct connectivity (STUN-like hole punching,
   QUIC-based traversal, or something else), and what's the fallback relay's
   trust and cost model when it's the encrypted byte-relay in the architecture
   diagrams?
6. **Key recovery and device revocation.** If a device's private key is lost
   (reinstall, hardware failure), how does the user regain access to their
   projects and collaborations? How is a compromised or decommissioned device's
   identity revoked from a project's collaborator set?
7. **Trigger for commits.** Is committing always an explicit user action (as in
   the MVP), or does the long-term product need autosave-driven/background
   commits tied to DAW save events? This affects whether a filesystem watcher and
   daemon are required early or can stay deferred.
8. **DAW integration surface.** Beyond watching project files on disk, does the
   product need direct DAW/plugin integration (e.g. a DAW plugin that talks to the
   core directly), and if so, which DAWs are prioritized and what does that
   integration require from the FFI API?
9. **Protocol formalization and compatibility policy.** The sync protocol
   currently lives inside the Rust core's design. At what point does it need to
   become the separate, formally versioned `protocol` component described in
   [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#repository-components), and what's
   the compatibility policy between core versions once real users depend on sync?
10. **Threat model for P2P sync.** What happens when a peer sends malformed,
    oversized, or maliciously crafted objects during sync? What are the concrete
    resource limits (transfer size, session duration, object count) the sync
    engine must enforce to stay robust against a misbehaving or compromised peer?
11. **On-disk repository layout and OS conventions.** Where does the object store,
    config, and key material live on each platform (e.g. platform-appropriate
    application-data directories), and what happens when a project directory is
    moved, renamed, or opened from multiple accounts on the same machine?
12. **Multi-project and nested-repository behavior.** Can a single working
    directory contain more than one versioned project, or be nested inside
    another? Git has well-known sharp edges here; this needs an explicit decision
    rather than inheriting Git's behavior by default.
