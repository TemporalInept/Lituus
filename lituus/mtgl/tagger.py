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
    #ntxt = first_pass(ntxt)
    #return postprocess(ntxt)
    return ntxt

#### PREPROCESSING ####

def preprocess(name,txt):
    """
     conducts an initial scrub of the oracle text. Then:
       1. replaces card name references with ref-id or self as necessary
       2. lowercases oracle text
       3. standarizes some common phrases
         (MOVE THIS) a. shuffle your library clause - will now read ", then shuffle your
          library" rather as a seperate sentence
         (???) b. "command zone" - "zone" is implied replaced with "command" only
         c. "your opponent(s)" - "your" is implied, replaced with "opponent(s)" only
       (STOP) 4. possessive "'s" removed
       5. english number words for 0 through 10 are replacing with corresponding ints,
       6. contractions are replaced with full words
       7. common phrases replaced by acronyms
       (HANDLED ABOVE ???) 8. pluralities i.e. 'y' to 'ies' hacked to read 'ys'
       (STOP) 9. action word pluralities replaced with singular form
      10. Some reminder text is removed, some paraenthesis is removed
      11. take care of keywords that are exemptions to keyword rules
    :param name: name of this card
    :param txt: the mtgl text
    :return: preprocessed oracle text
    """
    # a keyword
    ntxt = tag_ref(name,txt).lower()
    ntxt = pre_special_keywords(ntxt)
    ntxt = standarize(ntxt)
    ntxt = mtgl.re_wd2int.sub(lambda m: mtgl.E2I[m.group(1)],ntxt)
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
    # replace references to self by name and 'this spell', 'this permanent',
    # 'this card', 'his', 'her' (planeswalkers)
    ntxt = mtgl.re_self_ref(name).sub(r"ob<card ref=self>",txt)

    # token names like Etherium Cell which do not have a non-token representation
    # in the multiverse & includes copy tokens (https://mtg.gamepedia.com/Token/Full_List)
    # these are prefixed with 'create' and possibly 'named'
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
    # TODO: this will not catch cases where there is an and i.e. Throne of Empires
    #  "... named Crown of Empires and Scepter of Empires. For now, have to hack
    #  it using mtgl.re_oth_ref2
    assert(mtgl.re_oth_ref is not None)
    ntxt = mtgl.re_oth_ref.sub(
        lambda m: r"{} ob<card ref={}>".format(m.group(1),mtgl.N2R[m.group(2)]),ntxt
    )

    # references to other cards we know a priori
    return mtgl.re_oth_ref2.sub(
        lambda m: r"ob<token ref={}>".format(mtgl.NC2R[m.group(1)]),ntxt
    )
