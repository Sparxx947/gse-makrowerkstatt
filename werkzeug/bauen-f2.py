#!/usr/bin/env python3
"""Fassung 2 für UH-DK (Unholy DK) und Retri (Retribution Paladin).

Am 2026-08-21 lokal mit SimulationCraft gesucht (SimC 1210-01 gegen
12.1.0.69382), Puppenbedingungen, je 9000 Iterationen.

★ ENTSCHEIDENDE RANDBEDINGUNG: **msClickRate bleibt bei 100 ms.**
Vorgabe — alles darunter sieht für Blizzard nach Bot aus. 100 ms ist
zugleich GSE-Standard. Die Einstellung liegt PRO CHARAKTER in
`WTF/Account/DEIN_ACCOUNT/<Realm>/<Charakter>/SavedVariables/GSE.lua` und wirkt als
**Drossel**: die tatsächliche Rate ist min(AutoClicker, 1000/msClickRate).
Retri stand auf 150 ms (6,7 Klicks/s) und verlor allein dadurch rund fünf
Punkte — am 21.08. auf 100 korrigiert.

Damit ist die Rate nach oben bei 10/s gedeckelt und kann nur noch nach unten
abweichen (Jitter, Latenz). Bewertet wird deshalb über das Band **8/9/10
Klicks je Sekunde**, und **der schlechteste Einzelwert entscheidet**, nicht
der Mittelwert: Eine Sequenz, die bei 10/s glänzt und bei 9/s abstürzt, ist im
Spiel unbrauchbar. Genau das war der Fehler der ersten Fassungen.

ERGEBNIS (Mittel über 8/9/10 Klicks/s, in Klammern der schlechteste Wert)
    UH-DK  95,1 %  (93,3 %)     Fassung 1 an derselben Latte: 91,7 %  (88,5 %)
    Retri    94,5 %  (94,4 %)     Fassung 1 an derselben Latte: 88,2 %

Retri ist bei 100 ms gedeckelt: Alle 244 geprüften Muster landen zwischen 94,4
und 94,6 %. Mit 17 Klicks/s wären 96,2 % drin — das scheidet wegen der
Bot-Vorgabe aus. Seine Sequenz ist dafür extrem flach (94,4/94,4/94,6), also
gleichgültig gegen Klickraten-Schwankungen.

VIER BEFUNDE, die sich auf andere Klassen übertragen lassen:

1. **Über ein Band messen, nicht bei einer Rate.** Derselbe DK-Bestand kam bei
   10 Klicks/s auf 94,97 %, bei 11 auf 93,98 %, über ein weiteres Band gestreut
   zwischen 81,6 und 96,0 %. Das ist Resonanz zwischen Umlaufzeit und GCD bzw.
   Runenregeneration — im Spiel gibt es diese Kanten nicht.

2. **Füllerketten helfen genau dann, wenn sonst GCDs leer laufen.** Beim DK
   (Runen fehlen oft) +1,3 Punkte und, wichtiger, +4,8 Punkte im schlechtesten
   Fall. Beim Retri ±0,05. Nicht pauschal einbauen — messen.

3. **Cooldowns im Kopf können Spender verdrängen — müssen aber nicht.**
   Execution Sentence kostete Retri 1,7 Punkte, Hammer of Wrath im Kopf weitere
   2,0 (er kam 44,6 statt 19,0 mal; eine Makro-Bedingung half NICHT, erst ein
   eigener Schrittplatz). Gegenprobe: Army of the Dead aus dem DK-Kopf zu
   nehmen kostete 20 Punkte. Es kommt auf den einzelnen Zauber an.

4. **Die Reihenfolge im Kopf zählt nur, wo eine Mechanik daran hängt.** Bei Retri
   waren fünf Kopfvarianten binnen 0,05 Punkten gleich — aber Divine Toll vor
   Wake of Ashes kostete 4,2 Punkte. Beim DK gehört Dark Transformation vor
   Putrefy, weil Putrefy nur darunter wirkt.

GEPRÜFT UND VERWORFEN
  * Skillungen der weltbesten Spieler (Raider.IO, Saison mn-2, über `rio-get`):
    Beim DK gleichauf, beim Retri im Sim gleich gut, im Makro aber 8-11 %
    SCHLECHTER — sie setzen Handsteuerung voraus. Beide behalten ihre eigene.
  * 110 Reihenfolgen desselben Bestands bei Retri: 94,18-94,35 %. GSE liest die
    Sequenz als Gewichtung, nicht als Reihenfolge.
  * Hammer of Light mit der Bedingung aus der Sim-Prioritätsliste: 84,5 %.
  * Muster kürzer als 6 Schritte: 77,7-92,6 %, zu wenig Platz.

Spell-IDs aus `GSESpellCache` (enUS). Wo ein Zauber dort fehlte, steht
der englische Name; Client läuft auf Englisch.
"""
import importlib.util
import sys
from pathlib import Path

