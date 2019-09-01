#!/usr/bin/env python
""" parser.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Parses tagged oracle text and resolves tagger errors using contextual information
"""

__name__ = 'parser'
__license__ = 'GPLv3'
__version__ = '0.1.7'
__date__ = 'August 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
import lituus.mtgl.list_util as ll
import lituus.mtgl.tagger as tagger
import lituus.mtgl.lexer as lexer
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.grapher as grapher

# constants/helpers
re_draft = re.compile(r"draft(ing|ed)?")

def parse(name,card):
    """
     returns a tree for each line in card's text
    :param name: name of the card
    :param card: the card dict
     NOTE: modifies the card dict in place
    """
    # tag and tokenize the oracle text
    try:
        card['tag'] = tagger.tag(name,card['oracle'])
        card['tkn'] = lexer.tokenize(card['tag'])
    except Exception as e:  # generical catchall for debugging purposes
        print("Failed to tag and tokenize {} -> {]".format(name), type(e))

    # parse the tagged oracle text into mtgl
    for i,line in enumerate(card['tkn']):
        try:
            # check for reference to 'draft' in the line. if so, drop the line
            if ll.matchl([re_draft],line) > -1: continue
            line = rectify(line)
            line = chain(line)
            line = chain_zones(line)
            line = group(line)
            line = add_hanging(line)
            line = merge_possessive(line)
            card['mtgl'].append(line)
        except Exception as e: # generic catchall for debugging purposes
            print("Failed to parse {} at line {} -> {}.".format(name,i,type(e)))
            raise

    # parse the mtgl into a tree
    try:
        ctype = 'other'
        if 'Instant' in card['type'] or 'Sorcery' in card['type']: ctype = 'spell'
        elif 'Saga' in card['sub-type']: ctype = 'saga'
        card['mtgt'] = grapher.graph(card['mtgl'],ctype)
    except mtgl.MTGLException as e:
        print(e)
        raise

