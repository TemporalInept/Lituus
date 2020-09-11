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
__version__ = '0.1.8'
__date__ = 'August 2020'
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
        ntxt = postprocess(ntxt)
        ntxt = third_pass(ntxt)
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
        a. keep add mana removing the paranthesis
        b. keep melds with ... removing the paraenthesis
       7. replace any 'non' w/out hypen to 'non-' w/ hyphen
       8. replace any ", then" with "then"
       9. Modify modal spells
         a. Replace occurrences of ".•" with " •" in modal spells
         b. if present, replace the last occurrence of ". " with a semi-colon
      10. Fix level ups removing newlines inside of the the level descriptions
        and prefixing each level description with a bullet
      11. Fix sagas removing newlines inside of the chapter descriptions
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
    ntxt = mtgl.re_mana_remtxt.sub(r"\1",ntxt)                               # 6.a
    ntxt = mtgl.re_melds_remtxt.sub(r"\1",ntxt)                              # 6.b
    ntxt = mtgl.re_reminder.sub("",ntxt)                                     # 6
    ntxt = mtgl.re_non.sub(r"non-\1",ntxt)                                   # 7
    ntxt = ntxt.replace(", then"," then")                                    # 8
    if '•' in ntxt:                                                          # 9
        ntxt = mtgl.re_modal_blt.sub(r" •",ntxt)
        ntxt = mtgl.re_modal_lvl_instr_fix.sub(r" ; ",ntxt)
    if mtgl.re_lvl_up.search(ntxt): ntxt = fix_lvl_up(ntxt)                  # 10
    ntxt = mtgl.re_saga_chapter.sub(r"\1 — ",ntxt)                           # 11
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
    # token names, including meld
    ntxt = mtgl.re_tkn_ref1.sub(
        lambda m: r"{} ob<token ref={}>".format(
            m.group(1), mtgl.TN2R[m.group(2)]), txt
    )
    ntxt = mtgl.re_tkn_ref2.sub(
        lambda m: r"create ob<token ref={}>, {} token".format(
            mtgl.TN2R[m.group(1)], m.group(2)
        ), ntxt
    )
    ntxt = mtgl.re_tkn_ref3.sub(
        lambda m: r"ob<token ref={}>".format(mtgl.MN2R[m.group(1)]), ntxt
    )

    # references to other cards prefixed with 'named', 'Partner with' or melds with
    # This does not catch cases where there is an 'and' i.e. Throne of Empires
    #  "... named Crown of Empires and Scepter of Empires. For now, have to hack
    #  it using mtgl.re_oth_ref2
    ntxt = mtgl.re_oth_ref.sub(
        lambda m: r"{} ob<card ref={}>".format(m.group(1),mtgl.N2R[m.group(2)]),ntxt
    )
    ntxt = mtgl.re_oth_ref2.sub(
        lambda m: r"ob<token ref={}>".format(mtgl.NC2R[m.group(1)]),ntxt
    )

    # replace self references - do last to avoid conflict i.e. Hanweir Garrison
    return mtgl.re_self_ref(name).sub(r"ob<card ref=self>",ntxt)

def fix_lvl_up(txt):
    """
    Performs two modifications:
     1. splits the level up keyword line into the keyword clause(Level up [cost])
      and level descriptions
     2. inserts a bullet before each occurrence of level and replace all newlines
      with a space
     This will result in level up COST\nBLTlevel DESCRIPTION ... BLTlevel DESCRIPTION
    :param txt: level up text to modify
    :return: modified level up text
    """
    kw,line = mtgl.re_lvl_up.split(txt)[1:]                                # 1
    line = mtgl.BLT + mtgl.re_lvl_blt.sub(mtgl.BLT,line).replace('\n',' ') # 2
    return "{}\n{}".format(kw,line)

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
    ntxt = mtgl.re_number.sub(r"nu<\1>",ntxt)    # then numbers
    ntxt = tag_counters(ntxt)                    # markers
    ntxt = tag_entities(ntxt)                    # entities
    ntxt = tag_turn_structure(ntxt)              # phases & steps
    ntxt = tag_operators(ntxt)                   # operators
    ntxt = tag_english(ntxt)                     # english words
    ntxt = mtgl.re_trigger.sub(r"tp<\1>",ntxt)   # trigger preambles
    ntxt = tag_awkws(ntxt)                       # ability words, keywords & actions
    ntxt = mtgl.re_effect.sub(r"ef<\1>",ntxt)    # effects
    ntxt = tag_characteristics(ntxt)             # chars. - done after #s
    ntxt = mtgl.re_zone.sub(r"zn<\1>",ntxt)      # zones
    ntxt = mtgl.re_qualifier.sub(r"xl<\1>",ntxt) # qualifiers
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
    ntxt = mtgl.re_combat_phase.sub(r"ts<combat>",ntxt)
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
    ntxt = mtgl.re_pt_ctr.sub(r"xo<ctr type=\1\2/\3\4>",txt)    # tag p/t counters
    ntxt = mtgl.re_named_ctr.sub(lambda m: _named_ctr_(m),ntxt) # named counters
    ntxt = mtgl.re_iko_ctr.sub(r"xo<ctr type=\1>",ntxt)         # & IKO counters
    return ntxt

