#!/usr/bin/env python
""" parser.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Parses tagged oracle text and resolves tagger errors using contextual information
"""

#__name__ = 'parser'
__license__ = 'GPLv3'
__version__ = '0.1.9'
__date__ = 'September 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
import lituus.mtgl.list_util as ll
import lituus.mtgl.mtgl as mtgl

# constants/helpers
re_draft = re.compile(r"draft(ing|ed)?")

def parse(txt):
    """
    parses the tokenized text of card into mtgl
    :param txt: tagged and tokenized text
    returns the parsed oracle text
    """
    ptxt = []
    for i,line in enumerate(txt):
        try:
            # check for reference to 'draft' in the line. if so, drop the line
            if ll.matchl([re_draft],line) > -1: continue
            line = rectify(line)
            line = chain(line)
            line = chain_zones(line)
            line = group(line)
            line = add_hanging(line)
            line = merge_possessive(line)
            ptxt.append(line)
        except Exception as e: # generic catchall for debugging purposes
            raise mtgl.MTGLException("Parse failure {} at line {}.".format(type(e),i))
    return ptxt

def rectify(olds):
    """
     fixes several issues.
      1. token (non)token is the only top-level object from rule 109 but acts
        like a a chracteristic.
      2. or'ed and and'ed objects (primarily/only spells or abilities) need to be
       combined
      3. double tagged an mis-tagged require context to be fixed
      4. combines phrases like nu<1> or more or nu<10> or less into a single
       nu tag
      5. miscellaneous fixes that assist in parsing and graphing
    :param olds: the current list of tokens
    :return: tokens with subsequent entities merged
    """
    # 5. before enumerating the tokens we'll make some list replacements

    # a. combined or'ed activated, triggered status (see Stifle
    olds = ll.replacel(
        olds,['xs<activated>','or','xs<triggered>'],['xs<activated∨triggered>']
    )

    # b. combine xo<it> xp<...> and xp<their> xp<...>
    i = ll.matchl([ll.ors(['xo<it>','xp<their>']),mtgl.is_player],olds)
    while i > -1:
        t,v,ps = mtgl.untag(olds[i+1])
        ps['of'] = 'it' if olds[i] == 'xo<it>' else 'them' # add of=? to proplist
        olds[i:i+2] = [mtgl.retag(t,v,ps)]                 # retag
        i = ll.matchl([ll.ors(['xo<it>', 'xp<their>']),mtgl.is_player],olds)

    news = []
    skip = 0
    for i,tkn in enumerate(olds):
        # skip any tokens that have already been processed
        if skip:
            skip -= 1
            continue

        # check 1 and 2 here if current token is an object
        if mtgl.is_mtg_obj(tkn):
            # (1) move (non)token to right of characteristics
            if 'token' in tkn and ll.matchl([mtgl.is_mtg_char],olds[i:],1) == 1:
                j = i+1
                while ll.matchl([mtgl.is_mtg_char],olds[j:],0) == 0:
                    news.append(olds[j])
                    j += 1
                skip = (j-i)-1
                news.append(tkn)
                continue

            # (2) make two and'ed/or'ed 'consecutive' singleton objs one
            if ll.matchl([mtgl.is_coordinator,mtgl.is_mtg_obj],olds[i:],1) == 1:
                # see Glyph Keeper (spell or ability)
                t,v,p = mtgl.untag(olds[i+2])
                if not p: # don't join anything with a prop list
                    if olds[i+1] == 'or': op = mtgl.OR
                    elif olds[i+1] == 'and': op = mtgl.AND
                    else: op = mtgl.AOR
                    news.append(mtgl.retag(
                        t,"{}{}{}".format(mtgl.untag(tkn)[1],op,v),{})
                    )
                    skip = 2
                    continue

        # (3) determine if
        # a) 'copy' is always tagged as an ob because lituus actions check for an
        # existing tag before tagging. If it's followed by an object
        # or quantifier, then its an action (lituus) otherwise its an object
        if tkn == 'ob<copy>':
            # copy quantifier spell|ability, copy quantifier instant|sorcery

            if ll.matchl([mtgl.is_quantifier,mtgl.is_mtg_obj],olds[i:],1) == 1:
                news.append('xa<copy>')
            elif ll.matchl([mtgl.is_quantifier,mtgl.is_mtg_char],olds[i:],1) == 1:
                news.append('xa<copy>')
            elif ll.matchl(['xo<it>'],olds[i:],1) == 1:
                # i.e. copy it
                news.append('xa<copy>')
            else:
                # last check, looking for a phrase "copy the ob<...>" where the
                # value of ob is spell. Also looking for one of two phrases
                # in the already added tokens 'you may' or 'spell,'
                j = ll.matchl(['xp<you>','cn<may>'],news)
                k = ll.matchl(['ob<spell>', mtgl.CMA],news)
                if j > -1 and i-j == 2: news.append('xa<copy>')
                elif k > -1 and i-k == 2: news.append('xa<copy>')
                elif ll.matchl(['the',mtgl.is_mtg_obj],olds[i:],1) == 1:
                    _,v,ps = mtgl.untag(olds[i+2])
                    if v == 'spell': news.append('xa<copy>')
                    else: news.append('ob<copy>')
                else:
                    news.append('ob<copy>')
            continue

        # b) target (114)
        if tkn == 'xq<target>':
            # target could be a:
            #  1. action 'that targets one or more creatures'
            #  2. quantifier 'destroy target creature'
            #  3. object 'can't be the target of spells or abilities'
            # Although as an object, it presence in non-reminder text is limtited

            # NOTE: by using the slice "-n:" we avoid index errors

            if ll.matchl(['cn<cannot>','be','the'],news[-3:]) == 0:
                # check conversion to object first. The full phrase is "cannot be
                # the target of..."  but we can check news for "cannot be the".
                news.append('xo<target>')
            elif ll.matchl([ll.ors(['becomes','change']),'the'],news[-2:]) == 0:
                # another conversion to object requires checking for 'becomes' or
                # 'change' prior to the
                news.append('xo<target>')
            elif ll.matchl(['pr<with>','a','single'],news[-3:]) == 0:
                # look for "with a single"
                # TODO: are there cases where 'single' is not present or different
                news.append('xo<target>')
            elif ll.matchl(['new'],news[-1:]) == 0:
                # last object check if the preceding word is new
                news.append('xo<target>')
            elif ll.matchl([ll.ors(['xq<that>','could','ob<copy>'])],news[-1:]) == 0:
                # determine if 'target' is an action, the easiest is to check the
                # preceding tokens if we find, 'that', 'could' or 'copy' it's an
                # action NOTE: based on the assumption that rectify has correctly
                # fixed copy tokens
                news.append('xa<target>')
            else:
                news.append('xq<target>')
            continue

        # c) ka<exile> is an action or a zone. If its preceded by a preposition
        # change it to zone, otherwise leave it alone
        if tkn == 'ka<exile>':
            try:
                if mtgl.is_preposition(news[-1]): news.append('zn<exile>')
                else: news.append(tkn)
            except IndexError:
                news.append(tkn)
            continue

        # d) ka<counter> is a keyword action or refers to a counter. In counter
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

        # e) ka<vote> vote appears often in cards relating to voting. We could
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

        # f) activate/trigger mtgl and tagger do remove conjugations from activated
        # (& triggered) so we end up with both 'activate' and 'activated' where
        # activated is tagged as a status. see Cursed Totem. Here the first activated
        # is a status but the last activated should be rectified to an action
        if tkn == 'xs<activated>' or tkn == 'xs<triggered>':
            # create the tag and value if we have to change the token
            if tkn == 'xs<activated>':
                t = 'ka' # activate is recognized in the rules as a KWA
                v = 'activate'
            else:
                t = 'xa' # trigger is not recognized
                v = 'trigger'

            # if the next token is an object we have a status otherwise, we should
            # retag as an action
            if ll.matchl([mtgl.is_mtg_obj],olds[i:],1) != 1:
                news.append(mtgl.retag(t,v,{}))
            else: news.append(tkn)
            continue

        # (4) combine numeric phrases
        if mtgl.is_number(tkn):
            # check for 'or' followed by 'more' or 'less'
            try:
                op = None
                if ll.matchl(['or','less'],olds[i+1:]) == 0: op = mtgl.LE
                elif ll.matchl(['or','more'],olds[i+1:]) == 0: op = mtgl.GE
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
     Also takes care of card name card like phrases (see Hanweir Battlements)
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
            if not mtgl.is_meta_char(tkn): cs.append(v)
            else:
                if v == 'p/t' and news and not mtgl.is_lituus_act(news[-1]):
                    pt = p['val']
                else:
                    # close out the chain if its open
                    if cs:
                        pl = {tp:op.join(cs)}
                        if pt: pl['meta'] = 'p/t' + mtgl.EQ + pt
                        news.append(mtgl.retag(ti,_implied_obj_(cs),pl))
                        op = mtgl.AND
                        cs = []
                        pt = None

                    # then add the token
                    news.append(tkn)
        else:
            # current token is not a characterisitic. If we're not in a chain,
            # append the token otherwise determine how to treat the token
            if not cs: news.append(tkn) # not in chain, append the token
            else:
                # we are in a current chain
                if tkn == ',':
                    nop = _comma_read_ahead_(olds[i:])
                    # see grapher->collate, the rules for determining if objects
                    # should be chained is cumbersome. we'll use basic hueristics
                    # here and allow the grapher to apply the additional rules
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

    # combine card named card and variants. Looking for ob<card> name ob<card...>
    # or ch<...> named ob<card...> these phrases will be combined into a single
    # token. This is performed here because characteristics will have been tagged
    # as an object (Hanweir Battlements has 'creature named ...' at this point
    # is now ob<permanent characteristics=creature> named ..." which is easier
    # to process. Additionaly, if not done here it will be much harder to later
    cnc = [mtgl.is_mtg_obj,'named',mtgl.is_mtg_obj]
    i = ll.matchl(cnc,news)
    while i > -1:
        # the first token should be a permanent with a type in the characteristics
        # attribute. if not, it should be ob<card>
        t1,v1,ps1 = mtgl.untag(news[i])
        ctype = ps1['characteristics'] if 'characteristics' in ps1 else None

        # the last token should be a ob<card...> with a ref attribute
        # TODO: right now, just exiting the loop if it doesn't meet the criteria,
        #  (see Goblin Kaboomist, King Macar) but will have to code in the
        #  appropriate change
        t2,v2,ps2 = mtgl.untag(news[i+2])
        if t1 != t2 or 'ref' not in ps2: break

        # create a new token using the val from the first, the prop list from
        # the second (adding characterstics from the first one)
        if ctype:
            # shouldn't be chcaracteristics in the 2nd object but just in case
            try:
                ps2['characteristics'] += mtgl.AND + ctype
            except KeyError:
                ps2['characteristics'] = ctype
        news[i:i+3] = [mtgl.retag(t1,v1,ps2)]

        # check for more
        i = ll.matchl(cnc,news)

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
        if tkn == 'or':
            if ll.matchl([mtgl.is_mtg_char,mtgl.is_mtg_obj],tkns[i:],1) == 1:
                return mtgl.OR
            else: return mtgl.CMA
        elif tkn == 'and': return mtgl.AND
        elif tkn == ',': continue # skip the commas
        elif not mtgl.is_mtg_char(tkn): return mtgl.CMA
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
            # TODO: make sure this is working as expected
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
            # will be follwed by xp<player> xc<[not]control|own>
            if ll.matchl([mtgl.is_player,is_possessive],olds[i:],1) == 1:
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
                    op[prop] = pv
                    news.append(mtgl.retag(ot,ov,op))
                else:
                    # if there is a quantifier, AND it with player
                    if not 'quantifier' in pp: val = pv
                    else: val = pp['quantifier'] + mtgl.AND + pv

                    # does the player have a status?
                    # TODO: 1. haven't seen any players with a status and
                    #  quantifier 2. several ways to add status, could use
                    #  AND or ARW or wrap in parenthesis etc - which is best?
                    if 'status' in pp: val = pp['status'] + mtgl.AND + val
                    op[prop] = val
                    news.append(mtgl.retag(ot,ov,op))

                # skip the merged tokens
                skip = 2
                continue
        elif mtgl.is_player(tkn):
            # after chaining/grouping, players that possess a zone will be
            # followed by the zone
            try:
                if mtgl.is_zone(olds[i+1]):
                    pt,pv,pps = mtgl.untag(tkn)
                    zt,zv,_ = mtgl.untag(olds[i+1]) # shouldnt be a prop-list

                    # check for quantifiers in the plaer
                    if not 'quantifier' in pps: val = pv
                    else: val = pps['quantifier'] + mtgl.AND + pv

                    # check for 'of' in the player (looking for xp<owner of=it>
                    if 'of' in pps: val = pps['of'] + mtgl.ARW + val

                    # add the zone to news
                    news.append(mtgl.retag(zt,zv,{'player':val}))
                    skip = 1 # skip the next token (the zone)

                    continue
            except IndexError: pass

        # no possessive, just append the token
        news.append(tkn)
    return news

def is_possessive(tkn):
    """
     determines if the lituus_characteristic (xc) is possesive i.e. contains
     own or control
    :param tkn: token to check
    :return: True if possessive, False otherwise
    """
    if mtgl.is_lituus_char(tkn) and ('control' in tkn or 'own' in tkn):
        return True
    return False