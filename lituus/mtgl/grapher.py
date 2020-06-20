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
__version__ = '0.1.4'
__date__ = 'June 2020'
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
                except AttributeError:
                    raise lts.LituusException(
                        lts.EPTRN,"Failure matching aw line ({})".format(line)
                    )
            else: graph_line(t,pids[i],line,dcard['type'])

        # Remove keyword and ability word nodes if empty & graph the lines
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
    # enclosed quotes will mess up graphing - find all enclosed quotes and graph
    # them separately under an unrooted node
    line = dd.re_enclosed_quote.sub(lambda m: _enclosed_quote_(t,m),line)

    # Ability lines can be one of
    #  112.3a Spell = instant or sorcery,
    #  112.3b Activated = of the form cost:effect,instructions.
    #  112.3c Triggered = of the form tgr condition, effect. instructions &
    #  112.3d static = none of the above
    # A special case is the delayed trigger (603.7) as these may generally be
    # part of a larger line (Prized Amalgam), they are not checked for here but
    # in graph_phrase when phrases are checked
    if _activated_check_(line): graph_activated(t,pid,line)
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
        # split the line into cost and effect graph each separately
        cost,effect,instr = dd.re_act_line.search(line).groups()
        aaid = t.add_node(pid,'activated-ability')
        graph_cost(t,t.add_node(aaid,'activated-cost'),cost)
        graph_phrase(t,t.add_node(aaid,'activated-effect'),effect)
        if instr: graph_phrase(t,t.add_node(aaid,'activated-instructions'),instr)
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
        tp,cond,effect,instr = dd.re_tgr_line.search(line).groups()
        taid = t.add_node(pid,'triggered-ability')
        t.add_node(taid,'triggered-preamble',value=tp)
        graph_phrase(t,t.add_node(taid,'triggered-condition'),cond)
        graph_phrase(t,t.add_node(taid,'triggered-effect'),effect)
        if instr:
            graph_phrase(t,t.add_node(taid,'triggered-instruction'),instr)
    except AttributeError:
        raise lts.LituusException(
            lts.EPTRN,"Not a triggered ability ({})".format(line)
        )

def graph_phrase(t,pid,line,i=0):
    """
    Graphs phrases looking first at high-level consructs. Starting again with
    triggered and activated abilities, then replacement effects (614.1,614.2),
    and alternate cost (APC) effects (118.9)
    :param t: the tree
    :param pid: parent of the line
    :param line: the text to graph
    :param i: iteration count to avoid infinite rcursion
    """
    # check for activated/triggered ability first
    if _activated_check_(line): graph_activated(t,pid,line)
    elif dd.re_tgr_check.search(line): graph_triggered(t,pid,line)
    else:
        # then check for replacement and apc before continuing
        # TODO: can we make a check for all of these?
        if graph_replacement_effects(t,pid,line): return
        if graph_apc_phrases(t,pid,line): return
        if dd.re_modal_check.search(line) and graph_modal_phrase(t,pid,line): return
        if dd.re_lvl_up_check.search(line) and graph_lvl_up_phrase(t,pid,line): return
        if _sequence_check_(line) and graph_sequence_phrase(t,pid,line): return
        if graph_optional_phrase(t,pid,line): return
        if graph_restriction_phrase(t,pid,line): return
        if graph_option_phrase(t,pid,line): return
        if dd.re_delayed_tgr_check.search(line) and graph_delayed_tgr(t,pid,line): return
        if dd.re_act_clause_check.search(line) and graph_action_clause(t,pid,line): return

        # TODO: at this point how to continue: could take each sentence if more than
        #  one and graph them as phrase and if only sentence, graph each clause (i.e.
        #  comma separated i.e. Goblin Bangchuckers
        # if we get here start by breaking the line into sentences
        ss = [x.strip() + '.' for x in dd.re_sentence.split(line) if x != '']
        if len(ss) > 1:
            for s in ss: graph_phrase(t,pid,s,i+1)
        else:
            if i < 1: graph_phrase(t,t.add_node(pid,'sentence'),line,i+1)
            else:
                # TODO: FOR TESTING ONLY
                #if dd.re_time_check.search(line): return graph_phase(t,pid,line)
                t.add_node(pid,'ungraphed-sentence',tograph=line)

def graph_clause(t,pid,clause):
    """
    Graphs a clause, a keyword action orientated chunk of words
    :param t: the tree
    :param pid: parent of the line
    :param clause: the text to graph
    """
    #try:
    #    pre,ka,post = dd.re_keyword_action_clause.search(clause).groups()
    #    return
    #except AttributeError:
    #    pass
    #if dd.re_ka_clause.search(clause): graph_action_clause(t,pid,clause)
    t.add_attr(pid,'ungraphed',clause)

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
    if 'cn<instead>' in line: return graph_repl_instead(t,pid,line)
    elif 'xa<skip>' in line: # 614.1b 'skip' replacements
        rid = None
        try:
            ply,phase = dd.re_skip.search(line).groups()
            rid = t.add_node(pid,'replacement-effect')
            if not ply: ply = 'xp<you>' # TODO: is this necessary
            sid = t.add_node(rid,'skip')
            graph_thing(t,sid,ply)
            graph_phrase(t,sid,phase) # TOOD: dropping adding node 'phase' revisit
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass
        return None
    elif dd.re_etb_repl_check.search(line): # 614.1c and 614.1d ETB replacements
        # try 614.1c
        rid = graph_repl_etb1(t,pid,line)
        if rid: return rid

        # try 614.1d
        rid = graph_repl_etb2(t,pid,line)
        if rid: return rid
    elif dd.re_turn_up_check.search(line):
        rid = None
        try:
            perm,act = dd.re_turn_up.search(line).groups()
            rid = t.add_node(pid,'replacement-effect')
            graph_phrase(t,t.add_node(rid,'as'),perm)
            graph_phrase(t,t.add_node(rid,'is-turned-face-up'),act)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass
        return None
    elif dd.re_repl_dmg_check.search(line): return graph_repl_damage(t,pid,line)

    return None

