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

## Element correspondence

Diff and merge both reduce to one question: **given an element in commit A, which
element in commit B is the same element?** DAWproject does not answer this uniformly,
so the core answers it with a ladder of strategies and records which one was used.

| Tier | Strategy | Applies to | Confidence |
| --- | --- | --- | --- |
| 1 | Element `id` | Tracks, channels, devices, sends, scenes, timelines, automation lanes | Exact, when ids persist |
| 2 | Content key — media path + `playStart`/`playStop` | Audio clips | Exact when keys are unique |
| 3 | Assignment over a colliding key group, minimising displacement | Repeated audio clips | Inferred |
| 4 | Name + position | Tracks with unstable ids, MIDI clips, structure | Inferred |
| 5 | Opaque — changed or unchanged only | Plugin state, unrecognised constructs | None |

### Why it is a ladder and not an assumption

Three facts from
[`Project.xsd`](https://github.com/bitwig/dawproject/blob/main/Project.xsd) fix this
shape, and none of them is a matter of implementation quality:

- **Clips carry no `id`.** The `clip` type extends `nameable`; `id` is declared on
  `referenceable`. This is true in every DAW and cannot change without a schema
  revision. Tier 2 is not a fallback for the clip layer — it is the only thing the
  format permits.
- **Tracks, channels, devices, sends and timelines do carry `id`**, including the
  `Audio` element nested inside a clip and the `Points` container that holds an
  automation lane. Tier 1 is available for these *if* a DAW's exporter keeps them
  stable, which is what the format test measures.
- **Leaf data carries no identity at all.** The `point` and `note` types have no `id`
  and no `name` — only `time`, and `value`/pitch. For these, content *is* identity:
  two points with the same time and value are the same point in any meaningful sense,
  so matching them by value is correct rather than a degradation.

### Requirements

- The core must attempt correspondence in tier order and stop at the first tier that
  resolves an element unambiguously.
- **Every match must record the tier that produced it**, and that tier must be
  available to anything consuming the diff — a human reading history, and the merge
  path deciding what it is willing to combine.
- **The core must never present an inferred match as an exact one.** Where tiers 3 or
  4 cannot resolve an element confidently, reporting "changed, cannot attribute" is
  required; guessing silently is not permitted. A diff that confidently misattributes
  a change is worse than one that admits uncertainty, because it destroys the user's
  reason to trust any of it.
- Which tiers are available is a **measured property of a DAW's exporter**, not a
  constant. It is established by the format test and recorded per supported DAW, in
  the same way the rest of [supporting a DAW](#supporting-a-daw) is evidence-driven.
- Tier 3 must be a global assignment over a colliding key group — minimising total
  displacement — rather than greedy nearest-position matching, which produces
  order-dependent results on the exact case it exists to handle.
- Merge may rely on tiers 1 and 2. **Merge must not rely on tiers 3 and 4 without an
  explicit human confirmation**, because an inferred correspondence that is wrong
  silently combines the wrong material.

### Prior art

Establishing correspondence between timelines with no shared identity is a solved
commercial problem in audio post-production, where a picture editor's changes must be
re-synced into a sound editor's session. **Conformalizer** (Emmy Award-winning),
**Matchbox** (The Cargo Cult, supported in Pro Tools 2025.6) and
**[Vordio](https://vordio.net/reconform/)** all do this, classifying every clip as
moved, edge-edited, added, deleted or split. Study them before deriving anything.

Two caveats on transferring the technique. Those tools serve a domain where nearly
every element is a clip referencing external media, so their natural key is nearly
always unique; music production violates that constantly, which is the entire reason
tier 3 exists here. And Matchbox has moved toward matching on picture content rather
than declared metadata — the analogue here is matching on audio content hashes, which
the content-addressed object store already provides for free and which should be
preferred over declared paths wherever the two disagree.

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
- **A prerequisite that must be measured first: which correspondence tiers this DAW's
  exports support.** Merging two structured documents requires knowing which elements
  correspond, and [Element correspondence](#element-correspondence) describes how the
  core establishes that. Merge may rely on tiers 1 and 2; it may not rely on tiers 3
  and 4 without explicit human confirmation. If a DAW regenerates ids on every export,
  tier 1 is lost and merge is restricted to what content keys can resolve — a real
  constraint, but not the end of merge, since the clip layer never had ids to lose.
  See [MVP.md](MVP.md#step-zero-the-round-trip-experiment).
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
- Diff must distinguish **moved** from **removed and re-added**, which is the whole
  reason [element correspondence](#element-correspondence) exists, and must carry the
  correspondence tier through to its output so the reader knows which lines are exact
  and which are inferred.
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

They are ordered by **when the answer is needed**, not by how interesting they are. A
question in a later band is not less important — it is less urgent, and working on it
now would be working ahead of the evidence.

| Band | Meaning |
| --- | --- |
| **P0** | Blocks the next action, or gets more expensive the longer it waits |
| **P1** | Blocks the MVP |
| **P2** | Blocks the first networked milestone |
| **P3** | Blocks calling this a product |

### P0 — decide now

1. **What is the upstream ask, and who owns it?** The step after the format test is a
   conversation with Bitwig, not more code — see
   [MVP.md](MVP.md#after-the-test--upstream). The cheap ask is a stability guarantee
   on ids that already exist; the expensive one is a scriptable export hook. What
   exactly is being asked for, backed by which measurements, and does it arrive as a
   pull request or as measured evidence on
   [issue #40](https://github.com/bitwig/dawproject/issues/40)? The format is still
   being extended — lyrics, chords and video are on its roadmap — so this window is
   open now and will not stay open.

2. **Does the licence match the goal?** The core is GPL-3.0 while DAWproject itself is
   MIT. GPL-3.0 on an embeddable library with a planned C FFI forecloses the outcome
   this project would most want: a DAW vendor or the format's authors adopting the
   engine. If the goal is a hosted coordination service, AGPL is the coherent choice;
   if the goal is to become infrastructure, a permissive licence is. The current
   licence fits neither. Relicensing costs one commit today and unanimous consent from
   every contributor later — this is the cheapest it will ever be to fix.

3. **Under what evidence would the DAWproject bet be revisited?** The bet is
   deliberate and settled — see
   [ARCHITECTURE.md](../.docs/ARCHITECTURE.md#why-dawproject-and-not-a-native-format).
   Recording the conditions that would reopen it is what keeps it a decision rather
   than an attachment. Candidate triggers: the format test lands on
   [what would actually be fatal](../.docs/DAWproject-format-test/README.md#what-would-actually-be-fatal);
   no DAW gains a scriptable export within a defined window; or format adoption
   stalls.

### P1 — blocks the MVP

4. **Triggering and automating the export.** DAWproject is written by an explicit menu
   action, and the DAWs involved offer no documented scripting hook, so every commit
   depends on the user remembering a manual step. This remains the biggest usability
   risk in the whole design. Precedent says it need not be permanent — Avid shipped a
   Pro Tools Scripting SDK covering session open, save and export in 2022.12, and
   Bitwig publishes a documented controller API — so the question is whether the core
   detects and warns about staleness, drives the export some other way, or accepts
   that commits are export-gated until a vendor opens the door.
   **Cheapest next probe:** does Bitwig's controller API already expose the DAWproject
   export action? If it does, this is solved on one DAW today.

5. **How does tier 3 disambiguate colliding keys?** A loop dropped at sixteen
   positions produces sixteen identical `(path, playStart, playStop)` keys, and only
   position separates them — which is exactly what an edit changes. Global assignment
   minimising total displacement is the stated requirement, but what is the cost
   function, what happens when a clip is both moved *and* edge-edited, and what is the
   confidence threshold below which the core refuses to attribute rather than
   guessing?

6. **How are MIDI clips matched?** They carry no `id` and no media key, so they fall
   straight to tier 4, name and position. In a MIDI-heavy session that is most of the
   arrangement. Is name-and-position good enough, or does the core need to match on
   note content — and if the latter, how much can a clip's notes change before it
   stops being the same clip?

7. **How is tier surfaced to the user?** Every match records the tier that produced
   it, but a CLI diff annotating every line with a confidence level is unreadable.
   What is the actual presentation — a summary line, a flag on uncertain matches only,
   an `--explain` mode?

8. **Canonical repack fidelity.** A repacked `.dawproject` is byte-identical per entry
   but not as a container. Do the target DAWs accept a regenerated archive in all
   cases — entry ordering, compression method, directory layout — and what is the
   canonical form the core writes?

9. **Whether opaque files are worth tracking at all.** The native project file is
   currently tracked as an opaque blob, which is cheap for a Fender Studio Pro `.song` but
   expensive for DAWs whose native format embeds all audio in one monolithic file. If
   the same-DAW round trip proves faithful, tracking it may be unnecessary entirely;
   if not, some native formats may be too large to store whole. Which opaque files are
   worth keeping, and does the answer differ per DAW?

10. **On-disk repository layout and OS conventions.** Where do the object store,
    config, and key material live on each platform, and what happens when a project
    directory is moved, renamed, or opened from multiple accounts on the same machine?

11. **Multi-project and nested-repository behavior.** Can a single working directory
    contain more than one versioned project, or be nested inside another? Git has
    well-known sharp edges here; this needs an explicit decision rather than
    inheriting Git's behavior by default.

### P2 — blocks the first networked milestone

12. **Content-defined chunking and compression.** Unpacking the archive removes most
    of the pressure here, since audio deduplicates and only small XML changes land per
    commit. Is any chunking or packfile layer needed at all for realistic sessions, or
    does raw per-object storage suffice? The MVP's measured growth (see
    [MVP.md](MVP.md#success-criteria)) is the evidence.

13. **DAWproject schema evolution.** The format is young and will change. How does the
    core handle sessions written against a newer schema than it understands, and what
    is the policy for parsing versus passing through elements it does not recognize?
    Getting this right is what lets the project inherit the format's growth for free
    rather than needing a release for every spec change.

14. **Offline/async sync model.** The sync sequence assumes both peers are online
    simultaneously. Does the product need an async path — push to a staging point,
    pull later — for the common case where collaborators are rarely online at the same
    time, and if so, does that content ever transiently touch third-party storage?

15. **NAT traversal and relay approach.** Most consumer networks sit behind NAT.
    What's the concrete plan for direct connectivity (STUN-like hole punching,
    QUIC-based traversal, or something else), and what's the fallback relay's trust
    and cost model? A relay implies a server, which is in tension with "we host the
    collaboration, you own the files" — that tension needs stating plainly either way.

16. **Key recovery and device revocation.** If a device's private key is lost
    (reinstall, hardware failure), how does the user regain access to their projects
    and collaborations? How is a compromised or decommissioned device's identity
    revoked from a project's collaborator set?

17. **Threat model for P2P sync.** What happens when a peer sends malformed,
    oversized, or maliciously crafted objects — or a `project.xml` designed to attack
    the parser? What concrete resource limits (transfer size, session duration, object
    count, parse depth) must the sync engine enforce?

### P3 — blocks calling this a product

18. **Why does this survive where Splice Studio did not?** Splice shut down its Studio
    collaboration platform in 2023, its CEO noting that users "have many great
    alternatives for file sharing". That is the strongest available evidence that
    producers do not experience this as a problem worth changing tools for. The thesis
    here is different — structured diff on an open format, rather than file sync — but
    the demand question is unanswered, and no amount of engineering answers it.

19. **Whether mode can vary within a repository.** Mode is currently a property of the
    whole repository. Does a branch-heavy workflow want a single-DAW branch off a
    cross-DAW trunk — a Fender Studio Pro branch that uses everything Fender Studio Pro offers,
    while the trunk stays portable — and if so, what happens when such a branch is the
    one a collaborator wants to build on?

20. **Protocol formalization and compatibility policy.** The sync protocol currently
    lives inside the core's design. At what point does it become the separate,
    formally versioned `protocol` component described in
    [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#components), and what's the
    compatibility policy between core versions once real users depend on sync?
