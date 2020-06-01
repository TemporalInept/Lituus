#!/usr/bin/env python
""" grapher.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Graphs parsed oracle text as a rooted, ordered directed acyclic graph i.e. a Tree.
In a top down manner graphs increasinly smaller 'chunks' of mtgl (markup text).
"""

#__name__ = 'grapher'
__license__ = 'GPLv3'
__version__ = '0.1.3'
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
import lituus.mtgl.mtgltag as mtgltag

# TODO: togroup signifies attributes that need to be graphed
def graph(dcard):
    """
    graphs the oracle text in card cname return the MTG Tree
    :param dcard: the card dictionary
    :return: the MTG Tree of the oracle text
    """
    # create an empty tree & grab the parent. setup lines
    t = mtgt.MTGTree(dcard['name'])
    parent = t.root
    lines = []

    # three basic line types:
    # 1) ability word line: (207.2c) have no definition in the comprehensive rules
    #  but based on card texts, follow simple rules of the form:
    #  AW — ABILITY DEFINITION.(ability word and ability definition are separated
    #   by a long hyphen
    # 2) keyword line: contains one or more comma seperated keyword clauses.
    #    a) standard - does not end with a period or double quote
    #    b) non-standard - contains non-standard 'cost' & ends w/ a period
    # 3) ability line (not a keyword or ability word line) Four general types
    #  112.3a Spell, 112.3b Activated, 112.3c Triggered & 112.3d static
    # IOT to facilitate searching all keyword and ability words found will be
    # rooted under a single node. The ability word definitions will be added
    # back into the lines to be graphed further
    kwid = t.add_node(parent,'keywords')
    awid = t.add_node(parent,'ability-words')
    for line in dcard['tag'].split('\n'):
        if dd.re_kw_line.search(line):
            for ktype,kw,param in dd.re_kw_clause.findall(line):
                graph_keyword(t,kwid,kw,ktype,param)
        elif dd.re_aw_line.search(line):
            try:
                aw,ad = dd.re_aw_line.search(line).groups()
                t.add_node(awid,'ability-word',value=aw)
                graph_line(t,t.add_node(awid,'definition'),ad)
                lines.append(ad)
            except AttributeError:
                raise lts.LituusException(
                    lts.EPTRN,"Failure matching aw line ({})".format(line)
                )
        else: lines.append(line)

    # Remove keyword and ability word nodes if empty & graph the lines
    if t.is_leaf('keywords:0'): t.del_node('keywords:0')
    if t.is_leaf('ability-words:0'): t.del_node('ability-words:0')
    for line in lines: graph_line(t,parent,line,dcard['type'])

    # return the graph tree
    return t

def graph_keyword(t,pid,kw,ktype,param):
    """
    graphs the keyword as a new node in t under parent pid
    :param t: the tree
    :param pid: parent id
    :param kw: keyword to graph
    :param ktype: optional keyword type (landwalk,cylcling,offering)
    :param param: optional parameters
    """
    # create the keyword clause node with keyword (replacing underscore w/ space
    # and capitalizing first letter)
    kwid = t.add_node(pid,'kw-clause')
    t.add_node(kwid,'keyword',value=kw.replace('_',' ').capitalize())
    if ktype: t.add_node(kwid,'type',value=ktype)
    try:
        m = dd.kw_param[kw].search(param)
        if m.endpos == len(param):
            if m.group() != '': # have a good match, continue
                try:
                    # TODO: for each of these, have to graph accordingly
                    # i.e. cost should be graphed as a cost etc
                    for i,k in enumerate(dd.kw_param_template[kw]):
                        if m.group(i+1): t.add_node(kwid,k,value=m.group(i+1))
                except IndexError:
                    raise lts.LituusException(
                        lts.EPTRN,"Error with {} does not match template".format(kw)
                    )
        else:
            raise lts.LituusException(lts.PTRN,"Incomplete match for {}".format(kw))
    except KeyError:
        raise lts.LituusException(
            lts.EPTRN,"Missing template for keyword {}".format(kw)
        )

