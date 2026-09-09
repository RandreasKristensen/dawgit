#!/usr/bin/env python3
# DAWproject format test - comparison runner.
#
# Unpacks the exported .DAWproject archives, hashes every entry, and reports
# what changed between them: entry sets, content hashes, the project.xml diff,
# whether element ids survived, and - because clips carry no id in this format
# at all - whether content keys can identify clips instead.
#
# The output is not pass/fail. It says which tier of the correspondence ladder
# in README.md this DAW's exports actually support.
#
# Pure standard library. Run it from anywhere, with any Python 3.8+:
#
#   python compare.py waveform      A/B/C/D exported from Waveform Free
#   python compare.py studio-one    A/B/C/D exported from Fender Studio Pro
#   python compare.py cross         each DAW's A against its foreign round trip
#   python compare.py all           every run whose files are present
#
# Output:
#   extracted/<run>/           unpacked archives (scratch, gitignored)
#   reports/<run>/             summary.txt, project.xml diffs, id dumps,
#                              clip dumps
#
# See README.md for what the numbers mean.

import difflib
import hashlib
import os
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTED = os.path.join(HERE, "extracted")
REPORTS = os.path.join(HERE, "reports")

AUDIO_EXT = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a", ".caf"}

# run name -> list of (label, left archive stem, right archive stem, what it decides)
RUNS = {
    "waveform": [
        ("A-vs-B", "waveform/A", "waveform/B", "determinism and restart stability"),
        ("A-vs-C", "waveform/A", "waveform/C", "id persistence under edit"),
        ("A-vs-D", "waveform/A", "waveform/D", "round-trip structural loss"),
    ],
    "studio-one": [
        ("A-vs-B", "studio-one/A", "studio-one/B", "determinism and restart stability"),
        ("A-vs-C", "studio-one/A", "studio-one/C", "id persistence under edit"),
        ("A-vs-D", "studio-one/A", "studio-one/D", "round-trip structural loss"),
    ],
    "cross": [
        ("waveform-through-studio-one",
         "waveform/A", "cross-daw/waveform-A-via-studio-one",
         "what Fender Studio Pro keeps of a Waveform export"),
        ("studio-one-through-waveform",
         "studio-one/A", "cross-daw/studio-one-A-via-waveform",
         "what Waveform keeps of a Fender Studio Pro export"),
    ],
}


def find_archive(stem):
    # Accept A.DAWproject, A.dawproject, A.zip - DAWs are inconsistent about case.
    base = os.path.join(HERE, stem)
    for ext in (".DAWproject", ".dawproject", ".DAWPROJECT", ".zip"):
        if os.path.isfile(base + ext):
            return base + ext
    return None


def extract(archive, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)


def walk(root):
    # relative posix paths of every file under root
    out = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root):
    return {rel: sha256(os.path.join(root, rel)) for rel in walk(root)}


def project_xml(root):
    for rel in walk(root):
        if rel.lower().endswith("project.xml"):
            return os.path.join(root, rel)
    return None


def local(tag):
    return tag.rsplit("}", 1)[-1]


def collect_ids(xml_path):
    # Document-order list of (tag, name, id) for every element carrying an id,
    # plus the same keyed by id and by (tag, name).
    entries = []
    try:
        tree = ET.parse(xml_path)
    except Exception as exc:
        return entries, {}, {}, "unparseable: %s" % exc
    for elem in tree.iter():
        eid = elem.attrib.get("id")
        if eid is None:
            continue
        entries.append((local(elem.tag), elem.attrib.get("name", ""), eid))
    by_id = {e[2]: e for e in entries}
    by_name = {}
    for tag, name, eid in entries:
        if name:
            by_name.setdefault((tag, name), eid)
    return entries, by_id, by_name, None


def id_scheme(entries):
    if not entries:
        return "no ids found"
    ids = [e[2] for e in entries]
    if all(i.isdigit() for i in ids):
        return "numeric counter - suspect positional"
    if all(len(i) >= 32 for i in ids):
        return "opaque / GUID-like"
    return "mixed or DAW-specific"


def clip_entries(xml_path):
    # Every Clip in document order, carrying the natural key that the
    # reconform technique matches on: source media path plus content in/out
    # points (playStart/playStop).
    #
    # This exists because of a schema fact, not a hunch. In Project.xsd the
    # `clip` type extends `nameable`, while `id` is declared on
    # `referenceable`. Clips therefore carry NO id in any DAW, by design.
    # Tracks, channels, devices and timelines are referenceable; clips are
    # not. Clip correspondence is always inferred, never read.
    #
    # See README.md, "The correspondence ladder".
    entries = []
    try:
        tree = ET.parse(xml_path)
    except Exception as exc:
        return entries, "unparseable: %s" % exc

    for parent in tree.iter():
        for elem in list(parent):
            if local(elem.tag) != "Clip":
                continue
            path = None
            kind = "other"
            for desc in elem.iter():
                dl = local(desc.tag)
                if dl == "File" and desc.attrib.get("path"):
                    path = desc.attrib["path"]
                    kind = "audio"
                    break
                if dl == "Notes" and kind == "other":
                    kind = "notes"
            entries.append({
                "name": elem.attrib.get("name", ""),
                "kind": kind,
                "path": path,
                "play_start": elem.attrib.get("playStart"),
                "play_stop": elem.attrib.get("playStop"),
                "time": elem.attrib.get("time"),
                "duration": elem.attrib.get("duration"),
                # Clips/Lanes carry the owning track as an IDREF.
                "track": parent.attrib.get("track") or parent.attrib.get("id") or "",
            })
    return entries, None


