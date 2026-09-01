# Catalan test audio, and how to make more

11,025 Hz, mono, sixteen bit. Central Catalan.
docs/status.md says what is done and what is not.

## Saying something new

    python tools/speak.py "Bon dia. Com estas?"

Rebuilds the voice as it currently stands, writes out/speak.wav, and prints
what the words came out as. About half a minute. Change a formant, a letter
rule, an intonation number or a word, run it again, listen.

    -o FILE   write the wave somewhere else
    -v N      voice 1 to 8
    -n        do not rebuild, just speak
    -t        rebuild the tables too, after editing caes.statements,
              caes.settings, caes.globals or caes.dict
    -p        print the phonemes for each word, write no wave
    -P        print them a line at a time instead, which is the only way to
              see a function word losing its stress, an s voicing before the
              next word, or a consonant said only before a vowel
    -m        also measure the melody of what it just said

    python tools/speak.py -o hola.wav "Bon dia a tothom"
    python tools/speak.py -n -p "casa dia caixa cafe"
    python tools/speak.py -m "La casa es molt gran."
    type text.txt | python tools/speak.py -o out.wav

## Where to change what

    a sound a letter makes    lang/caes/rules/st_phone.up
    the schwa, the open e/o   lang/caes/rules/ss_ssval.up
    which words get the       the arms of apply_span_o_rules and
    open o or e               apply_span_e_rules in st_phone.up
    what a letter may ask     lang/caes/rules/glob.up, with the letters it
    about the next word       names in rules/constants
    how dark the l is         lang/caes/rules/ss_val.dr, span_ph_l -- the
                              second formant target, and out/catalan/dark-l
    how long a sound lasts    lang/caes/rules/ss_dur.up (consonants)
                              lang/caes/rules/ss_ssdur.up (vowels)
    which words are atonic    tools/lang-sets.py set caes <set> <word>...
    the melody                lang/caes/rules/ss_inton.dr, span_nucl_low_tone
                              and the phrase-final target in span_phrase_tone
    the numbers               lang/caes/rules/st_numbr.up and rules/constants
    what a letter is          tools/lang-alphabet.py show caes
    what a phoneme is         tools/lang-phonemes.py caes
    what a word is to the
    rules that stress it      tools/lang-sets.py show caes

## Measuring the melody

A change to an intonation number cannot be judged on one sentence: how far the
voice falls at the end depends on what the last word happens to end in. So it
is judged over a set.

    python tools/melody.py                  say all of them, print the numbers
    python tools/melody.py -o base          and keep them under a name
    python tools/melody.py -c base          print the change since that name
    python tools/melody.py -n               do not rebuild first

The sentences are `out/catalan/prosody.txt`, twenty-four of them under four
headings -- statements, polar questions, wh-questions, and sentences with a
comma -- and the numbers are averaged by heading. `docs/status.md` says what
each of them is, what a person does, and which way each has moved.

## The cases

01-salutacio.wav         Bon dia. Com estàs? Molt bé, gràcies.
02-reduccio.wav          casa cosa pare mare dona taula
03-Barcelona.wav         Barcelona és la capital de Catalunya.
04-sibilants.wav         caixa xocolata jove gener girafa panxa
05-africades.wav         cotxe despatx metge platja viatge dotze setze
06-palatals.wav          any Catalunya llibre ull cavall canya lluna palla
07-essa-sonora.wav       casa rosa francesa presentar passar massa
08-numeros.wav           un dos tres quatre cinc sis set vuit nou deu
09-dies.wav              dilluns dimarts dimecres dijous divendres dissabte diumenge
10-frase-llarga.wav      La meva germana treballa en una escola del poble i cada dia agafa el tren.
11-pregunta.wav          Vols venir amb mi a la platja aquest dissabte?
12-pangrama.wav          Aquest gener el jove metge de Barcelona va despatxar dotze caixes.
13-obertes.wav           cafè òpera això està sèrie dòna dóna més bé
14-hiat-ia.wav           dia via policia Maria família gràcies duana suau cua
15-diftongs.wav          dijous taula aigua quatre vuit avui peix noia riu bou
16-ix.wav                caixa peix baixa deixar coneixement calaix
17-final-sord.wav        fred verd club sang gat groc pop dissabte dubte
18-ena-final.wav         gran tren bon un món nen banc sang canvi enfadat
19-numeros-xifres.wav    1 5 9 12 15 19 20 21 25 26 30 31 36 45 55 66 78 91 99
20-text-corrent.wav      Avui és dissabte i el cafè de la cantonada és ple de gent que llegeix el diari.
21-penjat.wav            Mengen fetge d'un penjat.
22-jotes.wav             El jove de Girona menja taronges. Penjar, menjar, àngel, mengen.
23-melodia.wav           A statement, a question and a sentence with commas in it.

