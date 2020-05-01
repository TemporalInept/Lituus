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
__version__ = '0.1.5'
__date__ = 'May 2020'
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
    ntxt = tag_operators(ntxt)                   # operators
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
    ntxt = mtgl.re_prep.sub(r"pr<\1>",txt) # tag prepositions
    ntxt = mtgl.re_cond.sub(r"cn<\1>",ntxt) # & conditional/rqmt
    ntxt = mtgl.re_seq.sub(r"sq<\1>",ntxt)  # & sequence words
    return ntxt

def tag_operators(txt):
    """ tags math/comparison operators """
    # have to execute two substitutions for operators
    #  1. simple replacment of english with operator symbol
    #  2. transpose english words first then replace
    ntxt = mtgl.re_op.sub(lambda m: "op<{}>".format(mtgl.op[m.group(1)]),txt)
    ntxt = mtgl.re_num_op.sub(lambda m: _transpose_num_op_(m),ntxt)
    return ntxt

def tag_counters(txt):
    """ tags counters (markers) in txt returning tagged txt """
    ntxt = mtgl.re_pt_ctr.sub(r"xo<ctr type=\1\2/\3\4>",txt) # tag p/t counters
    #ntxt = mtgl.re_named_ctr.sub(r"xo<ctr type=\1>",ntxt)    # & named counters
    ntxt = mtgl.re_named_ctr.sub(lambda m: _named_ctr_(m),ntxt)
    return ntxt

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
       3. deconflict incorrectly tagged tokens
       4. move suffixes to inside the tag's prop-list
       5. set up hanging (a) basic and (b) snow supertypes
       6. arrange phrases with 'number'
        a. arrange phrases of the form op<OP> xq<the> number of ... to read
         op<OP> nu<y>, where nu<y> is the number of ... so that they read the
         same as cards like "As Foretold"
        b. replace "any number of" with nu<z>
        c. remove "are each" if followed by an operator
    :param txt: tagged oracle txt
    :return: processed oracle txt
    """
    ntxt = mtgl.re_val_join.sub(lambda m: mtgl.val_join[m.group(1)],txt) # 1
    ntxt = mtgl.re_negate_tag.sub(r"\1<¬\2>",ntxt)                       # 2
    ntxt = deconflict_tags(ntxt)                                         # 3
    ntxt = mtgl.re_suffix.sub(r"\1<\2 suffix=\3>",ntxt)                  # 4
    ntxt = mtgl.re_hanging_basic.sub(r"\1 ch<land>",ntxt)                # 5.a
    ntxt = mtgl.re_hanging_snow.sub(r"\1 ch<land>",ntxt)                 # 5.b
    ntxt = mtgl.re_equal_y.sub(r"nu<y>, where nu<y> is \1",ntxt)         # 6.a
    ntxt = mtgl.re_equal_z.sub(r"nu<z>",ntxt)                            # 6.b
    ntxt = mtgl.re_are_each.sub(r"",ntxt)                                # 6.c
    return ntxt

re_empty_postfix = re.compile(r"\ssuffix=(?=)>")
def deconflict_tags(txt):
    """
     deconflicts incorrectly tagged tokens
    :param txt: oracle txt after initial first pass
    :return: tagged oracle text
    """
    # Tapped, Flipped
    ntxt = mtgl.re_status.sub(r"st<\2\3p\4>",txt)

    # phase - can be Status (Time and Tide), Turn Structure (Breath of Fury) or
    #  action (Ertai's Familiar)
    ntxt = mtgl.re_status_phase.sub(r"st<phased amplifier=\2>",ntxt)
    ntxt = mtgl.re_action_phase.sub(r"xa<phase amplifier=\2 suffix=\1>",ntxt)
    ntxt = mtgl.re_ts_phase.sub(r"ts<phase suffix=\1>",ntxt)

    # actions and turn structure may result in empty suffixes
    ntxt = re_empty_postfix.sub('>',ntxt)

    # Face Up/Down
    ntxt = mtgl.re_status_face.sub(r"st<face amplifier=\1>",ntxt)
    ntxt = mtgl.re_mod_face.sub(r"xm<face amplifier=\1>",ntxt)

    # turn could be a lituus action
    ntxt = mtgl.re_turn_action.sub("xa",ntxt)

    # take care of misstagged
    ntxt = mtgl.re_misstag.sub(lambda m: mtgl.misstag[m.group(1)],ntxt)

    # Cost is defined as an object but may be an action
    ntxt = mtgl.re_cost_mana.sub(r"xa<cost>\1",ntxt)
    ntxt = mtgl.re_cost_num.sub(r"xa<cost>\1",ntxt)
    ntxt = mtgl.re_cost_aa.sub(r"xa<cost>\1",ntxt)
    ntxt = mtgl.re_cost_except.sub(r"xa<cost>\1",ntxt)

    # Not a deconfliction perse but to avoid conflicts 'named' is listed as
    # an action, rewrite it here so it shows up xa<name suffix=ed> rather than
    # xa<named>
    ntxt = ntxt.replace("xa<named>","xa<name suffix=ed>")

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
    ntxt = pre_chain(txt)
    ntxt = chain_characteristics(ntxt)
    ntxt = reify(ntxt)
    return ntxt

def pre_chain(txt):
    """
    Facilitates chaining
    :param txt: txt to prechain
    :return: prechainned text
    """
    #  1) handle special case of 'base power and toughness' replace phrase
    #   base ch<power> and ch<toughness> ch<p/t val=X/Y> with ch<p/t val=X/Y>
    #  2) attributes - (stand alone meta-characteristics)
    #   a. temporarily tag attributes as xr
    #   b. assign values where possible to temporary attributes including c.
    #    those without an operator
    #  3) add types to hanging subtypes
    #  4) align supertypes and subtypes
    ntxt = powt(txt)                                                     # 1
    ntxt = mtgl.re_meta_attr.sub(lambda m: _metachar_(m),ntxt)           # 2.a
    ntxt = mtgl.re_attr_val.sub(r"xr<\1 val=\2\3>",ntxt)                 # 2.b
    ntxt = mtgl.re_attr_val_nop.sub(r"xr<\1 val=≡\2>",ntxt)              # 2.c
    ntxt = mtgl.re_hanging_subtype.sub(lambda m: _insert_type_(m), ntxt) # 3
    ntxt = align_types(ntxt)                                             # 4
    return ntxt

def powt(txt):
    """
    chains phrase power and toughness accordingly as well as p/t chains
    :param txt: tagged oracle txt
    :return: modified tagged txt with power and toughness and p/t chains tagged
    """
    ntxt = mtgl.re_base_pt.sub(r"\1",txt)                    # base power & toughness
    ntxt = mtgl.re_single_pt.sub(r"ch<p/t>",ntxt)            # solitary power & toughness
    ntxt = mtgl.re_pt_chain.sub(lambda m: _ptchain_(m),ntxt) # p/t or p/t chain
    return ntxt

def align_types(txt):
    """
    conducts alignment of types
    :param txt: tagged oracle txt
    :return: aligned txt
    """
    ntxt = mtgl.re_align_dual.sub(lambda m: _align_dual_(m),txt)   # consecutive types
    ntxt = mtgl.re_align_sub.sub(lambda m: _align_type_(m),ntxt)   # sub, type
    ntxt = mtgl.re_align_super.sub(lambda m: _align_type_(m),ntxt) # super, type
    return ntxt

def chain_characteristics(txt):
    """
    Sequential charcteristics can be combined into a single characteristic
    :param txt: tagged oracle txt
    :return: modified tagged txt with sequential characterisitcs chained
    NOTE: these must be followed in order
    """
    # start with colors as they may be 'sub-chains' within a large chain or may
    # be part of a color type pair
    ntxt = mtgl.re_clr_conjunction_chain.sub(lambda m: _chain_(m),txt)
    ntxt = mtgl.re_clr_conjunction_chain_special.sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_clr_type_chain.sub(lambda m: _clr_type_(m),ntxt)

    # chain conjunctions
    ntxt = mtgl.re_conjunction_chain.sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_conjunction_chain_special.sub(lambda m: _chain_special_(m),ntxt)

    return ntxt

def reify(txt):
    """
    reifies characteristics
    :param txt: tagged and chained txt
    :return: txt with reified characteristics
    """
    return txt

####
## PRIVATE FUNCTIONS
####

def _named_ctr_(m):
    """
     creates a named counter tag from m
    :param m: regex Match object
    :return: named counter tag
    """
    if m.group(2): return "xo<ctr type={} suffix=s>".format(m.group(1))
    else: return r"xo<ctr type={}>".format(m.group(1))

def _transpose_num_op_(m):
    """
    transpose number or greater|less and replace english w/ symbol. For example,
    nu<1> or greater becomes >= nu<1>
    :param m: regex Match object
    :return: transposed text
    """
    # replace enlgish with operator symbol, then transpose with preceding number
    op = m.group(2)
    if op == 'greater': op = "op<" + mtgl.GE + ">"
    elif op == 'less': op = "op<" + mtgl.LE + ">"
    else:
        raise lts.LituusException(lts.EDATA,"invalid operator ({})".format(op))
    return "{} {}".format(op,m.group(1))

def _metachar_(m):
    """
    rewrites a standalone meta characteristics as an attribute. Attributes will
    have not have a value
    :param m: a regex.Match object
    :return: rewritten attribute if required otherwise the orginal tag
    """
    tid,val,attr = mtgltag.untag(m.group(1))
    if not 'val' in attr: tid = 'xr'
    return mtgltag.retag(tid,val,attr)

def _insert_type_(m):
    """
    inserts a type following a hanging subtype where type is the type the subtype
    belongs to
    :param m: a regex.Match object
    :return: subtype type
    """
    # unpack the subtype
    tid,val,attr = mtgltag.untag(m.group(1))

    # create the parameters for the new type tag. Have to get the type of this
    # subtype (NOTE: assuming its a singleton type as no chain/align have been
    # conducted) then move any suffix from the subtype to the type
    mtid = 'ch'
    mtype = mtgl.subtypes_of[mtgl.subtype(mtgltag.strip(val))]
    mattr = {}
    if 'suffix' in attr:
        mattr['suffix'] = attr['suffix']
        del attr['suffix']

    # return the two tags
    return "{} {}".format(
        mtgltag.retag(tid,val,attr),mtgltag.retag(mtid,mtype,mattr)
    )

def _ptchain_(m):
    """
    chains p/t or p/t chains
    :param m: a regex.Match object
    :return: the chained object
    """
    # get the two p/ts and unpack the value
    ch1,ch2 = m.groups()
    pt1 = mtgltag.tag_attr(ch1)['val']
    pt2 = mtgltag.tag_attr(ch2)['val']
    return mtgltag.retag('ch','p/t',{'val':pt1 + mtgl.OR + pt2})

def _chain_(m):
    """
    chains a group of sequential tokens into one
    :param m: a regex.Match object
    :return: the chained object
    """
    # initialize new tag parameters
    ntid = None
    nval = []
    nattr = {}
    op = mtgl.AND # default is and

    # initialize loop variables
    aligned = True
    atype = None

    # extract the tags and operator
    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
        try:
            # untag the tag and check for meta characterisitcs
            tid,val,attr = mtgltag.untag(tkn)
            if val in mtgl.meta_characteristics: return m.group()

            # instantiate the new tag-id once (for now, make sure eah tag has
            # the same tag-id
            if not ntid: ntid = tid
            assert(ntid == tid)

            # check for alignment on the same type across all tokens
            # See Quest for Ula's Temple
            if not mtgltag.is_aligned(val): aligned = False
            else:
                # get the type and set atype if necessary then ensure the new
                # type is the same as atype
                ptype = val.split(mtgl.ARW)[0]
                if not atype: atype = ptype
                if atype != ptype: aligned = False

            # check for complex values and wrap in () present then append the
            # tag-value and merge the tag's attribute dict
            if mtgltag.complex_ops(val): val = mtgltag.wrap(val)
            nval.append(val)
            nattr = mtgltag.merge_attrs([attr,nattr])
        except lts.LituusException:
            # should be the operator
            try:
                op = mtgl.conj_op[tkn]
            except Keyerror:
                raise lts.LituusException(lts.MTGL,"Illegal op {}".format(tkn))

    # if there is no alignment, join the values by the operator. otherwise
    # condense alignment joining only the aligned characteristics
    # For example creature→skeleton, creature→vampire, or creature→zombie>
    # becomes creature→(skeleton∨vampire∨zomebie)
    if not aligned: nval = op.join(nval)
    else:
        nval = "{}→({})".format(
            atype,op.join([_repackage_aligned_val_(x) for x in nval])
        )

    # create the new tag
    return mtgltag.retag(ntid,nval,nattr)

def _repackage_aligned_val_(val):
    """
    for aligned values will unwrap parenthesis as necessary, extract the aligned
    characteristics from the aligned val and rewrap those characteristics as
    necessary
    :param val: val to repackage
    :return: repackaged val
    """
    if not mtgltag.is_wrapped(val): return mtgltag.split_align(val)[1]
    else:
        val = mtgltag.unwrap(val)
        return mtgltag.wrap(mtgltag.split_align(val)[1])

def _chain_special_(m):
    """
    chains or aligns two sequential characteristics separated by a comma
    :param m: a regex.Match object
    :return: the chained object
    """
    # the first will be a value only but have to unpack the second
    ch1,ch2,op = m.groups()
    tid,val,attr = mtgltag.untag(ch2)
    ntag = None

    # don't do anything if ch1 and val are the same type
    if mtgltag.strip(ch1) == mtgltag.strip(val): return m.group()

    # two possibilities. If val is complex, we need to align otherwise conjoin
    if not mtgltag.complex_ops(val):
        # if there is a hanging conjunction use it otherwise use and
        nop = mtgl.conj_op[op] if op else mtgl.AND
        ntag = mtgltag.retag(tid,ch1+nop+val,attr)
        if nop != mtgl.AND: ntag += ', {}'.format(op)
    else:
        # the first operand is the main type, subsequent will be 'and'ed with ch1
        # and aligned to the first
        vals = mtgltag.operand(val)
        ntag = mtgltag.retag(
            tid,"{}→({})".format(vals[0],mtgl.AND.join(vals[1:]+[ch1])),attr
        )

    # return the tag plus any hanging conjunctions
    return ntag

def _clr_type_(m):
    """
    chains a color type pair appending the color to the type
    :param m: a regex.Match object
    :return: the chained object
    """
    # before appending the color, have to make sure that color is encapsulated
    # if a) it has a 'or/'and/or' or b) the type value has a 'or'/'and/or' and
    # it has an 'and'
    clr = m.group(1)
    tid,val,attr = mtgltag.untag(m.group(2))
    if mtgl.OR in clr or mtgl.AOR in clr: clr = mtgltag.wrap(clr)
    if mtgl.OR in val or mtgl.AOR in val and mtgl.AND in clr: val = mtgltag.wrap(val)
    return mtgltag.retag(tid,val+mtgl.AND+clr,attr)

def _align_dual_(m):
    """
    aligns or chains two consecutive types depending on presence of conjunction
    operator
    :param m: a regex.Match object
    :return: the aligned or chained types
    """
    # if we have a conjunction operator chain otherwise align
    if m.group(2) in mtgl.conj_op: return _chain_(m)
    else: return _align_type_(m)

def _align_type_(m):
    """
    aligns super-type(s) and sub-type(s) to type
    :param m: a regex.Match object
    :return: the aligned types
    """
    # split the group into tokens - the last tkn is the type, the first n-1 are
    # the super-type(s) or subtypes
    tkns = [x for x in lexer.tokenize(m.group())[0]]

    # untag the type. Determine the operator - if it already has an alignment
    # operator use an AND otherwise need to use the alignment first. Also have
    # to make sure the type is not complex, if it is encapsulate it
    _,val,attr = mtgltag.untag(tkns[-1])
    op = None
    if mtgl.ARW in val: op = mtgl.AND
    else: op = mtgl.ARW
    if mtgltag.complex_ops(val): val = mtgltag.wrap(val)

    # join the characteristics and retag
    # TODO: make sure we won't see attributes on the preceding characteristics
    val += op + mtgl.AND.join([mtgltag.tag_val(tkn) for tkn in tkns[:-1]])
    return mtgltag.retag('ch',val,attr)

#def _reify_st_(m):
#    """
#    creates an object from singleton types
#    :param m: a regex.Match object
#    :return: txt with singleton types reified
#    """
#    # 109.2 if there is a reference to a type or subtype but not card, spell or
#    # source, it means a permanent of that type or subtype
#    oval = 'permanent'                           # implied obj is a permanent
#    _,val,attr = mtgltag.untag(m.group(1))       # untag the type characteristic
#    if m.group(2):                               # if we have an object
#        _,oval,oattr = mtgltag.untag(m.group(2)) # untag it
#        attr = mtgltag.merge_attrs([oattr,attr]) # and merge the attribure dicts
#    attr['characteristics'] = val                # add type(s) to attribute dict
#    return mtgltag.retag('ob',oval,attr)         # & return the new object

