#!/usr/bin/env python3
"""What the voice does with pitch, over a list of sentences rather than one.

pitch.py measures one wav. Intonation is not one sentence: the terminal fall
of any single utterance depends on what the last word happens to end in -- a
reduced vowel, a dropped r, a voiceless stop -- so a change is only visible
as an average over a set. This speaks every line of a case file and prints
the averages by kind, which is what a change to an intonation number has to
be judged by.

    python tools/melody.py out/catalan/prosody.txt          measure
    python tools/melody.py out/catalan/prosody.txt -o base  and keep it
    python tools/melody.py out/catalan/prosody.txt -c base  against what was kept

The file is `kind|text' a line, and a kind is any word: stmt, yesno, wh,
comma. Lines beginning with a hash are ignored. `-n' does not rebuild.
"""

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import pitch                                             # noqa: E402
import speak                                             # noqa: E402

# The numbers that say what a melody is doing. The rest of pitch.py's line is
# either about the recording (seconds, voiced) or about the speaker (median).
KEEP = ["span", "top", "bottom", "declination", "onset", "tail", "move",
        "peaks", "peak_height", "syllables", "gap", "variability",
        "before_pause"]


def before_pause(frames):
    """How high the voice is left at an internal break.

    The sentence-final numbers say nothing about a comma, because the last
    half second of a sentence with a comma in it is still the full stop. What
    a comma does is a separate question -- Catalan raises the voice at the
    right edge of a phrase that is not the last, where a full stop lowers it
    -- and this is where that can be read: the pitch over the eighty
    milliseconds before each silence in the middle, in semitones from the
    utterance's own median.

    A silence is a run of at least a tenth of a second with no pitch in it.
    That is longer than any stop closure the engine makes and shorter than
    the pause it puts at a comma. A sentence with no such break answers
    nothing rather than nought, which is not the same thing.
    """
    v = [(t, f) for t, f, _rms, _r in frames if f]
    if len(v) < 8:
        return None
    mid = pitch.median([f for _t, f in v])
    at = [t for t, f, _rms, _r in frames if f]
    gaps = []
    for i in range(1, len(at)):
        if at[i] - at[i - 1] >= 0.10:
            gaps.append(at[i - 1])
    # The last voiced stretch is the sentence end, not a break in the middle,
    # and a break in the first fifth is a stop rather than a phrase.
    gaps = [g for g in gaps if g > at[0] + 0.20 and g < at[-1] - 0.20]
    if not gaps:
        return None
    out = []
    for g in gaps:
        near = [f for t, f in v if g - 0.08 <= t <= g]
        if near:
            out.append(pitch.semitones(pitch.median(near), mid))
    return sum(out) / len(out) if out else None


def cases(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, text = line.partition("|")
        if text:
            out.append((kind.strip(), text.strip()))
    return out


def measure(exe, kind, i, text):
    wav = os.path.join(ROOT, "out", "mel-%s-%02d.wav" % (kind, i))
    src = speak.write_text(text)
    subprocess.run([exe, "-f", src, "-o", wav], cwd=ROOT,
                   env=speak.environ(), check=True,
                   capture_output=True)
    rate, xs = pitch.read_wav(wav)
    frames = pitch.contour(rate, xs)
    s = pitch.summary(frames)
    if s:
        b = before_pause(frames)
        s["before_pause"] = b if b is not None else float("nan")
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="?", default="out/catalan/prosody.txt")
    ap.add_argument("-l", "--lang", default="caes")
    ap.add_argument("-j", "--jobs", type=int, default=8)
    ap.add_argument("-n", "--no-build", action="store_true")
    ap.add_argument("-o", "--save", help="keep these numbers under a name")
    ap.add_argument("-c", "--against", help="print the change since that name")
    a = ap.parse_args()

    if not a.no_build:
        sys.stderr.write("building %s ... " % a.lang)
        sys.stderr.flush()
        speak.build(a.lang, a.jobs, False)
        sys.stderr.write("done\n")

    exe = speak.engine()
    by = {}
    for i, (kind, text) in enumerate(cases(os.path.join(ROOT, a.cases))):
        s = measure(exe, kind, i, text)
        if s:
            by.setdefault(kind, []).append(s)
        else:
            sys.stderr.write("melody: too little voice in %r\n" % text)

    now = {}
    for kind, rows in by.items():
        now[kind] = {}
        for k in KEEP:
            have = [r[k] for r in rows if r[k] == r[k]]     # nan is not itself
            now[kind][k] = sum(have) / len(have) if have else float("nan")
        now[kind]["n"] = len(rows)

    was = {}
    if a.against:
        p = os.path.join(ROOT, "out", "melody-%s.json" % a.against)
        if os.path.exists(p):
            was = json.load(open(p))
        else:
            sys.stderr.write("melody: no %s kept\n" % p)

    for kind in sorted(now):
        print("%s  (%d sentences)" % (kind, now[kind]["n"]))
        for k in KEEP:
            line = "   %-12s %7.2f" % (k, now[kind][k])
            if kind in was:
                d = now[kind][k] - was[kind][k]
                line += "   %+7.2f" % d
            print(line)

    if a.save:
        p = os.path.join(ROOT, "out", "melody-%s.json" % a.save)
        json.dump(now, open(p, "w"), indent=1, sort_keys=True)
        sys.stderr.write("kept in %s\n" % os.path.relpath(p, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
