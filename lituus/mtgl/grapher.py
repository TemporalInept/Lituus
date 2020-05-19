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
    # create an empty tree
    t = mtgt.MTGTree(dcard['name'])
    parent = t.root

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
    # TODO: currently stripping each line due to TODO # 173 from reminder text
    for line in [x.strip() for x in dcard['tag'].split('\n')]:
        if dd.re_aw_line.search(line): t.add_node(parent,'aw-line',line=line)
        elif dd.re_kw_line.search(line): graph_kw_line(t,parent,line)
        else:
            if 'Instant' in dcard['type']: t.add_node(parent,'spell-line',line=line)
            elif 'Sorcery' in dcard['type']: t.add_node(parent,'spell-line',line=line)
            elif dd.re_activated_line.search(line): t.add_node(parent,'act-line',line=line)
            elif dd.re_triggered_line.search(line): t.add_node(parent,'tgr-line',line=line)
            else: t.add_node(parent,'static-line',line=line)
    return t

def graph_kw_line(t,pid,line):
    """
     graphs the keyword line at parent id pid of tree t
    :param t: the tree (MTGTree)
    :param pid: the parent id of this subtree
    :param line: the line to graph (must be a keyword line)
    """
    # create the keyword line node
    kwlid = t.add_node(pid,'kw-line',line=line)

    # each kwc is a tuple = (type,kw,parameters)
    for ktype,kw,param in dd.re_kw_clause.findall(line):
        graph_kw_node(t,kwlid,kw,ktype,param)

def graph_kw_node(t,pid,kw,ktype,param):
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
        if m is None:
            # may be non-standard kw line check for leading long hyphen. If so,
            # strip the long hyphen and pass the entire param as a value to the
            # first parameter in the param_template
            # TODO: do not like this handling at all
            # TODO: should we annotate that it is non-standard
            if param.startswith(mtgl.HYP):
                t.add_node(kwid,dd.kw_param_template[kw][0],value=param[1:])
        elif m.endpos == len(param):
            # have a good match, continue
            if m.group() != '':
                try:
                    for i,k in enumerate(dd.kw_param_template[kw]):
                        if m.group(i+1): t.add_node(kwid,k,value=m.group(i+1))
                except IndexError:
                    raise RuntimeError("Error with {} does not match template".format(kw))
                except KeyError:
                    t.add_node(kwid,'NO-TEMPLATE',kw=kw,param=param)
        else:
            raise lts.LituusException(lts.EDATA,"incomplete match")
    except KeyError:
        # either a misstagged kewyord or one that does not have a function
        t.add_node(kwid,'MISSTAG-ERROR',kw=kw,param=param)
    except AttributeError:
        # don't have it coded yet TODO: remove after debugging
        t.add_node(kwid,'NOT-IMPLEMENTED',kw=kw,param=param)

####
## PRIVATE FUNCTIONS
####

