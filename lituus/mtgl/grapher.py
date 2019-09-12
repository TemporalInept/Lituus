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
__version__ = '0.0.4'
__date__ = 'September 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.mtgt as mtgt
import lituus.mtgl.list_util as ll
import lituus.mtgl.mtgltag as tag

def graph(mtxt,ctype='other'):
    """
     graphs the mtgl parsed oracle text of card
    :param mtxt: the mtgl parsed oracle text
    :param ctype: card type one of:
     'spell' = the card is an Instant or Sorcery
     'saga' = the card is a Saga
     'other' = card type plays no role in graphing
    :return: a networkx rooted ordered DAG parse represenation
    """
    # create an empty/null tree and get the root node id
    t = mtgt.MTGTree()
    parent = t.root

    for i,line in enumerate(mtxt):
        try:
            graph_line(t,t.add_node(parent,'line'),line,ctype)
        except mtgt.MTGTException as e:
            raise mtgl.MTGLGraphException(e)
        except Exception as e:
            raise mtgl.MTGLException("Unknown Error ({})".format(e))

    # return only the networkx tree (currently due to pickling issues with
    # self-defined classes)
    return t.tree

def graph_line(t,pid,line,ctype='other'):
    """
     converts the mtgl tokens in line to tree format
    :param t: the tree (MTGTree)
    :param pid: the parent id of this subtree
    :param line: the mtgl tokens
    :param ctype: card type one of:
     'spell' = the card is an Instant or Sorcery
     'saga' = the card is a Saga
     'other' = card type plays no role in graphing
    """
    # three basic line types:
    # 1) 207.2c "appears in italics at the beginning of some abilities". but is
    #  not further defined. Heuristically, an ability word line starts with an
    #  ability word, contain a long hyphen and ends with a 'line'
    # 2) 702.1 "object lists only the name of an ability as a keyword" Again,
    #  heuristically, a keyword line: contains one or more comma seperated keyword
    #  clauses.
    # 3) ability line (not a keyword or ability word line) Four general types
    # 112.3a Spell, 112.3b Activated, 112.3c Triggered & 112.3d static
    # We also have (not specifically lsited in 112 but are handled here)
    #  e) 700.2 Modal spell or ability
    #  f) 710 Leveler Cards
    #  g) 714 Saga Cards
    #  h) 113.1a Granted abilities (preceded by has,have,gains,gain and
    #   double quoted
    if tag.is_ability_word(line[0]): graph_aw_line(t,pid,line)
    elif is_kw_line(line): graph_kw_line(t,pid,line)
    else:
        # (112.3) add an ability-line or 'ability-clause' node
        isline = pid.split(':')[0] == 'line'
        if isline: lid = t.add_node(pid,'ability-line')
        else: lid = pid

        if modal_type(line): graph_modal_line(t,lid,line) # e
        elif is_level(line): graph_level_line(t,lid,line) # f
        elif ctype == 'saga': graph_saga_line(t,lid,line) # g
        elif is_activated_ability(line): graph_activated_ability(t,lid,line)
        elif tag.is_tgr_word(line[0]): graph_triggered_ability(t,lid,line)
        elif ctype == 'spell': graph_clause(t,t.add_node(lid,'spell-ability'),line)
        else:
            # graph_line may be called by intermediate nodes and this is the
            # default handling of any line/clause that cannot be classified as
            # one of the above. But, static-abilities do not apply in all cases
            # 112.3d "...create continuous effects..." therefore, if this is not
            # a true line, it will be classified as an effect
            if isline: nid = t.add_node(lid,'static-ability')
            else: nid = t.add_node(lid,'effect-clause') #TODO: need a better name
            graph_clause(t,nid,line)

def graph_aw_line(t,pid,line):
    """
     graphs the ability-word line at parent id pid of tree t
    :param t: the tree (MTGTree)
    :param pid: parent id of this subtree
    :param line: the line to graph (an ability-word line

    ability word 207.2c have no definition in the comprehensive rules but based
    on card texts, follow simple rules of the form
       aw<ability-word> '—' ability definition.
    where the ability definition is itself a line
    """
    # add the aw-line, ability-word and ability-word-definition
    awid = t.add_node(pid,'aw-line')
    t.add_node(awid,'ability-word',word=tag.untag(line[0])[1])
    graph_line(t,t.add_node(awid,'ability-word-definition'),line[2:])

def graph_kw_line(t,pid,line):
    """
     graphs the keyword line line at parent id pid of tree t
    :param t: the tree (MTGTree)
    :param pid: the parent id of this subtree
    :param line: the line to graph (must be a keyword line)
    """
    # add a kw line node
    kwlid = t.add_node(pid,'kw-line')

    # get the keyword clauses NOTE: kw_clauses modifies the clause such that
    # all keywords will be the first token in the clause
    for kwc in kw_clauses(line):
        # add a kw-clause node.
        kwid = t.add_node(kwlid,'keyword-clause')

        # split the keyword clause into keyword and parameters
        kw = tag.untag(kwc[0])[1]
        ps = kwc[1:]

        # add the keyword node
        t.add_node(kwid,'keyword',word=kw)

        # handle 'special' and/or variation keywords first
        if kw == 'equip' and ps and tag.is_mtg_obj(ps[0]):
            # 702.6s Equip [quality] creature [cost]
            # [quality] and creature will be merged an object tag
            t.add_node(kwid,'quality',quality=ps[0])

            # graph the cost/subcosts
            graph_cost(t,t.add_node(kwid,'keyword-cost'),ps[1:])
        elif kw == 'hexproof' and\
                ll.matchl(ps,['pr<from>',tag.is_quality],stop=0) == 0:
            # 702.11d Hexproof from [quality]. 3 cards have this
            t.add_node(kwid,'from',quality=ps[1])
        elif kw == 'protection':
            # 702.16a Protection from [quality] (characteristic, player etc)
            # 702.16g Protection from [quality A] and from [quality B]
            # 702.16h/702.16i Protection from (all [characteristic])/everything
            # get the qualities in the parameters, if there is one, create a node
            # otherwise, create a conjunction of qualities
            qs =_pro_from_(ps)
            if len(qs) == 1: t.add_node(kwid,'from',quality=qs)
            else:
                cid = t.add_node(
                    kwid,'conjunction',coordinator='and',item_type='quality'
                )
                for q in qs: t.add_node(cid,'from',quality=q)
        elif kw == 'cycling' and tag.is_mtg_obj(ps[0]):
            # 702.28e [Type]cycling [cost] (Function kw_clauses rewrites
            # this as kw<cycling> [type] [cost]
            # NOTE: due to the parser's implementation of rule 109.2, the
            # [type] is tagged as a permanent vice a card as it should be
            # fix the issue here before adding to tree
            t.add_node(
                kwid,'cycling-type',type=tag.retag('ob','card',tag.untag(ps[0])[2])
            )

            # get the cost/subcosts
            graph_cost(t,t.add_node(kwid,'keyword-cost'),ps[1:])
        elif kw == 'kicker' and 'op<⊕>' in ps:
            # 702.32b Kicker [cost 1] and/or [cost 2]
            # all costs should be mana costs but just in case
            k1,_,k2 = ll.splitl(ps,ps.index('op<⊕>'))
            graph_cost(t,t.add_node(kwid,'keyword-cost'),k1)
            graph_cost(t,t.add_node(kwid,'keyword-cost'),k2)
        elif kw == 'affinity':
            # 702.40a Affinity for [text] (i.e. object)
            t.add_node(kwid,'for',object=ps[-1])
        elif kw == 'modular' and ll.matchl(ps,[mtgl.HYP,'kw<modular>']) == 0:
            # rule 702.43c (arcbound wanderer) has the form
            # Modular-Sunburst where Sunburst is a stand-in for N
            t.add_node(kwid,'n',value='sunburst')
        elif kw == 'splice':
            # 702.46a Splice onto [subtype] [cost]
            t.add_node(kwid,'onto',subtype=ps[1])

            # add a cost node to the tree and all subcost(s) under it
            graph_cost(t,t.add_node(kwid,'keyword-cost'),ps[2:])
        elif kw in KW_N_COST:
            # 702.61a Suspend N <long-hyphen> [cost]
            # 702.76a Reinforce N <long-hyphen> [cost]
            # 702.112a Awaken N <long-hyphen> [cost]
            # add the n
            t.add_node(kwid,'n',value=tag.untag(ps[0])[1])

            # skipping the long hyphen, add a cost node to the tree
            graph_cost(t, t.add_node(kwid,'keyword-cost'),ps[2:])
        elif kw == 'forecast':
            # 702.56a Forecast <long-hyphen> [Activated Ability]
            aid = t.add_node(kwid,'sub-line')
            graph_line(t,aid,ps[1:])
        elif len(ps) > 0:
            # singletons and special cases/variations have been added
            # three types remain, Object/Quality, N, Cost
            if tag.is_number(ps[0]):
                t.add_node(kwid,'n',value=tag.untag(ps[0])[1])
                if ll.matchl(ps,[tag.is_variable,',','where'],stop=0) == 0:
                    # Thromok the Insatiable has Devour X, the only card I've
                    # found with a keyword and variable for n
                    t.add_node(kwid,'clause',tokens=ps[3:])
            elif tag.is_mtg_obj(ps[0]):
                # TODO: check for need to collate, also should we continue
                #  to constrain to obj and not Thing
                t.add_attr(t.add_node(kwid,'object'),'object',ps[0])
                if len(ps) > 1: graph_clause(t,kwid,ps[1:])
            else:  # should be a cost
                # TODO: what if it isnt a cost?
                graph_cost(t,t.add_node(kwid, 'keyword-cost'),ps)