def tag_awkws(txt):
    """ tags ability words, keywords and action words returning tagged txt """
    ntxt = mtgl.re_aw.sub(r"aw<\1>",txt)                        # ability words
    ntxt = mtgl.re_kw.sub(r"kw<\1>",ntxt)                       # keyword abilities
    ntxt = mtgl.re_kw_act.sub(r"ka<\1>",ntxt)                   # keyword actions
    ntxt = mtgl.re_lituus_act.sub(r"xa<\1>",ntxt)               # lituus actions
    ntxt = mtgl.re_lituus_target_verb.sub(r"xa<target>\1",ntxt) # target action
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
       1. replaces spaces inside tags w/ underscore IOT make it a single tag value
       2. moves 'non-' in front of a tag to the negated symbol '¬' inside the tag
       3. move suffixes to inside the tag's prop-list
       4. set up hanging (a) basic and (b) snow supertypes
       5. arrange phrases with 'number'
        a. arrange phrases of the form op<OP> xq<the> number of ... to read
         op<OP> nu<y>, where nu<y> is the number of ... so that they read the
         same as cards like "As Foretold"
        b. replace "any number of" with nu<z>
        c. remove "are each" if followed by an operator
       6. replace 'mana cost' as xo<cost type=mana>
       7. replace 'no' followed by a thing (or quanitifier) as nu<0>
       8. deconflict incorrectly tagged tokens
    :param txt: tagged oracle txt
    :return: processed oracle txt
    """
    ntxt = mtgl.re_val_join.sub(lambda m: mtgl.val_join[m.group(1)],txt) # 1
    ntxt = mtgl.re_negate_tag.sub(r"\1<¬\2>",ntxt)                       # 2
    ntxt = mtgl.re_suffix.sub(r"\1<\2 suffix=\3>",ntxt)                  # 3
    ntxt = mtgl.re_hanging_basic.sub(r"\1 ch<land>",ntxt)                # 4.a
    ntxt = mtgl.re_hanging_snow.sub(r"\1 ch<land>",ntxt)                 # 4.b
    ntxt = mtgl.re_equal_y.sub(r"nu<y>, where nu<y> is \1",ntxt)         # 5.a
    ntxt = mtgl.re_equal_z.sub(r"nu<z>",ntxt)                            # 5.b
    ntxt = mtgl.re_are_each.sub(r"",ntxt)                                # 5.c
    ntxt = mtgl.re_mana_cost.sub(r"xo<cost type=mana\1>",ntxt)           # 6
    ntxt = mtgl.re_no_thing.sub(r"nu<0>",ntxt)                           # 7
    ntxt = deconflict_tags1(ntxt)                                        # 8
    return ntxt

re_empty_postfix = re.compile(r"\ssuffix=(?=)>")
def deconflict_tags1(txt):
    """
    deconflicts incorrectly tagged tokens
    :param txt: oracle txt after initial first pass
    :return: tagged oracle text
    """
    # Tapped, Flipped
    ntxt = mtgl.re_status.sub(r"st<\1\2 suffix=ed>",txt)
    ntxt = mtgl.re_status_tap.sub(r"st<\1tap suffix=ed>",ntxt)

    # phase - can be Status (Time and Tide), Turn Structure (Breath of Fury) or
    #  action (Ertai's Familiar),
    ntxt = mtgl.re_status_phase.sub(r"st<phase amplifier=\1 suffix=ed>",ntxt)
    ntxt = mtgl.re_action_phase.sub(r"xa<phase amplifier=\2 suffix=\1>",ntxt)
    ntxt = mtgl.re_ts_phase.sub(r"ts<phase suffix=\1>",ntxt)
    ntxt = re_empty_postfix.sub('>', ntxt) # may result in empty suffixes, remove

    # Face Up/Down
    ntxt = mtgl.re_status_face.sub(r"st<face amplifier=\1>",ntxt)
    ntxt = mtgl.re_mod_face.sub(r"xm<face amplifier=\1>",ntxt)

    # turn could be a lituus action and in some cases an object
    ntxt = mtgl.re_turn_action.sub(r"xa<\1>",ntxt)

    # exile is a zone if preceded by a preposition
    ntxt = mtgl.re_zn_exile.sub("zn<exile>",ntxt)

    # Cost is defined as an object but may be an action
    ntxt = mtgl.re_cost_mana.sub(r"xa<cost\1>",ntxt)
    ntxt = mtgl.re_cost_num.sub(r"xa<cost\1>",ntxt)
    ntxt = mtgl.re_cost_aa.sub(r"xa<cost\1>",ntxt)
    ntxt = mtgl.re_cost_except.sub(r"xa<cost\1>",ntxt)

    # Flip is defined as an action word but in some cases is an object (i.e.
    # win the flip)
    ntxt = mtgl.re_flip_object.sub(r"xo<flip>",ntxt)
    ntxt = mtgl.re_coin_flip.sub(r"xo<flip type='coin'>",ntxt)

    # deconflict counters as object or action
    ntxt = mtgl.re_counters_obj.sub(r"xo<ctr suffix=s>",ntxt)
    ntxt = mtgl.re_counter_obj.sub(r"xo<ctr>",ntxt)

    # take care of misstagged
    ntxt = mtgl.re_misstag.sub(lambda m: mtgl.misstag[m.group(1)],ntxt)

    # Tag combat preceded by from as an object
    ntxt = mtgl.re_from_combat.sub(r"xo<combat>",ntxt)

    # retag discarded as status where necessary, retag enchanted
    ntxt = mtgl.re_discard_stat.sub(r"xs<discard suffix=ed>",ntxt)
    ntxt = mtgl.re_enchant_stat.sub(r"xs<enchant suffix=ed>",ntxt)

    # retag spent as a status
    ntxt = mtgl.re_spend_stat.sub(r"xs<\1spent>",ntxt)

    # deconflict 'at' making it a preposition when followed by a qualifier
    ntxt = mtgl.re_at_prep.sub(r"pr<at>",ntxt)
    ntxt = mtgl.re_at_prep2.sub(r"pr<at>",ntxt)

    # a few cards (7) will have the phrase 'no nu<1>' - make this xp<no_one>,
    #(2) will have the phrase "with no" - make these pr<without> and several
    ntxt = mtgl.re_no_one.sub(r"xp<no_one>",ntxt)
    ntxt = mtgl.re_with_null.sub(r"pr<without>",ntxt)
    ntxt = mtgl.re_no_dmg.sub(r"nu<0> \1",ntxt)

    # Not deconflictions perse:
    #  1. to avoid conflicts 'named' is listed as an action, rewrite it here so
    #  it shows up xa<name suffix=ed> rather than xa<named>
    #  2. occurrences of pr<up_to> nu<NUMBER> should be replaced by LE nu<NUMBER>
    #  3. (three cases i.e. Sewer Rats) are tage LE NUMBER sq<time> standarize
    #   these to only LE NUMBER times
    ntxt = ntxt.replace("xa<named>","xa<name suffix=ed>")
    ntxt = mtgl.re_upto_op.sub(r"op<{}>".format(mtgl.LE),ntxt)
    ntxt = mtgl.re_only_upto.sub(r"cn<only> \1",ntxt)

    return ntxt

####
## 2ND PASS
####

def second_pass(txt):
    """
    performs a second pass of the oracle txt, working on Things and Attributes,
    and lituus statuses which may have to be deconflicted
     1. conduct pre chaining of characteristics
     2. chain characteristics
     3. reify characteristics
     4. conduct post chaining
     5. additional deconfliction of tags
     6. chain other tags
     7. merge objects with preceding/following tags
    :param txt: first pass tagged oracle txt
    :return: tagged oracle text
    """
    ntxt = pre_chain(txt)
    ntxt = chain(ntxt)
    ntxt = reify(ntxt)
    ntxt = post_chain(ntxt)
    ntxt = deconflict_tags2(ntxt)
    ntxt = chain_other(ntxt)
    ntxt = merge(ntxt)
    return ntxt

def pre_chain(txt):
    """
    Facilitates chaining by
     1) handle special case of 'base power and toughness' replace phrase base
     ch<power> and ch<toughness> ch<p/t val=X/Y> with ch<p/t val=X/Y>
     2) attributes - (stand alone meta-characteristics)
      a. temporarily tag attributes as xr
      b. assign values where possible to temporary attributes including c.
        those without an operator
      d. fix xr<color suffix=ed> to xr<color val=colored>
      e. chain cases of power and/pr toughness where toughness has a value
     3) attributes part 2 - (stand alone lituus objects like life)
      a. assign values where possible (Triskaidekaphobia)
     4) add types to hanging subtypes
     5) modify anamolous characteristic action charactistic
     6) align supertypes and subtypes

    :param txt: txt to prechain
    :return: prechainned text
    """
    ntxt = powt(txt)                                                    # 1
    ntxt = mtgl.re_meta_attr.sub(lambda m: _metachar_(m),ntxt)          # 2.a
    ntxt = mtgl.re_attr_val.sub(r"xr<\1 val=\2\3>",ntxt)                # 2.b
    ntxt = mtgl.re_attr_val_wd.sub(r"xr<\2 val=≡\1>",ntxt)              # 2.b
    ntxt = mtgl.re_attr_val_nop.sub(r"xr<\1 val=≡\2>",ntxt)             # 2.c
    ntxt = mtgl.re_attr_colored.sub(r"xr<color val=\1ed>",ntxt)         # 2.d
    ntxt = mtgl.re_combine_pt.sub(                                      # 2.e
        lambda m: r"xr<power{}toughness val={}>".format(
            mtgl.conj_op[m.group(1)],m.group(2)),ntxt
    )
    ntxt = mtgl.re_op_num_lo.sub(r"xr<\3 val=\1\2>",ntxt)               # 3
    ntxt = mtgl.re_hanging_subtype.sub(lambda m: _insert_type_(m),ntxt) # 4
    ntxt = mtgl.re_disjoint_ch.sub(r"\2 \1 \3",ntxt)                    # 5
    ntxt = align_types(ntxt)                                            # 6
    return ntxt

def powt(txt):
    """
    chains phrase power and toughness accordingly as well as p/t chains
    :param txt: tagged oracle txt
    :return: modified tagged txt with power and toughness and p/t chains tagged
    """
    ntxt = mtgl.re_base_pt.sub(r"\1",txt)                    # base power & toughness
    ntxt = mtgl.re_pt_chain.sub(lambda m: _ptchain_(m),ntxt) # p/t or p/t chain
    return ntxt

def align_types(txt):
    """
    conducts alignment of types
    :param txt: tagged oracle txt
    :return: aligned txt
    """
    #  Run align_dual up front to check cards like Silumgar Monument for dual
    #  types prior to aligning super and sub
    #  Then after aligning super and sub, run align_n to:
    #   1. Check cards like Gargantuan Gorilla for dual types
    #   2. Check cards like Warden of the First Tree for more than 2 consecutive
    #    types
    ntxt = mtgl.re_align_dual.sub(lambda m: _align_n_(m),txt)      # dual types
    ntxt = mtgl.re_align_sub.sub(lambda m: _align_type_(m),ntxt)   # sub, type
    ntxt = mtgl.re_align_super.sub(lambda m: _align_type_(m),ntxt) # super, type
    ntxt = mtgl.re_align_n.sub(lambda m: _align_n_(m),ntxt)        # consecutive types
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
    # TODO: Hacky we don't want to chain Elven Riders so have to perform a check
    # first prior to substituting
    ntxt = mtgl.re_chain('ch').sub(lambda m: _chain_check_(m),ntxt)

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

def post_chain(txt):
    """
    Further reduced objects and does additional tagging that can only be done
    after reification
     1. combine consecutive space delimited objects where possible
     2. replace no followed by an object with 0
    :param txt: chained and reified oracle txt
    :return: further reduced oracle text
    """
    ntxt = mtgl.re_consecutive_obj.sub(lambda m: _consecutive_obj_(m),txt)
    ntxt = mtgl.re_no2num.sub(r"nu<0>",ntxt)
    ntxt = mtgl.re_uninit_attr.sub(r"xr<\1 val=\2y>, where nu<y> is",ntxt)
    return ntxt

def deconflict_tags2(txt):
    """
    Deconflicts tags which are easier to do after characterstics have been reifed
    :param txt: tagged, chained and reified txt
    :return: txt with lituus statuses deconflicted
    """
    # start off with lituus statuses that have been tagged as something else
    ntxt = mtgl.re_ed_lituus_status.sub(r"xs",txt)
    ntxt = mtgl.re_ed_thing_lituus_status.sub(r"xs",ntxt)

    # combat related
    ntxt = mtgl.re_combat_status_chain.sub(lambda m: _combat_status_chain_(m),ntxt)
    ntxt = mtgl.re_combat_status.sub(r"xs<\1 suffix=ing>",ntxt)

    # activated and triggered, first chain the 5 'or' conjunctions
    ntxt = mtgl.re_ab_type_chain.sub(r"xs<activate∨trigger suffix=ed>",ntxt)
    ntxt = mtgl.re_ab_status.sub(r"xs<\1 suffix=ed>",ntxt)
    ntxt = mtgl.re_activation_cost.sub(r"xo<cost type=activation\1>",ntxt)

    # deconflict target as quantifier, object or action. 1) handle specials cases
    # follow rules for actions but are in fact objects. 2) take care of actions
    ntxt = mtgl.re_target_sc.sub(r"ob<target> and xq<that> ob<target>",ntxt)
    ntxt = mtgl.re_target_act.sub(r"xa<target>",ntxt)
    ntxt = mtgl.re_target_obj.sub(r"ob<target>",ntxt)

    # deconflict copy as action vs object (TODO: this could be done in the first
    # deconfliction)
    ntxt = mtgl.re_copy_act.sub(r"xa<copy\2>",ntxt)

    # look at keywords that could be converted to action words i.e. kicked and/or
    # status i.e. equipped
    ntxt = mtgl.re_kicker_act.sub(r"xa<kicker suffix=ed>",ntxt)
    ntxt = mtgl.re_be_kw.sub(r"xa<\1 suffix=ed>",ntxt)
    ntxt = mtgl.re_kw_status.sub(r"xs<\1 suffix=ed>",ntxt)
    ntxt = mtgl.re_kw_action.sub(r"xa<\1 suffix=s>",ntxt)

    # action words that can be converted to status' i.e. sacrificed
    ntxt = mtgl.re_action_status.sub(r"xs<\1>",ntxt)

    # combine some phases/steps & deconflict draw a step vs action
    #  1. any two consecutive turn structures unless the first is possessive
    #  2. declare attacker|blocker step
    ntxt = mtgl.re_consecutive_ts.sub(r"ts<\1>",ntxt)
    ntxt = mtgl.re_declare_step.sub(r"ts<declare-\1s>",ntxt)
    ntxt = mtgl.re_draw_step.sub(r"\1 ts<draw>",ntxt)

    return ntxt

def chain_other(txt):
    """
    chains tags other than characteristics
     1. zones and keywords will be compined
     2. combine objects if spell and/or ability
    :param txt: the tagged text
    :return: text with additional tags chained
    """
    ntxt = mtgl.re_chain('kw').sub(lambda m: _chain_(m),txt)
    ntxt = mtgl.re_chain('zn').sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_chain('ob').sub(lambda m: _chain_obj_(m),ntxt)
    ntxt = mtgl.re_chain('xo').sub(lambda m: _chain_ctr_(m),ntxt)
    ntxt = mtgl.re_chain('nu').sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_chain('xc').sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_chain('pr').sub(lambda m: _chain_(m),ntxt)
    ntxt = mtgl.re_chain_quantifiers.sub(lambda m: _chain_(m),ntxt)
    return ntxt

def merge(txt):
    """
    Many objects are followed by additional criteria:
     1. with keyword(s)
    :param txt: tagged, chained and reified txt with deconflicted status
    :return: objects with following critieria merged
    """
    ntxt = mtgl.re_obj_with_kw.sub(lambda m: _obj_with_(m),txt)
    return ntxt

def postprocess(txt):
    """
    post processes tagged txt in preparation for graphing
    :param txt: tagged text
    :return: processed txt
    """
    # find "kw cost" rewrite as "cost type=kw"
    ntxt = mtgl.re_cost_type.sub(lambda m: _cost_type_(m),txt)

    # punctuation followed by a quote (single/double/both) is moved to the outside
    # NOTE: have only seen periods but just in case
    ntxt = mtgl.re_encl_punct.sub(r"\2\1",ntxt)

    # combine stem and suffix on status i.e. st<tap suffix=ed> becomes st<tapped>
    ntxt = mtgl.re_status_suffix.sub(lambda m: _join_suffix_(m),ntxt)

    # combine type of ability to ability
    ntxt = mtgl.re_ability_type.sub(lambda m: _join_ability_(m),ntxt)

    # lazy tagging of 'is' verbs as a lituus action to avoid rewriting regex
    # patterns using 'is' versus a tagged version
    ntxt = mtgl.re_is2tag.sub(lambda m: mtgl.is_forms[m.group(1)],ntxt)

    # reify turns (has to be done here after chaining of quanitifiers)
    ntxt = mtgl.re_turn_object.sub(r"\1 xo<\2>",ntxt)

    # combine occurrences of OP NUMBER with OPNUMBER inside number tag
    ntxt = mtgl.re_op_num.sub(r"nu<\1\2>",ntxt)

    # combine damage with any preceding number
    ntxt = mtgl.re_num_dmg.sub(r"ef<\2 quantity=\1>",ntxt)

    # combine phrases of the form power and toughness = y
    ntxt = mtgl.re_pt_value.sub(r"xr<power∧toughness val=\1>",ntxt)

    return ntxt

def third_pass(txt):
    """
    performs a third/final pass of the oracle txt, working primarily on common
    phrases, replacing them with defined keyword actions, common slang or
    easier to process forms
    :param txt: second pass tagged oracle txt
    :return: tagged oracle text
    """
    # TODO: add loot, rummage? if so how to do if the # drawn is different then
    #  the # discarded i.e. attunement and how would this affect the words
    #  drawn & discard
    # mtg slang
    ntxt = mtgl.re_mill.sub(
        lambda m: r"xa<mill{}> {}".format(
            m.group(1) if m.group(1) else '',     # add suffix if present
            m.group(2) if m.group(2) else 'nu<1>' # if # not specified, make it 1
        ),txt
    )
    #ntxt = mtgl.re_loot.sub(
    #    lambda m: r"xa<loot draw={} discard={}>".format(
    #        _loot_num_(m.group(1)),
    #        _loot_num_(m.group(2))),
    #    txt)
    ntxt = mtgl.re_flicker.sub(
        lambda m: r"xa<flicker> {}{}".format(
            m.group(1),
            ' '+m.group(3) if m.group(3) else ''
        ),txt
    )
    ntxt = mtgl.re_detain.sub(r"xa<detain> \1",ntxt)
    ntxt = mtgl.re_etb.sub(r"xa<etb\1>",ntxt)
    ntxt = mtgl.re_ltb.sub(r"xa<ltb\1>",ntxt)

    # fix possessives (own, control) using logic symbols instead of tokens
    ntxt = mtgl.re_your_opponents.sub(r"xp<opponent suffix=s>",ntxt)  # for grapher
    ntxt = mtgl.re_one_of_opponents.sub(r"xq<a> xp<opponent>",ntxt)    # for grapher
    ntxt = mtgl.re_both_ownctrl.sub(r"\1",ntxt)
    ntxt = mtgl.re_neither_ownctrl.sub(r"xc<¬own∧¬control>", ntxt)
    ntxt = mtgl.re_own_not_ctrl.sub(r"xc<own∧¬control>",ntxt)
    ntxt = mtgl.re_dont_ownctrl.sub(r"xc<¬\1>",ntxt)

    # rewrite able to block IOT facilitate graphing
    ntxt = mtgl.re_able_to_block.sub(r"\1 xa<block> \2 cn<if> able",ntxt)

    # combine prefix action words of the form 'to be' action word (i.e. be cast)
    # and 'to' action word (i.e. to cast)
    ntxt = mtgl.re_prefix_aw.sub(lambda m: _prefixed_act_word_(m),ntxt)

    # remove reduant 'own'
    ntxt = mtgl.re_ply_own_phase.sub(r"\1 \2",ntxt)

    # deconflict/retag voting
    if mtgl.re_vote_check.search(ntxt): ntxt = deconflict_vote(ntxt)

    return ntxt

def deconflict_vote(txt):
    """
     deconflict vote in txt as an object vice action
    :param txt: taggec oracle txt (has been verfied as containing votes)
    :return: deconflicted vote tagged text
    """
    ntxt = txt

    # handle 'named' candidates, tagging each as a vote object
    try:
        c1,c2 = mtgl.re_vote_candidates.search(txt).groups()
        nc1 = _tag_vote_candidate_(c1)
        nc2 = _tag_vote_candidate_(c2)
        ntxt = mtgl.re_vote_choice.sub(r"{} or {}.".format(nc1,nc2),txt)
        ntxt = mtgl.vote_obj1(c1).sub(nc1,ntxt)
        ntxt = mtgl.vote_obj1(c2).sub(nc2,ntxt)
        ntxt = mtgl.vote_obj2(c1).sub(nc1,ntxt)
        ntxt = mtgl.vote_obj2(c2).sub(nc2,ntxt)
    except AttributeError:
        pass

    # deconflict remaining votes as object vs action
    ntxt = mtgl.re_vote_obj3.sub(r"xo<vote\1>",ntxt)

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
    elif op in ['less','fewer']: op = "op<{}>".format(mtgl.LE)
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
    try:
        pt1 = mtgltag.tag_attr(ch1)['val']
        pt2 = mtgltag.tag_attr(ch2)['val']
        return mtgltag.retag('ch','p/t',{'val':pt1 + mtgl.OR + pt2})
    except lts.LituusException:
        return m.group()

def _chain_check_(m):
    """
    checks first if chaining should be conducted otherwise return original txt
    :param m: regex.Match object
    :return: the chained object or the original text
    """
    vals = [mtgltag.tag_val(x) for x in m.groups() if x and mtgltag.is_tag(x)]
    if _skip_chain_(vals): return m.group()
    else: return _chain_(m)

def _chain_(m,strict=1):
    """
    chains a group of sequential tokens into one
    :param m: a regex.Match object
    :param strict: how to handle attribute merging (see mtgltag.merge_attributes)
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

    # extract the tags and operator #
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
                ptype = mtgltag.split_align(val)[0]
                if not atype: atype = ptype
                if atype != ptype: aligned = False

            # check for complex values and wrap in () present then append the
            # tag-value and merge the tag's attribute dict
            if mtgltag.conjunction_ops(val): val = mtgltag.wrap(val)
            nval.append(val)
            nattr = mtgltag.merge_attrs([attr,nattr],strict)
        except lts.LituusException:
            # should be the operator
            try:
                op = mtgl.conj_op[tkn]
            except KeyError:
                raise lts.LituusException(lts.EMTGL,"Illegal op {}".format(tkn))

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
    # TODO: is this really necessary?
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

    # if obj is a ref (primarily self) we want to create a new object and keep
    #  the ref object (see Wall of Corpses)
    tobj = None
    if obj:
        _,oval,oattr = mtgltag.untag(obj)
        if 'ref' in oattr:
            tobj = obj
            obj = None

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

    # put return value together and return it
    ret = mtgltag.retag(tid,val,attr)
    if tobj: ret += " " + tobj
    return ret

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

