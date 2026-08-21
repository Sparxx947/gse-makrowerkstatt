# UH-DK — Unholy Death Knight, ilvl 288, Loadout 3.
# der Spieler: hier darf alles automatisch laufen — also auch Schmuckstuecke und
# Cooldowns. Messlatte ist deshalb das VOLLE Optimum (79.120 DPS), nicht das
# ohne Schmuck.
# Zauberauswahl aus dem Sim-Lauf (Casts je 5 min): scourge_strike 93,6 |
# death_coil 60,1 | festering_strike 14,0 | soul_reaper 11,9.
# Geprueft, was seine Skillung wirklich kennt: raise_abomination, apocalypse,
# unholy_assault, summon_gargoyle und vile_contagion FEHLEN — nicht eintragen.
ZAUBER = {'SS':'scourge_strike', 'DC':'death_coil',
          'FS':'festering_strike', 'SR':'soul_reaper'}
# PFLICHT: Eine eigene APL ersetzt auch die Precombat-Liste. Ohne den Ghul
# sind Dark Transformation, Putrefy und Sweeping Claws nicht castbar — im
# ersten Lauf fehlten dadurch 459 Sweeping-Claws-Treffer und die DPS lag bei
# 62 % statt 90+. Gleicher Fehler wie beim BM-Jaeger ohne summon_pet.
PRECOMBAT = ['actions.precombat=raise_dead', 'actions.precombat+=/snapshot_stats']
# PFLICHT fuer Nahkaempfer: Eine eigene APL ersetzt auch `auto_attack`.
# Ohne diese Zeile schlaegt die Waffe nie zu — beim Retri fehlten dadurch
# 201,8 crusading_strike-Ausloesungen und die DPS lag bei 59,6 % statt 90+.
VOR = ['actions+=/auto_attack',
       'actions+=/army_of_the_dead',
       'actions+=/dark_transformation',
       'actions+=/outbreak,if=!dot.virulent_plague.ticking',
       # Laut Icy Veins (12.1): Putrefy NUR waehrend Dark Transformation, sonst
       # verpufft der Commander-of-the-Dead-Bonus. Festering Scythe ist KEIN wirkbarer
       # Zauber, sondern ein Proc, der Festering Strike ersetzt.
       'actions+=/putrefy,if=buff.dark_transformation.up',
       'actions+=/use_items']
BEREICHE = {'SS':(4,8), 'DC':(3,7), 'FS':(1,3), 'SR':(1,3)}
LAENGEN = (12, 14, 16)
KLICKS = (10,)
MESSLATTE = 79120.0
