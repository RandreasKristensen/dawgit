# Rust Core — Long-Term Requirements

## Purpose

This document captures the requirements for the Rust core that are already settled —
derived from the architecture in [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md) and
considered concrete, well thought out, or simply obvious given the product's premise.
It describes where the core is headed *after* [MVP.md](MVP.md). Anything not yet
decided is listed in [Open Questions](#open-questions) at the bottom, rather than
asserted here as a requirement — if it's in this list, it still needs a decision, a
discussion, or research before it can be built.

## Project format

- The core is built on **DAWproject**, the open MIT-licensed project format.
  DAWproject is not one supported format among several; it **is** the representation
  a repository is built out of, and it is the reason diff, merge, and meaningful
  history can exist at all. See
  [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#dawproject-is-the-repository-format).
- A session's `.dawproject` is the source of truth for its history. Every other file
  in the project directory — including the DAW's native project file — is tracked as
  an opaque blob: stored, versioned, and restored byte-for-byte, with no special
  semantics and no role in diff or merge. The core has one source of truth, not two.
- The archive is unpacked on ingest: `project.xml`, `metadata.xml`, and each media
  entry become separate blobs in the tree. The archive is never stored as a single
  blob.
- Entry contents are stored **decompressed**, so that identical audio deduplicates by
  content hash regardless of how any particular export compressed it.
- Checkout repacks the archive canonically. The guarantee is that every entry's
  content is byte-identical to what was committed; the ZIP container is regenerated,
  not preserved byte-for-byte. The repacked archive must be accepted by the DAWs the
  project targets.
- The object model and storage layer stay format-agnostic — they see blobs and trees,
  never DAW concepts. Format knowledge lives in one place and does not leak downward.

## Project mode: cross-DAW or single-DAW

Throughout this document, "DAW" is the unit of compatibility. The term *platform* is
reserved for the operating system, as in [Non-functional](#non-functional).

- Every repository declares a mode at initialization, and the mode is part of
  repository configuration:
  - **Cross-DAW.** The project restricts itself to constructs that travel between
    DAWs. It is a promise that a collaborator on a different DAW can open this
    session.
  - **Single-DAW.** The project is pinned to one named DAW and may use anything that
    DAW emits. It states plainly that other DAWs are not supported.
- The **cross-DAW subset** is: the generic DAWproject constructs — tracks, channels,
  clips, notes, audio, automation, and the generic built-in devices (EQ, Compressor,
  Gate, Limiter) — plus VST3 plugin state. Excluded are AU state (macOS-only, and not
  read by all target DAWs), CLAP state, legacy VST2, clip launcher data, and video
  tracks.
- The mode is **advisory, not enforcement.** The core cannot prevent a DAW from
  writing constructs outside the subset into its own export. What the mode governs is
  what the core promises, warns about, and relies on:
  - which constructs the linter flags,
  - which constructs diff interprets rather than treating as opaque,
  - which constructs merge is willing to combine,
  - what the project claims to its collaborators.
- When a cross-DAW project encounters constructs outside the subset, the core warns
  and stores them intact. It must never strip or rewrite them: silently destroying a
  user's plugin state to uphold a declared mode is worse than the mode being
  violated.
- The core identifies the authoring DAW from the `Application` element in
  `project.xml`, so mode violations are detected automatically rather than depending
  on the user to declare anything.
- Converting a project from cross-DAW to single-DAW widens what may be used but
  narrows who can open it, and is effectively irreversible once DAW-specific data
  enters history. It must be a deliberate, explicit operation rather than a
  configuration edit.

## Supporting a DAW

- A supported DAW is defined by: a detection rule matching its `Application` name; a
  declaration of which constructs it emits beyond the cross-DAW subset and which of
  those the core understands; diff semantics and merge classification for those
  constructs; and lint rules for what it emits that will not travel.
- Most DAW-specific data is opaque plugin state stored as separate archive entries.
  For those, "changed" or "unchanged" is the only honest diff, and they are never
  mergeable. Supporting a DAW is therefore mostly declaration, not parsing.
- What makes a DAW genuinely supported is not the code but the evidence: a round-trip
  experiment run against that DAW, and a corpus of real sessions from someone who
  uses it and would notice a subtle break on restore.
- Because that evidence requires a licence, real sessions, and a real user, **a DAW is
  added when a collaborator brings it, not because a roadmap lists it.** No DAW is
  supported speculatively.

## Support policy

- The core must document exactly which DAWproject constructs it understands. Being
  explicit about the boundary is a requirement, not a caveat.
- Constructs the core does not understand must be preserved verbatim through a commit
  and checkout, and excluded from diff and merge rather than guessed at.
- The core must be able to **lint a session** against its declared mode and report
  which of its features are unlikely to survive a round trip, so a user learns this
  before committing rather than after restoring. This is possible only because the
  format is open, and it is a central part of the engine's value over the format
  alone.
- Support is expected to grow as DAWproject and its implementations grow. Nothing in
  the design may assume today's gaps are permanent or work around them in ways that
  would have to be unwound later.

## Object model and storage

- Project content is represented with a content-addressed object model: blob (file
  contents), tree (directory structure), commit (project snapshot), and a reference
  manager for branches/HEAD/tags — mirroring Git's proven model.
- Objects are immutable and identified by a cryptographic hash of their content.
- A blob's identity is the hash of its **full logical content**. How the object store
  physically represents that content — whole, compressed, or as a list of chunks — is
  a private implementation detail behind the store's interface. This keeps
  deduplication and compression strategies internal changes rather than object-format
  or protocol breaks.
- The object store lives entirely on the local device; no service ever receives or
  persists object content.
- The core must expose a garbage collection path that removes objects no longer
  reachable from any reference. Because branching is a primary workflow and old
  branches are meant to be kept, GC is expected to reclaim very little in normal use
  — it exists for deleted branches and abandoned work, not as a growth strategy.
- A repository lock manager must protect the object store from concurrent,
  conflicting mutation (e.g. two processes committing at once).
- An object index is required for reasonable lookup performance once the object count
  is large.

## Branching and merge model

- Branching is a first-class, heavily used feature rather than an advanced escape
  hatch. Creating a branch from any commit must be cheap, and going back to an
  earlier point in history to continue working from there is a primary intended
  workflow — arguably the product's core value on its own, independent of any ability
  to recombine work afterwards.
Merge is planned in two stages. Stage one ships without it entirely; stage two aims
at general merge rather than a permanently restricted subset.

### Stage one — branches only

- **No merge of any kind.** Branching is the whole collaboration model. History along
  every branch is linear.
- Divergence is resolved by choosing a branch to continue from, never by combining
  two. Nothing is silently discarded: the branch not chosen remains in full.
- The commit object must nevertheless permit more than one parent, so stage two
  requires no object-format migration.

### Stage two — merge

- The goal is **general merge**, not a fixed subset. The format is open and
  structured, which is the entire reason attempting it is reasonable; the product
  should get as close to full merge as the format's structure allows rather than
  designing a ceiling in from the start.
- Strictly additive merges — two branches each adding material neither of the other
  touched, such as a guitar track and a vocal take — are the natural first increment,
  because they need no conflict resolution at all.
- Merges operate on the parsed `project.xml`, not on raw bytes. This is what the
  format choice buys.
- Expected order of difficulty, as an expectation rather than a commitment: timeline
  and track structure first, then clip arrangement, then automation curves, which need
  either curve-level merging or an explicit human choice.
- **A permanent ceiling: plugin state cannot be merged.** It is an opaque binary
  preset stored as its own archive entry. Two branches that both adjusted the same
  plugin can only be resolved by choosing one. This is structural, not a matter of
  effort, and no amount of openness in the surrounding format changes it. The same
  applies to opaque files tracked alongside the session.
- **A prerequisite that must be measured first: stable element identity across
  exports.** Merging two structured documents requires knowing which elements
  correspond. If a DAW regenerates element ids on every export, two exports of an
  unchanged session appear entirely different, and general merge is not possible —
  diff is badly degraded too. See
  [MVP.md](MVP.md#step-zero-the-round-trip-experiment).
- Anticipated interface work, to be built when the capability exists and the product
  deems it a priority: a merge editor for simple parameter-level differences (e.g.
  track volumes), and a diff editor for edits that trim or cut existing material
  (removing breaths, tightening the start or end of a take).

## Diff and history

- The core must be able to produce a structured diff between any two commits by
  comparing their parsed `project.xml` — added, removed, and modified tracks, clips,
  and automation — rather than reporting only "the project file changed".
- Diff output must be usable both by a human reading history and, in stage two, by
  the merge path deciding what can be combined.
- History listing must work without parsing anything: commit metadata alone.

## Working tree

- The core must be able to scan a project directory and build a manifest of its
  current state.
- The core must be able to compare the working tree manifest against the last
  committed tree to report status (changed/added/removed files).
- The core must be able to materialize (checkout) any historical commit back onto the
  filesystem, reproducing every archive entry and every opaque file byte-for-byte.
- The core must warn when a session's `.dawproject` is older than the DAW's own
  project file beside it, since that means the commit would capture stale work. A
  silently outdated export is the central failure mode of the whole workflow.
- A filesystem watcher is a reasonable future addition for detecting changes without
  polling, feeding the same manifest the scanner produces.

## Synchronization engine

- Synchronization is peer-to-peer: two Rust cores exchange only the objects one is
  missing relative to a target commit, verified by content hash before being stored,
  matching the sequence in
  [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#p2p-synchronization).
- A sync session requires: peer identity/authentication, inventory negotiation (what
  does each side already have), object transfer, and integrity verification of every
  received object before it is committed to local storage.
- Because the export is unpacked into per-entry blobs, sync granularity is naturally
  per-file: a peer that already holds the session's audio receives only the changed
  timeline.
- No service is ever a party to the object transfer itself or persists transferred
  content.
- Reference updates (moving a branch/HEAD forward) are only applied after the
  referenced commit and its full object closure have been verified locally.

## Cryptography and identity

- Each device holds its own identity keypair, stored in an OS-protected key store,
  never transmitted off the device.
- Peer-to-peer sessions must be mutually authenticated and encrypted end-to-end.
- Commits and other trust-sensitive metadata should be signable with the device
  identity to support future provenance/verification needs.

## Networking and transport

- A plain TCP transport between directly addressed peers is sufficient for the first
  networked version and does not require discovery, NAT traversal, or relay
  infrastructure to exist yet.
- Transport-level security (TLS or equivalent) and authenticated encryption of
  payloads are required before any real network sync ships, regardless of transport
  choice.
- QUIC, NAT traversal, and an encrypted relay fallback are acknowledged future needs
  for making P2P sync work across ordinary consumer networks, but are not required
  for the first networked milestone.

## Interfaces

- The core is an embeddable Rust library with a CLI on top. The CLI is the primary
  interface and the only one the MVP needs.
- A C-compatible FFI surface is a later addition, added when a concrete consumer
  needs it. If it is added, it must be stable and versioned independently of internal
  Rust module structure.
- A local daemon is a possible future addition for long-running services (watching
  the filesystem, holding a sync session open), not a current requirement.
- The dependency direction is fixed: interface layer → application services → format
  adapters → object model/storage and synchronization services →
  transport/cryptography. Higher layers may depend on lower layers; the reverse is
  not allowed. In particular, the object model must not depend on any format adapter.

## Non-functional

- The core is cross-platform (Windows, macOS, Linux).
- The core owns project content exclusively; no other component is a source of truth
  for file contents or version history.
- The core must be usable as a library embedded in a host process as well as a
  standalone binary — it should not assume it owns the process it runs in.

## Open questions

These are the things this document deliberately does **not** answer yet. Each one
needs a decision, a discussion, or research before the corresponding part of the core
can be built with confidence.

1. **Triggering and automating the export.** DAWproject is written by an explicit
   menu action (in Studio One, `File > Convert To > DAWproject File…`, Professional
   edition only), and the DAWs involved offer no scripting hook to automate it. So
   every commit depends on the user remembering a manual step. Does the core simply
   detect and warn about staleness, drive the export some other way, or accept that
   commits are export-gated? This is the biggest usability risk in the whole design.
2. **Whether opaque files are worth tracking at all.** The native project file is
   currently tracked as an opaque blob, which is cheap for a Studio One `.song` but
   expensive for DAWs whose native format embeds all audio in one monolithic file.
   If the same-DAW round trip proves faithful, tracking it may be unnecessary
   entirely; if not, some native formats may be too large to store whole. Which
   opaque files are worth keeping, and does the answer differ per DAW?
3. **Content-defined chunking and compression.** Unpacking the archive removes most
   of the pressure here, since audio deduplicates and only small XML changes per
   commit. Is any chunking or packfile layer needed at all for realistic sessions, or
   does raw per-object storage suffice? The MVP's measured growth (see
   [MVP.md](MVP.md#success-criteria)) is the evidence.
4. **Canonical repack fidelity.** A repacked `.dawproject` is byte-identical per
   entry but not as a container. Do the target DAWs accept a regenerated archive in
   all cases — entry ordering, compression method, directory layout — and what is the
   canonical form the core writes?
5. **DAWproject schema evolution.** The format is young and will change. How does the
   core handle sessions written against a newer schema than it understands, and what
   is the policy for parsing versus passing through elements it does not recognize?
   Getting this right is what lets the project inherit the format's growth for free
   rather than needing a release for every spec change.
6. **Whether mode can vary within a repository.** Mode is currently a property of
   the whole repository. Does a branch-heavy workflow want a single-DAW branch off a
   cross-DAW trunk — a Studio One branch that uses everything Studio One offers,
   while the trunk stays portable — and if so, what happens when such a branch is
   the one a collaborator wants to build on?
7. **Offline/async sync model.** The sync sequence assumes both peers are online
   simultaneously. Does the product need an async path (push to a staging point, pull
   later) for the common case where collaborators are rarely online at the same time,
   and if so, does that content ever transiently touch third-party storage?
8. **NAT traversal and relay approach.** Most consumer networks sit behind NAT.
   What's the concrete plan for direct connectivity (STUN-like hole punching,
   QUIC-based traversal, or something else), and what's the fallback relay's trust
   and cost model?
9. **Key recovery and device revocation.** If a device's private key is lost
   (reinstall, hardware failure), how does the user regain access to their projects
   and collaborations? How is a compromised or decommissioned device's identity
   revoked from a project's collaborator set?
10. **Protocol formalization and compatibility policy.** The sync protocol currently
    lives inside the core's design. At what point does it become the separate,
    formally versioned `protocol` component described in
    [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#components), and what's the
    compatibility policy between core versions once real users depend on sync?
11. **Threat model for P2P sync.** What happens when a peer sends malformed,
    oversized, or maliciously crafted objects — or a `project.xml` designed to attack
    the parser? What concrete resource limits (transfer size, session duration,
    object count, parse depth) must the sync engine enforce?
12. **On-disk repository layout and OS conventions.** Where do the object store,
    config, and key material live on each platform, and what happens when a project
    directory is moved, renamed, or opened from multiple accounts on the same
    machine?
13. **Multi-project and nested-repository behavior.** Can a single working directory
    contain more than one versioned project, or be nested inside another? Git has
    well-known sharp edges here; this needs an explicit decision rather than
    inheriting Git's behavior by default.