def _consecutive_obj_(m):
    """
    joins two consecutive objects these, the most common, nontoken permanent
    :param m:
    :return:
    """
    # unpack the objects
    tid1,val1,attr1 = mtgltag.untag(m.group(1))
    tid2,val2,attr2 = mtgltag.untag(m.group(2))

    if val1 == 'copy': # deconflict, copy here is an action
        return "{} {}".format(mtgltag.retag('xa',val1,attr1),m.group(2))
    elif val2 == 'copy': # only 1 card I found, copy is an action
        return "{} {}".format(m.group(1),mtgltag.retag('xa',val2,attr2))
    elif mtgltag.strip(val1) == 'token' and mtgltag.strip(val2) == 'permanent':
        # nontoken permanent - chain them
        return _chain_(m,0)
    elif mtgltag.strip(val1) == 'permanent' and mtgltag.strip(val2) in ['card','spell']:
        # align permanent under val2
        return mtgltag.retag(
            'ob',"{}→permanent".format(val2),mtgltag.merge_attrs([attr1,attr2])
        )

    # nothing found
    return m.group()

def _combat_status_chain_(m):
    """
    deconflicts and chains a conjunction of combat related statuses
    :param m: the regex.Match object
    :return: deconflicted and chained text
    """
    # pull out what we need
    op1 = m.group(2)
    op = mtgl.conj_op[m.group(4)] if m.group(4) else mtgl.AND
    op2 = m.group(5)

    # reappend suffixes
    op1 = 'tapped' if op1 == 'tap' else op1 +'ing'
    op2 = op2 + 'ing'

    # chain and retag
    return mtgltag.retag('xs',op1+op+op2,{})

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

