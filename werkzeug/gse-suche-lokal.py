#!/usr/bin/env python3
"""gse-suche-lokal.py — sucht das beste GSE-Schrittmuster mit lokalem SimulationCraft.

Nachfolger von `prot-suche.py`, aber klassenunabhängig: Die Zauber, ihre
zulässige Platzzahl und die Zeilen, die außerhalb des Musters laufen, kommen
aus einer Beschreibungsdatei.

WARUM LOKAL
    Raidbots begrenzt die Zahl der Läufe und sein Editor übernimmt Eingaben
    unzuverlässig ([[reference_raidbots_workflow]]). Lokal sind ein paar hundert
    Varianten eine Sache von Minuten, und der Nachbau ist reproduzierbar.

WIE DER NACHBAU FUNKTIONIERT
    Die GSE-Weiterschaltung als APL ([[reference_gse_als_simc_apl]]):
        variable,name=s,op=set,value=floor(time*<klicks>)%%<schritte>
        <zauber>,if=variable.s=<platz>|…
        wait,sec=<1/klicks>

    ZWEI Dinge gehören zusätzlich hinein, sonst misst man Unsinn:
    * **Off-GCD-Zauber** stehen VOR dem Muster und kosten keinen Platz
      (Prot-Paladin: Shield of the Righteous).
    * **Was der Spieler von Hand drückt** — Burst-Tasten, Zunft-Zauber —
      ebenfalls, denn er wirkt sie ja wirklich. Beim Prot-Paladin kam der
      Nachbau ohne sie auf 24.492 statt 37.565 DPS.

DIE MESSLATTE
    Nicht die volle Standard-APL, sondern dieselbe **ohne die Dinge, die laut
    Absprache von Hand kommen** (meist die Schmuckstücke). Beim Prot-Paladin
    waren das 15,8 % Unterschied — mit falschem Nenner sieht eine gute Sequenz
    wie eine schlechte aus.

BESCHREIBUNGSDATEI (Python)
    ZAUBER   = {'kurzname': 'simc_name', ...}
    VOR      = ['actions+=/…', ...]        # off-GCD und Handbetrieb
    BEREICHE = {'kurzname': (min, max), ...}
    LAENGEN  = (14, 16, 18)
    KLICKS   = (10,)

AUFRUF
    gse-suche-lokal.py <basis.simc> <beschreibung.py> [--vorlauf 800]
        [--fein 8000] [--beste 8]
"""
from __future__ import annotations

import argparse
import itertools
import re
import subprocess
import sys
from pathlib import Path

SIMC = Path.home() / 'simc-build' / 'engine' / 'simc'


def apl(muster: list[str], vor: list[str], klicks: int) -> str:
    n = len(muster)
    plaetze: dict[str, list[int]] = {}
    for i, z in enumerate(muster):
        plaetze.setdefault(z, []).append(i)
    z = ['actions.precombat=snapshot_stats',
         f'actions=variable,name=s,op=set,value=floor(time*{klicks})%%{n}']
    z += list(vor)
    for zauber, pl in plaetze.items():
        z.append(f'actions+=/{zauber},if=' + '|'.join(f'variable.s={p}' for p in pl))
    z.append(f'actions+=/wait,sec={1/klicks:g}')
    return '\n'.join(z) + '\n'


def verteile(schritte: int, anteile: dict[str, int]) -> list[str]:
    """Gleichmäßige Abstände statt Blöcke: Ein geballt stehender Zauber löst beim
    ersten Treffer seinen Cooldown aus, die folgenden Plätze verpuffen."""
    muster: list[str | None] = [None] * schritte
    for zauber, anzahl in sorted(anteile.items(), key=lambda x: -x[1]):
        for k in range(anzahl):
            ziel = round(k * schritte / anzahl) % schritte
            for versuch in range(schritte):
                p = (ziel + versuch) % schritte
                if muster[p] is None:
                    muster[p] = zauber
                    break
    haupt = max(anteile, key=lambda k: anteile[k])
    return [m if m else haupt for m in muster]