def graph_line(t,pid,line,ctype=None):
    """
    graphs the line of tagged text
    :param t: the tree
    :param pid: parent id
    :param line: line to graph
    :param ctype: the card type(s)
    """
    # enclosed quotes will mess up graphing - for now lines with enclosed quotes
    # will be extracted and left ungraphed
    if dd.re_enclosed_quote.search(line):
        ss = [x.strip()+'.' for x in dd.re_sentence.split(line) if x != '']
        for s in ss:
            if dd.re_enclosed_quote.search(s):
                t.add_node(pid,'enclosed-quote',ungraphed=s)
            else: graph_line(t,pid,s,ctype)
        #if len(ss) > 1:
        #    for s in ss:
        #        if dd.re_grant_ability_check.search(s):
        #            graph_granted_ability(t,pid,s)
        #        else: graph_line(t,pid,s,ctype)
        #else: graph_granted_ability(t,pid,ss[0])
    else:
        # Ability lines can be one of
        #  112.3a Spell = instant or sorcery,
        #  112.3b Activated = of the form cost:effect,
        #  112.3c Triggered = of the form tgr condition, effect. instructions &
        #  112.3d static = none of the above
        if dd.re_act_check.search(line): graph_activated(t,pid,line)
        elif dd.re_tgr_check.search(line): graph_triggered(t,pid,line)
        else:
            # only the first call from graph() will include a ctype. If there
            # isn't one graph the line without a line-node
            if not ctype: graph_phrase(t,pid,line)
            else:
                if 'Instant' in ctype or 'Sorcery' in ctype:
                    graph_phrase(t,t.add_node(pid,'spell-line'),line)
                else: graph_phrase(t,t.add_node(pid,'static-line'),line)

def graph_activated(t,pid,line):
    """
    graphs the activated ability in line under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param line: the tagged text to graph
    """
    try:
        # TODO: should we be using graph_line or graph_phrase
        # split the line into cost and effect graph each separately
        cost,effect,instr = dd.re_act_line.search(line).groups()
        aaid = t.add_node(pid,'activated-ability')
        graph_line(t,t.add_node(aaid,'activated-cost'),cost)
        graph_line(t,t.add_node(aaid,'activated-effect'),effect)
        if instr:
            graph_line(t,t.add_node(aaid,'activated-instructions'),instr)
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
        # TODO: should we be using graph_line or graph_phrase
        tp,cond,effect,instr = dd.re_tgr_line.search(line).groups()
        taid = t.add_node(pid,'triggered-ability')
        t.add_node(taid,'triggered-preamble',value=tp)
        graph_line(t,t.add_node(taid,'triggered-condition'),cond)
        graph_line(t,t.add_node(taid,'triggered-effect'),effect)
        if instr:
            graph_line(t,t.add_node(taid,'triggered-instruction'),instr)
    except AttributeError:
        raise lts.LituusException(
            lts.EPTRN,"Not a triggered ability ({})".format(line)
        )

def graph_phrase(t,pid,line):
    """
    Graphs phrase(s) in line looking at high level constructs which encompass one
    or more sentences. After lines (i.e. keyword, ability word, spell, activated,
    triggered, spell) the highest level constructs are phrases which include:
     replacement effects (614.1,614.2)
     alternate cost effects (118.9)
     optionals: player may ...
     conditionals
     stipulations: restrictions and additions
    :param t: the tree
    :param pid: parent of the line
    :param line: the text to graph
    """
    if graph_replacement_effects(t,pid,line): return
    elif graph_apc_phrases(t,pid,line): return
    elif graph_conditional_phrases(t,pid,line): return
    elif graph_stipulation_phrases(t,pid,line): return
    elif graph_optional_phrases(t,pid,line): return

    # TODO: at this point how to continue: could take each sentence if more than
    #  one and graph them as phrase and if only sentence, graph each clause (i.e.
    #  comma separated i.e. Goblin Bangchuckers
    # if we get here start by breaking the line into sentences
    ss = [x.strip() + '.' for x in dd.re_sentence.split(line) if x != '']
    if len(ss) > 1:
        for s in ss: graph_line(t,t.add_node(pid,'sentence'),s)
    else: t.add_node(pid,'ungraphed-sentence',tograph=line)