#def _ncolor_(m):
#    """
#    chains n color characteristics together. They will be comma-delimited and have
#    a conjuction
#    :param m: a regex.Match object
#    :return: the chained colors
#    """
#    clrs = []
#    op = None
#    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
#        try:
#            # unpack the color
#            clrs.append(mtgltag.tag_val(tkn)[1])
#        except lts.LituusException:
#            try:
#                op = mtgl.conj_op[tkn]
#            except KeyError:
#                raise lts.LituusException(lts.ETAGGING, "Illegal op {}".format(tkn))
#    return mtgltag.retag('ch',op.join(clrs),{})

#def _ntype_(m):
#    """
#    chains n type characteristics (comma-delimited with conjuction)
#    :param m: a regex.Match object
#    :return: the chained types
#    """
#    vals = []
#    attrs = []
#    op = None
#    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
#        try:
#            # unpack the type and keep the attributes (may have suffixes)
#            _,val,attr = mtgltag.untag(tkn)
#            vals.append(val)
#            attrs.append(attr)
#        except lts.LituusException:
#            try:
#                op = mtgl.conj_op[tkn]
#            except KeyError:
#                raise lts.LituusException(lts.ETAGGING, "Illegal op {}".format(tkn))
#    return mtgltag.retag('ch',op.join(vals),mtgltag.merge_attrs(attrs))

