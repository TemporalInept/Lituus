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
__version__ = '0.1.6'
__date__ = 'July 2020'
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

    # check for empty oracle texts and return the empty tree
    # TODO: what about split cards where one side has no text?
    if dcard['tag'] == '': return t

    # do we have a split card?
    if '//' in dcard['name']:
        a,b = dcard['name'].split(' // ')
        pids = [
            t.add_node(parent,'side-a',name=a),
            t.add_node(parent,'side-b',name=b)
        ]
    else: pids = [parent]

    for i,side in enumerate(dcard['tag'].split(' // ')):
        lines = []

        # three basic line types:
        # 1) ability word line: (207.2c) have no definition in the comprehensive
        # rules but based on card texts, follow simple rules of the form:
        #  AW — ABILITY DEFINITION.(ability word and ability definition are
        #   separated by a long hyphen
        # 2) keyword line: contains one or more comma seperated keyword clauses.
        #    a) standard - does not end with a period or double quote
        #    b) non-standard - contains non-standard 'cost' & ends w/ a period
        # 3) ability line (not a keyword or ability word line) 4 general types
        #  112.3a Spell, 112.3b Activated, 112.3c Triggered & 112.3d static
        # IOT to facilitate searching keyword and ability words found will be
        # rooted under a single node. The ability word definitions will be added
        # back into the lines to be graphed further
        kwid = t.add_node(pids[i],'keywords')
        awid = t.add_node(pids[i],'ability-words')
        for line in side.split('\n'):
            if not line: continue
            if dd.re_kw_line.search(line):
                for ktype,kw,param in dd.re_kw_clause.findall(line):
                    graph_keyword(t,kwid,kw,ktype,param)
            elif dd.re_aw_line.search(line):
                try:
                    # for ability words, don't want to graph the definition twice
                    # so graph the line, then add the ability-word node with the
                    # the word and a reference to the graphed definition
                    aw,ad = dd.re_aw_line.search(line).groups()
                    graph_line(t,pids[i],ad)
                    t.add_node(
                        awid,'ability-word',value=aw,id=t.children(pids[i])[-1]
                    )
                except AttributeError as e:
                    if e.__str__() == "'NoneType' object has no attribute 'groups'":
                        raise lts.LituusException(
                            lts.EPTRN,"Failure matching aw line ({})".format(line)
                        )
                    else: raise
            else: graph_line(t,pids[i],line,dcard['type'])

        # Remove keyword and ability word nodes if empty
        if t.is_leaf(kwid): t.del_node(kwid)
        if t.is_leaf(awid): t.del_node(awid)

    # return the graph tree
    return t

def graph_keyword(t,pid,kw,ktype,param):
    """
    graphs the keyword ability as a new node in t under parent pid
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
                        if m.group(i+1):
                            if k == 'cost':
                                graph_cost(t,t.add_node(kwid,'cost'),m.group(i+1))
                            else: t.add_node(kwid,k,value=m.group(i+1))
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
    # enclosed quotes, variable numbers and variable mana (both followed by a
    # where clause) will mess up graphing
    # find all enclosed quotes and graph them separately under an unrooted node
    # then do the same with variable numbers and variable mana
    line = dd.re_enclosed_quote.sub(lambda m: _enclosed_quote_(t,m),line)
    line = dd.re_variable_val.sub(lambda m: _variable_val_(t,m),line)
    line = dd.re_variable_mana.sub(lambda m: _variable_mana_(t,m),line)

    # Ability lines can be one of
    #  112.3a Spell = instant or sorcery,
    #  112.3b Activated = of the form cost:effect,instructions.
    #  112.3c Triggered = of the form tgr condition, effect. instructions &
    #  112.3d static = none of the above
    # Special cases are
    #  o Saga, (714) which we graph as a line in and of itself namely so that the
    #   highest node is a "saga" vice "static-line"
    #  o delayed trigger (603.7) as these may generally be part of a larger line
    #   (Prized Amalgam), they are not checked for here but in graph_phrase when
    #    phrases are checked
    #  o Leveler (710) have to graphed first because some of the level effects
    #   may contain activated abilities
    if dd.re_lvl_up_check.search(line): graph_lvl_up_phrase(t,pid,line)
    elif _activated_check_(line): graph_activated(t,pid,line)
    elif dd.re_tgr_check.search(line): graph_triggered(t,pid,line)
    elif dd.re_saga_check.search(line): graph_saga(t,pid,line)
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
        # split the line into cost and effect graph each separately
        cost,effect,instr = dd.re_act_line.search(line).groups()
        aaid = t.add_node(pid,'activated-ability')
        graph_cost(t,t.add_node(aaid,'activated-cost'),cost)
        graph_phrase(t,t.add_node(aaid,'activated-effect'),effect)
        if instr: graph_phrase(t,t.add_node(aaid,'activated-instructions'),instr)
        return aaid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'":
            raise lts.LituusException(
                lts.EPTRN,"Not an activated ability ({})".format(line)
            )
        else: raise

def graph_complex_triggered(t,pid,phrase):
    """
    graphs the complex triggered ability in line under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param phrase: the tagged text to graph
    """
    try:
        phrase1,op,phrase2 = dd.re_complex_tgr.search(phrase).groups()
        cid = t.add_node(pid,'conjunction',value=op,itype='phrase')
        graph_phrase(t,cid,phrase1)
        graph_phrase(t,cid,phrase2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise
    return None

def graph_triggered(t,pid,line):
    """
    graphs the activated ability in line under parent pid of tree t
    :param t: the tree
    :param pid: parent of the line
    :param line: the tagged text to graph
    """
    # check for dual conditions, rebuild the line as two separate triggered abilities
    # under a common conjunction node
    try:
        cond1,op,cond2,effect = dd.re_conjoined_tgr_condition_line.search(line).groups()
        cid = t.add_node(pid,'conjunction',value=op,itype='triggered-ability')
        graph_phrase(t,cid,cond1+", "+effect)
        graph_phrase(t,cid,cond2+", "+effect)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # then check for embedded trigger abilities
    try:
        tp,cond,effect = dd.re_embedded_tgr_line.search(line).groups()
        taid = t.add_node(pid,'triggered-ability')
        t.add_node(taid,'triggered-preamble',value=tp)
        graph_phrase(t,t.add_node(taid,'triggered-condition'),cond)
        graph_phrase(t,t.add_node(taid,'triggered-effect'),effect)
        return taid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # run of the mill triggered ability
    try:
        tp,cond,effect,instr = dd.re_tgr_line.search(line).groups()
        taid = t.add_node(pid,'triggered-ability')
        t.add_node(taid,'triggered-preamble',value=tp)

        # before proceeding, check if the condition is a split clause. if it is
        # move the if-cond to the effect
        m = dd.re_split_tgr_condition.search(cond)
        if m:
            cond,ceffect = m.groups()
            effect = ceffect + ", " + effect

        # finish up and return
        graph_phrase(t, t.add_node(taid,'triggered-condition'),cond)
        graph_phrase(t,t.add_node(taid,'triggered-effect'),effect)
        if instr: graph_phrase(t,t.add_node(taid,'triggered-instruction'),instr)
        return taid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

def graph_saga(t,pid,line):
    """
    graphs saga card text
    :param t: the tree
    :param pid: parent id
    :param line: the saga text
    :return: the node id or None
    """
    sid = None
    try:
        # split the line on the chapter symbol and long hyphen
        chapters = [x for x in dd.re_chapter_delim.split(line) if x]
        sid = t.add_node(pid,'saga')
        for j in range(0,len(chapters),2):
            # 714.2c add a chapter line for each individual chapter symbol
            syms,effect = chapters[j],chapters[j+1]
            for sym in syms.split(', '):
                ca = t.add_node(sid,'chapter-line')
                t.add_node(ca,'chapter-symbol',value=sym)
                graph_phrase(t,t.add_node(ca,'chapter-ability'),effect)
        return sid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'" and sid:
            t.del_node(sid)
        else: raise
    return None

def graph_phrase(t,pid,line,i=0):
    """
    Graphs phrases looking first at high-level consructs. Starting again with
    triggered and activated abilities, then replacement effects (614.1,614.2),
    and alternate cost (APC) effects (118.9)
    :param t: the tree
    :param pid: parent of the line
    :param line: the text to graph
    :param i: iteration count to avoid infinite recursion
    """
    # check for activated /triggered ability and complex phrases
    if _activated_check_(line): return graph_activated(t,pid,line)
    elif dd.re_tgr_check.search(line): return graph_triggered(t,pid,line)
    elif dd.re_complex_tgr_check.search(line): graph_complex_triggered(t,pid,line)
    else:
        # TODO: can we make a check for all of these?
        # have to modal first', due to  graph_replacment_effect mistakenly
        #  grabbing portions of modal lines
        if dd.re_modal_check.search(line): return graph_modal_phrase(t,pid,line)

        # replacement effects
        rid = graph_replacement_effect(t,pid,line)
        if rid: return rid

        # alternate casting costs
        rid = graph_apc_phrase(t,pid,line)
        if rid: return rid

        # additional casting costs
        if dd.re_add_cost_check.search(line):
            rid = graph_additional_cost_phrase(t,pid,line)
            if rid: return rid

        # restriction phrases
        rid = graph_restriction_phrase(t,pid,line)
        if rid: return rid

        # exception clauses
        if dd.re_exception_check.search(line):
            rid = graph_exception_phrase(t, pid, line)
            if rid: return rid

        # sequences
        if _sequence_check_(line):
            rid = graph_sequence_phrase(t,pid,line)
            if rid: return rid

        # condition phrases
        rid = graph_conditional_phrase(t,pid,line)
        if rid: return rid

        # optional phrases
        if dd.re_optional_check.search(line):
            rid = graph_optional_phrase(t,pid,line)
            if rid: return rid

        # delayed triggers
        if dd.re_delayed_tgr_check.search(line):
            rid = graph_delayed_tgr(t,pid,line)
            if rid: return rid

        # multiple comjoined action clause phrases
        rid = graph_conjoined_phrase(t,pid,line)
        if rid: return rid

        # Now we have to break down the line in smaller chunks: sentences and
        # then clauses
        ss = [x.strip() + '.' for x in dd.re_sentence.split(line) if x]
        if len(ss) > 1:
            rid = None
            for s in ss: rid = graph_phrase(t,pid,s,i+1)
            return rid # return the last one
        else:
            # if the iteration is less than one we have to run it through again
            # or oracle text with only one sentence will not be graphed
            if i < 1: return graph_phrase(t,pid,line,i+1)
            else: return graph_clause(t,pid,line)
                # split the phrase into clauses (by comma) - we have to run the
                # individual clauses through graph_phrase first NOTE: the clause
                # split removes any 'ands'
                #if mtgl.CMA not in line: return graph_clause(t,pid,line)
                #else:
                #    cid = None
                #    for clause in [x.strip() for x in dd.re_clause.split(line) if x]:
                #        cid = graph_phrase(t,pid,clause)
                #    return cid # return the last one

def graph_clause(t,pid,clause):
    """
    Graphs a clause, a keyword action orientated chunk of words
    :param t: the tree
    :param pid: parent of the line
    :param clause: the text to graph
    """
    # action clauses
    if dd.re_act_clause_check.search(clause):
        rid = graph_action_clause(t,pid,clause)
        if rid: return rid

    # sequencing
    if dd.re_sequence_clause_check.search(clause):
        rid = graph_sequence_clause(t,pid,clause)
        if rid: return rid

    # phase clauses
    if dd.re_phase_clause_check.search(clause):
        rid = graph_phase_clause(t,pid,clause)
        if rid: return rid

    return t.add_node(pid,'clause',tograph=clause)

def graph_replacement_effect(t,pid,line):
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
     614.2 effects that apply to damage from a source (see 609.7) and
     615 effects that prevent damage
    :param t: the tree
    :param pid: the parent id in the tree
    :param line: text to graph
    :return: returns the node id of the replacement effect root if a replacement
     effect was found and graphed
    """
    if dd.re_repl_time_turn_check.search(line):
        try:
            # TODO: this should really be handled first by sequences - need to
            #  write regex to exclude the below phrasing somehow, however, since
            #  the sequence is in two parts (time, phase) we'll handle it here
            #  for now
            time,th,act,phase,ne,instead = dd.re_repl_time_turn.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(t,t.add_node(sid,'seq-condition'),time+" "+phase)
            cid = t.add_node(t.add_node(sid,'seq-effect'),'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='would'),th+" "+act)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            efid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect')
            if instead: t.add_attr(efid,'value','instead')
            graph_phrase(t,efid,ne)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
    elif 'cn<instead>' in line: return graph_repl_instead(t,pid,line)
    elif dd.re_repl_dmg_check.search(line): return graph_repl_dmg(t,pid,line)
    elif 'xa<skip>' in line:
        # 614.1b 'skip' replacements
        rid = None
        try:
            # TODO: should we add a 'who' node for the player?
            ply,may,phase = dd.re_skip.search(line).groups()
            if may:
                rid = t.add_node(pid,'optional-phrase')
                oeid = t.add_node(rid,'opt-effect',value='may')
                rpid = t.add_node(oeid,'replacement-effect')
            else: rpid = t.add_node(pid,'replacement-effect')
            skid = t.add_node(rpid,'repl-effect',value='skip')
            if ply: graph_thing(t,skid,ply)
            graph_phrase(t,skid,phase)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN and rid: t.del_node(rid)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
        return None
    elif dd.re_etb_repl_check.search(line):
        rid = graph_repl_etb1(t,pid,line) # try 614.1c first
        if rid: return rid
        rid = graph_repl_etb2(t,pid,line) # then try 614.1d (continuous)
        if rid: return rid
    elif dd.re_turn_up_check.search(line):
        # 614.1e
        rid = None
        try:
            cond,action = dd.re_turn_up.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(t,t.add_node(sid,'seq-condition',value='as'),cond)
            rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
            rrid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect')
            graph_phrase(t,rrid,action)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
        return None

    return None