def lauf(basis: Path, text: str, iterationen: int) -> float | None:
    tmp = Path('/tmp/gse-suche-lokal.simc')
    tmp.write_text(basis.read_text() + '\n' + text)
    try:
        p = subprocess.run([str(SIMC), str(tmp), f'iterations={iterationen}'],
                           capture_output=True, text=True, timeout=2400)
    except subprocess.TimeoutExpired:
        return None
    m = re.search(r'Player: \S+ .*?\n\s+DPS=([\d.]+)', p.stdout, re.S)
    return float(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('basis', type=Path)
    ap.add_argument('beschreibung', type=Path)
    ap.add_argument('--vorlauf', type=int, default=800)
    ap.add_argument('--fein', type=int, default=8000)
    ap.add_argument('--beste', type=int, default=8)
    a = ap.parse_args()
    if not SIMC.is_file():
        sys.exit(f'SimulationCraft fehlt: {SIMC}')

    raum: dict = {}
    exec(a.beschreibung.read_text(), raum)
    ZAUBER, VOR = raum['ZAUBER'], raum['VOR']
    BEREICHE, LAENGEN = raum['BEREICHE'], raum['LAENGEN']
    KLICKS = raum.get('KLICKS', (10,))
    MESSLATTE = raum.get('MESSLATTE')

    # Messlatte: Standard-APL unter denselben Bedingungen
    if MESSLATTE is None:
        MESSLATTE = lauf(a.basis, '', a.fein)
        print(f'Messlatte (Standard-APL): {MESSLATTE:,.0f} DPS\n', flush=True)

    kurz = {v: k for k, v in ZAUBER.items()}
    kandidaten = []
    for n in LAENGEN:
        namen = list(BEREICHE)
        for kombi in itertools.product(*[range(BEREICHE[k][0], BEREICHE[k][1] + 1)
                                         for k in namen]):
            if sum(kombi) != n:
                continue
            anteile = {ZAUBER[k]: v for k, v in zip(namen, kombi) if v}
            beschriftung = f"{n}er " + " ".join(f'{k}{v}' for k, v in zip(namen, kombi) if v)
            kandidaten.append((beschriftung, verteile(n, anteile)))
    if not kandidaten:
        sys.exit('Keine Kombination passt zu LAENGEN und BEREICHE.')

    print(f'{len(kandidaten)} Verteilungen x {len(KLICKS)} Klickraten, '
          f'Vorlauf {a.vorlauf} Iterationen', flush=True)
    vor = []
    for i, (nm, m) in enumerate(kandidaten, 1):
        for kl in KLICKS:
            d = lauf(a.basis, apl(m, VOR, kl), a.vorlauf)
            if d:
                vor.append((d, f'{nm} @{kl}', m, kl))
        if i % 25 == 0:
            print(f'  {i}/{len(kandidaten)}', flush=True)
    vor.sort(reverse=True)

    print(f'\nBeste {a.beste} mit {a.fein} Iterationen nachgerechnet:', flush=True)
    fein = []
    for d, nm, m, kl in vor[:a.beste]:
        g = lauf(a.basis, apl(m, VOR, kl), a.fein)
        if g:
            fein.append((g, nm, m, kl))
            print(f'  {g:>10,.0f}  {100*g/MESSLATTE:>6.2f} %  {nm}', flush=True)
    fein.sort(reverse=True)

    print(f'\n=== ENDSTAND (Messlatte {MESSLATTE:,.0f}) ===')
    for d, nm, m, kl in fein:
        print(f'{d:>10,.0f}  {100*d/MESSLATTE:>6.2f} %  {nm}')
        print(f'{"":>12}{" ".join(kurz[x] for x in m)}')


if __name__ == '__main__':
    main()
