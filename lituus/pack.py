#!/usr/bin/env python
""" pack.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines a set of cards
"""

#__name__ = 'multiverse'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import lituus.mtg as mtg
import lituus.mtgcard as mtgcard

class PackException(Exception):
    def __init__(self,message): Exception.__init__(self,message)

class Pack(object):
    """ manages a set of cards """
    def __init__(self):
        self._qty = {} # dict of cardname -> number of cards in pack
        self._mb = {}  # dict of cardname -> MTGCard object

#### OP OVERLOADING

    def __getitem__(self,cname):
        """ overload the subscript '[]' operator """
        if not cname in self._mb: raise PackException("No such card {}".format(cname))
        return self._mb[cname]

    def __iter__(self):
        """ overload the __iter__ function to make dict looping transparent """
        yield from self._mb.__iter__()

    def __len__(self):
        """ overload length to return length of mainboard """
        return len(self._mb)

    @property
    def is_legal(self): return True

    def add_card(self,card):
        """
         adds the card to the pack
        :param card: MTGCard
        """
        if card.name in self._qty: self._qty[card.name] += 1
        else:
            self._qty[card.name] = 1
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
            raise PackException("No such card {}".format(cname))

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

#### METRICS

    def qty(self,unique=True):
        """
         returns the # of cards in the pack.
        :param unique: True = return only unique cnt
        :return: # of cards in pack
        """
        if unique: return len(self._qty)
        else: return sum([self._qty[k] for k in self._qty])

#### HISTOGRAMS

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

#### PRIVATE FCT

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