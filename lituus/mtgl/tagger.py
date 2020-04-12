#!/usr/bin/env python
""" tagger.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Tags MTG oracle text in the mtgl format
"""

#__name__ = 'tagger'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
import lituus as lts
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.lexer as lexer
import lituus.mtgl.mtgltag as mtgltag

def tag(name,txt):
    """
     tags the mtgl oracle
    :param name: name of card
    :param txt: the mtgl text
    :return: tagged mtgl text
    """
    try:
        ntxt = preprocess(name,txt)
        ntxt = first_pass(ntxt)
        ntxt = midprocess(ntxt)
        ntxt = second_pass(ntxt)
    except (lts.LituusException,re.error) as e:
        raise lts.LituusException(
            lts.ETAGGING,"Tagging {} failed due to {}".format(name,e)
        )
    except Exception as e:
        raise lts.LituusException(
            lts.EUNDEF,"Unexpected error tagging {} due to {}".format(name,e)
        )
    return ntxt

####
## PREPROCESSING
####

def preprocess(name,txt):
    """
     conducts an initial scrub of the oracle text. Then:
       1. replaces card name references with ref-id or self as necessary
       2. lowercases everything
       3. standardize keywords, cycling and landwalk
       4. hack words with anamolies contractions, etc
       5. english number words 0 - 10 are replacing with corresponding ints,
       6. Some reminder text is removed, some paraenthesis is removed
       7. replace any 'non' w/out hypen to 'non-' w/ hyphen
    :param name: name of this card
    :param txt: the mtgl text
    :return: preprocessed oracle text
    """
    # a keyword
    ntxt = tag_ref(name,txt).lower()                                         # 1 & 2
    ntxt = mtgl.re_cycling_pre.sub(r"\1 cycling",ntxt)                       # 3
    ntxt = mtgl.re_landwalk_pre.sub(r"\1 landwalk",ntxt)                     # 3
    ntxt = mtgl.re_word_hack.sub(lambda m: mtgl.word_hacks[m.group(1)],ntxt) # 4
    ntxt = mtgl.re_wd2int.sub(lambda m: mtgl.E2I[m.group(1)],ntxt)           # 5
    ntxt = mtgl.re_mana_remtxt.sub(r"\1",ntxt)                               # 6
    ntxt = mtgl.re_rem_txt.sub("",ntxt)                                      # 6
    ntxt = mtgl.re_non.sub(r"non-\1", ntxt)                                  # 7
    return ntxt

def tag_ref(name,txt):
    """
     replace occurrences of words in txt that refer to "this card" and names of
     other cards with the ref-id
    :param name: name of card
    :param txt: oracle text
    :return: reference tagged oracle text
    NOTE: this does not handle words like "it" that require contextual understanding
     to determine if "it" referes to this card or something else
    """
    # replace self references
    ntxt = mtgl.re_self_ref(name).sub(r"ob<card ref=self>",txt)

    # token names
    ntxt = mtgl.re_tkn_ref1.sub(
        lambda m: r"{} ob<token ref={}>".format(
            m.group(1),mtgl.TN2R[m.group(2)]),ntxt
    )
    ntxt = mtgl.re_tkn_ref2.sub(
        lambda m: r"create ob<token ref={}>, {} token".format(
            mtgl.TN2R[m.group(1)],m.group(2)
        ),ntxt
    )

    # meld tokens from Eldritch Moon
    ntxt = mtgl.re_tkn_ref3.sub(
        lambda m: r"ob<token ref={}>".format(mtgl.MN2R[m.group(1)]),ntxt
    )

    # references to other cards prefixed with 'named' or 'Partner with'
    # This does not catch cases where there is an 'and' i.e. Throne of Empires
    #  "... named Crown of Empires and Scepter of Empires. For now, have to hack
    #  it using mtgl.re_oth_ref2
    ntxt = mtgl.re_oth_ref.sub(
        lambda m: r"{} ob<card ref={}>".format(m.group(1),mtgl.N2R[m.group(2)]),ntxt
    )
    ntxt = mtgl.re_oth_ref2.sub(
        lambda m: r"ob<token ref={}>".format(mtgl.NC2R[m.group(1)]),ntxt
    )
    return ntxt

####
# 1ST PASS
####