def clip_key(entry):
    # Tier 2: source media plus content in/out points. None when the clip has
    # no media file to key on - MIDI/note clips, most obviously.
    if not entry["path"]:
        return None
    return (entry["path"], entry["play_start"], entry["play_stop"])


def group_by_key(entries):
    groups = {}
    for e in entries:
        k = clip_key(e)
        if k is not None:
            groups.setdefault(k, []).append(e)
    return groups


def report_clips(left, right, label, report_dir, say):
    # Measures which tier of the correspondence ladder this session actually
    # needs. A failed id test is not fatal on its own; what matters is whether
    # a weaker strategy can carry the clip layer instead.
    def census(entries, side):
        kinds = {}
        for e in entries:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        shape = ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items()))
        keyable = sum(1 for e in entries if clip_key(e) is not None)
        say("   clips %s : %d total (%s) - %d keyable, %d with no media key"
            % (side, len(entries), shape or "none", keyable, len(entries) - keyable))
        return keyable

    keyable_l = census(left, "L")
    census(right, "R")

    lg, rg = group_by_key(left), group_by_key(right)

    # Collision rate on the left is the question the vordio comment glosses:
    # "assuming all files have unique names". A loop dropped N times in an
    # arrangement produces N identical keys and the key alone cannot separate
    # them.
    ambiguous = {k: v for k, v in lg.items() if len(v) > 1}
    in_ambiguous = sum(len(v) for v in ambiguous.values())
    largest = max([len(v) for v in lg.values()] or [0])
    say("   keys    : %d distinct on the left, %d clips in colliding groups, largest group %d"
        % (len(lg), in_ambiguous, largest))

    matched = set(lg) & set(rg)
    lost = set(lg) - set(rg)
    fresh = set(rg) - set(lg)
    # Movement is only readable where the key is unambiguous on both sides.
    # Inside a colliding group the key cannot say which clip became which, so
    # those are counted as undecidable rather than silently compared.
    moved = unmoved = undecidable = 0
    for k in matched:
        if len(lg[k]) == 1 and len(rg[k]) == 1:
            if lg[k][0]["time"] != rg[k][0]["time"]:
                moved += 1
            else:
                unmoved += 1
        else:
            undecidable += 1
    say("   match   : %d keys matched, %d only left, %d only right"
        % (len(matched), len(lost), len(fresh)))
    say("             of matched: %d in place, %d moved, %d undecidable (colliding key)"
        % (unmoved, moved, undecidable))

    # The verdict this whole block exists to produce.
    if keyable_l == 0 and left:
        say("             TIER 2 UNAVAILABLE - no clip carries a media key here")
    elif len(left) - keyable_l > 0:
        say("             tier 2 covers audio clips only; %d clip(s) need tier 4 (name + position)"
            % (len(left) - keyable_l))
    if largest > 1:
        say("             keys COLLIDE - tier 3 (assignment by position) is required, not optional")
    elif lg:
        say("             keys are unique in this session - tier 2 resolves clips on its own")

    for side, entries in (("left", left), ("right", right)):
        path = os.path.join(report_dir, "%s.clips-%s.txt" % (label, side))
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# name  kind  time  duration  playStart  playStop  path\n")
            for e in entries:
                fh.write("%-20s %-6s %-10s %-10s %-10s %-10s %s\n"
                         % (e["name"] or "-", e["kind"], e["time"] or "-",
                            e["duration"] or "-", e["play_start"] or "-",
                            e["play_stop"] or "-", e["path"] or "-"))