def graph_apc_phrase(t,pid,line):
    """
    graphs APC phrases in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of the APC phrase root or None
    """
    # See 118.9 for some phrasing
    # start with 'you may' optional APCs
    if 'cn<may>' in line:
        # [condition]? [player] may [action] rather than pay [cost]
        cid = oid = None
        try:
            # have 1 primary & 2 alternate
            ply = cond = alt = cost = None

            # primary
            m = dd.re_action_apc.search(line)
            if m: cond,ply,alt,cost = m.groups()

            # alternate 1
            if not m:
                m = dd.re_alt_action_apc.search(line)
                if m: cond,cost,ply,alt = m.groups()

            # alternate 2
            if not m: cost,ply,alt = dd.re_rather_than_may_apc.search(line).groups()

            # graph condition if present than the optional apc
            if cond:
                cid = t.add_node(pid,'conditional-phrase')
                graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
                ceid = t.add_node(cid,'condition-effect')
                oid = t.add_node(ceid,'optional-phrase')
            else: oid = t.add_node(pid,'optional-phrase')
            aid = t.add_node(t.add_node(oid,'opt-option',value='may'),'apc')
            graph_thing(t,t.add_node(aid,'apc-player'),ply)
            graph_phrase(t,t.add_node(aid,'apc-apc-cost'),alt)
            graph_phrase(
                t,t.add_node(aid,'apc-original-cost',value='rather-than'),cost
            )
            return cid if cid else oid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN:
                if cid: t.del_node(cid)
                else: t.del_node(oid)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # alternate 3
        oid = None
        try:
            ply,act,alt,cost = dd.re_may_rather_than_apc.search(line).groups()
            oid = t.add_node(pid,'optional-phrase')
            graph_phrase(t,t.add_node(oid,'opt-option',value='may'),ply+" "+act)
            aid = t.add_node(t.add_node(oid,'opt-effect',value='by'),'apc')
            graph_phrase(t,t.add_node(aid,'apc-apc-cost'),alt)
            graph_phrase(t,t.add_node(aid,'apc-orginal-cost'),cost)
            return oid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # if [condition] you may cast ...
        cid = None
        try:
            cond,ply,act,cost = dd.re_cast_apc_nocost.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            oid = t.add_node(t.add_node(cid,'condition-effect'),'optional-phrase')
            aid = t.add_node(t.add_node(oid,'opt-option',value='may'),'apc')
            graph_thing(t,t.add_node(aid,'apc-player'),ply)
            _graph_mana_string_(t,t.add_node(aid,'apc-apc-cost'),'{0}')
            graph_phrase(t,t.add_node(aid,'apc-original-cost',value='without'),cost)
            return cid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN and cid: t.del_node(cid)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    # Mandatory apc
    cid = None
    try:
        ply,cond,alt,cost = dd.re_rather_than_mand_apc.search(line).groups()
        cid = t.add_node(pid,'conditional-phrase')
        graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),ply+" "+cond)
        aid = t.add_node(t.add_node(cid,'condition-effect'),'apc')
        graph_thing(t,t.add_node(aid,'apc-player'),ply)
        graph_phrase(t,t.add_node(aid,'apc-apc-cost'),alt)
        graph_phrase(t,t.add_node(aid,'apc-original-cost'),cost)
        return cid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and cid: t.del_node(cid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

def graph_additional_cost_phrase(t,pid,phrase):
    """
    graphs additional cost phrases
    :param t: the tree
    :param pid: parent id
    :param phrase: phrase to graph
    :return: the node id or None
    """
    aid = None
    try:
        thing,cost = dd.re_add_cost.search(phrase).groups()
        aid = t.add_node(pid,'additional-cost')
        graph_thing(t,t.add_node(aid,'add-cost-for'),thing)
        graph_phrase(t,t.add_node(aid,'add-cost-cost'),cost)
        return aid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(aid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise
    return None

####
## REPLACEMENT CLAUSES
####

## INSTEAD (614.1a)
def graph_repl_instead(t,pid,phrase):
    """
    graphs a 'instead' replacment effect (614.1a) subtree in tree t
    :param t: the tree
    :param pid: the parent id
    :param phrase: the text to graph
    :return: id of the replacement-effect node or None
    """
    # check for 'would' phrasing, 'of' phrasing and 'if' phrasing
    if 'cn<would>' in phrase:
        # if-would-instead variant a (conjunction of woulds)
        try:
            # for this, we graph the two 'woulds' as separate action-clauses
            # under a 'or' conjunction
            t1,w1,t2,w2,instead = dd.re_if_would2_instead.search(phrase).groups()
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='if-would')
            oid = t.add_node(ccid,'conjunction',value='or',itype='action-clause')
            graph_phrase(t,oid,t1+" "+ w1)
            graph_phrase(t,oid,t2+" "+ w2)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            reid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(reid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # if-would-instead variant b and variant c
        try:
            m = dd.re_if_would_instead1.search(phrase)
            if m: th,act,instead = m.groups()
            else: th,act,instead = dd.re_if_would_instead2.search(phrase).groups()
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='if-would')
            graph_phrase(t,ccid,th+" "+act)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            reid = t.add_node(rid, 'repl-new-event')
            graph_phrase(t,t.add_node(reid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # that-would-instead - have to deal with these differently due to
        # how the condition & replacement are separated/identified
        try:
            # get the effect and subphrase and split the subphrase. _twi_split_
            # will throw an exception if the phrase is not valid for this
            th,subphrase = dd.re_that_would_instead.search(phrase).groups()
            act,instead = _twi_split_(subphrase)
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='that-would')
            graph_phrase(t,ccid,th+" "+act)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            reid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(reid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # that-would-instead preceded by sequence
        try:
            seq,th,act,instead = dd.re_seq_that_would_instead.search(phrase).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(t,t.add_node(sid,'seq-condition'),seq)
            seid = t.add_node(sid,'seq_effect')
            cid = t.add_node(seid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='that-would')
            graph_phrase(t,ccid,th+" "+act)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            reid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(reid,'repl-effect',value='instead'),instead)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # test for may instead (optional replacement value)
        try:
            # NOTE: thing1 and thing2 should be the same
            th1,act1,th2,act2 = dd.re_if_may_instead.search(phrase).groups()
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='if-would')
            graph_phrase(t,ccid,th1+" "+act1)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            reid = t.add_node(rid,'repl-new-event')
            graph_phrase(
                t,t.add_node(reid,'repl-effect',value='instead'),th2+" cn<may> "+act2
            )
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    if 'of' in phrase:
        # if-instead-of clause
        try:
            # NOTE: does not have an orginal event
            cond,repl,iof = dd.re_if_instead_of.search(phrase).groups()
            cid = graph_phrase(t,pid,cond)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            rsid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rsid,'repl-effect',value='instead-of'),iof)
            graph_phrase(t,t.add_node(rsid,'repl-effect'),repl)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # test for instead-of-if clause
        try:
            repl,iof,cond = dd.re_instead_of_if.search(phrase).groups()
            cid = graph_phrase(t,pid,cond)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            rrid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rrid,'repl-effect',value='instead-of'),iof)
            graph_phrase(t,t.add_node(rrid,'repl-effect'),repl)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # test for instead-of
        try:
            # TODO: start here
            repl,iof = dd.re_instead_of.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            rrid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rrid,'repl-effect',value='instead-of'),iof)
            graph_phrase(t,t.add_node(rrid,'repl-effect'),repl)
            return rid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    if 'cn<if>' in phrase:
        # test for if-instead
        try:
            cond,instead = dd.re_if_instead.search(phrase).groups()
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            rrid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rrid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # test for if-instead fenced
        try:
            cond,instead = dd.re_if_instead_fence.search(phrase).groups()
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            rrid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rrid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # test for instead-if clause
        try:
            instead,cond = dd.re_instead_if.search(phrase).groups()
            cid = t.add_node(pid,'conditional-effect')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
            rrid = t.add_node(rid,'repl-new-event')
            graph_phrase(t,t.add_node(rrid,'repl-effect',value='instead'),instead)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    return None