def graph_replacement_effects(t,pid,line):
    """
    graphs replacement effect as covered in (614). these are:
     614.1a effects that use the word 'instead'
     614.1b effects that use the workd 'skip'
     614.1c effects that read
      [This permanent] enters the battlefied with ...
      As [this permanent] enters the battlefield...
      [This permanent] enters the battlefield as...
     614.1d effects that read  (continuous effects)
      [This permanent] enters the battlefield...
      [Objects] enter the battlefield...
     614.1e effects that read As [this permanent] is turned face up...
     614.2 effects that apply to damage from a source (see 609.7)
    :param t: the tree
    :param pid: the parent id in the tree
    :param line: text to graph
    :return: returns the node id of the replacement effect root if a replacement
     effect was found and graphed
    """
    # NOTE: this is very inefficient as multiple patterns are applied to each
    #  line. IOT to decrease some of the inefficiency checks will be used to
    #  eliminate lines that do not meet the basic requirements to be graphed
    if 'cn<instead>' in line: # 614.1a 'instead' replacements
        nid = graph_repl_instead(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='instead'),nid)
            return nid
    elif 'xa<skip>' in line: # 614.1b 'skip' replacements
        nid = graph_repl_skip(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='skip'),nid)
            return nid
    elif dd.re_etb_repl_check.search(line): # 614.1c and 614.1d ETB replacements
        # try 614.1c
        nid = graph_repl_etb1(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='etb-1c'),nid)
            return nid

        # then 614.1d
        nid = graph_repl_etb2(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='etb-1d'),nid)
            return nid
    elif dd.re_turn_up_check.search(line):
        nid = graph_repl_face_up(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='face-up'),nid)
            return nid
    elif dd.re_repl_dmg_check.search(line):
        nid = graph_repl_damage(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'replacement-effect',type='damage'),nid)
            return nid

    return None

def graph_apc_phrases(t,pid,line):
    """
    graphs APC phrases in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of the APC phrase root or None
    """
    # See 118.9 for some phrasing

    # start with 'you may' optional APCs
    if 'xp<you> cn<may>':
        nid = graph_optional_apc(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'apc',type='optional'),nid)
            return nid

        #nid = graph_

    return None

def graph_optional_phrases(t,pid,line):
    """
    graphs optional phrase in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of optional phrase root or None
    """
    if 'cn<may>' in line:
        nid = graph_player_may(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'optional',type='may'),nid)
            return nid

    return None

def graph_conditional_phrases(t,pid,line):
    """
    graphs conditional phrase in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of conditional phrase root or None
    """
    # starting with conditional that contain 'if' (but not instead that are
    # already graphed from above, then unless
    if 'cn<if>' in line:
        nid = graph_conditional_if(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'conditional',type='if'),nid)
            return nid
    elif 'cn<unless>' in line:
        nid = graph_conditional_unless(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'conditional',type='unless'),nid)
            return nid

    return None

