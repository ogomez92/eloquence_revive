#!/usr/bin/env python3
"""The bytecode back into the lower notation, so a module can be edited
without IBM's objects.

`delta-notation.py tree' writes a language's rules as text by lifting IBM's
objects. That is the only step in making a language that needs them, and a
tree that has the generated C but not the SDK cannot take it -- which is
every tree, since analysis/ is not in it.

But nothing is lost in the emitter. `delta-emit.py' turns operations into
bytecode, and the mapping is one to one: every operand kind, every opcode and
every pool index can be read back. So this inverts it. It reads
delta_rules_<tag>.c -- the bytecode, the pools and the rule table, all of
which are in the tree -- and writes the same lang/<tag>/rules a lift would
have written.

Two things are not in the bytecode and are named here, which is sound because
neither is anything but a name:

  A symbol is a pool entry that write_c turns into `<store> + <offset>'.
  Which name the object gave it is gone, and nothing downstream cares: what a
  rule holds is the pool index and what the C holds is the store and the
  offset. So each entry is named sym_<n> and rules/symbols records it against
  the store and offset the C already says. The pair a rule names is (object,
  symbol), so the object is the one whose rule reached the entry first, which
  is what numbered it.

  A map table is a run of bytes in delta_rule_map[] and a MAP names its
  offset. Where one ends is not recorded and does not have to be: the emitter
  appends each table whole at first use, so the distinct offsets in
  increasing order partition the array exactly.

Proof is not by argument. Written out, `delta-notation.py regenerate' emits
the whole module again from this text and holds it against the tree's own
delta_rules_<tag>.c byte for byte. If that says the same, the text is the
bytecode and nothing about it is a guess.

usage: delta-unemit.py <tag>
"""

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name,
                                                  os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dlo = load("delta_lower", "tools/delta-lower.py")

# The opcodes, the conditions and the kinds, in the order delta-emit.py
# numbers them. A copy rather than an import because that module reads an
# object at import time; if the two ever disagree the round trip says so at
# once, which is the only check either list needs.
OPS = ["call", "jump", "branch", "cmp", "alu2", "alu1", "load", "store",
       "switch", "map", "return", "scale", "addk", "mul", "div", "widen",
       "setcc", "push", "setarg", "popn", "popreg", "ftol"]

CONDS = ["e", "ne", "a", "ae", "b", "be", "g", "ge", "l", "le", "s", "ns"]
CMPS = ["testl", "testw", "testb", "cmpl", "cmpw", "cmpb"]
ALUS = ["addl", "addw", "subl", "subw", "andl", "andw", "orl", "orw",
        "incl", "incw", "decl", "decw", "shll", "shlw", "sarl", "sarw",
        "negl", "negw", "sbbl", "imull", "imulw"]
MOVS = ["movl", "movw", "movb", "movswl", "movzwl", "movsbl", "movzbl"]
FSTEPS = ["ld", "addi", "mulk", "addk"]

REG_FULL = ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi")
REG_W = ("ax", "cx", "dx", "bx", "sp", "bp", "si", "di")
REG_B = ("al", "cl", "dl", "bl")
REG_H = ("ah", "ch", "dh", "bh")


def reg_name(code):
    """A register byte as the name delta-lower writes. The width is the high
    nibble, which is where reg_code put it."""
    n, w = code & 0x0f, code >> 4
    if w == 0:
        return REG_FULL[n]
    if w == 1:
        return REG_W[n]
    if w == 2:
        return REG_B[n]
    if w == 3:
        return REG_H[n]
    raise ValueError("register byte 0x%02x" % code)


# ---- reading the generated C --------------------------------------------


def body_of(text, name):
    m = re.search(r"\b%s\[\]\s*=\s*\{(.*?)\n\};" % re.escape(name), text,
                  re.S)
    if m is None:
        raise SystemExit("delta-unemit: no %s in the generated C" % name)
    return m.group(1)


def numbers(text, name):
    return [int(x, 0) for x in body_of(text, name).replace("\n", "").split(",")
            if x.strip()]


def strings(text, name):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', body_of(text, name))


