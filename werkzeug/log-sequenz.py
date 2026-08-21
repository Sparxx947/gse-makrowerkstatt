#!/usr/bin/env python3
"""log-sequenz.py - was eine GSE-Sequenz im ECHTEN Kampf leistet.

Ergaenzt log-casts.py um die Fragen, die dieses nicht beantwortet:
  * Wie voll ist der GCD wirklich? (Rotations-Casts je Sekunde Kampfzeit)
  * Wie gut werden die Cooldowns ausgenutzt? (Abstand zwischen gleichen Casts)
  * Wie schnell reagiert die Sequenz auf einen frei gewordenen Cooldown?
  * Laeuft die Ressource ueber? Der Fokus steht in den Advanced-Feldern, die
    Regeneration wird aus dem Log SELBST gemessen statt angenommen.
  * Uptime der Kernbuffs auf AKTIVER Kampfzeit statt auf der Wanduhr.

ZWEI FALLEN, die je einen Anlauf gekostet haben (2026-08-19)
============================================================
1. DIE SPELL-IDs IM LOG SIND ANDERE ALS IN DER SEQUENZ.
   Die Sequenz schreibt `/cast 56641` (Barbed Shot) und `/cast 185358`
   (Cobra Shot) - beides aus GSESpellCache, also aus dem Spiel selbst.
   Im CombatLog stehen aber **217200** und **193455**; der Client loest die
   IDs beim Wirken auf. Wer nach den Sequenz-IDs sucht, misst NULL Casts und
   haelt die Sequenz faelschlich fuer kaputt. Erst die echten IDs holen:
       awk -F, '/SPELL_CAST_SUCCESS,<GUID>/ {print $10, $11}' log \\
         | sort | uniq -c | sort -rn
2. DIE FELDPOSITIONEN. An echten Zeilen geprueft (0-basiert):
       SPELL_CAST_SUCCESS: 9 spellId, 10 Name, 11 Schule,
                           22 powerType, 23 currentPower, 24 maxPower, 25 Kosten
       SPELL_CAST_FAILED : 12 Grund ("Not yet recovered", "Not enough focus", ...)
   Feld 11 ist die SCHULE, nicht der Grund - wer die nimmt, liest ueberall "0x1".

WAS DIE ZAHLEN BEDEUTEN
=======================
Die Soll-Prozente aus der Slot-Verteilung sind KEIN Sollwert fuer die Casts.
Die Slots gewichten nur, wie oft ein Zauber ANGEBOTEN wird; was durchkommt,
entscheidet der Cooldown. Ein Zauber ohne Cooldown (Cobra Shot) liegt darum
immer weit ueber seinem Slot-Anteil, ohne dass etwas falsch waere.

Der "Verzug" ist eine OBERGRENZE: gemessen wird der Abstand vom letzten
"Not yet recovered" bis zum Erfolg. Darin steckt auch der laufende GCD, der
ohnehin ablaufen muss - ein Wert um 0,8 s ist also praktisch verzugsfrei.

BEDIENUNG
=========
    log-sequenz.py <logdatei> [--spieler <Charaktername>] [--ids 34026,217200,...]
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

# Beast Mastery, Midnight 12.1 - die IDs, wie sie IM LOG stehen
BM = {'34026': 'Kill Command', '217200': 'Barbed Shot', '193455': 'Cobra Shot',
      '19574': 'Bestial Wrath', '1264359': 'Wild Thrash'}
# Kernbuffs, deren Uptime zaehlt
BUFFS = ('Frenzy', 'Beast Cleave', 'Bestial Wrath', 'Barbed Shot')
LUECKE = 5.0        # Sekunden ohne Cast = Kampfpause (Laufweg zwischen Pulls)


def zeit(m) -> datetime:
    mo, tg, jr, st, mi, se, ms, _ = m.groups()
    return datetime(int(jr), int(mo), int(tg), int(st), int(mi), int(se),
                    int(ms.ljust(6, '0')[:6]))


def finde_spieler(pfad: Path, gesucht: str | None) -> tuple[str, str]:
    """GUID und Name des auszuwertenden Spielers.

    Ohne --spieler wird NICHT der haeufigste Wirker genommen: In einer Gruppe
    castet oft ein Mitspieler mehr. Der lokale Spieler ist der einzige, fuer den
    der Client SPELL_CAST_FAILED schreibt - fremde Fehlversuche sieht er nicht.
    Das ist die eindeutige Kennung; der haeufigste Wirker bleibt nur Rueckfall.
    """
    fehl, erfolg = collections.Counter(), collections.Counter()
    with open(pfad, 'rb') as f:
        for roh in f:
            if b',Player-' not in roh:
                continue
            if b'SPELL_CAST_FAILED,Player-' in roh:
                f_ = roh.decode('utf-8', 'replace').split(',')
                if len(f_) > 2:
                    fehl[(f_[1], f_[2].strip('"'))] += 1
            elif b'SPELL_CAST_SUCCESS,Player-' in roh:
                f_ = roh.decode('utf-8', 'replace').split(',')
                if len(f_) > 2:
                    erfolg[(f_[1], f_[2].strip('"'))] += 1
    quelle = fehl or erfolg
    if gesucht:
        kurz = gesucht.split('-')[0]
        treffer = [(g, n) for (g, n) in erfolg if n.split('-')[0] == kurz]
        if not treffer:
            sys.exit(f"{gesucht} castet in diesem Log nicht. Vorhanden: "
                     + ', '.join(sorted({n.split('-')[0] for _, n in erfolg})))
        return treffer[0]
    (guid, name), n = quelle.most_common(1)[0]
    if not fehl:
        print(f"# Hinweis: keine SPELL_CAST_FAILED im Log - Spieler nur geraten "
              f"({name}, {n} Casts).", file=sys.stderr)
    return guid, name


def lies(pfad: Path, guid: str, name_b: bytes, ptyp: int | None):
    casts, fokus = [], []
    fehl_roh = []          # (t, name, grund) - Zeit noetig fuer --nur-bosse
    kaempfe, auf = [], None
    versuche = collections.defaultdict(list)     # id -> [(t, 'ok'|'cd')]
    auren = collections.defaultdict(list)
    offen: dict = {}
    with open(pfad, 'rb') as f:
        for roh in f:
            # ENCOUNTER-Zeilen tragen den Spielernamen nicht - separat durchlassen
            ist_enc = b'ENCOUNTER_' in roh
            if name_b not in roh and not ist_enc:
                continue
            m = KOPF.match(roh.decode('utf-8', 'replace').rstrip('\r\n'))
            if not m:
                continue
            rest = m.group(8)
            if ist_enc:
                g = rest.split(',')
                if g[0] == 'ENCOUNTER_START':
                    auf = zeit(m)
                elif g[0] == 'ENCOUNTER_END' and auf:
                    if (zeit(m) - auf).total_seconds() > 25:
                        kaempfe.append((auf, zeit(m)))
                    auf = None
                continue
            f_ = rest.split(',')
            if len(f_) < 12 or f_[1] != guid:
                continue
            sid = f_[9]
            if not sid.isdigit():
                continue
            t = zeit(m)
            ev, sname = f_[0], f_[10].strip('"')

            if ev == 'SPELL_CAST_SUCCESS':
                casts.append((t, sid))
                versuche[sid].append((t, 'ok'))
                if len(f_) > 25 and f_[22]:
                    typen = f_[22].split('|')
                    # Ohne Vorgabe: den ersten Typ ausser Mana (0) nehmen
                    kand = [x for x in typen if x != '0'] or typen
                    ziel = str(ptyp) if ptyp is not None else kand[0]
                    if ziel in typen:
                        i = typen.index(ziel)
                        try:
                            fokus.append((t, float(f_[23].split('|')[i]),
                                          float(f_[24].split('|')[i]), float(f_[25])))
                        except (ValueError, IndexError):
                            pass
            elif ev == 'SPELL_CAST_FAILED':
                grund = f_[12].strip('"')
                fehl_roh.append((t, sname, grund))
                if 'Not yet recovered' in grund:
                    versuche[sid].append((t, 'cd'))
            elif ev.startswith('SPELL_AURA_'):
                schl = (sname, f_[5].startswith('Pet-'))
                if ev == 'SPELL_AURA_REMOVED':
                    if schl in offen:
                        auren[schl].append((offen.pop(schl), t))
                elif ev in ('SPELL_AURA_APPLIED', 'SPELL_AURA_REFRESH'):
                    offen.setdefault(schl, t)     # REFRESH haelt das Fenster offen
    if casts:
        for schl, start in offen.items():
            auren[schl].append((start, casts[-1][0]))
    return casts, fehl_roh, fokus, versuche, auren, kaempfe


def phasen(casts):
    ab, lauf = [], [casts[0]]
    for vor, akt in zip(casts, casts[1:]):
        if (akt[0] - vor[0]).total_seconds() > LUECKE:
            ab.append(lauf)
            lauf = []
        lauf.append(akt)
    ab.append(lauf)
    return [b for b in ab if len(b) > 3]


def spanne(b):
    return (b[-1][0] - b[0][0]).total_seconds()


def anteil(fenster, bloecke) -> float:
    """Anteil der aktiven Kampfzeit, in der die Aura stand."""
    gesamt = summe = 0.0
    for b in bloecke:
        a, e = b[0][0], b[-1][0]
        gesamt += (e - a).total_seconds()
        for fa, fe in fenster:
            ue = (min(e, fe) - max(a, fa)).total_seconds()
            if ue > 0:
                summe += ue
    return 100 * summe / gesamt if gesamt else 0.0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('log', type=Path)
    p.add_argument('--spieler')
    p.add_argument('--ids', help='eigene ID:Name-Liste, sonst Beast Mastery')
    p.add_argument('--buffs', help='Komma-Liste der Buffs, deren Uptime zaehlt')
    p.add_argument('--nur-bosse', action='store_true', dest='nur_bosse',
                   help='nur ENCOUNTER_START..END auswerten. Dungeon-Bosse sind '
                        'ueberwiegend Einzelziel - so kommt man an ST-Daten, ohne '
                        'auf einen Raid zu warten (30 Bosse = 71,5 min statt 14,3).')
    p.add_argument('--ressource', type=int, default=None,
                   help='powerType: 2 Fokus, 9 Heilige Kraft, 1 Wut ... '
                        'Standard: der haeufigste Typ ausser Mana')
    a = p.parse_args()

    guid, name = finde_spieler(a.log, a.spieler)
    rot = BM
    if a.ids:
        rot = dict(t.split(':') for t in a.ids.split(','))

    casts, fehl_roh, fokus, versuche, auren, kaempfe = lies(a.log, guid,
                                              name.encode('utf-8'), a.ressource)
    if a.nur_bosse:
        if not kaempfe:
            sys.exit("Keine ENCOUNTER-Abschnitte ueber 25 s im Log.")
        drin = lambda t: any(x <= t <= y for x, y in kaempfe)
        casts = [(t, s_) for t, s_ in casts if drin(t)]
        fokus = [x for x in fokus if drin(x[0])]
        for k in versuche:
            versuche[k] = [(t, art) for t, art in versuche[k] if drin(t)]
        fehl_roh = [x for x in fehl_roh if drin(x[0])]
        bosszeit = sum((y - x).total_seconds() for x, y in kaempfe)
        print(f"# NUR BOSSPHASEN: {len(kaempfe)} Kaempfe ueber 25 s, "
              f"{bosszeit/60:.1f} min\n")
    if not casts:
        sys.exit("Keine Casts gefunden - stimmt der Spieler?")
    fehl = collections.Counter((nm, gr) for _, nm, gr in fehl_roh)
    bl = phasen(casts)
    aktiv = sum(spanne(b) for b in bl)
    print(f"{name} | {len(casts)} Casts, {sum(fehl.values())} Fehlversuche, "
          f"{len(bl)} Kampfabschnitte, {aktiv/60:.1f} min aktive Kampfzeit von "
          f"{spanne(casts)/60:.1f} min Log\n")

    wt = next((i for i, n in rot.items() if 'Thrash' in n or 'Multi' in n), None)
    if wt:
        gruppen = [("EINZELZIEL", [b for b in bl if not any(s == wt for _, s in b)]),
                   ("AoE (mit Flaechenzauber)", [b for b in bl if any(s == wt for _, s in b)])]
    else:
        # Kein Zauber in der Liste trennt ST von AoE - dann auch nicht so tun.
        gruppen = [("ALLE Kampfabschnitte", bl), ("", [])]
    for titel, g in gruppen:
        if not g:
            continue
        n = collections.Counter()
        z = sum(spanne(b) for b in g)
        for b in g:
            for _, s in b:
                n[s] += 1
        summe = sum(n[k] for k in rot)
        print(f"=== {titel}: {len(g)} Abschnitte, {z/60:.1f} min, "
              f"{summe} Rotations-Casts = {summe/z:.2f}/s ===")
        print(f"{'Zauber':<15}{'Casts':>7}{'/min':>7}{'Anteil':>8}{'Abstand':>9}")
        for sid, nm in rot.items():
            # NUR die Erfolgsreihe: wer hier ueber versuche[] iteriert, misst
            # bloss die Wiederholungen ohne Fehlversuch dazwischen und bekommt
            # viel zu kleine Abstaende (1,0 s statt 4,0 s bei Kill Command).
            ok = [t for t, art in versuche[sid] if art == 'ok']
            ab = [(y-x).total_seconds() for x, y in zip(ok, ok[1:])
                  if 0 < (y-x).total_seconds() < 60]
            # Abstand nur zeigen, wenn der Zauber in DIESER Gruppe vorkommt -
            # sonst steht bei Wild Thrash im Einzelziel-Block ein Wert aus den
            # AoE-Phasen und liest sich wie ein Widerspruch zu "0 Casts".
            md = f"{statistics.median(ab):.1f}s" if ab and n[sid] else "-"
            print(f"{nm:<15}{n[sid]:>7}{60*n[sid]/z:>7.1f}"
                  f"{100*n[sid]/summe if summe else 0:>7.1f}%{md:>9}")
        print()

    if not fehl:
        print("=== Fehlversuche, Reaktionszeit: NICHT MESSBAR ===")
        print("Der Client schreibt SPELL_CAST_FAILED nur fuer den EIGENEN Charakter.")
        print(f"{name} ist ein Mitspieler - Cooldown-Verzug und Reaktion auf freie")
        print("Cooldowns lassen sich aus diesem Log nicht bestimmen. Dafuer muesste")
        print("er selbst aufzeichnen.\n")
    else:
        print("=== Warum Klicks ins Leere laufen (Top 10) ===")
        for (zb, grund), k in fehl.most_common(10):
            print(f"{k:>7}  {zb:<16} {grund}")

    if fehl:
      print("\n=== Reaktion auf freie Cooldowns (Verzug = Obergrenze, GCD inklusive) ===")
      print(f"{'Zauber':<15}{'Angebot alle':>14}{'Verzug Median':>15}")
      for sid, nm in rot.items():
        e = sorted(versuche[sid])
        dt = [(b[0]-x[0]).total_seconds() for x, b in zip(e, e[1:])
              if 0 < (b[0]-x[0]).total_seconds() < 5]
        vz, letzt = [], None
        for t, art in e:
            if art == 'cd':
                letzt = t
            elif letzt is not None:
                d = (t-letzt).total_seconds()
                if 0 < d < 5:
                    vz.append(d)
                letzt = None
        if dt:
            print(f"{nm:<15}{statistics.median(dt):>13.2f}s"
                  f"{statistics.median(vz) if vz else float('nan'):>14.2f}s")

    if fokus:
        gross = statistics.median(m for _, _, m, _ in fokus)
        # Cap immer RELATIV pruefen: "max - 2" ist bei einer 5er-Skala
        # (Heilige Kraft, Combopunkte) jeder zweite Wert und meldet Unsinn.
        amcap = sum(1 for _, x, m, _ in fokus if m and x >= m - max(1, 0.02*m))
        print(f"\n=== Ressource (Skala 0..{gross:.0f}) ===")
        print(f"Am Cap: {100*amcap/len(fokus):.1f} % der Casts "
              f"({amcap} von {len(fokus)})")
        if gross < 20:
            # Punkte-Ressourcen regenerieren nicht passiv - sie werden erzeugt.
            # Ein Regenerationsmodell waere hier frei erfunden.
            print("Punkte-Ressource: sie regeneriert nicht von selbst, deshalb "
                  "keine Verlustrechnung.")
            print("Am Cap heisst hier: der naechste Erzeuger waere verschwendet "
                  "gewesen.")
        else:
            raten = []
            for (t1, a1, m1, k1), (t2, a2, m2, _) in zip(fokus, fokus[1:]):
                d = (t2-t1).total_seconds()
                if 0.3 < d < 3.0 and a2 < m2 - 2:
                    r = (a2 - (a1 - k1)) / d
                    if 0 < r < 40:
                        raten.append(r)
            regen = statistics.median(raten) if raten else 0
            verloren = moeglich = 0.0
            for (t1, a1, m1, k1), (t2, a2, m2, _) in zip(fokus, fokus[1:]):
                d = (t2-t1).total_seconds()
                if d > LUECKE:
                    continue
                moeglich += regen*d
                verloren += max(0.0, (a1 - k1) + regen*d - m2)
            print(f"Regeneration gemessen: {regen:.2f}/s "
                  f"(Median aus {len(raten)} Paaren)")
            print(f"Verworfen {verloren:.0f} von {moeglich:.0f} "
                  f"= {100*verloren/moeglich if moeglich else 0:.1f} %")

    buffs = tuple(x.strip() for x in a.buffs.split(',')) if a.buffs else BUFFS
    print("\n=== Uptime der Kernbuffs auf AKTIVER Kampfzeit ===")
    for (nm, pet), fen in sorted(auren.items()):
        if nm not in buffs:
            continue
        print(f"{nm:<16}({'Pet' if pet else 'ich':<3}) "
              f"ST {anteil(fen, gruppen[0][1]):>5.1f} %   "
              f"AoE {anteil(fen, gruppen[1][1]):>5.1f} %   {len(fen)} Fenster")


if __name__ == '__main__':
    main()
