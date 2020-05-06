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
    ntxt = mtgl.re_prep.sub(r"pr<\1>",txt)  # tag prepositions
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
    ntxt = chain(ntxt)
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
    ntxt = powt(txt)                                                    # 1
    ntxt = mtgl.re_meta_attr.sub(lambda m: _metachar_(m),ntxt)          # 2.a
    ntxt = mtgl.re_attr_val.sub(r"xr<\1 val=\2\3>",ntxt)                # 2.b
    ntxt = mtgl.re_attr_val_nop.sub(r"xr<\1 val=≡\2>",ntxt)             # 2.c
    ntxt = mtgl.re_hanging_subtype.sub(lambda m: _insert_type_(m),ntxt) # 3
    ntxt = align_types(ntxt)                                            # 4
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
    # TODO: don't like this but we have to run align_type two times once in
    #  front and once on the back end
    #  1. Need to check cards like Silumgar Monument for dual types prior to
    #   aligning super and sub
    #  2. Need to check cards like Gargantuan Gorilla for dual types after aligning
    #   super and sub
    ntxt = mtgl.re_align_dual.sub(lambda m: _align_dual_(m),txt)  # consecutive types
    ntxt = mtgl.re_align_sub.sub(lambda m: _align_type_(m),ntxt)    # sub, type
    ntxt = mtgl.re_align_super.sub(lambda m: _align_type_(m),ntxt) # super, type
    ntxt = mtgl.re_align_dual.sub(lambda m: _align_dual_(m),ntxt)  # consecutive types
    return ntxt

def chain(txt):
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
    ntxt = mtgl.re_clr_conj_type.sub(lambda m: _clr_conj_type_(m),ntxt)

    # chain conjunctions
    ntxt = mtgl.re_conjunction_chain.sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_conjunction_chain_special.sub(lambda m: _chain_special_(m),ntxt)
    ntxt = mtgl.re_pob_chain.sub( # Price of Betrayal
        lambda m: r"ch<{0}{4}{1}{4}{2}>, {3}".format(
            m.group(1),m.group(2),m.group(3),m.group(4),mtgl.conj_op[m.group(4)]),
        ntxt
    )

    return ntxt

def reify(txt):
    """
    reifies characteristics
    reifies characteristics
    :param txt: tagged and chained txt
    :return: txt with reified characteristics
    """
    # reify complex phrases first, then non-type singleton characteristics then
    # left-over singleton characteristics
    ntxt = mtgl.re_reify_phrase.sub(lambda m: _reify_phrase_(m),txt)
    ntxt = mtgl.re_reify_single.sub(lambda m: _reify_single_(m),ntxt)
    ntxt = mtgl.re_reify_singleton_char.sub(lambda m: _reify_singleton_(m),ntxt)
    return ntxt

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
    # replace english with operator symbol, then transpose with preceding number
    op = m.group(2)
    if op in ['greater','more']: op = "op<{}>".format(mtgl.GE)
    elif op == 'less': op = "op<{}>".format(mtgl.LE)
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

            # check for same type alignment on all tokens See Quest for Ula's Temple
            if not mtgltag.is_aligned(val): aligned = False
            else:
                # get the type and set atype if necessary then ensure the new
                # type is the same as atype
                ptype = val.split(mtgl.ARW)[0]
                if not atype: atype = ptype
                if atype != ptype: aligned = False

            # check for complex values and wrap in () present then append the
            # tag-value and merge the tag's attribute dict
            #if mtgltag.complex_ops(val): val = mtgltag.wrap(val)
            if mtgltag.conjunction_ops(val): val = mtgltag.wrap(val)
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

def _reify_phrase_(m):
    """
    chains and reifies phrases of the form [P/T] [COLOR] TYPE [OBJECT] into a
    single object
    :param m: a regex.Match object
    :return: the reify characteristic chain
    """
    # set up variables
    operands = [] # terms to be anded
    atype = None  # primary alignment

    # extract p/t, color, type and object, set up the new tag
    st,pt,clr,ent,obj = m.groups()

    # create the operand list
    if st: operands.append(st)
    if pt: operands.append(pt)
    if clr:
        # not sure if necessary but if there's a complex color with or wrap it first
        if not mtgltag.is_wrapped(clr) and (mtgl.OR in clr or mtgl.AOR in clr):
            clr = mtgltag.wrap(clr)
        operands.append(clr)

    # check the type characteristics for alignments/complexity. If there is
    # an alignment extract the aligned type and the aligned characteristics
    # However, have to make sure we don't have something like
    #    'creature→spirit∨((instant∨sorcery)→arcane)'
    nch = mtgltag.tag_val(ent)
    if mtgltag.is_aligned(nch): atype,nch = mtgltag.split_align(nch)

    # set up object tag  - 109.2 if there is a reference to a type or subtype but
    # not card, spell or source, it means a permanent of that type or subtype
    tid = 'ob'
    val = 'permanent' if not obj else mtgltag.tag_val(obj) # TODO check for type/subtype
    attr = mtgltag.merge_attrs(
        [mtgltag.tag_attr(ent),mtgltag.tag_attr(obj) if obj else {}]
    )

    # add the characteristics attribute to the new object
    assert('characteristics' not in attr)
    operands.append(nch)
    char = mtgl.AND.join(operands)
    if atype:
        if len(operands) > 1: char = mtgltag.wrap(char)
        char = atype + mtgl.ARW + char
    attr['characteristics'] = char

    return mtgltag.retag(tid,val,attr)

