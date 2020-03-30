#!/usr/bin/env python
""" mtgltag.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines functions to work with mtgl tags
"""

#__name__ = 'mtgltag'
__license__ = 'GPLv3'
__version__ = '0.1.0'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
import lituus.mtgl.mtgl as mtgl

"""
 Mana symbols (energy, tap and untap) are already enclosed by braces '{' and '}', 
 continue this concept using '<' and '>' to tag important words. All text is 
 lowered  cased. Then special words as defined in the Magic: The Gathering 
 Comprehensive Rules (3-May 2019) are tagged in addition to words that are common 
 throughout mtg card oracles. 
 
 Each tag is a two letter identifier followed by a '<', the word and a '>' 
 Identifiers beggining with 'x', specifies words that lituus treats as special or 
 common enough to warrant being tagged
"""

#### MTG SYMBOLS

# match mtg symbol string - one or more symbols of the form: {X}
re_mtg_sym = re.compile(r"^(\{[0-9wubrgscpxtqe\/]+\})+$",flags=re.M|re.I)

# match 1 mana symbol
re_mtg_ms = re.compile(r"{([0-9wubrgscpx\/]+)}",flags=re.I)

# match a mana string i.e. 1 or more mana symbols and nothing else
re_mtg_mstring = re.compile(r"^({([0-9wubrgscpx\/]+)})+$",flags=re.M|re.I)

# match phryexian mana
re_mtg_phy_ms = re.compile(r"{[wubrg]\/p}",flags=re.I)

# match a mana tag xo<mana> with or without the num attribute where values
# can be digits or one of the three variable designators (also allows for
# one operator preceding the digit(s))
# TODO: doesn't take into account mana 'objects' with other parameters
re_mana_tag = re.compile(r"xo<mana( num=(≥?\d+|[xyz]))?>")

# match a planeswalker loyalty cost
# Note this will also match:
#  a. invalid tokens with multiple x's i.e. nu<xxx>
#  b. it will match p/t i.e nu<1>/nu<1>
#  c. it will match singleton numbers i.e. 'where', 'nu<x>', 'is'
# also Note:
#  the negative is not a minus sign or long hyphen it is unicode 2212. Not sure
#  if this is just mtgjson's format or not
re_loy_cost = re.compile(r"[\+−]?nu<[\d|x]+>")

#### TAGS

# extract components of a tag (excluding all prop-values)
# TODO: scrub these i.e. will the EQ sign be found in a tag vaule?
re_tag = re.compile(
    r"(\w\w)"                       # 2 char tag-id       
    r"<"                            # opening bracket
    r"(¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡']+?)"    # tag value (w/ optional starting not)
    r"(\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*" # 0 or more prop lists delimited by space
    r">"                            # closing bracket
)

# extract the property and the property values
re_tag_props = re.compile(
    r"(\w+="                 # alphanumeric property and =
    r"[\w\+/\-¬∧∨⊕⋖⋗≤≥≡]+)" # prop-value
    r"[\s>]"                 # followed by space or closing bracket
)

MTGL_TAG = 0 # tag
MTGL_SYM = 1 # mtg symbol
MTGL_WRD = 2 # a word
MTGL_PUN = 3 # a punctutation
def tkn_type(tkn):
    """
     returns the type of token
    :param tkn: token to check
    :return: one of {0=tag,1=mtg symbol,2=word,3=punctuation}
    """
    if is_tag(tkn): return MTGL_TAG
    if is_mtg_symbol(tkn): return MTGL_SYM
    if tkn in [':',mtgl.CMA,mtgl.PER,mtgl.DBL,mtgl.SNG,mtgl.BLT,mtgl.HYP]:
        return MTGL_PUN
    return MTGL_WRD

# match a mtg symbol
def is_mtg_symbol(tkn): return re_mtg_sym.match(tkn) is not None

# match a mtg mana string
def is_mana_string(tkn): return re_mtg_mstring.match(tkn) is not None

