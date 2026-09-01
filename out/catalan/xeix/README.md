# The two postalveolars, before and after

A is what was in the tree at `aae5582`, B is what is there now. Five cases,
one per line of `cases.txt`, made the way the rest of `out/catalan` is made,
one process to a case:

    while IFS="|" read -r name text; do
      python tools/speak.py -n -o "out/catalan/xeix/B-$name.wav" "$text"
    done < out/catalan/xeix/cases.txt

## What A has wrong

Two separate faults that both silence a postalveolar, which is why they were
heard as one.

The fricative had no length. `span_ph_S_dur` in `lang/caes/rules/ss_dur.up`
sets 40 for the S of an affricate and 80 for one standing on its own, and both
were set to 0 over the two commits before this -- the same numbers the mute
phone next door was being walked down, 40/80 to 30/30 to 0/0, applied to the
rule below it as well. Nothing in the phoneme string changed, so `speak.py -p`
said what it always had; `16-ix.wav` lost ten kilobytes and the sound went.

The affricate said nothing at all, and never had. `tx` laid down the phone C,
Castilian's own voiceless affricate, on the belief that the module expands it
into a stop and a fricative. It does not: there is no `span_ph_C` anywhere,
any more than there is a `span_ph_J`, and Castilian reaches the sound by
spelling it `ch` and laying the two phones down from its `c` rule. So the
whole digraph went by without a sound -- cotxe was [k o @], despatx
[d @ s p a], butxaca [b u a k @] -- and `ss_dur.up`'s arm for an S that stands
after a t had been written and never once entered.

`tx` lays down `cat_ph_tsh` now, the stop and the fricative as one insertion,
which is what `cat_ph_dzz` already does for metge and platja and what Polish
did for the same reason.

## What to listen for

`01` and `02` are the fricative alone: caixa, peix, xocolata, això. In A it is
a click where the sound should be. In B it measures 75 milliseconds for caixa
and peix and 85 for xocolata, against the 65 of the s of passa.

`03` is the affricate: cotxe, despatx, butxaca, esquitx. In A the letters are
not there at all -- cotxe rhymes with nothing, it is co-e. In B there is a
stop closure and then 50 milliseconds of fricative for cotxe, 55 for despatx.

`04` puts the two side by side, which is the pair the language turns on: caixa
against cotxe is [k a S @] against [k o t S @], and the only difference is the
stop.

`05` is a sentence with both in it.

## One thing that changed after this

B was re-made when the glide came off the ix. It carried one for a while --
caixa as [k a y S @], on the reading that Western and Valencian keep it -- and
a listener heard it in every one of these words, so Central Catalan's reading
is what is here: the i of caixa is a graphic mark and the word is [k a S @].
A still has the glide, being what was in the tree at the time, so `01` and
`02` differ in that as well as in the length of the fricative.