def graph_stipulation_phrases(t,pid,line):
    """
    graphs stipulation phrase in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of conditional phrase root or None
    """
    # start with only conjunctions
    if len(dd.re_only_conj_check.findall(line)) == 2:
        nid = graph_only_conjunction(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'restriction',type='only-conjunction'),nid)
            return nid
        #t.add_node(pid,'restriction',type='conjunction',tograph=line)
    elif 'cn<only_if>' in line:
        nid = graph_only_if(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'restriction',type='only-if'),nid)
            return nid
    elif 'cn<only>' in line:
        if 'cn<can>' in line:
            nid = graph_can_only(t,line)
            if nid:
                t.add_edge(t.add_node(pid,'restriction',type='can-only'),nid)
                return nid

        nid = graph_timing_restriction_only(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'restriction',type='timing'),nid)
            return nid
    elif 'cn<except>' in line:
        nid = graph_restriction_except(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'restriction',type='except'),nid)
            return nid

        nid = graph_addition_except(t,line)
        if nid:
            t.add_edge(t.add_node(pid,'addition',type='except'),nid)
            return nid

    return None

####
## REPLACEMENT CLAUSES
####

## INSTEAD (614.1a)

def graph_repl_instead(t,phrase):
    """
    graphs a rootless 'instead' replacment effect (614.1a) in tree t
    :param t: the tree
    :param phrase: the text to graph
    :return: a rootless tree of the graphed clause or None
    """
    # check for 'would' phrasing, 'of' phrasing and 'if' phrasing
    if 'cn<would>' in phrase:
        # if-instead-would
        try:
            thing,would,instead = dd.re_if_would_instead.search(phrase).groups()
            rid = t.add_ur_node('if-instead-would')
            graph_line(t,t.add_node(rid,'thing'),thing)
            graph_line(t,t.add_node(rid,'would'),would)
            graph_line(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # that-would-instead - have to deal with these differently due to
        # how the condition & replacement are separated/identified
        try:
            # get the effect and subphrase and split the subphrase. _twi_split_
            # will throw an exception if the phrase is not valid for this
            effect,subphrase = dd.re_that_would_instead.search(phrase).groups()
            would, instead = _twi_split_(subphrase)

            # now graph it
            rid = t.add_ur_node('that-would-instead')
            graph_line(t,t.add_node(rid,'effect'),effect)
            graph_line(t,t.add_node(rid,'would'),would)
            graph_line(t,t.add_node(rid,'instead'),instead)
            return rid
        except (AttributeError,lts.LituusException):
            pass

        # would-instead (timing related)
        try:
            cond,would,instead = dd.re_would_instead.search(phrase).groups()
            rid = t.add_ur_node('would-instead')
            graph_line(t,t.add_node(rid,'condition'),cond)
            graph_line(t,t.add_node(rid,'would'),would)
            graph_line(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for may instead (optional replacement value)
        try:
            # could use the group(3) to confirm players ar3 the same
            ply,act1,_,act2 = dd.re_may_instead.search(phrase).groups()
            rid = t.add_ur_node('may-instead')
            graph_player(t,rid,ply)
            graph_line(t,t.add_node(rid,'action'),act1)
            graph_line(t,t.add_node(rid,'instead'),act2)
            return rid
        except AttributeError:
            pass
    elif 'cn<of>' in phrase:
        # if-instead-of clause
        try:
            act,repl,iof = dd.re_if_instead_of.search(phrase).groups()
            rid = t.add_ur_node('if-instead-of')
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'replacement'),repl)
            graph_line(t,t.add_node(rid,'instead-of'),iof)
            return rid
        except AttributeError:
            pass

        # test for instead-of-if clause
        try:
            repl,iof,cond = dd.re_instead_of_if.search(phrase).groups()
            rid = t.add_ur_node('instead-of-if')
            graph_line(t,t.add_node(rid,'replacement'),repl)
            graph_line(t,t.add_node(rid,'instead-of'),iof)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass

        # test for instead-of
        try:
            repl,iof = dd.re_instead_of.search(phrase).groups()
            rid = t.add_ur_node('instead-of')
            graph_line(t,t.add_node(rid,'replacement'),repl)
            graph_line(t,t.add_node(rid,'instead-of'),iof)
            return rid
        except AttributeError:
            pass
    elif 'cn<if>' in phrase:
        # test for if-instead
        try:
            cond,instead = dd.re_if_instead.search(phrase).groups()
            rid = t.add_ur_node('if-instead')
            graph_line(t,t.add_node(rid,'condition'),cond)
            graph_line(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for if-instead fenced
        try:
            cond,instead = dd.re_if_instead_fence.search(phrase).groups()
            rid = t.add_ur_node('if-instead-fence')
            graph_line(t,t.add_node(rid,'condition'),cond)
            graph_line(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for instead-if clause
        try:
            instead,cond = dd.re_instead_if.search(phrase).groups()
            rid = t.add_ur_node('instead-if')
            graph_line(t,t.add_node(rid,'instead'),instead)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass
    else:
        pass
        # TODO: should we do some debugging statement here to check for missed
        #  phrasing

    return None

def graph_repl_skip(t,phrase):
    """
    graphs a skip replacement effect in clause (614.1b)
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of a rootless skip clause
    """
    try:
        ply,phase = dd.re_skip.search(phrase).groups()
        if not ply: ply = 'xp<you'
        rid = t.add_ur_node('skip')
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'phase'),phase)
        return rid
    except AttributeError:
        return None