_p = Path(__file__).with_name('bauen-dk-retri.py')
_s = importlib.util.spec_from_file_location('bauen_dk_retri', _p)
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)
eintragen, gse3_encode = _m.eintragen, _m.gse3_encode

ZIEL = "/targetenemy [noharm][dead]\n"

# ---------------------------------------------------------------- UH-DK
SS, DC, FS, SR = 55090, 47541, 316239, 343294
AOTD, DT, OUT, PUT = 42650, 1233448, 77575, 1247378
DK_MUSTER = [SS, FS, DC, SS, FS, SS, FS, SR]
# Füllerkette: scheitert der Hauptzauber an fehlenden Runen, löst er keinen GCD
# aus und die nächste Zeile kommt durch. Zwei Fallbacks reichen — der dritte
# (Festering Strike) brachte 0,02 Punkte und sprengte die 255 Zeichen.
DK_KETTE = [SS, DC]
DK_KOPF = (
    "/startattack\n"
    f"/cast [nomod] {DT}\n"        # Dark Transformation zuerst …
    f"/cast [nomod] {PUT}\n"       # … denn Putrefy wirkt nur darunter
    f"/cast [nomod] {AOTD}\n"      # ohne Army of the Dead: -20 Punkte
    f"/cast [nomod] {OUT}\n"
    "/use [combat,nochanneling] 13\n"
    "/use [combat,nochanneling] 14\n"
)

# ---------------------------------------------------------------- Retri
TV = "Templar's Verdict"
AW, HOL, HOW = "Avenging Wrath", "Hammer of Light", "Hammer of Wrath"
BOJ, JUD, DTOLL, WOA = 184575, 20271, 375576, 255937
# Sechs Schritte, KEIN Templar Strike: Bei 100 ms Klickrate ist das 6er-Muster
# das flachste von 244 geprueften (94,4/94,4/94,6 ueber 8/9/10 Klicks/s). Das
# 8er waere im Mittel 0,04 Punkte besser, im schlechtesten Fall aber 0,3
# schlechter. Hammer of Wrath steht IM Muster, nicht im Kopf.
PAL_MUSTER = [TV, BOJ, TV, JUD, TV, HOW]
PAL_KETTE = []          # bei Retri wirkungslos (+-0,05 Punkte), also weglassen
PAL_KOPF = (
    "/startattack\n"
    f"/cast [nomod] {HOL}\n"       # Templar-Kernzauber, darf nie fehlen
    f"/cast [nomod] {WOA}\n"
    f"/cast [nomod] {DTOLL}\n"
    f"/cast [nomod] {AW}\n"
    "/use [combat,nochanneling] 13\n"
    "/use [combat,nochanneling] 14\n"
)


def akt(macro):
    return {b'Type': b'Action', b'type': b'macro', b'macro': macro.encode('utf-8')}


def bauen(name, anzeige, label, muster, kette, kopf, spec, mplus, hilfe):
    actions = []
    for spell in muster:
        zeilen = [f'/cast [nomod] {spell}']
        zeilen += [f'/cast [nomod] {f}' for f in kette if f != spell]
        t = (ZIEL if mplus else '') + kopf + '\n'.join(zeilen)
        if len(t) > 255:
            raise SystemExit(f'Schritt zu lang ({len(t)} Zeichen):\n{t}')
        actions.append(akt(t))
    return [name.encode('utf-8'), {
        b'LastUpdated': b'20260821120000',
        b'MetaData': {
            b'Author': b'Claude (fuer der Spieler)', b'Default': 1,
            b'Dependencies': {b'Macros': [], b'Sequences': [], b'Variables': []},
            b'EnforceCompatability': True, b'GSEVersion': 3326,
            b'Help': hilfe.encode('utf-8'), b'ManualIntervention': True,
            b'Name': anzeige.encode('utf-8'), b'SpecID': spec, b'TOC': 120100,
        },
        b'Versions': [{b'Actions': actions, b'InbuiltVariables': [],
                       b'Label': label.encode('utf-8')}],
        b'WeakAuras': [],
    }]


