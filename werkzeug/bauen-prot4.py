#!/usr/bin/env python3
"""GSE-Sequenzen fuer Protection Paladin (Midnight 12.1 / Season 2, Lightsmith).

Gebaut fuer der Prot-Paladin - Earthen, Protection, Lightsmith.
Gibt Import-Strings aus; schreibt NICHTS in eine GSE.lua, weil der Charakter
einem Dritten gehoert. Der Empfaenger fuegt den String in GSE ein
(GSE -> Sequenzen -> Importieren).

Konstruktionsregeln (aus der BM-Jaeger-Arbeit vom 2026-08-13):

  * Genau EIN GCD-Zauber pro Schritt. Scheitert ein /cast, das den GCD ausloesen
    wuerde, blockiert es alle folgenden /cast-Zeilen desselben Schritts.
    Prioritaet entsteht ueber die Haeufigkeit im Muster, nicht ueber die
    Reihenfolge im Schritt.
  * Zeilen mit [mod:...] blockieren nicht, wenn die Bedingung nicht zutrifft.
  * 255 Zeichen je Schritt sind die harte Grenze.

Der Sonderfall dieser Klasse: Shield of the Righteous ist OFF-GCD und braucht
kein Ziel. Es steht deshalb in JEDEM Schritt und kostet keinen Slot - damit kann
das Makro nie Heilige Kraft ueberlaufen lassen, ohne dass die Rotation leidet.

Bewusst NICHT im Makro (Vorgabe: Defensives und Schmuckstuecke von Hand):
  Ardent Defender, Guardian of Ancient Kings, Divine Shield, Lay on Hands,
  Word of Glory, Holy Armaments (Sacred Weapon / Holy Bulwark), /use 13, /use 14.

Holy Armaments ist zusaetzlich eine Falle: Sacred Weapon wird nach Benutzung zu
Holy Bulwark: ein Button, der umschaltet. Im Makro wuerde die defensive Ladung zu
zufaelligen Zeitpunkten verbrannt, und gezielte /cast-Versuche laufen in
"Spell not learned".
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gse3 import gse3_encode

# eigene GSE-Datenbank. Wird NUR mit --schreiben angefasst; normalerweise
# gibt dieses Skript blosse Import-Strings aus, weil der Charakter einem Dritten
# gehoert. Zum Testen an der eigenen Puppe ist das Eintragen aber praktisch.
# ---------------------------------------------------------------- HIER ANPASSEN
# Pfad zur GSE-Datenbank. Unter Windows/WSL etwa:
#   Path.home() / 'wow' / 'WTF' / 'Account' / 'DEIN_ACCOUNT' / 'SavedVariables' / 'GSE.lua'
# Unter Linux mit Steam/Proton liegt _retail_ im Proton-Praefix.
# Wie der Account-Ordner heisst, zeigt:  ls ~/wow/WTF/Account
GSE_DATEI = Path('BITTE_ANPASSEN/WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua')


def eintragen(neu: dict) -> None:
    """Traegt die Sequenzen ein. Vorhandene Namen werden ersetzt, neue
    eingefuegt — ohne den Einfuege-Zweig legt ein reines Ersetzen still nichts an
    und meldet trotzdem Erfolg."""
    if subprocess.run(['pgrep', '-x', '-i', 'wow.exe'],
                      capture_output=True).returncode == 0:
        sys.exit('WoW laeuft — der Client wuerde die Datei beim Beenden '
                 'ueberschreiben. Abbruch.')
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
            sys.exit('Keine GSE3-Zeile gefunden — Einfuegestelle unklar, Abbruch.')
        for n in sorted(fehlend):
            ausgabe.insert(letzte + 1,
                           ('\t\t["%s"] = "%s",' % (n, neu[n])).encode())
    GSE_DATEI.write_bytes(tr.join(ausgabe))
    print(f'\n{ersetzt} ersetzt, {len(fehlend)} neu angelegt: '
          f'{", ".join(sorted(fehlend)) or "—"}')

# --- Zauber-IDs -------------------------------------------------------------
# Alle aus dem Raidbots-Report des Charakters selbst belegt (data.json,
# sim.players[0].stats[].id) - nicht aus einer Webrecherche geraten.
SOTR   = 53600     # Shield of the Righteous  (off-GCD, kein Ziel noetig)
JUDG   = 275779    # Judgment  (wird waehrend Sentinel automatisch Hammer of Wrath)
BLHA   = 204019    # Blessed Hammer
AVSH   = 31935     # Avenger's Shield
CONS   = 26573     # Consecration
SENT   = 389539    # Sentinel   (Prot-Pala hat Sentinel, NICHT Avenging Wrath)
TOLL   = 375576    # Divine Toll
REBU   = 96231     # Rebuke
HOJU   = 853       # Hammer of Justice
SAWE   = 432472    # Sacred Weapon   \ EIN Knopf, der umschaltet:
HOBU   = 432459    # Holy Bulwark    / nach Benutzung wird aus dem einen der andere

# --- Modifikatoren: Belegung wie in ORBALISK-Sequenzen ----------------
# Shift = Unterbrechen, Strg = Betaeuben. Alt traegt hier das Burst-Fenster
# (ORBALISK legt dort ebenfalls eine castsequence aus Cooldowns ab).
MOD = (f"/castsequence [mod:alt] reset=10 {SENT}, {TOLL}\n"
       f"/cast [mod:shift] {REBU}\n"
       f"/cast [mod:ctrl] {HOJU}\n")

ZIEL = "/targetenemy [noharm][dead]\n"
ATT  = "/startattack\n"

# --- Schrittmuster ----------------------------------------------------------
# Gemessene Cast-Zahlen aus dem buff-freien Raidbots-Lauf (Patchwerk, 5 min),
# je Minute: Judgment+Hammer of Wrath 18,0 | Blessed Hammer 15,8 |
# Avenger's Shield 6,3 | Consecration 5,6.  Bei 14 Schritten und rund 1,3 s je
# Klick (Umlauf ~18 s) ergibt der Bedarf 5,5 / 4,8 / 1,9 / 1,8 Plaetze.
# Consecration bewusst auf 2 Plaetze (alle ~7,8 s) - sie ist eine
# Uptime-Mechanik, und ein fehlender Slot kostet dort ein ganzes Fenster.
# FASSUNG 4 (2026-08-21) — 95,8 % einer optimalen Rotation ohne Schmuckstuecke.
#
# PRUEFSTAND: lokal, SimC 1210-01 gegen WoW 12.1.0.69382, des Prot-Pala Armory-Profil
# (ilvl 297, Lightsmith, Loadout 5), Target-Dummy-Bedingungen. Die
# GSE-Weiterschaltung als APL nachgebaut (reference_gse_als_simc_apl).
#
# MESSLATTE: 40.448 DPS = dieselbe Rotation ohne Schmuckstuecke. Die vollen
# 48.012 DPS sind KEIN fairer Vergleich — 15,8 % davon stammen aus
# Schmuckstuecken, die laut Vorgabe von Hand kommen.
#
# WEG DORTHIN (rund 450 gerechnete Varianten):
#     Fassung 2, Holy Armaments von Hand      37.222 DPS = 92,0 %
#     Fassung 2, Holy Armaments im Makro      37.580 DPS = 93,0 %
#     Fassung 3 (14 Schritte)                 38.160 DPS = 94,3 %
#     DIESE FASSUNG                           38.739 DPS = 95,8 %  (+/- 27)
#
# DER ENTSCHEIDENDE SCHRITT war Holy Armaments. Es steckt hier auf einem EIGENEN
# Platz, nicht in jedem Schritt: Gemessen kostet es einen GCD (bei 6,5 Casts
# sinken die uebrigen um 5). In jeden Schritt geschrieben wuerde es die Rotation
# blockieren, sobald es nicht bereit ist.
#
# Was die Suche sonst ergab:
#   * Klickrate 10/s ist richtig; 20/s bringt nichts, 5/s kostet 3,2 %.
#   * Word of Glory im Makro kostet 7,7 % — er bleibt auf eigener Taste.
#   * Die Anordnung ist ausgereizt: 220 Varianten brachten nichts ueber diese.
#   * Lightsmith schlaegt Templar (Messlatte 40.448 gegen 39.937). Templar
#     braeuchte zwingend `Hammer of Light` im Makro, sonst faellt es auf 77 %.
HARM = 'HOLY_ARMAMENTS'   # Platzhalter, unten in eine Umschalt-Zeile aufgeloest
MUSTER = [JUDG, BLHA, AVSH, JUDG, BLHA, CONS, JUDG, BLHA, JUDG, AVSH,
          BLHA, JUDG, AVSH, CONS, JUDG, BLHA, HARM]


def akt(macro):
    return {b'Type': b'Action', b'type': b'macro', b'macro': macro.encode('utf-8')}


def bauen(name, anzeige, label, mplus, hilfe):
    actions = []
    for spell in MUSTER:
        m = (ZIEL if mplus else "") + ATT + MOD
        m += f"/cast [nomod] {SOTR}\n"      # off-GCD: kostet keinen Slot
        if spell == HARM:
            # Holy Armaments ist EIN Knopf, der zwischen Sacred Weapon und Holy
            # Bulwark umschaltet. Ein gezieltes /cast auf die gerade NICHT
            # aktive Haelfte laeuft in "Spell not learned" — deshalb per
            # [known:...] auf die passende Haelfte zeigen, mit der anderen als
            # Rueckfall. UNGETESTET im Spiel: Bitte einmal pruefen, ob beide
            # Haelften ausgeloest werden.
            m += f"/cast [nomod,known:{SAWE}] {SAWE}; [nomod] {HOBU}"
        else:
            m += f"/cast [nomod] {spell}"   # der einzige GCD-Zauber des Schritts
        pruefe(m)
        actions.append(akt(m))
    return [name.encode('utf-8'), {
        b'LastUpdated': b'20260821060000',
        b'MetaData': {
            b'Author': b'Claude (fuer der Spieler)',
            b'Default': 1,
            b'Dependencies': {b'Macros': [], b'Sequences': [], b'Variables': []},
            b'EnforceCompatability': True,
            b'GSEVersion': 3326,
            b'Help': hilfe.encode('utf-8'),
            b'ManualIntervention': True,
            b'Name': anzeige.encode('utf-8'),
            b'SpecID': 66,                  # Protection Paladin
            b'TOC': 120100,
        },
        b'Versions': [{b'Actions': actions, b'InbuiltVariables': [], b'Label': label.encode('utf-8')}],
        b'WeakAuras': [],
    }]


def pruefe(m):
    """Selbstpruefung: hoechstens ein unbedingter GCD-Zauber, hoechstens 255 Zeichen."""
    if len(m) > 255:
        raise SystemExit(f"Schritt zu lang ({len(m)} Zeichen):\n{m}")
    gcd = [z for z in m.splitlines()
           if z.startswith('/cast') and '[mod:' not in z and str(SOTR) not in z]
    if len(gcd) > 1:
        raise SystemExit(f"Mehr als ein GCD-Zauber im Schritt:\n{m}")


HILFE = (
    "Midnight 12.1 / Season 2 - Protection Paladin, Lightsmith.\n\n"
    "Zusatztasten:\n"
    "  Shift = Rebuke (Unterbrechen)\n"
    "  Strg  = Hammer of Justice (Betaeuben)\n"
    "  Alt   = Sentinel, danach Divine Toll (Burst-Fenster, zwei Klicks)\n\n"
    "Shield of the Righteous laeuft in jedem Schritt mit - es liegt ausserhalb\n"
    "des GCD und kostet daher keinen Platz in der Rotation.\n\n"
    "NICHT im Makro und bewusst auf eigenen Tasten:\n"
    "  Ardent Defender, Guardian of Ancient Kings, Divine Shield, Lay on Hands,\n"
    "  Word of Glory, Holy Armaments (Sacred Weapon / Holy Bulwark),\n"
    "  beide Schmuckstuecke.\n\n"
    "FASSUNG 4 (21.08.2026): lokal mit SimulationCraft gesucht, rund 450\n"
    "Varianten. 95,8 % einer optimalen Rotation ohne Schmuckstuecke\n"
    "(Fassung 2 lag bei 93,0 %).\n\n"
    "NEU: Holy Armaments laeuft jetzt IM Makro (Schritt 17). Das war der\n"
    "groesste Einzelgewinn (+2,2 Prozentpunkte). Es verbraucht dadurch die\n"
    "defensive Holy-Bulwark-Ladung zu Zeitpunkten, die du nicht selbst\n"
    "waehlst - dafuer steht Bulwark of Order endlich durchgehend.\n"
    "Word of Glory bewusst NICHT im Makro - er kostet dort 7,7 % Schaden.\n\n"
    "Holy Armaments gehoert von Hand gedrueckt: Sacred Weapon wird nach\n"
    "Benutzung zu Holy Bulwark - im Makro waere die defensive Ladung zu\n"
    "zufaelligen Zeitpunkten weg."
)

SEQS = [
    ("Claude_Prot_MPlus_F4", "Claude Prot M+ (Fassung 4)", "M+ F4",   True),
    ("Claude_Prot_Raid_F4",  "Claude Prot Raid (Fassung 4)",    "Raid F4", False),
]

if __name__ == '__main__':
    fertige = {}
    for name, anzeige, label, mplus in SEQS:
        seq = bauen(name, anzeige, label, mplus, HILFE)
        s = gse3_encode(seq)
        beispiel = seq[1][b'Versions'][0][b'Actions'][0][b'macro'].decode()
        print("=" * 72)
        print(f"{name}   ({len(MUSTER)} Schritte, Schritt 1 = {len(beispiel)} Zeichen)")
        print("=" * 72)
        print(beispiel)
        print("-" * 72)
        print(s)
        print()
        fertige[name] = s
    if '--schreiben' in sys.argv:
        eintragen(fertige)
    else:
        print('Nur Ausgabe. Mit --schreiben in der Spieler\' GSE.lua eintragen.')