def _align_n_(m):
    """
    aligns/chains two ore more consecutive types with/without a conjunction op
    :param m: a regex.Match object
    :return: the aligned/chained type
    """
    # TODO: what card did this safeguard against
    #  have to make sure that each non-operator type is not the same so we don't
    #  inadavertently combine "... creatures and creatures..."
    #vals = [mtgltag.tag_val(x) for x in m.groups() if x and mtgltag.is_tag(x)]
    #if len(set(vals)) == 1: return m.group()
    # have two make sure the conjunction is not part of two separate clauses i.e.
    # Elven Riders
    vals = [mtgltag.tag_val(x) for x in m.groups() if x and mtgltag.is_tag(x)]
    if _skip_chain_(vals): return m.group()

    # determine if we are chaining or aligning
    if m.group(2) in mtgl.conj_op: return _chain_(m)
    else:
        for val in vals:
            if mtgltag.complex_ops(val): return _chain_(m)
    return _align_type_(m)

def _skip_chain_(vals):
    """
    determines if the list of tags in ts should be not be chained
    :param vals: list of tag values to be chained
    :return: True if skip, False otherwise
    """
    # if each value has the same base type and at least one is not aligned we skip
    btype = mtgltag.base_type(vals[0])
    aligned = True
    for val in vals:
        if mtgltag.base_type(val) != btype: return False
        if not mtgltag.is_aligned(mtgltag.unwrap(val)): aligned = False
    return not aligned

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

