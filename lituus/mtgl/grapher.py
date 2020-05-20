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
import lituus as lts
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.mtgt as mtgt
import lituus.mtgl.mtgl_dd as dd
#import lituus.mtgl.list_util as ll
import lituus.mtgl.mtgltag as tag

def graph(dcard):
    """
    graphs the oracle text in card cname return the MTG Tree
    :param dcard: the card dictionary
    :return: the MTG Tree of the oracle text
    """
    # create an empty tree and grab the parent
    t = mtgt.MTGTree(dcard['name'])
    parent = t.root

    # add a keywords node, all keywords lines will be rooted here IOT to have a
    # single node w/ all keyword clauses which facilitates searching for keywords
    kwid = t.add_node(parent,'keywords')

    # three basic line types:
    # 1) ability word line: (207.2c) have no definition in the comprehensive rules
    #  but based on card texts, follow simple rules of the form:
    #  AW — ABILITY DEFINITION.(starts with an ability word, contain a long hyphen
    #  and end with a sentence)
    # 2) keyword line: contains one or more comma seperated keyword clauses.
    #    a) standard - does not end with a period or double quote
    #    b) non-standard - contains non-standard 'cost' & ends w/ a period
    # 3) ability line (not a keyword or ability word line) Four general types
    #  112.3a Spell, 112.3b Activated, 112.3c Triggered & 112.3d static
    for line in [x for x in dcard['tag'].split('\n')]:
        if dd.re_aw_line.search(line): graph_ability_word(t,parent,line)
        elif dd.re_kw_line.search(line):
            # enumerate and graph each keyword clause
            for ktype,kw,param in dd.re_kw_clause.findall(line):
                graph_keyword(t,kwid,kw,ktype,param)
        else:
            if 'Instant' in dcard['type']: t.add_node(parent,'spell-line',line=line)
            elif 'Sorcery' in dcard['type']: t.add_node(parent,'spell-line',line=line)
            elif dd.re_activated_line.search(line): t.add_node(parent,'act-line',line=line)
            elif dd.re_triggered_line.search(line): t.add_node(parent,'tgr-line',line=line)
            else: t.add_node(parent,'static-line',line=line)

    # if the keywords node is empty, delete it
    if t.is_leaf('keywords:0'): t.del_node('keywords:0')

    return t

def graph_ability_word(t,pid,line):
    """
    graphs the ability word line in tree t at parent pid
    :param t: the tree
    :param pid: the parent
    :param line: the aw line to graph
    """
    pass

def graph_keyword(t,pid,kw,ktype,param):
    """
    graphs the keyword as a new node in t under parent pid
    :param t: the tree
    :param pid: parent id
    :param kw: keyword to graph
    :param ktype: optional keyword type (landwalk,cylcling,offering)
    :param param: optional parameters
    """
    # create the keyword clause node with keyword set (replace underscore w/ space)
    kwid = t.add_node(pid,'kw-clause')
    t.add_node(kwid,'keyword',value=kw.replace('_',' '))
    if ktype: t.add_node(kwid,'type',value=ktype)
    try:
        m = dd.kw_param[kw].search(param)
        if m.endpos == len(param):
            if m.group() != '': # have a good match, continue
                try:
                    for i,k in enumerate(dd.kw_param_template[kw]):
                        if m.group(i+1): t.add_node(kwid,k,value=m.group(i+1))
                except IndexError:
                    raise RuntimeError(
                        "Error with {} does not match template".format(kw)
                    )
        else:
            raise lts.LituusException(lts.ETREE,"Incomplete match for {}".format(kw))
    except KeyError:
        # either a misstagged kewyord or one that does not have a function
        raise lts.LituusException(
            lts.ETREE,"Missing template for keyword {}".format(kw)
        )

####
## PRIVATE FUNCTIONS
####

