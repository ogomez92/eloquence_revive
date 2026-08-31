"""Change some numbers in the intonation rules, rebuild, measure, put them back.

The mapping from a number in an intonation rule to a semitone of audio is not
something to reason about: it is a table, and this is what fills it in.

    python out/sweep.py '963@  store movw imm 40 slot -6;3317@  store movw imm 90 slot -2'

One argument is one build: semicolons separate the lines it changes, and each
is the line number in lang/caes/rules/ss_inton.dr and what to put there.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import speak
import melody

RULES = 'lang/caes/rules/ss_inton.dr'
CASES = os.path.join(ROOT, 'out', 'catalan', 'prosody.txt')
WATCH = ['span', 'onset', 'tail', 'move', 'declination', 'peak_height', 'before_pause']


def run(edits):
    was = {}
    for path, line, text in edits:
        full = os.path.join(ROOT, path)
        lines = open(full, encoding='utf-8').read().split(chr(10))
        was.setdefault(full, list(lines))
        lines[line - 1] = text
        open(full, 'w', encoding='utf-8',
             newline=chr(10)).write(chr(10).join(lines))
    try:
        speak.build('caes', 8, False)
        exe = speak.engine()
        by = {}
        for i, (kind, text) in enumerate(melody.cases(CASES)):
            s = melody.measure(exe, kind, i, text)
            if s:
                by.setdefault(kind, []).append(s)
        out = {}
        for kind, rows in by.items():
            out[kind] = {}
            for w in WATCH:
                have = [r[w] for r in rows if r[w] == r[w]]
                out[kind][w] = sum(have) / len(have) if have else float('nan')
        return out
    finally:
        for full, lines in was.items():
            open(full, 'w', encoding='utf-8',
                 newline=chr(10)).write(chr(10).join(lines))


def main():
    base = json.load(open(os.path.join(ROOT, 'out', 'melody-cons.json')))
    for spec in sys.argv[1:]:
        edits = []
        for one in spec.split(';'):
            head, _, text = one.partition('@')
            if ':' in head:
                path, _, line = head.rpartition(':')
            else:
                path, line = RULES, head
            edits.append((path, int(line), text))
        got = run(edits)
        print(' '.join('%s:%d=%s' % (os.path.basename(p), l,
                                     t.split('imm')[1].split()[0])
                       for p, l, t in edits))
        for kind in ('stmt', 'comma', 'yesno', 'wh'):
            if kind not in got:
                continue
            print('   %-6s %s' % (kind, '  '.join(
                '%s %+.2f' % (w, got[kind][w] - base[kind][w]) for w in WATCH)))
        sys.stdout.flush()


if __name__ == '__main__':
    main()