def compare(label, left_root, right_root, decides, report_dir, out):
    def say(line=""):
        out.append(line)

    say("== %s  (%s)" % (label, decides))

    lm, rm = manifest(left_root), manifest(right_root)
    lset, rset = set(lm), set(rm)
    shared = lset & rset
    same = sorted(p for p in shared if lm[p] == rm[p])
    diff = sorted(p for p in shared if lm[p] != rm[p])
    only_l = sorted(lset - rset)
    only_r = sorted(rset - lset)

    say("   entries : %d shared, %d only left, %d only right"
        % (len(shared), len(only_l), len(only_r)))
    say("   content : %d identical, %d differing" % (len(same), len(diff)))
    for p in only_l:
        say("             - only left  : %s" % p)
    for p in only_r:
        say("             + only right : %s" % p)
    for p in diff:
        say("             ~ differs    : %s" % p)

    audio_l = {p: h for p, h in lm.items() if os.path.splitext(p)[1].lower() in AUDIO_EXT}
    audio_r = {p: h for p, h in rm.items() if os.path.splitext(p)[1].lower() in AUDIO_EXT}
    shared_audio = set(audio_l) & set(audio_r)
    common_content = set(audio_l.values()) & set(audio_r.values())
    say("   audio   : %d left, %d right, %d at identical paths, %d content hashes in common"
        % (len(audio_l), len(audio_r), len(shared_audio), len(common_content)))
    if audio_l and not shared_audio and common_content:
        say("             paths churn but content is stable - storage fine, diffs noisy")

    lx, rx = project_xml(left_root), project_xml(right_root)
    if not lx or not rx:
        say("   xml     : project.xml missing on one side - cannot compare")
        say("")
        return

    with open(lx, encoding="utf-8", errors="replace") as fh:
        lt = fh.read().splitlines(keepends=True)
    with open(rx, encoding="utf-8", errors="replace") as fh:
        rt = fh.read().splitlines(keepends=True)

    if lt == rt:
        say("   xml     : project.xml identical")
    else:
        ud = list(difflib.unified_diff(lt, rt, "left/project.xml", "right/project.xml"))
        added = sum(1 for l in ud if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in ud if l.startswith("-") and not l.startswith("---"))
        path = os.path.join(report_dir, label + ".project.xml.diff")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(ud)
        say("   xml     : differs, +%d / -%d lines -> %s"
            % (added, removed, os.path.relpath(path, HERE).replace(os.sep, "/")))

    left_ids, lbi, lbn, lerr = collect_ids(lx)
    right_ids, rbi, rbn, rerr = collect_ids(rx)
    if lerr or rerr:
        say("   ids     : %s" % (lerr or rerr))
        say("")
        return

    kept = set(lbi) & set(rbi)
    lost = set(lbi) - set(rbi)
    fresh = set(rbi) - set(lbi)
    say("   ids     : %d left, %d right - %d kept, %d lost, %d new"
        % (len(left_ids), len(right_ids), len(kept), len(lost), len(fresh)))
    say("             scheme on the left: %s" % id_scheme(left_ids))

    common_names = set(lbn) & set(rbn)
    renumbered = sorted(k for k in common_names if lbn[k] != rbn[k])
    say("   named   : %d named elements on both sides, %d changed id"
        % (len(common_names), len(renumbered)))
    for tag, name in renumbered[:20]:
        say("             ! %s '%s': %s -> %s"
            % (tag, name, lbn[(tag, name)], rbn[(tag, name)]))
    if renumbered:
        say("             ids are NOT stable for these elements")
    elif common_names:
        say("             every named element kept its id")

    for side, entries, root in (("left", left_ids, left_root),
                                ("right", right_ids, right_root)):
        path = os.path.join(report_dir, "%s.ids-%s.txt" % (label, side))
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# %s\n" % root.replace(os.sep, "/"))
            for tag, name, eid in entries:
                fh.write("%-24s %-24s %s\n" % (tag, name, eid))

    left_clips, lcerr = clip_entries(lx)
    right_clips, rcerr = clip_entries(rx)
    if lcerr or rcerr:
        say("   clips   : %s" % (lcerr or rcerr))
    else:
        report_clips(left_clips, right_clips, label, report_dir, say)
    say("")


def run(name):
    pairs = RUNS[name]
    report_dir = os.path.join(REPORTS, name)
    os.makedirs(report_dir, exist_ok=True)
    out = []
    ran = 0

    for label, left_stem, right_stem, decides in pairs:
        la, ra = find_archive(left_stem), find_archive(right_stem)
        missing = [s for s, a in ((left_stem, la), (right_stem, ra)) if a is None]
        if missing:
            out.append("== %s  SKIPPED - missing: %s" % (label, ", ".join(missing)))
            out.append("")
            continue
        left_root = os.path.join(EXTRACTED, name, label + "-left")
        right_root = os.path.join(EXTRACTED, name, label + "-right")
        extract(la, left_root)
        extract(ra, right_root)
        compare(label, left_root, right_root, decides, report_dir, out)
        ran += 1

    text = "\n".join(["# run: %s" % name, ""] + out)
    print(text)
    with open(os.path.join(report_dir, "summary.txt"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    return ran


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print("usage: python compare.py {waveform|studio-one|cross|all}")
        return 2
    target = argv[1]
    names = list(RUNS) if target == "all" else [target]
    for n in names:
        if n not in RUNS:
            print("unknown run: %s (expected one of: %s, all)" % (n, ", ".join(RUNS)))
            return 2
    total = 0
    for n in names:
        total += run(n)
    if total == 0:
        print("nothing compared - no archives found. See README.md for what to export.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