def first_pass(txt):
    """
     performs a first pass of the oracle txt after pre-processing, tagging mtg
     'reserved' words and lituus 'reserved' words. does not consider context
    :param txt: preprocessed oracle txt (lowered case)
    :return: tagged oracle text
     NOTE: many (but not all) of the below require certain replacements/tagging
      to be carried out prior to their execution, rearranging the order of the
      below will negatively effect the results
    """
    ntxt = mtgl.re_quantifier.sub(r"xq<\1>",txt) # tag quantifiers
    ntxt = mtgl.re_number.sub(r"nu<\1>",ntxt)    # then nubmers
    ntxt = tag_entities(ntxt)                    # entities
    ntxt = tag_turn_structure(ntxt)              # phases & steps
    ntxt = tag_english(ntxt)                     # english words
    ntxt = mtgl.re_trigger.sub(r"tp<\1>",ntxt)   # trigger preambles
    ntxt = tag_counters(ntxt)                    # markers
    ntxt = tag_awkws(ntxt)                       # ability words, keywords & actions
    ntxt = mtgl.re_effect.sub(r"ef<\1>",ntxt)    # effects
    ntxt = tag_characteristics(ntxt)             # chars. - done after #s
    ntxt = mtgl.re_zone.sub(r"zn<\1>",ntxt)      # zones
    return ntxt

def tag_entities(txt):
    """ tags entities (players & objects returntning tagged txt """
    ntxt = mtgl.re_obj.sub(r"ob<\1>",txt)          # tag mtg objects
    ntxt = mtgl.re_lituus_obj.sub(r"xo<\1>",ntxt)  # tag lituus objects
    ntxt = mtgl.re_lituus_ply.sub(r"xp<\1>",ntxt)  # tag players
    return ntxt

def tag_turn_structure(txt):
    """ tags turn structure phrases in txt returning tagged text """
    ntxt = mtgl.re_phase.sub(r"ts<\1>",txt)
    ntxt = mtgl.re_step1.sub(r"ts<\1>",ntxt)
    ntxt = mtgl.re_step2.sub(r"ts<\1>",ntxt)
    ntxt = mtgl.re_generic_turn.sub(r"ts<\1>",ntxt)
    return ntxt

def tag_english(txt):
    """ tags important english words """
    ntxt = mtgl.re_op.sub(lambda m: "op<{}>".format(mtgl.OP[m.group(1)]),txt) # operators
    ntxt = mtgl.re_prep.sub(r"pr<\1>",ntxt) # tag prepositions
    ntxt = mtgl.re_cond.sub(r"cn<\1>",ntxt) # & conditional/rqmt
    return mtgl.re_seq.sub(r"sq<\1>",ntxt)  # & sequence words

def tag_counters(txt):
    """ tags counters (markers) in txt returning tagged txt """
    ntxt = mtgl.re_pt_ctr.sub(r"xo<ctr type=\1\2/\3\4>",txt) # tag p/t counters
    return mtgl.re_named_ctr.sub(r"xo<ctr type=\1>",ntxt)    # & named counters

def tag_awkws(txt):
    """ tags ability words, keywords and action words returning tagged txt """
    ntxt = mtgl.re_aw.sub(r"aw<\1>",txt)          # tag ability words
    ntxt = mtgl.re_kw.sub(r"kw<\1>",ntxt)         # tag keywords
    ntxt = mtgl.re_kw_act.sub(r"ka<\1>",ntxt)     # tag keyword actions
    ntxt = mtgl.re_lituus_act.sub(r"xa<\1>",ntxt) # tag lituus actions
    return ntxt

def tag_effects(txt):
    """ tags effects in txt returning tagged txt """
    return mtgl.re_effect.sub(r"ef<\1>",txt)

def tag_characteristics(txt):
    """ tags characterisitcs in txt returning tagged txt """
    ntxt = mtgl.re_ch.sub(r"ch<\1>",txt)                    # tag characteristics
    ntxt = mtgl.re_ch_pt.sub(r"ch<p/t val=\1\2/\3\4>",ntxt) # tag p/t
    return mtgl.re_lituus_ch.sub(r"xc<\1>",ntxt)            # tag lituus char. & return

####
## MID-PROCESSING
####

