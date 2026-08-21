#!/usr/bin/env python3
"""prot-suche.py — sucht das beste GSE-Schrittmuster für den Prot-Paladin.

Rechnet lokal mit SimulationCraft, nicht auf Raidbots: Damit fallen die
Editor-Fallen weg und die Zahl der Varianten ist nur durch Rechenzeit begrenzt.

WIE DER NACHBAU FUNKTIONIERT
    Die GSE-Weiterschaltung wird als APL ausgedrückt
    ([[reference_gse_als_simc_apl]]): `floor(time*<klicks>)%%<schritte>` bildet
    den Schrittzeiger nach, `wait,sec=1/klicks` das Klickintervall.

    ZWEI Dinge müssen zusätzlich in die APL, sonst misst man Unsinn:
    * **Shield of the Righteous** liegt außerhalb des GCD und steht bei Prot in
      JEDEM Schritt — er kostet keinen Platz.
    * **Was der Spieler von Hand drückt**, gehört ebenfalls hinein: Sentinel und
      Divine Toll (Alt-Taste) sowie Holy Armaments (eigene Taste). Ohne sie fehlen
      dem Nachbau Zauber, die real gewirkt werden — der erste Lauf kam so auf
      24.492 statt 37.565 DPS.

AUFRUF
    prot-suche.py <basis.simc> [--iterationen 3000] [--nur-beste 5]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SIMC = Path.home() / 'simc-build' / 'engine' / 'simc'
J, BH, AS, C = 'judgment', 'blessed_hammer', 'avengers_shield', 'consecration'
KURZ = {J: 'J', BH: 'BH', AS: 'AS', C: 'C'}


def apl(muster: list[str], klicks: int = 10) -> str:
    n = len(muster)
    plaetze: dict[str, list[int]] = {}
    for i, z in enumerate(muster):
        plaetze.setdefault(z, []).append(i)
    z = ['actions.precombat=snapshot_stats',
         f'actions=variable,name=s,op=set,value=floor(time*{klicks})%%{n}',
         'actions+=/sentinel',
         'actions+=/divine_toll',
         'actions+=/holy_armaments,if=cooldown.holy_armaments.charges>=1',
         'actions+=/shield_of_the_righteous',
         'actions+=/hammer_of_wrath']
    for zauber, pl in plaetze.items():
        z.append(f'actions+=/{zauber},if=' + '|'.join(f'variable.s={p}' for p in pl))
    z.append(f'actions+=/wait,sec={1/klicks:g}')
    return '\n'.join(z) + '\n'


def verteile(schritte: int, anteile: dict[str, int]) -> list[str]:
    """Verteilt die Zauber möglichst gleichmäßig über die Schritte.

    Gleichmäßig heißt: gleiche Abstände statt Blöcke. Ein Zauber, der geballt
    hintereinander steht, kommt bei GSE seltener durch, weil er beim ersten
    Treffer den Cooldown auslöst und die folgenden Plätze verpuffen.
    """
    muster: list[str | None] = [None] * schritte
    for zauber, anzahl in sorted(anteile.items(), key=lambda x: -x[1]):
        for k in range(anzahl):
            ziel = round(k * schritte / anzahl) % schritte
            for versuch in range(schritte):
                p = (ziel + versuch) % schritte
                if muster[p] is None:
                    muster[p] = zauber
                    break
    # Reste auffüllen: der häufigste Zauber übernimmt
    haupt = max(anteile, key=lambda k: anteile[k])
    return [m if m else haupt for m in muster]


def lauf(basis: Path, apl_text: str, iterationen: int) -> float | None:
    eingabe = basis.read_text() + '\n' + apl_text
    tmp = Path('/tmp/prot-suche-lauf.simc')
    tmp.write_text(eingabe)
    try:
        p = subprocess.run([str(SIMC), str(tmp), f'iterations={iterationen}'],
                           capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return None
    m = re.search(r'Player: \S+ .*?\n\s+DPS=([\d.]+)', p.stdout, re.S)
    return float(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('basis', type=Path)
    ap.add_argument('--iterationen', type=int, default=3000)
    ap.add_argument('--nur-beste', type=int, default=8, dest='beste')
    a = ap.parse_args()
    if not SIMC.is_file():
        sys.exit(f'SimulationCraft nicht gefunden: {SIMC}')

    kandidaten: list[tuple[str, list[str], int]] = []
    # Fassung 2 als Bezugspunkt, exakt wie ausgeliefert
    kandidaten.append(('Fassung 2 (ist)',
                       [J, BH, AS, J, BH, C, J, BH, AS, J, BH, C, J, BH], 10))
    # Systematisch: Laenge x Verteilung x Klickrate
    for schritte in (12, 14, 16, 18):
        for bh in (4, 5, 6, 7):
            for j in (3, 4, 5):
                rest = schritte - bh - j
                if rest < 2:
                    continue
                for as_ in (1, 2, 3):
                    c = rest - as_
                    if not 1 <= c <= 3:
                        continue
                    m = verteile(schritte, {J: j, BH: bh, AS: as_, C: c})
                    name = f'{schritte}er J{j} BH{bh} AS{as_} C{c}'
                    kandidaten.append((name, m, 10))
    # Klickrate gegenpruefen, nur an der Ist-Fassung
    for kl in (5, 20):
        kandidaten.append((f'Fassung 2 @ {kl} Klicks/s',
                           [J, BH, AS, J, BH, C, J, BH, AS, J, BH, C, J, BH], kl))

    print(f'{len(kandidaten)} Varianten, je {a.iterationen} Iterationen\n', flush=True)
    ergebnisse = []
    for i, (name, m, kl) in enumerate(kandidaten, 1):
        dps = lauf(a.basis, apl(m, kl), a.iterationen)
        if dps is None:
            print(f'  [{i}/{len(kandidaten)}] {name:<24} FEHLER', flush=True)
            continue
        ergebnisse.append((dps, name, m, kl))
        print(f'  [{i}/{len(kandidaten)}] {name:<24}{dps:>10,.0f} DPS', flush=True)

    ergebnisse.sort(reverse=True)
    basis_dps = next((d for d, n, *_ in ergebnisse if n == 'Fassung 2 (ist)'), None)
    print(f'\n=== Beste {a.beste} ===')
    for dps, name, m, kl in ergebnisse[:a.beste]:
        rel = f'{100*dps/basis_dps-100:+.1f} %' if basis_dps else ''
        print(f'{dps:>10,.0f} DPS  {rel:>8}  {name}')
        print(f'{"":>21}{" ".join(KURZ[x] for x in m)}')


if __name__ == '__main__':
    main()