def _obj_with_(m):
    """
    merges object and trailing 'with' clause
    :param m: the regex.match object
    :return: object merge with training 'with' clause
    """
    # untag the object & create the 'with' attribute
    tid,val,attr = mtgltag.untag(m.group(1))
    wattr = {'with':''.join(m.groups()[1:])}
    return mtgltag.retag(tid,val,mtgltag.merge_attrs([attr,wattr],0))

def _chain_obj_(m):
    """
    chains objects where applicable
    :param m: regex.Match object
    :return: chained spell(s) and ability(s)
    """
    # return values
    val = attr = None

    # only continue if it a simple TERM1 OP TERM2 conjunction
    if mtgltag.is_tag(m.group(2)) and mtgltag.is_tag(m.group(4)):
        # untag the two objects and grab the operator
        _,val1,attr1 = mtgltag.untag(m.group(2))
        _,val2,attr2 = mtgltag.untag(m.group(4))
        op = mtgl.conj_op[m.group(3)]

        if val1 in mtgl.objects and val2 in mtgl.objects:
            if mtgltag.vanilla(m.group(2)) and mtgltag.vanilla(m.group(4)):
                val = val1 + op + val2
                attr = mtgltag.merge_attrs([attr1,attr2])
            elif val1 == 'source' and val2 == 'source':
                val = 'source'
                attr = mtgltag.merge_attrs([attr1,attr2],0)
        elif val1 == 'spell' and val2 in ['ability','permanent']:
            tid = tid1
            val = val1 + op + val2
            attr = mtgltag.merge_attrs([attr1,attr2])

    if val: return mtgltag.retag('ob',val,attr)
    else: return m.group()