def midprocess(txt):
    """
     prepares tagged txt for second pass
       1. replaces spaces/hyphens inside tags with underscore IOT make it a
        single tag value
       2. moves 'non-' in front of a tag to the negated symbol '¬' inside the tag
       3. align subsequent super-type, card type, ch<super-type> ch<type> are
        aligned i.e. ch<basic> ch<land> becomes ch<basic→land> this will assist
        in chaining
       4. align subsequent type sub-type, ch<sub-type> ch<type> are aligned i.e.
       ch<¬aura> ch<enchantment> becomes ch<enchantment→¬aura
       5. deconflict incorrectly tagged tokens
       6. move suffixes to inside the tag's prop-list
     NOTE:
      for 3 and 4 the highest hierarchical item will come first, that is in order
       of super-type, type, sub-type, so for #4 we have to switch the order
    :param txt: tagged oracle txt
    :return: processed oracle txt
    """
    ntxt = mtgl.re_tkn_delimit.sub(lambda m: mtgl.tkn_delimit[m.group(1)],txt) # 1
    ntxt = mtgl.re_negate_tag.sub(r"\1<¬\2>",ntxt)                             # 2
    ntxt = mtgl.re_align_type.sub(r"ch<\1\2→\3\4>",ntxt)                       # 3
    ntxt = mtgl.re_align_type2.sub(r"ch<\3\4→\1\2>",ntxt)                      # 4
    ntxt = deconflict_tags(ntxt)                                               # 5
    ntxt = mtgl.re_suffix.sub(r"\1<\2 suffix=\3>", ntxt)                       # 6
    return ntxt

re_emp_postfix = re.compile(r"\ssuffix=(?=)>")
def deconflict_tags(txt):
    """
     deconflicts incorrectly tagged tokens
    :param txt: oracle txt after initial first pass
    :return: tagged oracle text
    """
    # Status related

    # Tapped, Flipped
    ntxt = mtgl.re_status.sub(r"st<\2\3p\4>",txt)

    # phase - can be Status (Time and Tide), Turn Structure (Breath of Fury) or
    #  action (Ertai's Familiar)
    ntxt = mtgl.re_status_phase.sub(r"st<phased amplifier=\2>",ntxt)
    ntxt = mtgl.re_action_phase.sub(r"xa<phase amplifier=\2 suffix=\1>",ntxt)
    ntxt = mtgl.re_ts_phase.sub(r"ts<phase suffix=\1>",ntxt)

    # actions and turn structure may result in empty suffixes
    ntxt = re_emp_postfix.sub('>',ntxt)

    # Face Up/Down
    ntxt = mtgl.re_status_face.sub(r"st<face amplifier=\1>",ntxt)
    ntxt = mtgl.re_mod_face.sub(r"xm<face amplifier=\1>",ntxt)

    return ntxt

####
## 2ND PASS
####

def second_pass(txt):
    """
     performs a second pass of the oracle txt, working on Things and Attributes,
    :param txt: initial tagged oracle txt (lowered case)
    :return: tagged oracle text
    """
    ntxt = chain(txt)
    return ntxt

def chain(txt):
    """
     Sequential comma separated charcteristics can be combined into the
     characteristics parameter of a single object (that may be implied)
    :param txt: tagged oracle txt
    :return: modified tagged txt with sequential characterisitcs chained
    NOTE: these must be followed in order
    """
    # First, IOT faciliate chaining:
    #  a) chain dual conjoined color characteristics - this facilitates
    #   future chaining of characteristics like Stangg
    #  b) handle special case of 'base power and toughness' replace phrase
    #   base ch<power> and ch<toughness> ch<p/t val=X/Y> with ch<p/t val=X/Y>
    ntxt = mtgl.re_2chain_clr.sub(lambda m: _clr_combination_(m),txt)
    ntxt = powt(ntxt)

    # Now do multi chains:
    #  a) 3 or more comma separated characteristics w/ explicit conjunctions 'or'
    #    or 'and' which may or may not be followed by more characteristics and
    #    or an object
    #  b) 3 or more space separated characteristics w/o a conjuction and followed
    #   by a an object Spawning Pit
    ntxt = mtgl.re_nchain_comma.sub(lambda m: _nchain_(m),ntxt)
    ntxt = mtgl.re_nchain_space.sub(lambda m: _nchain_(m),ntxt)

    # Dual chains make up the prevalent characteristic chain but care must be
    # taken to not inadvertently chain characteristics inadverntly:
    #  a) 2 comma-delimited char followed by an object and preceded by a quantifier
    #   (quantifier char, char, obj) i.e. Chrome Mox (As of TBD, only 19 cards)
    #ntxt = mtgl.re_2chain_quant_obj.sub(lambda m: _2chain_qo_(m),ntxt)

    return ntxt

