# GSE-Sequenzen

Zwei getrennte Arbeiten liegen hier:

- **BM-Jäger** (`BM-Jäger`) — dieses Dokument, Stand 2026-08-13.
- **Protection Paladin** (`der Prot-Paladin`, Charakter eines Freundes) —
  `werkzeug/bauen-prot.py`, Stand 2026-08-15. Das Skript schreibt **nichts** in eine
  GSE.lua, sondern gibt Import-Strings aus; Aufbau, Messwerte und Fallstricke stehen
  ausführlich im Kopf des Skripts. Kernpunkt dort: Shield of the Righteous liegt
  außerhalb des GCD und steht deshalb in jedem Schritt, ohne einen Slot zu kosten.

---

# GSE-Sequenzen für den BM-Jäger

Midnight 12.1 / Season 2, Beast Mastery, Pack Leader. Stand 2026-08-13.

## Endstand

| Sequenz | Muster | gemessen |
|---|---|---|
| `Claude_BM_MPlus_ST`, `Claude_BM_Raid_ST` | BW KC BS KC CS KC BW KC BS KC CS KC | 84–90 % vom Sim |
| `Claude_BM_MPlus_AoE`, `Claude_BM_Raid_AoE` | BW WT KC BS WT KC BW WT KC BS WT KC | 82 % vom Sim |

Ingame 84–90k gegen 99.563 (Einzelziel) und ~202k gegen 245.440 (5 Ziele), jeweils
gegen den **buff-freien** Sim. Das ist die praktische Obergrenze für eine feste
Sequenz. Die M+-Fassungen haben automatischen Zielwechsel, die Raid-Fassungen nicht.

Zusatztasten in allen vier: **Shift** Counter Shot, **Alt** Mend Pet, **Strg**
Intimidation. `/stopmacro [mod]` unterdrückt dabei die Rotation.

## Wo alles liegt

- **Aktive Installation** (Steam-Prefix, *nicht* der Unraid-Share):
  `~/.steam/debian-installation/steamapps/compatdata/3137594837/pfx/drive_c/Program Files (x86)/World of Warcraft/_retail_`
  `/mnt/unraid/Privat-der Spieler/Wow/` ist eine **Kopie vom Februar 2026**.
- GSE-Datenbank: `WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua`
- Charakter: **`BM-Jäger`** auf dem eigenen Realm (Gravis auf i *und* e)
- Sicherungen und Prüfsummen: `~/wow-gse-backup/2026-08-13/`

## Werkzeug

| Datei | Zweck |
|---|---|
| `werkzeug/gse3.py` | kodiert und dekodiert `!GSE3!`-Strings |
| `werkzeug/bauen-bm12b.py` | **aktuell** (2026-08-19) — Fassung 12 **ohne das zweite Trinket** |
| `werkzeug/bauen-bm12.py` | Fassung 12 mit beiden Trinkets — der Rückweg |
| `werkzeug/bauen6.py` | überholt, Vor-Fassung-12-Stand |
| `werkzeug/bauen.py`, `bauen2.py` | fehlerhafte Frühfassungen, nicht verwenden |
| `werkzeug/bauen3.py` … `bauen5.py` | Zwischenstufen, `bauen5.py` war messbar schlechter |

Ohne Argument Probelauf, mit `--schreiben` eintragen. Das Skript **bricht ab, solange
WoW läuft**, und lässt keinen Schritt mit mehr als einer bedingungslosen `/cast`-Zeile
durch.

## Fallstricke

**WoW muss geschlossen sein.** Der Client hält die SavedVariables im Speicher und
überschreibt sie beim Speichern. Der Prozess heißt **`WoW.exe` — großes zweites W**;
ein Test auf `Wow.exe` findet ihn nie und meldet stumm „läuft nicht". Richtig ist
`pgrep -x -i "wow.exe"` — **`-x`, nicht `-f`**, sonst trifft die Prüfung die eigene
Shell, die den Suchstring trägt. Nach dem Schreiben Prüfsumme merken.

**Ein GCD-Zauber pro Schritt.** Mehrere `/cast`-Zeilen in einem Schritt sind keine
Prioritätskette: Scheitert ein `/cast`, das den GCD auslösen *würde*, blockiert es
alle folgenden `/cast`-Zeilen desselben Makros. Priorität entsteht über die
Häufigkeit im Schrittmuster. Zeilen mit `[mod:...]` blockieren nicht, wenn die
Bedingung nicht zutrifft; `/use` löst keinen GCD aus.

**Eintragen reicht nicht.** Ohne Tastenbindung oder Makro gibt es keinen Weg, eine
Sequenz auszulösen. Die Daumentasten hängen direkt an GSE-Buttons:

    bind BUTTON4 CLICK <Sequenzname>:LeftButton