def graph_modal_line(t,pid,line):
    """
     700.2 graphs a modal spell/line in tree t at parent id = pid
    :param t: the tree
    :param pid: parent id
    :param line: the list of tokens to graph
    """
    # get the modal type and set up the modal node
    mtype = modal_type(line)
    mid = t.add_node(pid,'modal')

    # Some modals require an opp to choose - if so extract it and add
    ply = None
    if tag.is_player(line[0]):
        #t.add_node(mid,'player',player=line[0])
        ply = line[0]
        line = line[1:]

    # several modal preambles (see modalN definitions) regardless, each will
    # have instruction & modes (instruction will be the length of the matching
    # pattern).
    i = line.index(mtgl.BLT)
    instr = line[:i]
    modes = line[i:]

    # Add instruction & choose node. the 'choose' format is dependent on the
    # modal type.
    iid = t.add_node(mid,'instruction')
    if ply: t.add_node(iid,'player',player=ply)
    if mtype == 1 or mtype == 2:
        # these are chosen at time of cast or activation and tell us how
        # many choices can be made (n) and if the same mode can be chosen
        # more than once (repeatable)
        rep = 'repeatable' if mtgl.PER in instr else 'not-repetable'
        t.add_node(iid,'choose',n=tag.untag(instr[1])[1],option=rep)
    elif mtype == 3:
        # multiple options 1 or more can be chose
        t.add_node(iid,'choose',n=mtgl.GE+'1',option='one or both')
    elif mtype == 4:
        # "as enters.." choose one of two options. There are only 5 cards
        # 'Seige' enchantments that fit this modal preamble and the choices
        # khans or dragons is already known but we'll code for the possibility
        # of future cards using the same preamble (NOTE: in siege enchantments,
        # dragons is tagged as a characteristice If future cards are released that
        # match this preamble the below could throw errors)
        # TODO: for now we are graphing the replacement "as NAME enters the
        #  battlefield clause under the instruction node of the modal node -
        #  this clause should really be the parent of the modal
        c1 = instr[6] # first choice
        c2 = instr[8] # second choice
        if tag.is_mtg_obj(c1): c1 = tag.untag(c1)[2]['characteristics']+'s'
        if tag.is_mtg_obj(c2): c2 = tag.untag(c2)[2]['characteristics']+'s'
        graph_clause(t,iid,ll.splitl(instr,instr.index('xa<choose>'))[0])
        t.add_node(iid,'choose',n=1,option1=c1,option2=c2)
    elif mtype == 5:
        # an event based decreasing number of options
        t.add_node(iid,'choose',n=1,option='has not been chosen')
    elif mtype == 6:
        # one card vindictive lich
        t.add_node(iid,'choose',n=mtgl.GE+'1',option='one mode per player')

    # each mode clause will be '•', [additional tokens], ... tkns ... , '.'
    ms = []
    prev = 0
    for i in ll.indicesl(modes,mtgl.BLT):  # looking for left splits
        if prev == i == 0: continue        # the first slice is the empty list
        ms.append(modes[prev+1:i])
        prev = i
    ms.append(modes[prev + 1:])

    # if the modal preamble is type 3, we have to do additional processing
    # before graphing
    for m in ms:
        moid = t.add_node(mid,'mode')
        if mtype == 4:
            r,_,line = ll.splitl(m,m.index(mtgl.HYP))
            if tag.is_mtg_obj(r[0]): r = tag.untag(r[0])[2]['characteristics']+'s'
            else: r = r[0]
            t.add_attr(moid,'option',r)
        else: line = m
        graph_line(t,moid,line)

def graph_level_line(t,pid,line):
    """
     graphps a level symbol 710.2 in line at parent-id pid of tree t
    :param t: the tree
    :param pid: parent of this subtree
    :param line: the line to graph
    """
    # Rules 710.2a (710.2b) state that leveler card lines will have the format
    #  LEVEL N1-N2 (or N3+) [Abilities] [P/T]
    # However, in the oracle text, all leveler cards follow the format
    #  LEVEL N1-N2 (or N3+) [P/T] [Abilities]

    # level up lines are treated differently in the tagger where <break> tokens
    # have replaced newlines in each line. These <break> tokens delimit the
    # 'clauses' of the level striation line

    # add a level striation, then children level symbol node, level p/t node
    mid = t.add_node(pid,'level-striation') # main node
    lsid = t.add_node(mid,'level-symbol')
    lpid = t.add_node(mid,'level-pt')

    # the level symbol will be in the first clause and will have the format
    # level nu<N1>-nu<N2> (or nu<3>+)
    lu,_,line = ll.splitl(line,line.index('<break>'))
    lsym = lu[1].split('-')
    if len(lsym) == 2:
        r = "{}-{}".format(tag.untag(lsym[0])[1],tag.untag(lsym[1])[1])
    else: r = "{}+".format(tag.untag(lsym[0])[1])
    t.add_attr(lsid,'range',r)

    # the level's P/T will be in the next clause (the tagger has tagged this as 'ls'
    # vice 'ch' in order to preserve it through the parser's processing
    try:
        lp,_,line = ll.splitl(line,line.index('<break>'))
    except ValueError:
        # nothing remains after the p/t
        lp = line
        line = []
    pt = tag.untag(lp[0])[2]
    t.add_attr(lpid,'p/t',pt['val'])

    # before moving to next clause(s), we have to take care of some artifacts
    # from the tagger related to leveler cards
    # 1) replace double periods with a single period
    # 2) replace KEYWORD PERIOD with just KEYWORD
    line = ll.replacel(line,[mtgl.PER,mtgl.PER],[mtgl.PER])
    if ll.matchl(line,[tag.is_keyword,mtgl.PER],stop=0) == 0: line = line[:-1]

    # the next clause can be keyword(s), ability, keyword(s) and ability or none
    # check if we have keywords, if so build the 'keyword line'
    laid = None
    kws = []
    i = ll.matchl(line,[tag.is_keyword])
    while i > -1:
        kws.extend(line[:i+1])
        line = line[i+1:]
        i = ll.matchl(line,[tag.is_keyword])

    # if there is a keyword line, create the level abilities node, graph it &
    # clean up any artifacts
    if kws:
        laid = t.add_node(mid,'level-abilities')
        graph_kw_line(t,laid,kws)
        #if line == ['<break>',mtgl.PER] or line == [mtgl.PER]: line = []

    # anything remaining is an ability, add level abilities node if necessary
    # and graph as a line
    if line:
        if not laid: laid = t.add_node(mid,'level-abilities')
        graph_line(t,laid,line)

def graph_saga_line(t,pid,line):
    """
     714.1 graphs a saga line in tree t with parent-id pid
    :param t: the tree
    :param pid: parent-id to graph under
    :param line: the tokens making up the saga line
    """
    # create the subtree node, a saga ability & split the line into the chapter
    # symbol(s) and effect
    sid = t.add_node(pid,'saga-ability')
    cs,_,effect = ll.splitl(line,line.index(mtgl.HYP))

    # the chapter symbol rN, (714.2) is a roman numeral and may be singleton
    # rN-[Effect] (71.2b) or multiple rN1,rN2-[Effect] (714.2c), if multiple,
    # remove the comma token
    if mtgl.CMA in cs: cs = [cs[0],cs[2]]

    # add the chapter node with chapter symbols, then graph the effect
    t.add_node(sid,'chapter',symbol=", ".join(cs))
    graph_line(t,t.add_node(sid,'effect'),effect)

def graph_activated_ability(t,pid,line):
    """
     602.1 graphs an activated ability line given the tree t and parent id pid
     where spell denotes whether the owning card is an Instant or Sorcery
    :param t: the tree
    :param pid: the parent id of this subtree
    :param line: the line to graph
    """
    # 602.1 activated ability
    #  [Cost]:[Effect.][Activation instructions (if any)]
    # the rules do not specify that the Effect ends at the first period
    # or if the activation instructions contain more than one sentence.
    # Rule 602.1b vaguely states "Some text after the colon ... states
    #  instructions..." There is also no specific rules on the structure
    # of effects and activation instructions. Therefore we make several
    # assumptions using Acidic Dagger as a guideline:
    #  1. The effect ends at the first period following the color
    #  2. The effect is itself a line i.e. it may be a triggered ability
    #  3. Activating instructions may be more than one sentence each sentence
    #   is also a line i.e. it may be triggered

    # start with an activated-ability node (under the ability-line-node,
    # split the line into cost & remainder, graph the cost & add an effect node
    aaid = t.add_node(pid,'activated-ability')
    cost,_,rem = ll.splitl(line,line.index(':'))
    graph_cost(t,t.add_node(aaid,'activated-ability-cost'),cost)
    eid = t.add_node(aaid,'activated-ability-effect')

    # if it's modal, graph as a line under effect
    if modal_type(rem): graph_line(t,eid,rem)
    else:
        # TODO: hanlding periods followed by double quotes is too hacky
        #  figure out a better way of doing this
        # otherwise split remainder into effect, activating instruction(s)
        try:
            effect,_,ais = ll.splitl(rem,rem.index(mtgl.PER))
            effect += [mtgl.PER] # add the period back
        except ValueError:
            effect = rem
            ais = []

        # graph effect as a line, add period back & check for hanging double-quote
        ds = ll.indicesl(effect,mtgl.DBL)
        if len(ds)%2 == 1:
            # have an odd number of double quotes in eff
            i = ll.rindexl(ais,mtgl.DBL)
            effect += ais[:i+1]
            ais = ais[i+1:]
        graph_line(t,eid,effect)

        # then any activating instructions - split the instructions by period
        # TODO: is the below double quote check still necessary?
        aiid = None
        prev = 0
        for i in ll.indicesl(ais,mtgl.PER): # looking for right splits
            # have to look at periods followed by a double quote
            left = 1
            try:
                if ais[i+1] == mtgl.DBL: left = 2
            except IndexError:
                pass
            if not aiid: aiid = t.add_node(aaid,'activated-ability-instructions')
            graph_line(t,t.add_node(aiid,'instruction'),ais[prev:i+left])
            prev = i+left # skip the period (and double quote)

def graph_triggered_ability(t,pid,line):
    """
     graphs the triggered ability on line at the parent-id pid of the tree t
    :param t: the tree
    :param pid: parent-id
    :param line: the list of tokens
    """
    # triggered ability per 603.1 have the format
    #  [Trigger word][Trigger condition/event,[effect].[Instructions]
    # all triggered abilties start with one of the trigger words (at,when,whenever)
    # (though not necessarily at the beginning of a line)

    # add a triggered-ability node, & split the line into word, cond, eff & instr
    taid = t.add_node(pid,'triggered-ability')
    word,cond,effect,instr = ta_clause(line)

    # add the trigger word node and graph the condition as a clause
    t.add_node(taid,'triggered-ability-word',word=tag.untag(word)[1])
    graph_clause(t,t.add_node(taid,'triggered-ability-condition'),cond)

    # for effect we add the node, then check if it is modal or not
    eid = t.add_node(taid,'triggered-ability-effect')

    # for modal, we need to recombine effect and instructions
    # TODO: this is nearly the same as activated_ability can we subfunction it
    if modal_type(effect+instr): graph_line(t,eid,effect+instr)
    else:
        # NOTE: function ta_clause takes care of hanging double quotes betw/
        # effect and instruction, no need to check here
        # graph the effect as a line
        graph_line(t,eid,effect)

        # if there are instructions, split them by periods and add to node.
        # NOTE: there may be hanging double quotes when instructions is
        # split
        #if instr: iid = t.add_node(taid,'triggered-instructions')
        iid = None
        prev = 0
        for i in ll.indicesl(instr,mtgl.PER): # looking for right splits
            # have to look at periods followed by a double quote
            left = 1
            try:
                if instr[i+1] == mtgl.DBL: left = 2
            except IndexError:
                pass
            if not iid: iid = t.add_node(taid,'triggered-ability-instructions')
            graph_line(t,t.add_node(iid,'instruction'),instr[prev:i+left])
            prev = i+left # skip the period

