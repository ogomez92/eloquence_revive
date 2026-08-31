#!/usr/bin/env python3
"""A language's lookup sets as the words they hold, and back again.

A set is a list of words the rules ask a token about. `span_funct_words' tries
the first ten in turn -- the determiners, the three lengths of preposition, the
two kinds of conjunction, the object and possessive pronouns, the relatives and
the demonstratives -- and a word found in any of them is marked a function word
rather than a content word, which is what decides whether it is given a stress
at all. The rest are asked about by name, one rule at a time.

They are in `lang/<tag>/<tag>.sets' as bytes, which is how the lifter found
them: one code per character of the language's own alphabet, a nul after each
word, the whole run sorted by those codes because the engine binary-searches it
and gives up on a run that is out of order. Reading that by eye and writing it
by hand is how a word quietly stops being found, so this reads and writes them
by name.

    lang-sets.py show <tag>                 every set and what is in it
    lang-sets.py show <tag> <set>...        only the ones named, by name or number
    lang-sets.py set <tag> <set> <word>...  give a set these words and no others
    lang-sets.py check <tag>                every set well formed, file unchanged

A set that still fits where it was is written back there and the bytes it no
longer needs are cleared; one that has outgrown its place goes at the end of
the store instead, and only its own offset moves. Nothing else in the file is
touched, because the placings are IBM's compiler's rather than a rule anyone
here knows: the sets are not evenly spaced, the gaps between them run from
nought to seven, and laying the whole store out again would be guessing at
what put them there.

A word is written as its characters. Where the alphabet has no character for a
code, `#<number>' names it; a space inside a word is what the two-word sets
hold and wants the word quoted.

Nothing here says what a set means. That is in the rules that ask about it, and
`tools/delta-decompile.py' is what reads those.
"""

import os
import re
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# One set's table entry, as tools/delta-sets.py lays it: the store it names,
# the statement type its characters belong to, how many words, how many bytes.
ENTRY = 0x24
E_STMT = 0x08
E_COUNT = 0x0c
E_BYTES = 0x10

# What a set put at the end of the store starts on. IBM's own are not all on
# one boundary, so this is what a new placing uses and never a rule read back
# off the file.
ALIGN = 8

# How many bytes to a line, which is what delta-sets.py writes and what this
# has to keep so that a file it has not changed comes back the same.
PER_LINE = 32


class Sets(object):
    """The file, kept as its lines, with the three blocks that say what the
    sets are pulled out of it. Everything else -- the comment, the streams,
    the dictionary, the actions -- is held as it was read and written back
    untouched, because none of it is this tool's business."""

    def __init__(self, tag):
        self.tag = tag
        self.path = os.path.join(ROOT, "lang", tag, "%s.sets" % tag)
        with open(self.path, encoding="utf-8", newline="") as f:
            self.lines = f.readlines()
        # Whatever the file already ends its lines with. delta-sets.py writes
        # with the platform's, so a tree made on Windows has one and a tree
        # made on Linux the other, and a tool that imposed either would report
        # every line as changed on the other.
        self.eol = "\r\n" if self.lines[0].endswith("\r\n") else "\n"
        self.table = bytearray()
        self.store = bytearray()
        self.at = []
        self.where = {}
        for kind, prefix in (("table", "table set "),
                             ("store", "store set "),
                             ("at", "at set ")):
            rows = [i for i, l in enumerate(self.lines) if l.startswith(prefix)]
            if not rows:
                raise SystemExit("lang-sets: %s has no %s lines" % (tag, prefix))
            if rows != list(range(rows[0], rows[-1] + 1)):
                raise SystemExit("lang-sets: %s's %s lines are not together"
                                 % (tag, prefix))
            self.where[kind] = (rows[0], rows[-1] + 1)
            for i in rows:
                p = self.lines[i].split()
                if kind == "at":
                    self.at.append([int(p[2]), p[3], int(p[4])])
                else:
                    getattr(self, kind).extend(int(x, 16) for x in p[2:])

    # ---- what the table says about one set ------------------------------

    def num(self, slot, off):
        return struct.unpack_from("<i", self.table, slot * ENTRY + off)[0]

    def put_num(self, slot, off, value):
        struct.pack_into("<i", self.table, slot * ENTRY + off, value)

    def keys(self, which):
        slot, _name, off = self.at[which]
        n = self.num(slot, E_BYTES)
        return [k for k in bytes(self.store[off:off + n]).split(b"\0") if k]

    def room(self, which):
        """How much of the store this set may fill: up to wherever the next
        one begins, and to the end for whichever comes last."""
        off = self.at[which][2]
        after = [o for _s, _n, o in self.at if o > off]
        return (min(after) if after else len(self.store)) - off

    # ---- and back to lines ----------------------------------------------

    def rendered(self):
        out = list(self.lines)
        for kind, data in (("table", self.table), ("store", self.store)):
            rows = ["%s set %s%s" % (kind, " ".join(
                "%02x" % b for b in data[i:i + PER_LINE]), self.eol)
                for i in range(0, len(data), PER_LINE)]
            out[self.where[kind][0]:self.where[kind][1]] = rows
            self._shift(kind, len(rows))
        rows = ["at set %d %s %d%s" % (s, n, o, self.eol)
                for s, n, o in self.at]
        out[self.where["at"][0]:self.where["at"][1]] = rows
        self._shift("at", len(rows))
        return out

    def _shift(self, kind, n):
        """A block that has changed length moves the ones after it."""
        lo, hi = self.where[kind]
        by = n - (hi - lo)
        self.where[kind] = (lo, lo + n)
        if by:
            for other in self.where:
                a, b = self.where[other]
                if a > lo:
                    self.where[other] = (a + by, b + by)

    def write(self):
        rows = self.rendered()
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.writelines(rows)
        self.lines = rows


