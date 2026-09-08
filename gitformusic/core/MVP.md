# Rust Core — MVP

## Purpose

Answer the question the whole platform now rests on: **does building on DAWproject
actually deliver a useful version history for a real session?** Concretely — can a
Studio One song be committed, branched, returned to, and diffed in a way that tells
you something a folder of dated copies wouldn't, and can it come back out of the
repository intact?

This MVP is a local-only, single-user command-line tool. Everything runs on one
machine, offline. No sync, no coordination service, no UI, no cryptographic identity
beyond content hashing. See [Requirements.md](Requirements.md) for what comes after,
and the [architecture reference](../.docs/ARCHITECTURE.md) for how this fits.

The trial case is real and specific: a producer working in Studio One Professional,
and a second person on the other end of the repository.

## Step zero: the round-trip experiment

Before any code, run the measurement the whole design rests on, because nobody has
published it: **export a real Studio One session to `.dawproject`, import it back
into Studio One, and compare.** Then re-export the imported version and diff the two
`project.xml` files against each other.

Every documented DAWproject fidelity gap is a gap between two *different* DAWs. None
of them necessarily applies to a session that leaves and returns to the same one.
This is an afternoon's work and it decides three things:

- Whether the DAW's native project file needs tracking at all, or whether the
  `.dawproject` alone is a complete record of the session.
- Whether audio inside the archive is byte-identical to the audio in the session
  folder, which decides whether content addressing deduplicates it for free or stores
  it twice.
- **Whether element ids are stable across exports.** Export an unchanged session
  twice and diff the two `project.xml` files. If ids are regenerated each time, an
  unmodified session looks completely rewritten — which degrades diff badly and makes
  the general merge of
  [stage two](Requirements.md#stage-two--merge) impossible. This is the single most
  consequential thing the experiment measures.

Record the answer. Everything below assumes the round trip is good enough to build
on; if it isn't, the opaque files stay and the scope grows.

## In scope

- **Repository initialization.** Turn a directory containing a session — its
  `.dawproject` plus whatever else the DAW put there — into a versioned repository,
  in place. Repositories are **cross-DAW only** in the MVP: the core relies on the
  cross-DAW subset defined in
  [Requirements.md](Requirements.md#project-mode-cross-daw-or-single-daw), and no
  single-DAW mode exists yet.
- **DAWproject ingest.** Unpack the archive and store `project.xml`, `metadata.xml`,
  and each media entry as separate blobs, decompressed, as described in
  [`ARCHITECTURE.md`](../.docs/ARCHITECTURE.md#dawproject-is-the-repository-format).
  Every other file in the directory is stored whole as an opaque blob.
- **Content-addressed object store.** Immutable blobs on local disk, addressed by a
  cryptographic hash of their content.
- **Tree and commit objects.** A directory snapshot as a tree of blobs and subtrees;
  a commit referencing a root tree.
- **Branching.** Named references, creating a branch from any commit, and switching
  between them. This is the product's core value proposition, so the MVP has to prove
  it feels good, not just that it's possible. This is stage one of the
  [two-stage merge plan](Requirements.md#branching-and-merge-model): branches only,
  no merge of any kind.
- **Working tree status.** Report which tracked files changed since the last commit,
  including a warning when the `.dawproject` is older than the DAW's own project file
  beside it — meaning a commit would capture stale work.
- **Structured diff.** Compare two commits by parsing `project.xml` and reporting
  added, removed, and modified tracks and clips — not just "the project changed".
  This is the thesis of the whole format bet and the most important thing to
  validate.
- **Checkout / restore.** Materialize any commit back onto disk: the archive
  repacked canonically with every entry's content byte-identical, and every opaque
  file restored byte-for-byte.
- **History listing.** Commits in order with message and timestamp.
- **CLI-only interface.** One binary. No daemon, no FFI, no file watcher — commits
  are explicit and user-triggered.

Suggested command surface:

```
gfm init                    # start versioning the current directory
gfm status                  # what changed since the last commit
gfm commit -m "<message>"   # snapshot the current session
gfm log                     # list commit history
gfm diff <commit> <commit>  # structured comparison of two versions
gfm branch <name>           # create a branch at the current commit
gfm switch <name|commit>    # move to a branch or an earlier commit
```

## Out of scope for this MVP

- Networking, P2P sync, and any coordination service.
- Device identity, keypairs, signing, and encrypted transport.
- Merging of any kind. That is stage two, and it depends on the element-identity
  measurement above.
- Chunking, deduplication beyond whole-blob content addressing, and packfiles.
- Any UI, FFI surface, or embedding beyond the CLI binary.
- Any format handling beyond DAWproject; everything else is stored opaquely.
- Single-DAW mode, and any DAW-specific construct handling. Constructs outside the
  cross-DAW subset are stored intact but are not interpreted, diffed, or merged.
- The support linter described in [Requirements.md](Requirements.md#support-policy).
  The MVP reports what it observes; it does not yet check a session against the
  subset.
- Cross-platform packaging or installers.

## Success criteria

- `gfm init` on a real Studio One session directory succeeds and starts tracking it.
- Editing the song in Studio One, re-exporting the `.dawproject`, and running
  `gfm commit` produces a new commit; checking it out restores a session that opens
  normally in Studio One.
- The repacked `.dawproject` from a checkout imports successfully into Studio One,
  **and** into at least one other DAW that supports the format. This is what makes
  "cross-DAW" a tested claim rather than an assertion; if it doesn't hold, the
  premise is wrong.
- `gfm diff` across a commit that added a guitar track names that track. Across a
  commit that changed a mix, it says something a human recognizes as what they did.
- Measured on-disk growth per commit is recorded. The prediction is that growth is
  roughly the size of the `project.xml` delta, with audio stored once — if measurement
  contradicts that, the storage questions in
  [Requirements.md](Requirements.md#open-questions) move up in priority.
- Branching from a commit several steps back and continuing work from there is
  possible and produces an openable session.

## What this MVP is trying to disprove

Stated plainly, so the experiment is honest:

- **That the export step is tolerable.** Every commit depends on the user manually
  re-exporting. If that friction makes the tool unusable in practice, the design
  needs rethinking before anything else gets built.
- **That a repacked archive is accepted.** If DAWs reject a canonically regenerated
  ZIP, checkout has to preserve containers byte-for-byte and some of the storage
  benefit disappears.
- **That the diff is legible.** A structurally correct diff nobody can read is not
  worth the format bet.
- **That the same-DAW round trip holds.** Step zero answers this before anything is
  built. If a session cannot survive leaving and returning to its own DAW, the format
  is not yet ready to be a repository format, and the opaque files carry the weight
  until it is.

## Non-goals

Performance at scale, large sample library handling, and packaging for distribution
are deferred. The MVP needs to work correctly, once, on a real session — it does not
need to be fast, small, or installable by anyone but the people running the trial.