def graph_apc_phrases(t,pid,line):
    """
    graphs APC phrases in line
    :param t: the tree
    :param pid: parent id to graph under
    :param line: text to graph
    :return: node id of the APC phrase root or None
    """
    aid = None

    # See 118.9 for some phrasing
    # start with 'you may' optional APCs
    if 'xp<you> cn<may>' in line:
        # [condition]? [player] may [action] rather than pay [cost]
        try:
            cond,ply,act,cost = dd.re_action_apc.search(line).groups()
            aid = t.add_node(pid,'apc')
            if cond: graph_phrase(t,t.add_node(aid,'if'),cond)
            rid = t.add_node(aid,'rather-than')
            graph_phrase(t,t.add_node(rid,'pay'),cost)
            mid = t.add_node(aid,'may')
            graph_thing(t,mid,ply)
            graph_phrase(t,t.add_node(mid,'apc-cost'),act)
            return aid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(aid)
        except AttributeError:
            pass

        # if [condition] you may cast ...
        try:
            cond,wo = dd.re_cast_apc_nocost.search(line).groups()
            aid = t.add_node(pid,'apc')
            graph_phrase(t,t.add_node(aid,'if'),cond)
            mid = t.add_node(aid,'may')
            graph_thing(t,mid,'xp<you>')
            graph_phrase(t,mid,"ka<cast> ob<card ref=self>")
            graph_phrase(t,t.add_node(mid,'without'),wo)
            return aid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(aid)
        except AttributeError:
            pass

        # alternate phrasing of action-apc that always has a condition
        try:
            cond,cost,act = dd.re_alt_action_apc.search(line).groups()
            aid = t.add_node(pid,'apc')
            graph_phrase(t,t.add_node(aid,'if'),cond)
            rid = t.add_node(aid,'rather-than')
            graph_phrase(t,t.add_node(rid,'pay'),cost)
            mid = t.add_node(aid,'may')
            graph_thing(t,mid,'xp<you>')
            graph_phrase(t,t.add_node(mid,'apc-cost'),act)
            return aid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(aid)
        except AttributeError:
            pass
    elif line.startswith('cn<rather_than> xa<pay>'):
        try:
            cost,ply,act = dd.re_rather_than_apc.search(line).groups()
            aid = t.add_node(pid,'apc')
            rid = t.add_node(aid,'rather-than')
            graph_phrase(t,t.add_node(rid,'pay'),cost)
            mid = t.add_node(rid,'may')
            graph_thing(t,mid,ply)
            graph_phrase(t,t.add_node(mid,'apc-cost'),act)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(aid)
        except AttributeError:
            pass

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
    rid = None
    # check for 'would' phrasing, 'of' phrasing and 'if' phrasing
    if 'cn<would>' in phrase:
        # if-would-instead variant a
        try:
            # for this, we graph the two 'woulds' as separate if-would clauses
            # under a 'or' conjunction
            t1,w1,t2,w2,instead = dd.re_if_would2_instead.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            oid = t.add_node(rid,'conjunction',value='or',itype="if-would")
            iid = t.add_node(oid,'if')
            try:
                graph_thing(t,iid,t1)
            except lts.LituusException as e:
                if e.errno == lts.EPTRN:
                    t.add_node(iid,'ungraphed-thing',tograph=t1)
                else: raise
            graph_phrase(t,t.add_node(iid,'would'),w1)
            iid = t.add_node(oid,'if')
            try:
                graph_thing(t,iid,t2)
            except lts.LituusException as e:
                if e.errno == lts.EPTRN:
                    t.add_node(iid,'ungraphed-thing',tograph=t2)
                else: raise
            graph_phrase(t,t.add_node(iid,'would'),w2)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass

        # if-would-instead variant b
        try:
            thing,would,instead = dd.re_if_would_instead1.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            iid = t.add_node(rid,'if')
            graph_thing(t,iid,thing)
            graph_phrase(t,t.add_node(iid,'would'),would)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass

        # if-instead-would variant c
        try:
            thing,would,instead = dd.re_if_would_instead2.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            iid = t.add_node(rid,'if')
            graph_thing(t,iid,thing)
            graph_phrase(t,t.add_node(iid,'would'),would)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass

        # that-would-instead - have to deal with these differently due to
        # how the condition & replacement are separated/identified
        try:
            # get the effect and subphrase and split the subphrase. _twi_split_
            # will throw an exception if the phrase is not valid for this
            effect,subphrase = dd.re_that_would_instead.search(phrase).groups()
            would,instead = _twi_split_(subphrase)

            # and graph it
            rid = t.add_node(pid,'replacement-effect')
            eid = t.add_node(rid,'effect')
            graph_phrase(t,eid,effect)
            graph_phrase(t,t.add_node(eid,'that-would'),would)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except (AttributeError,lts.LituusException):
            pass

        # would-instead (timing related)
        try:
            cond,would,instead = dd.re_would_instead.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            cid = t.add_node(rid,'condition') # TODO: rename this to something time related
            graph_phrase(t,cid,cond)
            graph_phrase(t,t.add_node(cid,'would'),would)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for may instead (optional replacement value)
        try:
            # NOTE: thing1 and thing2 should be the same
            thing1,act1,thing2,act2 = dd.re_may_instead.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            iid = t.add_node(rid,'if')
            graph_thing(t,iid,thing1)
            graph_phrase(t,t.add_node(iid,'would'),act1)
            iid = t.add_node(rid,'instead')
            mid = t.add_node(iid,'may')
            graph_thing(t,mid,thing2)
            graph_phrase(t,mid,act2)
            return rid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(rid)
        except AttributeError:
            pass

    if 'of' in phrase:
        # if-instead-of clause
        try:
            act,repl,iof = dd.re_if_instead_of.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            graph_phrase(t,t.add_node(rid,'if'),act)
            iid = t.add_node(rid,'instead-of')
            graph_phrase(t,iid,iof)
            graph_phrase(t,iid,repl)
            return rid
        except AttributeError:
            pass

        # test for instead-of-if clause
        # TODO: for now we are rearranging the order of the phrases so that it
        #  matches above but will it mess readers up
        try:
            repl,iof,cond = dd.re_instead_of_if.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            graph_phrase(t,t.add_node(rid,'if'),cond)
            iid = t.add_node(rid,'instead-of')
            graph_phrase(t,iid,iof)
            graph_phrase(t,iid,repl)
            return rid
        except AttributeError:
            pass

        # test for instead-of
        try:
            repl,iof = dd.re_instead_of.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            iid = t.add_node(rid,'instead-of')
            graph_phrase(t,iid,iof)
            graph_phrase(t,iid,repl)
            return rid
        except AttributeError:
            pass

    if 'cn<if>' in phrase:
        # test for if-instead
        try:
            cond,instead = dd.re_if_instead.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            graph_phrase(t,t.add_node(rid,'if'),cond)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for if-instead fenced
        try:
            cond,instead = dd.re_if_instead_fence.search(phrase).groups()
            rid = t.add_node(pid,'replacement-effect')
            graph_phrase(t,t.add_node(rid,'if'),cond)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

        # test for instead-if clause
        try:
            instead,cond = dd.re_instead_if.search(phrase).groups()
            rid = t.add_node(pid,'replacement-of')
            graph_phrase(t,t.add_node(rid,'if'), cond)
            graph_phrase(t,t.add_node(rid,'instead'),instead)
            return rid
        except AttributeError:
            pass

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
        perm,ctrs = dd.re_etb_with.search(phrase).groups()
        rid = t.add_node(pid,'etb')
        graph_thing(t,rid,perm)
        graph_phrase(t,t.add_node(rid,'with'),ctrs)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError:
        pass

    # As Permanent ETB ...
    try:
        perm,action = dd.re_as_etb.search(phrase).groups()
        rid = t.add_node(pid,'as')
        eid = t.add_node(rid,'etb')
        graph_thing(t,eid,perm)
        graph_phrase(t,eid,action)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError: # no match
        pass

    # Permanent ETB as
    try:
        perm,asa = dd.re_etb_as.search(phrase).groups()
        rid = t.add_node(pid,'etb')
        graph_thing(t,rid,perm)
        graph_phrase(t,t.add_node(rid,'as'),asa)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError: # no match
        pass

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
    rid = None

    # see if we have a status etb first
    try:
        thing,sts,unless = dd.re_etb_status.search(phrase).groups()
        rid = t.add_node(pid,'etb')
        graph_thing(t,rid,thing)
        t.add_node(rid,'status',value=sts)
        if unless: graph_phrase(t,t.add_node(rid,'unless'),unless)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError:
        pass

    # continuous etb with an optional effect
    try:
        perm,effect = dd.re_etb_1d.search(phrase).groups()
        rid = t.add_node(pid,'etb')
        graph_thing(t,rid,perm)
        if effect: graph_phrase(t,t.add_node(rid,'effect'),effect)
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError: # no match
        pass

    return None