def graph_clause(t,pid,tkns):
    """
     converts the mtgl tkns of a clause to tree format
    :param t: the tree (MTGTree)
    :param pid: the parent id of this subtree
    :param tkns: the mtgl tokens
    """
    cls = []
    skip = 0
    for i,tkn in enumerate(tkns):
        # ignore any already processed tokens
        if skip:
            skip -= 1
            continue

        if tag.tkn_type(tkn) == tag.MTGL_PUN:
            # assume that any punctuation we get here signifies a separation
            # between clauses
            if cls:
                t.add_node(pid,'clause',tkns=cls)
                cls = []

            # check for
            #  double quotes - grab the quoted tokens & graph them
            #  bullet - graph as a modal spell
            #  otherwise add the punctuation
            if tkn == mtgl.DBL:
                dbl = tkns[i+1:ll.indexl(tkns,mtgl.DBL,i)]
                graph_line(t,t.add_node(pid,'quoted-clause'),dbl)
                skip = len(dbl) + 1 # skip the right double quote
            else: t.add_node(pid,'punctuation',symbol=tkn)
        elif tag.tkn_type(tkn) == tag.MTGL_SYM:
            if cls:
                t.add_node(pid,'clause',tkns=cls)
                cls = []
            if tag.is_mana_string(tkn): t.add_node(pid,'mana-string',mana=tkn)
            else: t.add_node(pid,'mtg-symbol',symbol=tkn)
        elif tag.is_loyalty_cost(tkn) and len(tkns) == 1:
            # extract the parameters adding only +/- and the digit/variable
            if not tkn.startswith('nu'):
                s = tkn[0]
                tkn = tkn[1:]
            else: s = ''
            s += tag.untag(tkn)[1]
            t.add_node(pid,'loyalty-symbol',symbol=s)
        elif tag.is_keyword_action(tkn):
            # in most cases, the keyword action gets its parameters from the
            # tokens following it. However, a few require some/all of the tokens
            # preceding it. Regardless, cls will be claused out
            skip = graph_keyword_action(t,pid,cls,tkn,tkns[i+1:])
            cls = []
        elif tag.is_lituus_act(tkn):
            # special 'action' words we have identified as being common throughout
            # mtg oracle texts. Same as keyword actions where a few actions require
            # preceding tokens to grab their parameters
            skip = graph_lituus_action(t,pid,cls,tkn,tkns[i+1:])
            cls = []
        else:
            cls.append(tkn)

    # add any opened clause
    if cls: t.add_node(pid,'clause',tkns=cls)

def graph_keyword_action(t,pid,cls,kwa,tkns):
    """
     graphs a keyword action and associated parameters into tree t at parent
     id pid. the parameters cls, kwa and tkns could be combined
     cls+[kwa]+tkns to reconstruct a line
    :param t: the tree
    :param pid: parent id in the tree
    :param cls: previous tokens that haven't been added to the tree
    :param kwa: untagged keyword-action token
    :param tkns: next tokens that haven't been added to the tree
    :return: cls, skip such that cls is the new cls and skip is the number
     of items in tkns that have been processed
    """
    # extract the actual keyword-action
    v = tag.untag(kwa)[1]

    # keyword-actions follow rules similar to keywords i.e.
    #     keyword-action object
    # but there are many cards that reference that keyword-action. For example,
    # Adapt (701.42) is followed by a number. But Biomancer's Familiar refernces
    # the keyword-action Adapt in "The next time target creature adapts this
    # turn..." so for each keyword-action we check for the rule and if
    # it is not found, we assume the card references the keyword-action. For
    # now, in most cases it still graphed as a keyword action albeit without
    # any associated parameters

    # in most cases associated parameters follow the keyword-action. However,
    # there are some (explore and fight) which are preceded by some of their
    # associated parameters and exchange in some cases will also be preceded
    # by parameters
    if v == 'explore':
        # 701.39a Object ka<explore> in this case, object precedes
        # the keyword-action, meaning it has already been pushed
        # onto cls.
        ob = None  # havent seen any explore not preceded by an obj
        if cls and tag.is_thing(cls[-1]): ob = cls.pop()

        # add any open clauses
        if cls: t.add_node(pid,'clause',tkns=cls)

        # then the kwa clause node & sub-nodes
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v)
        if ob: t.add_node(kwid,'object',object=ob)

        # return
        return 0

    if v == 'fight':
        # fight 701.12 ob->creature ka<fight> ob->creature
        skip = 0
        o1 = o2 = None
        if cls and tag.is_thing(cls[-1]): o1 = cls.pop()
        if tkns and tag.is_thing(tkns[0]):  # could be an object or xo<it>
            o2 = tkns[0]
            skip = 1

        # add any open clauses
        if cls: t.add_node(pid,'clause',tkns=cls)

        # then the kwa clause node & sub-nodes
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v)
        if o1: t.add_attr(t.add_node(kwid,'object'),'object-1',o1)
        if o2: t.add_attr(t.add_node(kwid,'object'),'object-2',o2)

        return skip

    if v == 'exchange': return graph_kwa_exchange(t,pid,cls,tkns)

    # remaining keyword-actions have parameters that follow the word. Add any
    # open clauses then add a kwa clause and a keyword-action node
    if cls: t.add_node(pid,'clause',tkns=cls)
    kwid = t.add_node(pid,'keyword-action-clause')
    t.add_node(kwid,'keyword-action',word=v)
    skip = 0

    if v == 'search':
        # 701.18a search zone for card
        # ka<search> ZONE pr<for> card
        if ll.matchl(tkns,[tag.is_zone,'pr<for>',tag.is_mtg_obj],stop=0) == 0:
            t.add_node(kwid,'zone',zone=tkns[0])
            t.add_node(kwid,'for',card=tkns[2])
            skip = 3
    elif v == 'shuffle': skip = graph_kwa_shuffle(t,kwid,tkns)
    elif v == 'double': skip = graph_kwa_double(t,kwid,tkns)
    elif v == 'vote':
        # 701.31a vote for one choice
        # the keyword-action is always followed by a for
        simple = ['pr<for>',tag.is_mtg_obj,'or',tag.is_mtg_obj]
        embedded = ['pr<for>',tag.is_mtg_obj]
        if ll.matchl(tkns,simple,stop=0) == 0:
            # simple case chocies are opt1 or opt2
            t.add_node(kwid,'option',choices=[tkns[1],tkns[3]])
            skip = 4
        elif ll.matchl(tkns,embedded,stop=0) == 0:
            # the choices are embedded in the characterisitics of
            # the object or as in one case (Council's Judgement)
            # the choices are implied depending on the game state
            cs = tkns[1]
            ps = tag.untag(cs)[2]
            try:
                if mtgl.OR in ps['characteristics']:
                    cs = ps['characteristics'].split(mtgl.OR)
            except KeyError:
                pass
            t.add_node(kwid,'options',choices=cs)
            skip = 2
    elif v == 'meld':
        # 701.36a meld ob (however ob is always xo<them>)
        assert(tkns and tkns[0] == 'xo<them>')
        t.add_node(kwid,'pair',pair=tkns[0])
        skip = 1
    elif v in KWA_OBJECT: # keyword actions of the form keyword-action ob (or Thing)
        # collate will determine what object or objects to use, and create a
        # rootless subtree. Otherwise, None will be returned
        nid,skip = collate(t,tkns)
        if nid: t.add_edge(kwid,nid)
    elif v in KWA_N:
        # ka<KEYWORD-ACTION> N
        try:
            if tag.is_number(tkns[0]):
                t.add_node(kwid,'n',value=tag.untag(tkns[0])[1])
                skip = 1
        except IndexError:
            pass

    return skip

def graph_kwa_exchange(t,pid,cls,tkns):
    """
     because exchange has so many variations, it is handled here.
    :param t: the tree
    :param pid: the id of the current node
    :param cls: previously seen tokens
    :param tkns: the list of tokens immediately following ka<shuffle>
    :return: the skip number
    """
    # 701.10b exchange control of permanents, 701.10c exchange of
    # life total(s), 701.10f exchange zones, 701.10g exchange numerical
    # values
    # TODO: I have not seen legal cards that instruct
    #  701.10d exchange cards in one zone with cards in another zone

    # define our phrase matchs here
    #  cobs = 'control of objects' and seperated
    #  cobe = 'control of objects' embedded
    #  cobe_edge 'control of objects' embedded edge case
    #  lt = 'life totals'
    #  ltch = 'life total with obj's characteristic'
    #  val_edge = (Seren Master) in order to hopefully expand if
    #   other similar edge cases arise, we use thing vice mtg_boj
    #   for matching
    # NOTE: cobe will match everything cobs does so cobs must be
    #  matched first
    cobs = ['xc<control>','of',tag.is_mtg_obj,'and',tag.is_mtg_obj]
    cobe = ['xc<control>','of',tag.is_mtg_obj]
    cobe_edge = ['xc<control>','of','the',tag.is_mtg_obj]
    lt = ['xc<life>','totals','pr<with>',tag.is_player]
    ltch = [
        tag.is_player,'xc<life>','total','pr<with>',
        tag.is_mtg_obj,tag.is_mtg_char
    ]
    val_edge = [
        tag.is_thing,tag.is_mtg_char,'and','the',
        tag.is_mtg_char,'of',tag.is_thing
    ]
    v = 'exchange'

    if ll.matchl(tkns,[tag.is_zone],stop=0) == 0:
        # 701.10d exchange cards in one zone w/ cards in another zone
        # go ahead and add cls, then the kwa clause and kwa node, then
        # the kwa clause and subsequent nodes
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='zone')

        # the 2 zones should be anded and a player should be specified
        _, zs, ps = tag.untag(tkns[0])
        zs = zs.split(mtgl.AND)
        assert(len(zs) == 2)
        assert('player' in ps)

        # recombine and add the nodes
        t.add_node(kwid,'what',zone=tag.retag('zn',zs[0],ps))
        t.add_node(kwid,'with',zone=tag.retag('zn',zs[1],ps))

        # we'll skip the zone
        return 1
    elif ll.matchl(tkns,cobs,stop=0) == 0:
        # 701.10b is always worded exchange control of. here the
        # objs being exchanged are 'and' seperated i.e. ob1 and ob2
        # we no longer need cls, add it, then the kwa etc
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='control')
        t.add_attr(t.add_node(kwid,'what'),'object',tkns[2])
        t.add_attr(t.add_node(kwid,'with'),'object',tkns[4])
        return 5
    elif ll.matchl(tkns,cobe,stop=0) == 0 or ll.matchl(tkns,cobe_edge,stop=0) == 0:
        # 701.10b (same as above) but here, the objects are embedded.
        # Have one edge juxtaposition which has a preceding 'the'
        # go ahead and add cls, kwa clause and kwa node
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='control')

        # check for edge case
        if tkns[2] == 'the':
            t.add_node(kwid,'what',objects=tkns[3])
            skip = 4
        else:
            t.add_node(kwid, 'what', objects=tkns[2])
            skip = 3
        return skip
    elif ll.matchl(tkns,lt,stop=0) == 0:
        # 701.10c exchange life totals
        # do not need the cls, go ahead and add then kwa etc
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='life')
        t.add_node(kwid,'who',player=tag.retag('xp','you',{}))
        t.add_node(kwid,'with',player=tkns[3])
        return 4
    elif tkns == ['xc<life>', 'totals']:
        # 701.10c exchange life totals but in this case the 'who'
        # players are listed prior i.e. have already been added to
        # cls
        # TODO: this is bad, when punctation is added back in we
        #  can expect a period or other punctuation to end this
        #  clause

        # have to pop the players off of cls before adding it
        assert cls  # cls shouldn't be empty
        ply = cls.pop()
        if cls: t.add_node(pid,'clause',tkns=cls)

        # and now the kwa clause and nodes
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='life')
        t.add_node(kwid,'who',players=ply)
        return 2
    elif ll.matchl(tkns,ltch,stop=0) == 0:
        # 701.10g exchange numerical values. So far have only seen
        #  three cards with this specific value exchange which is
        # exchange a life total with the toughness of a creature
        # do not need the cls, go ahead and add then kwa etc
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='value')

        # TODO: see 188
        # add life total to player as a meta-charactersitic and
        # retag before adding the kwa subnodes
        _,pv,pps=tag.untag(tkns[0])
        assert('meta' not in pps)  # will trigger if 188 is fixed
        pps['meta'] = 'life'
        t.add_node(kwid,'what',value=tag.retag('xp',pv,pps))

        # TODO: see 188
        # add the the characteristic as as a meta-charactersitic and
        # retag before addint the kwa subnodes
        _,ov,ops = tag.untag(tkns[4])
        assert('meta' not in ops)  # will trigger if 188 is fixed
        ops['meta'] = tag.untag(tkns[5])[1]
        t.add_node(kwid,'with',value=tag.retag('ob',ov,ops))

        # skip the six tokens we added
        return 6
    elif ll.matchl(tkns,val_edge,stop=0) == 0:
        # 701.10g exchange numerical values - edge case So far have
        # only seen 1 card (Serene Master) with this specific value
        # exchange which is exchange the characterisitic of and object
        # with the characteristic of another object
        # do not need the cls, go ahead and add then kwa etc
        if cls: t.add_node(pid,'clause',tkns=cls)
        kwid = t.add_node(pid,'keyword-action-clause')
        t.add_node(kwid,'keyword-action',word=v,type='value')

        # TODO: see 188
        # add the first charactersitic as a meta-characteristic
        # to the first 'thing'
        ot,ov,ops = tag.untag(tkns[0])
        assert('meta' not in ops)  # will trigger if 188 is fixed
        ops['meta'] = tag.untag(tkns[1])[1]
        t.add_node(kwid,'what',value=tag.retag(ot,ov,ops))

        # TODO: see 188
        # add the second charactersitic as a meta-characteristic
        # to the second 'thing'
        ot,ov,ops = tag.untag(tkns[6])
        assert('meta' not in ops)  # will trigger if 188 is fixed
        ops['meta'] = tag.untag(tkns[4])[1]
        t.add_node(kwid,'with',value=tag.retag(ot,ov,ops))

        # skip the seven tokens we added
        return 7
    else:
        if cls: t.add_node(pid,'clause',tkns=cls)
        return 0

