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
                # first check for a basic land then legal multi-count
                if card.is_land():
                    if not 'Basic' in card.super_type:
                        return False,"Non-basic land: found {}x {}".format(n,cname)
                else:
                    try:
                        if n > mtg.legal_multicnt[cname]:
                            return False,"Found {}x {}".format(n,cname)
                    except KeyError:
                        return False,"Found {}x {}".format(n,cname)
            ttl += n
        if ttl != 100: return False,'Mainboard contain {} cards,'.format(ttl)
        return True,'Deck is EDH legal'

    def report(self):
        """ prints basic information to console """
        rpt = "Deck {} with Commander(s) '{}'\n".format(
            self.name,self.commander
        )
        rpt += "\tAvg CMC {:.2f}\n".format(self.avg_cmc())
        rpt += "\tMana Color {}\n".format(self.color_hist())
        rpt += "\tTypes {}\n".format(self.type_hist())
        rpt += "\tCMC {}\n".format(self.cmc_hist())
        rpt += "Cumulative CMC "
        rpt += " ".join(
            ["{} {:.2f}%".format(c, float(n) / self.nonland()) for c, n in self.cumulative_cmc_hist()]
        )
        rpt += "\n"
        return rpt

    def is_playable(self,card):
        """ determines if MTGCard card is playable in this deck """
        return set(card.color_ident).issubset(self.color_ident())

    ####
    # HISTOGRAMS
    ####

    def color_id_cmc_hist(self):
        """ returns histogram of cmcs in the deck, by color identity """
        cmcs = {}
        for cname in self._mb:
            # get the card object and the cmc (unless its a land)
            card = self._mb[cname]
            if card.is_land(): continue
            cmc = card.cmc

            # get the color identity
            ci = None
            if card.is_gold(True): ci = "O"
            else:
                clr = card.color_ident
                if not clr: ci = "C"
                else: ci = clr[0]

            # add to the cmc index
            if cmc in cmcs: cmcs[cmc][ci] += 1
            else:
                cmcs[cmc] = {c:0 for c in self.color_ident(False) + ["C","O"]}
                cmcs[cmc][ci] = 1

        # now, we want to return a list of ascended order cmcs
        # [(0,color-dict),...(n,color-dict)], it should already be sorted by
        # cmc in the dict but just in case
        pref = mtg.mana_colors + ["C","O"]
        return sorted(
            [(cmc,sorted([(clr,cmcs[cmc][clr]) for clr in cmcs[cmc]],
              reverse=True,key=lambda x: pref.index(x[0]))) for cmc in cmcs],
            key=lambda x:x[0]
        )

    def decklist(self):
        """ overrides mtgdeck.decklist separating Commander(s) into own category """
        # get the decklist, add a Commander category and move commander(s)
        dl = super().decklist()
        dl['Commander'] = []
        for cmdr in self.commander:
            dl['Commander'].append((1,cmdr))   # add cmdr to commander category
            i = dl['Creature'].index((1,cmdr)) # get index of commander
            del dl['Creature'][i]              # & remove from creature category
        return dl

    def competition_hash(self):
        """
        calculates the cockatrice hash for an online cEDH Competition deck
        (Commander(s) and only commander(s) in sidedeck)
        NOTE: we ignore the sideboard parameter
        """
        # we have to temporalily remove any cards in the sideboard
        t_sb = self._sb.copy()
        t_sqty = self._sqty.copy()
        t_mb = self._mb.copy()
        t_qty = self._qty.copy()
        dhash = None

        try:
            # empty the sideboard
            self.del_sideboard()

            # move commanders from mainboard to sideboard before hashing
            for cmdr in self.commander:
                card = self._mb[cmdr]
                self.del_card(cmdr)
                self.add_sb_card(card,1)

            # calculate the hash
            dhash = self.hash(True)

            # & restore the deck
            for cname in self._sb: self.add_card(self._sb[cname],1)
            self.del_sideboard()
            for cname in t_sb: self.add_sb_card(t_sb[cname],t_sqty[cname])
        except Exception as e:
            # recover
            self._mb = t_mb
            self._qty = t_qty
            self._sb = t_sb
            self._sqty = t_sqty
            raise

        return dhash

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
                raise RuntimeError("Unable to process '{}' files".format(fext))
            if not ds: raise RuntimeError("Error reading {}".format(f))
        except mtgl.MTGLException: raise
        except RuntimeError: raise
        except Exception as e:
            raise RuntimeError("Error reading deck {}\n{}".format(f,e))

        # start with the mainboard (make sure split cards are handled properly)
        for qty,cname in ds['mainboard']:
            if '/' in cname and not '//' in cname:
                cname = " // ".join([cname.strip() for cname in cname.split('/')])
            self.add_card(mv[cname],qty)

        # then the sideboard
        for qty,cname in ds['sideboard']:
            if '/' in cname and not '//' in cname:
                cname = " // ".join([cname.strip() for cname in cname.split('/')])
            try:
                self.add_sb_card(mv[cname],qty)
            except mtgl.MTGLException:
                # we'll ignore sideboard errors
                pass

        # since some decks have commander(s) in sideboard, some in mainboard & some
        # in both, make uniform and place in mainboard
        for cmdr in self._cmdr:
            if cmdr in self._sb:
                if not cmdr in self._mb: self.add_card(mv[cmdr],1)
                self.del_sb_card(cmdr)

        # set the deck name and path
        self._dname = ds['name'] # set the name
        self._path = f

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
                    if not 'name' in zone.attrs: continue
                    if zone.attrs['name'] == 'main':
                        for card in zone.find_all('card'):
                            ds['mainboard'].append(
                                (int(card.attrs['number']),   # qty
                                card.attrs['name'].__str__()) # card name
                            )
                    elif zone.attrs['name']  == 'side':
                        for card in zone.find_all('card'):
                            ds['sideboard'].append(
                                (int(card.attrs['number']),    # qty
                                 card.attrs['name'].__str__()) # card name
                            )
            except IndexError:
                raise
                #pass # TODO: why am I doing this

        except IOError as e:
            raise
            #if e.errno != 2: raise # TODO: why am I doing this
        finally:
            if fin: fin.close()

        # set the path if we get here
        return ds

    def _read_dec_(self,f):
        """ reads a .dec deck file """
        ds = {}

        fin = None
        try:
            fin = open(f)
            ls = fin.readlines()
            fin.close()

            # get cards from mainboard and sideboard
            # 3 cases mainboard, sideboard and token (we ignore tokens for now)
            ds = {'name': "", 'mainboard': [], 'sideboard': []}
            sb = False
            for l in ls:
                l = l.strip()  # remove trailing newlines
                if not l: continue  # skip empty lines
                if l.startswith('SB:'): sb = True  # tokens start after SB and are not prepended with "SB: "
                if sb and not l.startswith('SB:'): break
                else:
                    if sb: ds['sideboard'].append(EDHDeck._dec_card_(l[3:].strip()))
                    else: ds['mainboard'].append(EDHDeck._dec_card_(l))
        except IOError as e:
            raise
            #if e.errno != 2: raise
        finally:
            if fin: fin.close()
        return ds

    @staticmethod
    def _dec_card_(l):
        """ returns a tuple t = (cnt,name) from the line l """
        l = l.split(' ')
        return (int(l[0]),' '.join(l[1:]))

