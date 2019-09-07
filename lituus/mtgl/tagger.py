#!/usr/bin/env python
""" tagger.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Tags MTG oracle text in the mtgl format
"""

__name__ = 'tagger'
__license__ = 'GPLv3'
__version__ = '0.0.5'
__date__ = 'September 2019'
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
    return postprocess(ntxt)

#### PREPROCESSING ####

def preprocess(name,txt):
    """
     conducts an initial scrub of the oracle text txt. After this
       1. replaces card name references with ref-id or self as necessary
       2. lowercases oracle and replace ';' with ',' (older cards have semi-colons
        vice commas seperating keyword clauses
       3. standarizes some common phrases
         a. shuffle your library clause - will now read ", then shuffle your
          library" rather as a seperate sentence
         b. "command zone" - "zone" is implied replaced with "command" only
         c. "your opponent(s)" - "your" is implied, replaced with "opponent(s)" only
       4. possessive "'s" removed
       5. english number words for 0 through 10 are replacing with corresponding ints,
       6. contractions are replaced with full words
       7. common phrases replaced by acronyms
       8. some pluralities i.e. 'y' to 'ies' hacked to read 'ys'
       9. action word pluralities replaced with singular form
      10. Some reminder text is removed, some paraenthesis is removed
      11. take care of keywords that are exemptions to keyword rules
      12. replace occurrences of command zone with command
      13. remove simple determiners 'a', 'an' and 'the'
    :param name: name of this card
    :param txt: the mtgl text
    :return: preprocessed oracle text
    """
    # a keyword
    ntxt = tag_ref(name,txt).lower()
    ntxt = pre_special_keywords(ntxt)
    ntxt = standarize(ntxt)
    ntxt = mtgl.re_wint.sub(lambda m: mtgl.E2I[m.group(1)],ntxt)
    ntxt = mtgl.re_mana_rtxt.sub(r"\1",ntxt)
    ntxt = mtgl.re_rem_txt.sub("",ntxt)
    ntxt = mtgl.re_non.sub(r"non-\1",ntxt)
    ntxt = mtgl.re_acts_conj.sub(lambda m: mtgl.all_acts[m.group(1)],ntxt)
    return mtgl.re_characteristics_conj.sub(
        lambda m: mtgl.all_characteristics[m.group(1)],ntxt
    )

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
    ntxt = mtgl.re_self_ref(name).sub(r"ob<card ref=self>",txt)
    assert(mtgl.re_oth_ref is not None)
    return mtgl.re_oth_ref.sub(
        lambda m: r"{} ob<card ref={}>".format(m.group(1),mtgl.N2R[m.group(2)]),ntxt
    )

def standarize(txt):
    """
     standarizes common phrases
    :param txt: the current text
    :return: standarized text
    """
    ntxt = txt.replace(';',mtgl.CMA)
    ntxt = mtgl.re_wh.sub(lambda m: mtgl.word_hacks[m.group(1)],ntxt)
    ntxt = ntxt.replace("'s","")
    ntxt = ntxt.replace("s'","s")
    ntxt = ntxt.replace("command zone","command")
    return ntxt.replace("your opponent","opponent")

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

#### FIRST PASS ####

def first_pass(txt):
    """
     performs a first pass of the oracle txt after pre-processing
    :param txt: preprocessed oracle txt (lowered case)
    :return: tagged oracle text
     NOTE: many (but not all) of the below require certain replacements/tagging
      to be carried out prior to their execution, rearranging the order of the
      below will negatively effect the results
    """
    # first pass, tag everything without context inspection
    ntxt = tag_status(txt)
    ntxt = tag_phases(ntxt)
    ntxt = tag_numbers(ntxt)
    ntxt = tag_quantifiers(ntxt)
    ntxt = tag_effects(ntxt)
    ntxt = tag_entities(ntxt)
    ntxt = tag_characteristics(ntxt)
    ntxt = tag_counters(ntxt)
    ntxt = tag_awkws(ntxt)
    ntxt = tag_zones(ntxt)
    ntxt = tag_trigger(ntxt)
    ntxt = tag_english(ntxt)
    return ntxt

def tag_status(txt):
    ntxt = mtgl.re_stat.sub(r"st<\1>",txt)
    return mtgl.re_lituus_stat.sub(r"xs<\1>",ntxt)

def tag_phases(txt):
    ntxt = mtgl.re_phase.sub(r"ph<\1>",txt)
    return mtgl.re_phase2.sub(r"ph<\1>",ntxt)

def tag_counters(txt):
    ntxt = mtgl.re_pt_ctr.sub(r"xo<ctr type=\1\2/\3\4>",txt)  # tag p/t counters
    return mtgl.re_named_ctr.sub(r"xo<ctr type=\1>",ntxt)     # & named counters

def tag_numbers(txt): return mtgl.re_mint.sub(r"nu<\1>",txt)

def tag_quantifiers(txt): return mtgl.re_lituus_qu.sub(r"xq<\1>",txt)

def tag_effects(txt): return mtgl.re_ef.sub(r"ef<\1>",txt)

