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
__version__ = '0.1.6'
__date__ = 'August 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
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
        self._kas = []            # list of keyword actions
        self._tree = card['mtgt'] # initialize the parse tree

        # pull out the keywords
        # NOTE: we only save the keywords themselves
        for node in self._tree.findall('keyword'):
            self._kws.append(self._tree.attr(node,'word'))

        # & then ability words
        for node in self._tree.findall('ability-word'):
            self._aws.append(self._tree.attr(node,'word'))

    def print(self,attr=False):
        """ pretty print card's tree """
        print(self.name)
        self._tree.print2(attr)

    @property
    def name(self): return self._card['name']

    @property
    def rid(self): return self._card['rid']

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
    def mana_cost(self): return self._card['mana-cost']

    @property
    def color_ident(self):
        return sorted(self._card['color-ident'],key=mtg.mana_colors.index)

    @property
    def color(self):
        return sorted(self._card['colors'],key=mtg.mana_colors.index)

    @property
    def oracle(self): return self._card['oracle']

    @property # NOTE: this may include duplicates
    def keywords(self): return self._kws

    @property
    def ability_words(self): return self._aws

    #TODO: for the below, how to implement these
    #@property
    #def activated_ability(self): return self._card['act-ability']

    #@property
    #def triggered_ability(self): return self._card['tgr-ability']

    @property
    def pt(self):
        try:
            return self._card['P/T']
        except KeyError:
            raise RuntimeError("{} is not a creature".format(self.name))

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

    # TODO: archaic
    def enters_tapped(self):
        """ returns whether the card enters tapped """
        for line in self.oracle:
            # NOTE:
            # 1. have only seen enters tapped on 1st line of oracle but just in case
            # 2. "comes into play" appears to have been errated out but keep it in mind
            if line.startswith("{} enters the battlefield tapped.".format(self.name)):
                return True
        return False

    # TODO: archaic
    def enters_tapped_cond(self):
        """ returns whether the card enters tapped unless a condition is met """
        for line in self.oracle:
            if line.startswith("As {} enters the battlefield,".format(self.name)) and\
               line.endswith("enters the battlefield tapped."):
                return True
            if line.startswith("{} enters the battlefield tapped unless".format(self.name)):
                return True
        return False

    #### CASTING/COST RELATED ####

    def x_cost(self): return '{X}' in self.mana_cost

    def phyrexian_mana(self): 
        """ returns True if card has Phyrexian Mana symbols in casting """
        return mtgl.re_mtg_phy_ms.match(self.mana_cost) is not None

    # TODO: archaic
    def acc(self):
        """ 
         returns the alternate casting cost of card as a 'mana string' or None. This
         includes cards of subtype Trap
        """
        # check for phyrexian mana
        if self.phyrexian_mana():
            rc = ""
            for ms in re.findall(re_ms, self.mana_cost):
                if _is_int_(ms): rc += "{{{}}}".format(ms)
                else:
                    # could assume no card with phyrexian mana has snow mana
                    if ms == 'X': rc += '{X}'
                    else:
                        s = ms.split('/')
                        if len(s) > 1 and s[1] != 'P': rc.append(ms)
            if rc == "": rc = "{0}"
            return rc

        # in oracle, look for alternate casting cost phrase
        for line in self.oracle:
            if re.search(re_acc,line): 
                amc = re.findall(re_ms, line)
                if not amc: return '{0}' # no mana payed
                else: return "".join(['{{{}}}'.format(c) for c in amc])

        # in definitions of ability words, look for alternate casting cost phrase
        for _,awt in self.ability_words:
            if re.search(re_acc,awt):
                amc = re.findall(re_ms, awt)
                if not amc: return '{0}'
                else: return "".join(['{{{}}}'.format(c) for c in amc]) 

        return None

    # TODO: archaic
    def rcc(self):
        """ same as above but considers ability/keyword reduced cards i.e. improvise """
        # look at the card's ability words searching for RCC expression or 
        # in definitions of ability words, look for alternate casting cost phrase
        op = "for each opponent you"
        ct = "card type among cards"
        bl = "basic lands"
        for aw,awt in self.ability_words:
            if re.search(re_rcc,awt) or re.search(re_rcc2(self.name),awt):
                if aw == 'domain': return self._reduce_by_('1'*5) 
                elif aw == 'undaunted': return self._reduce_by_('1'*3)                 
                else: 
                    # check if a for each or single mana reduction & get the mana symbols
                    dy = True if "for each" in awt else False
                    rmc = re.findall(re_ms, awt)

                    # if it's a for each we'll assume the max # of reduction
                    if dy:
                        if op in awt: return self._reduce_by_(rmc*3)
                        elif ct in awt: return self._reduce_by_(rmc*8)
                        elif bl in awt: return self._reduce_by_(rmc*5)
                        else: return self._reduce_by_(rmc*self.cmc)
                    else: return self._reduce_by_(rmc)

        # do the same for the oracle
        for line in self.oracle:
            if re.search(re_rcc,line) or re.search(re_rcc2(self.name),line): 
                # check if a for each or single mana reduction & get the mana symbols
                dy = True if "for each" in line else False
                rmc = re.findall(re_ms, line)

                # if it's a for each we'll assume the max # of reduction
                if dy:
                    if op in line: return self._reduce_by_(rmc*3)
                    elif ct in line: return self._reduce_by_(rmc*8)
                    elif bl in line: return self._reduce_by_(rmc*5)
                    else: return self._reduce_by_(rmc*self.cmc)
                else: return self._reduce_by_(rmc)
        
        # Keywords that reduce casting cost    
        for kw in self.v_kws():
            if kw == 'convoke': return "{0}" # assume enough creatures to pay for all
            elif kw in ['affinity','delve','improvise']: # assume can pay for all colorless
                rc = ""
                for ms in re.findall(re_ms, self.mana_cost):
                    if not _is_int_(ms): rc += "{{{}}}".format(ms)
                return rc if rc else "{0}"
            elif kw == 'offering': break # do nothing for now
            elif kw in ["dash","madness","miracle","ninjutsu","commander ninjutsu",
                        "emerge","evoke","prowl","spectacle","surge"]:
                # the reduced cost will be in the hypenhated portion, have to go
                # to original keywords and refind
                for x in self.keywords:
                    if x.startswith(kw): return x.split('-')[1]

        # do the same for untaps upto X lands this is difficult, assume the lands 
        # will untap for colored mana    
        ut = self.qupto()   
        if ut: return "{{{}}}".format(self.cmc - ut)

        return None

    # TODO: archaic
    # TODO: look at planeswalkers
    def qupto(self):
        """ 
         identifies whether the card has an ETB with untap up to X lands or as 
         part of the resolution untap up to X lands. For spells, we're looking 
         for "Do something. [You] [U|u]ntap uo to X lands." Pore over the pages 
         is the exception with "Draw three cards, untap up to two lands, then 
         discard a card." At present, we ignore Planeswalkers
        """
        # start with non-Planeswalker, non-Land permanents
        for line in self.oracle:
            if 'Instant' in self.type or 'Sorcery' in self.type:
                ret = re.search(re_qupto,line)
                if ret: return _E2I_[ret.groups(1)[0]]
            elif 'Planeswalker' in self.type: pass
            else:        
                ret = re.search(re_qupto2(self.name),line)
                if ret: return _E2I_[ret.groups(1)[0]]
        return None

    # TODO: archaic
    def additional_cost(self):
        """
         returns activated abilities with additional costs outside of {X}, {T}, {Q}
        """
        acs = []
        for m,c,e,_ in self.activated_ability:
            for cost in c.split(', '):
                if cost.strip() == "{T}" or cost.strip() == "{Q}": pass
                elif re.search(re_ms, cost.strip()): pass
                else: acs.append((m,c,e,cost.strip()))
        return acs

    # TODO: archaic
    def grants_activated(self):
        """ Returns True if card grants a triggered ability to a card or cards """
        for line in self.oracle:
            if not re.match(re_eqen,line): continue # only look at equipped/enchanted
            for subline in re.findall(re_dblq, line):
                try:
                    _,_ = subline.split(':')
                    return True
                except ValueError:
                    pass
        return False

    # TODO: archaic
    def act_mana_ability(self):
        """ returns a list of all mana activated abilties """
        return [(c,e) for m,c,e,_ in self.activated_ability if m]

    # TODO: archaic
    def act_nonmana_ability(self):
        """ returns a list of all nonmana activated abilities """
        return [(c,e) for m,c,e,_ in self.activated_ability if not m]

    # TODO: archaic
    def tgr_mana_ability(self):
        """ returns a list of all mana triggered abilties """
        return [(c,e) for m,c,e,_ in self.triggered_ability if m]

    def tgr_nonmana_ability(self):
        return [(c,e) for m,c,e,_ in self.triggered_ability if not m]

    # TODO: archaic
    def delayed_trigger(self):
        """ 
         returns True if the card has a delayed triggered ability. The words When, 
         Whenever or At will appear in the middle of a line but not inside
         double quotes  
        """
        for line in self.oracle:
            line = re.sub(re_dblq, '', line)
            if re.search(re_tgr, line) and not re.match(re_tgr, line): return True
        return False

    # TODO: archaic
    def grants_trigger(self):
        """ Returns True if card grants a triggered ability to a card or cards """
        for line in self.oracle:
            for subline in re.findall(re_dblq, line):
                if re.match(re_tgr, subline.replace('"', '')): return True
        return False

    # TODO: archaic
    def etb(self,tgr=2):
        """ 
         returns True if card has an etb ability where tgr = one of 
          {0='self',1='other',2='either',3='both'}
        """
        # dont execute if this is a non-permanent card
        if 'Instant' in self.type or 'Sorcery' in self.type: return False
        if tgr == 3: return self._etb_self_() and self._etb_other_()
        elif tgr == 2: return self._etb_self_() or self._etb_other_()
        elif tgr == 1: return self._etb_other_()
        elif tgr == 0: return self._etb_self_()
        return False

    #### MISCELLANEOUS ####

    # TODO: archaic
    def grants_generic(self):
        """ returns True if the card grants something to a card or cards """
        if self.name in ["Cavern of Souls","Boseiju, Who Shelters All"]: return True
        for line in self.oracle:
            if re.match(re_grant,line): return True
        return False

    # TODO: add this at some time
    def grants_keyword(self): pass

    # TODO: archaic
    def is_interactive(self):
        """ returns whether the card is interactive """
        if 'Instant' in self.type: return True
        elif 'flash' in self.v_kws(): return True
        elif self.activated_ability:
            for r in [r for m,_,_,r in self.activated_ability if m]:
                if "only during your turn" in r or "you could cast a sorcery" in r: pass
                else: return True 
        return False

    #### MANA RELATED ####

    # TODO: archaic
    def adds_mana_all(self):
        """ returns all unique mana symbols, card can produce across activations """
        mss = []        
        # determine if ritual or activated/triggered ability
        if self.is_instant() or self.is_sorcery():
            for l in self.oracle:
                if re.search(re_ma, l): mss.extend(re.findall(re_ms, l))
        else:
            for _,e in self.act_mana_ability() + self.tgr_mana_ability():
                res = re.findall(re_anym, e)
                if res:
                    if res[0][1] == 'color': mss.extend(mana_colors)
                    elif res[0][1] == 'type': mss.extend(mana_colors + ['C'])
                else: mss.extend(re.findall(re_ms, e))
        
        # check ability words definitions
        #for _,d in self.ability_words:
        #    res = re.findall(mtg.re_anym,d)
        #    if res:
        #        if res[0][1] == 'color': mss.extend(mtg.mana_colors)
        #        elif res[0][1] == 'type': mss.extend(mtg.mana_colors+['C'])
        #    else: mss.extend(re.findall(mtg.re_ms,d))
        return list(set(mss))

    # TODO: archaic
    def adds_mana(self):
        """
         returns the color/type and amount of mana the card can add as a list of
         mana symbols. For example Phyrexian Tower returns ['C','BB']
        """
        mss = []
        # determine if ritual or activated/triggered ability
        if self.is_instant() or self.is_sorcery(): # Ritual
            for l in self.oracle:
                if re.search(re_ma, l):
                    # should'nt have to do this but just in case
                    ms = re.findall(re_ms, l)  # extract the symbols
                    if 'or' in l: mss.extend(ms)  # if there's an or, theyre distinct
                    else: mss.append("".join(ms)) # otherwise, they're together
        else:
            for _,e in self.act_mana_ability() + self.tgr_mana_ability():
                res = re.findall(re_anym, e)
                if res:
                    n,t = res[0]
                    n = 1 if n == 'X' or n == 'a' else _E2I_[n]
                    clrs = mana_colors if t == 'color' else mana_colors + ['C']
                    mss.extend([n*clr for clr in clrs])
                else:
                    ms = re.findall(re_ms, e)  # extract the symbols
                    if 'or' in e: mss.extend(ms)  # if there's an or, theyre distinct
                    else: mss.append("".join(ms)) # otherwise, they're together

        # check ability word definitions
        #for _,d in self.ability_words:
        #    if re.search(mtg.re_ma,d): mss.append("".join(re.findall(mtg.re_ms,d)))
        # check ability words definitions
        #for _,d in self.ability_words:
        #    res = re.findall(mtg.re_anym,d)
        #    if res:
        #        n,t = res[0]
        #        n = 1 if n == 'X' or n == 'a' else _E2I_[n]
        #        clrs = mtg.mana_colors if t == 'color' else mtg.mana_colors+['C']
        #        mss.extend([n*clr for clr in clrs])
        #    else:
        #        ms = re.findall(mtg.re_ms,d)  # extract the symbols
        #        if 'or' in d: mss.extend(ms)  # if there's an or, theyre distinct
        #        else: mss.append("".join(ms)) # otherwise, they're together

        return mss

    # TODO: archaic
    def adds_mana_pref(self):
        """
         returns the prefered mana that could be produced via one activation
         i.e. 
          if it could produce a colorless and colored, returns the colored
          if it could produce x of a color or y of a color returns whichever
           is greatest
          if it could produce more than one colored, returns gold
        """
        # TODO: doesn't take into account stuff that could tap for W
        # or 'WB' for example
        mss = self.adds_mana()
        if len(mss) == 1: return mss[0]
        elif len(mss) >= 2:
            clr = None
            l = 0
            for ms in mss:              
                if ms[0] == 'C':
                    if clr == None or clr == 'C': 
                        clr = 'C'
                        l = max(l,len(ms))
                else:
                    if clr == None or clr == 'C':
                        clr = ms[0]
                        l = len(ms)
                    elif clr == ms[0]: l = max(l,len(ms))
                    elif l == len(ms): clr = 'O'
                    elif l > len(ms): 
                        clr = ms[0]
                        l = len(ms)
            return l*clr
        else: return ''

    # TODO: archaic
    def mana_plurality(self):
        """
         returns whether the card can produce uni (one colored mana), bi (2 
         different colors) mana, tri (3 different colors) mana, any (5 different 
         colors) 
        """
        high = 0
        for _,e in self.act_mana_ability() + self.tgr_mana_ability():
            if re.search(re_anym, e): x = 5
            else: x = len(set(re.findall(re_cm, e)))
            if x > high: high = x
        if high == 1: return "uni"        
        elif high == 2: return "bi"
        elif high == 3: return "tri"
        elif high == 5: return "any"
        else: return None    

    #### LAND RELATED ####

    # TODO: archaic
    def utility_land(self):
        """ returns True if this is a utility land, False otherwise. """
        if not self.is_land(): raise RuntimeError("{} is not a land".format(self.name))
        if not self.act_mana_ability(): return True
        elif self.additional_cost(): return True         
        elif self.triggered_ability(): return True
        elif self.delayed_trigger(): return True
        elif self.grants_trigger(): return True
        elif self.nonmana_land(): return True
        elif self.keywords or self.ability_words: return True
        elif self.grants_generic(): return True
        elif self.is_multitype(): return True
        return False

    # TODO: archaic
    def nonmana_land(self):
        """ returns True if this land card does not produce mana."""
        if not self.is_land(): raise RuntimeError("{} is not a land".format(self.name))        
        return ([_ for m,_,_,_ in self.activated_ability if m] or\
                [_ for m,_,_,_ in self.activated_ability if m]) == []

    # TODO: archaic
    def land_category(self):
        """
         returns the category of this land as one of the following (or None)
        """
        if not self.is_land(): raise RuntimeError("{} is not a land".format(self.name))

        # hardcoded, defined prefix or basic
        if 'Basic' in self.super_type: return 'Basic'         
        elif self.name in dual_land: return "Dual"
        elif self.name.startswith("Tainted"): return "Tainted"  

        # lands identified via triggered abilities
        for _,c,e,_ in self.triggered_ability:
            if re.match(re_blcst(self.name),c) and re.match(re_bleff,e): return "Bounce"
            elif e == 'scry 1.': return "Scry"          
            
        # lands identified via oracle
        for line in self.oracle:
            if line.startswith(self.name) and line.endswith("depletion counter on it."):
                return "Slow Depl"
            elif line.endswith("two or more basic lands."): return "Battle"
            elif line.endswith("two or more opponents."): return "Bond"
            elif line.endswith("two or fewer other lands."): return "Fast"
            elif re.search(re_chl,line): return "Check" 
            elif self.enters_tapped_cond():
                try:
                    cond = re.findall(re_utcond,line)[0]
                    if cond == "pay 2 life": return "Shock"
                    elif cond.startswith("reveal"): return "Reveal"
                except: pass
                    
        # cycle lands have a cycling keyword, hardcode the new Bicycle lands
        if "cycling" in self.v_kws():
            if self.name in bicycle_land: return "Bicycle"
            else: return "Cycling"
        
        # look at activated ability
        for _,c,e,r in self.activated_ability:
            if r.endswith(self.name + " doesn't untap during your next untap step."):
                return "Slow"
            if re.match(re_fila,c) and re.match(re_ma, e): return "Filter"
            if self.name in ["Zoetic Cavern","Nantuko Monastery"] or\
               (re.findall(re_ms, c) and "becomes" in e and "creature" in e):
                return "Man"
            if self.name == "Thawing Glaciers": return "Fetch"
            if re.match(re_flcst(self.name),c) and re.match(re_fleff,e): return "Fetch"            
            if self.name == "City of Brass": return "Pain"            
            if (re.match(re_plcst,c) and re.search(re_ma, e)): return "Pain"
            if re.search(re_plres(self.name),r):
                if "threshold" in self.v_aws(): return "Threshold"
                else: return "Pain"
            if re.match(re_slcst(self.name),c) and re.match(re_sleff,e): return "Sac"
            if re.match(re_sdpl(self.name),c) and\
             e.endswith("counters on {}, sacrifice it.".format(self.name)): 
                return "Sac Depl"            
            if c == "{{T}}, Remove a charge counter from {}".format(self.name) and\
               e == "Add one mana of any color.":
                return "Charge"
            if re.match(re_flcst(self.name),c) and re.match(re_stleff,e):
                return "Strip"
      
        return None

    #### PRIVATE HELPER FUNCTIONS ####

    # TODO: archaic
    def _etb_self_(self):
        """ returns True if card has a (self triggered) etb ability """
        # first check for rally or soulbond, special cases
        if 'rally' in self.v_aws(): return True
        if 'constellation' in self.v_aws(): return True
        if 'soulbond' in self.v_kws(): return True
        
        for _,c,_,r in self.triggered_ability:
            if re.match(re_etb(self.name),c): return True
        return False

    # TODO: archaic
    def _etb_other_(self):
        """ returns True if card has etb ability triggered by another permanent """
        # first check for rally, landfall or soulbond, special cases      
        if 'rally' in self.v_aws(): return True
        if 'landfall' in self.v_aws(): return True
        if 'constellation' in self.v_aws(): return True
        if 'soulbond' in self.v_kws(): return True
        
        # looking for the phrase
        #  When[ever] [another|a] ____ enters the battlefied[under your control],
        # at the beginning of a line in the oracle
        for _,c,_,r in self.triggered_ability:
            if re.match(re_etboth,c): return True
        return False

    # TODO: archaic
    def _reduce_by_(self,ms):
        """ returns the card's mana cost mc subtracted by list of mana symbols in ms """
        # have to take each symbol in ds - if its an integer, subtract it from the
        # integral portion of mc. Otherwise, subtract like mana from like mana i.e. 
        # if the symbol is 'G', subtract a 'G'. If no colored symbols remain, subtract
        # from the integral portion. Once done, any negative integers are set to 0

        # break up the card's mana cost into the integral (coloress) and mana symbols
        i = 0     # integral mana cost component
        oths = [] # list of other mana symbols
        for x in re.findall(re_ms, self.mana_cost):
            if _is_int_(x): i += int(x) # overkill, should only be 1 integer
            else: oths.append(x)

        # iterate through each mana symbol
        for m in ms:
            if _is_int_(m): i -= int(m) # if its an int, subtract from integral
            elif m == 'X': i = 0        # what to do here?
            else:
                # for each mana symbol, determine if we can remove a mana symbol
                # otherwise subtract from the integral portion
                f = -1
                for j,o in enumerate(oths):
                    if m in o.split('/'):
                        f = j
                        break
                if f >= 0: del oths[f]
                else: i -= 1   

        # set any less than zero integral to 0
        if i < 0: i = 0
        if not oths: rmc = "{{{}}}".format(i)
        else: 
            rmc = "".join("{{{}}}".format(x) for x in oths)
            if i > 0: rmc = "{{{}}}".format(i) + rmc
        return rmc

