#!/usr/bin/env python
""" mtgcard.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines the MTGCard class - a wrapper around a  card dict
"""

#__name__ = 'mtgcard'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
import lituus as lts
import lituus.mtg as mtg
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.mtgt as mtgt

# helper function
def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

class MTGCard(object):
    """ a more manageable wrapper around a card dictionary """
    def __init__(self,card):
        # set the card dict then pass the networkx tree to a ParseTree
        self._card = card         # the card dict
        self._kws = []            # list of keywords
        self._aws = []            # list of ability words

    def tree(self): raise lts.LituusException(lts.EIMPL,"Pending")

    """ pretty print card's tree """
    def print(self,attr=False): raise lts.LituusException(lts.EIMPL,"Pending")

    @property
    def name(self): return self._card['name']

    @property
    def rid(self): return self._card['rid']

    @property
    def sets(self): return self._card['sets']

    @property
    def super_type(self): return self._card['super-type']

    @property
    def type(self): return self._card['type']

    @property
    def sub_type(self): return self._card['sub-type']

    @property
    def primary_type(self): 
        for ptype in mtg.pri_types:
            if ptype in self.type: return ptype

    @property
    def cmc(self): return self._card['cmc']

    @property
    def face_cmc(self): return self._card['face-cmc']

    @property
    def mana_cost(self): return self._card['mana-cost']

    @property
    def color_ident(self):
        return sorted(self._card['color-ident'],key=mtg.mana_colors.index)

    @property
    def color(self):
        return sorted(self._card['colors'],key=mtg.mana_colors.index)

    @property
    def oracle(self): return self._card['oracle']

    # TODO: for debugging only
    @property
    def tag(self): return self._card['tag']

    # TODO: for debugging only
    @property
    def tree(self): return self._card['mtgt']

    @property # NOTE: this may include duplicates
    def keywords(self): raise lts.LituusException(lts.EIMPL,"Pending")

    @property
    def ability_words(self): raise lts.LituusException(lts.EIMPL,"Pending")

    @property
    def activated_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    @property
    def triggered_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    @property
    def pt(self):
        try:
            return self._card['P/T']
        except KeyError:
            raise lts.LituusException(lts.EATTR,"Not a creature")

    @property
    def sets(self): return self._card['sets']

    def is_split(self): return '//' in self._card['name']

    def is_land(self): return 'Land' in self._card['type']

    def is_creature(self): return 'Creature' in self._card['type']

    def is_artifact(self): return 'Artifact' in self._card['type']

    def is_enchantment(self): return 'Enchantment' in self._card['type']
    
    def is_instant(self): return 'Instant' in self._card['type']

    def is_sorcery(self): return 'Sorcery' in self._card['type']

    def is_planeswalker(self): return 'Planeswalker' in self._card['type']

    def is_legendary(self): return 'Legendary' in self._card['super-type']

    def is_multitype(self): return len(self.type) > 1

    def is_gold(self,ci=False): 
        return len(self.color_ident) > 1 if ci else len(self.color) > 1

    def is_historic(self):
        return self.is_artifact() | self.is_legendary() | ('Saga' in self.sub_type)

    def enters_tapped(self): raise lts.LituusException(lts.EIMPL,"Pending")


    def enters_tapped_cond(self): raise lts.LituusException(lts.EIMPL,"Pending")

    #### CASTING/COST RELATED ####

    def x_cost(self): return '{X}' in self.mana_cost

    def phyrexian_mana(self): 
        """ returns True if card has Phyrexian Mana symbols in casting """
        return mtgl.re_mtg_phy_ms.match(self.mana_cost) is not None

    def acc(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def rcc(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def qupto(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def additional_cost(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def grants_activated(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def act_mana_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def act_nonmana_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def tgr_mana_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def tgr_nonmana_ability(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def delayed_trigger(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def grants_trigger(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def etb(self,tgr=2): raise lts.LituusException(lts.EIMPL,"Pending")

    #### MISCELLANEOUS ####

    def grants_generic(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def grants_keyword(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def is_interactive(self): raise lts.LituusException(lts.EIMPL,"Pending")

    #### MANA RELATED ####

    def adds_mana_all(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def adds_mana(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def adds_mana_pref(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def mana_plurality(self): raise lts.LituusException(lts.EIMPL,"Pending")

    #### LAND RELATED ####

    def utility_land(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def nonmana_land(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def land_category(self): raise lts.LituusException(lts.EIMPL,"Pending")

    #### PRIVATE HELPER FUNCTIONS ####

    def _etb_self_(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def _etb_other_(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def _reduce_by_(self,ms): raise lts.LituusException(lts.EIMPL,"Pending")

