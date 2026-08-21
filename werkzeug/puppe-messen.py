#!/usr/bin/env python3
"""puppe-messen.py — DPS und Rotationsqualität an der Übungspuppe.

Beantwortet die eine Frage, für die es einen sauberen Prüfstand braucht:
**Wie viel Prozent des Sim-Werts erreicht die Sequenz?**

DREI FALLEN, die je eine falsche Zahl erzeugt haben (2026-08-19)
================================================================
1. **Fremde schlagen auf dieselbe Puppe.** Ohne Filter kamen 129.765 DPS heraus
   statt 77.693 — 34 % des Schadens stammten von einem zweiten BM-Jäger und
   dessen Pets. Allein an einer Puppe zu stehen ist in der Stadt nicht möglich;
   der Filter muss es richten, nicht die Verabredung.
2. **Begleiter braucht BEIDE Erkennungswege.** `SPELL_SUMMON` findet die
   kurzlebigen Beschwoerungen (Dire Beast, Fenryr, Hati, Bear, Wyvern), die selbst
   nie zaubern; `ownerGUID` findet die dauerhaften Pets inklusive des zweiten aus
   Animal Companion. Mit nur einem Weg fehlten **13 Prozentpunkte** des
   Gesamtergebnisses. Immer ueber GUIDs gehen, nie ueber Namen — „Beast"
   beschwoeren auch Mitspieler.
3. **SWING_DAMAGE hat drei Felder weniger.** Kein spellId/Name/School, der Betrag
   steht an Index **28** statt 31. Wer ueberall 31 liest, misst bei jedem
   Auto-Angriff „1 Schaden".
4. **Bei SPELL_DAMAGE beschreiben die Advanced-Felder das ZIEL.** Ein
   ownerGUID-Filter auf Schadenszeilen erklaert deshalb Raid-Gegner zu eigenen
   Begleitern, sobald sie einen selbst treffen.

BEDIENUNG
=========
    puppe-messen.py <logdatei> [--spieler <Charaktername>] [--sim 108323] [--ziel 95]

Ohne --spieler wird der Spieler genommen, der SPELL_CAST_FAILED schreibt — das
ist immer der lokale Charakter.
"""
from __future__ import annotations

import argparse
import collections
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

KOPF = re.compile(r'^(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+)\.(\d+)\s{2}(.*)$')
# Betragsfeld je Ereignisart. SWING_DAMAGE hat KEINE spellId/spellName/school —
# der Betrag steht dort drei Felder frueher. Wer ueberall 31 nimmt, liest bei
# Auto-Angriffen ein Flag und bekommt "1 Schaden je Treffer".
BETRAG = {'SPELL_DAMAGE': 31, 'SPELL_PERIODIC_DAMAGE': 31,
          'RANGE_DAMAGE': 31, 'SWING_DAMAGE': 28}
BESITZER_FELD = 13          # ownerGUID in den Advanced-Feldern der QUELLE
PUPPE = 'Training Dummy'
LUECKE = 10.0               # Sekunden ohne Treffer = neuer Durchgang
MINDEST = 60.0              # kürzere Durchgänge sind nicht aussagekräftig

# Beast Mastery, IDs wie sie IM LOG stehen (nicht wie in der Sequenz!)
BM = {'34026': 'Kill Command', '217200': 'Barbed Shot', '193455': 'Cobra Shot',
      '19574': 'Bestial Wrath', '1264359': 'Wild Thrash'}
COOLDOWN = {'19574': 30.0}  # für die Ausnutzungsrechnung


def zeit(m) -> datetime:
    mo, tg, jr, st, mi, se, ms, _ = m.groups()
    return datetime(int(jr), int(mo), int(tg), int(st), int(mi), int(se),
                    int(ms.ljust(6, '0')[:6]))


def lokaler_spieler(pfad: Path, gesucht: str | None):
    """Nur der lokale Charakter hat SPELL_CAST_FAILED-Zeilen."""
    fehl, erfolg = collections.Counter(), collections.Counter()
    with open(pfad, 'rb') as f:
        for roh in f:
            if b',Player-' not in roh:
                continue
            if b'SPELL_CAST_FAILED,Player-' in roh:
                t = roh.decode('utf-8', 'replace').split(',')
                if len(t) > 2:
                    fehl[(t[1], t[2].strip('"'))] += 1
            elif b'SPELL_CAST_SUCCESS,Player-' in roh:
                t = roh.decode('utf-8', 'replace').split(',')
                if len(t) > 2:
                    erfolg[(t[1], t[2].strip('"'))] += 1
    if gesucht:
        kurz = gesucht.split('-')[0]
        for g, n in erfolg:
            if n.split('-')[0] == kurz:
                return g, n
        sys.exit(f"{gesucht} castet in diesem Log nicht.")
    if not fehl:
        sys.exit("Keine SPELL_CAST_FAILED im Log — der lokale Spieler ist nicht "
                 "bestimmbar. Bitte --spieler angeben.")
    return fehl.most_common(1)[0][0]