def graph_repl_damage(t,pid,phrase):
    """
    graphs as obj is turned face up (614.2)
    :param t: the tree
    :param pid: parent id
    :param phrase: the clause to graph
    :return: node id of the replacement subtree or None
    """
    rid = did = None
    # damage prevention if [object/source] would [old], [new]
    try:
        src,old,new = dd.re_if_would.search(phrase).groups()
        rid = t.add_node(pid,'replacement-effect')
        graph_thing(t,t.add_node(rid,'if'),src)
        graph_phrase(t,t.add_node(rid,'would'),old)
        graph_phrase(t,rid,new) # TODO: removed intermeditary node
        return rid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(rid)
    except AttributeError:
        pass

    # look for prevent damage
    try:
        time,src,act1,tgt,dur,act2 = dd.re_repl_dmg.search(phrase).groups()
        did = graph_duration(t,pid,dur)
        tid = t.add_node(did,'when')
        graph_phrase(t,tid,time) # TODO: revisit
        rid = t.add_node(tid,'replacement-effect')
        graph_thing(t,rid,src)
        graph_phrase(t,t.add_node(rid,'would'),act1)
        if tgt: graph_thing(t,t.add_node(rid,'to'),tgt)
        graph_phrase(t,rid,act2)
        return did
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(did)
    except AttributeError:
        pass

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
    except AttributeError:
        pass

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
    except AttributeError:
        pass

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
            if pt: t.add_node(lvid,'p/t',value=pt)
            if ab: graph_phrase(t,t.add_node(lvid,'ability'),ab)
        return lid
    except AttributeError:
        if lid: t.del_node(lid)
        return None

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
    # start with time (ending with a turn structure
    if dd.re_time_check.search(line):
        try:
            _,when,cls,xq,ts = dd.re_sequence_time.search(line).groups()
            tid = tid = t.add_node(pid,'timing') # TODO: don't like this label
            t.add_node(tid,'when',value=when)  # ignore the first quantifier
            if ts in mtgl.steps1: ts = ts + "-step"
            if cls:
                # TODO: have to graph the complex phrases
                t.add_node(tid,'timing-clause',tograph=cls)
            t.add_node(tid,'phase',quantifier=xq,value=ts)
            return tid
        except AttributeError:
            pass
    elif dd.re_sequence_check.search(line):
        # check for then [action] first
        try:
            _,act = dd.re_sequence_then.search(line).groups()
            sid = t.add_node(pid,'then')
            graph_phrase(t,sid,act)
            return sid
        except AttributeError:
            pass

        # then durations [sequence] [phase/step], [action]
        try:
            dur,act = dd.re_sequence_dur.search(line).groups()
            did = graph_duration(t,pid,dur)
            graph_phrase(t,did,act) # TODO: should this be under the 'until' node (see Pale Moon)
            return did
        except AttributeError:
            pass

        # then other sequences of the form [sequence] [cond], [effect]
        try:
            seq,cond,act = dd.re_sequence_cond.search(line).groups()
            sid = t.add_node(pid,seq.replace('_','-'))
            graph_phrase(t,t.add_node(sid,'condition'),cond)
            graph_phrase(t,sid,act)
            return sid
        except AttributeError:
            pass
    else:
        # should never get here
        raise lts.LituusException(lts.EPTRN,"{} not a sequence".format(line))

    return None