Das in alten Bindungen auftauchende `_KD` ist **kein Namensschema**, sondern ein
Relay, den GSE erst beim Zuweisen über die eigene Oberfläche erzeugt. Von Hand
geschrieben zeigt es ins Leere — also ohne `_KD` binden.

**Trinkets.** Automatisch feuert nur **Slot 13** (oberes Trinket) mit; Slot 14 hat
der Spieler am 2026-08-19 herausnehmen lassen und zündet es selbst. `/use` löst keinen GCD
aus und belegt keinen Schritt — die Rotation und damit alle Messwerte der Fassung 12
bleiben unberührt. Zurück mit `bauen-bm12.py --schreiben`.
**Stand 2026-08-19: der Spieler trägt zwei Proc-Trinkets, kein On-Use** — beide
`/use`-Zeilen sind damit ohnehin wirkungslos. Slot 13 bleibt als Vorrat für
ein künftiges On-Use-Trinket stehen; ein solches gehört dann in Slot 13,
nicht in 14.

**255 Zeichen pro Schritt** ist die harte Grenze. Deshalb trägt der Eröffnungsschritt
keine Trinket-Zeilen.

**CRLF.** Die Datei nutzt Windows-Zeilenenden; Python im Textmodus schreibt sie auf
LF um und lässt die ganze Datei als geändert erscheinen. Binär lesen, Trenner
beibehalten.

## Das GSE3-Format

Aus `Interface/AddOns/GSE/API/Serialisation.lua`:

    "!GSE3!" .. C_EncodingUtil.EncodeBase64(
                  C_EncodingUtil.CompressString(
                    C_EncodingUtil.SerializeCBOR(tab)))

Also **CBOR → raw Deflate (wbits = -15) → Base64**. Lua-Strings landen als CBOR-
*Byte*-Strings (Major Type 2) — beim Bauen zwingend `bytes` verwenden. Gespeichert
wird ein Zweier-Array: `[Name, {LastUpdated, MetaData, Versions, WeakAuras}]`.
`GSESequences` ist nach **Klassen-ID** indiziert: 1 Krieger, 2 Paladin, **3 Jäger**,
6 Todesritter, 8 Magier.

Spell-IDs am besten aus `GSESpellCache` in der GSE.lua selbst — die stammt aus dem
laufenden Spiel. Midnight hat neu vergeben: Barbed Shot **56641**, Cobra Shot
**185358**, Wild Thrash **1264359**; unverändert Kill Command 34026, Bestial Wrath
19574.

## Warum nicht weiter optimiert wird

**Sim-Cast-Anteile sind kein Sollwert.** Der Simulator kennt jeden Cooldown und trifft
das Timing exakt; GSE ist blind und muss über Häufigkeit kompensieren. Zwei Versuche:
Einzelziel auf sim-nahe Gewichte umgestellt brachte **keinen messbaren Unterschied**;
Wild Thrash im AoE von 33 % auf den Sim-Wert 20 % gesenkt kostete **202.000 → 170.000
DPS**, weil Beast Cleave abriss. Faustregel: Ein überzähliger Slot kostet 100 ms, ein
fehlender einen ganzen GCD — bei Zaubern mit Uptime-Mechanik sogar ein ganzes Fenster.
**Lieber über- als unterrepräsentieren.**

**Fair messen:** Raidbots läuft standardmäßig mit *Optimal Raid Buffs*. An der Puppe
ohne Bloodlust, Flask, Food und Trank sind 60–75 % des Sim-Werts auch bei perfektem
Spiel normal — Vergleichswert nur mit dem Preset **„No Buffs"** bilden. Report als
JSON: `curl https://www.raidbots.com/simbot/report/<id>/data.json`, darin
`sim.players[0].stats`.

## Geprüft und verworfen

Der **Single-Button Assistant** (Spell 1229376, `/cast Single-Button Assistant`) wäre
technisch die einzige Lösung mit echtem Zustandswissen — er kennt sogar die
Zielanzahl. Er trägt aber eine eingebaute Strafe von +0,2 s pro GCD (nach anderer
Quelle 25 %), also 13–20 % weniger Casts, und landet damit rechnerisch unter dem, was
die feste Sequenz erreicht. der Spieler will ihn nicht.

## Offen

- Die **Raid-Varianten** liegen auf keiner Taste; auf den Daumentasten sind die
  M+-Fassungen. Für Bosse ohne Adds umbinden, weil `/targetenemy` sonst auf Adds
  springt.
- Die **Talent-Import-Strings** stammen aus Icy Veins und Method und sind nicht
  nachgerechnet. Wichtig ist nur, dass **Wild Thrash** geskillt ist.