#def _2type_(m):
#    """
#    chains 2 type characteristics separated by a conjunction
#    :param m: a regex.Match object
#    :return: the chained types
#    """
#    _,val1,attr1 = mtgltag.untag(m.group(1))
#    _,val2,attr2 = mtgltag.untag(m.group(3))
#    try:
#        op = mtgl.conj_op[m.group(2)]
#    except KeyError:
#        raise lts.LituusException(lts.ETAGGING,"Illegal op {}".format(m.group(2)))
#    return mtgltag.retag('ch',val1+op+val2,mtgltag.merge_attrs([attr1,attr2]))

def _reify_chain_(m):
    """
    chains and reifies phrases of the form [P/T] [COLOR] TYPE [OBJECT] into a
    single object
    :param m: a regex.Match object
    :return: the reify characteristic chain
    """
    # extract p/t, color, type and object, set up the new tag
    pt,clr,ent,obj = m.groups()

    # set up the new object tag - 109.2 if there is a reference to a type or
    # subtype but not card, spell or source, it means a permanent of that type
    # or subtype
    tid = 'ob'
    val = 'permanent' if not obj else mtgltag.tag_val(obj)
    attr = mtgltag.merge_attrs(
        [mtgltag.tag_attr(ent),{} if not obj else mtgltag.tag_attr(obj)]
    )

    # add 'characteristics' to attribute dict and return the new tag
    assert('characteristics' not in attr)
    attr['characteristics'] = _chain_char_(mtgltag.tag_val(ent),pt,clr)
    return mtgltag.retag(tid,val,attr)