####
## CONDITION PHRASES
####

def graph_optional_phrase(t,pid,line):
    """
    determines how to graph the condition phrase in line
    :param t: the tree
    :param pid: the parent id
    :param line: text to graph
    :return: node id or None
    """
    cid = None
    if line.startswith('cn<if>'):
        # if-player-does
        try:
            ply,neg,act = dd.re_if_ply_does.search(line).groups()
            cid = t.add_node(pid,'if')
            graph_thing(t,cid,ply)
            did = t.add_node(cid,"does{}".format('-not' if neg else ''))
            graph_phrase(t,did,act)
            return cid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(cid)
        except AttributeError:
            pass

        # if-player-cannot
        try:
            ply,act = dd.re_if_ply_cant.search(line).groups()
            cid = t.add_node(pid,'if')
            graph_thing(t,cid,ply)
            graph_phrase(t,t.add_node(cid,'cannot'),act)
            return cid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(cid)
        except AttributeError:
            pass

        # if condition-action
        try:
            cond,act = dd.re_if_cond_act.search(line).groups()
            cid = t.add_node(pid,'if')
            graph_phrase(t,cid,cond)
            graph_phrase(t,cid,act)
            return cid
        except AttributeError:
            pass
    elif 'cn<unless' in line:
        # thing-cannot-unless
        try:
            thing,act,cond = dd.re_cannot_unless.search(line).groups()
            cid = t.add_node(pid,'cannot')
            graph_thing(t,cid,thing)
            graph_phrase(t,cid,act)
            graph_phrase(t,t.add_node(cid,'unless'),cond)
            return cid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN: t.del_node(cid)
        except AttributeError:
            pass

        # action-unless
        try:
            act,cond = dd.re_action_unless.search(line).groups()
            graph_phrase(t,pid,act)
            cid = t.add_node(pid,'unless')
            graph_phrase(t,cid,cond)
            return cid
        except AttributeError:
            pass

    return None

def graph_restriction_phrase(t,pid,phrase):
    """
    graphs restriction phases
    :param t: the tree
    :param pid: the parent id
    :param phrase: text to graph
    :return: node id or None on failure
    """
    # TODO: do we need to add intermediate restriction node
    # need to check conjunctions first
    try:
        act,rstr1,conj,rstr2 = dd.re_only_conjunction.search(phrase).groups()
        oid = t.add_node(pid,'only')
        graph_phrase(t,oid,act)
        cid = t.add_node(oid,'conjunction',value=conj,itype='only')
        graph_restriction_phrase(t,cid,rstr1)
        graph_restriction_phrase(t,cid,rstr2)
        return oid
    except AttributeError:
        pass

    # The below may be part of a recursive call due to a conjunction. Check the
    # parent type first. If conjunction, only the restriction will be present,
    # do not add a new 'only' node, merely graphing the restriciton

    # only-ifs
    if 'cn<only_if>' in phrase:
        try:
            effect,cond = dd.re_only_if.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction':
                return graph_phrase(t,t.add_node(pid,'if'),cond)
            else:
                oid = t.add_node(pid,'only')
                graph_phrase(t,oid,effect)
                graph_phrase(t,t.add_node(oid,'if'),cond)
                return oid
        except AttributeError:
            pass

    if 'cn<only>' in phrase:
        # start with only-[sequence]
        try:
            act,seq,phase = dd.re_restriction_timing.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction':
                return graph_phase(t,t.add_node(pid,seq),phase)
            else:
                oid = t.add_node(pid,'only')
                graph_phrase(t,oid,act)
                graph_phase(t,t.add_node(oid,seq),phase)
                return oid
        except AttributeError:
            pass

        # only-number per turn
        try:
            act,num,phase = dd.re_restriction_number.search(phrase).groups()
            if mtgt.node_type(pid) == 'conjunction':
                nid = t.add_node(pid,'times',value=num)
                if phase: graph_phase(t,nid,phase)
                return nid
            else:
                oid = t.add_node(pid,'only')
                graph_phrase(t,oid,act)
                nid = t.add_node(oid,'times',value=num)
                if phase: graph_phase(t,nid,phase)
                return oid
        except AttributeError:
            pass

    return None