def rectify(olds):
    """
     fixes three issues.
      1. token (non)token is the only top-level object from rule 109 but acts
        like a a chracteristic.
      2. or'ed and and'ed objects (primarily/only spells or abilities) need to be
       combined
      3. double-tags like ob<xa<copy>> as well as single tags like ka<exile>
       require context to be fixed
      4. combines phrases like nu<1> or more or nu<10> or less into a single
       nu tag
    :param olds: the current list of tokens
    :return: tokens with subsequent entities merged
    """
    news = []
    skip = 0
    for i,tkn in enumerate(olds):
        # skip any tokens that have already been processed
        if skip:
            skip -= 1
            continue

        # if the below fails, drop to end of for loop and just append the token
        if mtgl.is_mtg_obj(tkn):
            # (1) move (non)token to right of characteristics
            try:
                if mtgl.is_mtg_char(olds[i+1]) and 'token' in tkn:
                    j = i+1
                    while mtgl.is_mtg_char(olds[j]):
                        news.append(olds[j])
                        j += 1
                        skip += 1
                    news.append(tkn)
                    continue
            except IndexError:
                pass

            # (2) make two and'ed/or'ed 'consecutive' singleton objs one
            # TODO: is this still relevant? find an example
            try:
                if olds[i+1] == 'or' or olds[i+1] == 'and':
                    t,v,p = mtgl.untag(olds[i+2])
                    if t == 'ob' and not p:
                        op = mtgl.OR if olds[i+1] == 'or' else mtgl.AND
                        news.append(mtgl.retag(
                            t,"{}{}{}".format(mtgl.untag(tkn)[1],op,v),{}
                            )
                        )
                        skip = 2
                        continue
            except mtgl.MTGLTagException: pass
            except IndexError: pass

        # (3) determine if
        # a) 'xe<xa<copy>>' is an entity or action. If it's followed by an object
        # or quantifier, then its an action (lituus) otherwise its an object
        #  TODO: or will it always be followed by a quantifier target, that, all etc
        #   for now only do quanitifiers
        if tkn == 'ob<xa<copy>>':
            try:
                if mtgl.is_quantifier(olds[i+1]): news.append('xa<copy>')
                else: news.append('ob<copy>')
            except IndexError:
                news.append('ob<copy>')
            continue

        # b) ka<exile> is an action or a zone. If its preceded by a preposition
        # change it to zone, otherwise leave it alone
        if tkn == 'ka<exile>':
            try:
                if mtgl.is_preposition(news[-1]): news.append('zn<exile>')
                else: news.append(tkn)
            except IndexError:
                news.append(tkn)
            continue

        # c) ka<counter> is a keyword action or refers to a counter. In counter
        # spells, the word counter is followed by a quantifier. Additionally,
        # the phrase cannot be countered (cn<cannot>, be, ka<counter>) referes
        # to the keyword action
        if tkn == 'ka<counter>':
            try:
                if mtgl.is_quantifier(olds[i+1]) or\
                        news[i-2:i] == ['cn<cannot>','be']:
                    news.append(tkn)
                else: news.append('xo<ctr>')
            except IndexError:
                news.append('xo<ctr>')
            continue

        # d) ka<vote> vote appears often in cards relating to voting. We could
        # take the "strict" interpretation but since we don't yet do that for
        # other keyword-actions we will change cases of the form
        # "tied for the most votes", "gets more votes", "vote is tied"
        # TODO: it doesn't catch for each x vote see Expropriate
        if tkn == 'ka<vote>':
            try:
                if news and news[-1] == 'most': news.append('vote')
                elif news and news[-1] == 'more': news.append('vote')
                elif olds[i+1:i+3] == ['is','tied']: news.append('vote')
                else: news.append(tkn)
            except IndexError:
                news.append('vote')
            continue

        # d) 'ph<xa<draw> step>' is a phase, remove the draw as an action

        # e) activate and trigger are actions unless followed by ob<ability>
        #if tkn == 'ka<activate>' or tkn == 'xa<trigger>':
        #    try:
        #        if mtgl.is_mtg_obj(olds[i+1]) and\
        #                mtgl.untag(olds[i+1])[1] != 'ability':
        #            ch = mtgl.untag(tkn)[1]
        #            ch = ch + 'd' if ch[-1] == 'e' else ch + 'ed'
        #            news.append(mtgl.retag('ch',ch,{}))
        #            continue
        #    except IndexError: pass

        # (4) combine numeric phrases
        if mtgl.is_number(tkn):
            # check for 'or' followed by 'more' or 'less'
            try:
                op = None
                if ll.subl(['or','less'],olds[i+1:]) == 0: op = mtgl.LE
                elif ll.subl(['or','more'],olds[i+1:]) == 0: op = mtgl.GE
                if op:
                    news.append("nu<{}{}>".format(op,mtgl.untag(tkn)[1]))
                    skip = 2
                    continue
            except IndexError: pass

        # append the token
        news.append(tkn)

    return news