def graph_kwa_shuffle(t,kwid,tkns):
    """
     because shuffle has so many variations, it is handled here.
    :param t: the tree
    :param kwid: the id of the current node
    :param tkns: the list of tokens immediately following ka<shuffle>
    :return: the skip number
    """
    # 701.19a shuffle zone->library although there are cases where
    # we see shuffle it where it refers to the library
    # 701.19c,701.19d shuffle card(s) [from a zone] into its owner
    # library

    # for the variation 701.19c we may find shuffle xo<it> as in
    # Alabaster Dragon or shuffle ob<card ...> as in 'Beacon of ...'
    # spells but the next token will always be pr<into> and the
    # 'object' being shuffled will be 3 tokens from the current
    # for the variation 701.19d we will have shuffle cards from
    # zone into zone

    # 701.19c shuffle card(s) into zone->library. This covers cases
    # of shuffle card into library and shuffle zone into library i.e. zone
    # = graveyard:
    if ll.matchl(tkns,[tag.is_thing,'pr<into>',tag.is_zone],stop=0) == 0:
        t.add_node(kwid,'thing',thing=tkns[0])
        t.add_node(kwid,'zone',zone=tkns[2])
        return 3

    # 701.19c shuffle cards from zone into zone
    sp = [tag.is_thing,'pr<from>',tag.is_zone,'pr<into>',tag.is_zone]
    if ll.matchl(tkns,sp,stop=0) == 0:
        t.add_node(kwid,'thing',thing=tkns[0])
        t.add_attr(t.add_node(kwid,'from'),'from',tkns[2])
        t.add_node(kwid,'zone',zone=tkns[4])
        return 5

    # 701.19a simple case
    # ...  ka<shuffle> zn<library player=you> ...
    # or ... ka<shuffle> xo<it> ...
    try:
        if tag.is_zone(tkns[0]) or tkns[0] == 'xo<it>':
            t.add_node(kwid,'zone',zone=tkns[0])
            return 1
    except IndexError:
        pass

    # should never get to here
    return 0

def graph_kwa_double(t,kwid,tkns):
    """
     graphs the keyword action
    :param t: the tree
    :param kwid: the id of the current node
    :param tkns: the list of tokens immediately following ka<shuffle>
    :return: the skip number
    """
    # double 701.9 - double power and/or toughness, double life, double counters
    # and double mana.

    # 701.9a (b,c) ka<double> power and/or toughness two basic forms
    # double obj<creature> characteristic or the edge case
    # double [the|target] characteristic of obj<creature> (God-Eternal Rhonas)
    # primary case
    if ll.matchl(tkns,[tag.is_thing,tag.is_meta_char]) == 0:
        t.add_node(kwid,'P/T',characteristic=tag.untag(tkns[1])[1],creature=tkns[0])
        return 2

    # edge case
    if ll.matchl(tkns,['the',tag.is_meta_char,'of',tag.is_mtg_obj]) == 0:
        t.add_node(kwid,'P/T',characteristic=tag.untag(tkns[1])[1],creature=tkns[3])
        return 4

    # 701.9d ka<double> player's life
    # looking for 'player life total'
    i = ll.matchl(tkns,[tag.is_player,'xc<life_total>'])
    if i > - 1:
        t.add_node(kwid,'life-total',who=tkns[i])
        return i+2

    # 701.9e ka<double> of counters on player or permanent
    # looking for "the number of CTR on obj|Thing
    # TODO: this might be a place to collate even though at this point, I have
    #  not seen a case of doubling counters on conjoined objects
    if ll.matchl(tkns,['the','number','of',tag.is_lituus_obj],stop=0) == 0:
        # split on the 3rd token (which should be the counter(s)
        _,ctr,rem = ll.splitl(tkns,3)
        _,val,ps = tag.untag(ctr)
        assert(val == 'ctr')

        # grab the Thing
        i = ll.matchl(rem,[tag.is_thing])
        ob = rem[i] # will throw an error if we don't have an object

        # is there an intermediate clause
        cls = rem[1:i]
        if cls:
            # see if we can find a quantifier & if so, untag it
            j = ll.matchl(cls,[tag.is_quantifier])
            if j > -1: cls = tag.untag(cls[j])[1]

        # create the node and ad quantifying clause if present
        nid = t.add_node(kwid,'counters',type=ps['type'],thing=ob)
        if cls: t.add_attr(nid,'quantifier',cls)

        return 4+i+1 # (the intial clause, then 1 past the thing)

    # 701.9f ka<double> amount of mana (also double {X} which technically falls
    # under double amount of mana see Unbound Flourishing) and Doubling Cube.
    # This one is hard due to the limited number of cards to use for reference
    # a. looking for 'amount' and then a reference to mana or b. 'value' followed
    # by a reference to a number or a number
    # TODO: check Unbound Flourshing once new allcards is download
    i = ll.matchl(tkns,[ll.ors(['amount','value'])])
    if i > -1:
        # i should always be 1
        tkn = tkns[i]
        if tkn == 'amount':
            j = ll.matchl(tkns,['xo<mana>'])
            assert(j > i)
            # should have something along the lines of 'of .... mana'
            # TODO: have to graph the tokens or further parse somehow
            x = tkns[i+1:i+j] # drop the first 'of' when adding
            t.add_node(kwid,'mana',by=x[1:] if x[0] == 'of' else x)
        else:
            j = ll.matchl(tkns,[tag.is_number])
            assert(j > i)
            t.add_node(kwid,'value',of=tag.untag(tkns[j])[1])
        return i+j

    return 0

def graph_lituus_action(t,pid,cls,la,tkns):
    """
     graphs a lituus action and associated parameters from tkns (and sometimes)
     cls) into tree t at
      parent id pid.
    :param t: the tree
    :param pid: parent id in the tree
    :param cls: previous (ungraphed) tokens
    :param la: untagged lituus-action token
    :param tkns: next tokens that haven't been added to the tree
    :return: skip, the number of items in tkns that have been processed
    """
    # extract the action word
    v = tag.untag(la)[1]

    # a few lituus actions require tokens from cls
    if v in THING_LA:
        # collate what we can from cls. Note that collate is grabbing from the
        # beginning of cls meaning we may have tokens in cls 'left over' and
        # between the rootless action node i.e. the last line of Ertai's familiar
        # "Ertai's Familiar cannot phase out" - the word 'cannot' will remain
        # TODO: have to figure out how/where to graph the additional for
        #  Ertai's Familar, it works but for adarkar Valkyrie it doesn't
        nid,skip = collate(t,cls)
        #if skip < len(cls): graph_clause(t,pid,cls[skip:])
        graph_clause(t,pid,cls[skip:])

        # now, create our hierarchy and add the collated subtree
        laid = t.add_node(pid,'lituus-action-clause')
        t.add_node(laid,'lituus-action',word=v)
        if nid: t.add_edge(laid,nid)
        return 0 # nothing in tokens was processed
    elif v == 'block':
        # block is different. it can refer to an object coming after the action
        # see Alluring Scent or the object can come prior to the action see
        # Ageless Sentinels.
        # TODO: see Alaborn Zealot block can actually take two object(s) preceding
        #  and succeeding the action word
        if ll.matchl(tkns,[tag.is_mtg_obj],stop=0) == 0:
            # post action object, clause out any opened clause, create a
            # lituus-action-clause node and the action action node
            if cls: t.add_node(pid,'clause',tkns=cls)
            laid = t.add_node(pid,'lituus-action-clause')
            t.add_node(laid,'lituus-action',word=v)
            nid,skip = collate(t,tkns)
            if nid: t.add_edge(laid,nid)
        else:
            # look behind
            nid,skip = collate(t,cls)
            #if skip < len(cls): t.add_node(pid,'clause',tkns=cls[skip:])
            graph_clause(t,pid,cls[skip:])

            laid = t.add_node(pid,'lituus-action-clause')
            t.add_node(laid,'lituus-action',word=v)
            if nid: t.add_edge(laid,nid)
            skip = 0
        return skip

    # TODO: pay will go here as well

    # the following do not require tokens from cls, so we can close it out, then
    # add our hierarchy
    if cls: t.add_node(pid,'clause',tkns=cls)
    laid = t.add_node(pid,'lituus-action-clause')
    t.add_node(laid,'lituus-action', word=v)

    skip = 0
    if v == 'add': return graph_lituus_action_add(t,laid,tkns)
    elif v == 'put': return graph_lituus_action_put(t,laid,tkns)
    elif v == 'distribute': return graph_lituus_action_distribute(t,laid,tkns)
    elif v in LA_THING:
        nid,skip = collate(t,tkns)
        if nid: t.add_edge(laid,nid)
    return skip

