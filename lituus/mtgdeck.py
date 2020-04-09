#!/usr/bin/env python
""" mtgdeck.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines a MTG Deck as a subset of a pack. This is basically in the event that
someone wants to branch out into other decks but I plan only to subclass an
EDHDeck
"""

#__name__ = 'mtgdeck'
__license__ = 'GPLv3'
__version__ = '0.0.1'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

from hashlib import sha1
import lituus.pack as pack
import lituus.mtgcard as mtgcard

sbl = '0123456789abcdefghijklmnopqrstuvwxyz' # for deck hashing

class MTGDeck(pack.Pack):
    """ defines a MTG Constructed Deck (100.2) """
    def __init__(self,f=None,dname=None,durl=None,aname=None,aurl=None,diurl=None):
        """
        Initializes a deck from file if present or an empty deck if not
        :param f: the file path (local)
        :param dname: name of the deck
        :param durl: deck url
        :param aname: deck author
        :param aurl: author url
        :param diurl: discord url
        """
        super().__init__()
        self._sb = {}   # define the sideboard (100.4)
        self._sqty = {} # & sideboard quanities
        self._path = None
        self._dname = None
        self._url = None
        self._author = None
        self._aurl = None
        self._diurl = None
        if f: self.open_deck(f,dname,durl,aname,aurl,diurl)

    def open_deck(self,f,dname=None,durl=None,aname=None,aurl=None,diurl=None):
        """
        Opens a deck from file f (overwriting current deck if present)
        :param f: the file path (local)
        :param dname: name of the deck
        :param durl: deck url
        :param aname: deck author
        :param aurl: author url
        :param diurl: discord url
        """
        # TODO: add better exception handling and raising i.e. check for existence
        #  of file first
        try:
            self._read_deck_(f)
            self._dname = dname if dname else self._path.split('/')[-1]
            self._url = durl if durl else "Unknown"
            self._author = aname if aname else "Unknown"
            self._aurl = aurl if aurl else ""
            self._diurl = diurl if diurl else ""
        except Exception as e:
            raise pack.PackException(e)

    def save_deck(self,f): raise NotImplementedError

    @property
    def name(self): return self._dname

    @property
    def deck_url(self): return self._url

    @property
    def deck_file(self): return self._path

    @property
    def auther(self): return self._author

    @property
    def author_url(self): return self._aurl

    @property
    def discord_url(self): return self._diurl

    @property
    def mainboard(self): return sorted([(k,self._qty[k],self._mb[k]) for k in self._mb])

    @property
    def sideboard(self): return sorted([(k,self._sqty[k],self._sb[k]) for k in self._sb])

    def is_legal(self): raise NotImplementedError

    def add_sb_card(self,card,qty=1):
        """
         adds the card to the sideboard
        :param card: MTGCard object
        :param qty: # of cards to add
        """
        self._sqty[card.name] = qty
        self._sb[card.name] = card

    def del_sb_card(self,cname):
        """
         deletes the sideboard card identified by cname
        :param cname: card name
        """
        try:
            del self._sqty[cname]
            del self._sb[cname]
        except KeyError:
            raise PackException("No such card {}".format(cname))

    def hash(self,sideboard=False):
        """
        Calculates the cockatrice deck hash of this deck - see cockatrice
        decklist.cpp  function updateDeckHash
        :param sideboard: calculate sideboard into hash if set
        """
        ms = []
        ss = []

        # first the main board
        for cname in self._mb:
            for i in range(self._qty[cname]): ms.append(cname.lower())

        # then the sideboard
        if sideboard:
            for cname in self._sb:
                for i in range(self._sqty[cname]):
                    ss.append("SB: {}".format(cname.lower()))

        # sort the combined lists and hash
        dhash = sha1(";".join(sorted(ms+ss)).encode("utf-8")).digest()
        dhash = (
            (ord(dhash[0]) << 32) +
            (ord(dhash[1]) << 24) +
            (ord(dhash[2]) << 16) +
            (ord(dhash[3]) << 8) +
            (ord(dhash[4]))
        )

        # convert the hash to string
        neg = False
        if dhash < 0:
            neg = True
            dhash = -dhash

        dhash,rem = divmod(dhash,32)
        val = ''
        while dhash:
            val = sbl[rem] + val
            dhash,rem = divmod(dhash,32)
        val = ('-' if neg else '') + sbl[rem] + val

        return (8 - len(val)) * "0" + val

    ####
    # PRIVATE FCTS
    ####

    def _read_deck_(self,f): raise NotImplementedError

    def _write_deck(self,f): raise NotImplementedError