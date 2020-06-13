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
        graph_line(t,t.add_node(aaid,'activated-effect'),effect)
        if instr:
            graph_phrase(t,t.add_node(aaid,'activated-instructions'),instr)
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
        # TODO: can we make a check for these?
        if graph_replacement_effects(t,pid,line): return
        if graph_apc_phrases(t,pid,line): return
        if dd.re_modal_check.search(line): return graph_modal_phrase(t,pid,line)
        if dd.re_lvl_up_check.search(line): return graph_lvl_up_phrase(t,pid,line)
        if dd.re_sequence_check.search(line): return graph_sequence_phrase(t,pid,line)
        if graph_condition_phrase(t,pid,line): return
        if graph_option_phrase(t,pid,line): return
        if graph_action_clause(t,pid,line): return

        # TODO: at this point how to continue: could take each sentence if more than
        #  one and graph them as phrase and if only sentence, graph each clause (i.e.
        #  comma separated i.e. Goblin Bangchuckers
        # if we get here start by breaking the line into sentences
        ss = [x.strip() + '.' for x in dd.re_sentence.split(line) if x != '']
        if len(ss) > 1:
            for s in ss: graph_phrase(t,pid,s,i+1)
        else:
            if i < 1: graph_phrase(t,t.add_node(pid,'sentence'),line,i+1)
            else: t.add_node(pid,'ungraphed-sentence',tograph=line)

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
            graph_phrase(t,t.add_node(mid,'action'),act)
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
            graph_phrase(t,t.add_node(mid,'action'),act)
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
            graph_phrase(t,t.add_node(mid,'action'),act)
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
            oid = t.add_node(rid,'conjunction',value='or',itype="if-woudd")
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
            graph_phrase(t,t.add_node(mid,'option'),opt)
        return mid
    except AttributeError:
        pass

    # then with instructions (700.2d)
    try:
        # unpack the phrase
        op,num,instr,opts = dd.re_modal_phrase_instr.search(line).groups()

        # add a modal node and nodes for each of the choices
        mid = t.add_node(pid,'modal')
        cid = t.add_node(mid,'choose',number=op+num if op else num)
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

    # then timing
    #try:
    #    time,phrase = dd.re_sequence_time.search(line).groups()
    #    tid = t.add_node(pid,'timing')
    #    graph_phrase(t,t.add_node(tid,'when'),time)
    #    graph_phrase(t,tid,phrase)
    #    return tid
    #except AttributeError:
    #    pass

    return None

####
## CONDITION PHRASES
####

def graph_condition_phrase(t,pid,line):
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

####
## OPTIONAL PHRASES
####

def graph_option_phrase(t,pid,phrase):
    """
    determines how to graph the condition phrase in line
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
        #oid = t.add_node(pid,'option')
        #mid = t.add_node(oid,'may')
        #graph_thing(t,mid,ply)
        #graph_phrase(t,mid,act1)
        #graph_phrase(t,t.add_node(oid,'as-though'),act2)
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
    try:
        # determine if there is a conjunction of actions or a singleton action
        thing = cnd = aw1 = act1 = aw2 = act2 = None
        m = dd.re_anded_action_clause.search(phrase)
        if m: thing,aw1,act1,aw2,act2 = m.groups()
        else:
            m = dd.re_action_clause.search(phrase)
            if m: thing,cnd,aw1,act1 = m.groups()
            else: return None # TODO: this covers up improperly passed phrases

        # set up nid and aid as None
        nid = aid = None

        try:
            # now set up of singleton and graph the thing if present
            acs = [(aw1,act1)]
            if cnd:
                nid = t.add_node(pid,cnd)
                aid = t.add_node(nid,'action')
            else: aid = t.add_node(pid,'action')
            if thing: graph_thing(t, aid, thing)

            # if there is a conjunction add a 'and' node and append the 2nd action
            if aw2:
                aid = t.add_node(aid,'conjunction',value='and',itype="action")
                acs.append((aw2,act2))

            # graph the action(s)
            for aw,act in acs:
                awid = t.add_node(aid,mtgltag.tag_val(aw))
                if act: t.add_node(awid,'action-params',tograph=act)
        except lts.LituusException as e:
            if e.errno == lts.EPTRN:
                if nid: t.del_node(nid)
                else: t.del_node(aid)
            else:
                raise
            return None
        else:
            return aid
    except AttributeError:
        pass

    return None

def graph_thing(t,pid,clause):
    """
    Graphs the thing under node pid
    :param t: the tree
    :param pid: the parent id
    :param clause: the clause
    :return: the player node id
    """
    # TODO: if we have just a self ref, use self as the value
    # TODO: should we combine suffix with the stem if present?
    # could have a qst phrase or a possesive phrase have to check both
    try:
        # 'unpack' the phrase
        n,xq,st,th1,conj,xq2,th2,poss,pr = dd.re_qst.search(clause).groups()
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

        # graph any trailing posession clauses and.or prepositions
        if poss:
            try:
                ply,wd = dd.re_possession_clause.search(poss).groups()
                lbl = 'owned-by' if wd == 'own' else 'controlled-by'
                graph_thing(t,t.add_node(eid,lbl),ply)
            except AttributeError:
                raise lts.LituusException(lts.EPTRN,"{} is not a possession".format(ctlr))
        if pr: graph_phrase(t,t.add_node(eid,'with'),pr)

        # and return the thing node id
        return eid
    except KeyError:
        print(clause)
        raise
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
    # untag the obj and create an object node using the tag value as the label
    # if it is a non mtg object, add an attribute specifying the type, then
    # pull any references out the attributes and put in the main node
    tid,val,attr = mtgltag.untag(obj)
    oid = t.add_node(pid,val)
    if tid != 'ob': t.add_attr(oid,'type',mtgl.TID[tid])
    if 'ref' in attr:
        t.add_attr(oid,'ref-id',attr['ref'])
        del attr['ref']
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
    # subcost could be a mtg symbol (a mana string, E, T or Q) or it could be
    # an action clause i.e. a action word like sacrifice or pay and the parameters
    # or a conjunction i.e. or of symbols
    sid = t.add_node(pid,'subcost')
    if mtgltag.tkn_type(sc) == mtgltag.MTGL_SYM: t.add_attr(sid,'value',sc)
    elif dd.re_is_act_clause.search(sc): graph_clause(t,sid,sc)
    else: t.add_attr(sid,'anamolie',sc)

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
    return dd.re_act_check.search(line) and not dd.re_lvl_up_check.search(line)