def syms(text, name):
    """Each pool entry as (store, offset). A bare store is offset nought."""
    out = []
    for raw in body_of(text, name).split(","):
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\+\s*(\d+)$", s)
        if m:
            out.append((m.group(1), int(m.group(2))))
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)$", s)
        if m:
            out.append((m.group(1), 0))
            continue
        raise SystemExit("delta-unemit: cannot read the symbol %r" % s)
    return out


def rule_table(text, name):
    out = []
    pattern = (r'\{\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*'
               r'(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,'
               r'\s*(-?\d+)\s*\}')
    for m in re.finditer(pattern, body_of(text, name)):
        out.append((m.group(1), m.group(2))
                   + tuple(int(m.group(i)) for i in range(3, 8)))
    return out


# ---- decoding ------------------------------------------------------------


class Decoder:
    def __init__(self, code, imm, entries, symnames):
        self.code = code
        self.imm = imm
        self.entries = entries
        self.symnames = symnames
        self.used_syms = []

    def u8(self, p):
        return self.code[p], p + 1

    def u16(self, p):
        return self.code[p] | (self.code[p + 1] << 8), p + 2

    def s16(self, p):
        v = self.code[p] | (self.code[p + 1] << 8)
        return (v - 0x10000 if v & 0x8000 else v), p + 2

    def operand(self, p):
        k = self.code[p]
        p += 1
        if k == 0:
            return None, p
        if k == 1:
            i, p = self.u16(p)
            return ("imm", self.imm[i]), p
        if k == 2:
            i, p = self.u16(p)
            self.used_syms.append(i)
            return ("sym", self.symnames[i]), p
        if k in (3, 4, 5, 6):
            kind = ("slot", "slotaddr", "state", "statefld")[k - 3]
            v, p = self.s16(p)
            return (kind, v), p
        if k == 7:
            c, p = self.u8(p)
            return ("reg", reg_name(c)), p
        if k == 8:
            inner, p = self.operand(p)
            d, p = self.s16(p)
            return ("indirect", inner, d), p
        raise ValueError("operand kind %d at %d" % (k, p - 1))

    def insn(self, p):
        """One operation, where the next begins, and the places it can go.
        A target is a byte offset from the rule's start, which is what the
        emitter patched in."""
        op = OPS[self.code[p]]
        p += 1
        targets = []

        if op == "call":
            i, p = self.u16(p)
            a, p = self.u8(p)
            d, p = self.u8(p)
            return ("call", self.entries[i], a, d), p, targets
        if op == "jump":
            t, p = self.u16(p)
            targets.append(t)
            return ("jump", t), p, targets
        if op == "branch":
            c, p = self.u8(p)
            t, p = self.u16(p)
            targets.append(t)
            return ("branch", "j" + CONDS[c], t), p, targets
        if op == "cmp":
            k, p = self.u8(p)
            a, p = self.operand(p)
            b, p = self.operand(p)
            return ("cmp", CMPS[k], a, b), p, targets
        if op == "alu2":
            k, p = self.u8(p)
            a, p = self.operand(p)
            b, p = self.operand(p)
            return ("alu", ALUS[k], a, b), p, targets
        if op == "alu1":
            k, p = self.u8(p)
            a, p = self.operand(p)
            return ("alu", ALUS[k], None, a), p, targets
        if op == "load":
            k, p = self.u8(p)
            a, p = self.operand(p)
            r, p = self.u8(p)
            return ("load", MOVS[k], a, reg_name(r)), p, targets
        if op == "store":
            k, p = self.u8(p)
            a, p = self.operand(p)
            b, p = self.operand(p)
            return ("store", MOVS[k], a, b), p, targets
        if op == "switch":
            a, p = self.operand(p)
            n, p = self.u16(p)
            ts = []
            for _ in range(n):
                t, p = self.u16(p)
                ts.append(t)
                targets.append(t)
            return ("switch", ts, a), p, targets
        if op == "map":
            off, p = self.u16(p)
            a, p = self.operand(p)
            r, p = self.u8(p)
            return ("map", off, a, reg_name(r)), p, targets
        if op == "return":
            a, p = self.operand(p)
            return ("return", a), p, targets
        if op == "scale":
            i, p = self.u16(p)
            a, p = self.operand(p)
            b, p = self.operand(p)
            n, p = self.u8(p)
            r, p = self.u8(p)
            return ("scale", self.imm[i], a, b, n, reg_name(r)), p, targets
        if op == "addk":
            i, p = self.u16(p)
            a, p = self.operand(p)
            r, p = self.u8(p)
            return ("addk", self.imm[i], a, reg_name(r)), p, targets
        if op == "mul":
            k, p = self.u8(p)
            a, p = self.operand(p)
            b, p = self.operand(p)
            r, p = self.u8(p)
            return ("mul", ALUS[k], a, b, reg_name(r)), p, targets
        if op == "div":
            k, p = self.u8(p)
            a, p = self.operand(p)
            return ("div", "idivl" if k else "divl", a), p, targets
        if op == "widen":
            k, p = self.u8(p)
            return ("widen", "cltd" if k else "cwtl"), p, targets
        if op == "setcc":
            c, p = self.u8(p)
            r, p = self.u8(p)
            return ("setcc", CONDS[c], reg_name(r)), p, targets
        if op == "push":
            a, p = self.operand(p)
            return ("push", a), p, targets
        if op == "setarg":
            n, p = self.u8(p)
            a, p = self.operand(p)
            return ("setarg", n, a), p, targets
        if op == "popn":
            n, p = self.u8(p)
            return ("popn", n), p, targets
        if op == "popreg":
            r, p = self.u8(p)
            return ("popreg", reg_name(r)), p, targets
        if op == "ftol":
            n, p = self.u8(p)
            steps = []
            for _ in range(n):
                k, p = self.u8(p)
                if FSTEPS[k] in ("ld", "addi"):
                    a, p = self.operand(p)
                    steps.append((FSTEPS[k], a))
                else:
                    lo, p = self.u16(p)
                    hi, p = self.u16(p)
                    v = (self.imm[hi] & 0xffffffff) << 32
                    v |= self.imm[lo] & 0xffffffff
                    steps.append((FSTEPS[k], v))
            r, p = self.u8(p)
            return ("ftol", steps, reg_name(r)), p, targets
        raise ValueError("opcode %r at %d" % (op, p - 1))