####
## OPTIONAL PHRASES
####

def graph_option_phrase(t,pid,phrase):
    """
    determines how to graph the optional phrase in line
    :param t: the tree
    :param pid: the parent id
    :param phrase: text to graph
    :return: node id or None
    """
    mid = None

    # check may as-though first
    try:
        # TODO: should we graph these under an i-node 'option'
        ply,act1,act2 = dd.re_may_as_though.search(phrase).groups()
        mid = t.add_node(pid,'may')
        graph_thing(t,mid,ply)
        graph_phrase(t,mid,act1)
        graph_phrase(t,t.add_node(mid,'as-though'),act2)
        return mid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(mid)
    except AttributeError:
        pass

    # may have
    try:
        ply,phrase = dd.re_may_have.search(phrase).groups()
        mid = t.add_node(pid,'may')
        graph_thing(t,mid,ply)
        graph_phrase(t,t.add_node(mid,'have'),phrase)
        return mid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(mid)
    except AttributeError:
        pass

    # then may only
    try:
        ply,act = dd.re_optional_may.search(phrase).groups()
        mid = t.add_node(pid,'may')
        graph_thing(t,mid,ply)
        graph_phrase(t,mid,act)
        return mid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(mid)
    except AttributeError:
        pass

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
        t.add_node(dtid,'triggered-preamble',value=tp)
        graph_phrase(t,t.add_node(dtid,'triggered-condition'),cond)
        graph_phrase(t,t.add_node(dtid,'triggered-effect'),effect)
        return dtid
    except AttributeError:
        return None

####
## CLAUSES, TOKENS
####

def graph_cost(t,pid,phrase):
    """
    graphs the cost(s) in phrase
    :param t: the tree
    :param pid: parent id to graph under
    :param phrase: the cost phrase
    :return: cost node id
    """
    # a cost is one or more comma separated subcosts
    # graph_line(t,t.add_node(aaid,'activated-cost'),cost)
    # i.e. Flooded Strand
    #  └─activated-ability:0
    #    ├─activated-cost:0
    #    │ └─ungraphed-sentence:0 (tograph={t}, xa<pay> nu<1> xo<life>, ka<sacrifice> ob<card ref=self>)
    # = ['{t}', 'xa<pay> nu<1> xo<life>', 'ka<sacrifice> ob<card ref=self>']
    for subcost in [x for x in dd.re_comma.split(phrase) if x != '']:
        _subcost_(t,pid,subcost)

def graph_action_clause(t,pid,phrase):
    """
    graphs the keyword or lituus action clause in phrase under pid
    :param t: the tree
    :param pid: parent id
    :param phrase: the text to graph
    :return: the node id
    """
    # look for 'traditional' action claues first i.e. they have an action word
    try:
        # determine if there is a conjunction of actions or a singleton action
        # TODO: we need to check for conditional in anded clauses
        thing = cnd = aw1 = act1 = aw2 = act2 = None
        m = dd.re_anded_action_clause.search(phrase)
        if m: thing,aw1,act1,aw2,act2 = m.groups()
        else: thing,cnd,aw1,act1 = dd.re_action_clause.search(phrase).groups()

        # set up nid and aid as None
        nid = aid = None

        try:
            # now set up of singleton and graph the thing if present
            acs = [(aw1,act1)]
            if cnd:
                nid = t.add_node(pid,cnd)
                aid = t.add_node(nid,'action')
            else: aid = t.add_node(pid,'action')
            if thing: graph_thing(t,aid,thing)

            # if there is a conjunction add a 'and' node and append the 2nd action
            if aw2:
                aid = t.add_node(aid,'conjunction',value='and',itype="action")
                acs.append((aw2,act2))

            # graph the action params
            for aw,act in acs:
                awid = t.add_node(aid,mtgltag.tag_val(aw))
                if act:
                    if not graph_action_param(t,awid,mtgltag.tag_val(aw),act):
                        graph_phrase(t,awid,act)
            return aid
        except lts.LituusException as e:
            if e.errno == lts.EPTRN:
                if nid: t.del_node(nid)
                else: t.del_node(aid)
            else:
                raise
            return None
    except AttributeError:
        pass

    # then check for player own/control
    aid = None
    try:
        ply,poss,clause = dd.re_action_ply_poss.search(phrase).groups()
        aid = t.add_node(pid,'action')
        graph_thing(t,aid,ply)
        awid = t.add_node(aid,poss)
        graph_phrase(t,awid,clause)
        return aid
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(aid)
    except AttributeError:
        pass

    return None

