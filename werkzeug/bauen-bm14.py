#!/usr/bin/env python3
"""BM-Jaeger, FASSUNG 14 - gefunden mit dem LOKALEN SimulationCraft.

WARUM ES FASSUNG 12 SCHLAEGT (2026-08-20)
=========================================
Die fruehere Suche lief mit der falschen Klickrate. echter Wert steht in
GSE_C.msClickRate und ist 100 ms = 10 Klicks/s - gerechnet wurde aber mit 6/s,
weil ich die Rate aus dem Kampflog geschaetzt hatte (dort erscheinen nur die
protokollierten Zauberversuche, nicht jeder Klick).

Bei der richtigen Rate faellt Fassung 12 von Rang 1 auf Rang 25 von 190.

Zusaetzlich hatte das erste Suchraster Bestial Wrath auf 1-2 Plaetze begrenzt.
DREI Plaetze sind besser - alle Sieger der neuen Suche haben BW3.

    Einzelziel  KC2 BS2 CS1 BW3, 8 Schritte     +4,4 % gegen Fassung 12
    AoE         WT5 KC3 BS3 CS1 BW3, 15         +3,1 % gegen Fassung 12

GEPRUEFT UND VERWORFEN
======================
- Anordnung: 70 Anordnungen bei fester Gewichtung. Die gleichmaessige Verteilung
  ist Rang 1 von 70 - die Spanne zur schlechtesten betraegt aber 15,7 %.
- Fuellerregel aus Fassung 13 ("zwei Fueller vor jedem Kill Command"): widerlegt.
  F13 lag messbar zurueck (ST -10,7 %, AoE -7,6 %), weil sie BW auf 1 Platz senkte.
  Die Pruefung ist hier bewusst NICHT mehr eingebaut.
- Hoehere Klickrate: 20/s bringt Fassung 12 +3,9 %, die neue Fassung nur noch
  +0,4 % ueber ihren 10/s-Wert. Der Sequenzwechsel allein holt fast alles.

Rueckweg: die Fassung-12-Sequenzen ohne Namenszusatz bleiben unangetastet.
"""
import re
import shutil
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
GSE = Path('BITTE_ANPASSEN/WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua')

KC, BS, CS, BW, WT = 34026, 56641, 185358, 19574, 1264359
MEND, REVI, CALL = 136, 982, 883
INTI, CTRS = 19577, 147362

# Nur noch Slot 13 (oberes Trinket). Slot 14 hat der Spieler am 2026-08-19 bewusst aus
# der Automatik genommen - das zweite Trinket wird von Hand gezuendet.
TRINKET = "/use [combat,nochanneling] 13\n"
MOD = (f"/cast [mod:shift,harm] {CTRS}\n"
       f"/cast [mod:alt,@pet] {MEND}\n"
       f"/cast [mod:ctrl,harm] {INTI}\n"
       f"/stopmacro [mod]\n")
PET = f"/cast [@pet,dead] {REVI}; [nopet,nomounted] {CALL}\n/petattack\n/startattack\n"
ZIEL = "/targetenemy [noharm][dead]\n"

# FASSUNG 13 (2026-08-20) - Nature's Ally: JEDER Kill Command braucht einen
# Fueller (Barbed oder Cobra Shot) davor, sonst trifft er nur mit 73 % Schaden.
# Gemessen an der Puppe: 20 von 80 Kill Commands kamen ohne Fueller, davon 18 mal
# direkt hintereinander. Kosten: 21.510 Schaden je Fall = 1,3 Prozentpunkte.
# Ursache: Zwischen zwei KC-Plaetzen lag nur EIN Fueller. Faellt der aus (Barbed
# Shot auf Cooldown, Cobra Shot ohne Fokus), folgt KC direkt auf KC. Bestial
def _verteile(n, plaetze):
    """Gleichmaessig, Cooldowns zuerst - genau die Anordnung, mit der gesimmt wurde."""
    muster = [None] * n
    for spell, anzahl in plaetze:
        for k in range(anzahl):
            wunsch = int(n * (k + 0.5) / anzahl) % n
            for versatz in range(n):
                pos = (wunsch + versatz) % n
                if muster[pos] is None:
                    muster[pos] = spell
                    break
    return muster