def _chain_char_(ch,pt=None,clr=None):
    """
    ANDs type, pt and clr encapsulating in parentheses as necessary
    :param ch: a tagged type, value may be complex
    :param pt: a pt value i.e x/y may be None
    :param clr: a color value may be complex or None
    :return: a tagged object
    """
    # set ret to ch, if ch has 'opposite' conjunctions encapsulate in parentheses
    ret = mtgltag.wrap(ch) if (pt or clr) and (mtgl.OR in ch or mtgl.AOR in ch) else ch

    # AND the p/t if present. With color is different, encapsulate in parentheses
    # if it has 'opposite' conjuctions
    if pt: ret += mtgl.AND + pt
    if clr:
        if mtgl.OR in clr: clr = mtgltag.wrap(clr)
        ret += mtgl.AND + clr

    # and return the chained string
    return ret

#def _nchain_(m):
#    """
#    chains comma or space separated characteristics possibly cantaining an 'and'/'or'
#    into a single object (implied or explicit)
#    :param m: a regex.Match object
#    :return: the chained object
#    """
#    # TODO: should be able to drop the meta related bookkeeping etc
#    # set up our lists for values and attributes
#    vals = []                                   # characteristics to chain
#    attrs = []                                  # & their attributes
#    meta = []                                   # meta characteristics
#    op = mtgl.AND                               # default 'and'ed characteristics
#    tkn = None                                  # current token in chain
#
#    # untag each characteristic, save the op when we hit it
#    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
#        try:
#            # untag the token
#            ti,tv,ta = mtgltag.untag(tkn)
#
#            # check if it is a meta-characteristic and if it is p/t
#            if tv in mtgl.meta_characteristics:
#                assert('val' in ta)  # any metas should have a 'val'
#                assert(len(ta) == 1) # and only a 'val'
#
#                # should only get p/t = 'x/y' here
#                if tv == 'p/t':
#                    vals.append(ta['val']) # append the x/y
#                    del ta['val']          # this should be empty after this
#                    attrs.append(ta)
#                else:
#                    # cannot see anything being here but just in case
#                    meta.append((tv,ta['val']))
#            else:
#                vals.append(tv)
#                attrs.append(ta)
#        except lts.LituusException:
#            # we've hit the operator, save it
#            try:
#                op = mtgl.conj_op[tkn]
#            except KeyError:
#                raise lts.LituusException(lts.ETAGGING, "Illegal op {}".format(tkn))
#        except Exception as e:
#            raise lts.LituusException(
#                lts.EUNDEF,"Unknown error {} in _nchain_".format(e)
#            )