def graph_lituus_action_add(t,pid,tkns):
    """
     graphs a add (mana) lituus action and associated parameters from tkns into
     tree t at parent id pid.
    :param t: the tree
    :param pid: parent id in the tree
    :param tkns: next tokens that haven't been added to the tree
    :return: skip, the number of items in tkns that have been processed
    NOTE: we assume that any following tokens up to the first period (if
          it exists) or the end the tokens are qualifying instructions
    """
    # drop in the mana node
    mid = t.add_node(pid,'mana')

    # TODO: with double and triple. need to monitor new cards to make
    #  sure there are no amplyifing clauses by not stopping matchl at 0
    #  and there are not qualifying clauses
    # try double first
    dbl = [tag.is_mana_string,'or',tag.is_mana_string]
    if ll.matchl(tkns,dbl,stop=0) == 0:
        cid=t.add_node(mid,'conjunction',coordinator='or',item_type='mana-string')
        t.add_node(cid,'mana-string',mana=tkns[0])
        t.add_node(cid,'mana-string',mana=tkns[2])
        return len(dbl)

    # then triple
    tpl = [tag.is_mana_string,',',tag.is_mana_string,',','or',tag.is_mana_string]
    if ll.matchl(tkns,tpl,stop=0) == 0:
        cid = t.add_node(mid,'conjunction',coordinator='or',item_type='mana-string')
        t.add_node(cid,'mana-string',mana=tkns[0])
        t.add_node(cid,'mana-string',mana=tkns[2])
        t.add_node(cid,'mana-string',mana=tkns[5])
        return len(tpl)

    # single mana string find the index of the mana-string
    sng = ll.matchl(tkns,[tag.is_mana_string])
    if sng > -1:
        amp,ms,rem = ll.splitl(tkns,sng)

        if amp: t.add_node(mid,'amplifying-clause',tkns=tkns[:sng])
        t.add_node(mid,'mana-string',mana=ms)

        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            if rem: t.add_node(mid,'qualifying-clause',tkns=rem)
        return len(amp)+1+len(rem) # remember the mana-string is only 1 token

    # after double, triple and single i.e. any add mana with mana strings,
    #  we have two cases. Case 1 follow semi-strict phrasing and case 2 is
    #  all else which is suprisingly small
    # case 1:
    #  (a) add n mana of TOKEN color/type where TOKEN could be xq<any>,
    #   different, xq<that>
    #  (b) add n mana of any one color/type (have not seen type)
    #  (c) add n mana of the chosen color/type (have not seen type)
    #  (d) add n mana in any combination of colors (where n > 1)
    # case 2: has non-standard phrasing with xo<mana...> in the clause
    # TODO: all case 1 are very similary in processing, can we combine
    #  their processing in a single code block?
    # TODO: notice that all of these start with xo<mana...> and end with
    #  ch<color|type> have to go back and figure a way to match sub lists
    #  that start with a given query and end with a given query

    # case 1.a
    nm1 = [tag.re_mana_tag,'of',ll.re_all,tag.is_mtg_char]
    l1 = len(nm1)
    i = ll.matchl(tkns,nm1)
    if i > -1:
        # i will gives us [amplifying clause] mana clause [qualifying clause]
        # NOTE: I havent seen any with all three clauses but there are single
        # mana cases from above (i.e. Viridian Joiner) that have all three
        amp = tkns[:i]
        mc = tkns[i:i+l1]
        rem = tkns[i+l1:]

        # get the quantity and whether its color or type, then determine
        # what 'quantifier' to put in the 'of' parameter
        q = tag.re_mana_tag.match(mc[0]).group(2) # gives us the number
        o = tag.untag(mc[3])[1]                   # gives color or type
        if tag.tkn_type(mc[2]) == tag.MTGL_TAG: x = tag.untag(mc[2])[1]
        else: x = mc[2]

        # add amplfying clause (if it exists), the mana-clause and
        # qualifying clause (if it exists)
        if amp: t.add_node(mid,'amplifying-clause',tkns=amp)
        mcid=t.add_node(mid,'mana-clause',of="{} {}".format(x,o))
        if q: t.add_attr(mcid,'quantity',q)
        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            t.add_node(mid,'qualifying-clause',tkns=rem)
        return len(amp)+len(mc)+len(rem)

    # case 1.b
    # For below I have not seen any cases where
    #  1 there are amplifying or qualifying clauses
    #  2 the mana is specified as type
    # but for future expansion etc, we will code for those eventualities
    # This is a more specific match than case 1.a as it requires
    #  'xq<any>','nu<1>'
    nm2 = [tag.re_mana_tag,'of','xq<any>','nu<1>',tag.is_mtg_char]
    l2 = len(nm2)
    i = ll.matchl(tkns,nm2)
    if i > -1:
        amp = tkns[:i]
        mc = tkns[i:i+l2]
        rem = tkns[i+l2:]

        # get the quantity and whether its color or type, then determine
        # what 'quantifier' to put in the 'of' parameter
        q = tag.re_mana_tag.match(mc[0]).group(2) # gives us the number
        o = tag.untag(mc[4])[1]                   # gives color or type

        # add amplfying clause (if it exists), the mana-clause and
        # qualifying clause (if it exists)
        if amp: t.add_node(mid,'amplifying-clause',tkns=amp)
        t.add_node(mid,'mana-clause',quantity=q,of="any one {}".format(o))
        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            t.add_node(mid,'qualifying-clause',tkns=rem)
        return len(amp)+len(mc)+len(rem)

    # case 1.c
    nm3 = [tag.re_mana_tag,'of','the','xa<choose>',tag.is_mtg_char]
    l3 = len(nm3)
    i = ll.matchl(tkns,nm3)
    if i > -1:
        amp = tkns[:i]
        mc = tkns[i:i+l3]
        rem = tkns[i+l3:]

        # get the quantity and whether its color or type, then determine
        # what 'quantifier' to put in the 'of' parameter
        q = tag.re_mana_tag.match(mc[0]).group(2) # gives us the number
        o = tag.untag(mc[4])[1]                   # gives color or type

        # add amplfying clause (if it exists), the mana-clause and
        # qualifying clause (if it exists)
        if amp: t.add_node(mid,'amplifying-clause',tkns=amp)
        t.add_node(mid,'mana-clause',quantity=q,of="chosen {}".format(o))
        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            t.add_node(mid, 'qualifying-clause',tkns=rem)
        return len(amp)+len(mc)+len(rem)

    # case 1.d NOTE: there are not any "any combination of types"
    nm4 = [tag.re_mana_tag,'pr<in>','xq<any>','combination','of','ch<color>']
    l4 = len(nm4)
    i = ll.matchl(tkns,nm4)
    if i > -1:
        amp = tkns[:i]
        mc = tkns[i:i+l4]
        rem = tkns[i+l4:]

        # get the quantity and whether its color or type, then determine
        # what 'quantifier' to put in the 'of' parameter
        q = tag.re_mana_tag.match(mc[0]).group(2)  # gives us the number

        # add amplfying clause (if it exists), the mana-clause and
        # qualifying clause (if it exists)
        if amp: t.add_node(mid,'amplifying-clause',tkns=amp)
        t.add_node(mid,'mana-clause',quantity=q,of="any combination")
        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            t.add_node(mid,'qualifying-clause',tkns=rem)
        return len(amp)+len(mc)+len(rem)

    # case 2
    # have to find the index of mana then split tkns into amp, mana, qual
    i = ll.matchl(tkns,[tag.re_mana_tag])
    if i > -1:
        amp,mc,rem = ll.splitl(tkns,i)

        # get quantity if present TODO: what to do if it isnt
        try:
            q = tag.re_mana_tag.match(mc).group(2)
        except AttributeError:
            q = None

        # add amplfying clause if present, mana and qualifying clause if present
        # TODO: right now we have the following 'unprocessed' cards
        #  Jeweled Amulet: ([], 'xo<mana num=1>', ['of', 'ob<card ref=self>', 'last', 'noted', 'ch<type>'])
        #  Elemental Resonance ([], 'xo<mana>', ['op<≡>', 'ob<permanent status=enchanted>', 'ch<mana_cost>'])
        #  Chrome Mox ([], 'xo<mana num=1>', ['of', 'xq<any>', 'of', 'the', 'ob<card status=exiled>', 'ch<color>'])
        #  Jeweled Amulet (['ob<card ref=self>', 'last', 'noted', 'ch<type>', 'and', 'amount', 'of'], 'xo<mana>', [])
        #  Drain Power (['the'], 'xo<mana>', ['xa<lose>', 'xq<this>', 'way', mtgl.PER])
        if amp: t.add_node(mid,'amplifying-clause',tkns=amp)
        mcid=t.add_node(mid,'mana-clause')
        if q: t.add_attr(mcid,'quantity',q)

        if rem:
            stop = ll.matchl(rem,[mtgl.PER])
            if stop > -1: rem = rem[:stop]
            t.add_node(mid,'qualifying-clause',tkns=rem)
        return len(amp)+len(mc)+len(rem)

    # should never get here but leave in for debugging for now
    print("Unprocessed Add Mana: {}".format(tkns))
    return 0

# put-counter
def is_ctr(tkn): return tag.is_lituus_obj(tkn) and tag.untag(tkn)[1] == 'ctr'
put_ctr_sng = [is_ctr,'pr<on>',tag.is_thing]
put_ctr_dbl = [is_ctr,'pr<on>',tag.is_thing,'and',is_ctr,'pr<on>',tag.is_thing]
put_ctr_tpl = [
    is_ctr,'pr<on>',tag.is_thing,',',
    is_ctr,'pr<on>',tag.is_thing,',','and',
    is_ctr,'pr<on>',tag.is_thing
]
# put-card
def is_card(tkn): return tag.is_mtg_obj(tkn) and tag.untag(tkn)[1] == 'card'
put_card1 = [is_card,tag.is_preposition,tag.is_zone]
put_card2 = [
    is_card,tag.is_preposition,tag.is_zone,tag.is_preposition,tag.is_zone
]
def graph_lituus_action_put(t,pid,tkns):
    """
     graphs the lituus action 'put' and associated parameters (taken from tkns)
     at parent-id pid of of the tree t
    :param t: the tree
    :param pid: the parent-id to graph at
    :param tkns: the list of tokens to extract the parameters from
    :return: skip, the number of items in tkns that have been processed
    """
    # put refers to two separate actions 1) put a counter on an object and 2)
    # put a card into a zone

    # Action 1 - (121.6) put a counter on an object. Basic (single) has the form
    # xa<put> xo<ctr...> pr<on> ob<...>
    # NOTE:
    #  1. we'll use Thing to handle xo<it> and player(although in reference to
    #  players we only see gets a counter
    #  2. conjunctions are similar to but different than object conjuction
    #   phrasing, due to the xo<ctr...> and pr<on> repeated between the conjoined
    #   objects - therefor it is handled here

    # TODO: we need to relook at quantifiers, will there be cards with something
    #  other than 'any'
    # triple counter conjunction (only 2 cards Incremental Growth, Incremental Blight
    if ll.matchl(tkns,put_ctr_tpl,stop=0) == 0:
        cid = t.add_node(pid,'conjunction',coordinator='and',item_type='counter')
        for i in [0,4,9]: # index of xo<ctr...>s
            # extract the counter type and number (if any)
            ps = tag.untag(tkns[i])[2]
            ctype = ps['type'] if 'type' in ps else 'any' # set to any if necessary
            n = ps['num'] if 'num' in ps else '1'         # set num to 1 if necessary

            # add a counter node with a 'type' attribute (counter type) and an
            # 'on' attribute (the object the counter is put on)
            t.add_node(cid,'counter',type=ctype,num=n,on=tkns[i+2])
        return len(put_ctr_tpl)

    # double counter conjunction
    if ll.matchl(tkns,put_ctr_dbl,stop=0) == 0:
        cid = t.add_node(pid,'conjunction',coordinator='and',item_type='counter')
        for i in [0,4]: # index of xo<ctr...>s
            # extract the counter type and number (if any)
            ps = tag.untag(tkns[i])[2]
            ctype = ps['type'] if 'type' in ps else 'any' # set to any if necessary
            n = ps['num'] if 'num' in ps else '1'         # set to 1 if necessary

            # add a counter node with a 'type' attribute (counter type) and an
            # 'on' attribute (the object the counter is put on)
            t.add_node(cid,'counter',type=ctype,num=n,on=tkns[i+2])
        return len(put_ctr_dbl)

    # single put counter
    if ll.matchl(tkns,put_ctr_sng,stop=0) == 0:
        # extract the counter type and number (if any)
        # TODO: haven't seen any quantifiers other than 'another' or 'a' both
        #  of which can be considered '1' do we need to check anyway
        ps = tag.untag(tkns[0])[2]
        ctype = ps['type'] if 'type' in ps else 'any' # set to any if necessary
        n = ps['num'] if 'num' in ps else '1'         # set num to 1 if necessary
        t.add_node(pid,'counter',type=ctype,num=n,on=tkns[2])
        return len(put_ctr_sng)

    # Action 2 - put card in zone has two forms a. put card onto/into zone
    # (i.e. no from) and b. put card into/from zone into/onto/from zone
    # 2.b - do this first to avoid false positives from 2.a
    # TODO: we are dropping the specific preposition i.e. 'onto' and 'into' will
    #  this have an adverse effect?
    if ll.matchl(tkns,put_card2,stop=0) == 0:
        # in this case, we have to determine the from zone and the to zone
        if tag.untag(tkns[1])[1] == 'from':
            fz = tkns[2]
            tz = tkns[4]
        else:
            fz = tkns[4]
            tz = tkns[2]

        t.add_attr(t.add_node(pid,'card',to=tz,what=tkns[0]),'from',fz)
        return len(put_card2)

    # 2.a
    if ll.matchl(tkns,put_card1,stop=0) == 0:
        # in this case, we assume that the preposition is always 'onto' or 'into'
        # and therefore defines 'to'. 'from' is not stated in the clause
        t.add_node(pid,'card',to=tkns[2],what=tkns[0])
        return len(put_card1)

    return 0