def graph_thing(t,pid,clause):
    """
    Graphs the thing under node pid
    :param t: the tree
    :param pid: the parent id
    :param clause: the clause
    :return: the thing node id
    """
    # TODO: should we combine suffix with the stem if present?
    # could have a qst phrase, a qtz phrase or a possesive phrase - check all
    try:
        xq,loc,num,thing,zn,amp = dd.re_qtz.search(clause).groups()
        eid = t.add_node(pid,'thing')
        sid = t.add_node(eid,'specifying-clause')

        # two formats
        #  1. the [top|bottom] [num]? [card] [zone] [amp]?
        #  2. [quantifier] [card] [zone] [amp]?
        # the specifying claues differs depending on the format
        if loc:
            if xq: t.add_node(sid,'quantifier',value=xq)
            t.add_node(sid,'which',value=loc,quanitity=num if num else 1)
        else:
            assert(num is None)
            t.add_node(sid,'which',quantifier=xq)
        if amp: t.add_node(sid,'how',value='face-'+amp)
        _graph_object_(t,eid,thing)
        quid = t.add_node(eid, 'qualifying-clause')
        if not _graph_qualifying_clause_(t,quid,zn):
            t.del_node(quid)
            raise lts.LituusException(lts.EPTRN,"{} is not a thing".format(clause))

        return eid
    except AttributeError:
        pass

    try:
        # 'unpack' the phrase
        n,xq,st,th1,conj,xq2,th2,poss,qual = dd.re_qst.search(clause).groups()
        eid = t.add_node(pid,'thing')

        # any preceding quantifier and/or status belong to the holistic thing
        # while intermediate quantifiers belong only to the subsequent thing
        if n: t.add_node(eid,'number',value=n)
        if xq: t.add_node(eid,'quantifier',value=xq)
        if st: t.add_node(eid,'status',value=st)

        # if there is a conjunction, graph the things as items under a conjunction
        # node, adding the second quanitifier if present
        if conj:
            cid = t.add_node(eid,'conjunction',value=conj,itype='thing')
            iid = t.add_node(cid,'item')
            _graph_object_(t,iid,th1)
            iid = t.add_node(cid, 'item')
            if xq2: t.add_node(iid,'quantifier',value=xq2)
            _graph_object_(t,iid,th2)
        else: _graph_object_(t,eid,th2)

        # graph any trailing posession clauses
        if poss:
            nid = None
            try:
                ply,neg,wd = dd.re_possession_clause.search(poss).groups()
                lbl = 'owned-by' if wd == 'own' else 'controlled-by'
                if not neg: cid = t.add_node(nid,lbl)
                else:
                    nid = t.add_node(eid,'not')
                    cid = t.add_node(nid,lbl)
                graph_thing(t,cid,ply)
            except lts.LituusException:
                if nid: t.del_node(nid)
                raise lts.LituusException(lts.EPTRN, "{} is not a possession".format(ctlr))
            except AttributeError:
                raise lts.LituusException(lts.EPTRN,"{} is not a possession".format(ctlr))

        # graph any trailing qualifying clauses
        if qual:
            quid = t.add_node(eid,'qualifying-clause')
            if not _graph_qualifying_clause_(t,quid,qual):
                t.del_node(eid)
                raise lts.LituusException(lts.EPTRN,"{} is not a qualifying".format(qual))

        # and return the thing node id
        return eid
    except AttributeError:
        pass

    # check for possessives which may be preceded by a quantifier
    try:
        # unpack the things then untag each thing
        xq,thing1,thing2 = dd.re_consecutive_things.search(clause).groups()
        tid1,val1,attr1 = mtgltag.untag(thing1)
        tid2,val2,attr2 = mtgltag.untag(thing2)

        # only continue if an r or "'s" possesive suffix exists
        if 'suffix' in attr1 and attr1['suffix'] in ["r","'s"]:
            # remove the suffix the first thing and retag
            del attr1['suffix']
            thing1 = mtgltag.retag(tid1,val1,attr1)

            # the second thing is the primary node (readd quanitifier if present)
            if xq: thing2 = "xq<{}> {}".format(xq,thing2)
            eid = graph_thing(t,pid,thing2)

            # the label of the intermeditary node depends on the two things
            lbl = 'whose' if tid1 == 'xp' and tid2 == 'zn' else 'of'

            # add the 1st thing under the intermeditary node of the 2nd thing
            graph_thing(t,t.add_node(t.children(eid)[-1],lbl),thing1)
            return eid
    except AttributeError:
        pass

    raise lts.LituusException(lts.EPTRN,"Not a thing {}".format(clause))

def graph_duration(t,pid,clause):
    """
    graphs a duration clause
    :param t: the tree
    :param pid: parent id
    :param clause: the duration clause to graph
    :return:  node id of the duration subtree or None
    """
    # there are two variations
    #  a) [quantifier] [phase/step] and
    #  b) [sequence] [phase/step)

    try:
        # unpack the tags and create the duration node
        tkn,phase = dd.re_duration_ts.search(clause).groups()
        did = t.add_node(pid,'duration')

        # untag the first tag and get the value for the turn structure tag
        tid,val,attr = mtgltag.untag(tkn)

        # graph the clause based on the type of the first token
        if tid == 'sq': t.add_node(did,val,value=phase)
        elif tid == 'xq': t.add_node(did,phase,value=val)
        else: assert(False)

        return did
    except AttributeError:
        pass
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
    # TODO: double, exchange
    if aw == 'activate': return _graph_ap_thing_(t,pid,param) # 701.2
    elif aw == 'attach': return _graph_ap_attach_(t,pid,param) # 701.3
    elif aw == 'unattach': return _graph_ap_thing_(t,pid,param) # 701.3d
    elif aw == 'cast': return _graph_ap_thing_(t,pid,param) # 701.4
    elif aw == 'counter': return _graph_ap_thing_(t,pid,param) # 701.5
    elif aw == 'create': return _graph_ap_thing_(t,pid,param)  # 701.6
    elif aw == 'destroy': return _graph_ap_thing_(t,pid,param) # 701.7
    elif aw == 'discard': return _graph_ap_thing_test_(t,pid,param) # 701.8
    # TODO: elif aw == 'double': # 701.9
    # TODO: elif aw == 'exchange': # 701.10
    elif aw == 'exile': return _graph_ap_thing_(t,pid,param) # 701.11
    elif aw == 'fight': return _graph_ap_thing_(t,pid,param) # 701.12
    # TODO: elif aw == 'play': # 701.13
    elif aw == 'regenerate': return _graph_ap_thing_test_(t,pid,param) # 710.14

    # then lituus actions
    if aw == 'add': return _graph_ap_add_(t,pid,param)

    # nothing found
    return t.add_node(pid,'action-params',tograph=param)