def graph_repl_etb1(t,phrase):
    """
    graphs ETB replacement clauses from (614.1c)
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless graph or None
    """
    # Permanent ETB with ...
    try:
        perm,ctrs = dd.re_etb_with.search(phrase).groups()
        rid = t.add_ur_node('etb-with')
        graph_line(t,t.add_node(rid,'permanent'),perm)
        graph_line(t,t.add_node(rid,'counters'),ctrs)
        return rid
    except AttributeError:
        pass

    # As Permanent ETB ...
    try:
        perm,action = dd.re_as_etb.search(phrase).groups()
        rid = t.add_ur_node('as-etb')
        graph_line(t,t.add_node(rid,'permanent'),perm)
        graph_line(t,t.add_node(rid,'action'),action)
        return rid
    except AttributeError: # no match
        pass

    # Permanent ETB as
    try:
        perm,asa = dd.re_etb_as.search(phrase).groups()
        rid = t.add_ur_node('etb-as')
        graph_line(t,t.add_node(rid,'permanent'),perm)
        graph_line(t,t.add_node(rid,'as'),asa)
        return rid
    except AttributeError: # no match
        pass

    # found nothing
    return None

def graph_repl_etb2(t,phrase):
    """
    graphs ETB replacement clauses from (614.1d)
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless graph or None
    """
    try:
        perm,effect = dd.re_etb_1d.search(phrase).groups()
        rid = t.add_ur_node('etb-continuous')
        graph_line(t,t.add_node(rid,'permanent'),perm)
        graph_line(t,t.add_node(rid,'effect'),effect)
        return rid
    except AttributeError: # no match
        return None

def graph_repl_face_up(t,phrase):
    """
    graphs as obj is turned face up (614.1e)
    :param t: the tree
    :param phrase: the clause to graph
    :return: node id of the graphed clause or None
    """
    try:
        perm,act = dd.re_turn_up.search(phrase).groups()
        rid = t.add_ur_node('turned-up')
        graph_line(t,t.add_node(rid,'permanent'),perm)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        return None

def graph_repl_damage(t,phrase):
    """
    graphs as obj is turned face up (614.2)
    :param t: the tree
    :param phrase: the clause to graph
    :return: node id of the graphed clause or None
    """
    # look for prevent damage
    try:
        src,tgt = dd.re_repl_dmg.search(phrase).groups()
        iid = t.add_ur_node('prevent-damage-this-turn')
        graph_line(t,t.add_node(iid,'source'),src)
        graph_line(t,t.add_node(iid,'target'),tgt)
        return iid
    except AttributeError:
        pass

    # damage prevention if [object/source] would [old], [new]
    try:
        src,old,new = dd.re_if_would.search(phrase).groups()
        rid = t.add_ur_node('damage-repl-if-would')
        graph_line(t,t.add_node(rid,'source'),src)
        graph_line(t,t.add_node(rid,'damage'),old)
        graph_line(t,t.add_node(rid,'prevention'),new)
        return rid
    except AttributeError:
        pass

    return None