def graph_lituus_action_distribute(t,pid,tkns):
    """
     graphs the lituus action 'distribute' and associated parameters (taken from
     tkns) at parent-id pid of of the tree t
    :param t: the tree
    :param pid: the parent-id to graph at
    :param tkns: the list of tokens to extract the parameters from
    :return: skip, the number of items in tkns that have been processed
    """
    # distribute has the initial phrase [distribute] xo<ctr...> among
    # then is followed by a list of numbers and an object in other words
    # [distribute] xo<ctr...> among [n [, n ,] or n] ob<...>
    # there are two numbers in distribute a. the number of counters and b.
    # the number of objects the counters will be put on

    # determine if tkns has the initial distribute clause
    # TODO: see Vastwood Hydra
    if ll.matchl(tkns,[is_ctr,'among'],stop=0) == 0:
        i = 2

        # have to read up to the first obj from the end of the phrase, then add
        # the two tokens from the initial phrase to get the index of the object
        j = ll.matchl(tkns[i:],[tag.is_mtg_obj])
        assert(j != -1)
        j += i

        # betw/ the initial phrase & the obj will be the list of numbers (if any)
        # two basic possibilities 1) there is no list of numbers regarding the
        # object(s), that number is stored in the object itself see
        # Blessings of Nature, the parsed mtgl is
        # 'xa<distribute>', 'xo<ctr type=+1/+1 num=4>', 'among',
        # 'ob<permanent characteristics=creature num=y quantifier=target>'
        # 2) a list of numbers is found between the initial clause and the object
        # Note: a parser side effect is that the last number will be 'assigned'
        #  to the object

        # regardless of case, the # and type of counters are in the initial phrase
        # TODO don't do any error checking now to see what happens
        ps = tag.untag(tkns[0])[2]
        ctype = ps['type']
        cnum = ps['num']

        # and the object will be always be at j. the last (or only) num of 'target'
        # objects will be in the object's prop list, pull the number out of the
        # object then retag it
        ot,ov,ops = tag.untag(tkns[j])
        onum = ops['num']
        del ops['num']
        ob = tag.retag(ot,ov,ops)

        # no further analysis needs to be done, since we can determine by
        # the distance between i and j what case we have
        diff = j-1
        if diff == 0: pass # could go an delete this
        elif diff == 3: onum = "{}, {}".format(tag.untag(tkns[i])[1],onum)
        elif diff == 6:
            onum = "{}, {}, {}".format(
                tag.untag(tkns[i])[1],tag.untag(tkns[i+2])[1],onum
            )
        t.add_node(pid,'counter',type=ctype,num_ctr=cnum,num_obj=onum,on=ob)
        return j # skip up the object

    return 0

def graph_lituus_action_pay(t,pid,tkns):
    """
     graphs a pay lituus action and associated parameters from tkns into
     tree t at parent id pid.
    :param t: the tree
    :param pid: parent id in the tree
    :param tkns: next tokens that haven't been added to the tree
    :return: skip, the number of items in tkns that have been processed
    """
    # find the first period (if one exits), no need to go further than that
    if mtgl.PER in tkns:
        tkns,_,rem = ll.splitl(tkns,tkns.index(mtgl.PER))
        skip = len(tkns)
    else: skip = len(tkns)

    # there are several cases where pay does not have subcosts,
    # "This effect reduces only the amount of colored mana you pay." (Edgewalker,
    # Ragemonger) and "If they dont' pay, ..." (Arcum's Whistle, Cyclone etc)
    # exit if we get that case
    if not tkns or tkns[0] == mtgl.CMA: return 0

    try:
        ss = subcosts(tkns)
        if ss == [['ob<card ref=self>', 'kw<cumulative_upkeep>']]:
            raise RuntimeError
        print(ss)
        #_ = subcosts(tkns)
    except:
        #print(tkns)
        raise
    # now, take the tokens and graph as subcosts
    #assert(tkns != [])
    #try:
    #    #print(subcosts(tkns))
    #    _ = subcosts(tkns)
    #except IndexError:
    #    print(tkns)

    return 0

def graph_cost(t,pid,tkns):
    """
     graphs a cost (and subsequent subcosts) contained in tkns at parent id
     pid of tree t
    :param t: the tree
    :param pid: the parent id
    :param tkns: the list of tokens containing the cost
    """
    ss = subcosts(tkns)
    if len(ss) == 1: cid = pid
    else: cid=t.add_node(pid,'conjunction',item_type='cost',coordinator='and')
    for s in ss: graph_clause(t,cid,s)

# TODO: this needs testing for confirmation
def subcosts(tkns):
    """
     extracts all subcosts from the list of tokens
    :param tkns: list to extract subcosts from
    :return: a list of subcosts
    """
    # remove long hyphen and trailing period if present
    if tkns[0] == mtgl.HYP:
        tkns = tkns[1:]
        if tkns[-1] == mtgl.PER: tkns.pop()

    # split the tkns into clauses by comma
    ss = []
    prev = 0
    for i in ll.indicesl(tkns,mtgl.CMA): # looking for middle splits
        ss.append(tkns[prev:i])          # don't include the comma
        prev = i+1                       # skip the comma
    if prev != len(tkns): ss.append(tkns[prev:]) # last (or only) subcost

    # sanity check on the subcosts see Behemoth's Herald, the above loops breaks
    # everything up by comma meaning meaning the ka<sacrifice clause gets broken
    # into three subcosts when it is only one. Based on going through multiple card
    # with more than 1 costs, it appears that each subcost will be a mtg token
    # (a mana string or {t} or {q} etc) or an action clause.
    ss1 = []     # the final list of subcosts
    running = [] # list of clauses encountered that arent mtg tokens
    for s in ss:
        if tag.tkn_type(s[0]) == tag.MTGL_SYM:
            # got a symbol
            if running:
                # close out running, joining the running list by comma & reset
                ss1.append(ll.joinl(running,mtgl.CMA))
                running = []
            ss1.append(s) # add the symbol
        else:
            # got something else: if it's an action word, close out & append
            # running then rest otherwise append the new clause to running
            if tag.is_action(s[0]):
                if running: ss1.append(ll.joinl(running,mtgl.CMA))
                running = [s]
            else: running.append(s)
    if running: ss1.append(ll.joinl(running,mtgl.CMA))
    return ss1

def ta_clause(tkns):
    """
     breaks the list of tkns into trigger word, trigger condition/event and
     trigger effect
    :param tkns: list of tokens beginning with a trigger word
    :return: trigger-word, trigger-condition, trigger-effect, instructions
    """
    # break tkns into trigger-word and remaining
    _,tw,rem = ll.splitl(tkns,0)
    assert(tag.is_tgr_word(tw))

    # get the list of comma indices
    idx = ll.indicesl(rem,mtgl.CMA) # looking for middle split
    assert(idx) # should be at least one

    # for more than one comma, break the remainder up by comma
    prev = 0
    ss = []
    for i in idx:
        ss.append(rem[prev:i])
        prev = i+1 # drops the comma
    ss.append(rem[prev:])

    # look for key phrases to determine where the condition and effect are joined
    # these are
    #  Thing action-word or player (may) action-word
    # conditional-if, that is, cn<if> signifies that this clause is part of the
    #  condition, the effect will be the next clause
    #   TODO: are there any other conditions we have to look at
    # where nu<x> - signifies that this clause is part of the previous one,
    # meaning the previous one should be the beginning of the effect
    # TODO: any event like enter the battlefield signifies a condition (except
    #  in the case multiple objects that make up an 'or' clause)
    split = None
    for i,s in enumerate(ss):
        if i == 0:
            # the first clause is always in the condition but, if it ends with
            # a phase, it is the only part of the condition
            if ll.matchl(s[-1:],[tag.is_phase],stop=0) == 0: split = 1
            else: continue
        if ll.matchl(s,[tag.is_thing,tag.is_action],stop=0) == 0:
            split = i
            break
        elif ll.matchl(s,[tag.is_player,'cn<may>',tag.is_action],stop=0) == 0:
            split = i
            break
        elif tag.is_action(s[0]):
            split = i
            break
        elif s[0] == 'cn<if>':
            split = i+1
            break
        elif ll.matchl(s,['where',tag.is_variable],stop=0) == 0:
            split = i-1
            break
    if not split: split = -1

    # now, have to rejoin the subclauses putting needed commas back in
    cond = ll.joinl(ss[:split],mtgl.CMA)
    rem  = ll.joinl(ss[split:],mtgl.CMA)

    # The remainder is either only the effect or, it is effect. instructions
    if mtgl.PER in rem:
        effect,_,instr = ll.splitl(rem,rem.index(mtgl.PER))
        effect += [mtgl.PER] # add the period back to effect
    else:
        effect = rem
        instr = []

    # before returning we have to make sure that a double-quoted clause has not
    # been split across effect and instr.
    ds = ll.indicesl(effect,mtgl.DBL)
    if len(ds)%2 == 1: # have an odd number of double quotes
        i = ll.rindexl(instr,mtgl.DBL)
        effect += instr[:i+1]
        instr = instr[i+1:]

    return tw,cond,effect,instr