ST = _verteile(8, [(BW, 3), (KC, 2), (BS, 2), (CS, 1)])
AOE = _verteile(15, [(BW, 3), (KC, 3), (BS, 3), (WT, 5), (CS, 1)])

HILFE_ST = (
    "Midnight 12.1 - Beast Mastery, EINZELZIEL. FASSUNG 14.\n\n"
    "8 Schritte: Bestial Wrath 3, Kill Command 2, Barbed Shot 2, Cobra Shot 1\n\n"
    "Gefunden mit lokalem SimulationCraft 1210-01 (12.1.0.69382): 190 Gewichtungen,\n"
    "danach Feinentscheid ueber neun Klickraten von 9 bis 22 Anschlaegen je Sekunde.\n\n"
    "Gegen Fassung 12 rund +4,4 Prozent bei der eingestellten Klickrate von 10/s.\n"
    "Der Gewinn kommt aus DREI Plaetzen fuer Bestial Wrath - das alte Suchraster\n"
    "liess hoechstens zwei zu.\n\n"
    "TRINKETS: Nur Slot 13 feuert automatisch mit, Slot 14 von Hand zuenden.\n"
    "RUECKWEG: Claude_BM_Raid_ST bzw. _MPlus_ST sind unveraendert Fassung 12.\n"
)

HILFE_AOE = (
    "Midnight 12.1 - Beast Mastery, MEHRERE ZIELE. FASSUNG 14.\n\n"
    "15 Schritte: Wild Thrash 5, Bestial Wrath 3, Kill Command 3,\n"
    "Barbed Shot 3, Cobra Shot 1\n\n"
    "An fuenf Zielen gesimmt, M+-Skillung: rund +3,1 Prozent gegen Fassung 12.\n\n"
    "ACHTUNG: In der RAID-Skillung ist Wild Thrash NICHT geskillt - dort laufen\n"
    "5 der 15 Plaetze ins Leere. Diese Sequenz nur mit der M+-Skillung klicken.\n\n"
    "RUECKWEG: Claude_BM_Raid_AoE bzw. _MPlus_AoE sind unveraendert Fassung 12.\n"
)


def akt(macro):
    return {b'Type': b'Action', b'type': b'macro', b'macro': macro.encode('utf-8')}


def bauen(name, label, muster, mplus, hilfe):
    actions = []
    for i, spell in enumerate(muster):
        kopf = MOD
        if i == 0:
            if mplus:
                kopf += ZIEL
            kopf += PET
        actions.append(akt(kopf + ("" if i == 0 else TRINKET) + f"/cast {spell}"))
    return [name.encode('utf-8'), {
        b'LastUpdated': b'20260819123000',
        b'MetaData': {
            b'Author': b'Claude (fuer der Spieler)', b'Default': 1,
            b'Dependencies': {b'Macros': [], b'Sequences': [], b'Variables': []},
            b'EnforceCompatability': True, b'GSEVersion': 3326,
            b'Help': hilfe.encode('utf-8'), b'ManualIntervention': True,
            b'Name': name.encode('utf-8'), b'SpecID': 253, b'TOC': 120100,
        },
        b'Versions': [{b'Actions': actions, b'InbuiltVariables': [],
                       b'Label': label.encode('utf-8')}],
        b'WeakAuras': [],
    }]


SEQUENZEN = {
    'Claude_BM_MPlus_ST_v14':  (ST,  True,  'M+ Einzelziel, Fassung 14',   HILFE_ST),
    'Claude_BM_Raid_ST_v14':   (ST,  False, 'Raid Einzelziel, Fassung 14', HILFE_ST),
    'Claude_BM_MPlus_AoE_v14': (AOE, True,  'M+ AoE, Fassung 14',          HILFE_AOE),
    'Claude_BM_Raid_AoE_v14':  (AOE, False, 'Raid AoE, Fassung 14',        HILFE_AOE),
}
# Diese Altlasten werden entfernt - sie sind durch die Suche ueberholt.
ENTFERNEN = re.compile(rb'(?!)')   # nichts loeschen - Fassung 12 ist der Rueckweg


