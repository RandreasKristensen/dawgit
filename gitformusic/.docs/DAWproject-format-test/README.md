# DAWproject Format Test

The measurement that [`MVP.md`](../../core/MVP.md#step-zero-the-round-trip-experiment)
calls step zero. It decides whether DAWproject can carry version history at all, and
whether the general merge of
[stage two](../../core/Requirements.md#stage-two--merge) is possible.

Nobody appears to have run this. [Issue #40 on the DAWproject
repository](https://github.com/bitwig/dawproject/issues/40) — "Version control for
.dawproject files", which asks for exactly the ID persistence this test measures —
has been open since January 2023 with no maintainer response. The format is used for
one-way handoff, so no one has had a reason to export the same session twice and
compare.

**Results are per-DAW, not per-format.** What Waveform does says nothing about what
Studio One does. So the test runs three times:

| Run | Needs | Answers |
| --- | --- | --- |
| 1. [Waveform](#run-1--waveform-free-14) | Waveform Free 14, no licence | Does *a* DAW keep ids stable? |
| 2. [Studio One](#run-2--studio-one) | Studio One 6.5+ **Pro** | Does the DAW this project is actually aimed at? |
| 3. [Cross-DAW](#run-3--cross-daw) | both, ideally the same machine | Do the [cross-DAW subset](../../core/Requirements.md#project-mode-cross-daw-or-single-daw) assumptions hold? |

Run 1 first. It costs nothing, and if it fails there is no point borrowing a Studio
One licence yet.

## What is being measured

| | Question | Decides |
| --- | --- | --- |
| 1 | Does a session survive export and re-import into the same DAW? | Whether the DAW's native project file must also be tracked |
| 2 | Is audio byte-identical across exports, at stable paths? | Whether audio deduplicates for free, and how noisy diffs are |
| 3 | Do element ids survive an edit elsewhere in the project? | Whether structured diff and stage-two merge are possible |
| 4 | Does the cross-DAW subset survive a transfer between two DAWs? | Whether cross-DAW mode is a real mode or a fiction |

Question 3 is the one with a trap in it. Two exports of an *unchanged* session prove
only that the exporter is **deterministic**. If ids are assigned by walking the
project in order, an unchanged session exports identically every time while ids are
really *positional* — and the moment a track is inserted above another, everything
below it renumbers and every future diff shows the whole arrangement rewritten. That
is why file **C** inserts its new track at the **top**, not the bottom.

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
  extracted/                  unpacked scratch — gitignored
```

The archives are committed. They are the evidence, and they are small if the audio
rule below is followed.

## The base session

Build this once **in each DAW** and save it. All four exports of a run derive from it.

- A new empty project. Leave tempo and time signature at their defaults.
- **Three audio tracks**, in this order from top to bottom, named exactly:
  1. `Kick`
  2. `Bass`
  3. `Vox`
- Each track holds **one audio clip starting at bar 1**. Use three *different* audio
  files so each has a distinct content hash — any sounds will do.
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

- Three tracks, correct names, correct order
- One clip per track at bar 1, correct positions
- Audio content byte-identical (the archive carries it)
- Track volume and pan
- The three-point volume automation curve on `Bass`
- The VST3 on `Vox`, loaded, with its moved parameter intact

Anything on this list that does not survive is a hole in the cross-DAW subset as
documented in
[Requirements.md](../../core/Requirements.md#project-mode-cross-daw-or-single-daw),
and the requirement is what has to change — not the test.

### What is expected to fail

**Element ids almost certainly do not survive a cross-DAW transfer.** The importing
DAW builds its own objects and assigns its own ids; nothing in the format obliges it
to carry the originals through.

If that is confirmed, it is the most consequential result in this whole document. It
means a repository where two people export from different DAWs shows a **whole-project
rewrite on every handoff**, even when nothing changed — and stage-two merge is only
real *within* one DAW, unless diff falls back to matching by name and position.

Concretely, confirming it would force one of:

- record which DAW exported each commit, and expect noise at every handoff;
- match elements by name and position rather than id in cross-DAW mode, accepting
  weaker merge;
- or treat "one exporter per branch" as the supported collaboration shape.

None of those are in the requirements today. Do not soften the result if it lands
this way — it is exactly the kind of thing this test exists to find early.

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

The line to read first is `named:` — *N named elements on both sides, M changed id*.
`M = 0` on `A-vs-C` is question 3 passing.

## What the results mean

- **A vs B identical** → the exporter is deterministic and stable across a restart.
  Necessary, but on its own it does not prove ids persist. **If they differ**, note
  whether the difference is ids, audio paths, or timestamps.
- **A vs C shows only the added track, 0 named elements changed id** → ids genuinely
  persist, and structured diff and stage-two merge are on. **If pre-existing tracks
  changed id**, ids are positional; diff must fall back to matching by name and
  position, and general merge is constrained.
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

#### A vs C — id persistence under edit

- Did `Kick`, `Bass` and `Vox` keep their ids after `Inserted` was added above them?
- What id scheme is in use (sequential counter, GUID, name-derived)?
- Does the diff show only the added track, or more?

#### A vs D — round trip

Machine comparison:

- Elements present in `A` and missing from `D`:
- Elements changed between `A` and `D`:

Visual inspection of the imported project:

- Automation curve on `Bass` present and correct?
- Plugin on `Vox` loaded, with its moved parameter intact?
- Clip positions correct?
- Track names and order intact?
- Anything else wrong or missing:

#### Storage

- Size of each archive:
- Total size of the four archives:
- Combined size if audio were stored once (deduplicated):

### Run 2 — Studio One

**Run date:**
**Studio One version and edition:**
**Export menu path used:**
**Import menu path used:**
**Plugin used on `Vox`:**

#### A vs B — determinism and restart stability

#### A vs C — id persistence under edit

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
- Clip positions intact?
- Audio content hashes preserved? Paths preserved?
- Automation curve on `Bass` intact?
- VST3 on `Vox` loaded with its parameter intact?
- Element ids preserved, or fully reassigned?
- Anything else lost:

#### `studio-one/A` → Waveform → export

- Tracks, names, order intact?
- Clip positions intact?
- Audio content hashes preserved? Paths preserved?
- Automation curve on `Bass` intact?
- VST3 on `Vox` loaded with its parameter intact?
- Element ids preserved, or fully reassigned?
- Anything else lost:

#### Is the transfer symmetric?

Does one direction lose more than the other, and what:

### Verdict

| | Waveform | Studio One |
| --- | --- | --- |
| 1 — round trip survives | | |
| 2 — audio deduplicates | | |
| 3 — ids persist | | |

**4 — cross-DAW subset holds:**

**Cross-DAW ids survive:**

**Consequences for the design:**

**Requirements that need changing:**

**Worth reporting upstream on [issue #40](https://github.com/bitwig/dawproject/issues/40)?**
