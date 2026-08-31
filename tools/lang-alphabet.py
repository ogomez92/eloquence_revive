#!/usr/bin/env python3
"""A language's alphabet, and what each character of it is.

The alphabet is the value names of the input statement's first field, and
beside it in the same statement is a record for every one of those names: what
case the character is, whether it is a letter or a digit or punctuation,
whether it is a vowel or a consonant or a glide, whether it carries an accent,
and the phoneme it stands for on its own. Which is letter-to-sound at its
simplest, and it is data rather than code.

Both are in `lang/<tag>/<tag>.statements`, the alphabet as `value' lines and
the records as the `variants' bytes of the same statement -- one record of five
bytes per name, in the order the names are in. Reading those bytes by eye and
writing them by hand is how a letter quietly comes out as a digit, so this
reads and writes them by name.

    lang-alphabet.py show <tag>              every character and what it is
    lang-alphabet.py show <tag> <char>...    only the ones named
    lang-alphabet.py add <tag> <byte> <field>=<value>...
    lang-alphabet.py set <tag> <char> <field>=<value>...

`add' puts a character at a byte value nothing in the alphabet claims yet, so
that no existing code changes meaning: the dictionaries are keyed by these
codes and moving one would move every word that used it. The byte is what the
engine will see for that character once it arrives, in hex.

    lang-alphabet.py add plpl b1 case=lower type=letter letter=vow \\
                              accent='~yes' phoneme=a

usage: as above; `show' with no character lists the lot
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Which statement holds the characters. What a record carries is not fixed
# and must not be assumed: it is the statement's own fields after the name,
# less `afterslash' where there is one, as many of them as `at start stride'
# says. That number is 3 in the two Englishes and German, 4 in the Frenches
# and both Spanishes and 5 in Italian, so a tool that assumes one of them
# misreads six of the nine languages -- every record after the first by a
# little more, until a vowel reads as a consonant and nothing says so.
STATEMENT = "inp"
NL = chr(10)


def path_of(tag):
    return os.path.join(ROOT, "lang", tag, "%s.statements" % tag)


def read(tag):
    """The statement's lines, its alphabet, its field values and its records.

    The file is kept as its lines so that writing it back changes only what
    was asked for: everything else, including every other statement, goes
    back exactly as it came.
    """
    lines = open(path_of(tag)).read().split("\n")
    first = last = None
    names = []
    values = {}
    fields = []
    field = None
    stride = None
    variants = bytearray()
    var_at = []

    for i, line in enumerate(lines):
        if line == "statement %s" % STATEMENT:
            first = i
            continue
        if first is not None and last is None:
            if line.startswith("statement ") or line == "end":
                last = i
                continue
            w = line.split()
            if line.startswith("  field "):
                field = w[1]
                fields.append(field)
                values.setdefault(field, [])
            elif w[:3] == ["at", "start", "stride"]:
                stride = int(w[3])
            elif line.startswith("    value") and field:
                text = line[len("    value"):]
                text = text[1:] if text.startswith(" ") else text
                text = text.replace("\\s", " ").replace("\\\\", "\\")
                values[field].append(text)
                if field == "name":
                    names.append(text)
            elif w and w[0] == "variants":
                var_at.append(i)
                variants += bytes(int(x, 16) for x in w[1:])
    if first is None:
        raise SystemExit("lang-alphabet: %s has no %s statement"
                         % (tag, STATEMENT))
    if stride is None:
        raise SystemExit("lang-alphabet: %s says no stride for %s"
                         % (tag, STATEMENT))
    record = [f for f in fields
              if f not in ("name", "afterslash")][:stride]
    return (lines, first, last, names, values, bytes(variants), var_at,
            stride, record)


def named(values, field, v):
    table = values.get(field, [])
    return table[v] if 0 <= v < len(table) else str(v)


def number(values, field, text):
    table = values.get(field, [])
    if text in table:
        return table.index(text)
    raise SystemExit("lang-alphabet: %s has no value called %r; it has %s"
                     % (field, text, ", ".join(table)))


def show(tag, want):
    _l, _f, _t, names, values, variants, _at, stride, record = read(tag)
    print("%s: %d characters, %d bytes of records, %d to a record"
          % (tag, len(names), len(variants), stride))
    for code, ch in enumerate(names):
        if want and ch not in want:
            continue
        r = variants[code * stride:code * stride + stride]
        if len(r) < stride:
            print("%3d  %-4s no record" % (code, ch))
            continue
        print("%3d  %-4s %s"
              % (code, ch if ch.strip() else "' '",
                 " ".join("%s=%s" % (f, named(values, f, r[i]))
                          for i, f in enumerate(record))))
    return True


def set_record(tag, char, args):
    """Change named fields of one character's record, writing everything else
    back exactly as it came."""
    lines, _f, _t, names, values, variants, var_at, stride, record = read(tag)
    if char not in names:
        raise SystemExit("lang-alphabet: %s has no character %r"
                         % (tag, char))
    code = names.index(char)
    at = code * stride
    if at + stride > len(variants):
        raise SystemExit("lang-alphabet: %r has no record" % char)
    rec = bytearray(variants[at:at + stride])
    for a in args:
        if "=" not in a:
            raise SystemExit("lang-alphabet: %r is not field=value" % a)
        k, v = a.split("=", 1)
        if k not in record:
            raise SystemExit("lang-alphabet: a record has no %r; it has %s"
                             % (k, ", ".join(record)))
        rec[record.index(k)] = number(values, k, v)
    var = bytearray(variants)
    var[at:at + stride] = rec
    out = ["  variants " + " ".join("%02x" % b for b in var[i:i + 32])
           for i in range(0, len(var), 32)]
    lines[min(var_at):max(var_at) + 1] = out
    open(path_of(tag), "w").write(NL.join(lines))
    print("%s: %s is now %s"
          % (tag, char, ", ".join("%s %s" % (f, named(values, f, rec[i]))
                                  for i, f in enumerate(record))))
    return True


def add(tag, byte, args):
    (lines, first, last, names, values, variants, var_at,
     stride, RECORD) = read(tag)
    want = {}
    for a in args:
        if "=" not in a:
            raise SystemExit("lang-alphabet: %r is not field=value" % a)
        k, v = a.split("=", 1)
        if k not in RECORD:
            raise SystemExit("lang-alphabet: a record has no %r; it has %s"
                             % (k, ", ".join(RECORD)))
        want[k] = v
    for k in RECORD:
        if k not in want:
            raise SystemExit("lang-alphabet: say what its %s is" % k)

    ch = bytes([int(byte, 16)]).decode("latin-1")
    if ch in names:
        raise SystemExit("lang-alphabet: %s already has that character, as"
                         " code %d" % (tag, names.index(ch)))
    if len(variants) < len(names) * stride:
        raise SystemExit("lang-alphabet: %d names want %d bytes of records"
                         " and there are %d"
                         % (len(names), len(names) * stride, len(variants)))

    record = bytes(number(values, k, want[k]) for k in RECORD)
    written = ch.replace("\\", "\\\\").replace(" ", "\\s")

    # The name goes after the last one of the field it belongs to, and the
    # record after the last of the records, so every code that exists keeps
    # the meaning it had.
    at_name = max(i for i in range(first, last)
                  if lines[i].startswith("    value")
                  and i < min([j for j in range(first, last)
                               if lines[j].startswith("  field ")
                               and lines[j].split()[1] != "name"]
                              or [last]))
    lines.insert(at_name + 1, "    value %s" % written)

    at_var = max(j for j in var_at) + 1        # the line after the last one
    lines.insert(at_var, "  variants %s"
                 % " ".join("%02x" % b for b in record))

    open(path_of(tag), "w").write("\n".join(lines))
    print("%s: %s is code %d now, %s"
          % (tag, ch, len(names),
             ", ".join("%s %s" % (k, want[k]) for k in RECORD)))
    return True


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    what, tag = argv[0], argv[1]
    if what == "show":
        return 0 if show(tag, set(argv[2:])) else 1
    if what == "add" and len(argv) > 2:
        return 0 if add(tag, argv[2], argv[3:]) else 1
    if what == "set" and len(argv) > 3:
        return 0 if set_record(tag, argv[2], argv[3:]) else 1
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