def fueller_pruefen(muster, name):
    """Nature's Ally: vor JEDEM Kill Command muessen mindestens zwei Fueller
    (Barbed oder Cobra Shot) liegen. Bestial Wrath und Wild Thrash zaehlen
    NICHT - sie buffen den Kill Command nicht. Ein ungebuffter Kill Command
    trifft nur mit 73 % (an der Puppe gemessen, 2026-08-20)."""
    F = {BS, CS}
    n = len(muster)
    for i, x in enumerate(muster):
        if x != KC:
            continue
        anzahl = 0
        for k in range(1, n):
            j = (i - k) % n
            if muster[j] == KC:
                break
            if muster[j] in F:
                anzahl += 1
        if anzahl < 2:
            raise SystemExit(f"{name}: Kill Command an Platz {i+1} hat nur "
                             f"{anzahl} Fueller davor - Fassung 13 verlangt zwei.")
    return True


def main() -> None:
    if subprocess.run(['pgrep', '-x', '-i', 'wow.exe'],
                      capture_output=True).returncode == 0:
        sys.exit("WoW laeuft - der Client haelt die SavedVariables im Speicher "
                 "und wuerde die Datei beim Beenden ueberschreiben. Abbruch.")

    # fueller_pruefen bewusst NICHT aufgerufen: die Regel stammt aus Fassung 13
    # und ist durch die Messung vom 2026-08-20 widerlegt.
    neu = {n: gse3_encode(bauen(n, lab, mu, mp, h))
           for n, (mu, mp, lab, h) in SEQUENZEN.items()}

    for n, s in neu.items():
        print(f"{n:<24}{len(s):>6} Zeichen Import-String")

    if '--schreiben' not in sys.argv:
        print("\nProbelauf - nichts geschrieben. Mit --schreiben eintragen.")
        return

    roh = GSE.read_bytes()
    tr = b"\r\n" if b"\r\n" in roh else b"\n"
    print(f"\nZeilentrenner: {'CRLF' if tr == b'\r\n' else 'LF'}")
    zeilen = roh.split(tr)

    # Namen, die es schon gibt, werden ersetzt; neue werden EINGEFUEGT.
    # Ohne den Einfuege-Zweig legt das Skript neue Sequenzen still nicht an -
    # es ersetzt nur, was schon dasteht.
    vorhanden = {n for n in neu if any(
        re.match(rb'\s*\["' + n.encode() + rb'"\] = "', z) for z in zeilen)}
    fehlend = [n for n in neu if n not in vorhanden]

    ersetzt, entfernt, letzte_claude = 0, 0, -1
    ausgabe = []
    for z in zeilen:
        m = re.match(rb'\s*\["(Claude_BM[^"]+)"\] = "', z)
        if m:
            name = m.group(1).decode()
            if name in neu:
                ausgabe.append(('\t\t["%s"] = "%s",' % (name, neu[name])).encode('utf-8'))
                ersetzt += 1
                letzte_claude = len(ausgabe) - 1
                continue
            if ENTFERNEN.match(z):
                entfernt += 1
                continue
            letzte_claude = len(ausgabe)
        ausgabe.append(z)

    if fehlend:
        if letzte_claude < 0:
            sys.exit("Keine Claude-Sequenz gefunden - Einfuegestelle unklar, Abbruch.")
        for n in sorted(fehlend):
            ausgabe.insert(letzte_claude + 1,
                           ('\t\t["%s"] = "%s",' % (n, neu[n])).encode('utf-8'))
        print(f"{len(fehlend)} neue Sequenzen angelegt: {', '.join(sorted(fehlend))}")

    GSE.write_bytes(tr.join(ausgabe))
    print(f"{ersetzt} Sequenzen ersetzt, {entfernt} alte v2/v3-Zeilen entfernt.")


if __name__ == '__main__':
    main()
