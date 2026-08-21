#!/usr/bin/env python3
"""Baut aus einem Raidbots-Basisprofil einen Suchlauf mit Profilesets.

VERFAHREN
=========
Die GSE-Weiterschaltung wird als SimulationCraft-APL nachgebaut
(siehe reference_gse_als_simc_apl):

    actions=variable,name=s,op=set,value=floor(time*10)%%<Schritte>
    actions+=/<zauber>,if=variable.s=<platz>|variable.s=<platz>|...
    actions+=/wait,sec=0.1

Jede zu pruefende Sequenz wird ein Profileset; ein einziger Raidbots-Lauf
rechnet alle gegeneinander. Der Nachbau liegt systematisch rund 4 Punkte unter
dem Ingame-Wert - fuer den VERGLEICH von Fassungen kuerzt sich das heraus, fuer
absolute Aussagen taugt er nicht.

BEDIENUNG
=========
    simc-varianten.py <basis.simc> <varianten.py> > eingabe.txt

Die Basisdatei ist das Profil aus einem frueheren Report
(data.json -> /simbot/input), von dem der APL-Block abgeschnitten wird.
Die Variantendatei liefert VARIANTEN (Liste aus (Name, Schritte-Liste)) und
VORSPANN (Zeilen, die vor jedem Profileset stehen, z. B. auto_attack).

FALLSTRICKE, die je einen Fehllauf gekostet haben
=================================================
- Klassen-Pflichtzeilen: `summon_pet` beim Jaeger, `auto_attack` beim Krieger.
  Eine Custom-APL ersetzt auch die Precombat-Liste; ohne sie faellt die DPS auf
  ein Zehntel und der Lauf ist wertlos.
- `%%` ist Modulo in SimC, `%` ist Division.
- `armory=` und Profilesets vertragen sich nicht. Deshalb muss die Basisdatei
  das ausgeschriebene Gear enthalten.
- Fuer Auren-Uptime taugt der Suchlauf nicht: Profileset-Ergebnisse enthalten
  nur DPS. Die Siegerfassung dafuer noch einmal einzeln mit report_details=1.
"""
import importlib.util
import sys


def verteile(n, plaetze):
    """Verteilt Zauber moeglichst gleichmaessig ueber n Schritte.

    plaetze ist eine Liste (spell, anzahl), die Reihenfolge bestimmt den
    Vorrang bei Kollisionen: was zuerst kommt, bekommt seinen Wunschplatz.
    Gleichmaessig heisst hier: der k-te von m Plaetzen will nach
    round(n*(k+0.5)/m) - das haelt den mittleren Verzug eines Cooldowns klein.
    """
    muster = [None] * n
    for spell, anzahl in plaetze:
        for k in range(anzahl):
            wunsch = int(n * (k + 0.5) / anzahl) % n
            for versatz in range(n):
                pos = (wunsch + versatz) % n
                if muster[pos] is None:
                    muster[pos] = spell
                    break
            else:
                raise ValueError(f"mehr Plaetze als Schritte bei {spell}")
    if any(x is None for x in muster):
        raise ValueError(f"{muster.count(None)} Schritte unbesetzt")
    return muster


def apl(muster, vorspann, precombat=(), klickrate=10):
    """Erzeugt die APL-Zeilen fuer ein Schrittmuster.

    precombat muss mitgegeben werden, weil eine Custom-APL die gesamte
    Standardliste ersetzt - einschliesslich der Precombat-Liste.
    """
    n = len(muster)
    zeilen = []
    for i, z in enumerate(precombat):
        zeilen.append(f"actions.precombat{'=' if i == 0 else '+=/'}{z}")
    zeilen.append(
        f"actions=variable,name=s,op=set,value=floor(time*{klickrate})%%{n}")
    zeilen += [f"actions+=/{z}" for z in vorspann]
    for spell in dict.fromkeys(muster):          # Reihenfolge des ersten Auftretens
        pl = [str(i) for i, s in enumerate(muster) if s == spell]
        bed = "|".join(f"variable.s={p}" for p in pl)
        zeilen.append(f"actions+=/{spell},if={bed}")
    zeilen.append(f"actions+=/wait,sec={1 / klickrate:.2f}")
    return zeilen


def profileset(name, zeilen):
    """Wandelt APL-Zeilen in einen Profileset-Block."""
    return "\n".join(f'profileset."{name}"+="{z}"' for z in zeilen)


def basis_ohne_apl(text):
    """Schneidet den APL-Block und alte Profilesets aus einem Basisprofil."""
    raus = []
    for zeile in text.splitlines():
        s = zeile.strip()
        if s.startswith(("actions", "profileset")) or s.startswith("# "):
            continue
        raus.append(zeile)
    return "\n".join(raus).rstrip() + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    basis = basis_ohne_apl(open(sys.argv[1]).read())

    spec = importlib.util.spec_from_file_location("varianten", sys.argv[2])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    print(basis)
    # Die Standard-APL des Laufs ist die erste Variante; Profilesets werden
    # immer gegen das Basisprofil gerechnet, das damit als Referenz mitlaeuft.
    vor = getattr(mod, "PRECOMBAT", ())
    # Klickrate aus der Variantendatei; ohne Angabe die alten 10/s.
    # echte Rate ist gemessen (Log 2026-08-20): 6,2/s im Raid, 9,0/s in M+.
    kr = getattr(mod, "KLICKRATE", 10)
    erste_name, erstes_muster = mod.VARIANTEN[0]
    print(f"# Referenz: {erste_name}  (Klickrate {kr}/s)")
    print("\n".join(apl(erstes_muster, mod.VORSPANN, vor, kr)))
    print()
    for name, muster in mod.VARIANTEN[1:]:
        print(profileset(name, apl(muster, mod.VORSPANN, vor, kr)))
    print(file=sys.stderr)
    print(f"{len(mod.VARIANTEN)} Varianten "
          f"(1 Referenz + {len(mod.VARIANTEN) - 1} Profilesets)", file=sys.stderr)


if __name__ == "__main__":
    main()