def chain(olds):
    """
     combines charcteristics belonging to an object, creating an implied object
     if necessary - characteristics will occur prior to the object (if there is one)
     :param olds: the current list of tokens
     :return: chained list of tokens

     NOTE:
      Perceived "rules" regarding and'ed, or'ed sequences of characterisitics
      along with uses of commas in MTG oracle text are:
      1. chained characteristics are always either all 'anded' or all 'ored'
      2. chained characteristics will precede the object (if there is one)
       a. token, while an object (109), acts as a characterisitic
      3. 'and' chains are (almost always) space delimited
       a. any comma signifies distinct objects vice a sequence
       b. two items may be 'and'ed if there are no commas
       c. two characteristics may be comma 'and'ed if they are followed by a
          object i.e. type, type obj and the types are negated
      4. 'or' chains will contain the word 'or' and will be comma delimited
       for chains of more than 2 characterisitcs
    """
    news = []              # new tokens
    cs = []                # list of characterisitcs
    pt = None              # power/toughness
    op = mtgl.AND          # the chain operator
    ti = 'ob'              # tag-id
    tp = "characteristics" # prop-list key

    for i,tkn in enumerate(olds):
        if mtgl.is_mtg_char(tkn):
            # only chain meta characteristics if they are p/t (& not incr/decr)
            # and not part of a level symbol
            _,v,p = mtgl.untag(tkn)
            if mtgl.is_meta_char(tkn):
                try:
                    if v == 'p/t' and not mtgl.is_lituus_act(news[-1]):
                        pt = p['val']
                    else: news.append(tkn)
                except IndexError:
                    news.append(tkn)
            else: cs.append(v)
        else:
            # current token is not a characterisitic. If we're not in a chain,
            # append the token otherwise determine how to treat the token
            if not cs: news.append(tkn) # not in chain, append the token
            else:
                # we are in a current chain
                if tkn == ',':
                    nop = _comma_read_ahead_(olds[i:])
                    if nop == mtgl.AND or nop == ',': # distinct objects
                        pl = {tp:op.join(cs)}
                        if pt: pl['meta'] = 'p/t'+mtgl.EQ+pt
                        news.append(mtgl.retag(ti,_implied_obj_(cs),pl))
                        news.append(',')
                        op = mtgl.AND
                        cs = []
                        pt = None
                    else: op = mtgl.OR
                elif tkn == 'or': op = mtgl.OR
                elif tkn == 'and':
                    # have to read ahead. if next token is not a characteristic,
                    # need to close out the current chain, and append the 'and'
                    # otherwise just set the op and continue
                    if _chained_and_(i,olds): op = mtgl.AND
                    else:
                        pl = {tp:op.join(cs)}
                        if pt: pl['meta'] = 'p/t'+mtgl.EQ+pt
                        news.append(mtgl.retag(ti,_implied_obj_(cs),pl))
                        news.append(tkn)
                        op = mtgl.AND
                        cs = []
                        pt = None
                elif mtgl.is_mtg_obj(tkn):
                    t,v,p = mtgl.untag(tkn)              # untag it
                    p[tp] = op.join(cs)                  # update it's prop list
                    if pt: p['meta'] = 'p/t'+mtgl.EQ+pt  # & meta if present
                    news.append(mtgl.retag(t,v,p))       # retag and append
                    op = mtgl.AND                        # and reset the chain
                    cs = []
                    pt = None
                else:
                    # no object, end the chain and append the implied object
                    pl = {tp:op.join(cs)}
                    if pt: pl['meta'] = 'p/t'+mtgl.EQ+pt
                    news.append(mtgl.retag(ti,_implied_obj_(cs),pl))
                    news.append(tkn)
                    op = mtgl.AND
                    cs = []
                    pt = None

    # if unbuilt chain remains, build/append the object then return the new tkns
    # p/t should never be present if other characteristics are not present
    if cs:
        pl = {tp:mtgl.AND.join(cs)}
        if pt: pl['meta'] = 'p/t'+mtgl.EQ+pt
        news.append(mtgl.retag(ti,_implied_obj_(cs),pl))
    return news

def _comma_read_ahead_(tkns):
    """
     reads ahead to determine how a comma will be processed in the current chain
    :param tkns: the list of tokens
    :return: mtgl.AND if it is a list of and'ed characteristics, mtgl.OR if it
     is a list of or'ed characteristcs or ',' if neither
    """
    # read ahead until we find 'or' or 'and' or a non-characteristic
    for i,tkn in enumerate(tkns):
        try:
            if tkn == 'or':
                if not mtgl.is_mtg_obj(tkns[i+1]): return mtgl.CMA
                else: return mtgl.OR
            elif tkn == 'and': return mtgl.AND
            elif tkn == ',': continue # skip the commas
            elif not mtgl.is_mtg_char(tkn): return mtgl.CMA
        except IndexError:
            pass
    return mtgl.CMA

def _chained_and_(i,tkns):
    """
     reads ahead to determine how an 'and' inside a chain should be processed
    :param i: the current index into tkns
    :param tkns: the list of tokens
    :return: True if the and should be chained, False otherwise
    """
    try:
        if not mtgl.is_property(tkns[i+1]): return False
        else: return True
    except IndexError:
        pass
    return False # shouldn't get here but just in case

def _implied_obj_(cs):
    """
     determines from the chain of characterisitcs if the implied object is
     a card or pormenent
    :param cs: chain of characterisitcs
    :return: the implied object
    """
    # 109.2 if there is a reference to a type or subtype but not card,
    # spell or source, it means a permanent of that type/subtype
    for c in cs:
        x = c.replace(mtgl.NOT,'') # remove any nots
        if x in mtgl.type_characteristics+mtgl.sub_characteristics:
            return 'permanent'
    return 'card'