def _chain_ctr_(m):
    """
    determines if m specifies a chain of counters and if so chains them otherwise
    returns the orginal text
    :param m: regex.Match object
    :return: the chained coutners
    """
    ntid = 'xo'
    nval = 'ctr'
    nattr = []
    op = mtgl.AND

    for tkn in [x for x in lexer.tokenize(m.group())[0] if x != ',']:
        try:
            # we have caught every chain with a tag-id of xo, if we find any
            # non-counter, return the original text
            _,val,attr = mtgltag.untag(tkn)
            if val != 'ctr': return m.group()
            nattr.append(attr)
        except lts.LituusException:
            # should be the operator
            try:
                op = mtgl.conj_op[tkn]
            except KeyError:
                raise lts.LituusException(lts.EMTGL,"Illegal op {}".format(tkn))

    # unlike other chains, here we are chaining the 'type' in the attribute dict
    # merge_attr will automatically and the ctrs,replace with the right op
    attr = mtgltag.merge_attrs(nattr,0)
    attr['type'] = attr['type'].replace(mtgl.AND,op)

    # & return it
    return mtgltag.retag('xo','ctr',attr)

def _cost_type_(m):
    """
    merge cost type and cost
    :param m: the regex.Match object
    :return: cost type is moved to cost attribute
    """
    # untag the cost tag and insert the cost type as a new attribute
    tid,val,attr = mtgltag.untag(m.group(2))
    attr['type'] = mtgltag.tag_val(m.group(1))
    return mtgltag.retag(tid,val,attr)

