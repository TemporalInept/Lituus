#!/usr/bin/env python
""" pack.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines a set of cards. Can be used for a multiverse or a deck.
"""

#__name__ = 'pack'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

from operator import itemgetter
import lituus as lts
import lituus.mtg as mtg
import lituus.mtgcard as mtgcard

class Pack(object):
    """ manages a set of cards """
    def __init__(self):
        self._mb = {}  # mainboard (mb): dict of cardname -> MTGCard object
        self._qty = {} # mb quanitties: dict of cardname -> # of cards in pack

    ####
    # OP OVERLOADING
    ####

    def __getitem__(self,cname):
        """ overload the subscript '[]' operator """
        if not cname in self._mb:
            raise lts.LituusException(lts.EDATA,"No such card {}".format(cname))
        return self._mb[cname]

    def __iter__(self):
        """ overload the __iter__ function to make dict looping transparent """
        yield from self._mb.__iter__()

    def __len__(self):
        """ overload length to return length of mainboard """
        return len(self._mb)

    @property
    def is_legal(self): return True

    def add_card(self,card,qty=1):
        """
         adds the card to the pack
        :param card: MTGCard object
        :param qty: # of cards to add
        """
        self._qty[card.name] = qty
        self._mb[card.name] = card

    def del_card(self,cname):
        """
         deletes the card identified by cname
        :param cname: card name
        """
        try:
            del self._qty[cname]
            del self._mb[cname]
        except KeyError:
            raise lts.LituusException(lts.EDATA,"No such card {}".format(cname))

    def has_card(self,cname): return cname in self._mb

    def has_cards(self,cards,op='and'):
        """
          returns True if cards with boolean operator op applied is in the deck's
          mainboard. op is oneof {'and','or'}
          Can be used to find synergetic pairings i.e. Dramatic Reversal and
          Isochron Scepter
         :param cards: list of card names to find
         :param op: oneof {'and','or'}
         :return; True of found
        """
        ks = self._mb.keys()
        x = False
        for card in cards:
            x = card in ks
            if op == 'and' and x == False: return False
            if op == 'or' and x == True: return True
        return x

    def cards(self,lands='all'):
        """
         returns a list of card names in pack where lands is oneof
         {'all'=keep all lands,'non-basic'=keep only non-basic,'none'=don't keep
         lands}
        :param lands: see above
        :return: a list of tuples (cname,qty)
        """
        cards = []
        for cname in self._qty:
            # don't count lands if specified
            if self._mb[cname].is_land() and (lands == 'none' or lands == 'non-basic'):
                if lands == 'none': continue
                elif 'Basic' in self._mb[cname].super_type: continue
            cards.append((cname,self._qty[cname]))
        return sorted(cards,key=itemgetter(0))

    ####
    # METRICS
    ####

    def qty(self,unique=False):
        """
         returns the # of cards in the pack.
        :param unique: True = return only unique cnt
        :return: # of cards in pack
        """
        if unique: return len(self._qty)
        else: return sum([self._qty[k] for k in self._qty])

    def avg_cmc(self):
        """ returns the average cmc of the pack. TTL CMC / # Non-land cards """
        ttl = 0
        n = 0.0

        # add each non-land card
        for cname in self._mb:
            if self._mb[cname].is_land(): continue
            ttl += self._qty[cname] * self._mb[cname].cmc
            n += 1
        return ttl / n

    def nonland(self):
        """ returns number of non-land cards in pack """
        return self.qty() - self.type_hist(False)['Land']

    def mana_base(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def double_mana(self):
        """
        returns list of cards in pack with double (or more) of the same mana symbol
        in the casting cost
        """
        dbl = []
        for cname in self._mb:
            # get the card object and skip if a land
            card = self._mb[cname]
            if card.is_land(): continue

            # find mana symbols in the casting cost
            try:
                mcs = mtg.re_mana_sym.findall(card.mana_cost)
            except TypeError as e:
                # cards with no casting cost i.e. suspend will end up here
                if mv[card].cmc == 0: continue
                else: raise lts.LituusException(lts.UNDEF,"Unexpected {}".format(e))

            # for ease, recreate manacost list removing extra symbols could be snow,
            # phyrexian or hybrid and numeral symbols
            mcs2 = []
            for mc in mcs:
                if '/' in mc:
                    for s in mc.split('/'):
                        if s in mtg.mana_colors: mcs2.append(s)
                elif mc in mtg.mana_colors: mcs2.append(mc)

            # iterate the modified list of mana symbols
            for mc in mcs2:
                if mcs2.count(mc) > 1:
                    dbl.append(cname)
                    break
        return dbl

    ####
    # HISTOGRAMS
    ####

    def mana_sym_hist(self,aslist=True):
        """
         returns histogram of pack's colored mana symbols (casting cost) as a
         list of tuples (Color,Cnt) if aslist or a dict color->cnt otherwise
         :param aslist: if true returns hist as a list otherwise as a dict
         :return: mana symbol histogram
        """
        mh = {x:0 for x in mtg.mana_colors}
        for c in self._mb:
            if not self._mb[c].is_land(): self._card_mana_(c,mh)
        mh = {x:mh[x] for x in mh if mh[x] > 0}
        if aslist: return [(x,mh[x]) for x in sorted(mh.keys())]
        else: return mh

    def color_hist(self,aslist=True):
        """
         returns histogram of pack's colors - colored mana in casting cost
        :param aslist: if true returns hist as a list otherwise as a dict
        :return: color histogram
        """
        ch = {}
        for c in self._mb:
            clr = "".join(self._mb[c].color)
            if not clr: continue
            if clr in ch: ch[clr] += self._qty[c]
            else: ch[clr] = self._qty[c]
        if aslist: return [(x,ch[x]) for x in sorted(ch.keys())]
        else: return ch

    def type_hist(self,aslist=True):
        """
         returns histogram of pack's types
        :param aslist: if true returns hist as a list otherwise as a dict
        :return: color histogram
        """
        th = {x:0 for x in mtg.card_types}
        for c in self._mb:
            for t in self._mb[c].type: th[t] += self._qty[c]
        th = {x:th[x] for x in th if th[x] > 0}
        if aslist: return [(x,th[x]) for x in sorted(th.keys())]
        else: return th

    def cmc_hist(self,aslist=True):
        """
         returns histogram of pack's cmcs (excluding lands)
        :param aslist: if true returns hist as a list otherwise as a dict
        :return: color histogram
        """
        ch = {}
        for c in self._mb:
            if self._mb[c].is_land(): continue
            cmc = self._mb[c].cmc
            if cmc in ch: ch[cmc] += self._qty[c]
            else: ch[cmc] = self._qty[c]
        if aslist: return [(x,ch[x]) for x in sorted(ch.keys())]
        else: return ch

    def cumulative_cmc_hist(self):
        """
        returns a histogram of the count of cards with casting costs upto and
        including the "current" cmc as a list of numerically ordered tuples
        """
        ch = self.cmc_hist()
        cch = []

        # sum the counts
        for i,t in enumerate(ch):
            cch.append((t[0],t[1]))
            if i > 0: cch[i] = (cch[i][0],cch[i-1][1] + cch[i][1])
        return cch

    def mana_producer_hist(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def mana_plurality_hist(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def land_cat_hist(self): raise lts.LituusException(lts.EIMPL,"Pending")

    def basic_hist(self):
        """ returns histogram of packs's lands: basic vs non-basics """
        lands = {'Basic':0,'Non-Basic':0}
        for cname in self._mb:
            card = self._mb[cname]
            if card.is_land():
                if 'Basic' in card.super_type: lands['Basic'] += self._qty[cname]
                else: lands['Non-Basic'] += self._qty[cname]
        return [(x,lands[x]) for x in sorted(lands.keys())]

    def gold_hist(self):
        """
         returns a histogram of the count of multicolored cards. This will be of
         the form i->n where i is the number of colors and n is the number of cards
         in the deck having i colors
        """
        # set histogram to 0 for 2..n where n is the maximum number of colors
        # i.e. 2 = 2 different colors, 3 = 3 different colors etc
        mch = {x:0 for x in range(2,len(mtg.mana_colors)+1)}

        for cname in self._mb:
            # get card object, skip if land
            card = self._mb[cname]
            if card.is_land(): continue

            # get the mana symbols in the cards cost
            try:
                mcs = mtg.re_mana_sym.findall(card.mana_cost)
            except TypeError:
                # cards with no casting cost i.e. suspend will end up here
                if mv[card].cmc == 0: continue
                else: raise lts.LituusException(lts.UNDEF,"Unexpected {}".format(e))
            mcs2 = []

            # for ease, recreate manacost list removing could be snow, phyrexian
            # or hybrid and numeral symbols
            for mc in mcs:
                if '/' in mc:
                    for s in mc.split('/'):
                        if s in mtg.mana_colors: mcs2.append(s)
                elif mc in mtg.mana_colors: mcs2.append(mc)

            try:
                mch[len(set(mcs2))] += 1
            except KeyError:
                pass
        return mch

    #####
    # PRIVATE FCT
    ####

    def _card_mana_(self,cname,chist):
        """
         updates a color hist chist with the colored mana symbols in card cname
        :param cname: name of card in pack to update chist with
        :param chist: the current color histogram
        """
        for ms in mtg.re_clr_mana_sym.findall(self._mb[cname].mana_cost):
            if ms in mtg.mana_colors: chist[ms] += self._qty[cname]
            elif '/' in ms:
                for s in ms.split('/'):
                    if s in mtg.mana_colors: chist[s] += self._qty[cname]