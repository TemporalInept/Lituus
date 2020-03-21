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
__version__ = '0.1.0'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import lituus.mtgl.mtgl as mtgl

def tag(name,txt):
    """
     tags the mtgl oracle
    :param name: name of card
    :param txt: the mtgl text
    :return: tagged mtgl text
    """
    ntxt = preprocess(name,txt)
    ntxt = first_pass(ntxt)
    #ntxt = postprocess(ntxt)
    return ntxt

#### PREPROCESSING ####

def preprocess(name,txt):
    """
     conducts an initial scrub of the oracle text. Then:
       1. replaces card name references with ref-id or self as necessary
       2. lowercases oracle text
       3. english number words for 0 through 10 are replacing with corresponding ints,
       4. contractions are replaced with full words
       5. Some reminder text is removed, some paraenthesis is removed
       6. take care of keywords that are exemptions to keyword rules
    :param name: name of this card
    :param txt: the mtgl text
    :return: preprocessed oracle text
    """
    # a keyword
    ntxt = tag_ref(name,txt).lower() # lowercase everything after referencing
    ntxt = pre_special_keywords(ntxt)
    ntxt = mtgl.re_wh.sub(lambda m: mtgl.word_hacks[m.group(1)],ntxt)
    ntxt = mtgl.re_wd2int.sub(lambda m: mtgl.E2I[m.group(1)],ntxt)
    ntxt = mtgl.re_mana_remtxt.sub(r"\1",ntxt) # remove paranthesis around (Add {G})
    ntxt = mtgl.re_rem_txt.sub("",ntxt)
    return mtgl.re_non.sub(r"non-\1",ntxt)

    #ntxt = mtgl.re_acts_conj.sub(lambda m: mtgl.all_acts[m.group(1)],ntxt)
    #return mtgl.re_characteristics_conj.sub(
    #    lambda m: mtgl.all_characteristics[m.group(1)],ntxt
    #)

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

def pre_special_keywords(txt):
    """
     take special keywords (pre-tagged) cycling and landwalk and seperate the type
     from the keyword
    :param txt: lower-cased oracle text (not tagged)
    :return: processed oracle text
    NOTE: this has to occur after self tagging, lowercasing
    """
    # cycling has two forms 1) Cycling [cost] and 2) [Type]cycling [cost] where
    # type may consist of two seperate words i.e. basic landcycling
    ntxt = mtgl.re_cycling_pre.sub(r"\1 cycling",txt)

    # landwalk will have the form [type]walk where type could be a basic land type
    # i.e. forestwalk or a nonbasic land as in legendary landwalk. In both cases
    # isolate (and make the word if necessary) landwalk and the type(s) as in
    # forestwalk = forest landwalk and legendary landwalk
    ntxt = mtgl.re_landwalk_pre.sub(r"\1 landwalk",ntxt)
    return ntxt

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
    # first pass, tag everything without context inspection
    ntxt = tag_status(txt)
    ntxt = tag_turn_structure(ntxt)
    #ntxt = tag_numbers(ntxt)
    #ntxt = tag_quantifiers(ntxt)
    #ntxt = tag_effects(ntxt)
    #ntxt = tag_entities(ntxt)
    #ntxt = tag_characteristics(ntxt)
    #ntxt = tag_counters(ntxt)
    #ntxt = tag_awkws(ntxt)
    #ntxt = tag_zones(ntxt)
    #ntxt = tag_trigger(ntxt)
    #ntxt = tag_english(ntxt)
    return ntxt

def tag_status(txt):
    """ tags status words in txt returning tagged text """
    return mtgl.re_stat.sub(r"st<\1>",txt)

def tag_turn_structure(txt):
    """ tags turn structure phrases in in txt returning tagged text """
    ntxt = mtgl.re_phase.sub(r"ph<\1>",txt)
    ntxt = mtgl.re_step1.sub(r"sp<\1>",ntxt)
    ntxt = mtgl.re_step2.sub(r"sp<\1>",ntxt)
    return ntxt