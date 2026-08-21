# Changelog

Alle nennenswerten Änderungen an diesem Projekt / All notable changes to this project.

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Added

- Twelve tools for building and measuring GSE sequences: pattern search against a locally
  built SimulationCraft (`gse-suche-lokal.py`), `!GSE3!` encoding and decoding (`gse3.py`),
  four build scripts covering different class shapes, three combat-log analysers, and the
  Raidbots profileset path as a fallback.
- Two complete description files as templates (`beispiele/besch-dk.py`, `besch-retri.py`).
- Bilingual README documenting the method, the requirements, and the nine measured rules
  whose violation costs between 7 and 92 percent.
- Original working notes (`LIESMICH-original.md`) covering the GSE3 wire format and the
  in-game pitfalls when writing to `GSE.lua`.

### Changed

- Character and account identifiers replaced by neutral placeholders throughout.
- Build scripts resolve their sibling modules relative to their own location instead of an
  absolute home directory, and carry an explicit `BITTE_ANPASSEN` placeholder for the GSE
  database path rather than a working path from one specific machine.