veu-1 .. veu-8.wav       the eight voices, on "Bon dia. Em dic
                         Eloqüència i parlo català."

## canvis/

The open o and the open e, the s that voices in front of the next word, amb,
the final r, -ble as -ple, aquest as aquet, and the conjunction i: sixteen
cases, with a README beside them saying what each is for and which of them are
rules and which are single words.

## xeix/

The fricative of caixa and the affricate of cotxe, before and after the two
faults that silenced them: a duration walked to nought by a change meant for
the phone below it, and a `tx` that laid down a phone nothing in the module
speaks. A is what was in the tree before, B is what is there now.

## zeta/

The voiced postalveolar -- the sound of jove and gener, and the release of the
affricate in metge and platja -- at five settings. A is what IBM left there
and no Castilian spelling could reach: 20 milliseconds, no noise modulation,
and the frication five under what its own S gets. B to E are the S line for
line with voicing added, and differ in how long the affricate's stop is held
and how long its release runs. C is what is in the tree.

## schwa-a/

The schwa and the a moved apart. They were sixty hertz and a hundred from each
other, closer than any two of Castilian's own five vowels, and casa has both
in it. B is what is in the tree.

## dark-l/

The l at eight settings of its second, third and fourth formants, over ten
sentences that put an l in every position a Catalan l can be in. E is what is
in the tree. `dark-l/README.md` says what the ladder was for and why the
darkness is the second formant's alone.

## schwa/

The commonest vowel in the language at five settings of its first two
formants, on the same six words. A is what was there first and was heard as
far too close, almost an o. C is what is in the tree. To change it, edit
cat_ph_schwa_vals in lang/caes/rules/ss_ssval.up and run speak.py.

    A-F1_500-F2_1500.wav
    B-F1_550-F2_1550.wav
    C-F1_600-F2_1500.wav
    D-F1_620-F2_1400.wav
    E-F1_660-F2_1350.wav

## The melody, over twelve statements

                      before   now    a person
    tail              -0.88   -2.29    -1.0
    terminal fall     -3.72   -5.65    -1.5
    range              4.96    5.53     4.1
    accent height      3.19    3.05     2.3

A statement used to climb over its last two hundred milliseconds and only then
fall, which is heard as a question would be. `python tools/pitch.py trace
<wav>` is what shows that; the averages above cannot, because a fall and a
rise-then-fall can end in the same place.

## What the words come out as

@ is the schwa, E and O the open e and o, Z the voiced postalveolar and S its
voiceless pair, N the palatal nasal, L the palatal lateral, B D G the lenited
stops, y and w the glides.

casa               k a z @
dia                d i @
cafè               k @ f E
dòna               d O n @
caixa              k a S @
cotxe              k o t S @
metge              m e d Z @
dijous             d i Z o w s
quinze             k i n z @
fred               f r e t
dissabte           d i s a p t @
gran               g r a n
llibre             L i B r @
Barcelona          b @ r s @ l o n @
5                  s i ng k
12                 d o d z @
25                 b i n t i s i ng k
45                 k w @ r @ n t @ s i ng k
66                 s @ S @ n t a s i s
99                 n u r a n t @ n o w