# match a generic mana tag
def is_mana(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'xo' and v == 'mana'
    except mtgl.MTGLTagException:
        return False

def is_tag(tkn):
    try:
        _ = untag(tkn)
        return True
    except mtgl.MTGLTagException:
        return False

def untag(tkn):
    """
     returns the tag and value of tkn if it is a tagged item
    :param tkn: the token to untag
    :return: the tag, tag-value and property dict
    """
    props = {}
    try:
        # get the tag, the value and any properties
        tag,val,ps = re_tag.match(tkn).groups()
        if ps:
            props = {
                p[0]:p[1] for p in [p.split('=') for p in re_tag_props.findall(tkn)]
            }
        return tag,val,props
    except AttributeError:
        raise mtgl.MTGLTagException(tkn)

def merge_props(props,strict=True):
    """
     merges the proplists in props. if strict is True confirms all proplists have
     the same key->value pairs, otherwise adds unique key->value pairs and 'ands'
     differing values
    :param props: list of proplists
    :param strict: oneof {True, False}
    :return: merged proplist
    """
    ps = {}
    keys = list(set.union(*map(set,[x.keys() for x in props])))
    for key in keys:
        vals = set()
        for prop in props:
            if strict:
                try:
                    vals.add(prop[key])
                except KeyError:
                    raise mtgl.MTGLTagException("KeyError {}".format(key))
            else:
                pass
        if strict:
            if len(vals) == 1: ps[key] = vals.pop()
            else: raise mtgl.MTGLTagException("Incompatible properties {}".format(key))
        else:
            pass
    return ps

re_hanging = re.compile(r"(\s)>") # find hanging spaces before ending angle brace
def retag(tag,val,ps):
    """
     builds a tag from tag name, tag-value and property dict
    :param tag: two character tag name
    :param val: the tag value
    :param ps: dict of key=property,value=prop-value
    :return: the built tag
    """
    return re_hanging.sub(
        '>',"{}<{} {}>".format(tag,val," ".join(["=".join([p,ps[p]]) for p in ps]))
    )

def same_tag(tkns):
    tid = None
    for tkn in tkns:
        t = mtgl.untag(tkn)[0]
        if not tid: tid = t
        elif t != tid: return False
    return True

def is_tgr_word(tkn):
    try:
        return untag(tkn)[0] == 'mt'
    except mtgl.MTGLTagException:
        return False

def is_quality(tkn):
    try:
        if is_mtg_char(tkn): return True
        elif is_mtg_obj(tkn) and 'characteristics' in untag(tkn)[2]: return True
        else: return False
    except mtgl.MTGLTagException:
        return False

# things are mtg objects, lituus objects, players, effects/events and zones
def is_thing(tkn):
    try:
        return untag(tkn)[0] in ['ef','ob','xp','xo','zn']
    except mtgl.MTGLTagException:
        return False

def is_mtg_obj(tkn):
    try:
        return untag(tkn)[0] == 'ob'
    except mtgl.MTGLTagException:
        return False

def is_lituus_obj(tkn):
    try:
        return untag(tkn)[0] == 'xo'
    except mtgl.MTGLTagException:
        return False

# an object is a mtg object or a lituus object
def is_object(tkn):
    try:
        return untag(tkn)[0] in ['ob','xo']
    except mtgl.MTGLTagException:
        return False

def is_player(tkn):
    try:
        return untag(tkn)[0] == 'xp'
    except mtgl.MTGLTagException:
        return False

def is_zone(tkn):
    try:
        return untag(tkn)[0] == 'zn'
    except mtgl.MTGLTagException:
        return False

def is_phase(tkn):
    try:
        return untag(tkn)[0] == 'ph'
    except mtgl.MTGLTagException:
        return False

def is_event(tkn):
    try:
        return untag(tkn)[0] == 'ef'
    except mtgl.MTGLTagException:
        return False

def is_property(tkn):
    try:
        return untag(tkn)[0] in ['ch','xc']
    except mtgl.MTGLTagException:
        return False

def is_mtg_char(tkn):
    try:
        return untag(tkn)[0] == 'ch'
    except mtgl.MTGLTagException:
        return False

def is_meta_char(tkn):
    try:
        val = untag(tkn)[1]
    except mtgl.MTGLTagException:
        return False

    if mtgl.OR in val: val = val.split(mtgl.OR)
    elif mtgl.AND in val: val = val.split(mtgl.AND)
    else: val = [val]
    for v in val:
        if v.replace('_',' ') not in mtgl.meta_characteristics: return False
    return True

def is_lituus_char(tkn):
    try:
        return untag(tkn)[0] == 'xc'
    except mtgl.MTGLTagException:
        return False

def is_action(tkn):
    try:
        return untag(tkn)[0] in ['ka','xa']
    except mtgl.MTGLTagException:
        return False

def is_mtg_act(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except mtgl.MTGLTagException:
        return False

def is_lituus_act(tkn):
    try:
        return untag(tkn)[0] == 'xa'
    except mtgl.MTGLTagException:
        return False

def is_state(tkn):
    try:
        return untag(tkn)[0] in ['st','xs']
    except mtgl.MTGLTagException:
        return False

def is_quantifier(tkn):
    try:
        return untag(tkn)[0] == 'xq'
    except mtgl.MTGLTagException:
        return False

def is_sequence(tkn):
    try:
        return untag(tkn)[0] == 'sq'
    except mtgl.MTGLTagException:
        return False

def is_preposition(tkn):
    try:
        return untag(tkn)[0] == 'pr'
    except mtgl.MTGLTagException:
        return False

def is_conditional(tkn):
    try:
        return untag(tkn)[0] == 'cn'
    except mtgl.MTGLTagException:
        return False

def is_number(tkn):
    try:
        return untag(tkn)[0] == 'nu'
    except mtgl.MTGLTagException:
        return False

def is_variable(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'nu' and v in ['x','y','z']
    except mtgl.MTGLTagException:
        return False

def is_expression(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'nu' and v in [mtgl.LT,mtgl.GT,mtgl.LE,mtgl.GE,mtgl.EQ]
    except mtgl.MTGLTagException:
        return False

def is_operator(tkn):
    try:
        return untag(tkn)[0] == 'op'
    except mtgl.MTGLTagException:
        return False

def is_keyword(tkn):
    try:
        return untag(tkn)[0] == 'kw'
    except mtgl.MTGLTagException:
        return False

def is_keyword_action(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except mtgl.MTGLTagException:
        return False

def is_ability_word(tkn):
    try:
        return untag(tkn)[0] == 'aw'
    except mtgl.MTGLTagException:
        return False

def is_loyalty_cost(tkn):
    try:
        # find a match (if any) and check the endpos, if its greater than the
        # the end of the matching span, there's more to the token
        m = re_loy_cost.match(tkn)
        return m.end() == m.endpos
    except AttributeError:
        pass
    return False

def is_coordinator(tkn):
    if tkn in ['and','or','op<⊕>']: return True
    return False