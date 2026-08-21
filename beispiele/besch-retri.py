# Retri — Retribution Paladin (Templar), ilvl 288, Loadout 4. Fassung 2.
#
# GEGENUEBER FASSUNG 1 GEAENDERT (jeweils gemessen, 8000 Iterationen):
# * `execution_sentence` aus VOR entfernt  -> es verdraengte Spender, ohne
#   selbst Schaden zu bringen (88,1 -> 89,8 %).
# * `hammer_of_wrath` aus VOR heraus und als EIGENER Musterplatz
#   (89,8 -> 91,8 %). In VOR kam er 44,6 statt 18,9 mal; eine Bedingung
#   (`target.health.pct<20|buff.avenging_wrath.up`) half NICHT, weil sie an
#   der Puppe nie greift bzw. den Zauber gar nicht bremst. Nur die Begrenzung
#   auf einen Schrittplatz begrenzt ihn wirklich.
# * Reihenfolge in VOR: Hammer of Light zuerst — er hat das kuerzeste Fenster.
ZAUBER = {'TS':'templar_strike', 'TV':'templars_verdict',
          'BoJ':'blade_of_justice', 'J':'judgment', 'TSl':'templar_slash',
          'HoW':'hammer_of_wrath', 'DS':'divine_storm'}
# PFLICHT fuer Nahkaempfer: `auto_attack` — sonst schlaegt die Waffe nie zu
# (beim Retri fehlten dadurch 201,8 crusading_strike-Ausloesungen, 59,6 % DPS).
VOR = ['actions+=/auto_attack',
       'actions+=/hammer_of_light',
       'actions+=/wake_of_ashes',
       'actions+=/divine_toll',
       'actions+=/avenging_wrath',
       'actions+=/use_items']
BEREICHE = {'TS':(4,8), 'TV':(4,6), 'BoJ':(1,3), 'J':(1,3),
            'TSl':(0,1), 'HoW':(1,1), 'DS':(0,0)}
LAENGEN = (15, 16, 17)
KLICKS = (10,)
MESSLATTE = 74279.0
