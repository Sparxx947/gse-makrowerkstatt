#!/usr/bin/env python3
"""Wertet ein WoW-CombatLog aus: was eine GSE-Sequenz TATSAECHLICH gewirkt hat.

WOZU
====
Bis 2026-08-16 gab es zwei Erkenntnisquellen und zwischen ihnen eine Luecke:

  Raidbots-Sim   sagt, was bei perfektem Spiel herauskaeme
  DPS an der Puppe   sagt, was unterm Strich herauskam - eine einzige Zahl

Was dazwischen fehlte: WELCHE Casts die Sequenz ingame wirklich erzeugt. Das
musste ich modellieren, und das Modell lag mehrfach daneben (siehe
project_wow_gse_jaeger, zwei zurueckgezogene Fassungen). Das CombatLog schliesst
die Luecke - es steht darin, Cast fuer Cast.

Damit laesst sich endlich direkt beantworten:
  - Kommt Kill Command wirklich auf seine Casts, oder verhungert er?
  - Wie lange steht Beast Cleave / Bestial Wrath im echten Spiel?
  - Wo genau verliert die Sequenz gegen den Sim - Zauber fuer Zauber?

VORAUSSETZUNG
=============
`ADVANCED_LOG_ENABLED,1` im Kopf des Logs, also erweitertes Kampfprotokoll.
Steht bei der Spieler auf 1. Aufzeichnung im Spiel mit /combatlog starten.

BEDIENUNG
=========
    log-casts.py <logdatei> [--spieler <Charaktername>] [--sim datei.json] [--ab HH:MM] [--bis HH:MM]

Ohne --spieler wird der haeufigste Wirker im Log genommen.
Mit --sim wird gegen die Casts eines Raidbots-Reports (data.json) verglichen.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Das Zeitfeld steht vorn: "8/13/2026 20:48:35.0412  EVENT,..."
KOPF = re.compile(r'^(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+)\.(\d+)\s{2}(.*)$')


def felder(rest: str) -> list[str]:
    """Zerlegt eine CombatLog-Zeile an Kommas, respektiert Anfuehrungszeichen."""
    out, akt, quote = [], [], False
    for z in rest:
        if z == '"':
            quote = not quote
        elif z == ',' and not quote:
            out.append(''.join(akt))
            akt = []
        else:
            akt.append(z)
    out.append(''.join(akt))
    return out


def passt(name: str, gesucht: str | None) -> bool:
    """Im Log heisst der Charakter '<Name>-<Realm>-EU'. Ein Aufruf mit blossem
    '<Name>' soll trotzdem treffen, deshalb Vergleich ohne Realm-Suffix."""
    if gesucht is None:
        return True
    return name == gesucht or name.split('-')[0] == gesucht.split('-')[0]


def lies(pfad: Path, spieler: str | None, ab: str | None, bis: str | None):
    casts = collections.Counter()
    ids: dict[str, str] = {}
    wirker = collections.Counter()
    auren: dict[str, list] = collections.defaultdict(list)   # Zauber -> [(auf, ab)]
    offen: dict[str, datetime] = {}
    erste = letzte = None
    advanced = None
    marken: list = []

    with open(pfad, 'rb') as f:
        for rohzeile in f:
            zeile = rohzeile.decode('utf-8', 'replace').rstrip('\r\n')
            m = KOPF.match(zeile)
            if not m:
                continue
            mo, tg, jr, st, mi, se, ms, rest = m.groups()
            t = datetime(int(jr), int(mo), int(tg), int(st), int(mi), int(se),
                         int(ms.ljust(6, '0')[:6]))
            f_ = felder(rest)
            ereignis = f_[0]

            if ereignis == 'COMBAT_LOG_VERSION':
                if 'ADVANCED_LOG_ENABLED' in rest:
                    advanced = rest.split('ADVANCED_LOG_ENABLED,')[1][0]
                continue

            if ab and t.strftime('%H:%M') < ab:
                continue
            if bis and t.strftime('%H:%M') > bis:
                continue

            if ereignis in ('ENCOUNTER_START', 'CHALLENGE_MODE_START'):
                marken.append(('start', t, f_[2] if len(f_) > 2 else '?'))
                continue
            if ereignis in ('ENCOUNTER_END', 'CHALLENGE_MODE_END'):
                marken.append(('ende', t, f_[2] if len(f_) > 2 else '?'))
                continue
            if len(f_) < 11:
                continue

            quelle = f_[2]          # sourceName
            zauber_id, zauber = f_[9], f_[10]
            if not zauber:
                continue

            if ereignis == 'SPELL_CAST_SUCCESS':
                wirker[quelle] += 1
                if passt(quelle, spieler):
                    casts[zauber] += 1
                    ids[zauber] = zauber_id
                    erste = erste or t
                    letzte = t
            elif ereignis in ('SPELL_AURA_APPLIED', 'SPELL_AURA_REFRESH'):
                if passt(f_[6], spieler) or passt(quelle, spieler):
                    if zauber in offen and ereignis == 'SPELL_AURA_REFRESH':
                        auren[zauber].append((offen[zauber], t))
                    offen[zauber] = offen.get(zauber, t) if ereignis == 'SPELL_AURA_REFRESH' else t
            elif ereignis == 'SPELL_AURA_REMOVED':
                if zauber in offen:
                    auren[zauber].append((offen.pop(zauber), t))

    for z, start in offen.items():
        if letzte:
            auren[z].append((start, letzte))
    return casts, ids, wirker, auren, erste, letzte, advanced, marken


def uptime(fenster: list, erste: datetime, letzte: datetime) -> float:
    """Vereinigt ueberlappende Fenster und gibt den Anteil an der Kampfzeit."""
    if not fenster or not erste or letzte <= erste:
        return 0.0
    fenster = sorted(fenster)
    zus, (a, b) = [], fenster[0]
    for x, y in fenster[1:]:
        if x <= b:
            b = max(b, y)
        else:
            zus.append((a, b))
            a, b = x, y
    zus.append((a, b))
    gesamt = sum((y - x).total_seconds() for x, y in zus)
    return gesamt / (letzte - erste).total_seconds() * 100


def sim_casts(pfad: Path) -> dict[str, float]:
    d = json.loads(pfad.read_text())
    p = d['sim']['players'][0]
    out = {}
    for s in p['stats']:
        n = s.get('num_executes', {}).get('mean', 0)
        if n >= 0.5:
            out[s['name']] = n
    return out


def normal(name: str) -> str:
    return re.sub(r'[^a-z]', '_', name.lower()).strip('_')


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('logdatei', type=Path)
    p.add_argument('--spieler', help='Name des Charakters (Standard: haeufigster Wirker)')
    p.add_argument('--sim', type=Path, help='Raidbots data.json zum Vergleich')
    p.add_argument('--ab', help='nur ab dieser Uhrzeit, HH:MM')
    p.add_argument('--bis', help='nur bis dieser Uhrzeit, HH:MM')
    p.add_argument('--auren', type=int, default=8, help='wieviele Auren zeigen')
    p.add_argument('--kaempfe', action='store_true',
                   help='Boss- und M+-Abschnitte des Logs auflisten (mit Uhrzeiten)')
    p.add_argument('--wer', action='store_true',
                   help='nur auflisten, wer im Log Zauber wirkt, dann beenden')
    a = p.parse_args()

    if not a.logdatei.exists():
        sys.exit(f'nicht gefunden: {a.logdatei}')

    if a.kaempfe:
        *_, marken = lies(a.logdatei, None, None, None)
        if not marken:
            print('Keine Boss- oder M+-Abschnitte im Log.')
            return
        print(f'Abschnitte in {a.logdatei.name}:\n')
        print(f"  {'Nr':<4}{'von':<10}{'bis':<10}{'Dauer':>8}   Name")
        nr, start, name = 0, None, ''
        for art, zeit, bez in marken:
            if art == 'start':
                start, name = zeit, bez
            elif start:
                nr += 1
                d = (zeit - start).total_seconds()
                print(f'  {nr:<4}{start:%H:%M:%S}  {zeit:%H:%M:%S}  {d/60:>6.1f}m   {name}')
                print(f"      -> --ab {start:%H:%M} --bis {zeit:%H:%M}")
                start = None
        return

    if a.wer:
        *_, wirker, _, _, _, _, _ = [None] + list(lies(a.logdatei, None, a.ab, a.bis))
        print(f'Wirker in {a.logdatei.name} (Casts):\n')
        for n, c in wirker.most_common(30):
            print(f'  {n:<28}{c:>7}')
        return

    # Erster Durchgang ohne Spielerfilter, um den Hauptwirker zu finden
    if not a.spieler:
        *_, wirker, _, _, _, _, _ = [None] + list(lies(a.logdatei, None, a.ab, a.bis))
        if not wirker:
            sys.exit('keine SPELL_CAST_SUCCESS-Zeilen gefunden - '
                     'ist das erweiterte Kampfprotokoll an?')
        a.spieler = wirker.most_common(1)[0][0]
        print(f'(kein --spieler angegeben, nehme haeufigsten Wirker: {a.spieler})\n')

    casts, ids, _, auren, erste, letzte, advanced, marken = lies(
        a.logdatei, a.spieler, a.ab, a.bis)
    if not casts:
        sys.exit(f'keine Casts von "{a.spieler}" im gewaehlten Zeitraum')

    dauer = (letzte - erste).total_seconds() or 1
    gesamt = sum(casts.values())
    print(f'{a.logdatei.name}')
    print(f'Spieler {a.spieler} | {erste:%d.%m. %H:%M:%S} bis {letzte:%H:%M:%S} '
          f'= {dauer/60:.1f} min | erweitertes Log: '
          f'{"ja" if advanced == "1" else "NEIN - Werte unvollstaendig"}')
    print()

    soll = sim_casts(a.sim) if a.sim else {}
    if soll:
        # Sim-Casts auf die Logdauer umrechnen (Sim laeuft 300 s)
        soll = {k: v * dauer / 300 for k, v in soll.items()}

    kopf = f'{"Zauber":<26}{"Casts":>7}{"/min":>8}{"Anteil":>9}'
    if soll:
        kopf += f'{"Sim":>8}{"Diff":>8}'
    print(kopf)
    print('-' * len(kopf))
    for z, c in casts.most_common(18):
        zeile = f'{z:<26}{c:>7}{c/dauer*60:>8.1f}{c/gesamt*100:>8.1f}%'
        if soll:
            s = soll.get(normal(z))
            zeile += f'{s:>8.1f}{c-s:>+8.1f}' if s else f'{"-":>8}{"-":>8}'
        print(zeile)
    print(f'{"GESAMT":<26}{gesamt:>7}{gesamt/dauer*60:>8.1f}')

    if auren:
        print(f'\n{"Aura":<26}{"Uptime":>8}{"Anwendungen":>13}')
        print('-' * 47)
        rang = sorted(((uptime(f, erste, letzte), z, len(f)) for z, f in auren.items()),
                      reverse=True)
        for u, z, n in rang[:a.auren]:
            if u >= 1:
                print(f'{z:<26}{u:>7.1f}%{n:>13}')


if __name__ == '__main__':
    main()