def _pro_from_(tkns):
    """
     extracts the 'characteristics' listed in the 'protection clause' tkns. tkns is
     all tokens in the keyword clause following the keyword protection
    :param tkns: a list of one or more characteristics seperated by 'pr<from>
    :return: a list of qualities
    """
    # first, get the protection from tokens/clauses
    pros = []
    prev = 0
    for i in ll.indicesl(tkns,'pr<from>'):
        if prev == i == 0: continue
        pro = tkns[prev+1:i]
        if 'and' in pro: pro,_,_ = ll.splitl(pro,pro.index('and'))
        pros.append(pro)
        prev = i
    pro = tkns[prev+1:]
    if 'and' in pro: pro,_,_ = ll.splitl(pro,pro.index('and'))
    pros.append(pro)

    # pros will be either be a list of one more items where each item is an object
    # with a chararacteristic i.e. see Phyrexian Crusader pros will be
    #  [['ob<card characteristics=white>'],['ob<card characteristics=black>']]
    # or in edges cases single element list where the element is a list of tokens
    # one of which is a meta characteristic.
    # NOTE: have not seen anything that has more than singleton edge case see
    # Mistmeadow Skulk but just in case will be prepared for multiple edgecases
    ch = [] # list of found characterstics
    for i,pro in enumerate(pros):
        if len(pro) == 1:
            # have either an object with a characteristic or a characteristic
            if tag.is_mtg_char(pro[0]): ch.append(tag.untag(pro[0])[1])
            else:
                ps = tag.untag(pro[0])[2]
                assert('characteristics' in ps)
                ch.append(ps['characteristics'])
        else:
            # edge case - currently know of two possibilities, a meta-characteristic
            # with value or a quantified meta-characteristic
            mc = [tag.is_meta_char,tag.is_operator,tag.is_number]
            qc = [tag.is_quantifier,tag.is_meta_char]
            if ll.matchl(pro,mc,stop=0) == 0:
                ch.append("{}{}{}".format(
                        tag.untag(pro[0])[1], # the meta-characteristic,
                        tag.untag(pro[1])[1], # the operator
                        tag.untag(pro[2])[1]  # the numeric value
                    )
                )
            elif ll.matchl(pro,qc,stop=0) == 0:
                ch.append("{}{}{}".format(
                        tag.untag(pro[1])[1], # the meta-chararcteristics
                        mtgl.EQ,              # equal to sign
                        tag.untag(pro[0])[1]  # the quantifier
                    )
                )
            else:
                # in the rule book, 702.16a discusses protection from a card name
                # and 702.16j discusses protection from a player. Have not seen
                # any of these
                raise mtgl.MTGLGraphException("Unknown edge-case in protection")
    return ch

# TODO: have to look at is_mtg_obj vs is_thing there are cases (Contempt)
#  in bi-chains where an mtg object should be conjoined with a lituus obj
qud_chain = [ # only a few quad chain cards (see Decimate)
    tag.is_mtg_obj,mtgl.CMA,                                    # 0,1
    tag.is_mtg_obj,mtgl.CMA,                                    # 2,3
    tag.is_mtg_obj,mtgl.CMA,tag.is_coordinator,tag.is_mtg_obj # 4,5,6,7
]
tri_chain = [
    tag.is_mtg_obj,',',tag.is_mtg_obj,',',tag.is_coordinator,tag.is_mtg_obj
]
tri_chain_alt = [ # three objects (missed by the parser) that should be 'chained'
    tag.is_mtg_obj,',',tag.is_mtg_obj,',',tag.is_mtg_obj,
]
bi_chain = [tag.is_thing,tag.is_coordinator,tag.is_thing]
bi_chain_alt = [tag.is_mtg_obj,',',tag.is_mtg_obj]
def collate(t,tkns):
    """
     given that the first token in tkns is a Thing, gathers and combines all
     subsequent tokens in tkns that refer to a Thing or Things under a conjuction
    :param t: the tree
    :param tkns: list of unprocessed tokens
    :return: id for the 'rootless' conjunction node, number of tokens processed
    """
    # check in decreasing number of conjoined object to avoid false positives

    # check quad-chains
    if ll.matchl(tkns,qud_chain,stop=0) == 0:
        return conjoin(t,[tkns[0],tkns[2],tkns[4],tkns[7]],tkns[6]),len(qud_chain)

    # check tri-chains
    if ll.matchl(tkns,tri_chain,stop=0) == 0:
        return conjoin(t,[tkns[0],tkns[2],tkns[5]],tkns[4]),len(tri_chain)

    # check tri-chain alternate (create a single object) see Victim of Night
    # 'fixing' an inability of the parser to chain these under a single object
    if ll.matchl(tkns,tri_chain_alt,stop=0) == 0:
        # TODO: this will fail if any of the objects do not have characteristics
        tg,val,ps = tag.untag(tkns[0]) # untag the first object
        ps2 = tag.untag(tkns[2])[2]
        ps3 = tag.untag(tkns[4])[2]
        ps['characteristics'] = mtgl.AND.join(
            [ps['characteristics'],ps2['characteristics'],ps3['characteristics']]
        )
        nid = t.add_ur_node('object')
        t.add_attr(nid,'object',tag.retag(tg,val,ps))
        return nid,len(tri_chain_alt)

    # check bi-chain
    if ll.matchl(tkns,bi_chain,stop=0) == 0 and conjoin_bi_chain(tkns):
        return conjoin(t,[tkns[0],tkns[2]],tkns[1]),len(bi_chain)

    # check bi-chain alternate, once again, create a single object
    if ll.matchl(tkns,bi_chain_alt,stop=0) == 0:
        # based on review of cards, these can be chained into a single object
        # unless one of the objects is a self-reference
        if tkns[0] != 'ob<card ref=self>' and tkns[2] != 'ob<card ref=self>':
            # from the 1st object, we want the tag (should be 'ob') and the prop
            # list. from the 2nd object we want the val and the prop list. Due to
            # the parser, the 1st object will have a value of permanent the 2nd
            # will have the value as found in the oracle text (if any) or
            # permanent if it wasn't stated.
            # TODO: i don't think there is any problem but should we check
            #  the second object for other properties?
            tg,_,ps = tag.untag(tkns[0])
            _,val,ps1 = tag.untag(tkns[2])
            if 'characteristics' in ps:
                ps['characteristics'] += mtgl.AND + ps1['characteristics']
            else: ps['characteristics'] = ps1['characteristics']

            # add a rootless node & retag the chained object
            nid = t.add_ur_node('object')
            t.add_attr(nid,'object',tag.retag(tg,val,ps))
            return nid,len(bi_chain_alt)

    # single token?
    if ll.matchl(tkns,[tag.is_thing],stop=0) == 0:
        nid = t.add_ur_node('object')
        t.add_attr(nid,'object',tkns[0])
        return nid,1

    return None,0

def conjoin(t,objs,c):
    """
     combines the objects in objs with coordinator c under a conjunction node
    :param t: the tree
    :param objs: a list of 'objects'
    :param c: the coordinator token
    :return: node-id of a 'rootles' conjuction node
    """
    # to conjoin, create a conjunction node with coordinator attribute. Due to the
    # parser's method of chaining and combining objects, any quantifiers (that apply
    # to all the objects) will be in the first object, the same goes for numbers,
    # possessives that apply to all the objects (i.e. owner, controller) will be
    # in the last object. status, meta, characteristics will stay with the object
    # they're found in. As will numbers etc that are found in non-first nodes
    # TODO: Sands of time does not follow this convention, 'status = tapped' should
    #  be in each object but is only found in the first

    # initialize top-level attributes to None and update coordinator if neccessary
    qtr = num = pk = pv = None
    crd = 'and/or' if c == 'op<⊕>' else c

    # get any quantifier and/or number from the first object
    # TODO: do we need to verify that val is the same for each object?
    tg,val,ps = tag.untag(objs[0])
    qtr = ps['quantifier'] if 'quantifier' in ps else None

    if qtr: del ps['quantifier']
    if 'num' in ps:
        # for number, store it, delete the attribute from the object & retag it
        num = ps['num']
        del ps['num']
    objs[0] = tag.retag(tg,val,ps)

    # get any possessor from the last object
    tg,val,ps = tag.untag(objs[-1])
    if 'owner' in ps or 'controller' in ps:
        # for possesive, store it, delete the attr. from the object & retag it
        pk = 'owner' if 'owner' in ps else 'controller'
        pv = ps[pk]
        del ps[pk]
    objs[-1] = tag.retag(tg,val,ps)

    # create a (rootless) conjunction node and add attributes if present
    nid = t.add_ur_node('conjunction',coordinator=crd,item_type='object')
    if qtr: t.add_attr(nid,'quantifier',qtr)
    if num: t.add_attr(nid,'n',num)
    if pk: t.add_attr(nid,pk,pv)

    # iterate the objects and add to the conjuction node
    for obj in objs:
        tg,val,ps = tag.untag(obj)
        if 'quantifier' in ps: del ps['quantifier']
        t.add_attr(t.add_node(nid,'item'),'object',tag.retag(tg,val,ps))

    return nid

def conjoin_bi_chain(tkns):
    """
     determines if there is a bi-chain of objects in tkns which can be conjoined
    :param tkns: the list of tokens to check
    :return: True if the start of tokens can be conjoined (bi-chain) or False
     otherwise
    """
    # TODO: this needs extensive testing and verification
    # do not chain anything that meets the following criteria
    #  1. the word immediately after the bi-chain is an action word
    #  2. the word immediately after the bi-chain is a conditional or negation
    #   i.e. 'cn<may>' or 'doesnt'
    #  3. the word immediately after the bi-chain is a characteristic
    try:
        nxt = tkns[len(bi_chain)]
    except IndexError: return True
    else:
        if tag.is_action(nxt): return False
        if tag.is_conditional(nxt) or nxt == 'doesnt': return False
        if tag.is_property(nxt): return False
        return True

# modal preambles
# TODO: modal3 (Siege) needs to be redone once we have graphed replacements
# TODO: by splitting on the first bullet, we can look at condesing and reducing
#  the number of modal preambles
modal1 = ['xa<choose>',tag.is_number,mtgl.HYP]
modal2 = [
    'xa<choose>',tag.is_number,mtgl.PER,'xp<you>','cn<may>','xa<choose>',
    'the','same','mode','more','than','once',mtgl.PER
]
modal3 = [ # choose any
    'xa<choose>',tag.is_number,'or','both',mtgl.HYP
]
modal4 = [ # Siege enchantments
    'as','ob<card ref=self>', 'xa<enter>', 'zn<battlefield>',
    ',', 'xa<choose>',ll.re_all,'or',ll.re_all,mtgl.PER
]
modal5 = [ # decreasing options (choose one that hasn't been chose)
    'xa<choose>',tag.is_number,'xq<that>','hasnt','been','xa<choose>',mtgl.HYP
]
modal6 = [ # edge case Vindictive Lich (very similar to modal 2 initially)
    'xa<choose>',tag.is_number,mtgl.PER,'xq<each>','mode','must','xa<target>',
    'a','different','xp<player>',mtgl.PER
]
def modal_type(tkns):
    """
     determines if the list of tokens is modal
    :param tkns: tokens to check
    :return: positive number matching the modal type or 0 if not modal
    """
    # modal1 may be preceded by 'an opponent' other modals start the line
    if not mtgl.BLT in tkns: return 0 # ignore any matches if there are no bullets
    if ll.matchl(tkns,modal1,stop=1) > -1: return 1
    elif ll.matchl(tkns,modal2,stop=0) == 0: return 2
    elif ll.matchl(tkns,modal3,stop=0) == 0: return 3
    elif ll.matchl(tkns,modal4,stop=0) == 0: return 4
    elif ll.matchl(tkns,modal5,stop=0) == 0: return 5
    elif ll.matchl(tkns,modal6,stop=0) == 0: return 6

