# The dark l, and the eight settings it was chosen off

Castilian's l is clear: the tongue front against the ridge and nothing behind
it. Catalan's is velarised in every position -- the back of the tongue raised
towards the soft palate -- and it is one of the two or three things a listener
hears first. Catalan spoken with a Castilian l sounds like Spanish, whatever
else is right about it.

The whole of it is three numbers in one rule, `span_ph_l` in
`lang/caes/rules/ss_val.dr`: the second, third and fourth formant targets it
aims at before six hundred lines of context tests move them for the sounds
either side. Lowering a target there darkens the l everywhere without touching
a single one of those tests.

## The settings

    f2    f3    f4
    1440  2500  3000   A   Castilian, which is what was here before
    1150  2700  3000   B
     950  2850  3000   C
     800  3000  3000   D   IBM's own American English lateral locus
    1150  2500  3000   E   in the tree
    1150  2700  3300   F
     950  2600  3300   G
    1150  2400  3200   H

A to D walk f2 down and f3 up together, which is what the phonetics books say
a velarised l is and what IBM's American English does: `eng_lat_Fv` in
`lang/enus/rules/es_val.dr` is f2 800 and f3 3000, against Castilian's 1440 and
2500. The first formant is 300 in both languages and is not in the ladder.

That ladder was wrong in a way listening found and arithmetic then explained. B
was dark enough and carried a ring over the top of it, loud enough to hear as a
beep. This module's fourth formant for the l is 3000 and stays there, so an f3
raised to 2700 sits three hundred hertz under it and the two resonances ring
together; D, at 3000, puts them on top of each other. E to H are the second
ladder, which separates the three.

Measured on the l of `escola`, as the smoothed spectrum's peak between two and
three kilohertz and how far it stands above the trough below it:

    A   peak 2200    8 dB   broad
    B   peak 2600   14 dB   narrow      the beep
    E   peak 2200    9 dB   broad
    G   peak 2400    7 dB   broad

So the darkness is f2's alone, and E is B with nothing else moved: the second
formant leans down on the first, the top of the spectrum is left as flat as
Castilian left it. G is the darker one, spaced rather than crowded, and is
where to go if E is not dark enough.

## The cases

`cases.txt` is ten of them, one per line, the name and the text separated by a
tab. Every position an l can be in, and the contrast that has to survive
darkening: `la palla i la pala`, the palatal ll against the plain l, which are
two different phonemes and must not become one.

    01-llum-sol      La llum del sol al poble.
    02-final         mal sal sol cel mil tal
    03-inicial       lila lent lògic litre luxe
    04-grups         clar blau plaça flor glaç plou
    05-entre-vocals  escola tela pilota bala fila
    06-geminada      il·lusió novel·la col·legi
    07-frase         Els alumnes de l'escola llegeixen el llibre al vespre.
    08-palla-pala    la palla i la pala
    09-barcelona     Barcelona és la capital de Catalunya.
    10-el-poble      El poble vell de la vall és molt bell.

## Making the ladder again

Each setting is one build and ten sentences, about a minute:

    python tools/speak.py -o /tmp/warm.wav hola      # builds what is in the tree
    while IFS="	" read -r name text; do
      python tools/speak.py -n -o "out/catalan/dark-l/X-$name.wav" "$text"
    done < out/catalan/dark-l/cases.txt

One process to a case, which matters: the engine's second utterance is not its
first -- the machine's state has moved on -- so two settings are only
comparable when each sentence is somebody's first.