def alphabet(tag, stmt):
    """Code to character, out of the statement's own value names.

    Every set in the nine languages is over the input alphabet, but the
    statement is carried through rather than assumed, so a set over some other
    one says so instead of being read with the wrong names."""
    if stmt != 1:
        raise SystemExit("lang-sets: that set is over statement %d, not the"
                         " input alphabet; nothing here can name its"
                         " characters" % stmt)
    got = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "lang-alphabet.py"),
         "show", tag],
        capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONUTF8="1"))
    if got.returncode != 0:
        sys.stderr.write(got.stderr or "")
        raise SystemExit("lang-sets: cannot read %s's alphabet" % tag)
    m = {}
    for line in (got.stdout or "").splitlines():
        g = re.match(r"\s*(\d+)\s+(.*?)\s+letcase=", line)
        if g:
            name = g.group(2)
            m[int(g.group(1))] = " " if name == "' '" else name
    return m


def spell(key, alpha):
    return "".join(alpha.get(c, "#%d" % c) for c in key)


def encode(word, alpha):
    back = {}
    for code, name in sorted(alpha.items()):
        back.setdefault(name, code)
    out, i = bytearray(), 0
    while i < len(word):
        g = re.match(r"#(\d+)", word[i:])
        if g:
            out.append(int(g.group(1)))
            i += g.end()
            continue
        if word[i] not in back:
            raise SystemExit("lang-sets: %r, in %r, is not in the alphabet"
                             % (word[i], word))
        out.append(back[word[i]])
        i += 1
    if not out:
        raise SystemExit("lang-sets: a set cannot hold an empty word")
    return bytes(out)


def pick(s, want):
    for i, (slot, name, _off) in enumerate(s.at):
        if want in (name, str(slot)) or name == want + "_setentries":
            return i
    raise SystemExit("lang-sets: no set called %s" % want)


def show(s, wanted):
    for i, (slot, name, _off) in enumerate(s.at):
        if wanted and not any(w in (name, str(slot))
                              or name == w + "_setentries" for w in wanted):
            continue
        alpha = alphabet(s.tag, s.table[slot * ENTRY + E_STMT])
        ws = [spell(k, alpha) for k in s.keys(i)]
        print("set %-3d %-32s %d words" % (slot, name, len(ws)))
        if ws:
            print("   " + "  ".join(ws))


def check(s):
    """Every set the shape the engine's search needs, and the file the same
    file afterwards. The search backs up to the nul before wherever it lands
    and gives up when an entry comes round twice, so an unsorted run finds
    some of its words and not others rather than failing outright -- which is
    why the order is checked here and not left to be heard."""
    bad = 0
    for i, (slot, name, _off) in enumerate(s.at):
        ks = s.keys(i)
        if len(ks) != s.num(slot, E_COUNT):
            print("set %d %s says %d words and holds %d"
                  % (slot, name, s.num(slot, E_COUNT), len(ks)))
            bad += 1
        if sum(len(k) + 1 for k in ks) != s.num(slot, E_BYTES):
            print("set %d %s says %d bytes and its words are %d"
                  % (slot, name, s.num(slot, E_BYTES),
                     sum(len(k) + 1 for k in ks)))
            bad += 1
        if [list(k) for k in ks] != sorted(list(k) for k in ks):
            print("set %d %s is not in the order the engine searches"
                  % (slot, name))
            bad += 1
    if s.rendered() != s.lines:
        print("%s.sets is not written back as it was read" % s.tag)
        bad += 1
    if bad:
        raise SystemExit("lang-sets: %d thing%s wrong"
                         % (bad, "" if bad == 1 else "s"))
    print("%s: %d sets, %d words, %d bytes, all in order and unchanged"
          % (s.tag, len(s.at),
             sum(s.num(slot, E_COUNT) for slot, _n, _o in s.at), len(s.store)))


def put(s, which, given):
    slot, name, off = s.at[which]
    alpha = alphabet(s.tag, s.table[slot * ENTRY + E_STMT])
    ks = sorted(set(encode(w, alpha) for w in given), key=list)
    blob = b"".join(k + b"\0" for k in ks)
    have = s.room(which)

    if len(blob) <= have:
        s.store[off:off + have] = blob + bytes(have - len(blob))
        where = "where it was"
    else:
        while len(s.store) % ALIGN:
            s.store.append(0)
        off = len(s.store)
        s.at[which][2] = off
        s.store += blob
        while len(s.store) % ALIGN:
            s.store.append(0)
        where = "at %d, past the end of the room it had" % off

    s.put_num(slot, E_COUNT, len(ks))
    s.put_num(slot, E_BYTES, len(blob))
    s.write()
    print("set %d %s: %d words in %d bytes, %s; the store is %d"
          % (slot, name, len(ks), len(blob), where, len(s.store)))


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mode, tag = sys.argv[1], sys.argv[2]
    s = Sets(tag)

    if mode == "show":
        show(s, sys.argv[3:])
    elif mode == "check":
        check(s)
    elif mode == "set":
        if len(sys.argv) < 5:
            raise SystemExit("lang-sets: `set' wants a set and its words")
        put(s, pick(s, sys.argv[3]), sys.argv[4:])
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
