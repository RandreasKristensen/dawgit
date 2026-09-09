# DAWgit

Version control for music production projects, built on the open
[DAWproject](https://github.com/bitwig/dawproject) interchange format.

> We host the collaboration. You own the files.

Proprietary DAW formats are binary and opaque, which is why versioning music has
never worked properly — content addressing solves storage without solving diff or
merge. DAWproject is XML plus media in a ZIP container, supported today by Studio
One, Bitwig Studio, Cubase, Cubasis, VST Live and n-Track.

This project builds *directly on* that format rather than treating it as one option
among many. The format is young and its implementations are uneven; the bet is that
being aligned with where it is going means capability arrives here as the format
grows. What is supported is documented explicitly rather than papered over.

## Current scope

This repository contains one component: [`core`](core/README.md), the Rust versioning
engine. There is no UI and no backend here — see
[`.docs/ARCHITECTURE.md`](.docs/ARCHITECTURE.md) for the full design.

- [`core/MVP.md`](core/MVP.md) — the local, single-user, CLI-only slice being built
  first, and the experiment it is designed to run.
- [`core/Requirements.md`](core/Requirements.md) — settled long-term requirements,
  and the open questions that still need deciding, ordered by when the answer is
  needed.
- [`.docs/ARCHITECTURE.md`](.docs/ARCHITECTURE.md) — architecture and diagrams,
  starting with why DAWproject is the repository format and what follows from it.
- [`.docs/DAWproject-format-test/`](.docs/DAWproject-format-test/README.md) — the
  measurement everything else is waiting on.

## What happens next

In order, and none of it is Rust yet:

1. **Run the format test.** Waveform Free first — no licence, no cost. It measures
   whether a session survives a same-DAW round trip, and which
   [correspondence tier](core/Requirements.md#element-correspondence) each class of
   element lands on.
2. **Take the result to Bitwig.** The format is young and still growing, and the
   upstream repository responds to measured artifacts rather than feature requests.
   See [`core/MVP.md`](core/MVP.md#after-the-test--upstream).
3. **Then build the MVP**, against whatever the measurement actually showed.

## Build

There is not yet a buildable application in this checkout.
[`core/README.md`](core/README.md) describes the expected Rust build commands once a
`Cargo.toml` and source exist.
