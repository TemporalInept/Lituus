#!/usr/bin/env python
""" mtg.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Constants and general functions
"""

__name__ = 'mtg'
__license__ = 'GPLv3'
__version__ = '0.2.0'
__date__ = 'May 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import os
from itertools import combinations

# COMMON PATHS (use path magic to a) hide our directory structure and b) enable
# lituus to find paths regardless of download/installation path
pth_resources = os.path.join(os.path.dirname(__file__),'resources')
pth_sto = os.path.join(os.path.dirname(__file__),'sto')
pth_data = os.path.join(os.path.dirname(__file__),'data')
pth_decks = os.path.join(os.path.dirname(__file__),'decks')
pth_esolw = os.path.join(os.path.dirname(__file__),'ESoLW/res')

# returns a single global copy of the multiverse
_mv = None
def get_multiverse():
    """ :returns multiverse dict """
    global _mv
    try:
        _ = not _mv
    except NameError:
        # import here to avoid ciruclar import references
        import lituus.multiverse as multiverse
        _mv = multiverse.multiverse()
    return _mv

# CONSTANTS
last_exp = ['WAR','RNA','GRN','C18','M19']
types = [
    'Artifact','Creature','Enchantment','Instant','Land','Planeswalker','Sorcery'
]
pri_types = [ # ordered by priority i.e. a 'Land Creature' is a Land first
    'Land','Creature','Artifact','Enchantment','Instant','Planeswalker','Sorcery'
]
mana_colors = ['W','U','B','R','G']
mana_types = ['S','C','P'] + mana_colors
lands = {
    'Swamp':'B',
    'Island':'U',
    'Mountain':'R',
    'Plains':'W',
    'Forest':'G',
    'Wastes': 'C'}
legal_multicnt = [
    "Rat Colony","Relentless Rats","Shadowborn Apostle","Persistent Petitioners"
]
mana_combinations = mana_colors + ["".join(x) for x in
                                   combinations(mana_colors, 2)] + \
                    ["".join(x) for x in combinations(mana_colors, 3)] + \
                    ["".join(x) for x in combinations(mana_colors, 4)] + [
                        'WUBRG']
land_cats = [
    "Basic","Bounce","Shock","Reveal","Battle","Bond","Fast","Check","Slow",
    "Slow Depl","Scry","Cycling","Bicyle","Filter","Man","Pain","Threshold",
    "Fetch","Sac","Sac Depl","Charge","Strip","Dual","Tainted","Other"]

### REG EXP CONSTANTS
re_ms = r"{[0-9wubrgcspx\/]+}" # matches 1 mana symbol brace enclosed digit, type {}

### HELPER FUNCTIONS
