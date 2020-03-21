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
__version__ = '0.0.1'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

from hashlib import sha1
#from operator import itemgetter
import lituus.mtgcard as mtgcard

#sbl = '0123456789abcdefghijklmnopqrstuvwxyz' # for pack hashing

class PackException(Exception):
    def __init__(self,message): Exception.__init__(self,message)

class Pack(object):
    """ manages a set of cards """
    def __init__(self):
        self._qty = {}   # dict of cardname -> number of cards in pack
        self._cards = {} # dict of cardname -> MTGCard object

    @property
    def is_legal(self): return True

    def __getitem__(self,cname):
        """ overload the subscript '[]' operator """
        if not cname in self._cards: raise PackException("No such card {}".format(cname))
        return self._cards[cname]

    def add_card(self,card):
        """
         adds the card to the pack
        :param card: MTGCard
        """
        if card.name in self._qty: self._qty[card.name] += 1
        else:
            self._qty[card.name] = 1
            self._cards[card.name] = card

    def del_card(self,cname):
        """
         deletes the card identified by cname
        :param cname: card name
        """
        try:
            del self._qty[cname]
            del self._cards[cname]
        except KeyError:
            raise PackException("No such card {}".format(cname))

    def qty(self,unique=True):
        """
         returns the # of cards in the pack if unique returns only the unique cnt
        :param unique: True = return only unique cnt
        :return: # of cards in pack
        """
        if unique: return len(self._qty)
        else: return sum([self._qty[k] for k in self._qty])

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
            if self._cards[cname].is_land() and (lands == 'none' or lands == 'non-basic'):
                if lands == 'none': continue
                elif 'Basic' in self._cards[cname].super_type: continue
            cards.append((cname,self._qty[cname]))
        return sorted(cards,key=itemgetter(0))
