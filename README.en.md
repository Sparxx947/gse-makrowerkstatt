# GSE Macro Workshop

*[Deutsche Fassung](README.md)*

Tools for building GSE sequences for World of Warcraft by **measurement rather than
guesswork**, using a locally built SimulationCraft as the test bench.

The approach reached **94 to 96 percent** of what a perfectly played character achieves in
the simulator, across five specialisations (Unholy DK, Retribution and Protection Paladin,
Beast Mastery Hunter, Arms Warrior).

**Full handbook covering the method:**
<https://claude.ai/code/artifact/239a1890-be4d-4834-8cb7-4b134802fa3c> (in German)

---

## Why this repository exists

A GSE sequence is a fixed list of steps advanced blindly. It cannot know anything about game
state. The obvious way to build one — invent a pattern, test it on a training dummy, adjust —
costs an evening per version and yields a single number that tells you nothing about *why*
it came out that way.

This takes a different route: the GSE step advance is reproduced exactly as a SimulationCraft
APL, and the simulator then races a few hundred patterns against each other — in minutes
instead of evenings, with a spell-by-spell breakdown.

The real value is not in the code but in the **comment headers**: nearly every script records
which concrete failed run forced it, and how many percentage points that run cost.

## What is here

| Path | Purpose |
|---|---|
| `werkzeug/gse-suche-lokal.py` | **The main tool.** Searches for the best step pattern using local SimC. Class-agnostic — spells, slot counts and extra lines come from a description file. |
| `werkzeug/gse3.py` | Encodes and decodes `!GSE3!` import strings (CBOR → raw Deflate → Base64). Also useful for taking other people's sequences apart. |
| `werkzeug/bauen-f2.py` | Best template for a new class: contains the scoring loop across a click-rate band, and four transferable findings in its header. |
| `werkzeug/bauen-dk-retri.py` | How a GSE structure is assembled (MetaData, Versions, Actions) — compact and readable. |
| `werkzeug/bauen-prot4.py` | Example of an off-GCD spell placed in *every* step without costing a slot. |
| `werkzeug/bauen-bm14.py` | Example of M+ and raid variants with and without `/targetenemy`. |
| `werkzeug/puppe-messen.py` | DPS and rotation quality from a combat log, filtering out other players hitting the same dummy. |
| `werkzeug/log-casts.py` | Which casts a sequence actually produced, optionally compared against a Raidbots report. |
| `werkzeug/log-sequenz.py` | GCD saturation, cooldown usage, resource overflow, buff uptimes over *active* combat time. |
| `werkzeug/simc-varianten.py` | Turns a base profile into a Raidbots run with profilesets, for when local simulation is not an option. |
| `werkzeug/prot-suche.py` | Predecessor of `gse-suche-lokal.py`, hard-wired. Reference reading only. |
| `werkzeug/varianten-arms-aoe4.py` | Example variant file for `simc-varianten.py`. |
| `beispiele/besch-dk.py`, `besch-retri.py` | Two complete, real description files — the best learning material here. |
| `LIESMICH-original.md` | The original working notes (German), covering the GSE3 format and the in-game pitfalls. |

Note: file and directory names are German. `werkzeug` = tools, `beispiele` = examples,
`bauen-*` = build scripts, `besch-*` = description files.

## Requirements

- Linux, macOS, or Windows with WSL 2
- `python3`, `git`, `build-essential`
- **SimulationCraft built locally** from the branch matching the game version you play

```bash
git clone https://github.com/simulationcraft/simc.git ~/simc-build
cd ~/simc-build && git checkout midnight
cd engine && SC_NO_NETWORKING=1 make optimized -j$(nproc)
```

The tools expect the binary at `~/simc-build/engine/simc`.

## Quick start

```bash
git clone https://github.com/Sparxx947/gse-makrowerkstatt.git ~/wow-gse
cd ~/wow-gse

# 1. Export the character profile in game with /simc, save it as basis.simc
# 2. Write a description file — use beispiele/besch-dk.py as a template
# 3. Run the search
werkzeug/gse-suche-lokal.py basis.simc beispiele/besch-dk.py \
    --vorlauf 800 --fein 8000 --beste 8
```

## Rules that cost points

Measured, not estimated. Derivations are in the handbook.

| Rule | Cost of breaking it |
|---|---|
| The precombat summon (`summon_pet` / `raise_dead`) belongs in the APL — a custom APL replaces the precombat list too | up to −92 % DPS |
| `auto_attack` is mandatory for melee | −28.6 points |
| Read up on class mechanics (example: Putrefy only works during Dark Transformation) | +11.5 points |
| Check every spell name against SimC individually — names in the report are not necessarily castable actions | run aborts |
| Cooldowns need at least two slots | −16 to −18 % of casts |
| Rather over- than under-represent buff cooldowns | −7 % |
| Score across a **band** of click rates, never a single one | −14 points of illusory gain |
| Sim cast shares are **not** a target — damage per cast is what matters | −16 % |
| One GCD spell per step; 255 characters is the hard limit | step never fires |

**And one rule that is not technical:** keep GSE's `msClickRate` at **100 ms or above**.
Conspicuously even input at high frequency is exactly the pattern bot detection looks for,
and 100 ms is also the GSE default. The two percent of damage a faster rate would yield is
left on the table deliberately.

## Adjust before the first run

The build scripts carry a placeholder for the GSE database:

```python
GSE_DATEI = Path('BITTE_ANPASSEN/WTF/Account/DEIN_ACCOUNT/SavedVariables/GSE.lua')
```

`ls <WoW>/_retail_/WTF/Account` shows what the account folder is called.

**Under WSL, additionally:** the "is WoW running" guard in the build scripts uses `pgrep`,
which cannot see Windows processes at all. It reports "not running" while WoW is running,
the script writes, and WoW overwrites it on logout. Use
`/mnt/c/Windows/System32/tasklist.exe` instead; the handbook has the exact code.

## About this edition

This repository is the **neutral edition**: character and account identifiers are replaced by
placeholders (`UH-DK`, `Retri`, `Prot-Pala`, `BM-Jäger`, `Arms-Krieger`, `DEIN_ACCOUNT`).
Nothing was removed technically — all measurements, derivations and pitfalls are complete.

## Licence

No licence file, so ordinary copyright applies. Use for your own macros is expressly welcome.