####
## APC PHRASES
####

def graph_optional_apc(t,phrase):
    """
    graphs optional APC (contains you may) related phrases containing
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless apc or None
    """
    # TODO: group these under checks
    # [condition]? [player] may [action] rather than pay [cost]
    try:
        cond,ply,act,cost = dd.re_action_apc.search(phrase).groups()
        rid = t.add_ur_node('apc-optional-action')
        if cond: graph_line(t,t.add_node(rid,'condition'),cond)
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'action'),act)
        graph_line(t,t.add_node(rid,'cost'),cost)
        return rid
    except AttributeError:
        pass

    # if [condition] you may cast ...
    try:
        cond = dd.re_cast_apc_nocast.search(phrase).groups()
        rid = t.add_ur_node('apc-optional-nocost')
        graph_line(t,t.add_node(rid,'condition'),cond)
        return rid
    except AttributeError:
        pass

    # alternate phrasing of action-apc
    try:
        cond,act = dd.re_if_cond_act_apc.search(phrase).groups()
        rid = t.add_ur_node('apc-optional-action-alt')
        graph_line(t,t.add_node(rid,'condition'),cond)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    # alternate phrasing of action-apc (the reverse)
    try:
        cost,ply,act = dd.re_rather_than_apc.search(phrase).groups()
        rid = t.add_ur_node('apc-optional-action-alt2')
        graph_line(t,t.add_node(rid,'cost'),cost)
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    return None

####
## CONDITIONAL PHRASES
####

def graph_player_may(t,phrase):
    """
    graphs player may optional phrases
    :param t: the tree
    :param phrase: the text to graph
    :return: the nod of the rootless player may node or None
    """
    try:
        ply,act = dd.re_optional_may.search(phrase).groups()
        rid = t.add_ur_node('player-may-action')
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    return None

####
## CONDITIONAL PHRASES
####

def graph_conditional_if(t,phrase):
    """
    graphs conditional phrases containing 'if'
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless conditional or None
    """
    # if a player does...
    try:
        ply,neg,act = dd.re_if_ply_does.search(phrase).groups()
        rid = t.add_ur_node("if-player-does{}".format('-not' if neg else ''))
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    # if a player cannot...
    try:
        ply,act = dd.re_if_ply_cant.search(phrase).groups()
        rid = t.add_ur_node('if-player-cannot')
        graph_player(t,rid,ply)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    # generic if condition, do not related to APC
    try:
        cond,act = dd.re_if_cond_act.search(phrase).groups()
        rid = t.add_ur_node('if-cond-action')
        graph_line(t,t.add_node(rid,'condition'),cond)
        graph_line(t,t.add_node(rid,'action'),act)
        return rid
    except AttributeError:
        pass

    #raise lts.LituusException(lts.ETREE,"Ungraphed if condition {}".format(phrase))

def graph_conditional_unless(t,phrase):
    """
    graphs conditional phrases containing 'unless
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless conditional or None
    """
    # five flavors
    if 'cn<cannot>' in phrase:
        try:
            # TODO: this is really a restriction
            thing,act,cond = dd.re_cannot_unless.search(phrase).groups()
            rid = t.add_ur_node('cannot-unless')
            graph_line(t,t.add_node(rid,'thing'),thing)
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass
    elif phrase.startswith('ka') or phrase.startswith('xa'):
        try:
            act,cond = dd.re_action_unless.search(phrase).groups()
            rid = t.add_ur_node('action-unless')
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass
    elif phrase.startswith('st'):
        try:
            stat,cond = dd.re_status_unless.search(phrase).groups()
            rid = t.add_ur_node('status-unless')
            t.add_node(rid,'status',value=stat)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass
    elif 'cn<may>' in phrase:
        try:
            ply,act,cond = dd.re_may_unless.search(phrase).groups()
            rid = t.add_ur_node('may-unless')
            graph_player(t,rid,ply)
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'condition'),cond)
            return rid
        except AttributeError:
            pass
    else:
        # TODO: currently not graphing these until we merge quantifiers and status
        #  with players and objects
        try:
            _,_ = dd.re_ungraphed_unless.search(phrase).groups()
            rid = t.add_urn_node('ungraphed-unles',tograph=phrase)
            return rid
        except AttributeError:
            pass

    return None

