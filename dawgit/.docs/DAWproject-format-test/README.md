# DAWproject Format Test

The measurement that [`MVP.md`](../../core/MVP.md#step-zero-the-round-trip-experiment)
calls step zero. It decides how DAWproject can carry version history, and which
correspondence strategy diff and
[stage-two merge](../../core/Requirements.md#stage-two--merge) have to be built on.

**This test does not produce a pass or a fail.** It produces a *tier* — see
[the correspondence ladder](#the-correspondence-ladder) below. An earlier framing
treated stable element ids as the single thing the design lived or died by. That was
wrong on a point of fact: DAWproject's schema does not give clips ids at all, and the
audio-post industry has been diffing timelines without ids for over a decade. So the
question is not "do ids survive" but "how far down the ladder does this DAW put us,
and what does that cost".

Nobody appears to have run this. [Issue #40 on the DAWproject
repository](https://github.com/bitwig/dawproject/issues/40) — "Version control for
.dawproject files", which asks for exactly the id persistence this test measures —
has been open since January 2023 with no maintainer response. The format is used for
one-way handoff, so no one has had a reason to export the same session twice and
compare.

The one substantive reply on that issue comes from the author of
[Vordio](https://vordio.net/reconform/), a commercial reconform tool, and it is the
reason this document has a ladder in it rather than a single question. See
[prior art](#prior-art-the-reconform-problem).

## The correspondence ladder

Diff and merge both reduce to one question: **given an element in commit A, which
element in commit B is the same element?** There is no single answer, so the core
uses a ladder of strategies and records which one produced a given match.

| Tier | Strategy | Applies to | Confidence |
| --- | --- | --- | --- |
| 1 | Element `id` | Tracks, channels, devices, sends, scenes, timelines | Exact, when ids persist |
| 2 | Content key — media path + `playStart`/`playStop` | Audio clips | Exact when keys are unique |
| 3 | Assignment over a colliding key group, minimising displacement | Repeated audio clips | Inferred |
| 4 | Name + position | Tracks with unstable ids, MIDI clips, structure | Inferred |
| 5 | Opaque — changed or unchanged only | Plugin state, unrecognised constructs | None |

Two schema facts fix the shape of this ladder, and neither is negotiable:

- In [`Project.xsd`](https://github.com/bitwig/dawproject/blob/main/Project.xsd), the
  `clip` type extends `nameable`; the `id` attribute is declared on `referenceable`.
  **Clips therefore carry no id in any DAW, by design.** Tier 2 is not a fallback for
  clips, it is the only thing the format permits. Tier 1 covers tracks, channels,
  devices and timelines — including the `Audio` element *inside* a clip — but never
  the clip itself.
- Tier 2's key is not unique in music production the way it is in audio post. A loop
  dropped at sixteen positions yields sixteen identical `(path, playStart, playStop)`
  keys. The key returns a *set*, and only position separates its members — which is
  exactly what an edit changes. That is what tier 3 is for, and
  [`compare.py`](compare.py) now measures how often it is needed.

What the test decides is which tiers this DAW's exports let the core reach, and how
much of a real session each tier covers.

### Prior art: the reconform problem

Establishing correspondence between two timelines with no shared identity is a solved
commercial problem in audio post-production, where the picture editor's changes must
be re-synced into a sound editor's session. Worth studying before deriving anything:

- **Conformalizer** — Emmy Award-winning; the original.
- **[Matchbox](https://www.thecargocult.nz/products/matchbox/)** (The Cargo Cult,
  2020) — the current standard, and
  [supported in Pro Tools 2025.6](https://www.avid.com/resource-center/matchbox). It
  carries automation and routing along with the timing changes, and has moved toward
  matching on picture content rather than declared metadata — the analogue here is
  matching on audio content hashes, which the object store provides for free.
- **[Vordio](https://vordio.net/reconform/)** — FCPXML/AAF into Reaper RPP; classifies
  every clip as moved, edge-edited, added, deleted or split.

These tools solve tiers 2–4 for a domain where nearly every element is a clip
referencing external media. Music sessions are more hostile: MIDI clips have no media
key at all, and repeated loops collide. The technique transfers; the assumption that
keys are unique does not.

**Results are per-DAW, not per-format.** What Waveform does says nothing about what
Studio One does. So the test runs three times:

| Run | Needs | Answers |
| --- | --- | --- |
| 1. [Waveform](#run-1--waveform-free-14) | Waveform Free 14, no licence | Which tier does *a* DAW put us on? |
| 2. [Studio One](#run-2--studio-one) | Studio One 6.5+ **Pro** | Does the DAW this project is actually aimed at? |
| 3. [Cross-DAW](#run-3--cross-daw) | both, ideally the same machine | Do the [cross-DAW subset](../../core/Requirements.md#project-mode-cross-daw-or-single-daw) assumptions hold? |

Run 1 first. It costs nothing, and if it fails there is no point borrowing a Studio
One licence yet.

## What is being measured

| | Question | Decides |
| --- | --- | --- |
| 1 | Does a session survive export and re-import into the same DAW? | Whether the DAW's native project file must also be tracked |
| 2 | Is audio byte-identical across exports, at stable paths? | Whether audio deduplicates for free, and how noisy diffs are |
| 3 | Do element ids survive an edit elsewhere in the project? | Whether **tier 1** is available for tracks, channels and devices |
| 4 | Does the cross-DAW subset survive a transfer between two DAWs? | Whether cross-DAW mode is a real mode or a fiction |
| 5 | Are clip content keys stable, and how often do they collide? | Whether **tier 2** carries the clip layer, or **tier 3** is mandatory |

Question 3 is the one with a trap in it. Two exports of an *unchanged* session prove
only that the exporter is **deterministic**. If ids are assigned by walking the
project in order, an unchanged session exports identically every time while ids are
really *positional* — and the moment a track is inserted above another, everything
below it renumbers and every future diff shows the whole arrangement rewritten. That
is why file **C** inserts its new track at the **top**, not the bottom.

Question 5 is new, and it is the one that keeps a bad answer to question 3 from being
fatal. Even if ids churn completely, the clip layer may still be identifiable by
`(media path, playStart, playStop)` — and the clip layer is most of what a musician
recognises in a diff. `compare.py` reports, per session: how many clips carry a usable
key at all, how many distinct keys exist, how many clips sit in a colliding group, and
how large the worst group is. Those four numbers say whether tier 2 is sufficient or
tier 3 has to be built.

## Layout

```
DAWproject-format-test/
  compare.py                  the comparison runner
  waveform/       A B C D     run 1  (see "The four files")
  studio-one/     A B C D     run 2
  cross-daw/                  run 3
    waveform-A-via-studio-one.DAWproject
    studio-one-A-via-waveform.DAWproject
  reports/                    generated evidence — committed
    <run>/summary.txt           the printed summary
    <run>/*.project.xml.diff    unified diff of the two project.xml files
    <run>/*.ids-{left,right}    every element carrying an id
    <run>/*.clips-{left,right}  every clip with its content key
  extracted/                  unpacked scratch — gitignored
```

The archives are committed. They are the evidence, and they are small if the audio
rule below is followed.

## The base session

Build this once **in each DAW** and save it. All four exports of a run derive from it.

- A new empty project. Leave tempo and time signature at their defaults.
- **Four tracks**, in this order from top to bottom, named exactly:
  1. `Kick` — audio
  2. `Bass` — audio
  3. `Vox` — audio
  4. `Keys` — instrument / MIDI
- `Bass` and `Vox` each hold **one audio clip starting at bar 1**. Use two *different*
  audio files so each has a distinct content hash — any sounds will do.
- **`Kick` holds the same audio file three times**, as three separate clips at bars
  1, 3 and 5, each the full length of the file with no trimming. This is deliberate
  and it is the point of question 5: three clips that share one `(path, playStart,
  playStop)` key. A session without repeated material cannot measure key collision,
  and repeated material is normal in music production. Use a third audio file here,
  distinct from the other two.
- **`Keys` holds one MIDI clip at bar 1** with three or four notes in it. The
  instrument can be any VST3, or none at all — it does not need to make a sound. This
  clip exists to measure the other half of question 5: a clip with **no media key**,
  which tier 2 cannot address at all.
- **Keep the audio short: 2–5 seconds per file.** The export embeds audio in the
  archive, and these files are going into git. Long audio makes the repository heavy
  for no extra information.
- **Use the same three audio files in both DAWs.** That makes the cross-DAW audio
  hashes in run 3 comparable instead of meaningless.
- On **`Bass`**, add a **volume automation curve with exactly three points** at
  distinct times and distinct values — for example 0 dB at bar 1, −6 dB at bar 2,
  0 dB at bar 3.
- On **`Vox`**, add **one plugin** and move at least one parameter clearly off its
  default. It must be a **VST3 that is installed in both DAWs** — VST3 is the only
  plugin format in the
  [cross-DAW subset](../../core/Requirements.md#project-mode-cross-daw-or-single-daw),
  and if the plugin only exists on one side, run 3 cannot tell a format limitation
  from a missing install.
- **Save the session** before exporting anything.

Always export **self-contained**, so audio and plugin state are embedded in the
archive rather than referenced from disk.

## The four files

Each run produces these four. Order matters: do not make the change for `C` until
`A` and `B` both exist.

### `A.DAWproject`

The base session exactly as described above, exported.

This is the reference. Every comparison is against it.

### `B.DAWproject`

The **same session, completely unchanged**, exported a second time — but first
**quit the DAW entirely and reopen it**, then load the saved session and export.

Nothing about the session may differ from `A`. The restart is the point: it tests
whether ids and paths survive the application's process lifetime, not just a second
export within one run.

### `C.DAWproject`

The base session with **exactly one change**: add **one new empty audio track**,
named `Inserted`, positioned at the **very top of the track list, above `Kick`**.

Nothing else. No new audio, no plugin, no automation, no reordering of the existing
three tracks.

Placing it at the top is essential. If ids are positional, inserting above existing
tracks forces them to renumber and the test catches it. Adding a track at the bottom
would look identical to genuinely stable ids and give a false pass.

### `D.DAWproject`

The result of a **round trip**: import `A.DAWproject` back into the same DAW as a new
project, then export that imported project without editing anything.

While the imported project is open, **look at it** and record what is missing or
wrong in the results below. Automation still there? Plugin loaded with its parameter
still moved? Clips in the right places? Track names and order intact? This is the
only part of the test that needs human judgement rather than file comparison, and it
is the part that decides question 1.

---

## Run 1 — Waveform Free 14

Free, no account, no time limit, full DAWproject import and export. This is the run
that costs nothing, so it goes first.

- Export: `File > Export Other > Export as DAWproject file…`
- Import: `File > Import Other > Import a DAWproject file…`

If the menu path differs in your build, record the one you used in the results.

Put the four exports in `waveform/` as `A.DAWproject` … `D.DAWproject`, then:

```
python compare.py waveform
```

## Run 2 — Studio One

Studio One **6.5 or later, Professional only** — DAWproject is not in Artist. This is
the DAW that matters most for this project, since it is what the collaborator on the
first real trial uses.

Since January 2026 this product ships as **Fender Studio Pro**. Record which build you
actually ran, under whichever name it carries — the rebrand landed mid-format-adoption
and export behaviour may well differ across it, which would itself be worth knowing.

Build the same base session, following the spec above exactly: same track names, same
order, same three audio files, same three-point automation curve, same VST3 plugin
with the same parameter moved.

Export and import live under Studio One's DAWproject menu entries; the exact path has
moved between versions, so **record the path you used** in the results.

Put the four exports in `studio-one/`, then:

```
python compare.py studio-one
```

### Comparing run 2 against run 1

This is not a file diff — the two sessions contain different bytes and there is no
meaningful comparison between `waveform/A` and `studio-one/A` as archives. What is
compared is **behaviour**, in the results table below: does each DAW pass the same
three questions?

The two `project.xml` files are still worth reading side by side, though, for a
different reason: they show how two independent implementations encode the same
logical session. Where they diverge is where the cross-DAW subset is thinner than the
format on paper.

## Run 3 — Cross-DAW

Both earlier runs test a DAW against itself. This one tests the claim the whole
cross-DAW project mode rests on: that a session exported by one DAW arrives intact in
another.

Two files, each an import-then-export in the *other* DAW:

| File | How | Compared against |
| --- | --- | --- |
| `cross-daw/waveform-A-via-studio-one.DAWproject` | import `waveform/A.DAWproject` into Studio One, export without editing | `waveform/A` |
| `cross-daw/studio-one-A-via-waveform.DAWproject` | import `studio-one/A.DAWproject` into Waveform, export without editing | `studio-one/A` |

As with `D`, **look at each imported project before exporting** and record what
arrived and what did not.

```
python compare.py cross
```

### What is expected to hold

Everything in the base session is inside the cross-DAW subset, so all of this should
survive:

- Four tracks, correct names, correct order
- Clip positions correct, including all three `Kick` clips at bars 1, 3 and 5
- Audio content byte-identical (the archive carries it)
- The MIDI notes in the `Keys` clip
- Track volume and pan
- The three-point volume automation curve on `Bass`
- The VST3 on `Vox`, loaded, with its moved parameter intact

**Expect the automation curve to be the first thing that breaks.** Users report
volume, pan and plugin-parameter automation failing to transfer between Studio One
and Cubase, so a failure here would confirm a known gap rather than reveal a new one —
but it is a gap in a construct this project's
[cross-DAW subset](../../core/Requirements.md#project-mode-cross-daw-or-single-daw)
currently claims. If it fails, the subset is what has to change.

Anything on this list that does not survive is a hole in the cross-DAW subset as
documented in
[Requirements.md](../../core/Requirements.md#project-mode-cross-daw-or-single-daw),
and the requirement is what has to change — not the test.

### What is expected to fail

**Element ids almost certainly do not survive a cross-DAW transfer.** The importing
DAW builds its own objects and assigns its own ids; nothing in the format obliges it
to carry the originals through.

Confirming this would mean tier 1 is unavailable across a handoff: a repository where
two people export from different DAWs would show a **whole-project rewrite on every
handoff** if ids were all the core had to go on.

They are not all it has to go on, and that is the difference between this being a
finding and being a catastrophe. Clips never had ids anyway, so the clip layer is
already on tier 2 and loses nothing crossing DAWs — provided media paths and in/out
points survive, which is the thing to check carefully here. Tracks and devices fall
from tier 1 to tier 4, and track lists are short, named and ordered, which is the
friendliest possible case for name matching.

So the honest consequence is narrower than it first looks: **cross-DAW handoff costs
one tier, not the whole design.** What it does rule out is any merge that needs exact
device or parameter identity across a handoff.

Confirming it would still force a choice between:

- recording which DAW exported each commit and expecting tier-4 matching at every
  handoff;
- or treating "one exporter per branch" as the supported collaboration shape, keeping
  tier 1 within a branch.

Neither is in the requirements today. Do not soften the result if it lands this way —
it is exactly the kind of thing this test exists to find early.

---

## Running the comparisons

[`compare.py`](compare.py) does everything: unpacks each archive, hashes every entry,
diffs `project.xml`, and reports which element ids survived. Standard library only,
Python 3.8+, no `unzip` or `sha256sum` needed — it runs the same from PowerShell or
Git Bash.

```
python compare.py waveform      # run 1
python compare.py studio-one    # run 2
python compare.py cross         # run 3
python compare.py all           # everything present; missing files are skipped
```

Each run writes to `reports/<run>/`:

- `summary.txt` — the printed summary
- `<pair>.project.xml.diff` — unified diff of the two `project.xml` files
- `<pair>.ids-left.txt` / `.ids-right.txt` — every element carrying an `id`, in
  document order, as `tag  name  id`
- `<pair>.clips-left.txt` / `.clips-right.txt` — every clip with its content key, as
  `name  kind  time  duration  playStart  playStop  path`

Two lines to read first:

- `named:` — *N named elements on both sides, M changed id*. `M = 0` on `A-vs-C`
  means **tier 1 is available** for tracks, channels and devices.
- `keys:` and the verdict lines under `match:` — how many clips are keyable, and
  whether the keys collide. This says whether **tier 2** carries the clip layer or
  **tier 3** has to be built.

## What the results mean

- **A vs B identical** → the exporter is deterministic and stable across a restart.
  Necessary, but on its own it does not prove ids persist. **If they differ**, note
  whether the difference is ids, audio paths, or timestamps.
- **A vs C shows only the added track, 0 named elements changed id** → ids genuinely
  persist, and **tier 1** is available for everything that carries one. **If
  pre-existing tracks changed id**, ids are positional and tier 1 is gone; tracks drop
  to **tier 4** (name + position), which is weaker but not fatal — track lists are
  short, named, and ordered, which is close to the easiest case for name matching.
- **Clip keys** are read independently of the id result, because clips never have ids:
  - *All clips keyable, no collisions* → tier 2 resolves the clip layer exactly. Best
    realistic outcome.
  - *Collisions present* (expected — `Kick` has three identical clips by
    construction) → tier 3 is mandatory, and the "largest group" number says how hard
    the assignment problem gets. Three is trivial; a session with a loop repeated
    sixty-four times is not.
  - *Clips with no media key* (expected — `Keys` is MIDI) → the share of a real
    session that tier 2 cannot touch at all. If that share is large, MIDI-heavy
    sessions need tier 4 to be good, not just present.
- **A vs D** → anything present in `A` and absent from `D` was dropped by the import.
  This is machine-checkable structural loss, and it complements the visual inspection.
- **Audio hashes equal at equal paths** → audio deduplicates across commits for free.
  **If paths churn** but hashes match, storage is still fine and only the diff gets
  noisy — this is the least damaging outcome. **If hashes differ** for unchanged
  audio, every commit re-stores the audio and the storage questions in
  [Requirements.md](../../core/Requirements.md#open-questions) become urgent.

### If the round trip fails

Failing question 1 does **not** mean abandoning DAWproject for format-agnostic blob
storage. Opaque blobs cannot support additive merge at all, since the arrangement
lives inside one file. The fallback is to re-add the DAW's native project file as a
byte-exact fidelity anchor while keeping DAWproject for diff — the dual-representation
design, which is preserved in this repository's git history.

### What would actually be fatal

For the record, since this test is deliberately hard to fail: the results that would
genuinely end the DAWproject bet are narrow, and none of them are about ids.

- **The round trip loses musical content** (question 1) *and* the native file is too
  large or too opaque to serve as an anchor. Then the format cannot be trusted to hold
  a session at all.
- **Clip content keys are unstable across exports of the same session** — media paths
  churn *and* `playStart`/`playStop` are rewritten. That removes tier 2 as well as
  tier 1, leaving only name-and-position for everything, which is too weak to build
  diff on.
- **Exports are non-deterministic in content**, so that `A` and `B` differ in ways
  that are not ids — meaning every commit records changes the user did not make.

Anything short of that is a tier, not a failure. Record it as such.

---

## Results

Paste the relevant lines from `reports/<run>/summary.txt` and add what only a human
can see.

### Run 1 — Waveform Free 14

**Run date:**
**Waveform version:**
**Export menu path used:**
**Plugin used on `Vox`:**

#### A vs B — determinism and restart stability

- Identical `project.xml`?
- If not, what differs?
- Audio entry paths identical? Content hashes identical?

#### A vs C — id persistence under edit (tier 1)

- Did `Kick`, `Bass`, `Vox` and `Keys` keep their ids after `Inserted` was added
  above them?
- What id scheme is in use (sequential counter, GUID, name-derived)?
- Does the diff show only the added track, or more?
- **Tier 1 available for tracks/channels/devices?** yes / no

#### Clip keys — tier 2 viability

From the `clips:`, `keys:` and `match:` lines of the summary.

- Total clips, and how many carry a media key:
- Distinct keys, clips in colliding groups, largest group:
- Did the three `Kick` clips collapse to one key as predicted?
- Is `playStart`/`playStop` present on every audio clip, or omitted when untrimmed?
- Are media paths stable across `A`, `B` and `C`?
- **Tier reached for the clip layer:** 2 / 3 / 4

#### A vs D — round trip

Machine comparison:

- Elements present in `A` and missing from `D`:
- Elements changed between `A` and `D`:

Visual inspection of the imported project:

- Automation curve on `Bass` present and correct?
- Plugin on `Vox` loaded, with its moved parameter intact?
- MIDI notes in the `Keys` clip present and correct?
- All three `Kick` clips present, at bars 1, 3 and 5?
- Clip positions correct?
- Track names and order intact?
- Anything else wrong or missing:

#### Storage

- Size of each archive:
- Total size of the four archives:
- Combined size if audio were stored once (deduplicated):
- Did the three `Kick` clips embed the audio once or three times?

### Run 2 — Studio One

**Run date:**
**Studio One version and edition:**
**Export menu path used:**
**Import menu path used:**
**Plugin used on `Vox`:**

#### A vs B — determinism and restart stability

#### A vs C — id persistence under edit (tier 1)

#### Clip keys — tier 2 viability

#### A vs D — round trip

Machine comparison:

Visual inspection of the imported project:

#### Storage

#### How Studio One's `project.xml` differs in shape from Waveform's

### Run 3 — Cross-DAW

**Run date:**
**Same machine, or transferred between two?**
**VST3 present in both DAWs?**

#### `waveform/A` → Studio One → export

- Tracks, names, order intact?
- Clip positions intact, including all three `Kick` clips?
- Audio content hashes preserved? Paths preserved?
- MIDI notes in `Keys` intact?
- Automation curve on `Bass` intact?
- VST3 on `Vox` loaded with its parameter intact?
- Element ids preserved, or fully reassigned?
- **Clip content keys preserved?** (paths and `playStart`/`playStop` — this is what
  decides whether cross-DAW diff has anything to work with once ids are gone)
- Anything else lost:

#### `studio-one/A` → Waveform → export

- Tracks, names, order intact?
- Clip positions intact, including all three `Kick` clips?
- Audio content hashes preserved? Paths preserved?
- MIDI notes in `Keys` intact?
- Automation curve on `Bass` intact?
- VST3 on `Vox` loaded with its parameter intact?
- Element ids preserved, or fully reassigned?
- **Clip content keys preserved?** (paths and `playStart`/`playStop` — this is what
  decides whether cross-DAW diff has anything to work with once ids are gone)
- Anything else lost:

#### Is the transfer symmetric?

Does one direction lose more than the other, and what:

### Verdict

| | Waveform | Studio One |
| --- | --- | --- |
| 1 — round trip survives | | |
| 2 — audio deduplicates | | |
| 3 — ids persist (tier 1) | | |
| 5 — clip keys usable (tier 2) | | |
| 5 — keys collide (tier 3 needed) | | |
| clips with no key at all | | |

**4 — cross-DAW subset holds:**

**Cross-DAW ids survive:**

### Tier reached

Fill this in per DAW. This is the actual output of the test and the thing
[Requirements.md](../../core/Requirements.md#element-correspondence) is written
against.

| Element class | Waveform | Studio One | Cross-DAW |
| --- | --- | --- | --- |
| Tracks / channels | | | |
| Devices / plugins | | | |
| Audio clips | | | |
| MIDI clips | | | |
| Automation | | | |

**Consequences for the design:**

**Requirements that need changing:**

### Upstream

The next step after this test is not code — it is
[taking the result to Bitwig](../../core/MVP.md#after-the-test-upstream). Fill in what
this run supports.

- **Is there a minimal, cheap change to the format that would raise a tier?** (The
  candidate: a stability guarantee on ids that already exist, which costs a vendor
  nothing to honour and benefits every consumer of the format.)
- **Which DAW's behaviour is the counter-example worth showing?**
- **Does anything here belong on
  [issue #40](https://github.com/bitwig/dawproject/issues/40) as measured evidence
  rather than a request?**