def is_level(tkns): return ll.matchl(tkns,['level',tag.is_number],stop=0) == 0

def is_activated_ability(tkns):
    """
     determines if the list of tkns defines an activated ability and if so it
     defines a ability of the card vice an activated ability granted by the card
    :param tkns: tokens to check
    :return: True if tkns is a 'true' activated ability
    """
    if ':' in tkns:
        # NOTE: even though we do not process single-quoted phrases, we still need
        #  to check for them here
        if mtgl.DBL in tkns and tkns.index(mtgl.DBL) < tkns.index(':'): return False
        if mtgl.SNG in tkns and tkns.index(mtgl.SNG) < tkns.index(':'): return False
        else: return True
    else: return False

####
# KEYWORDS
# keyword lines contain one or more comma seperated keyword clauses where a keyword
# clause has one keyword and associated definitions. the keyword clause may also
# contain commas
####

def is_kw_line(line):
    """
     determines if line is a keyword line
    :param line: the line to check
    :return: True if line is a keyword line
    """
    # TODO: have to fix this as it can fail (particulary if lines aren't being
    #  graphed correctly)
    # standard keyword ability line is one or more comma separated keyword clauses
    # and does not end with a period or a period and a double quote
    if not line[-1] in [mtgl.PER,mtgl.DBL] and ll.matchl(line,[tag.is_keyword]) > -1:
        return True

    # keyword clauses with non-mana cost will have a long hyphen, start with a
    # keyword and end with a period
    if tag.is_keyword(line[0]) and mtgl.HYP in line and line[-1] == mtgl.PER:
        return True

    return False

def kw_clauses(line):
    """
    parse out keyword ability clauses from line return them as a list
    :param line: the line to parse
    :return: a list of keyword ability clauses
    """
    # preprocess three keywords: cycling, landwalk and offering may have
    # preceding quality rearrange order so keyword comes first
    news = []
    for tkn in line:
        try:
            if tag.is_keyword(tkn):
                if tag.untag(tkn)[1] in KW_VARIATION and tag.is_quality(news[-1]):
                    t = news.pop()
                    news.append(tkn)
                    news.append(t)
                    continue
        except IndexError: pass
        news.append(tkn)

    kwcs = [] # the list of kwcs
    kwc = []  # the current keyword ability clause
    try:
        for tkn in news:
            if not tag.is_keyword(tkn): kwc.append(tkn)
            else: # found a keyword, process the last clause if any
                if kwc:
                    # one keyword: modular (in one card) has the form
                    # modular-sunburst
                    if tag.untag(tkn)[1] == 'sunburst' and\
                        kwc == ['kw<modular>', '—']:
                        kwc.append(tkn)
                    else:
                        if kwc[-1] == 'xa<has>' or kwc[-1] == 'xa<gain>':
                            # if the preceding word is gain or has, this is not
                            # the start of new keyword clause
                            kwc.append(tkn)
                        else:
                            # finish this clause and start the next (strip the
                            # last comma if present)
                            if kwc[-1] == mtgl.CMA: kwc = kwc[:-1]
                            kwcs.append(kwc)
                            kwc = [tkn]
                else: kwc = [tkn]

        # finish and any remaining clause (strip the last comma if present)
        if kwc:
            if kwc[-1] == mtgl.CMA: kwc = kwc[:-1]
            kwcs.append(kwc)
    except mtgl.MTGLException:
        raise mtgl.MTGLException("Invalid keyword ability clause")

    return kwcs

####
# KEYWORD ABILITY REFERENCES Section 702
# NOTE: below is primarily for reference but we do use KW_N_COST & KW_VARIATION
# keyword clauses come in multiple formats
#   Singleton i.e.flying = kw<KEYWORD>
#   Numeric i.e.rampage = kw<KEYWORD> nu<N>
#   Cost i.e.echo = kw<KEYWORD> COST
#   Thing or Quality i.e.enchant = kw<KEYWORD> Thing/Quality
#   Special i.e.affinity = kw<KW> ENLISH_WORD QUALITY or NAME[MANA_COST]
#    or kw<KW> nu<N>—COST i.e. awaken
# keywords with non - mana costs have the form kw<KW> — COST
####

KW_VARIATION = ['cycling','landwalk','offering']
KW_N_COST = [
    'awaken',      # 702.112a Awaken N <long-hyphen> [cost]
    'suspend',     # 702.61a Suspend N <long-hyphen> [cost]
    'reinforce',   # 702.76a Reinforce N <long-hyphen> [cost]
]

# NOTE:
# 1. hexproof (3 cards have hexproof from)
# 2. 1 card has modular<long hyphen>sunburst
""" REFERENCE ONLY
KW_SINGLETON = [
    'deathtouch','defender','double_strike','first_strike','flash','flying',
    'haste','hexproof','indestructible','intimidate','lifelink','reach','shroud',
    'trample','vigilance','banding','flanking','phasing','shadow','horsemanship',
    'fear','provoke','storm','modular','sunburst','epic','convoke',
    'haunt','split_second','delve','gravestorm','changeling','hideaway','conspire',
    'persist','wither','retrace','exalted','cascade','rebound','totem_armor',
    'infect','battle_cry','living_weapon','undying','soulbond','unleash','cipher',
    'evolve','extort','fuse','dethrone','prowess','exploit','menace','devoid',
    'ingest','myriad','skulk','melee','partner','undaunted',
    'improvise','aftermath','ascend','assist','jump_start','mentor','riot'
]
"""
# NOTE:
# 1. Champion would be special but due to parsing the quantifier is merged into
# the object i.e. champion an object becomes kw<champion> ob<type quantifier=a>
# 2. Partner with would be special but due to parsing the name bcecomes and
# object
""" REFERENCE ONLY
KW_OBJECT = [ #kw<KEYWORD> ob<OBJ>
    'enchant','landwalk','offering','champion','partner_with'
]
"""

# NOTE:
# 1. Kicker has a and/or variation
# 2. Cycling has a [Type]cycling [cost] variation
# 3. Equip has a Equip [quality] creature i.e. Blackblade Reforged
""" REFERENCE ONLY
KW_COST = [ #kw<KEYWORD> [cost]
    'equip','buyback','echo','kicker','multikicker','flashback','madness',
    'morph','megamorph','entwine','ninjutsu','commander_ninjutsu','replicate',
    'recover','aura_swap','fortify','transfigure','evoke','prowl','unearth'
    'level_up','miracle','overload','scavenge','bestow','outlast','dash',
    'surge','emerge','embalm','eternalize','spectacle'
]
"""
""" REFERENCE ONLY
KW_N = [ # kw<KEYWORD> N
    'rampage','fading','amplify','modular','bushido','soulshift','dredge',
    'bloodthirst','graft','ripple','vanishing','absorb','frenzy','poisonous',
    'devour','annihilator','tribute','renown','crew','fabricate','afflict',
    'afterlife'
]
"""
""" REFERENCE ONLY
KW_SPECIAL = [
    #'equip',        # 702.6s Equip [quality] creature [cost]. 1 card, Blackblade Reforged
    #'protection',   # 702.16a Protection from [quality]
                    # 702.16g Protection from [quality A] and from [quality B]
                    # 702.16h/702.16i Protection from (all [characteristic])/everything
    #'cycling',      # 702.28e [Type]cycling [cost]
    #'kicker',       # 702.32b Kicker [cost 1] and/or [cost 2]
    #'affinity',     # 702.40a Affinity for [text] (i.e. object)
    #'splice',       # 702.46a Splice onto [subtype] [cost]
    #'forecast',     # 702.56a Forecast <long-hyphen> [Activated Ability]
    #'champion',    # 702.71a Champion an [object]
    #'partner_wth', # 702.123f Partner with [name]
]
"""

####
# KEYWORD ACTION REFERENCES Section 701
# NOTE: below is primarily for reference but we do use KW_N_COST & KW_VARIATION
####

KWA_N = [ # ka<KEYWORD ABILITY> N
    'scry','fateseal','monstrosity','bolster','support','surveil','adapt','amass'
]

KWA_OBJECT = [ # ka<KEYWORD-ACTION> ob
    'destroy','regenerate','sacrifice','tap','untap','detain','exert','attach',
    'unattach','goad','create','exile','manifest','discard','reveal','counter',
    'activate','cast','play','meld',                                                            # xo or obj
]

""" REFERENCE ONLY
KWA_SINGLETON = ['proliferate','populate','investigate']
"""

""" REFERENCE ONLY
KWA_SPECIAL = [
    'double',   # 701.9a TODO
    #'exchange'  # 701.10a  TODO
    #'fight',   # 701.12a ob1 fights obj2
    #'search'    # 701.18a search zone 'for' card
    #'clash',    # 701.22a clash with an opponent
    #'vote',     # 701.31a
    #'meld',     # 701.36a meld ob (however ob is always xo<them>'
    #'explore', # 701.39a ob explores
    #'shuffle', # 701.19a
]
"""

# double 701.9
# ka<double> power and/or toughness 701.9a
# ka<double> player's life 701.9d
# ka<double> # of counters on player or permanet 701.9e
# ka<double> amount of mana 701.9f

####
# LITUUS ACTION REFERENCES
# Lituus actions are words that are common and important in MTG oracle text but
# are not referenced, identified or discussed in the comprehensive rules.
# A prime example is draw. Some refer to kewyord actions or abilities like cycle,
# phase in etc.
#
# Because these are not referenced by the rules book, we attempt to define their
# usage and parameters via how and where they are used in oracle texts
####

LA_THING = [ # xa<LITUUS ACTION> Thing
    'flip','cycle'
]

THING_LA = [ # Thing xa<LITUUS ACTION>
    'phase_in','phase_out','die','attack',
]

"""
    'remove','get','return','draw','move','copy','look','pay','paid',
    'deal','gain','lose','block','enter','leave','choose','die',
    'spend','take','skip','cycle','reduce','trigger','prevent','declare',
    'has','have','switch','assign','win','target'
"""

"""
 Working Notes
  return will be very similar to shuffle 
   it will have an object an a zone (return it to the battlefield)
   it may also have two zones (return all Human creature cards from your 
   graveyard to the battlefield)
  declare
   different, because we know we will get word,ob,word,la
"""

""" REFERENCE ONLY 
add - xa<add> Mana ((symbol, string or xo<mana...>)
put - xa<put> Card (from Zone) to Zone or xa<put> n counter(s) on object
distribute - xa<distribute> n1 counters among n2 objects
phase in/phase out: object xa<phase_in> or object xa<phase_out>
flip - xa<flip> Thing (coin or object)
cycle - xa<cycle> a card
die - object xa<die>
attack - object xa<attack>
"""