def _reify_single_(m):
    """
    reifies a singleton characteristic followed by an object
    :param m: the  regex.Match object
    :return: reified characteristic
    """
    # get the characteristic value and untag the object
    # NOTE: the object should only have a suffix attribute or no attributes
    char = m.group(1)
    tid,val,attr = mtgltag.untag(m.group(2))
    assert('characteristics' not in attr)
    attr['characteristics'] = char
    return mtgltag.retag(tid,val,attr)

def _reify_singleton_(m):
    """
    reifies left-over singleton characteristics as an attribute
    :param m: the regex.Match
    :return: reified attribute
    """
    # unpack the characteristic - should not be complex
    _,val,attr = mtgltag.untag(m.group(1))

    # what kind is it - if it's a meta characteristic, just retag it
    # otherwise, it should be a color
    # TODO: some colors are associated with lituus objects i.e. Soul Burn
    if val in mtgl.meta_characteristics: return mtgltag.retag('xr',val,attr)
    else:
        # could be color or super-type
        cat = None
        for v in mtgltag.operand(val):
            tcat = None
            if mtgltag.strip(v) in mtgl.color_characteristics: tcat = 'color'
            elif mtgltag.strip(v) in mtgl.super_characteristics: tcat = 'super-type'
            elif mtgltag.strip(v) == 'historic': tcat = 'type'
            else:
                raise lts.LituusException(
                    lts.EPARAM,
                    "Invalid category {} for singleton characteristics".format(v)
                )
            if not cat: cat = tcat
            elif cat != tcat: assert(False) # should never get here
        return mtgltag.retag('xr',cat,mtgltag.merge_attrs([attr,{'val':val}]))

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

    # also need to check for alignment
    if not mtgltag.is_aligned(val): val += mtgl.AND + clr
    else:
        atype,aval = mtgltag.split_align(val)
        val = atype + mtgl.ARW + mtgltag.wrap(aval+mtgl.AND+clr)

    # retag and return
    return mtgltag.retag(tid,val,attr)

def _clr_conj_type_(m):
    """
    special case of color conjunction type i.e. Soldevi Adnate or Tezzeret's
    Gatebreaker
    :param m: the regex.Match object
    :return: the chained type
    """
    # for now there are only two but want to generalize as much as possible
    clr = m.group(1)
    op = mtgl.conj_op[m.group(2)]
    _,val,attr = mtgltag.untag(m.group(3))
    if not mtgltag.is_aligned(val): val += op + clr
    else:
        atype,aval = mtgltag.split_align(val)
        val = "{}→({}{}{})".format(atype,aval,op,clr)
    return mtgltag.retag('ch',val,attr)

def _align_dual_(m):
    """
    aligns or chains two consecutive types depending on presence of conjunction
    operator
    :param m: a regex.Match object
    :return: the aligned or chained types
    """
    # verify first that the types are not the same i.e. Elven Rider
    if mtgltag.tag_val(m.group(1)) == mtgltag.tag_val(m.group(3)): return m.group()
    #return _chain_(m)
    # if we have a connjunction operator or complex operand(s), chain
    # otherwise align
    if m.group(2) in mtgl.conj_op: return _chain_(m)
    else:
        for tkn in [m.group(1),m.group(3)]:
            if mtgltag.complex_ops(mtgltag.tag_val(tkn)): return _chain_(m)
    return _align_type_(m)

def _align_type_(m):
    """
    aligns super-type(s) sub-type(s) to type
    :param m: a regex.Match object
    :return: the aligned types
    """
    # split the group into tokens. The last tkn is the type, untag it. The first
    # n-1 are the super-type(s), subtypes or types, 'and' them
    tkns = [x for x in lexer.tokenize(m.group())[0]]
    _,val,attr = mtgltag.untag(tkns[-1])
    vs = mtgl.AND.join([mtgltag.tag_val(tkn) for tkn in tkns[:-1]])

    #op = mtgl.AND
    #if not mtgltag.is_aligned(val): op = mtgl.ARW

    # if the type is already aligned, need to wrap the aligned characteristics
    if mtgltag.is_aligned(mtgltag.unwrap(val)):
        atype,aval = mtgltag.split_align(mtgltag.unwrap(val))
        if mtgltag.conjunction_ops(atype): atype = mtgltag.wrap(atype)
        val = atype + mtgl.ARW + mtgltag.wrap(aval + mtgl.AND + vs)
    else:
        # if the aligned type is a conjunction, encapsulate it
        if mtgltag.conjunction_ops(val): val = mtgltag.wrap(val)
        val += mtgl.ARW + vs

    # TODO: make sure we won't see attributes on the preceding characteristics
    return mtgltag.retag('ch',val,attr)