#    # check alignments, merge the attributes & returned chained characteristics
#    return mtgltag.retag('ch',op.join(_aligned_(vals)),mtgltag.merge_attrs(attrs))

#def _aligned_(vals):
#    """
#    determines in a list of characteristic tag-values, if an align is present
#    whether the alignment remains as is or should be a subclass of operator.
#    Arranges the list of values such that an alignment will be in the first value
#    :param tkns: list of characteristics which may or may not contain an alignment
#    :return: the new list of tkns
#    """
#    # first determine if there is an alignment operator
#    i = main = sub = None
#    for i,val in enumerate(vals):
#        if mtgl.ARW in val:
#            main,sub = val.split(mtgl.ARW)
#            break
#    if not main: return vals
#    else: vals = vals.copy()
#
#    # determine if each other value is a subtype of the aligned type
#    align = True
#    for j,val in enumerate(vals):
#        # ignore the aligned token
#        if j == i: continue
#        if mtgl.ARW in val: val = val.split(mtgl.ARW)[1]
#
#        # check each operand if there conjunctions
#        for par in mtgltag.operand(val):
#            try:
#                if not mtgl.subtype_of(mtgltag.strip(par),main):
#                    align = False
#                    break
#            except lts.LituusException:
#                align = False
#                break

#    # if align is True, put the main type and alignment op at the first value
#    # otherwise replace the align operator with a subclass operator
#    if align:
#        vals[0] = main + mtgl.ARW + vals[0]
#        vals[i] = sub
#    else:
#        vals[i] = vals[i].replace(mtgl.ARW,mtgl.SUB)
#
#    # have to check whether
#    return vals