def chain_zones(olds):
    """
     combines anded zones creating an a single zone
     :param olds: the current list of tokens
     :return: list of tokens with zones chained
    """
    news = []
    skip = 0

    for i,tkn in enumerate(olds):
        # skip already processed tokens
        if skip:
            skip -= 1
            continue

        if mtgl.is_zone(tkn):
            # 'and has two cases (1) zone1 and zone2 (2) zone1, zone2, and zone3
            # possible to get an (3) and/or ('op<⊕>')
            try:
                # case 1 and case 3
                if olds[i+1] in ['and','op<⊕>'] and mtgl.is_zone(olds[i+2]):
                    # untag both zones
                    z1 = mtgl.untag(tkn)[1]
                    z2 = mtgl.untag(olds[i+2])[1]

                    # determine the operator to use
                    op = mtgl.AND if olds[i+1] == 'and' else mtgl.AOR
                    news.append(mtgl.retag('zn',z1+op+z2,{}))
                    skip = 2
                    continue

                # case 2
                case2 = [mtgl.CMA,mtgl.is_zone,mtgl.CMA,'and',mtgl.is_zone]
                if ll.matchl(case2,olds,1) == 1:
                    zs = [
                        mtgl.untag(tkn)[1],
                        mtgl.untag(olds[i+2])[1],
                        mtgl.untag(olds[i+5])[1]
                    ]
                    news.append(mtgl.retag('zn',mtgl.AND.join(zs),{}))
                    skip = 5
                    continue
            except IndexError:
                pass
        news.append(tkn)
    return news

def group(olds):
    """
     similar to chain, groups sequence of status(es) and/or quanitifiers with
     corresponding object. Unlike characteristics however, these properties
     require an object.
    :param olds: the current tokens
    :return: the new tokens after grouping
    """
    news = []

    # check each token, if it's an object look back at preceding for status and
    # or quantifier tags
    for tkn in olds:
        if mtgl.is_thing(tkn):
            qs = []        # quanitifier sequence
            ss = None      # status list
            sop = mtgl.AND # status operator
            n = None       # number specifier
            while len(news) > 0:
                # check for preceding meta-characteristics quanitifiers, status
                if mtgl.is_number(news[-1]): n = mtgl.untag(news.pop())[1]
                elif news[-1] == 'a': qs.append(news.pop())
                elif mtgl.is_quantifier(news[-1]):
                    qs.append(mtgl.untag(news.pop())[1])
                elif mtgl.is_state(news[-1]):
                    # found a status - may be and'ed or or'ed
                    ss = [mtgl.untag(news.pop())[1]]
                    while len(news) >= 1:
                        if mtgl.is_state(news[-1]):
                            ss.append(mtgl.untag(news.pop())[1])
                        elif news[-1] == 'or' and mtgl.is_state(news[-2]):
                            news.pop()
                            sop = mtgl.OR
                        elif news[-1] == 'and' and mtgl.is_state(news[-2]):
                            news.pop()
                        else: break
                else: break

            # add status/quantifiers found
            if qs or ss or n:
                # untag the object and add status/quantifiers found
                t,v,p = mtgl.untag(tkn)
                if qs:
                    qs = mtgl.AND.join(qs)
                    if 'quantifier' in p: p['quantifier'] += mtgl.AND + qs
                    else: p['quantifier'] = qs
                if ss:
                    if 'status' in p: p['status'] += mtgl.AND + sop.join(ss)
                    else: p['status'] = sop.join(ss)
                if n: p['num'] = n
                news.append(mtgl.retag(t,v,p))
            else: news.append(tkn)
        else: news.append(tkn)
    return news

