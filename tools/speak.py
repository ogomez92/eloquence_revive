#!/usr/bin/env python3
"""Build the voice as it stands and say something in it.

This is the loop for working on a language by ear. Change a formant, a letter
rule, an intonation number or a word in the dictionary, run this, and hear the
result -- it rebuilds whatever the change needs and writes a wave file, and it
says what the words came out as so that a wrong sound can be told from a wrong
letter-to-sound before anybody argues about it.

    python tools/speak.py "Bon dia. Com estas?"
    python tools/speak.py -o hello.wav "Bon dia"
    python tools/speak.py -v 3 "Bon dia"          in voice three
    python tools/speak.py -n "Bon dia"            do not rebuild, just speak
    python tools/speak.py -t "Bon dia"            rebuild the tables too
    python tools/speak.py -p "casa dia caixa"     the phonemes, and no wave
    python tools/speak.py -m "La casa es gran."   what the melody measures

The text is written out as UTF-8, which is what the accents want: the grave
accents are converted on the way in and that conversion only looks at text
that really is UTF-8. Passing it on the command line is fine -- it is put in a
file before the engine sees it.

    -l <tag>   which language, caes by default
    -t         run tables-write first, which is what a change to <tag>.statements,
               <tag>.settings, <tag>.globals or <tag>.dict needs
    -n         skip the build entirely
    -j <n>     how many compiler jobs, eight by default

What it rebuilds without being asked: the authored constants out of
rules/constants, the rules out of the text with the upper form in, and then
the engine. That covers a change to any .up file, to rules/constants, or to a
.dr edited in place. RULES=bytecode is used because it builds in half a minute
where the rules-as-C build is a quarter of an hour, and the two speak the same
samples.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The words printed back carry accents, and a Windows console is not UTF-8
# unless it is told. Without this a grave comes back as a question mark and
# the reading looks wrong when it is right.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def make_program():
    """What make is called here. Windows has it under a longer name, and a
    tree without either is a tree that cannot build at all."""
    for name in ("mingw32-make", "make", "gmake"):
        if shutil.which(name):
            return name
    raise SystemExit("speak: no make found; tried mingw32-make, make, gmake")


_PATH_HEAD = None


def path_head():
    """The two directories a Windows shell has to have in front of it, and
    outside Git Bash does not.

    make runs a recipe through cmd.exe unless it can find sh.exe on the path,
    and every recipe here is written for a shell -- `mkdir -p', a test in
    brackets, a redirection to /dev/null -- so from PowerShell the build stops
    at "the syntax of the command is incorrect" before it has compiled
    anything. And the engine imports libwinpthread-1.dll, which several
    unrelated programs also ship: the first one on the path wins, and an older
    one fails the load with STATUS_ENTRYPOINT_NOT_FOUND before main is
    reached. Putting the compiler's own directory first means the DLL loaded
    is the one it was linked against.

    Neither is a thing to set up by hand once, because the path a shell hands
    us is not ours to keep; it is worked out per run and put in front."""
    global _PATH_HEAD
    if _PATH_HEAD is not None:
        return _PATH_HEAD
    dirs = []
    if os.name == "nt":
        cc = shutil.which(os.environ.get("CC") or "gcc")
        if cc:
            dirs.append(os.path.dirname(cc))
        # sh.exe by that name and no other: bash is not a fallback, because
        # the bash on a stock Windows path is WSL's stub in system32, and
        # make wants an sh.exe in a directory it can find one in.
        sh = shutil.which("sh")
        if not sh:
            git = shutil.which("git")
            roots = []
            if git:
                roots.append(os.path.dirname(os.path.dirname(git)))
            roots += [r"C:\Program Files\Git", r"C:\msys64"]
            for root in roots:
                cand = os.path.join(root, "usr", "bin", "sh.exe")
                if os.path.exists(cand):
                    sh = cand
                    break
        if sh:
            dirs.append(os.path.dirname(sh))
    _PATH_HEAD = dirs
    return dirs


def environ(extra=None):
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    head = path_head()
    if head:
        e["PATH"] = os.pathsep.join(head + [e.get("PATH", "")])
    if extra:
        e.update(extra)
    return e


def run(cmd, env=None, quiet=True):
    e = environ(env)
    r = subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True, text=True,
                       errors="replace")
    if r.returncode != 0:
        sys.stderr.write(r.stdout or "")
        sys.stderr.write(r.stderr or "")
        raise SystemExit("speak: %s failed" % " ".join(cmd[:3]))
    return (r.stdout or "") + (r.stderr or "")


def build(tag, jobs, tables):
    """Everything a change to the language might need, in the order the tools
    want it. delta-dict.py writes into the generated rules as well as the
    tables, so `authored' has to come after the tables and before the build,
    or a rewritten dictionary entry is lost."""
    py = sys.executable
    make = make_program()
    lang = "lang/%s" % tag
    steps = []
    if tables:
        steps.append(([make, "LANGS=" + lang, "tables-write"], None))
    steps += [
        ([py, "tools/delta-consts.py", tag], None),
        ([py, "tools/delta-notation.py", "authored"],
         {"EVV_NOTATION_LANG": tag}),
        ([make, "RULES=bytecode", "CC=gcc", "LANGS=" + lang,
          "-j%d" % jobs], None),
    ]
    for cmd, env in steps:
        run(cmd, env)


def engine():
    for name in ("build/evv.exe", "build/evv"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            return p
    raise SystemExit("speak: no build/evv; build it first")


def write_text(text):
    p = os.path.join(ROOT, "out", "speak-in.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n")
    return p


PHONE = re.compile(r"(cat_ph_schwa_vals|cat_ph_eopen_vals|cat_ph_oopen_vals"
                   r"|(?:stan)?[a-z]+_ph_[A-Za-z]+(?:_dur)?)")
SHOWN = {"cat_ph_schwa_vals": "@", "cat_ph_eopen_vals": "E",
         "cat_ph_oopen_vals": "O"}


def phonemes(exe, path):
    """What the language decided the words are made of, out of a rule trace.
    A phoneme rule is entered once per segment it lays down, so a run of one
    name is one phoneme; T forwards to n and is shown as the n it is."""
    e = environ({"DELTA_RULE_TRACE": "1"})
    r = subprocess.run([exe, "-f", path, "-o", os.devnull], cwd=ROOT, env=e,
                       capture_output=True, text=True, errors="replace")
    out, last = [], None
    for m in PHONE.finditer(r.stderr or ""):
        name = m.group(1)
        if name.endswith("_dur"):
            continue
        name = SHOWN.get(name) or re.sub(r".*_ph_", "", name)
        if name == "T":
            name = "n"
        if name != last:
            out.append(name)
        last = name
    return " ".join(out)


def melody(wav):
    r = subprocess.run([sys.executable, "tools/pitch.py", wav], cwd=ROOT,
                       capture_output=True, text=True, errors="replace")
    m = re.search(r"span ([-\d.]+).*declination ([-\d.]+).*tail ([-\d.]+)"
                  r".*peak_height ([-\d.]+)", r.stdout or "")
    if not m:
        return None
    return ("range %s semitones, declination %s, terminal fall %s,"
            " accents %s tall" % m.groups())


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    ap.add_argument("text", nargs="*", help="what to say")
    ap.add_argument("-o", "--out", default="out/speak.wav")
    ap.add_argument("-l", "--lang", default="caes")
    ap.add_argument("-v", "--voice", type=int, default=0)
    ap.add_argument("-j", "--jobs", type=int, default=8)
    ap.add_argument("-n", "--no-build", action="store_true")
    ap.add_argument("-t", "--tables", action="store_true")
    ap.add_argument("-p", "--phonemes", action="store_true")
    ap.add_argument("-m", "--melody", action="store_true")
    a = ap.parse_args()

    text = " ".join(a.text) if a.text else sys.stdin.read()
    if not text.strip():
        raise SystemExit("speak: nothing to say")

    if not a.no_build:
        sys.stderr.write("building %s ... " % a.lang)
        sys.stderr.flush()
        build(a.lang, a.jobs, a.tables)
        sys.stderr.write("done\n")

    exe = engine()
    src = write_text(text)

    if a.phonemes:
        for line in text.splitlines() or [text]:
            for word in line.split():
                p = write_text(word)
                print("%-18s %s" % (word, phonemes(exe, p)))
        return 0

    out = a.out if os.path.isabs(a.out) else os.path.join(ROOT, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [exe, "-f", src, "-o", out]
    if a.voice:
        cmd[1:1] = ["-v", str(a.voice)]
    subprocess.run(cmd, cwd=ROOT, env=environ(), check=True)

    import wave
    with wave.open(out) as w:
        secs = w.getnframes() / float(w.getframerate())
    print("%s  %.2f s" % (os.path.relpath(out, ROOT), secs))
    print("   %s" % phonemes(exe, src))
    if a.melody:
        m = melody(out)
        if m:
            print("   %s" % m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