def _join_suffix_(m):
    """
    merge the stem with the suffix
    :param m: the regex.Match object
    :return: joined suffix and stem
    """
    # TODO: needs to handle all anamolies, not just stems ending with 'p'
    tid,stem,suffix = m.groups()
    if stem == 'monstrosity': joined = "monstrous"
    elif stem.endswith('p') and suffix in ['ed','ing']: joined = stem+'p'+suffix
    elif stem.endswith('e') and suffix in ['ed','ing']: joined = stem[:-1]+suffix
    elif stem.endswith('y') and suffix in ['ed','ing']: joined = stem[:-1]+'i'+suffix
    else: joined = stem+suffix
    return "{}<{}>".format(tid,joined)

def _join_ability_(m):
    """
    merges ability type with ability i.e. activated ability
    :param m: the regex.Match object
    :return: abilty with type attribute
    """
    atype = m.group(1)
    if not atype: atype = 'bands-with-other'
    tid,val,attr = mtgltag.untag(m.group(3))
    attr['type'] = atype
    return mtgltag.retag(tid,val,attr)

def _prefixed_act_word_(m):
    """
     merges prefix with action word as a hyphenated value
    :param m: the regex.Match object
    :return: merged prefix and action word tag
    """
    pw,neg,aw = m.groups()
    pval = mtgltag.tag_val(pw)
    tid,val,attr = mtgltag.untag(aw)
    if pval == 'is' or pval == 'be': attr['prefix'] = 'to-be'
    else: attr['prefix'] = pval

    # prepend cn<not> if present
    ret = mtgltag.retag(tid,val,attr)
    if neg: ret = neg + ' ' + ret
    return ret

def _tag_vote_candidate_(c):
    """
     given candidate c returns the tag xo<vote candidate=c1> where c1 is is
     untagged as necessary
    :param c:
    :return:
    """
    candidate = c
    if mtgltag.tkn_type(c) == mtgltag.MTGL_TAG:
        tid,val,attr = mtgltag.untag(c)
        if 'suffix' in attr: val += attr['suffix'] # TODO: use _join_suffix_ like fct
        candidate = val
    return mtgltag.retag('xo','vote',{'candidate':candidate})

def _loot_num_(tkn):
    if tkn == 'xq<a>': return 1
    else: return mtgltag.tag_val(tkn)