def add_hanging(olds):
    """
     adds any hanging meta characterisitics, status to an object and the seq.
     pr<in> zn<ZONE> to objects
    :param olds: the current mtgl
    :return: updated mtgl w/ hanging meta characteristics, status added to objs
    """
    news = []
    skip = 0

    for i,tkn in enumerate(olds):
        # skip already processed tokens
        if skip:
            skip -= 1
            continue

        if tkn == 'pr<with>' or tkn == 'pr<without>':
            # if the last token added is an object untag it
            if news and mtgl.is_mtg_obj(news[-1]):
                ot,ov,ops = mtgl.untag(news[-1])

                # two possibilities following the with/without
                #  keywords - the next 'phrase' is "kw<KW>" or "kw<KW> and kw<KW>"
                #   we assume there won't be 'or'ed keywords or more than 2
                #  NOTE: we have to check the double kw first
                #  meta - the next 'phrase' is ch<META> op<OP> nu<NU>
                skw = [mtgl.is_keyword]
                dkw = [mtgl.is_keyword,'and',mtgl.is_keyword]
                meta = [mtgl.is_meta_char,mtgl.is_operator,mtgl.is_number]

                if ll.matchl(dkw,olds[i+1:],0) == 0:
                    assert(tkn == 'pr<with>') # shouldn't have a neg in this case
                    # pull out both keywords and combine
                    kw = mtgl.AND.join(
                        [mtgl.untag(olds[i+1])[1],mtgl.untag(olds[i+3])[1]]
                    )

                    # add the keyword to the objects meta or create meta parameter
                    if 'meta' in ops: ops['meta'] += mtgl.AND + kw
                    else: ops['meta'] = kw

                    # retags and appends the popped object)
                    news.pop()
                    news.append(mtgl.retag(ot,ov,ops))
                    skip = 3
                    continue
                elif ll.matchl(skw,olds[i+1:],0) == 0:
                    # single keyword, extract it, & check if should be negative
                    kw = mtgl.untag(olds[i+1])[1]
                    neg = '' if tkn == 'pr<with>' else mtgl.NOT

                    # add the keyword to the objects meta or create meta parameter
                    if 'meta' in ops: ops['meta'] += mtgl.AND + neg + kw
                    else: ops['meta'] = kw

                    # retags and appends the popped object)
                    news.pop()
                    news.append(mtgl.retag(ot,ov,ops))
                    skip = 1
                    continue
                elif ll.matchl(meta,olds[i+1],0) == 0:
                    # 2) meta op number
                    mv = mtgl.untag(olds[i+1])[1] # untag the meta characteristic
                    ov = mtgl.untag(olds[i+2])[1] # and the operator
                    nv= mtgl.untag(olds[i+3])[1] # and the number

                    # check if obj already has a meta parameter
                    if 'meta' in ops: ops['meta'] += mtgl.AND + mv + ov + nv
                    else: ops['meta'] = mv + ov + nv
                    # retags and appends the popped object)
                    news.pop()
                    news.append(mtgl.retag(ot,ov,ops))
                    skip = 3
                    continue

                # if nothing happens, the preposition will fall through and
                # be added
        elif mtgl.is_state(tkn):
            # untag the last token added and verify it's an object
            try:
                t,v,p = mtgl.untag(news[-1])
                if t == 'ob':
                    # untag the current, saving the 'status' value
                    ss = [mtgl.untag(tkn)[1]]
                    op = mtgl.AND

                    # read ahead while and/or and status are present
                    j = i+1
                    while True:
                        try:
                            if mtgl.is_state(olds[j]):
                                ss.append(mtgl.untag(olds[j])[1])
                                skip += 1
                                j += 1
                            elif olds[j] == 'or':
                                op = mtgl.OR
                                skip += 1
                                j += 1
                            elif olds[j] == 'and':
                                skip += 1
                                j += 1
                            else: break
                        except IndexError:
                            break

                    # add the status(es)
                    if 'status' in p: p['status'] += op.join(ss)
                    else: p['status'] = op.join(ss)
                    news.pop()
                    news.append(mtgl.retag(t,v,p))
                    continue
            except mtgl.MTGLTagException: pass
        elif tkn == 'xc<devotion>':
            # look for devotion 'clauses' - devotion will be of the form:
            #  xp<PLY> xc<devotion> pr<to> ob<card characteristics=CH>
            # and although currently worded only for xp<you>, we will consider
            # any player as viable
            try:
                # last added will be xp, next 2 will be pr<to> and ch<...>
                if mtgl.is_player(news[-1]) and olds[i+1] == 'pr<to>' and\
                        mtgl.is_mtg_obj(olds[i+2]):
                    # for devotion, player should be simple & characteristics
                    # should be a color(s)
                    ply = mtgl.untag(news.pop())[1] # should always be 'you'
                    ps = mtgl.untag(olds[i+2])[2]
                    news.append(
                        mtgl.retag('xp',ply,{'devotion':ps['characteristics']})
                    )
                    skip = 2
                    continue
            except mtgl.MTGLTagException: pass
            except (IndexError,ValueError): pass
        elif mtgl.is_zone(tkn):
            # check if we have a phrase ob<OBJECT> pr<in> zn<ZONE>
            try:
                if mtgl.is_mtg_obj(news[-2]) and news[-1] == 'pr<in>':
                    # untag the zone and get owner or quantifer
                    t,v,ps = mtgl.untag(tkn)
                    assert(not('quantifier' in ps and 'player' in ps))
                    p = None
                    if 'quantifier' in ps: p = ps['quantifier']
                    elif 'player' in ps: p = ps['player']

                    # untag the existing object (make it zone->player or
                    # zone->quantifier) and add to that object
                    news.pop() # pop the preposition
                    ot,ov,ops = mtgl.untag(news.pop())

                    if p: ops['zone'] = '{}{}{}'.format(v,mtgl.ARW,p)
                    else: ops['zone'] = v

                    # add the ob back to news
                    news.append(mtgl.retag(ot,ov,ops))
                    continue
            except IndexError: pass
        news.append(tkn)
    return news

