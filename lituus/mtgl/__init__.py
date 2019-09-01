#!/usr/bin/env python
""" mtgl
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Top level directory for mtg grammar. The intent is to tag, tokenize the oracle text
and reduce the overall number of tokens in mtg card oracle text to facilitate
programmatic processing, categorization and 'reasoning' over MTG cards

Top level directory for MTG card oracle parsing and graphing
Contains:
 mtgl.py - defines regex, string replacements etc for parsing/processin mtg oracle
  text
 tagger.py - a first-pass parser, tagging mtg oracle text
 lexer.py - tokenizes the tagged text
 parser.py - parses tagged and tokeneized oracle text and graphs it
 mtgt.py - defines the MTGTree (a wrapper around a networkx rooted, ordered DAG)
"""

__name__ = 'mtgl'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__date__ = 'June 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'


