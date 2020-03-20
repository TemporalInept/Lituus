#!/usr/bin/env python
""" lexer
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Top level directory for mtg grammar. The intent is to tag, tokenize the oracle text
and reduce the overall number of tokens in mtg card oracle text to facilitate
programmatic processing, categorization and 'reasoning' over MTG cards

Tokenizes tagged oracle text
"""

#__name__ = 'lexer'
__license__ = 'GPLv3'
__version__ = '0.1.0'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Production'

import lituus.mtgl.mtgl as mtgl

def tokenize(txt): return