#!/usr/bin/env python
""" lituus v 0.2.1: A Python 3.x Magic the Gathering Oracle Parsing and Collation
Tool primarily for the study of Competitive EDH (cEDH)
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Top level directory for lituus program files
Contains:
 /ESoLW report files
 /mtgl parsing and graphing files
 /resources contains AllCards.json and the cEDH database
 /sto contains data files downloaded or generated by lituus
 __init__.py this file
 decklist.py downloads, scrapes and stores cEDH decks from online sources
 mtg.py common paths and constants used by lituus program files
 pack.py super class for a set of cards
 mtgdeck.py defines a constructed MTG deck
 edhdeck.py defiens a constructed EDH deck
 mtgcard.py defines the MTGCard class - a wrapper around a card dict
 multiverse.py MTGCard generator for all cEDH legal cards in the multiverse
 scrape.py scraper for online decks

DO NOT IMPORT *

Defines Lituus error classes for consolidation purposes.
"""

#__name__ = 'Lituus'
__license__ = 'GPLv3'
__version__ = '0.2.3'
__date__ = 'May 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

# Lituus Error modeled after EnvironmentError as tuple (ERRNO,ERRMSG)
class LituusException(Exception):
    def __init__(self,errno,message):
        self.errno = errno
        self.errmsg = message
        super().__init__(message)
    def __str__(self):
        return "({}): {}".format(self.errno,self.errmsg)

# Define our error numbers
EUNDEF   =  0 # Undefined
EGENERIC =  1 # Basic something happened
EIOIN    =  2 # Input
EIOOUT   =  3 # Output
ENET     =  4 # Network i.e. Internet related
EPARAM   =  5 # Parameter Error
EDATA    =  6 # Data Error
EATTR    =  7 # Attribute Error
EIMPL    =  8 # ImplementationError
# MTGL RELATED
EMTGL    = 10 # Generic MTGL Error
ETAG     = 11 # MTGL Tag Error
ETAGGING = 12 # Error while tagging oracle
# MTG TREE RELATED
ETREE    = 20 # Generic tree error
ENODE    = 21 # Node error
EPTRN    = 22 # Pattern Error

# for setup.py us
version = __version__
long_desc = """
 UNDER CONSTRUCTION
"""