def decode_rule(dec, start, length):
    """A rule as its operations at their offsets, and the offsets branched
    to. Those are where the blocks have to begin."""
    at = []
    marks = set()
    p = start
    end = start + length
    while p < end:
        off = p - start
        op, p, targets = dec.insn(p)
        at.append((off, op))
        marks.update(targets)
    if p != end:
        raise ValueError("a rule runs %d bytes past its length" % (p - end))
    return at, marks


class Shape:
    """What write_rule asks a rule for: its blocks, the three numbers of its
    shape, and where a label is. The same few lines as delta-lower's Written,
    which the reader builds and this cannot."""

    def __init__(self, name, obj, frame, pbase, params):
        self.name = name
        self.obj = obj
        self.frame = frame
        self.pbase = pbase
        self.params = params
        self.blocks = []
        self._at = {}

    def block(self, label):
        at = len(self.blocks) + 1
        self._at[label] = at
        self.blocks.append((label, at, []))
        return self.blocks[-1][2]

    def resolve(self, text):
        return self._at.get(text)


def retarget(op, block_of):
    """A control-flow target as the name of the block it lands on, and a map
    as the name of its table."""
    if op[0] == "jump":
        return ("jump", "B%d" % block_of[op[1]])
    if op[0] == "branch":
        return ("branch", op[1], "B%d" % block_of[op[2]])
    if op[0] == "switch":
        return ("switch", ["B%d" % block_of[t] for t in op[1]], op[2])
    if op[0] == "map":
        return ("map", "map_%d" % op[1], op[2], op[3])
    return op


# ---- writing the text ----------------------------------------------------


