#!/usr/bin/env python
""" grapher.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Graphs parsed oracle text as a rooted, ordered directed acyclic graph i.e. a Tree
"""

#__name__ = 'grapher'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__date__ = 'May 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.mtgt as mtgt
#import lituus.mtgl.list_util as ll
import lituus.mtgl.mtgltag as tag

def graph(cname,dcard):
    """
    graphs the oracle text in card cname return the MTG Tree
    :param cname: name of card
    :param dcard: the card dictionary
    :return: the MTG Tree of the oracle text
    """
    # split the txt into lines and determine the type of each line
    # three basic line types:
    # 1) ability word line: starts with an ability word, contain a long hyphen
    #  and end with a sentence
    # 2) keyword line: contains one or more comma seperated keyword clauses.
    #    a) standard - does not end with a period or double quote
    #    b) non-standard - contains non-standard 'cost' & ends w/ a period
    # 3) ability line (not a keyword or ability word line) Four general types
    #  a. 113.3a Spell - an instant or sorcery
    #  b. 113.3b Activated - has the form cost: effect
    #  c. 113.3c Triggered - has the form TRIGGER PREAMBLE instructions
    #  d. 113.3d static all other
    lines = []
    for line in dcard['tag'].split('\n'):
        if mtgl.re_aw_line.search(line): lines.append(('aw-line',line))
        elif mtgl.re_kw_line.search(line): lines.append(('kw-line',line))
        else:
            if 'Instant' in dcard['type'] or 'Sorcery' in dcard['type']:
                lines.append(('spell-line',line))
            elif mtgl.re_activated_line.search(line): lines.append(('act-line',line))
            elif mtgl.re_triggered_line.search(line): lines.append(('tgr-line',line))
            else: lines.append(('static-line',line))
    return lines