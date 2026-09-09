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

A naming note, since it will otherwise cause confusion: **PreSonus Studio One Pro was
rebranded Fender Studio Pro in January 2026.** These documents say "Studio One"
throughout, because that is what the versions carrying DAWproject support are called
and what the trial user has installed. It is the same product and the same development
team.

## Step zero: the round-trip experiment

Before any code, run the measurement the whole design rests on, because nobody has
published it: **export a real session to `.dawproject`, import it back into the same
DAW, and compare.** Then re-export the imported version and diff the two
`project.xml` files against each other.

Every documented DAWproject fidelity gap is a gap between two *different* DAWs. None
of them necessarily applies to a session that leaves and returns to the same one.
This is an afternoon's work, and the full protocol is in
[`.docs/DAWproject-format-test/`](../.docs/DAWproject-format-test/README.md) — run
**Waveform Free first**, because it costs nothing and no licence.

It decides four things:

- Whether the DAW's native project file needs tracking at all, or whether the
  `.dawproject` alone is a complete record of the session.
- Whether audio inside the archive is byte-identical to the audio in the session
  folder, which decides whether content addressing deduplicates it for free or stores
  it twice.
- **Whether element ids are stable across exports** — which decides whether tier 1 of
  the [correspondence ladder](Requirements.md#element-correspondence) is available for
  tracks, channels and devices.
- **Whether clip content keys are usable, and how often they collide** — which decides
  whether tier 2 carries the clip layer or tier 3 has to be built.

### This produces a tier, not a verdict

An earlier version of this document treated stable ids as the thing the design lived
or died by. That was wrong on a point of fact, and the correction matters enough to
state plainly: in
[`Project.xsd`](https://github.com/bitwig/dawproject/blob/main/Project.xsd) the `clip`
type extends `nameable`, while `id` is declared on `referenceable`. **Clips have no
ids in any DAW.** The clip layer was never going to be identified by id, so an id
failure cannot take away something the format never offered.

What identifies clips instead is a content key — media path plus in/out points — which
is the same technique commercial reconform tools have used in audio post for over a
decade. So the experiment's job is to say *which tier each class of element lands on*,
and everything downstream is written against tiers rather than against a single
assumption.

Record the answer in the results tables. The scope below assumes tier 1 for tracks and
tier 2 or 3 for clips; if the measurement is worse, the
[open questions](Requirements.md#open-questions) say what changes.

## After the test — upstream

The step after the measurement is **not code. It is Bitwig.**

The evidence from step zero is the only thing that makes an upstream conversation
worth anyone's time, and there is a specific reason to have it. The format is young
and still being extended — lyrics, chords and video are on its roadmap — so this is
the window in which a small, cheap guarantee could still be added. Once implementations
harden, it closes.

The approach is fixed by what the upstream repository actually responds to:

- [Issue #40](https://github.com/bitwig/dawproject/issues/40) has asked for exactly
  this guarantee since January 2023 and has **no maintainer response**.
- The same repository has merged outside contributors' pull requests steadily from
  2021 through 2024 — six of them from the author of ProjectConverter alone.

**The repository responds to artifacts, not to requests.** So the deliverable is a
reproducible harness plus measured per-DAW results, not a well-argued comment.

Sequence:

1. Run the test. Publish the results, pass or fail.
2. Make [`compare.py`](../.docs/DAWproject-format-test/compare.py) runnable
   standalone against anyone's exports, so a maintainer can reproduce it on their own
   build.
3. Take the **cheap ask** first: a stability guarantee on ids that already exist. That
   is a constraint on an existing code path, not a feature — no UI, no docs, no
   support cost — and it benefits every consumer of the format. The expensive ask
   (a scriptable export hook, see
   [open question 1](Requirements.md#open-questions)) is the follow-on that gets
   earned, not the opener.
4. Target **Bitwig, not Studio One.** Bitwig co-authored the format, publishes a
   documented controller API, and demonstrably merges outsiders' code. Studio One's
   scripting engine exists but has never been exposed publicly, and its vendor has
   shown no interest in exposing it. Studio One is the trial *user*; Bitwig is the
   standards *partner*. Those are different relationships and only one of them is
   currently reachable.

There is one cheap check worth doing in the same week as the test, because it could
retire the biggest usability risk in the design outright: **does Bitwig's controller
API expose the DAWproject export action?** If it does, automated commits are already
possible on at least one DAW today. Bitwig's API reference is in-app under
Help > Documentation > Developer Resources.

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
- **Correspondence by tier.** Diff matches elements using the ladder in
  [Requirements.md](Requirements.md#element-correspondence), starting at the highest
  tier the format test showed to be available. The MVP must implement tiers 1, 2 and
  4; **tier 3 is required only if the test shows keys colliding**, which for any
  session with repeated material it will. Every match records which tier produced it,
  because that is what tells a user how much to trust a line of the diff.
- **Checkout / restore.** Materialize any commit back onto disk: the archive
  repacked canonically with every entry's content byte-identical, and every opaque
  file restored byte-for-byte.
- **History listing.** Commits in order with message and timestamp.
- **CLI-only interface.** One binary. No daemon, no FFI, no file watcher — commits
  are explicit and user-triggered.

Suggested command surface:

```
dawgit init                    # start versioning the current directory
dawgit status                  # what changed since the last commit
dawgit commit -m "<message>"   # snapshot the current session
dawgit log                     # list commit history
dawgit diff <commit> <commit>  # structured comparison of two versions
dawgit branch <name>           # create a branch at the current commit
dawgit switch <name|commit>    # move to a branch or an earlier commit
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

- `dawgit init` on a real Studio One session directory succeeds and starts tracking it.
- Editing the song in Studio One, re-exporting the `.dawproject`, and running
  `dawgit commit` produces a new commit; checking it out restores a session that opens
  normally in Studio One.
- The repacked `.dawproject` from a checkout imports successfully into Studio One,
  **and** into at least one other DAW that supports the format. This is what makes
  "cross-DAW" a tested claim rather than an assertion; if it doesn't hold, the
  premise is wrong.
- `dawgit diff` across a commit that added a guitar track names that track. Across a
  commit that changed a mix, it says something a human recognizes as what they did.
- `dawgit diff` across a commit that **moved one instance of a repeated loop** reports
  that one clip moved — not that every instance of the loop changed. This is the
  narrowest test of whether tier 3 works, and it is the case the content-key technique
  is weakest at.
- Every diff line states the tier its match came from, and a diff the core cannot
  resolve says so rather than guessing silently.
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
- **That inferred correspondence is trustworthy enough to show a user.** Tiers 3 and
  4 guess. A diff that confidently reports the wrong clip as moved is worse than one
  that says it cannot tell, so the MVP has to surface tier alongside every match and
  find out whether people accept the uncertainty or stop believing the tool.

## Non-goals

Performance at scale, large sample library handling, and packaging for distribution
are deferred. The MVP needs to work correctly, once, on a real session — it does not
need to be fast, small, or installable by anyone but the people running the trial.
