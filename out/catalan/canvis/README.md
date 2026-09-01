# The vowels and the words, to listen to

Sixteen cases, one per line of `cases.txt`, name and text separated by a bar.
Made the way the rest of `out/catalan` is made, one process to a case:

    while IFS="|" read -r name text; do
      python tools/speak.py -n -o "out/catalan/canvis/$name.wav" "$text"
    done < out/catalan/canvis/cases.txt

## The open o and the open e

Catalan has an open o and a close one and one letter for both, and the same
for the e. Where a word carries a grave the letter rules settled it already;
where it does not, the writing says nothing -- which is what the accent is for
and why the grammars' lists are lists of which accent to write on a word that
already has one. So what is here is contexts that hold, and words.

`01` and `02` are the two contexts that are rules: an o with a u or an i after
it, and an o the word ends on after a c or an l, counting the feminine and the
plural. `03` is the check that goes with them -- tot, molt, gos, cos, son,
front, Barcelona, persona, corona and estona are close and stay close.

`04` and `05` are the rest of the o: -onj- for taronja, -obl- for poble with
doble taken out by hand, bon and dona by the letter in front of them, volta
and cor and got by name, and -osa for rosa and cosa, which has to keep the
bare -os of gos and cos out and the doubled s of gossa with it.

`06` and `07` are the e, which is thinner: -ema, -eu, tren, tres, setze, set,
ple, and against them tretze, meu, teu, seu, mes, pes, be, te and ve. `08` is
-eix, the one shape that turns on the length of the word rather than its
letters: peix and neix are close and llegeix, coneix and farceix are open.

`09` is the digits, which never reach the letter rules -- a number word is
laid down as letters out of `rules/constants` -- so seven, nine, ten and
sixteen are spelt there with a grave.

## The rest

`10` is an s at the end of a word voicing in front of whatever is voiced at
the start of the next. `11` is amb, whose b says nothing at all unless a vowel
follows: amb mi and em mi are the same wave from the m onwards. `12` is the
final r of fer, dir, ser, por, dur and every word with a second vowel in it,
against cor, mar and clar which keep theirs. `13` is -ble said as -ple. `14`
is aquest said as aquet, with aquesta keeping its s. `15` is the stress on
escoles and pobles, which the voicing rule had moved.

## What is not here

fe and re are open and are not covered; ple is, and only because it has an l
in front of its e. The acute is flattened on the way in, so be and te look
exactly like ple to a letter rule and the l is the only thing between them.
-ot, -ort and -ost are left out of the o's endings because tot is close. This
is a list that grows by ear, and `lang/caes/rules/glob.up` says how to add to
it.