def graph_phase(t,pid,clause):
    """
    Graphs the phase under node pid
    :param t: the tree
    :param pid: the parent id
    :param clause: the clause
    :return: the phase node id
    """
    # TODO: combine graph_duration and this
    try:
        xq,ply,phase = dd.re_phase.search(clause).groups()
        phid = t.add_node(pid,'phase-clause')
        if xq: t.add_node(phid,'quantifier',value=xq)
        t.add_node(phid,'phase',value=phase)
        if ply: t.add_node(phid,'whose',value=ply)
        return phid
    except AttributeError:
        pass

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
        oid = t.add_node(pid,mtgl.TID[tid],value=val)

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
            return _graph_mana_string_(t,t.add_node(pid,'subcost',type='mana'),sc)
        else:
            # have a non mana symbol
            return t.add_node(pid,'subcost',type='symbol',value=sc)
        #return t.add_node(pid,'subcost',type='mana',value=sc)
    elif ttype == mtgltag.MTGL_LOY:
        op,num = mtgltag.re_mtg_loy_sym.search(sc).groups()
        return t.add_node(
            pid,'subcost',type='loyalty',value="{}{}".format(op if op else '',num)
        )
    elif dd.re_is_act_clause.search(sc):
        return graph_phrase(t,t.add_node(pid,'sub-cost',type='action'),sc)
    else:
        return t.add_node(pid,'subcost',tograph=sc)

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

def _activated_check_(line):
    return dd.re_act_check.search(line) and not dd.re_modal_check.search(line)
    #return dd.re_act_check.search(line) and mtgl.BLT not in line

def _sequence_check_(line):
    return dd.re_sequence_check.search(line) or dd.re_time_check.search(line)

def _graph_qualifying_clause_(t,pid,clause):
    """
    Graphs a qualifying clause (as part of a thing)
    :param t: the tree
    :param pid: parent of the line
    :param clause: the text to graph
    """
    # check for duals first
    # TODO: for the below we should add an itermediary node with the qualying word first
    cid = None
    try:
        q1,q2 = dd.re_dual_qualifying_clause.search(clause).groups()
        cid = t.add_node(pid,'conjunction',value='and',itype='qualifying-clause')
        _graph_qualifying_clause_(t,cid,q1)
        _graph_qualifying_clause_(t,cid,q2)
        return cid
    except AttributeError:
        if cid: t.del_node(cid)

    # TODO: instead of adding the 'word' for each check, add once in beginning?
    # TODO: have to handle cases where graph_thing fails or a hanging node will
    #  be left behind
    qid = None
    try:
        pw,pcls = dd.re_qualifying_clause.search(clause).groups()
        qid = t.add_node(pid,pw)
        if pw == 'from' or pw == 'in': return graph_thing(t,qid,pcls) # a zone
        elif pw == 'other_than': return graph_thing(t,qid,pcls)       # an object
        elif pw == 'with' or pw == 'without':
            # check for ability
            m = dd.re_qual_with_ability.search(pcls)
            if m:
                ob,kw = m.groups()
                if ob:
                    assert(kw == 'landwalk')
                    attr = mtgltag.tag_attr(ob)
                    assert('characteristics' in attr)
                    kw = "landwalk→{}".format(
                        mtgltag.split_align(attr['characteristics'])[1]
                    )
                return t.add_node(qid,'ability',value=kw)

            # check for attribute
            m = dd.re_qual_with_attribute.search(pcls)
            if m:
                # TODO: for now just recombining the op and the value, but
                #  maybe do something else later
                name,op,val = m.groups()
                return t.add_node(qid,'attribute',name=name,value=op+val)

            # attribute2
            # TODO: I don't like this whol approach
            m = dd.re_qual_with_attribute2.search(pcls)
            if m:
                num,xq,attr = m.groups()
                name = mtgltag.tag_val(attr)
                return t.add_node(
                    qid,'attribute',name=name,quantity=num,qualifier=xq
                )

            # check with quantifier name attributes
            m = dd.re_qual_with_attribute_xq.search(pcls)
            if m:
                xq,attr = m.groups()
                return t.add_node(qid,'attribute',quantifier=xq,value=attr)

            # check for lituus object attributes
            m = dd.re_qual_with_attribute_lo.search(pcls)
            if m:
                qual,attr = m.groups()
                return t.add_node(qid,'attribute',qualifier=qual,value=attr)

            # check for counters
            m = dd.re_qual_with_ctrs.search(pcls)
            if m:
                # TODO: will throw error if there is not type attribute
                q,ct = m.group(1),m.mtgltag.tag_attr(m.group(2))['type']
                return t.add_node(qid,'counter',quantity=q,type=ct)

            # check for object (should be abilities)
            m = dd.re_qual_with_object.search(pcls)
            if m: return graph_thing(t,qid,m.group(1))
        elif pw == 'of':
            # attributes
            m = dd.re_qual_of_attribute.search(pcls)
            if m:
                xq,attr,lo = m.groups()
                val = attr if attr else lo
                return t.add_node(qid,'attribute',quantifier=xq,value=val)

            # objects
            m = dd.re_qual_of_object.search(pcls)
            if m: return graph_thing(t,qid,m.group(1))

            # possessives (possessive suffix)
            m = dd.re_qual_of_possessive.search(pcls)
            if m: return graph_thing(t,qid,m.group(1))

            # player own/control
            m = dd.re_qual_of_possessive2.search(pcls)
            if m: return graph_thing(t,qid,m.group(1))
        elif pw == 'that_is' or pw == 'that_are':
            # check for status
            m = dd.re_qual_thatis_status.search(pcls)
            if m: return t.add_node(qid,'status',value=m.group(1))

            # check for attribute
            m = dd.re_qual_thatis_attribute.search(pcls)
            if m:
                # TODO: for now just recombining the op and the value, but
                #  maybe do something else later
                neg,name,val = m.groups()
                if neg: val = "{}{}".format(mtgl.NOT,val)
                return t.add_node(qid,'attribute',name=name,value=val)

            # check for location
            # TODO: only finds [quantifier] [zone] i.e. does expand to meet
            #  zones with preceding players etc
            m = dd.re_qual_thatis_zone.search(pcls)
            if m:
                neg,zn = m.groups()
                cid = None
                if neg: cid = t.add_node(t.add_node(qid,'not'),'on')
                else: cid = t.add_node(qid,'on')
                return graph_thing(t,cid,zn)  # always a zone
    except lts.LituusException as e:
        if e.errno == lts.EPTRN: t.del_node(qid)
    except AttributeError:
        pass
    return None

