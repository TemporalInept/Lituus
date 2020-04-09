#!/usr/bin/env python
""" edhdeck.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines a EDH Deck as a subset of a MTGDeck.
"""

#__name__ = 'edhdeck'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import os
from bs4 import BeautifulSoup as soup
import lituus.mtg as mtg
import lituus.mtgl.mtgl as mtgl
import lituus.multiverse as multiverse
import lituus.mtgdeck as mtgdeck

class EDHDeck(mtgdeck.MTGDeck):
    """ Defines an EDH Deck """
    def __init__(self,cs=None,f=None,dname=None,durl=None,aname=None,aurl=None,diurl=None):
        """
        Initializes an EDH  deck from file f with commander(s) cs if present or
        an empty deck if not
        :param f: the file path (local)
        :param cs: Commander(s) multiple cmdrs are separated by '/'s
        :param dname: name of the deck
        :param durl: deck url
        :param aname: deck author
        :param aurl: author url
        :param diurl: discord url
        """
        self._cmdr = [c.strip() for c in cs.split('/')] if cs else []
        super().__init__(f,dname,durl,aname,aurl,diurl)

    @property
    def commander(self): return self._cmdr

    def is_legal(self):
        """
        Checks for legality of deck
        :return: a tuple (True,) if legal, (False,Explanation) otherwise
        """
        # check for commander and 100 cards total in mainboard
        if not self._cmdr: return False,"EDH Deck must have a Commander(s)"

        # ensure mainboard is only 100 cards, only multiples of basic lands
        # (& those authorized at any number) and color identity
        ci = self.color_ident()
        ttl = 0
        for cname in self._mb:
            card = self._mb[cname]
            n = self._qty[cname]
            if n > 1:
                # first check for a basic land
                if card.is_land() and not 'Basic' in card.super_type:
                    return False,"Non-basic lands must be unique {}x {}".format(n,cname)
                # then check for legal multicnt
                try:
                    if n > mtg.legal_multicnt: return False,"Found {}x {}".format(n,cname)
                except KeyError:
                    return False,"Found {}x {}".format(n,cname)
            ttl += n
        if ttl != 100: return False,'Mainboard contain {} cards,'.format(ttl)
        return True,'Deck is EDH legal'

    def color_ident(self,aslist=True):
        """
        Returns the color identity of the deck. Default is as a list otherwise
        will return as a string. Uses the color-identity of the commanders and
        assumes the deck is legal
        :param aslist: True returns as list of mana colors, otherwise as string
        :return: color identity of the deck
        """
        ci = set([])
        for cmdr in self._cmdr: ci = ci.union(self._mb[cmdr].color_ident)
        ci = list(ci)
        ci.sort(key=mtg.mana_colors.index)
        return "".join(ci) if aslist else ci

    ####
    # PRIVATE FUNCTIONS
    ####

    def _read_deck_(self,f):
        """ reads a deck from file with path f """
        # check for commander
        if not self._cmdr: raise
        ds = None

        try:
            # get the multiverse (assumes saved)
            mv = multiverse.multiverse(0)

            # check file extension and read in if possible
            _,fext = os.path.splitext(f)
            if fext == '.cod': ds = self._read_cod_(f)
            elif fext == '.dec': ds = self._read_dec_(f)
            else:
                raise RuntimeError("Unable to process files of type '{}'".format(fext))
            if not ds: raise RuntimeError("No such deck {}".format(f))
        except mtgl.MTGLException: raise
        except RuntimeError: raise
        except Exception as e:
            raise RuntimeError("Error reading deck {}\n{}".format(f,e))

        # ds has keys name, mainboard, sideboard. for each card make sure names
        # like lim-duls vault are encoded properly & split cards are handled
        # read in the mainboard
        for qty,cname in ds['mainboard']:
            if '/' in cname and not '//' in cname:
                cname = " // ".join([cname.strip() for cname in cname.split('/')])
            self.add_card(mv[cname],qty)

        # read in the mainboard
        for qty,cname in ds['sideboard']:
            if '/' in cname and not '//' in cname:
                cname = " // ".join([cname.strip() for cname in cname.split('/')])
            self.add_sb_card(mv[cname],qty)

        # since some decks have commander(s) in sideboard, some in mainboard & some
        # in both, make uniform and place in mainboard
        for cmdr in self._cmdr:
            if cmdr in self._sb:
                if not cmdr in self._mb: self.add_card(mv[cmdr],1)
                self.del_sb_card(cmdr)
        # set the name and return
        self._dname = ds['name']

    def _read_cod_(self,f):
        """ reads a cockatrice deck file """
        ds = {'name':"",'mainboard':[],'sideboard':[]}
        fin = None
        try:
            # open the xml file, soup it and close
            fin = open(f)
            deck = soup(fin,'xml')
            fin.close()

            # is there a name in the cockatrice file?
            try:
                dname = deck.find('deckname').contents[0].__str__()
                if dname: ds['name'] = dname
            except IndexError:
                pass

            # get mainboard, sideboard cards
            try:
                zones = deck.find_all('zone')
                for zone in zones:
                    if 'name' in zone.attrs:
                        if zone.attrs['name'] == 'main':
                            for card in zone.find_all('card'):
                                ds['mainboard'].append(
                                    (int(card.attrs['number']),    # qty
                                    card.attrs['name'].__str__()) # card name
                                )
                    elif zone.attrs['name']  == 'side':
                        for card in zone.find_all('card'):
                            ds['sideboard'].append(
                                (int(card.attrs['number']),  # qty
                                 card.attrs['name'].__str__())  # card name
                            )
            except IndexError:
                pass # TODO: why am I doing this

        except IOError as e:
            if e.errno != 2: raise # TODO: why am I doing this
        finally:
            if fin: fin.close()

        # set the path if we get here
        self._path = f
        return ds

    def _read_dec_(self,f): return None