def main(argv):
    if len(argv) != 1:
        raise SystemExit("usage: delta-unemit.py <tag>")
    tag = argv[0]
    where = os.path.join(ROOT, "lang", tag)
    src = os.path.join(where, "delta_rules_%s.c" % tag)
    text = open(src, encoding="utf-8", errors="surrogateescape").read()

    code = bytes(numbers(text, "%s_delta_rule_code" % tag))
    imm = numbers(text, "%s_delta_rule_imm" % tag)
    maps = bytes(numbers(text, "%s_delta_rule_map" % tag))
    entries = strings(text, "%s_delta_rule_entry_name" % tag)
    sym_at = syms(text, "%s_delta_rule_sym" % tag)
    rules = rule_table(text, "%s_delta_rules" % tag)
    print("%d rules, %d bytes of code, %d immediates, %d symbols, %d entries"
          % (len(rules), len(code), len(imm), len(sym_at), len(entries)))

    symnames = ["sym_%d" % i for i in range(len(sym_at))]
    dec = Decoder(code, imm, entries, symnames)

    # Everything is decoded before anything is written, because a map table's
    # end is only known once every offset that is used is known.
    done = []
    map_offsets = set()
    for name, obj, start, length, frame, pbase, params in rules:
        dec.used_syms = []
        at, marks = decode_rule(dec, start, length)
        for _off, op in at:
            if op[0] == "map":
                map_offsets.add(op[1])
        done.append((name, obj, frame, pbase, params, at, marks,
                     list(dec.used_syms)))

    bounds = sorted(map_offsets)
    map_bytes = {}
    for i, off in enumerate(bounds):
        end = bounds[i + 1] if i + 1 < len(bounds) else len(maps)
        map_bytes["map_%d" % off] = maps[off:end]
    print("%d map tables over %d bytes" % (len(bounds), len(maps)))

    # Which object first named a symbol: that pair is what a rule holds.
    owner = {}
    for name, obj, frame, pbase, params, at, marks, used in done:
        for i in used:
            owner.setdefault(i, obj)

    out_dir = os.path.join(where, "rules")
    os.makedirs(out_dir, exist_ok=True)

    by_obj = []
    for item in done:
        obj = item[1]
        if not by_obj or by_obj[-1][0] != obj:
            by_obj.append((obj, []))
        by_obj[-1][1].append(item)

    for obj, items in by_obj:
        lines = []
        for name, _obj, frame, pbase, params, at, marks, _used in items:
            d = Shape(name, obj, frame, pbase, params)
            starts = sorted({0} | marks)
            block_of = dict((s, i) for i, s in enumerate(starts))
            cur = None
            for off, op in at:
                if off in block_of:
                    cur = d.block("B%d" % block_of[off])
                if cur is None:
                    raise SystemExit("%s: an operation before any block"
                                     % name)
                cur.append(retarget(op, block_of))
            tables = {}
            for _off, op in at:
                if op[0] == "map":
                    tables["map_%d" % op[1]] = map_bytes["map_%d" % op[1]]
            dlo.write_rule(name, obj, d, tables, lines)
        stem = obj[:-4] if obj.endswith(".obj") else obj
        with open(os.path.join(out_dir, stem + ".dr"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

    print("%d files written to %s"
          % (len(by_obj), os.path.relpath(out_dir, ROOT)))

    # The stores in the order write_c wants them, which is not the order the
    # symbol pool reaches them in: a store with no symbol pointing into it
    # would be missed by that, and the order decides the table of pointers.
    # The C already declares them, one to a line, in exactly that order.
    stores = re.findall(r"^extern uint8_t ([A-Za-z_][A-Za-z0-9_]*)\[\];",
                        text, re.M)
    missing = sorted(set(s for s, _ in sym_at) - set(stores))
    if missing:
        raise SystemExit("delta-unemit: %s is pointed into but not declared"
                         % ", ".join(missing))

    lines = ["# Where each address the rules name falls: which store of the",
             "# language's own bytes, and how far into it. Written by",
             "# tools/delta-unemit.py out of the bytecode in the tree, so the",
             "# names between the two are its own: what a rule holds is a pool",
             "# index and what the C holds is a store and an offset, and",
             "# nothing else ever reads the name in between.",
             ""]
    for st in stores:
        lines.append("store %s" % st)
    for i, (store, off) in enumerate(sym_at):
        lines.append("at %s %s %s %d"
                     % (owner.get(i, by_obj[0][0]), symnames[i], store, off))
    with open(os.path.join(out_dir, "symbols"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("%d stores and %d addresses in rules/symbols"
          % (len(stores), len(sym_at)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