####
## GRAPH STIPULATIONS
####

def graph_only_conjunction(t,phrase):
    """
    graphs a conjunction of only restriction phrases
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless restrictions or None
    """
    try:
        # have to look at the first restriction type to determine 'what' clause
        # is. If rtype is only we have a conjunction of timing restrictions
        # otherwise we have a condition and a timing restriction
        act,ct1,cl1,ct2,cl2 = dd.re_only_conjunction.search(phrase).groups()
        rid = t.add_ur_node('only-conjunction')
        graph_line(t,t.add_node(rid,'action'),act)
        if ct1 == 'only': graph_line(t,t.add_node(rid,'phase'),cl1)
        elif ct1 == 'only_if': graph_line(t,t.add_node(rid,'condition'),cl1)
        if ct2 == 'only': graph_line(t,t.add_node(rid,'phase'),cl2)
        elif ct2 == 'only_if': graph_line(t,t.add_node(rid,'condition'),cl2)
        return rid
    except AttributeError:
        pass

    return None


def graph_only_if(t,phrase):
    """
    graphs restriction phrases containin only if
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless restriction or None
    """
    # only-if are always action only-if condition
    try:
        act,cond = dd.re_only_if.search(phrase).groups()
        rid = t.add_ur_node('only-if')
        graph_line(t,t.add_node(rid,'action'),act)
        graph_line(t,t.add_node(rid,'condition'),cond)
        return rid
    except AttributeError:
        return None

def graph_can_only(t,phrase):
    """
    graphs can only restriction phrase
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless restriction or None
    """
    try:
        thing,act,restr = dd.re_can_only.search(phrase).groups()
        rid = t.add_ur_node('can-only')
        graph_line(t,t.add_node(rid,'action'),act)
        graph_line(t,t.add_node(rid,'restriction'),restr)
        return rid
    except AttributeError:
        return None

def graph_timing_restriction_only(t,phrase):
    """
    graphs restriction phrases related to timing
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless timing restriction or None
    """
    if 'sq<during>' in phrase:
        try:
            act,ts = dd.re_only_during.search(phrase).groups()
            rid = t.add_ur_node('only-during')
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'phase'),ts)
            return rid
        except AttributeError:
            pass
    elif 'cn<could>' in phrase:
        try:
            ply1,opt,act1,tim,ply2,act2 = dd.re_only_could.search(phrase).groups()
            # opt is an implied can
            if not opt: opt = 'can'
            rid = t.add_ur_node('only-could',type=opt)


            # use player1 if present otherwise player2
            if not ply1: ply1 = ply2
            graph_player(t,rid,ply1)

            # strip hanging but from action (present in some cases)
            if act1.endswith(' but'): act1 = act1[:-4]

            # graph the remaining
            graph_line(t,t.add_node(rid,'action'),act1)
            graph_line(t,t.add_node(rid,'timing'),tim)
            graph_line(t,t.add_node(rid,'could'),act2)
            return rid
        except AttributeError:
            pass
    return None