def begleiter(pfad: Path, guid: str):
    """Alle Begleiter — BEIDE Wege sind noetig:

    (a) `SPELL_SUMMON` des Spielers erfasst die kurzlebigen Beschwoerungen
        (Dire Beast, Fenryr, Hati, Bear, Wyvern), die selbst nie zaubern und
        deshalb nirgends ein ownerGUID hinterlassen.
    (b) `ownerGUID` erfasst die dauerhaften Pets — darunter das zweite Pet aus
        Animal Companion, das in SPELL_SUMMON fehlen kann.

    Ueber GUIDs gehen, nie ueber Namen: "Beast" beschwoeren auch Mitspieler.
    """
    meine, namen = set(), {}
    with open(pfad, 'rb') as f:
        for roh in f:
            if guid.encode() not in roh:
                continue
            t = roh.decode('utf-8', 'replace').split(',')
            if len(t) < 8:
                continue
            ev = t[0].split('  ')[-1]
            if ev == 'SPELL_SUMMON' and t[1] == guid:
                meine.add(t[5])
                namen[t[5]] = t[6].strip('"')
            # ownerGUID nur aus Zeilen lesen, deren Advanced-Felder die QUELLE
            # beschreiben. Bei SPELL_DAMAGE beschreiben sie das ZIEL — dort steht
            # die eigene GUID, sobald man selbst getroffen wird, und man erklaert
            # sich Raid-Gegner und fremde Totems zu Begleitern.
            elif (ev in ('SPELL_CAST_SUCCESS', 'SPELL_AURA_APPLIED', 'SPELL_ENERGIZE')
                  and len(t) > BESITZER_FELD and t[BESITZER_FELD] == guid
                  and (t[1].startswith('Pet-') or t[1].startswith('Creature-'))):
                meine.add(t[1])
                namen[t[1]] = t[2].strip('"')
    return meine, namen


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('log', type=Path)
    p.add_argument('--spieler')
    p.add_argument('--sim', type=float, help='Sim-DPS als Vergleichswert')
    p.add_argument('--ziel', type=float, default=95.0, help='Zielwert in Prozent')
    a = p.parse_args()

    guid, name = lokaler_spieler(a.log, a.spieler)
    meine, namen = begleiter(a.log, guid)
    print(f"{name} | {len(meine)} Begleiter erkannt: "
          f"{', '.join(sorted(set(namen.values()))) or '—'}\n")

    treffer, casts = [], []
    with open(a.log, 'rb') as f:
        for roh in f:
            if PUPPE.encode() not in roh and guid.encode() not in roh:
                continue
            m = KOPF.match(roh.decode('utf-8', 'replace').rstrip('\r\n'))
            if not m:
                continue
            t_ = m.group(8).split(',')
            if len(t_) < 11:
                continue
            t = zeit(m)
            feld = BETRAG.get(t_[0])
            if (feld is not None and len(t_) > feld
                    and PUPPE in t_[6] and (t_[1] == guid or t_[1] in meine)):
                try:
                    wer = 'SPIELER' if t_[1] == guid else t_[2].strip('"')
                    treffer.append((t, int(t_[feld]), wer))
                except ValueError:
                    pass
            elif t_[0] == 'SPELL_CAST_SUCCESS' and t_[1] == guid and t_[9].isdigit():
                casts.append((t, t_[9]))
    if not treffer:
        sys.exit("Keine Treffer auf eine Übungspuppe gefunden.")

    bloecke, lauf = [], [treffer[0]]
    for x, y in zip(treffer, treffer[1:]):
        if (y[0] - x[0]).total_seconds() > LUECKE:
            bloecke.append(lauf)
            lauf = []
        lauf.append(y)
    bloecke.append(lauf)
    bloecke = [b for b in bloecke if (b[-1][0] - b[0][0]).total_seconds() >= MINDEST]

    for i, g in enumerate(bloecke, 1):
        d = (g[-1][0] - g[0][0]).total_seconds()
        s = sum(x[1] for x in g)
        anteil = collections.Counter()
        for _, x, q in g:
            anteil[q] += x
        c = [x for x in casts if g[0][0] <= x[0] <= g[-1][0]]
        print(f"=== Durchgang {i}: {g[0][0].strftime('%H:%M:%S')}, {d:.0f} s ===")
        for q, v in anteil.most_common():
            print(f"    {q:<26}{v:>13,}  {100*v/s:>5.1f} %")
        print(f"    {'GESAMT':<26}{s:>13,}  = {s/d:,.0f} DPS")
        if a.sim:
            pz = 100 * (s/d) / a.sim
            fehlt = a.ziel/100 * a.sim - s/d
            print(f"    Sim {a.sim:,.0f} → **{pz:.1f} %**"
                  + (f"   (für {a.ziel:.0f} % fehlen {fehlt:,.0f} DPS)" if fehlt > 0
                     else f"   — Ziel {a.ziel:.0f} % ERREICHT"))
        n = collections.Counter(s_ for _, s_ in c)
        rot = sum(n[k] for k in BM)
        print(f"\n    {'Zauber':<15}{'Casts':>7}{'/min':>8}{'Anteil':>8}{'Abstand':>9}")
        for sid, nm in BM.items():
            if not n[sid]:
                continue
            ts = [x for x, y in c if y == sid]
            ab = [(y-x).total_seconds() for x, y in zip(ts, ts[1:])
                  if 0 < (y-x).total_seconds() < 120]
            md = f"{statistics.median(ab):.1f}s" if ab else "-"
            zeile = (f"    {nm:<15}{n[sid]:>7}{60*n[sid]/d:>8.1f}"
                     f"{100*n[sid]/rot:>7.1f}%{md:>9}")
            if sid in COOLDOWN:
                moeglich = d / COOLDOWN[sid] + 1
                zeile += f"   {100*n[sid]/moeglich:.0f} % des Cooldowns genutzt"
            print(zeile)
        pausen = [(y[0]-x[0]).total_seconds() for x, y in zip(c, c[1:])
                  if (y[0]-x[0]).total_seconds() > 3]
        print(f"\n    Casts {len(c)} = {len(c)/d:.2f}/s, "
              f"Pausen über 3 s: {len(pausen)}\n")


if __name__ == '__main__':
    main()