## DAMAGE (614) and (615)
def graph_repl_dmg(t,pid,phrase):
    """
    graphs a damage replacement effect
    :param t: the tree
    :param pid: the parent id
    :param phrase: the text to graph
    :return: id of the replacement-effect node or None
    """
    # 614.2 damage prevention from a source if [source] would [old], [new]
    try:
        th,act,ne = dd.re_repl_dmg.search(phrase).groups()
        cid = t.add_node(pid,'conditional-phrase')
        graph_phrase(t,t.add_node(cid,'cond-condition',value='if-would'),th+" "+act)
        rid = t.add_node(t.add_node(cid,'cond-effect'),'replacement-effect')
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect')
        graph_phrase(t,reid,ne)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # and prevention (615)
    # from a target and/or to a source
    sid = rid = None
    try:
        # need to add a sequence node if present, otherwise just a replacement node
        dmg,tgt,seq,exc,src = dd.re_prevent_dmg.search(phrase).groups()
        if seq:
            sid = t.add_node(pid,'sequence-phrase')
            graph_phase_clause(t,t.add_node(sid,'seq-condition'),seq)
            rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        else: rid = t.add_node(pid,'replacement-effect')

        # graph the replacment
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect',value='prevent')
        graph_thing(t,t.add_node(reid,'repl-prevent'),dmg)
        if tgt: graph_thing(t,t.add_node(reid,'repl-target'),tgt)
        if src:
            if not exc: graph_thing(t,t.add_node(reid,'repl-source'),src)
            else: graph_thing(t,t.add_node(reid,'repl-exception',value='by'),src)

        # return the root node of the subtree
        return sid if sid else rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN:
            if sid: t.del_node(sid)
            elif rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check variations
    # target and source are the same
    sid = rid = None
    try:
        # need to add a sequence node if present, otherwise just a replacement node
        dmg,thing,seq = dd.re_prevent_dmg2.search(phrase).groups()
        if seq:
            sid = t.add_node(pid,'sequence-phrase')
            graph_phase_clause(t,t.add_node(sid,'seq-condition'),seq)
            rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        else: rid = t.add_node(pid,'replacement-effect')

        # graph the replacment
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect',value='prevent')
        graph_thing(t,t.add_node(reid,'repl-prevent'),dmg)
        graph_thing(t,t.add_node(reid,'repl-target'),thing)
        graph_thing(t,t.add_node(reid,'repl-source'),thing)

        # return the root node of the subtree
        return sid if sid else rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN:
            if sid: t.del_node(sid)
            elif rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # wording differs
    sid = rid = None
    try:
        # need to add a sequence node if present, otherwise just a replacement node
        dmg,src,tgt,seq = dd.re_prevent_dmg3.search(phrase).groups()
        if seq:
            sid = t.add_node(pid,'sequence-phrase')
            graph_phase_clause(t,t.add_node(sid,'seq-condition'),seq)
            rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        else: rid = t.add_node(pid,'replacement-effect')

        # graph the replacment
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect',value='prevent')
        graph_thing(t,t.add_node(reid,'repl-prevent'),dmg)
        if tgt: graph_thing(t,t.add_node(reid,'repl-target'),tgt)
        graph_thing(t,t.add_node(reid,'repl-source'),src)

        # return the root node of the subtree
        return sid if sid else rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN:
            if sid: t.del_node(sid)
            elif rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check target only
    rid = sid = None
    try:
        # need to add a sequence node if present, otherwise just a replacement node
        dmg,seq,tgt = dd.re_prevent_dmg_tgt.search(phrase).groups()
        if seq:
            sid = t.add_node(pid,'sequence-phrase')
            graph_phase_clause(t,t.add_node(sid,'seq-condition'),seq)
            rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        else: rid = t.add_node(pid,'replacement-effect')

        # graph replacement
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect',value='prevent')
        graph_thing(t,t.add_node(reid,'repl-prevent'),dmg)
        graph_thing(t,t.add_node(reid,'repl-target'),tgt)

        # return sub-tree root
        return sid if sid else rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN:
            if sid: t.del_node(sid)
            elif rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check source only
    sid = None
    try:
        dmg,src,seq = dd.re_prevent_dmg_src.search(phrase).groups()
        sid = t.add_node(pid,'sequence-phrase')
        graph_phase_clause(t,t.add_node(sid,'seq-condition'),seq)
        rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        reid = t.add_node(t.add_node(rid,'repl-new-event'),'repl-effect',value='prevent')
        graph_thing(t,t.add_node(reid,'repl-prevent'),dmg)
        graph_thing(t,t.add_node(reid,'repl-source'),src)
        return sid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and sid: t.del_node(sid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

def graph_repl_etb1(t,pid,phrase):
    """
    graphs ETB replacement clauses from (614.1c)
    :param t: the tree
    :param pid: the parent id
    :param phrase: the text to graph
    :return: node id of the etb subtree or None
    """
    rid = None
    # Permanent ETB with ...
    try:
        thing,cls = dd.re_etb_with.search(phrase).groups()
        rid = t.add_node(pid,'replacement-effect')
        rrid = t.add_node(rid,'repl-new-event')
        graph_thing(t,t.add_node(rrid,'repl-etb-trigger'),thing)
        graph_phrase(t,t.add_node(rid,'repl-etb-effect',value='with'),cls)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # As Permanent ETB ...
    sid = None
    try:
        thing,etb,action = dd.re_as_etb.search(phrase).groups()
        sid = t.add_node(pid,'sequence-phrase')
        scid = t.add_node(sid,'seq-condition',value='as')
        graph_action_clause(t,scid,thing+" "+etb)
        rid = t.add_node(t.add_node(sid,'seq-effect'),'replacement-effect')
        rrid = t.add_node(rid,'repl-new-event')
        graph_thing(t,t.add_node(rrid,'repl-etb-trigger'),thing)
        graph_phrase(t,t.add_node(rid,'repl-etb-effect'),action)
        return sid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and sid: t.del_node(sid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # Permanent ETB as
    oid = rid = None
    try:
        # have to first graph the optional-phrase if present
        ply,thing,cls = dd.re_etb_as.search(phrase).groups()
        if ply:
            oid = t.add_node(pid,'optional-phrase')
            ooid = t.add_node(oid,'opt-option',value='may-have')
            try:
                graph_thing(t,ooid,ply)
            except lts.LituusException as e:
                if e.errno == lts.EPTRN and oid: t.del_node(oid)
                return None
            rid = t.add_node(ooid,'replacment-effect')
        else: rid = t.add_node(pid,'replacement-effect')

        # graph the etb replacement effect
        rrid = t.add_node(rid,'repl-new-event')
        graph_thing(t,t.add_node(rrid,'repl-etb-trigger'),thing)
        # TODO: either have to graph the below as a thing or make graphing
        #  things a part of the graphing flow
        graph_phrase(t,t.add_node(rrid,'repl-etb-effect',value='etb-as'),cls)
        return oid if oid else rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN:
            if oid: t.del_node(oid)
            elif rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # found nothing
    return None

def graph_repl_etb2(t,pid,phrase):
    """
    graphs ETB replacement clauses from (614.1d)
    :param t: the tree
    :param pid: the parent id
    :param phrase: the text to graph
    :return: node id of the etb subtree  or None
    """
    # see if we have a status etb
    rid = None
    try:
        thing,status = dd.re_etb_status.search(phrase).groups()
        rid = t.add_node(pid,'replacement-effect')
        rrid = t.add_node(rid,'repl-new-event')
        graph_thing(t,t.add_node(rrid,'repl-etb-trigger'),thing)
        t.add_node(t.add_node(rrid,'repl-etb-effect'),'status',value=status)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and rid: t.del_node(rid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # continuous etb with an optional effect
    #try:
    #    etb,effect = dd.re_etb_1d.search(phrase).groups()
    #    rid = t.add_node(pid,'replacement-effect')
    #    rrid = t.add_node(rid,'repl-new-event')
    #    graph_action_clause(t,t.add_node(rrid,'repl-etb-trigger'),etb)
    #    if effect: graph_phrase(t,t.add_node(rrid,'repl-etb-effect'),effect)
    #    return rid
    #except AttributeError as e:
    #    if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
    #    else: raise

    return None

####
## MODAL PHRASES
####

def graph_modal_phrase(t,pid,line):
    """
    graphs the modal phrase in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id of the modal subtree or None
    """
    # try 'normal' phrasing first (700.2)
    try:
        # unpack the phrase
        num,opts = dd.re_modal_phrase.search(line).groups()

        # add a modal node and nodes for each of the choices
        mid = t.add_node(pid,'modal')
        cid = t.add_node(mid,'choose',number=num)
        for opt in [x for x in dd.re_opt_delim.split(opts) if x]:
            # have to split the opt on semi-colon to see if there are option
            # instructions
            oid = t.add_node(mid,'option')
            opt = opt.split(" ; ")
            graph_phrase(t,oid,opt[0])
            if len(opt) > 1:
                graph_phrase(t,t.add_node(oid,'option-instruction'),opt[1])
        return mid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # then with instructions (700.2d) on choices
    try:
        # unpack the phrase
        num,instr,opts = dd.re_modal_phrase_instr.search(line).groups()

        # add a modal node and nodes for each of the choices
        mid = t.add_node(pid,'modal')
        cid = t.add_node(mid,'choose',quantity=num)
        graph_phrase(t,t.add_node(mid,'instructions'),instr)
        for opt in [x for x in dd.re_opt_delim.split(opts) if x]:
            graph_phrase(t,t.add_node(mid,'option'),opt)
        return mid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

####
## LEVELER
####

def graph_lvl_up_phrase(t,pid,line):
    """
    graphs the leveler phrase in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id of the leveler subtree or None
    """
    lid = None
    try:
        lid = t.add_node(pid,'leveler')
        for lvl in [x for x in dd.re_opt_delim.split(line) if x]:
            ep1,_,ep2,pt,ab = dd.re_lvl_up_lvl.search(lvl).groups()
            lvid=t.add_node(
                lid,'level',symbol="{}{}".format(ep1,'+' if not ep2 else "-"+ep2)
            )
            if pt: t.add_node(lvid,'lvl-p/t',value=pt)
            if ab: graph_phrase(t,t.add_node(lvid,'lvl-ability'),ab)
        return lid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'":
            if lid: t.del_node(lid)
            return None
        else: raise

####
## SEQUENCE PHRASES
####

def graph_sequence_phrase(t,pid,line):
    """
    determines how to graph the sequence phrase in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id or None
    """
    # before checking for 'normal' sequence phrases, check for a effect as condition
    # phrase (i.e. Trueheart Twins)
    if dd.re_sequence_as_cond_check.search(line):
        try:
            effect,cond = dd.re_sequence_as_cond.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(t,t.add_node(sid,'seq-condition',value='as'),cond)
            graph_phrase(t,t.add_node(sid,'seq-effect'),effect)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    # check for dual sequences. there are not many but they need to be taking care
    # of before the comma is handled incorrectly
    try:
        cond1,cond2 = dd.re_dual_sequence.search(line).groups()
        cid = t.add_node(pid,'conjunction',value='and',itype='sequence-phrase')
        graph_phrase(t,cid,cond1)
        graph_phrase(t,cid,cond2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check for conjoined sequences
    try:
        thing,seq1,op,seq2 = dd.re_conjoined_seq_phrase.search(line).groups()
        cid = t.add_node(pid,'conjunction',value=op,itype='sequence-phrase')
        graph_phrase(t,cid,thing+" "+seq1)
        graph_phrase(t,cid,thing+" "+seq2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check time first, followed by sequence
    if dd.re_time_check_start.search(line) or dd.re_time_check_end.search(line):
        # starts (or ends) wih a turn-structure
        try:
            #m = dd.re_sequence_turn_structure1.search(line)
            #if m: phase,cls = m.groups()
            #else: cls,phase = dd.re_sequence_turn_structure2.search(line).groups()
            phase,cls = dd.re_sequence_turn_structure1.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(t,t.add_node(sid,'seq-condition',value='when'),phase)
            graph_phrase(t,t.add_node(sid,'seq-effect'),cls)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # ends with a sequence
        try:
            # TODO: Fragmentery - should be moved to clause graphing perhaps graph_
            #  phase_clause
            m = dd.re_sequence_time1.search(line)
            if m: seq,phase = m.groups()
            else:
                # need to move the player in front of the phase to make it
                # the same wording as sequence_time1
                seq,phase,ply = dd.re_sequence_time2.search(line).groups()
                phase = ply + " " + phase
            sid = t.add_node(pid,'sequence-phrase')
            cid = t.add_node(sid,'seq-condition',value='when')
            t.add_node(cid,'time',value=seq)
            graph_phrase(t,cid,phase)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
    # TODO: can we elif the below
    if dd.re_sequence_check.search(line):
        # look for "then [phrase]" IOT remove the 'then'
        try:
            phrase = dd.re_then_sequence.search(line).group(1)
            return graph_phrase(t,pid,phrase)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'group'": pass
            else: raise

        try:
            # we're removing the 'then' as the pre and post will be graphed
            # sequentially implying the 'then'
            pre,post,again = dd.re_sequence_then.search(line).groups()
            if pre: graph_phrase(t,pid,pre)
            if not again: return graph_phrase(t,pid,post)
            else:
                sid = t.add_node(pid,'sequence-phrase')
                graph_phrase(t,t.add_node(sid,'seq-effect',value='again'),post)
                return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # then sequence-condition-effect
        try:
            seq,cond,act = dd.re_sequence_cond_effect.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(
                t,t.add_node(sid,'seq-condition',value=seq.replace('_','-')),cond
            )
            graph_phrase(t,t.add_node(sid,'seq-effect'),act)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # and effect-sequence-condition
        try:
            act,seq,cond = dd.re_sequence_effect_cond.search(line).groups()
            sid = t.add_node(pid,'sequence-phrase')
            graph_phrase(
                t,t.add_node(sid,'seq-condition',value=seq.replace('_','-')),cond
            )
            graph_phrase(t,t.add_node(sid,'seq-effect'),act)
            return sid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    return None

####
## CONDITION PHRASES
####

def graph_conditional_phrase(t,pid,line):
    """
    determines how to graph the condition phrase in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id or None
    """
    if "pr<for> xq<each" in line:
        try:
            m = dd.re_for_each_cond_start.search(line)
            if m: xq,cond,act = m.groups()
            else: act,xq,cond = dd.re_for_each_cond_mid.search(line).groups()
            if xq: cond = "xq<{}> ".format(xq) + cond # add quantifier back if present
            ccid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(ccid,'cond-condition',value='for-each'),cond)
            graph_phrase(t,t.add_node(ccid,'cond-effect'),act)
            return ccid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
    elif 'cn<if>' in line:
        # check first for special case if-ply-can|do
        cid = None
        try:
            ply,aw,neg,effect = dd.re_if_ply_cando.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='if')
            dpid = t.add_node(ccid,'decision-point',value=aw + "-not" if neg else aw)
            graph_thing(t,dpid,ply)
            graph_phrase(t,t.add_node(cid,'cond-effect'),effect)
            return cid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN and cid: t.del_node(cid)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # if condition action
        try:
            cond,effect = dd.re_if_cond_act.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            graph_phrase(t,t.add_node(cid,'cond-effect'),effect)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # generic if-would condition
        try:
            th,act = dd.re_if_would.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='if-would')
            graph_phrase(t,ccid,th+" "+act)
            return cid
        except AttributeError as e:
           if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
           else: raise

        # generic if condition
        # TODO: see Nim Abomination, this is a fragmentary condition, it should
        #  be rolled into the larger phrase it is a part of
        try:
            cond = dd.re_if_cond.search(line).group(1)
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'group'": pass
            else: raise

        # if-otherwise NOTE: since this spans sentences, we need to catch it
        #  prior to splitting on periods which means we will grab sentences that
        #  are not part of this sructure
        # TODO: would be a good example of if-then-else
        try:
            pre,cond,act1,act2,post = dd.re_if_otherwise.search(line).groups()
            if pre: graph_phrase(t,pid,pre)
            cid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            graph_phrase(t,t.add_node(cid,'cond-effect'),act1)
            graph_phrase(t,t.add_node(cid,'cond-effect',value='otherwise'),act2)
            if post: graph_phrase(t,pid,post)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # action if condition
        try:
            # one possibility is a "if able", handle these differently
            act,cond = dd.re_act_if_cond.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            if cond == 'able':
                # TODO: what card is this
                t.add_node(cid,'cond-condition',value='if-able')
            else:
                graph_phrase(t,t.add_node(cid,'cond-condition',value='if'),cond)
            graph_phrase(t,t.add_node(cid,'cond-effect'),act)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
    elif 'cn<unless>' in line:
        # action-unless
        try:
            # we need to check for "can not" and not graph if found
            act,cond = dd.re_action_unless.search(line).groups()
            if "xa<can> cn<not>" in act: return None
            ccid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(ccid,'cond-condition',value='unless'),cond)
            graph_phrase(t,t.add_node(ccid,'cond-effect'),act)
            return ccid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
    elif 'cn<otherwise' in line:
        try:
            # TODO: see Primal Empathy - these should really be part of a larger
            #  conditional-phrase in the preceding line
            oth = dd.re_otherwise.search(line).group(1)
            ccid = t.add_node(pid,'conditional-phrase')
            graph_phrase(t,t.add_node(ccid,'cond-effect',value='otherwise'),oth)
            return ccid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'group'": pass
            else: raise
    elif "cn<could>" in line or "cn<would>" in line:
        # generic would|could conditions w/out effects
        try:
            th,xq,abw,neg,act = dd.re_gen_cond.search(line).groups()
            cid = t.add_node(pid,'conditional-phrase')
            lbl = "that-" + abw if xq else abw
            if neg: lbl += "-not"
            graph_phrase(t,t.add_node(cid,'cond-condition',value=lbl),th+" "+act)
            return cid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    return None

def graph_restriction_phrase(t,pid,phrase):
    """
    graphs restriction phases
    :param t: the tree
    :param pid: the parent id
    :param phrase: text to graph
    :return: node id or None on failure
    """
    # "but"-restrictions and "can/do"-restrictions will not be part of a conjunctive
    # restriction, get them out of theway first
    # graph but restrictions first (only 12 at time of IKO)
    if 'but' in phrase:
        try:
            act,wd,rstr = dd.re_restriction_but.search(phrase).groups()
            rsid = t.add_node(pid,'restriction-phrase')
            graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            graph_phrase(t,t.add_node(rsid,'rstr-restriction',value='but-'+wd),rstr)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    # can/do not
    if dd.re_restriction_cando_check.search(phrase):
        # can/dos with unless
        try:
            th,rw,act,cond = dd.re_restriction_cando_unless.search(phrase).groups()
            rsid = t.add_node(pid,'restriction-phrase')
            rrid = t.add_node(rsid,'rstr-restriction',value=rw+'-not')
            graph_phrase(t,rrid,th+" "+act)
            graph_phrase(t,t.add_node(rsid,'rstr-exception',value='unless'),cond)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # can/dos with "that would"
        try:
            # TODO: Don't like the graphing of this
            th,act1,rw,act2 = dd.re_restriction_would_cando.search(phrase).groups()
            rsid = t.add_node(pid,'restriction-phrase')
            rrid = t.add_node(rsid,'rstr-restriction',value=rw+'-not')
            cid = t.add_node(rrid,'conditional-phrase')
            ccid = t.add_node(cid,'cond-condition',value='that-would')
            graph_phrase(t,ccid,th+" "+act1)
            graph_phrase(t,t.add_node(rrid,'rstr-effect'),act2)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    # now check conjunctions of restrictions
    try:
        act,rstr1,op,rstr2 = dd.re_conjoined_restriction_only.search(phrase).groups()
        rsid = t.add_node(pid,'restriction-phrase')
        graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
        cid = t.add_node(rsid,'conjunction',value=op,itype='rstr-restriction')
        graph_restriction_phrase(t,cid,rstr1)
        graph_restriction_phrase(t,cid,rstr2)
        return rsid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # The below may be part of a recursive call due to a conjunction. Check the
    # parent type first. If conjunction, only the restriction will be present,
    # do not add a new 'only' node, merely graphing the restriciton
    # only-ifs
    if 'cn<only_if>' in phrase:
        try:
            act,cond = dd.re_only_if.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction': rsid = pid
            else: rsid = t.add_node(pid,'restriction-phrase')
            if act: graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            graph_phrase(t,t.add_node(rsid,'rstr-restriction',value='only-if'),cond)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    if 'cn<only>' in phrase:
        # may-only (will not be part of a conjunction)
        try:
            th,act,rstr = dd.re_restriction_may_only.search(phrase).groups()
            rsid = t.add_node(pid,'restriction-phrase')
            graph_phrase(t,t.add_node(rsid,'rstr-effect',value='may'),th+" "+act)
            graph_phrase(t,t.add_node(rsid,'rstr-restriction',value='on;y'),rstr)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # only - any time player could cast a sorcery
        try:
            act,rstr = dd.re_restriction_anytime.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction': rsid = pid
            else: rsid = t.add_node(pid,'restriction-phrase')
            if act: graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            graph_phrase(t,t.add_node(rsid,'rstr-restriction',value='only-when'),rstr)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # only-[sequence]
        try:
            act,seq,phase = dd.re_restriction_phase.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction': rsid = pid
            else: rsid = t.add_node(pid,'restriction-phrase')
            if act: graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            rrid = t.add_node(rsid,'rstr-restriction',value='only')
            scid = t.add_node(
                t.add_node(rrid,'sequence-phrase'),'seq-condition',value='during'
            )
            graph_phrase(t,scid,phase)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # only-number per turn
        try:
            act,limit,phase = dd.re_restriction_number.search(phrase).groups()
            if mtgt.node_type(pid) == 'item': rsid = pid
            else: rsid = t.add_node(pid,'restriction-phrase')
            if act: graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            rrid=t.add_node(rsid,'rstr-restriction',value='times')
            t.add_node(rrid,'rstr-limit',value=limit)
            if phase: graph_phase_clause(t,rrid,phase)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

        # only - all else
        try:
            act,rstr = dd.re_restriction_only.search(phrase).groups()
            # NOTE: these should not be part of a conjunction but just in case
            if mtgt.node_type(pid) == 'conjunction': rsid = pid
            else: rsid = t.add_node(pid,'restriction-phrase')
            graph_phrase(t,t.add_node(rsid,'rstr-effect'),act)
            graph_phrase(t,t.add_node(rsid,'rstr-restriction',value='only'),rstr)
            return rsid
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise

    return None

####
## OPTIONAL PHRASES
####

def graph_optional_phrase(t,pid,phrase):
    """
    determines how to graph the optional phrase in line
    :param t: the tree
    :param pid: the parent id
    :param phrase: text to graph
    :return: node id or None
    """
    # conjoined optionals
    try:
        opt1,op,opt2 = dd.re_conjoined_optional_phrase.search(phrase).groups()
        cid = t.add_node(pid,'conjunction-phrase',value=op,itype='phrase')
        graph_phrase(t,cid,opt1)
        graph_phrase(t,cid,opt2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise


    # may as-though
    try:
        ply,opt,effect = dd.re_may_as_though.search(phrase).groups()
        opid = t.add_node(pid,'optional-phrase')
        graph_phrase(t,t.add_node(opid,'opt-option',value='may'),ply+" "+opt)
        graph_phrase(t,t.add_node(opid,'opt-effect',value='as-though'),effect)
        return opid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # may have and singleton may
    try:
        ply,opt = dd.re_player_may.search(phrase).groups()
        opid = t.add_node(pid,'optional-phrase')
        graph_phrase(t,t.add_node(opid,'opt-option',value='may'),ply+" "+opt)
        return opid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

####
## EXCEPTION PHRASES
####

def graph_exception_phrase(t,pid,phrase):
    """
    graphs phrase containing an exception
    :param t: the tree
    :param pid: the parent id
    :param phrase: text to graph
    :return: node id or None
    """
    # except (exclusion)
    try:
        act,excp = dd.re_exclusion_phrase.search(phrase).groups()
        eid = t.add_node(pid,'exception-phrase')
        if act: graph_phrase(t,t.add_node(eid,'excp-effect'),act)
        graph_phrase(t,t.add_node(eid,'excp-exclusion',value='except-for'),excp)
        return eid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'":
            pass
        else:
            raise

    # except (additional abilities)
    try:
        act,excp = dd.re_exception_phrase.search(phrase).groups()
        eid = t.add_node(pid,'exception-phrase')
        graph_phrase(t,t.add_node(eid,'excp-effect'),act)
        graph_phrase(t,t.add_node(eid,'excp-exception',value='except'),excp)
        return eid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

####
## DELAYED TRIGGERED ABILITIES
####

def graph_delayed_tgr(t,pid,clause):
    """
    graphs the delayed trigger in line
    :param t: the tree
    :param pid: the parent id
    :param clause: text to graph
    :return: node id or None on failure
    """
    try:
        effect,tp,cond = dd.re_delayed_tgr_clause.search(clause).groups()
        dtid = t.add_node(pid,'delayed-trigger-ability')
        t.add_node(dtid,'del-triggered-preamble',value=tp)
        graph_phrase(t,t.add_node(dtid,'del-triggered-condition'),cond)
        graph_phrase(t,t.add_node(dtid,'del-triggered-effect'),effect)
        return dtid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise
    return None

####
## ACTION PHRASE
####

def graph_conjoined_phrase(t,pid,line):
    """
    graphs the conjunctipn of (2 or more) phrases in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id or None on failure
    """
    # 3 or more phrases (generally action clauses)
    try:
        # try implied first
        th = ac1 = ac2 = ac3 = ac4 = op = None
        m = dd.re_conjoined_act_phrase_implied.search(line)
        if m: ac1,ac2,ac3,op,ac4 = m.groups()

        # if not check common subject
        if not m:
            m = dd.re_conjoined_act_phrase_common.search(line)
            if m: th,ac1,ac2,ac3,op,ac4 = m.groups()

        # and if not check default
        if not m:
            m = dd.re_conjoined_act_phrase_distinct.search(line)
            ac1,ac2,ac3,op,ac4 = m.groups()

        # add the conjunction and children
        cid = t.add_node(pid,'conjunction',value=op,itype='phrase')
        if ac1: graph_phrase(t,cid,th+" "+ac1 if th else ac1)
        graph_phrase(t,cid,th+" "+ac2 if th else ac2)
        graph_phrase(t,cid,th+" "+ac3 if th else ac3)
        graph_phrase(t,cid,th+" "+ac4 if th else ac4)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check for bi-conjunction
    try:
        phrase1,phrase2 = dd.re_conjoined_phrase_dual.search(line).groups()
        cid = t.add_node(pid,'conjunction',value='and',itype='phrase')
        graph_phrase(t,cid,phrase1)
        graph_phrase(t,cid,phrase2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

####
## CLAUSES, TOKENS
####

def graph_cost(t,pid,cls):
    """
    graphs the cost(s) in phrase
    :param t: the tree
    :param pid: parent id to graph under
    :param cls: the cost clause
    :return: cost node id
    """
    # a cost is one or more comma separated subcosts
    for sc in [x.strip() for x in dd.re_clause.split(cls) if x]: _subcost_(t,pid,sc)

def graph_action_clause(t,pid,phrase):
    """
    graphs action clause
    :param t: the tree
    :param pid: parent id
    :param phrase: action clause with possible qualifying clause(s)
    :return: the action node id
    """
    return graph_action_clause_ex(t,pid,phrase)

def graph_action_clause_ex(t,pid,phrase):
    """
    graphs the keyword or lituus action clause in phrase under pid
    :param t: the tree
    :param pid: parent id
    :param phrase: the text to graph
    :return: the node id
    """
    # check for 'tap or untap' phrases as they need to be handled differently before
    # processing 'normal' action clauses
    aid = None
    try:
        ply, _, obj = dd.re_tq_action_clause.search(phrase).groups()
        aid = t.add_node(pid,'action-clause')
        graph_thing(t,t.add_node(aid,'act-subject'),ply)
        apid = t.add_node(t.add_node(aid,'act-predicate'),"ka<tap∨untap>")
        try:  # TODO: this is just a hack for now
            graph_thing(t,t.add_node(aid,'act-object'),obj)
        except lts.LituusException as e:
            graph_phrase(t,t.add_node(aid,'act-parameters'),apid,obj)
        return aid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and aid: t.del_node(aid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'":
            pass
        else:
            raise

    # subjects are specified for both actions
    try:
        act1,op,act2 = dd.re_conjoined_act_clause_unique.search(phrase).groups()
        cid = t.add_node(pid,'conjunction',value=op,itype='action-clause')
        graph_action_clause(t,cid,act1)  # TODO: graph as action_clause or phrase
        graph_action_clause(t,cid,act2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # then check for those with a common thing
    try:
        th,ac1,op,ac2 = dd.re_conjoined_act_clause_common.search(phrase).groups()
        if th:
            ac1 = th + " " + ac1
            ac2 = th + " " + ac2
        cid = t.add_node(pid,'conjunction',value=op,itype="action-clause")
        graph_action_clause(t,cid,ac1) # TODO: graph as action_clause or phrase
        graph_action_clause(t,cid,ac2)
        return cid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    aid = None
    try:
        # unpack the clause
        thing,abw,cnd,aw,ap = dd.re_action_clause.search(phrase).groups()

        if abw:
            # check for a restricted action i.e. "can not", "do not"
            aid = t.add_node(pid,'restriction-phrase')
            reid = t.add_node(
                aid,'restriction-effect',value=abw+"-"+cnd if cnd else abw
            )
            phrase = thing + " " + aw if thing else aw
            if ap: phrase = phrase + " " + ap
            graph_action_clause(t,reid,phrase)
        else:
            # TODO: we are only seeing one card (Escaped Shapeshifter) with a
            #  conditional precededing the action word that is not also preceded
            #  by 'can' or 'do'
            if cnd: assert(cnd == 'not')
            aid = t.add_node(pid,'action-clause')
            if thing: graph_thing(t,t.add_node(aid,'act-subject'),thing)
            apid = t.add_node(aid,'act-predicate')
            awid,val = _graph_action_word_(t,apid,aw if not cnd else 'not '+aw)
            if ap: graph_action_param(t,aid,val,ap)
        return aid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and aid: t.del_node(aid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # try player own/control
    aid = None
    try:
        ply,poss,clause = dd.re_action_ply_poss.search(phrase).groups()
        aid = t.add_node(pid,'action-clause')
        graph_thing(t,t.add_node(aid,'act-subject'),ply)
        apid = t.add_node(aid,'act-predicate')
        t.add_node(t.add_node(apid,'lituus-action'),poss)
        try: # TODO: this is just a hack for now
            graph_thing(t,t.add_node(aid,'act-object'),clause)
        except lts.LituusException as e:
            graph_phrase(t,t.add_node(aid,'act-parameters'),apid,clause)
        return aid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and aid: t.del_node(aid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

def graph_thing(t,pid,clause):
    """
    Graphs the thing under node pid
    :param t: the tree
    :param pid: the parent id
    :param clause: the clause
    :return: the thing node id
    """
    # first look at reified attributes
    if dd.re_reified_attribute.search(clause):
        rid = graph_attribute_clause(t,pid,clause)
        if rid: return rid

    # could have a qtz phrase, a qst phrase or a possesive phrase - check all
    # check cards in zones
    eid = None
    try:
        xq,loc,num,thing,prep,zn,amp = dd.re_qtz.search(clause).groups()
        eid = t.add_node(pid,'thing')
        if xq: t.add_node(eid,'quantifier',value=xq)
        if loc: t.add_node(eid,'which',value=loc) # TODO: don't like label
        if num: t.add_node(eid,'quantity',value=num)
        _graph_object_(t,eid,thing)
        prid = t.add_node(eid,prep)
        zid = graph_thing(t,prid,zn)
        if amp: t.add_node(zid,'how',value=amp)
        return eid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and eid: t.del_node(eid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # check for possessives which may be preceded by a quantifier
    try:
        # unpack the things then untag each thing
        xq,_,thing1,thing2 = dd.re_consecutive_things.search(clause).groups()
        tid1,val1,attr1 = mtgltag.untag(thing1)
        tid2,val2,attr2 = mtgltag.untag(thing2)

        # only continue if an "'s" or "s'"possesive suffix exists
        if 'suffix' in attr1 and attr1['suffix'] in ["'s","s'"]:
            # remove the suffix the first thing and retag (if it is a plural
            # possessive, add the plural back)
            if attr1['suffix'] == "s'": attr1['suffix'] = "s"
            else: del attr1['suffix']
            thing1 = mtgltag.retag(tid1,val1,attr1)

            # the second thing is the primary node (re-add quanitifier if present)
            if xq: thing2 = "xq<{}> {}".format(xq,thing2)
            eid = graph_thing(t,pid,thing2)

            # the label of the intermeditary node depends on the two things
            lbl = 'whose' if tid1 == 'xp' and tid2 == 'zn' else 'of'

            # add the 1st thing under the intermeditary node of the 2nd thing
            graph_thing(t,t.add_node(t.children(eid)[-1],lbl),thing1)
            return eid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    rid = None # subroot parent node id
    try:
        # first unpack the thing clauses which will determine how to proceed
        # NOTE: have only seen one or two things but just in case we check for
        # a conjunction of upto three
        thing1,thing2,op,thing3 = dd.re_thing_clause.search(clause).groups()
        if (thing1 or thing2) and not op:
            # TODO: this is a hack for now, re_thing_clause needs to be redone
            raise lts.LituusException(lts.EPTRN, "Not a thing {}".format(clause))

        # we will always need thing clause 3 unpacked
        n1 = xq1 = st1 = th1 = dh1 = None
        n2 = xq2 = st2 = th2 = dh2 = None
        n3,xq3,st3,th3,dh3 = dd.re_qst2.search(thing3).groups()

        # if there is a thing1 there will be a thing2 likewise, if there is no
        # thing2 there is not thing1
        if thing2:
            # unpack thing2 and if thing1 is present, unpack it too
            n2,xq2,st2,th2,dh2 = dd.re_qst2.search(thing2).groups()
            if thing1: n1,xq1,st1,th1,dh1 = dd.re_qst2.search(thing1).groups()

            # determien if we will use common qualifying terms or not
            if n3 or xq3 or st3:
                # if there are two (or more) things and the last thing has
                # qualifying terms (i.e. a quantifier) we need to create a
                # conjunction of thing clauses where each thing clause has their
                # own qualifying tmers
                rid = t.add_node(pid,'conjunction',value=op,itype='thing-clause')
                if thing1:
                    tcid1 = t.add_node(rid,'thing-clause') # thing clause 1
                    if n1: t.add_node(tcid1,'number',value=n1)
                    if xq1: t.add_node(tcid1,'quantifier',value=xq1)
                    if st1: t.add_node(tcid1,'status',value=st1)
                    thid1 = _graph_object_(t,t.add_node(tcid1,'thing'),th1)
                    if dh1: t.add_node(thid1,'dump-huff', tograph=dh1)
                tcid2 = t.add_node(rid,'thing-clause') # thing clause 2
                if n2: t.add_node(tcid2,'number',value=n2)
                if xq2: t.add_node(tcid2,'quantifier',value=xq2)
                if st2: t.add_node(tcid2,'status',value=st2)
                thid2 =_graph_object_(t,t.add_node(tcid2,'thing'),th2)
                if dh2: t.add_node(thid2,'dump-huff',tograph=dh2)
                tcid3 = t.add_node(rid,'thing-clause') # thing clause 3
                if n3: t.add_node(tcid3,'number',value=n3)
                if xq3: t.add_node(tcid3,'quantifier',value=xq3)
                if st3: t.add_node(tcid3,'status',value=st3)
                thid3 = _graph_object_(t,t.add_node(tcid3,'thing'),th3)
                if dh3: t.add_node(thid3,'dump-huff',tograph=dh3)
            else:
                # if there is only one set of qualifying terms they apply to the
                # conjunction as a whole, create as single thing-clause (adding
                # the qualifying terms) then create a conjunction of things
                rid = t.add_node(rid,'thing-clause')
                if n2: t.add_node(rid,'number',value=n2)
                if xq2: t.add_node(rid,'quantifier',value=xq2)
                if st2: t.add_node(rid,'status',value=st2)
                cid = t.add_node(rid,'conjunction',value=op,itype='thing')
                if thing1:
                    thid1 =  _graph_object_(t,t.add_node(cid,'thing'),th1)
                    if dh1: t.add_node(thid1,'dump-huff',tograph=dh1)
                thid2 = _graph_object_(t,t.add_node(cid,'thing'),th2)
                if dh2: t.add_node(thid2,'dump-huff',tograph=dh2)
                thid3 = _graph_object_(t,t.add_node(cid,'thing'),th3)
                if dh3: t.add_node(thid3,'dump-huff',tograph=dh3)
        else:
            # only one thing clause
            rid = t.add_node(pid,'thing-clause')
            if n3: t.add_node(rid,'number',value=n3)
            if xq3: t.add_node(rid,'quantifier',value=xq3)
            if st3: t.add_node(rid,'status',value=st3)
            thid3 = _graph_object_(t,t.add_node(rid,'thing'),th3)
            if dh3: t.add_node(thid3,'dump-huff',tograph=dh3)
        return rid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    raise lts.LituusException(lts.EPTRN,"Not a thing {}".format(clause))

def graph_attribute_clause(t,pid,clause):
    """
    graphs an attribute clause
    :param t: the tree
    :param pid: parent id
    :param clause: the attribute clause to graph
    :return: node id of the attribute subtree or None
    """
    if dd.re_attr_clause_check.search(clause):
        atid = None
        try:
            # unpack the components & create the attribute node
            m = dd.re_things_attr.search(clause)
            if m: thing,attr1,op,attr2 = m.groups()
            else: attr1,op,attr2,thing = dd.re_attr_of_thing.search(clause).groups()
            atid = t.add_node(pid,'attribute')

            # add the attribute (add conjunction if necessary) & the thing
            if attr1:
                cid = t.add_node(atid,'conjunction',value=op,itype='attr-name')
                t.add_node(cid,'item',value=attr1)
                t.add_node(cid,'item',value=attr2)
            else: t.add_node(atid,'attr-name',value=attr2)
            graph_thing(t,t.add_node(atid,'attr-of'),thing)
            return atid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN and atid: t.del_node(atid)
        except AttributeError as e:
            if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
            else: raise
        return graph_phrase(t,t.add_node(pid,'attribute'),clause)
    return None

# TODO: is this really necessary?
def graph_duration(t,pid,clause):
    """
    graphs a duration clause
    :param t: the tree
    :param pid: parent id
    :param clause: the duration clause to graph
    :return:  node id of the duration subtree or None
    """
    # a simple phrasing [quantifier] [turn-structure] defines a 'when' clause
    # i.e. next turn, each turn, this turn etc
    try:
        phase = dd.re_quant_duration_clause.search(clause).group(1)
        wid = t.add_node(pid,'when')
        graph_phase_clause(t,wid,phase)
        return wid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'group'": pass
        else: raise

    return None

def graph_action_param(t,pid,aw,param):
    """
    graphs the action consisting of action word aw and its parameters
    :param t: the tree
    :param pid: parent id to graph under
    :param aw: the action word
    :param param: paremeters
    :return: the graphed action node or None
    """
    # starting with mtg defined keyword actions
    # The following do not have parameters (proliferate,populate,investigate,
    #  explore)
    # The following are not considered (Planeswalk, Set in Motion, Abandon,Assemble)
    if aw == 'activate': return _graph_ap_thing_(t,pid,param) # 701.2
    elif aw == 'attach': return _graph_ap_attach_(t,pid,param) # 701.3
    elif aw == 'unattach': return _graph_ap_thing_(t,pid,param) # 701.3d
    elif aw == 'cast': return _graph_ap_thing_(t,pid,param) # 701.4
    elif aw == 'counter': return _graph_ap_thing_(t,pid,param) # 701.5
    elif aw == 'create': return _graph_ap_thing_(t,pid,param)  # 701.6
    elif aw == 'destroy': return _graph_ap_thing_(t,pid,param) # 701.7
    elif aw == 'discard': return _graph_ap_thing_(t,pid,param) # 701.8
    elif aw == 'double': return _graph_ap_double_(t,pid,param) # 701.9
    elif aw == 'exchange': return _graph_ap_exchange_(t,pid,param) # 701.10
    elif aw == 'exile': return _graph_ap_thing_(t,pid,param) # 701.11
    elif aw == 'fight': return _graph_ap_fight_(t,pid,param) # 701.12
    elif aw == 'mill': return _graph_ap_n_(t,pid,param) # 701.13
    elif aw == 'play': return _graph_ap_thing_(t,pid,param) # 701.14
    elif aw == 'regenerate': return _graph_ap_thing_(t,pid,param) # 701.15
    elif aw == 'reveal': return _graph_ap_thing_(t,pid,param) # 701.16
    elif aw == 'sacrifice': return _graph_ap_thing_(t,pid,param) # 701.17
    elif aw == 'scry': return _graph_ap_n_(t,pid,param) # 701.18
    elif aw == 'search': return _graph_ap_search_(t,pid,param) # 701.19
    elif aw == 'shuffle': return _graph_ap_thing_(t,pid,param) # 701.20
    elif aw == 'tap' or aw == 'untap': return _graph_ap_tap_(t,pid,param) # 701.21
    elif aw == 'fateseal': return _graph_ap_n_(t,pid,param)  # 701.22
    elif aw == 'clash': return _graph_ap_clash_(t,pid,param) # 701.23
    elif aw == 'transform': return _graph_ap_thing_(t,pid,param) # 701.28
    elif aw == 'detain': return _graph_ap_thing_(t,pid,param) # 701.29
    elif aw == 'monstrosity': return _graph_ap_n_(t,pid,param)  # 701.31
    elif aw == 'vote': return _graph_ap_vote_(t,pid,param) # 701.32
    elif aw == 'bolster': return _graph_ap_n_(t,pid,param)  # 701.33
    elif aw == 'manifest': return _graph_ap_thing_(t,pid,param) # 701.34
    elif aw == 'support': return _graph_ap_n_(t,pid,param)  # 701.35
    elif aw == 'meld': return _graph_ap_meld_(t,pid,param) # 701.37
    elif aw == 'goad': return _graph_ap_thing_(t,pid,param) # 701.38
    elif aw == 'exert': return _graph_ap_thing_(t,pid,param)  # 701.39
    elif aw == 'surveil': return _graph_ap_n_(t,pid,param)  # 701.42
    elif aw == 'adapt': return _graph_ap_n_(t,pid,param)  # 701.43
    elif aw == 'amass': return _graph_ap_n_(t,pid,param)  # 701.44

    # then lituus actions
    if aw == 'add': return _graph_ap_add_(t,pid,param)
    elif aw == 'assign': pass  # TODO
    elif aw == 'attack': pass  # TODO
    elif aw == 'become': pass  # TODO
    elif aw == 'begin': pass  # TODO
    elif aw == 'bid': pass  # TODO
    elif aw == 'block': pass  # TODO
    elif aw == 'can' or aw =='do': print(t._name,pid,aw,param) #pass  # TODO
    elif aw == 'cause': pass # TODO
    elif aw == 'change': pass  # TODO
    elif aw == 'choose': pass  # TODO
    elif aw == 'copy': pass  # TODO
    elif aw == 'cost': pass  # TODO
    elif aw == 'count': pass  # TODO
    elif aw == 'deal': pass  # TODO
    elif aw == 'declare': pass  # TODO
    elif aw == 'defend': pass  # TODO
    elif aw == 'die': pass  # TODO
    elif aw == 'distribute': pass  # TODO
    elif aw == 'divide': pass  # TODO
    elif aw == 'do': pass  # TODO
    elif aw == 'draw': pass  # TODO
    elif aw == 'flip': pass  # TODO
    elif aw == 'gain': pass  # TODO
    elif aw == 'get':  pass  # TODO
    elif aw == 'have': pass  # TODO
    elif aw == 'leave': pass  # TODO
    elif aw == 'look': pass  # TODO
    elif aw == 'move': pass  # TODO
    elif aw == 'named': pass  # TODO
    elif aw == 'note': pass  # TODO
    elif aw == 'pay': pass  # TODO
    elif aw == 'phase': pass  # TODO
    elif aw == 'prevent': pass  # TODO
    elif aw == 'produce': pass  # TODO
    elif aw == 'put': pass  # TODO
    elif aw == 'reduce': pass  # TODO
    elif aw == 'remain': pass  # TODO
    elif aw == 'remove': pass  # TODO
    elif aw == 'reorder': pass  # TODO
    elif aw == 'repeat': pass  # TODO
    elif aw == 'reselect': pass  # TODO
    elif aw == 'resolve': pass  # TODO
    elif aw == 'return': pass  # TODO
    elif aw == 'round': pass  # TODO
    elif aw == 'select': pass  # TODO
    elif aw == 'separate': pass  # TODO
    elif aw == 'share': pass  # TODO
    elif aw == 'skip':  pass  # TODO
    elif aw == 'spend': pass  # TODO
    elif aw == 'switch': pass  # TODO
    elif aw == 'take': pass  # TODO
    elif aw == 'tie': pass  # TODO
    elif aw == 'trigger': pass  # TODO
    elif aw == 'turn': pass  # TODO
    elif aw == 'unblock': pass  # TODO
    elif aw == 'unspend': pass  # TODO
    elif aw == 'win' or aw == 'lose': return _graph_ap_thing_(t,pid,param)

    # TODO: have to add keywords
    if aw == 'cycle': return _graph_ap_thing_(t,pid,param)

    # nothing found TODO: after debugging, return None
    return t.add_node(pid,'act-parameter',tograph=param)

def graph_sequence_clause(t,pid,clause):
    """
    graphs standalone sequence clauses
    :param t: the tree
    :param pid: parent id
    :param clause: text to graph
    :return: node id or None
    """
    try:
        sq,cls = dd.re_sequence_clause.search(clause).groups()
        sid = t.add_node(pid,'sequence',value=sq)
        if sq == 'during': graph_phrase(t,sid,cls)
        else: graph_clause(t,sid,cls)
        return sid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise
    return None

def graph_phase_clause(t,pid,clause):
    """
    Graphs a standalone phase under node pid
    :param t: the tree
    :param pid: the parent id
    :param clause: the clause
    :return: the phase node id
    """
    # checking for three possibilities
    #  a) [number] time(s) [phase] i.e. 1 time this turm
    #  b) [time] [phase] i.e. the next time this turn
    #  c) [thing]'s [phase] i.e. target player's next turn
    try:
        n,_,xq,phase = dd.re_num_times_phase.search(clause).groups()
        tsid = t.add_node(pid,'turn-structure')
        t.add_node(tsid,'limit',value=n) # TODO: don't like limit being placed here
        if xq: t.add_node(tsid,'quantifier',value=xq)
        t.add_node(tsid,'phase',value=phase)
        return tsid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    try:
        xq1,time,xq2,phase = dd.re_time_phase_clause.search(clause).groups()
        tsid = t.add_node(pid,'turn-structure')
        t.add_node(tsid,'time',value=xq1) # TODO: this needs to be at pid
        if xq2: t.add_node(tsid,'quantifier',value=xq2)
        t.add_node(tsid,'phase',value=phase)
        return tsid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    try:
        thing,xq,phase = dd.re_thing_phase_clause.search(clause).groups()
        tsid = t.add_node(pid,'turn-structure')
        if xq: t.add_node(tsid,'quantifier',value=xq)
        phid = t.add_node(tsid,'phase',value=phase)
        try:
            if thing:
                # TODO: Crystalline Resonance
                graph_thing(t,t.add_node(phid,'whose'),thing)
        except lts.LituusException as e:
            if e.errno == lts.EPTRN:
                t.add_node(phid,'dump-huff',tograph=thing)
        return tsid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

####
## PRIVATE FUNCTIONS
####

def _graph_object_(t,pid,obj):
    """
     graphs an object under pid
    :param t: the tree
    :param pid: the parent id
    :param obj: the object to untag and graph
    :return: ?
    """
    # untag the obj
    tid,val,attr = mtgltag.untag(obj)
    oid = None

    # if we have an mtg object, label the object with the tag value (i.e. card)
    # and add any references as attributes to the node. If we have a non-mtg object
    # i.e. player
    # TODO: what to do about plural suffixes
    if tid == 'ob':
        oid = t.add_node(pid,val)
        if 'ref' in attr:
            t.add_attr(oid,'ref-id',attr['ref'])
            del attr['ref']
    else:
        oid = t.add_node(pid,dd.TID[tid],value=val)

    # modify any plural suffixes
    if 'suffix' in attr and attr['suffix'] == 's':
        del attr['suffix']
        t.add_attr(oid,'plurality',1)

    # remove possessive suffixes
    if 'suffix' in attr and attr['suffix'] == "'s": del attr['suffix']

    # add any (remaining) attributes as subnodes
    for k in attr: t.add_node(oid,k,value=attr[k])
    return oid

def _enclosed_quote_(t,m):
    """
    graphs the contents of an enclosed quote (in m) under an unrooted node and
    returns a tag nd<node-id> to sub in for the quoted text
    :param t: the tree
    :param m: regex match object
    :return: the tagged node-id of the graphed contents
    """
    # create a rootless node to graph the text under (stripping the quotation
    # marks) and return the tagged node-id
    eqid = t.add_ur_node('enclosed-quote')
    graph_line(t,eqid,m.group()[1:-1])
    return "nd<{} num={}>".format(*eqid.split(':'))

def _variable_val_(t,m):
    """
    graphs the value of a variable in an unrooted node returning the node-id inside
    the variable tag
    :param t: the tree
    :param m: regex Match object
    :return: retagged variable
    """
    # untag the tag with a variable, need the attribute dict
    tid,val,attr = mtgltag.untag(m.group(1))

    # graph the variable instantiation
    vid = t.add_ur_node('variable-value')
    graph_phrase(t,vid,m.group(2))

    # add the variable node to the tag & return it
    attr['node-num'] = vid.split(':')[1]
    return mtgltag.retag(tid,val,attr)

def _variable_mana_(t,m):
    """
    graphs the value of variable mana in an unrooted node
    the variable tag
    :param t: the tree
    :param m: regex Match object
    :return: retagged variable
    """
    vid = t.add_ur_node('variable-mana')
    graph_phrase(t,vid,m.group(2))
    inst = "nd<{} num={}>".format(*vid.split(':'))
    return "{} op<≡> {}".format(m.group(1),inst)

def _subcost_(t,pid,sc):
    """
    graphs a subcost (sc) phrase under parent pid
    :param t: the tree
    :param pid: the parent id
    :param sc: subcost phrase
    :return:
    """
    # subcost could be a loyality symbole ([+1]), a mtg symbol (a mana string, E,
    # T or Q) or it could be an action clause i.e. a action word like sacrifice
    # or pay and the parameters or a conjunction i.e. or of symbols
    ttype = mtgltag.tkn_type(sc)
    #TODO need to flesh out
    if ttype == mtgltag.MTGL_SYM:
        if dd.re_mana_check.search(sc):
            return _graph_mana_string_(t,t.add_node(pid,'sub-cost',type='mana'),sc)
        else: return t.add_node(pid,'sub-cost',type='symbol',value=sc)
    elif ttype == mtgltag.MTGL_LOY:
        op,num = mtgltag.re_mtg_loy_sym.search(sc).groups()
        return t.add_node(
            pid,'sub-cost',type='loyalty',value="{}{}".format(op if op else '',num)
        )
    elif dd.re_is_act_clause.search(sc):
        return graph_phrase(t,t.add_node(pid,'sub-cost',type='action'),sc)
    else:
        return t.add_node(pid,'sub-cost',tograph=sc)

def _graph_action_word_(t,pid,aw):
    """
    graphs the action word(s) aw under pid
    :param t: the tree
    :param pid: the parent id
    :param aw: the action word(s) to graph
    :return: a tuple t = (node-id,aw-value)
    """
    try:
        # TODO: what about suffixes
        # extract negation if present
        neg,wd = dd.re_action_word.search(aw).groups()

        tid,val,attr = mtgltag.untag(wd)
        awid = t.add_node(pid,dd.TID[tid])
        avid = t.add_node(awid,val)
        assert(not ('prefix' in attr and neg))
        if 'prefix' in attr: t.add_attr(avid,'prefix',attr['prefix'])
        elif neg: t.add_attr(avid,'prefix','not')
        return awid,val
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

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
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'":
            raise lts.LituusException(lts.EPTRN,"Not a twi clause")
        else: raise

def _activated_check_(line):
    return dd.re_act_check.search(line) and not dd.re_modal_check.search(line)

def _sequence_check_(line):
    if dd.re_sequence_check.search(line): return True
    if dd.re_time_check_start.search(line): return True
    if dd.re_time_check_end.search(line): return True
    if dd.re_sequence_as_cond_check.search(line): return True
    return False

def _graph_mana_string_(t,pid,phrase):
    try:
        # get the mana symbols and recursively call for conjuctions
        xq,m1,m2,m3 = dd.re_mana_chain.search(phrase).groups()
        if m1 or m2:
            oid = t.add_node(pid,'conjunction',value='or',itype="mana")
            for ms in [m1,m2,m3]:
                if not ms: continue
                _graph_mana_string_(t,t.add_node(oid,'item'),ms)
            return oid

        ms = mtgltag.re_mtg_ms.findall(m3)
        mid = t.add_node(
            pid,'mana',quantity=0 if m3 == '{0}' else len(ms),value=m3
        )
        if xq: t.add_node(mid,'quantifier',value=xq)
        return mid

    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise
    return None

####
## ACTIONS
####

## KEYWORD ACTIONS

def _graph_ap_thing_(t,pid,phrase):
    apid = None
    try:
        apid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(apid,'act-direct-object'),phrase)
        return apid
    except lts.LituusException:
        return graph_phrase(t,apid,phrase)

def _graph_ap_n_(t,pid,phrase):
    # graph parameters as number
    m = dd.re_number.search(phrase)
    apid = t.add_node(pid,'act-parameter')
    adoid = t.add_node(apid,'act-direct-object')
    qid = t.add_node(adoid,'quantity')
    if m: t.add_node(qid,'number',value=m.group(1))
    else: graph_phrase(t,t.add_node(qid,'number'),phrase)
    return apid

def _graph_ap_attach_(t,pid,phrase):
    # attach 701.3 has the form attach [self] to [thing]
    apid = None
    try:
        thing1,thing2 = dd.re_attach_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(apid,'act-direct-object'),thing1)
        graph_thing(t,t.add_node(pid,'act-prep-object',value='to'),thing2)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": return None
        else: raise

    # should never get here
    return None

def _graph_ap_double_(t,pid,phrase):
    # double # 701.9 - three variations 1) double the # of counters, 2) double
    # the amount of mana in a mana pool, 3) double an attribute (including a
    # player's life total)

    # counters
    apid = None
    try:
        # the ctr clause may be a specific ctr i.e. +1/+1 (Primordial Hydra) or
        # each kind of counter (Gilder Bairn)
        # TODO: for now we are ignoring "each kind of"
        _,ctr,thing = dd.re_double_ctr_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(apid,'act-direct-object'),ctr)
        graph_thing(t,t.add_node(apid,'act-prep-object',value='on'),thing)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # amount of mana
    apid = None
    try:
        wd,cls = dd.re_double_mana_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        t.add_node(t.add_node(apid,'act-direct-object'),'quantity',value=wd)
        apoid = t.add_node(apid,'act-prep-object',value='of')
        if mtgltag.is_number(cls):
            t.add_node(apoid,'number',value=mtgltag.tag_val(cls))
        else: graph_phrase(t,apoid,cls)
        return apid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # attributes - Okaun, Eye of Chaos, Beacon of Immortality
    if dd.re_attr_clause_check.search(phrase):
        apid = t.add_node(pid,'act-parameter')
        if graph_attribute_clause(t,t.add_node(apid,'act-direct-object'),phrase):
            return apid
        else: t.del_node(apid)

    return None

def _graph_ap_exchange_(t,pid,phrase):
    # exchange 701.10 "A spell or ability may instruct players to exchange something (for example, life totals or
    # control of two permanents) as part of its resolution."

    # control of
    apid = None
    try:
        # unpack and add the act-object node
        thing1,thing2 = dd.re_exchange_ctrl_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        adoid = t.add_node(apid,'act-direct-object')
        if thing2:
            cid = t.add_node(adoid,'conjunction',value='and',itype='thing')
            graph_thing(t,t.add_node(cid,'item'),thing1)
            graph_thing(t,t.add_node(cid,'item'),thing2)
        else: graph_thing(t,adoid,thing1)

        # before returning, add the variation value to the exchange node
        eid = t.findall('exchange',pid)[0]
        t.add_attr(eid,'variation','control-of')
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
        else: raise # something went wrong with adding attribute to 'exchange'
    except IndexError: # means there was no 'exchange' node
        raise lts.LituusException(lts.ENODE,"No exchange node in tree at {}".format(pid))
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # life totals
    apid = None
    try:
        thing1,thing2 = dd.re_exchange_lt_clause.search(phrase).groups()
        if thing1 or thing2:
            # only add a object node if there is one
            apid = t.add_node(pid,'act-parameter')
            if thing1: graph_thing(t,t.add_node(apid,'act-direct-object'),thing1)
            graph_thing(t,t.add_node(apid,'act-prep-object',value='with'),thing2)

        # add the variation value
        eid = t.findall('exchange',pid)[0]
        t.add_attr(eid,'variation','life-total')
        return apid if apid else pid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and aoid: t.del_node(aoid)
        else: raise
    except IndexError: # means there was no 'exchange' node
        raise lts.LituusException(lts.ENODE,"No exchange node in tree at {}".format(pid))
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None

def _graph_ap_fight_(t,pid,phrase):
    # fight 701.12 "A spell or ability may instruct a creature to fight another
    # creature or it may instruct two creatures to fight each other"

    if phrase == "xq<each∧other>": return pid # nothing more to do
    else: return _graph_ap_thing_(t,pid,phrase)

def _graph_ap_search_(t,pid,phrase):
    # search 701.19 "to search for a card in a zone"
    aoid = None
    try:
        zone,thing = dd.re_search_clause.search(phrase).groups()
        aoid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(aoid,'act-indirect-object'),zone)
        graph_thing(t,t.add_node(aoid,'act-direct-object'),thing)
        return aoid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and aoid: t.del_node(aoid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": return None
        else: raise
    return None

def _graph_ap_tap_(t,pid,phrase):
    # tap/untap 701.21 in general we tap or untap a permanent but in some caess
    # there can be a qualifying phrase "for mana"
    apid = None
    try:
        thing,fc = dd.re_tap_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        if thing: graph_thing(t,t.add_node(apid,'act-direct-object'),thing)
        if fc: graph_thing(t,t.add_node(apid,'act-prep-object',value='for'),fc)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": return None
        else: raise
    return None

def _graph_ap_clash_(t,pid,phrase):
    # clash 701.23 - ATT all clash cards have phrase "pr<with> xq<a> xp<opponent>"
    apid = None
    try:
        ply = dd.re_clash_clause.search(phrase).group(1)
        apid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(apid,'act-prep-object',value='with'),ply)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'group'": return None
        else: raise
    return None

def _graph_ap_vote_(t,pid,phrase):
    # vote 701.32 - three forms
    fid = None

    # attribute
    try:
        _,val = dd.re_vote_attribute_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        adoid = t.add_node(apid,'act-prep-object',value='for')
        for val in val.split(mtgl.OR): t.add_node(adoid,'candidate',value=val)
        return apid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # tokens
    try:
        tkn1,tkn2 = dd.re_vote_tokens_clause.search(phrase).groups()
        apid = t.add_node(pid,'act-parameter')
        adoid = t.add_node(apid,'act-prep-object',value='for')

        # have to make sure we untag any tagged tokens first
        if mtgltag.is_tag(tkn1):
            _,tkn1,attr = mtgltag.untag(tkn1)
            if 'suffix' in attr: tkn1 += attr['suffix']
        t.add_node(adoid,'candidate',value=tkn1)

        if mtgltag.is_tag(tkn2):
            _,tkn2,attr = mtgltag.untag(tkn2)
            if 'suffix' in attr: tkn2 += attr['suffix']
        t.add_node(adoid,'candidate',value=tkn2)
        return apid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # object
    apid = None
    try:
        obj = dd.re_vote_thing_clause.search(phrase).group(1)
        apid = t.add_node(pid,'act-parameter')
        adoid = t.add_node(apid,'act-prep-object',value='for')
        graph_thing(t,t.add_node(apid,'candidate'),obj)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'group'": pass
        else: raise

    return None

def _graph_ap_meld_(t,pid,phrase):
    # meld 701.37 two forms "meld them into ..." and "melds with"

    apid = None
    try:
        obj = dd.re_meld_clause1.search(phrase).group(1)
        apid = t.add_node(pid,'act-parameter')
        oid = graph_thing(t,t.add_node(apid,'act-direct-object'),'xo<them>')
        graph_thing(t,t.add_node(apid,'act-prep-object',value='into'),obj)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'group'": pass
        else: raise

    # meld with
    apid = None
    try:
        obj = dd.re_meld_clause2.search(phrase).group(1)
        apid = t.add_node(pid,'act-parameter')
        graph_thing(t,t.add_node(apid,'act-prep-object',value='with'),obj)
        return apid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN and apid: t.del_node(apid)
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'group'": pass
        else: raise

    return None

## Lituus Actions

def _graph_ap_add_(t,pid,phrase):
    # TODO: should we be graphing mana
    # the simplest is a mana string or mana string conjunction
    #oid = graph_thing(t, t.add_node(apid, 'act-direct-object'), 'xo<them>')
    if dd.re_mana_check.search(phrase):
        mid = _graph_mana_string_(t,t.add_node(pid,'act-direct-object'),phrase)
        if mid: return mid

    # now have to check for complex phrasing
    # additional number of mana
    try:
        xq,num,cls = dd.re_nadditional_mana.search(phrase).groups()
        doid = t.add_node(pid,'act-direct-object')
        mid = t.add_node(doid,'mana',quantity=num)
        if xq: t.add_node(mid,'quantifier',value=xq)
        t.add_node(mid,'mana-qualifier',tograph=cls) # TODO
        return doid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # {X} clause
    try:
        ms,cls = dd.re_mana_trailing.search(phrase).groups()
        doid = t.add_node(pid,'act-direct-object')
        mid = _graph_mana_string_(t,doid,ms)
        t.add_node(mid,'mana-qualifier',tograph=cls) # TODO
        return doid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # amount of {X} clause
    try:
        ms,cls = dd.re_amount_of_mana.search(phrase).groups()
        doid = t.add_node(pid,'act-direct-object')
        mid = t.add_node(doid,'mana',value='amount-of')
        _graph_mana_string_(t,mid,ms)
        t.add_node(mid,'mana-qualifier',tograph=cls)
        return doid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    # that much {x}
    try:
        ms,cls = dd.re_that_much_mana.search(phrase).groups()
        doid = t.add_node(pid,'act-direct-object')
        mid = t.add_node(doid,'mana',value='that-much')
        _graph_mana_string_(t,doid,ms)
        if cls: t.add_node(mid,'mana-qualifier',tograph=cls)
        return doid
    except AttributeError as e:
        if e.__str__() == "'NoneType' object has no attribute 'groups'": pass
        else: raise

    return None