def graph_restriction_except(t,phrase):
    """
    graphs restriction phrases containin except
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless restriction or None
    """
    if 'pr<for>' in phrase:
        try:
            act,obj1,obj2 = dd.re_except_for.search(phrase).groups()
            rid = t.add_ur_node('exclusion')
            graph_line(t,t.add_node(rid,'action'),act)
            graph_line(t,t.add_node(rid,'object'),obj1)
            graph_line(t,t.add_node(rid,'except-for'),obj2)
            return rid
        except AttributeError:
            pass
    elif 'pr<by>' in phrase:
        try:
            obj1,act,obj2 = dd.re_except_by.search(phrase).groups()
            rid = t.add_ur_node('exception')
            graph_line(t,t.add_node(rid,'object'),obj1)
            graph_line(t,t.add_node(rid,'cannot'),act)
            graph_line(t,t.add_node(rid,'except-by'),obj2)
            return rid
        except AttributeError:
            pass

    # TODO: Island Sanctuary, Flame Sweep, Akron Legionnaire, Keldon Firebombers,
    #  Slinn Voda, the Rising Deep and Inspire Awe are exceptions to the except
    #  for/by patterns. 'Ungraph' here until a solution can be found
    if dd.re_except_prep.search(phrase):
        return t.add_ur_node('except-prep',anamolie=phrase)

    return None

def graph_addition_except(t,phrase):
    """
    graphs restriction phrases containin except
    :param t: the tree
    :param phrase: the text to graph
    :return: node id of the rootless restriction or None
    """
    try:
        act,add = dd.re_except_it.search(phrase).groups()
        rid = t.add_ur_node('except-it')
        graph_line(t,t.add_node(rid,'action'),act)
        graph_line(t,t.add_node(rid,'except-it'),add)
        return rid
    except AttributeError:
        pass
    return None

#def graph_granted_ability(t,pid,line):
#    """
#    graphs granted ability in line
#    :param t: the tree
#    :param pid: parent id
#    :param line: line to graph
#    """
#    try:
#        bdur,obj,gw,ab1,ab2,edur = dd.re_grant_ability.search(line).groups()
#        gid = t.add_node(pid,'grant-ability',gw=mtgltag.tag_val(gw))
#        dur = bdur if bdur else edur if edur else None
#        if dur: graph_line(t,t.add_node(gid,'durartion'),dur)
#        graph_line(t,t.add_node(gid,'object'),obj)
#        graph_line(t,t.add_node(gid,'ability'),ab1)
#        if ab2: graph_line(t,t.add_node(gid,'ability'),ab2)
#    except AttributeError:
#        raise lts.LituusException(
#            lts.EPTRN, "Not a granted ability ({})".format(line)
#        )

####
## CLAUSES AND TOKENS
####

#graph_line(t,t.add_node(rid,'player'),ply)
def graph_player(t,pid,ply):
    """
    Graphs the player clause ply under/in node pid
    :param t: the tree
    :param pid: the parent id
    :param ply: the playe rclause
    :return: the player node id
    """
    # TODO: this is a proof of concept and will extract singular player value
    #  all else will be an ungraphed phrase
    try:
        ply = dd.re_vanilla_player.search(ply).group(1)
        return t.add_node(pid,'player',value=ply)
    except AttributeError:
        pass

    # default
    return graph_line(t,t.add_node(pid,'player'),ply)

####
## PRIVATE FUNCTIONS
####

# find the stem of the action word
_re_act_wd_ = re.compile(
    r"(be )?(?:ka|xa)<([\w-]+)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*>"
)
def _re_2nd_act_(wd,tobe):
    if tobe:
        return re.compile(
            r"^.*((?:is|are) "
              r"(?:ka|xa)<(?:{})(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*>)".format(wd)
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
    try:
        tobe,wd = _re_act_wd_.search(txt).groups()
        m = _re_2nd_act_(wd,tobe).search(txt)
        i = m.span()[1] - len(m.group(1))
        return txt[:i-1],txt[i:]
    except AttributeError:
        raise lts.LituusException(lts.EPTRN,"Not a twi clause")