def _2chain_ex_(m):
    """
    chains the 2chain exception CHAR, CHAR OBJ|CHAR
    :param m: are regex.Match object
    :return: the chained or aligned characteristic
    """
    # first two are charactersitics (only), they will always be 'and'ed
    tkns = m.groups()
    ch = mtgl.AND.join(tkns[:2])

    # get the last token
    tid,val,attr = mtgltag.untag(tkns[-1])

    # the last token will determine whether we align or chain
    # if its an object return the chained characteristics & the original obj
    # if its a type characteristic, we align
    if tid == 'ob': return "{} {}".format(mtgltag.retag('ch',ch,{}),tkns[-1])
    else: return mtgltag.retag(tid,val + mtgl.ARW + ch,attr)

#def _2chain_conj_(m):
#    """
#    chains two characteristics delimited by a conjunction
#    :param m: the regex.Match object
#    :return: the chained characteristics
#    """
#    # pull out the characteristics and operator
#    ch1,op,ch2 = m.groups()
#
#    # unpack the characteristics
#    _,val1,attr1 = mtgltag.untag(ch1)
#    _,val2,attr2 = mtgltag.untag(ch2)
#
#    # convert operator to symbol
#    try:
#        op = mtgl.conj_op[op]
#    except KeyError:
#        raise lts.LituusException(lts.ETAGGING, "Illegal op {}".format(op))
#
#    # return the conjoined characteristic
#    return mtgltag.retag('ch',val1+op+val2,mtgltag.merge_attrs([attr1,attr2]))