HILFE_DK = (
    "UH-DK - Unholy Death Knight, Midnight 12.1. Fassung 2 (21.08.2026).\n\n"
    "95,1 % einer optimal gespielten Rotation, gemittelt ueber 8 bis 10 Klicks\n"
    "je Sekunde; schlechtester Einzelwert 93,3 % (Fassung 1: 91,7 / 88,5 %).\n\n"
    "8 Schritte: Scourge Strike 3, Festering Strike 3, Death Coil 1,\n"
    "Soul Reaper 1. Jeder Schritt hat zusaetzlich Scourge Strike und\n"
    "Death Coil als Fuellzeilen - fehlen Runen, laeuft der GCD dadurch nicht\n"
    "leer. Das ist bei ihm der groesste Einzelposten: +4,8 Punkte im\n"
    "schlechtesten Fall.\n\n"
    "KLICKRATE: msClickRate bleibt auf 100 ms. Schneller waere messbar besser,\n"
    "faellt aber als Bot-Verdacht auf - bewusste Entscheidung.\n\n"
    "Im Makro laufen automatisch mit: Dark Transformation, Putrefy,\n"
    "Army of the Dead, Outbreak und beide Schmuckstuecke.\n\n"
    "ARMY OF THE DEAD ist der groesste Einzelposten im Kopf - ohne ihn faellt\n"
    "die Sequenz von 94 auf 74 Prozent. DARK TRANSFORMATION muss VOR Putrefy\n"
    "stehen, weil Putrefy nur darunter wirkt.\n\n"
    "NICHT im Makro: Death Strike, Anti-Magic Shell, Icebound Fortitude,\n"
    "Lichborne - alles Defensive gehoert auf eigene Tasten."
)

HILFE_PAL = (
    "Retri - Retribution Paladin (Templar), Midnight 12.1. Fassung 2 (21.08.2026).\n\n"
    "94,5 % einer optimal gespielten Rotation, gemittelt ueber 8 bis 10 Klicks\n"
    "je Sekunde; schlechtester Einzelwert 94,4 % (Fassung 1: 88,2 %).\n\n"
    "6 Schritte: Templar's Verdict 3, Blade of Justice 1, Judgment 1,\n"
    "Hammer of Wrath 1.\n\n"
    "WICHTIGSTE EINZELAENDERUNG war nicht die Sequenz, sondern die Einstellung:\n"
    "msClickRate stand bei ihm auf 150 ms (6,7 Klicks/s) und ist jetzt auf 100.\n"
    "Das allein waren rund fuenf Punkte.\n\n"
    "Diese Sequenz ist bewusst die FLACHSTE von 244 geprueften: 94,4 / 94,4 /\n"
    "94,6 Prozent bei 8, 9 und 10 Klicks je Sekunde. Sie ist damit\n"
    "gleichgueltig gegen Schwankungen der Klickrate.\n\n"
    "TEMPLAR STRIKE ist nicht drin, EXECUTION SENTENCE auch nicht - beide\n"
    "verdraengten Spender.\n\n"
    "Im Makro laufen automatisch mit: Hammer of Light, Wake of Ashes,\n"
    "Divine Toll, Avenging Wrath und beide Schmuckstuecke.\n"
    "DIVINE TOLL muss NACH Wake of Ashes stehen - umgekehrt kostet es\n"
    "4,2 Punkte.\n\n"
    "NICHT im Makro: Shield of Vengeance, Divine Shield, Lay on Hands,\n"
    "Word of Glory, Blessing of Protection."
)

SEQS = [
    ('Claude_UH_MPlus_F2', 'Claude Unholy - Mythic+ F2', 'M+ F2',
     DK_MUSTER, DK_KETTE, DK_KOPF, 252, True, HILFE_DK),
    ('Claude_UH_Raid_F2', 'Claude Unholy - Raid F2', 'Raid F2',
     DK_MUSTER, DK_KETTE, DK_KOPF, 252, False, HILFE_DK),
    ('Claude_Ret_MPlus_F2', 'Claude Retri - Mythic+ F2', 'M+ F2',
     PAL_MUSTER, PAL_KETTE, PAL_KOPF, 70, True, HILFE_PAL),
    ('Claude_Ret_Raid_F2', 'Claude Retri - Raid F2', 'Raid F2',
     PAL_MUSTER, PAL_KETTE, PAL_KOPF, 70, False, HILFE_PAL),
]

if __name__ == '__main__':
    fertig = {}
    for name, anzeige, label, muster, kette, kopf, spec, mplus, hilfe in SEQS:
        seq = bauen(name, anzeige, label, muster, kette, kopf, spec, mplus, hilfe)
        s = gse3_encode(seq)
        fertig[name] = s
        laengen = [len(a[b'macro'].decode()) for a in seq[1][b'Versions'][0][b'Actions']]
        print(f'{name:<22}{len(muster):>3} Schritte, laengster {max(laengen):>3} von 255 '
              f'Zeichen, Import {len(s)} Zeichen')
    if '--schreiben' in sys.argv:
        eintragen(fertig)
    else:
        print('\nNur Ausgabe. Mit --schreiben eintragen.')
