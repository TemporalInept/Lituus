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

# TODO: remove text attributes after debugging is complete
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
    for i,line in enumerate([x for x in dcard['tag'].split('\n')]):
        try:
            if dd.re_aw_line.search(line): graph_ability_word(t,parent,line)
            elif dd.re_kw_line.search(line):
                # enumerate and graph each keyword clause
                for ktype,kw,param in dd.re_kw_clause.findall(line):
                    graph_keyword(t,kwid,kw,ktype,param)
            else:
                if 'Instant' in dcard['type']: t.add_node(parent,'spell-line',text=line)
                elif 'Sorcery' in dcard['type']: t.add_node(parent,'spell-line',text=line)
                elif dd.re_act_check.search(line): graph_activated(t,parent,line)
                elif dd.re_tgr_check.search(line): graph_triggered(t,parent,line)
                else: graph_clause(t,t.add_node(parent,'static-line',text=line),line)
        except RuntimeError:
            # For Debugging Purposes
            print("{} {}\n".format(dcard['name'],line))

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
    awid = t.add_node(pid,'aw-clause',text=line)
    try:
        aw,ad = dd.re_aw_line.search(line).groups()
        t.add_node(awid,'ability-word',value=aw)
        graph_clause(t,t.add_node(awid,'definition'),ad)
    except AttributeError:
        raise lts.LituusException(
            lts.EPTRN,"Failure matching aw line ({})".format(line)
        )

def graph_keyword(t,pid,kw,ktype,param):
    """
    graphs the keyword as a new node in t under parent pid
    :param t: the tree
    :param pid: parent id
    :param kw: keyword to graph
    :param ktype: optional keyword type (landwalk,cylcling,offering)
    :param param: optional parameters
    """
    # TODO: how to determine if we have a non-standard parameter that needs to be
    #  further graphed
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
                    raise lts.LituusException(
                        lts.EPTRN,"Error with {} does not match template".format(kw)
                    )
        else:
            raise lts.LituusException(lts.PTRN,"Incomplete match for {}".format(kw))
    except KeyError:
        # either a misstagged kewyord or one that does not have a function
        raise lts.LituusException(
            lts.EPTRN,"Missing template for keyword {}".format(kw)
        )

def graph_activated(t,pid,line):
    """
    graphs the activated ability in line under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param line: the tagged text to graph
    """
    try:
        # split the line into cost and effect graph each separately
        cost,effect = dd.re_act_line.search(line).groups()
        aaid = t.add_node(pid,'activated-ability',text=line)
        graph_clause(t,t.add_node(aaid,'activated-cost',tograph=cost),cost)
        graph_clause(t,t.add_node(aaid,'activated-effect',tograph=effect),effect)
    except AttributeError:
        raise lts.LituusException(
            lts.EPTRN,"Not an activated ability ({})".format(line)
        )

def graph_triggered(t,pid,line):
    """
    graphs the activated ability in line under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param line: the tagged text to graph
    """
    try:
        # at a minimum will have tp, condition and effect. may have instructions
        m = dd.re_tgr_line.search(line)
        taid = t.add_node(pid,'triggered-ability',text=line)
        t.add_node(taid,'triggered-preamble',value=m.group(1))
        t.add_node(taid,'triggered-condition',tograph=m.group(2))
        t.add_node(taid,'triggered-effect',tograph=m.group(3))
        if m.group(4): t.add_node(taid,'triggered-instruction',tograph=m.group(4))
    except AttributeError:
        raise lts.LituusException(
            lts.EPTRN,"Not a triggered ability ({})".format(line)
        )

def graph_clause(t,pid,clause):
    """
    graphs the clause under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param clause: the tagged text to graph
    """
    # starting high up, look for replacement effects
    # TODO: since the intent is to only graph those clauses that are entirely
    #  replacements and not those that contain one, how do we work this
    if 'cn<instead>' in clause:
        nid = graph_repl_instead(t,clause)
        if nid:
            rid = t.add_node(pid,'replacement-effect')
            t.add_edge(rid,nid)
            return
    t.add_node(pid,'clause',tograph=clause)