def powt(txt):
    """
    chains phrase power and toughness accordingly
    :param txt: tagged oracle txt
    :return: modified tagged txt with power and toughness tagged
    """
    ntxt = mtgl.re_base_pt.sub(r"\1",txt) # base power and toughness
    ntxt = mtgl.re_single_pt.sub(r"ch<p/t>",ntxt)
    return ntxt


####
## PRIVATE FUNCTIONS
####

def _nchain_(m):
    """
    chains comma or space separated characteristics possibly cantaining an 'and'/'or'
    into a single object (implied or explicit)
    :param m: a regex.Match object
    :return: the chained object
    """
    # set up our lists for values and attributes
    vals = []                                   # characteristics to chain
    tas = []                                    # & their attributes
    meta = []                                   # meta characteristics
    op = mtgl.AND                               # default 'and'ed characteristics
    tkn = None                                  # current token in chain
    tid = val = attrs = None                    # obj to create
    space = ' ' if m.group()[-1] == ' ' else '' # hanging space

    # untag the characteristics saving the tag value and attributes
    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
        try:
            # untag
            ti,tv,ta = mtgltag.untag(tkn)

            # if its an object, we're done. Save the tag
            if ti == 'ob':
                tid,val,attr = ti,tv,ta
                break

            # check for a meta characterisics
            if tv in mtgl.meta_characteristics:
                # if 'val is in the attributes, append as a meta otherwise return
                # We should always only have one meta characteristic in a chain
                # they should always be anded but just in case
                if 'val' in ta:
                    assert(len(ta) == 1)
                    meta.append((tv,ta['val']))
                else: return m.group()
            else:
                # append the value and the proplist to running lists
                vals.append(tv)
                tas.append(ta)
        except lts.LituusException:
            # cannot untag - this is the operator
            assert(tkn == 'and' or tkn == 'or')
            op = mtgl.AND if tkn == 'and' else mtgl.OR

    # chain the characteristics, merge the proplists & move suffix if present
    attrs = {}
    chs = op.join(vals)
    merged = mtgltag.merge_props(tas)
    if 'suffix' in merged: attrs['suffix'] = merged['suffix']
    if meta: attrs['meta'] = op.join(mt[0]+mtgl.EQ+mt[1] for mt in meta)

    # Create implied object if necessary. Then add chained characteristics
    if not tid:
        tid = 'ob'
        val = _implied_obj_(vals)
    attrs['characteristics'] = chs

    # retag the chained characteristics and return
    return mtgltag.retag(tid,val,attrs) + space

def _2chain_qo_(m):
    """
    chains 2 comma-delimited characteristics followed by an object i.e. Chrome Mox
    :param m: are regex.Match object
    :return: the chained object
    """
    # untag the object & the characteristics
    i,v,p = mtgltag.untag(m.group(3))
    _,cv1,cp1 = mtgltag.untag(m.group(1))
    _,cv2,cp2 = mtgltag.untag(m.group(2))
    assert(cp1 == {} and cp2 == {})
    assert('characteristics' not in p)
    p['characteristics'] = cv1 + mtgl.AND + cv2

    return mtgltag.retag(i,v,p)

def _clr_combination_(m):
    """
    chains two color characteristics together they can be seperated by an 'and',
    'or' or comma
    :param m: a regex.Match object
    :return: the chained colors
    """
    # 3  groups color1, operator, color2 (assumes no attributes for colors)
    clr1 = mtgltag.untag(m.group(1))[1]
    op = mtgl.OR if m.group(2) == 'or' else mtgl.AND
    clr2 = mtgltag.untag(m.group(3))[1]
    return mtgltag.retag('ch',clr1+op+clr2,{})

def _implied_obj_(cs):
    """
    determines from list of characteristics what value an object should have
    109.2 if there is a reference to a type or subtype but not card,spell or source,
    it means a permanent of that type or subtype
    :param cs: list of characteristics
    :return: 'card' or 'permanent' based on rule 109.2
    """
    for c in cs:
        x = c.replace(mtgl.NOT,'') # remove any negations
        if x in mtgl.type_characteristics+mtgl.sub_characteristics: return 'permanent'
    return 'card'