#!/usr/bin/env python3
# DAWproject format test - comparison runner.
#
# Unpacks the exported .DAWproject archives, hashes every entry, and reports
# what changed between them: entry sets, content hashes, the project.xml diff,
# and - the point of the whole exercise - whether element ids survived.
#
# Pure standard library. Run it from anywhere, with any Python 3.8+:
#
#   python compare.py waveform      A/B/C/D exported from Waveform Free
#   python compare.py studio-one    A/B/C/D exported from Studio One
#   python compare.py cross         each DAW's A against its foreign round trip
#   python compare.py all           every run whose files are present
#
# Output:
#   extracted/<run>/           unpacked archives (scratch, gitignored)
#   reports/<run>/             summary.txt, project.xml diffs, id dumps
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
         "what Studio One keeps of a Waveform export"),
        ("studio-one-through-waveform",
         "studio-one/A", "cross-daw/studio-one-A-via-waveform",
         "what Waveform keeps of a Studio One export"),
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