####
## ACTIONS
####

## KEYWORD ACTIONS

def _graph_ap_thing_test_(t,pid,phrase):
    # attempt to graph parameters as a thing
    try:
        return graph_thing(t,pid,phrase)
    except lts.LituusException:
        return t.add_node(pid,'action-params',tograph=phrase)

def _graph_ap_thing_(t,pid,phrase):
    # attempt to graph parameters as a thing
    try:
        return graph_thing(t,pid,phrase)
    except lts.LituusException:
        return None

def _graph_ap_attach_(t,pid,phrase):
    # attach 701.3 has the form attach [self] to [thing]
    tid = None
    try:
        ob1,ob2 = dd.re_attach_clause.search(phrase).groups()
        tid=graph_thing(t,pid,ob1)
        graph_thing(t,t.add_node(tid,'to'),ob2)
        return tid
    except lts.LituusException:
        # have to check if the first object was graphed but the second failed
        if tid: t.del_node(tid)
    except AttributeError:
        pass
    return None

def _graph_mana_string_(t,pid,phrase):
    try:
        # get the mana symbols and recursively call for conjuctions
        xq,m1,m2,m3 = dd.re_mana_chain.search(phrase).groups()
        if m1 or m2:
            oid = t.add_node(pid,'conjunction',value='or',itype="mana")
            for ms in [m1,m2,m3]:
                if not ms: continue
                _graph_mana_string_(t,oid,ms)
            return oid

        ms = mtgltag.re_mtg_ms.findall(m3)
        mid = t.add_node(pid,'mana',quantity=len(ms),value=m3)
        if xq: t.add_node(mid,'quantifier',value=xq)
        return mid
    except AttributeError:
        return None

## Lituus Actions

def _graph_ap_add_(t,pid,phrase):
    # the simplest is a mana string or mana string conjunction
    if dd.re_mana_check.search(phrase):
        mid = _graph_mana_string_(t,pid,phrase)
        if mid: return mid

    # now have to check for complex phrasing
    # additional number of mana
    try:
        xq,num,cls = dd.re_nadditional_mana.search(phrase).groups()
        mid = t.add_node(pid,'mana',quantity=num)
        t.add_node(mid,'quantifier',value=xq)
        t.add_node(mid,'mana-qualifier',tograph=cls) # TODO
        return mid
    except AttributeError:
        pass

    # {X} clause
    try:
        ms,cls = dd.re_mana_trailing.search(phrase).groups()
        mid = _graph_mana_string_(t,pid,ms)
        t.add_node(mid,'mana-qualifier',tograph=cls) # TODO
        return mid
    except AttributeError:
        pass

    # amount of {X} clause
    try:
        ms,cls = dd.re_amount_of_mana.search(phrase).groups()
        mid = t.add_node(pid,'amount-of')
        _graph_mana_string_(t,mid,ms)
        t.add_node(mid,'mana-qualifier',tograph=cls)
        return mid
    except AttributeError:
        pass

    # that much {x}
    try:
        ms,cls = dd.re_that_much_mana.search(phrase).groups()
        mid = t.add_node(pid,'that-much')
        _graph_mana_string_(t,mid,ms)
        if cls: t.add_node(mid,'mana-qualifier',tograph=cls)
        return mid
    except AttributeError:
        pass

    return None