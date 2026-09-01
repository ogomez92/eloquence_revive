# The voiced postalveolar, at five settings

The sound of jove, gener and Girona, and the release of the affricate in
metge, platja and penjat. Six cases, one per line of `cases.txt`, one process
to a case, made the way the rest of `out/catalan` is made:

    while IFS="|" read -r name text; do
      python tools/speak.py -n -o "out/catalan/zeta/C-$name.wav" "$text"
    done < out/catalan/zeta/cases.txt

## What A is

A is what the sound was, with the ix already fixed so that nothing else moved
between it and the rest. It is IBM's `span_ph_Z` and IBM's `span_ph_Z_dur`,
neither of which Castilian spelling can reach, so neither had ever been heard:

    frication amplitude   50   where its own S has 55
    the three below it    --, 65, 50   where S has 60, 62, 62
    the formants          written out inline, not span_pal_Fv's
    modulate_noise        not called at all
    duration              20 milliseconds, flat, in every context
    the affricate's stop  45, shared with the d that follows an l

Twenty milliseconds of a fricative with no noise modulation is a click. That
is what "too quiet and maybe a bit short" was.

## What B to E are

All four are `span_ph_S` line for line with one number added -- 2754, the
amplitude of voicing, which the voiceless one never sets. Same frication, same
amplitudes, same `span_pal_Fv`, same `modulate_noise`. The sh with voice in
it, which is what was asked for. What they differ in is two lengths:

              the affricate's stop     the release
    A              45                      20
    B              50                      40
    C              60                      40
    D              70                      40
    E              60                      55

The stop is the hold before the affricate lets go -- the d of metge -- and
the release is the noise after it. A fricative standing on its own, the Z of
jove and gener, is 80 in all of B to E, which is what the S of caixa gets.

D is what is in the tree: the hold at 70, the release at 40. It was picked by
ear over the other four -- B and C are the same sound with a shorter hold, and
E answers a different question, whether the release wants to be longer than
the voiceless one's 40. It does not: a longer release is the thing that turns
an affricate back into a fricative, and E is here to be heard doing it.

## Where the numbers are

    the stop        lang/caes/rules/ss_dur.dr, span_ph_d_dur, label L33
    the release     lang/caes/rules/ss_dur.up, span_ph_Z_dur
    everything else lang/caes/rules/ss_val.up, span_ph_Z
