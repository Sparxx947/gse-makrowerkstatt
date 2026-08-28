# GSE-Makrowerkstatt

*[English version](README.en.md)*

Werkzeuge, um GSE-Sequenzen für World of Warcraft nicht zu raten, sondern zu **rechnen** —
mit einem lokal gebauten SimulationCraft als Prüfstand.

Erreicht wurden damit **94 bis 96 Prozent** dessen, was ein perfekt gespielter Charakter im
Simulator schafft, über fünf Spezialisierungen hinweg (Unholy DK, Retribution- und
Protection-Paladin, Beast-Mastery-Jäger, Arms-Krieger).

**Handbuch mit dem vollständigen Verfahren:**
<https://claude.ai/code/artifact/239a1890-be4d-4834-8cb7-4b134802fa3c>

---

## Warum es dieses Repo gibt

Eine GSE-Sequenz ist eine feste Schrittliste, die stur weitergeschaltet wird. Sie kann
nichts über den Spielzustand wissen. Der naheliegende Bauweg — ein Muster ausdenken, ingame
an der Puppe testen, nachbessern — kostet pro Fassung einen Abend und liefert eine einzige
Zahl, aus der sich nicht ablesen lässt, *warum* sie so ausfiel.

Der Weg hier ist ein anderer: Die GSE-Weiterschaltung wird als SimulationCraft-APL exakt
nachgebaut, und dann rechnet der Simulator ein paar hundert Muster gegeneinander — in
Minuten statt in Abenden, und mit einer Aufschlüsselung Zauber für Zauber.

Der eigentliche Wert steckt nicht im Code, sondern in den **Kommentarköpfen**: Fast jedes
Skript erklärt, welcher konkrete Fehllauf es erzwungen hat und wie viele Prozentpunkte er
gekostet hat.

## Was hier liegt

| Ordner / Datei | Zweck |
|---|---|
| `werkzeug/gse-suche-lokal.py` | **Das Hauptwerkzeug.** Sucht das beste Schrittmuster mit lokalem SimC. Klassenunabhängig — Zauber, Platzzahlen und Zusatzzeilen kommen aus einer Beschreibungsdatei. |
| `werkzeug/gse3.py` | Kodiert und dekodiert `!GSE3!`-Import-Strings (CBOR → raw Deflate → Base64). Taugt auch, um fremde Sequenzen zu zerlegen. |
| `werkzeug/bauen-f2.py` | Beste Vorlage für eine neue Klasse: enthält die Bewertungsschleife über ein Klickratenband und im Kopf die vier übertragbaren Befunde. |
| `werkzeug/bauen-dk-retri.py` | Aufbau einer GSE-Struktur (MetaData, Versions, Actions) — kompakt und lesbar. |
| `werkzeug/bauen-prot4.py` | Beispiel für einen Off-GCD-Zauber, der in *jedem* Schritt steht, ohne einen Platz zu kosten. |
| `werkzeug/bauen-bm14.py` | Beispiel für M+- und Raid-Varianten mit und ohne `/targetenemy`. |
| `werkzeug/puppe-messen.py` | DPS und Rotationsgüte aus einem CombatLog — mit Filtern gegen fremde Spieler an derselben Puppe. |
| `werkzeug/log-casts.py` | Welche Casts eine Sequenz tatsächlich erzeugt hat, optional gegen einen Raidbots-Report. |
| `werkzeug/log-sequenz.py` | GCD-Auslastung, Cooldown-Ausnutzung, Ressourcenüberlauf, Buff-Uptimes auf aktiver Kampfzeit. |
| `werkzeug/simc-varianten.py` | Baut aus einem Basisprofil einen Raidbots-Lauf mit Profilesets — falls lokal nicht geht. |
| `werkzeug/prot-suche.py` | Vorgänger von `gse-suche-lokal.py`, fest verdrahtet. Nur als Lesebeispiel. |
| `werkzeug/varianten-arms-aoe4.py` | Beispiel-Variantendatei für `simc-varianten.py`. |
| `beispiele/besch-dk.py`, `besch-retri.py` | Zwei vollständige, echte Beschreibungsdateien — das beste Lernmaterial hier. |
| `LIESMICH-original.md` | Die gewachsene Ursprungsnotiz zum BM-Jäger, mit dem GSE3-Format und den Ingame-Fallstricken. |