####
## REPLACEMENT CLAUSES
####

## INSTEAD (614.1a)

def graph_repl_instead(t,clause):
    """
    graphs a rootless 'instead' replacment effect (614.1a) in tree t
    :param t: the tree
    :param clause: the clause to graph
    :return: a rootless tree of the graphed clause or None
    """
    # test for if-would-instead
    m = dd.re_if_would_instead.search(clause)
    if m:
        iid = t.add_ur_node('if-instead-would',text=clause)
        t.add_node(iid,'thing',tograph=m.group(1))
        t.add_node(iid,'would',tograph=m.group(2))
        t.add_node(iid,'instead',tograph=m.group(3))
        return iid

    # test for if-instead
    m = dd.re_if_instead.search(clause)
    if m:
        iid = t.add_ur_node('if-instead',text=clause)
        t.add_node(iid,'condition',tograph=m.group(1))
        t.add_node(iid,'instead',tograph=m.group(2))
        return iid

    # test for if-instead fenced
    m = dd.re_if_instead_fence.search(clause)
    if m:
        iid = t.add_ur_node('if-instead-fence',text=clause)
        t.add_node(iid,'condition',tograph=m.group(1))
        t.add_node(iid,'instead',tograph=m.group(2))
        return iid

    # test for if-instead-of clause
    m = dd.re_if_instead_of.search(clause)
    if m:
        iid = t.add_ur_node('if-instead-of',text=clause)
        t.add_node(iid,'event',tograph=m.group(1))
        t.add_node(iid,'replacement',tograph=m.group(2))
        t.add_node(iid,'instead-of',tograph=m.group(3))
        return iid

    # test for instead-if clause
    m = dd.re_instead_if.search(clause)
    if m:
        iid = t.add_ur_node('instead-if',text=clause)
        t.add_node(iid,'instead',tograph=m.group(1))
        t.add_node(iid,'condition',tograph=m.group(2))
        return iid

    # test for instead-of-if clause
    m = dd.re_instead_of_if.search(clause)
    if m:
        iid = t.add_ur_node('instead-of-if',text=clause)
        t.add_node(iid,'replacement', tograph=m.group(1))
        t.add_node(iid,'instead-of',tograph=m.group(2))
        t.add_node(iid,'condition',tograph=m.group(3))
        return iid

    # test for that-would-instead clause
    # we have to deal with these differently due to how the condition & replacement
    # are separated/identified
    m = dd.re_that_would_instead.search(clause)
    if m:
        iid = t.add_ur_node('that-would-instead',text=clause)
        t.add_node(iid,'effect',tograph=m.group(1))
        try:
            original,new = _twi_split_(m.group(2))
        except AttributeError:
            return None
        t.add_node(iid,'original',tograph=original)
        t.add_node(iid,'instead',tograph=new)
        return iid

    return None

####
## PRIVATE FUNCTIONS
####

# find the stem of the action word
_re_act_wd_ = re.compile(r"(be )?(?:ka|xa)<([\w-]+)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*>")
def _re_2nd_act_(wd,tobe): # #^.*(now saving to disk).*$
    if tobe:
        return re.compile(
            r"^.*((?:is|are) (?:ka|xa)<(?:{})(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*>)".format(wd)
        )
    else:
        return re.compile(
            r"^.*((?:ka|xa)<(?:{})(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*>)".format(wd)
        )
def _twi_split_(txt):
    """
    determines the split location for a that-would-instead clause
    :param txt: txt to split
    :return: a tuple old,new
    """
    # find the first action word, generally the first word then find the second
    # occurrence of this word. The 2nd occurrence will be the beginning of new
    # NOTE: some words will "to be" in front
    # NOTE: have only seen lituus action words here but just in case
    tobe,wd = _re_act_wd_.search(txt).groups()
    m = _re_2nd_act_(wd,tobe).search(txt)
    i = m.span()[1] - len(m.group(1))
    return txt[:i-1],txt[i:]
