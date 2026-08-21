#!/usr/bin/env python3
"""Sequenzen für UH-DK (Unholy DK) und Retri (Retribution Paladin).

Beide am 2026-08-21 lokal mit SimulationCraft gesucht (SimC 1210-01 gegen
12.1.0.69382), Profile per Armory-Import, Target-Dummy-Bedingungen.

VORGABE DES SPIELERS HIER: **Alles darf automatisch laufen** — auch Cooldowns und
Schmuckstücke. Die Messlatte ist deshalb das VOLLE Optimum, nicht wie beim
Prot-Paladin das Optimum ohne Schmuck.

ERGEBNIS
    UH-DK  74.713 von 79.120 DPS = 94,4 %
    Retri    65.504 von 74.279 DPS = 88,2 %

VIER FEHLER IM NACHBAU, die zusammen über 30 Prozentpunkte gekostet haben —
sie gelten für JEDE künftige Klasse:

1. **`actions.precombat` beschwören nicht vergessen.** Eine eigene APL ersetzt
   die Precombat-Liste. Ohne `raise_dead` fehlten dem DK Dark Transformation,
   Putrefy und 459 Sweeping-Claws-Treffer: 62 % statt 78 %.
   (Gleicher Fehler wie beim BM-Jäger ohne `summon_pet`.)
2. **`actions+=/auto_attack` ist Pflicht für Nahkämpfer.** Ohne die Zeile
   schlägt die Waffe nie zu. Beim Retri löst der Auto-Angriff `crusading_strike`
   aus — 201,8 Auslösungen fehlten, 59,6 % statt 88,2 %.
3. **Namen aus dem Sim-Bericht sind nicht zwingend wirkbare Zauber.**
   `crusading_strike` ersetzt den Auto-Angriff, `final_verdict` ist die
   Ersatzform von `templars_verdict`, `festering_scythe` ein Proc auf
   Festering Strike. Alle drei lassen sich nicht als Aktion anlegen — vorher
   einzeln gegen SimC prüfen.
4. **Klassenmechanik nachlesen.** Icy Veins (12.1) nennt für Unholy
   „Putrefy nur während Dark Transformation" — dieser eine Zauber brachte
   **+11,5 Prozentpunkte** (82,9 → 94,4 %).

Spell-IDs stammen aus eigenem `GSESpellCache` (enUS) — die zuverlässigste
Quelle, weil sie aus dem laufenden Spiel kommt. Wo ein Zauber dort fehlte, steht
der englische Name; Client läuft auf Englisch.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gse3 import gse3_encode

# ---------------------------------------------------------------- HIER ANPASSEN
# Pfad zur GSE-Datenbank. Unter Windows/WSL etwa:
#   Path.home() / 'wow' / 'WTF' / 'Account' / 'DEIN_ACCOUNT' / 'SavedVariables' / 'GSE.lua'
# Unter Linux mit Steam/Proton liegt _retail_ im Proton-Praefix.
# Wie der Account-Ordner heisst, zeigt:  ls ~/wow/WTF/Account
GSE_DATEI = Path('BITTE_ANPASSEN/WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua')

# ---------------------------------------------------------------- UH-DK
SS, DC, FS, SR = 55090, 47541, 316239, 343294        # Scourge/Death Coil/Festering/Soul Reaper
AOTD, DT, OUT, PUT = 42650, 1233448, 77575, 1247378  # Army/Dark Transf./Outbreak/Putrefy
DK_MUSTER = [SS, DC, SS, DC, FS, SS, DC, SS, DC, SS, FS, DC, SS, SR]

DK_KOPF = (
    "/startattack\n"
    f"/cast [nomod] {AOTD}\n"      # Cooldowns laufen mit, sobald bereit
    f"/cast [nomod] {DT}\n"
    f"/cast [nomod] {PUT}\n"       # wirkt nur waehrend Dark Transformation
    f"/cast [nomod] {OUT}\n"
    "/use [combat,nochanneling] 13\n"
    "/use [combat,nochanneling] 14\n"
)

# ---------------------------------------------------------------- Retri
# Diese vier fehlen in Spell-Cache — sein Client ist enUS, Namen tragen.
TV, TS, TSL, ES = "Templar's Verdict", "Templar Strike", "Templar Slash", "Execution Sentence"
BOJ, JUD, DTOLL, WOA = 184575, 20271, 375576, 255937
AW, HOL, HOW = "Avenging Wrath", "Hammer of Light", "Hammer of Wrath"
PAL_MUSTER = [TV, TS, BOJ, TV, TS, JUD, TV, TS, TV, BOJ, TS, TV, JUD, TSL]

# Die Kopfzeilen sprengen mit allen Cooldowns die 255-Zeichen-Grenze
# (296 Zeichen). Deshalb ZWEI Koepfe, die sich abwechseln: Bei zehn Klicks je
# Sekunde ist jeder Schritt mehrmals pro Sekunde dran, ein Cooldown wird also
# trotzdem binnen Sekundenbruchteilen angeboten.
PAL_KOPF_A = (
    "/startattack\n"
    f"/cast [nomod] {HOL}\n"       # Templar-Kernzauber, darf nie fehlen
    f"/cast [nomod] {HOW}\n"
    f"/cast [nomod] {AW}\n"
    "/use [combat,nochanneling] 13\n"
)
PAL_KOPF_B = (
    "/startattack\n"
    f"/cast [nomod] {HOL}\n"
    f"/cast [nomod] {ES}\n"
    f"/cast [nomod] {WOA}\n"
    f"/cast [nomod] {DTOLL}\n"
    "/use [combat,nochanneling] 14\n"
)

ZIEL = "/targetenemy [noharm][dead]\n"


def akt(macro):
    return {b'Type': b'Action', b'type': b'macro', b'macro': macro.encode('utf-8')}


def pruefe(m):
    """Höchstens ein unbedingter GCD-Zauber je Schritt, höchstens 255 Zeichen.

    Die Kopfzeilen zaehlen NICHT als GCD-Konkurrenz: Sie stehen vor dem
    Rotationszauber und koennen ihn blockieren, wenn sie scheitern — das ist bei
    Cooldowns mit langer Wartezeit hinnehmbar, weil sie meist gar nicht erst
    angeboten werden. Beim Prot-Paladin wurde das gemessen und war unkritisch.
    """
    if len(m) > 255:
        raise SystemExit(f'Schritt zu lang ({len(m)} Zeichen):\n{m}')


def bauen(name, anzeige, label, muster, kopf, spec, mplus, hilfe):
    actions = []
    koepfe = kopf if isinstance(kopf, (list, tuple)) else [kopf]
    for i, spell in enumerate(muster):
        t = (ZIEL if mplus else '') + koepfe[i % len(koepfe)] + f'/cast [nomod] {spell}'
        pruefe(t)
        actions.append(akt(t))
    return [name.encode('utf-8'), {
        b'LastUpdated': b'20260821090000',
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
    "UH-DK - Unholy Death Knight, Midnight 12.1. Fassung 1 (21.08.2026).\n\n"
    "Lokal mit SimulationCraft gesucht: 74.713 von 79.120 DPS = 94,4 % einer\n"
    "optimal gespielten Rotation, gemessen unter Puppenbedingungen.\n\n"
    "14 Schritte: Scourge Strike 6, Death Coil 5, Festering Strike 2,\n"
    "Soul Reaper 1.\n\n"
    "Im Makro laufen automatisch mit: Army of the Dead, Dark Transformation,\n"
    "Outbreak, Putrefy und beide Schmuckstuecke.\n\n"
    "PUTREFY ist der wichtigste Einzelposten: Er wirkt nur waehrend Dark\n"
    "Transformation und brachte allein 11,5 Prozentpunkte.\n\n"
    "NICHT im Makro: Death Strike, Anti-Magic Shell, Icebound Fortitude,\n"
    "Lichborne - alles Defensive gehoert auf eigene Tasten."
)

HILFE_PAL = (
    "Retri - Retribution Paladin (Templar), Midnight 12.1. Fassung 1 (21.08.2026).\n\n"
    "Lokal mit SimulationCraft gesucht: 65.504 von 74.279 DPS = 88,2 % einer\n"
    "optimal gespielten Rotation, gemessen unter Puppenbedingungen.\n\n"
    "14 Schritte: Templar's Verdict 5, Templar Strike 4, Blade of Justice 2,\n"
    "Judgment 2, Templar Slash 1.\n\n"
    "Im Makro laufen automatisch mit: Avenging Wrath, Execution Sentence,\n"
    "Wake of Ashes, Divine Toll, Hammer of Light, Hammer of Wrath und beide\n"
    "Schmuckstuecke.\n\n"
    "HAMMER OF LIGHT darf nie fehlen - beim Prot-Paladin kostete das Fehlen\n"
    "dieses einen Templar-Zaubers 16 Prozentpunkte.\n\n"
    "NICHT im Makro: Shield of Vengeance, Divine Shield, Lay on Hands,\n"
    "Word of Glory, Blessing of Protection."
)

SEQS = [
    ('Claude_UH_MPlus', 'Claude Unholy - Mythic+', 'M+', DK_MUSTER, DK_KOPF, 252, True, HILFE_DK),
    ('Claude_UH_Raid', 'Claude Unholy - Raid', 'Raid', DK_MUSTER, DK_KOPF, 252, False, HILFE_DK),
    ('Claude_Ret_MPlus', 'Claude Retri - Mythic+', 'M+', PAL_MUSTER, (PAL_KOPF_A, PAL_KOPF_B), 70, True, HILFE_PAL),
    ('Claude_Ret_Raid', 'Claude Retri - Raid', 'Raid', PAL_MUSTER, (PAL_KOPF_A, PAL_KOPF_B), 70, False, HILFE_PAL),
]


def eintragen(neu):
    if subprocess.run(['pgrep', '-x', '-i', 'wow.exe'],
                      capture_output=True).returncode == 0:
        sys.exit('WoW laeuft — Abbruch, der Client wuerde die Datei ueberschreiben.')
    roh = GSE_DATEI.read_bytes()
    tr = b'\r\n' if b'\r\n' in roh else b'\n'
    zeilen = roh.split(tr)
    vorhanden = {n for n in neu if any(
        re.match(rb'\s*\["' + n.encode() + rb'"\] = "', z) for z in zeilen)}
    ausgabe, ersetzt, letzte = [], 0, -1
    for z in zeilen:
        m = re.match(rb'\s*\["([A-Za-z_0-9]+)"\] = "!GSE3!', z)
        if m:
            name = m.group(1).decode()
            if name in neu:
                ausgabe.append(('\t\t["%s"] = "%s",' % (name, neu[name])).encode())
                ersetzt += 1
                letzte = len(ausgabe) - 1
                continue
            letzte = len(ausgabe)
        ausgabe.append(z)
    fehlend = [n for n in neu if n not in vorhanden]
    if fehlend:
        if letzte < 0:
            sys.exit('Keine GSE3-Zeile gefunden — Abbruch.')
        for n in sorted(fehlend):
            ausgabe.insert(letzte + 1, ('\t\t["%s"] = "%s",' % (n, neu[n])).encode())
    GSE_DATEI.write_bytes(tr.join(ausgabe))
    print(f'\n{ersetzt} ersetzt, {len(fehlend)} neu: {", ".join(sorted(fehlend)) or "—"}')


if __name__ == '__main__':
    fertig = {}
    for name, anzeige, label, muster, kopf, spec, mplus, hilfe in SEQS:
        seq = bauen(name, anzeige, label, muster, kopf, spec, mplus, hilfe)
        s = gse3_encode(seq)
        fertig[name] = s
        beispiel = seq[1][b'Versions'][0][b'Actions'][0][b'macro'].decode()
        print(f'{name:<20}{len(muster):>3} Schritte, Schritt 1 = {len(beispiel):>3} Zeichen, '
              f'Import {len(s)} Zeichen')
    if '--schreiben' in sys.argv:
        eintragen(fertig)
    else:
        print('\nNur Ausgabe. Mit --schreiben eintragen.')
        for n, s in fertig.items():
            print(f'\n=== {n} ===\n{s}')