## Voraussetzungen

- Linux, macOS oder Windows mit WSL 2
- `python3`, `git`, `build-essential`
- **SimulationCraft, lokal gebaut** aus dem Branch, der zur gespielten Spielversion passt

```bash
git clone https://github.com/simulationcraft/simc.git ~/simc-build
cd ~/simc-build && git checkout midnight
cd engine && SC_NO_NETWORKING=1 make optimized -j$(nproc)
```

Die Werkzeuge erwarten die Binärdatei unter `~/simc-build/engine/simc`.

## Schnellstart

```bash
git clone https://github.com/Sparxx947/gse-makrowerkstatt.git ~/wow-gse
cd ~/wow-gse

# 1. Basisprofil aus dem Spiel holen: ingame /simc eingeben, Text nach basis.simc
# 2. Beschreibungsdatei schreiben — als Vorlage beispiele/besch-dk.py
# 3. Suchlauf
werkzeug/gse-suche-lokal.py basis.simc beispiele/besch-dk.py \
    --vorlauf 800 --fein 8000 --beste 8
```

## Die Regeln, die Punkte kosten

Gemessen, nicht geschätzt. Ausführlich mit Herleitung im Handbuch.

| Regel | Kosten beim Bruch |
|---|---|
| Precombat-Beschwörung (`summon_pet` / `raise_dead`) gehört in die APL — eine eigene APL ersetzt auch die Precombat-Liste | bis −92 % DPS |
| `auto_attack` ist Pflicht für Nahkämpfer | −28,6 Punkte |
| Klassenmechanik nachlesen (Beispiel: Putrefy wirkt nur während Dark Transformation) | +11,5 Punkte |
| Jeden Zaubernamen einzeln gegen SimC prüfen — Namen aus dem Bericht sind nicht zwingend wirkbar | Lauf bricht ab |
| Cooldowns brauchen mindestens zwei Plätze | −16 bis −18 % der Casts |
| Buff-Cooldowns lieber über- als unterrepräsentieren | −7 % |
| Über ein **Band** von Klickraten bewerten, nicht bei einer einzigen | −14 Punkte Scheinwert |
| Sim-Cast-Anteile sind **kein** Sollwert — maßgeblich ist Schaden je Cast | −16 % |
| Nur ein GCD-Zauber pro Schritt; 255 Zeichen sind die harte Grenze | Schritt feuert nicht |

**Und eine Regel, die nicht technisch ist:** GSEs `msClickRate` bleibt bei **100 ms oder
höher**. Auffällig gleichmäßige Eingaben im schnellen Takt sind das Muster, an dem eine
Bot-Erkennung ansetzt; 100 ms ist zugleich der GSE-Standardwert. Die zwei Prozent Schaden,
die eine höhere Rate brächte, bleiben liegen.

## Vor dem ersten Lauf anpassen

Die Bauskripte tragen einen Platzhalter für die GSE-Datenbank:

```python
GSE_DATEI = Path('BITTE_ANPASSEN/WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua')
```

Wie der Account-Ordner heißt, zeigt `ls <WoW>/_retail_/WTF/Account`.

**Unter WSL zusätzlich:** Die WoW-läuft-Prüfung der Bauskripte benutzt `pgrep` — das findet
Windows-Prozesse grundsätzlich nicht. Sie meldet dort „läuft nicht", während WoW läuft, das
Skript schreibt, und WoW überschreibt es beim Ausloggen. Ersatz ist
`/mnt/c/Windows/System32/tasklist.exe`; der genaue Code steht im Handbuch.

## Hinweis zur Fassung

Dieses Repo ist die **neutrale Fassung**: Charakter- und Kontokennungen sind durch
Platzhalter ersetzt (`UH-DK`, `Retri`, `Prot-Pala`, `BM-Jäger`, `Arms-Krieger`,
`DEIN_ACCOUNT`). Fachlich ist nichts weggelassen — alle Messwerte, Herleitungen und
Fallstricke sind vollständig.

## Lizenz

[MIT](LICENSE). Nutzung für eigene Makros ist ausdrücklich erwünscht. Das Projekt ist privat
und selbstgebaut und steht in keiner Verbindung zu GSE oder SimulationCraft.