def merge_possessive(olds):
    """
     combines possesive with corresponding object (if there is one) and
     possessive with corresponding zones (if there is one)
    :param olds: current list of tokens
    :return: the updated list of tokens
    """
    news = []
    skip = 0
    for i,tkn in enumerate(olds):
        # skip tokens if necessary
        if skip:
            skip -= 1
            continue

        if mtgl.is_mtg_obj(tkn):
            # after chaining/grouping, objects that have possesives
            # will be follwed by player xc<[not]control|own>
            try:
                if mtgl.is_player(olds[i+1]) and _is_possessive_(olds[i+2]):
                    ot,ov,op = mtgl.untag(tkn)          # object tag
                    pt,pv,pp = mtgl.untag(olds[i+1])    # player tag
                    _,v,_ = mtgl.untag(olds[i+2])       # possessive tag

                    # is the possessive negated? if so, strip it out
                    neg = mtgl.NOT in v
                    if neg: v = v[1:]

                    # determine property
                    prop = 'controller' if v == 'control' else 'owner'

                    # process 'you' and player/opponent differently
                    if pv == 'you':
                        if neg: pv = 'opponent' # make opponent if negated
                        assert(prop not in op)  # (shouldn't already have a possessive)
                        op[prop] = pv
                        news.append(mtgl.retag(ot,ov,op))
                    else:
                        if not 'quantifier' in pp: val = pv
                        else: val = pp['quantifier'] + mtgl.AND + pv
                        assert(prop not in op)
                        op[prop] = val
                        news.append(mtgl.retag(ot,ov,op))

                    # skip the merged tokens
                    skip = 2
                    continue
            except IndexError: pass
        elif mtgl.is_player(tkn):
            # after chaining/grouping, players that possess a zone will be
            # followed by the zone
            try:
                if mtgl.is_zone(olds[i+1]):
                    pt,pv,pp = mtgl.untag(tkn)
                    zt,zv,_ = mtgl.untag(olds[i+1]) # shouldnt be a prop-list
                    if not 'quantifier' in pp: val = pv
                    else: val = pp['quantifier'] + mtgl.AND + pv

                    # it's possible that we have also have an it preceding this
                    # see Guile "... ts owner's library."
                    # before adding the zone, run a check and pop if necessary
                    if news and news[-1] == 'xo<it>': news.pop()

                    # add the zone to news
                    news.append(mtgl.retag(zt,zv,{'player':val}))
                    skip = 1 # skip the next token (the zone)

                    continue
            except IndexError: pass

        # no possessive, just append the token
        news.append(tkn)
    return news

def _is_possessive_(tkn):
    """
     determines if the lituus_characteristic (xc) is possesive i.e. contains
     own or control
    :param tkn: token to check
    :return: True if possessive, False otherwise
    """
    if mtgl.is_lituus_char(tkn) and ('control' in tkn or 'own' in tkn):
        return True
    return False