def tag_entities(txt):
    """
     tags players, mtg objects and lituus objects
    :param txt: text to be tagged
    :return: entity tagged text
    """
    ntxt = mtgl.re_lituus_ply.sub(r"xp<\1>",txt)  # tag players
    ntxt = mtgl.re_lituus_obj.sub(r"xo<\1>",ntxt) # tag lituus objects
    return mtgl.re_obj.sub(r"ob<\1>",ntxt)      # tag mtg objects

def tag_characteristics(txt):
    ntxt = mtgl.re_ch.sub(r"ch<\1>",txt)                    # tag characteristics
    ntxt = mtgl.re_ch_pt.sub(r"ch<p/t val=\1\2/\3\4>",ntxt) # tag p/t
    return mtgl.re_lituus_ch.sub(r"xc<\1>",ntxt)            # tag lituus char. & return

def tag_awkws(txt):
    ntxt = mtgl.re_aw.sub(r"aw<\1>",txt)          # tag ability words
    ntxt = mtgl.re_kw.sub(r"kw<\1>",ntxt)         # tag keywords
    ntxt = mtgl.re_kw_act.sub(r"ka<\1>",ntxt)     # tag keyword actions
    return mtgl.re_lituus_act.sub(r"xa<\1>",ntxt) # tag lituus actions

def tag_zones(txt): return mtgl.re_zone.sub(r"zn<\1>",txt)

def tag_trigger(txt): return mtgl.re_trigger.sub(r"mt<\1>",txt)

def tag_english(txt):
    """
     tags english words
    :param txt: untagged text
    :return: english tagged tagged text
    """
    ntxt = mtgl.re_op.sub(lambda m: "op<{}>".format(mtgl.OP[m.group(1)]),txt)
    ntxt = mtgl.re_prep.sub(r"pr<\1>",ntxt) # tag prepositions
    ntxt = mtgl.re_cond.sub(r"cn<\1>",ntxt) # & conditional/rqmt
    return mtgl.re_seq.sub(r"sq<\1>",ntxt)  # & sequence words

#### POST PROCESSING

def postprocess(txt):
    """
     conducts post processing after the initial first pass in order to prep for
     tokenization and the second pass by the parser.
      1. changes modal spells, moving options to one line
      2. merges two or more tags and/or words mistagged during first pass
      3. replaces occurrences of space|hyphen inside singleton tags with '_'
      4. moves all level descriptions to one line for each level in level up cards
    :param txt: oracle text after first pass
    :return: post processed oracles text
    """
    ntxt = txt.replace("\n• ","•")                     # modal spells
    ntxt = merge_tags(ntxt)                            # merge multiple tags
    ntxt = mtgl.re_negate_tag.sub(r"\1<¬\2>",ntxt)     # relocate negated tags
    ntxt = mtgl.re_non_possessive.sub(r"xc<¬\1>",ntxt) # relocate non-possessive
    ntxt = mtgl.re_pro_fix.sub( # special fix for extended protection clauses
        r"kw<protection> pr<from> ch<\1> and pr<from> ch<\2> and pr<from>",ntxt
    )

    # fix operators
    ntxt = mtgl.re_le.sub(r"ch<\1> op<≤> nu<\2>",ntxt) # 'or less'
    ntxt = mtgl.re_ge.sub(r"ch<\1> op<≥> nu<\2>",ntxt) # 'or greater
    ntxt = mtgl.re_is_op.sub(r"\1",ntxt)               # 'is' operator
    ntxt = mtgl.re_op_to.sub(r"\1",ntxt)               # operator 'to'
    ntxt = mtgl.re_up_to.sub(r"nu<≤\1>",ntxt)          # 'up to' D

    # probably not the best method, but repeat the token prep pattern until no more
    # spaces/hyphens exist inside tags of only words
    while mtgl.re_tag_prep.search(ntxt): ntxt = mtgl.re_tag_prep.sub(r"<\1_\3>",ntxt)

    # fix level up
    if ntxt.startswith('kw<level_up>'): ntxt = fix_lvl_up(ntxt)

    return ntxt

def merge_tags(txt):
    """
     merges tags/words
    :param txt: the tagged text
    :return: merged tagged text
    """
    for mt in mtgl.rephrase: txt = txt.replace(mt,mtgl.rephrase[mt])
    return txt

def fix_lvl_up(txt):
    """
     rewrites txt so that all descriptions of each level in a level up card
     are on a single line
    :param txt: tagged oracle text for a level up card
    :return: fixed level up text
    """
    # get indexes for each level, add start and end
    ls = [0]+[m.start() for m in mtgl.re_lvl.finditer(txt)]+[len(txt)]

    # remove all newlines, then append a newline for each level
    ltxt = ""
    for i,j in enumerate(ls):
        if i < len(ls) - 1:
            if i < len(ls) - 1:
                if i == 0:
                    # the first line is the level up COST line, remove any
                    # <break>s & add one newline
                    ltxt = ltxt.replace('<break>','')
                    ltxt += '\n'
                else:
                    # for the remaining lines, add a period if one doesn't exist
                    # and add a newline
                    if not ltxt.endswith(mtgl.PER): ltxt += mtgl.PER
                    ltxt += '\n'

    # change ch<p/t to ls<p/t iot parser ignores it
    ltxt = ltxt.replace('ch<p/t','ls<p/t')

    return ltxt