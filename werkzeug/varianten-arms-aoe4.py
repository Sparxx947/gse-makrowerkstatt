"""Arms Warrior (Arms-Krieger), MEHRERE ZIELE - Suchlauf 4, gezielt auf die Cooldowns.

WARUM DIESE VARIANTEN
=====================
Aus dem Report der Fassung 3 (vnQTabJEAvuHh33HjbsGMQ, 210.306 DPS) gegen die
Sim-Casts:

    Zauber            Fassung 3   Sim    Luecke
    Cleave                 65,1   70,8    -8 %
    Overpower              44,1   45,6    -3 %
    Execute                67,1   60,0   +12 %
    Colossus Smash          8,3    9,9   -16 %   <- ein Platz
    Sweeping Strikes        8,4   10,2   -18 %   <- ein Platz
    Bladestorm              9,9   12,0   -18 %   <- ein Platz

ALLE DREI Zauber mit genau einem Platz liegen 16-18 % unter dem Sim, alle
anderen nicht. Das ist kein Verpuffen (widerlegt, siehe
feedback_gse_cooldown_slots), sondern VERZUG: ein Platz bekommt zwar alle 1,7 s
einen Klick, aber nur dann einen Cast, wenn der Klick zufaellig ans GCD-Ende
faellt - also rund alle n * GCD = 24 s. Bei einem Cooldown von 30-45 s kostet
das je Zyklus mehrere Sekunden. Ein zweiter Platz halbiert den Verzug.

Execute liegt als einziger UEBER dem Sim und ist damit der Kandidat, der einen
Platz abgeben kann. Cleave ist mit 138.783 Schaden je Cast der staerkste und
liegt unter dem Sim - Plaetze dorthin sind nie verkehrt.

Gerechnet wird gegen den Sim-Wert 262.637 DPS (5 Ziele, buff-frei).
"""
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "simc_varianten", str(Path(__file__).resolve().parent / "simc-varianten.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
verteile = _mod.verteile

CL, EX, OP = "cleave", "execute", "overpower"
SW, CS, BL = "sweeping_strikes", "colossus_smash", "bladestorm"

# Ohne auto_attack erzeugt der Krieger keine Wut: 48.179 statt 197.000 DPS.
# Avatar drueckt Arms-Krieger von Hand (Alt), gehoert aber in die Rechnung.
VORSPANN = ["auto_attack", "avatar"]
PRECOMBAT = ["battle_stance"]

# Fassung 3 in ihrer tatsaechlichen Anordnung - der Nullpunkt des Laufs.
F3 = [CL, EX, OP, CL, EX, OP, CL, SW, CL, EX, OP, CL, CS, EX, CL, OP, BL]


def v(n, **anzahl):
    """Zusammensetzung -> gleichmaessig verteiltes Muster.

    Die Cooldowns stehen zuerst, damit sie ihre gleichmaessigen Wunschplaetze
    bekommen; die Fueller ruecken auf.
    """
    reihenfolge = [CS, SW, BL, CL, EX, OP]
    return verteile(n, [(s, anzahl[s]) for s in reihenfolge if anzahl.get(s)])


VARIANTEN = [
    ("F3_Referenz", F3),

    # --- Gegenprobe: dieselbe Zusammensetzung, nur gleichmaessig angeordnet ---
    ("F3_gleichverteilt", v(17, cleave=6, execute=4, overpower=4,
                            sweeping_strikes=1, colossus_smash=1, bladestorm=1)),

    # --- Colossus Smash bekommt einen zweiten Platz ---
    ("CS2_n18", v(18, cleave=6, execute=4, overpower=4,
                  sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("CS2_n17_wenigerEX", v(17, cleave=6, execute=3, overpower=4,
                            sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("CS2_n17_wenigerOP", v(17, cleave=6, execute=4, overpower=3,
                            sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("CS2_n17_wenigerCL", v(17, cleave=5, execute=4, overpower=4,
                            sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("CS3_n19", v(19, cleave=6, execute=4, overpower=4,
                  sweeping_strikes=1, colossus_smash=3, bladestorm=1)),

    # --- Sweeping Strikes bekommt einen zweiten Platz ---
    ("SW2_n18", v(18, cleave=6, execute=4, overpower=4,
                  sweeping_strikes=2, colossus_smash=1, bladestorm=1)),
    ("SW2_n17_wenigerEX", v(17, cleave=6, execute=3, overpower=4,
                            sweeping_strikes=2, colossus_smash=1, bladestorm=1)),

    # --- Bladestorm bekommt einen zweiten Platz ---
    ("BL2_n18", v(18, cleave=6, execute=4, overpower=4,
                  sweeping_strikes=1, colossus_smash=1, bladestorm=2)),
    ("BL2_n17_wenigerEX", v(17, cleave=6, execute=3, overpower=4,
                            sweeping_strikes=1, colossus_smash=1, bladestorm=2)),

    # --- zwei Cooldowns gleichzeitig verdoppelt ---
    ("CS2_SW2_n19", v(19, cleave=6, execute=4, overpower=4,
                      sweeping_strikes=2, colossus_smash=2, bladestorm=1)),
    ("CS2_SW2_n17", v(17, cleave=5, execute=3, overpower=4,
                      sweeping_strikes=2, colossus_smash=2, bladestorm=1)),
    ("CS2_BL2_n19", v(19, cleave=6, execute=4, overpower=4,
                      sweeping_strikes=1, colossus_smash=2, bladestorm=2)),

    # --- alle drei verdoppelt ---
    ("alle2_n20", v(20, cleave=6, execute=4, overpower=4,
                    sweeping_strikes=2, colossus_smash=2, bladestorm=2)),
    ("alle2_n18", v(18, cleave=5, execute=3, overpower=4,
                    sweeping_strikes=2, colossus_smash=2, bladestorm=2)),
    ("alle2_n17", v(17, cleave=5, execute=3, overpower=3,
                    sweeping_strikes=2, colossus_smash=2, bladestorm=2)),
    ("alle3_n23", v(23, cleave=7, execute=4, overpower=4,
                    sweeping_strikes=3, colossus_smash=3, bladestorm=2)),

    # --- Execute abgeben, Cleave staerken (Execute liegt ueber dem Sim) ---
    ("CL7_EX3_n17", v(17, cleave=7, execute=3, overpower=4,
                      sweeping_strikes=1, colossus_smash=1, bladestorm=1)),
    ("CL8_EX2_n17", v(17, cleave=8, execute=2, overpower=4,
                      sweeping_strikes=1, colossus_smash=1, bladestorm=1)),
    ("CL7_EX3_CS2_n18", v(18, cleave=7, execute=3, overpower=4,
                          sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("CL7_EX3_CS2_SW2_n19", v(19, cleave=7, execute=3, overpower=4,
                              sweeping_strikes=2, colossus_smash=2, bladestorm=1)),
    ("CL8_EX3_alle2_n20", v(20, cleave=8, execute=3, overpower=3,
                            sweeping_strikes=2, colossus_smash=2, bladestorm=2)),

    # --- kuerzerer Umlauf: mehr Klicks je Platz, weniger Verzug fuer alle ---
    ("kurz_n12", v(12, cleave=4, execute=2, overpower=3,
                   sweeping_strikes=1, colossus_smash=1, bladestorm=1)),
    ("kurz_n13_CS2", v(13, cleave=4, execute=2, overpower=3,
                       sweeping_strikes=1, colossus_smash=2, bladestorm=1)),
    ("kurz_n10", v(10, cleave=4, execute=2, overpower=1,
                   sweeping_strikes=1, colossus_smash=1, bladestorm=1)),

    # --- laengerer Umlauf als Gegenprobe zur Umlauflaenge ---
    ("lang_n26", v(26, cleave=9, execute=6, overpower=6,
                   sweeping_strikes=2, colossus_smash=2, bladestorm=1)),
    ("lang_n34_alle3", v(34, cleave=12, execute=7, overpower=7,
                         sweeping_strikes=3, colossus_smash=3, bladestorm=2)),
]
