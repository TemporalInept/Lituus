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
__version__ = '0.1.4'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
import lituus as lts
import lituus.mtgl.mtgl as mtgl

"""
 Mana symbols (energy, tap and untap) are already enclosed by braces '{' and '}', 
 continue this concept using '<' and '>' to tag important words. All text is 
 lowered  cased. Then special words as defined in the Magic: The Gathering 
 Comprehensive Rules are tagged in addition to words that are common throughout 
 mtg card oracles. 
 
 Each tag can is defined as (see re_tag below): 
  tag-id<tag-value[ tag-attributes]>
 where 
  tag-id is a two letter identifier (see mtgl) that defines the type of tag
   i.e. kw defines a keyword
  tag-value is the 'word' or token being tagged i.e. 'flying'
  tag-attributes is a list of space delimited attribute pairs attr=val 
"""

#### MTG SYMBOLS
# TODO: do we really need the re.I flag
# match mtg symbol string - one or more symbols of the form: {X}
re_mtg_sym = re.compile(r"^({[0-9wubrgscpxytqe\/]+})+$",flags=re.M|re.I)

# match 1 mana symbol
re_mtg_ms = re.compile(r"{([0-9wubrgscpxyz\/]+)}",flags=re.I)

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
# TODO: scrub this
re_tag = re.compile(
    r"(\w\w)"                             # 2 char tag-id       
    r"<"                                  # opening bracket
    r"(¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→¬→'\(\)]+?)"  # tag value (w/ optional starting not)
    r"( [\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)*"  # 0 or more attributes delimited by space
    r">"                                  # closing bracket
)

# extract the attribute pairs
re_tag_attrs = re.compile(
    r"(\w+="                        # alphanumeric property and =
    r"[\w\+/\-¬∧∨⊕⋖⋗≤≥≡→'\(\)]+)" # prop-value
    r"[ >]"                         # followed by space or closing bracket
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
    except lts.LituusException:
        return False

####
## TAG RELATED
####

def is_tag(tkn):
    try:
        _ = untag(tkn)
        return True
    except lts.LituusException:
        return False

def untag(tkn):
    """
     returns the tag-id, tag value and attribute dict of tkn if it is a tagged item
    :param tkn: the token to untag
    :return: the tag, tag-value and property dict
    """
    attrs = {}
    try:
        # get the tag, the value and any properties
        tag,val,attr = re_tag.match(tkn).groups()
        if attr:
            attrs = {
                p[0]:p[1] for p in [p.split('=') for p in re_tag_attrs.findall(tkn)]
            }
        return tag,val,attrs
    except AttributeError: # signifies a None returned from re_tag
        raise lts.LituusException(lts.ETAG,"Invalid tag {}".format(tkn))

re_hanging = re.compile(r"(\s)>") # find hanging spaces before ending angle brace
def retag(tag,val,attrs):
    """
     builds a tag from tag name, tag-value and attribute list
    :param tag: two character tag name
    :param val: the tag value
    :param attrs: dict of key=property,value=prop-value
    :return: the built tag
    """
    return re_hanging.sub(
        '>',"{}<{} {}>".format(
            tag,val," ".join(["=".join([a,attrs[a]]) for a in attrs])
        )
    )

# TAG COMPONENTS

def tag_id(tag): return untag(tag)[0]

def tag_val(tag): return untag(tag)[1]

def tag_attr(tag): return untag(tag)[2]

# TAG VALUES

def operand(val,op=False):
    """
    splits the parameter tkn in operands and operators
    :param tkn: the paramater value
    :param op: if true returns operators as well
    :return: list of parameter operands (operators if specified)
    """
    # TODO: why is '' returned
    if op: return [x for x in mtgl.re_param_delim_wop.split(val) if x != '']
    else: return [x for x in mtgl.re_param_delim_nop.split(val) if x != '']

# infix to postfix of complex value expressions
exp_ops = [mtgl.ARW,mtgl.AND,mtgl.OR,mtgl.AOR,]
_OPP_ = {
    mtgl.NOT:4, mtgl.ADD:4, mtgl.SUB:4, # prefix
    mtgl.ARW:3,                         # align
    mtgl.AND:2, mtgl.OR:2, mtgl.AOR:2,  # conjunction
    '(':1
}
def _precedence_(op1,op2): return _OPP_[op1] <= _OPP_[op2]
def postfix(val):
    """ convert the infix expression of val to postfix """
    p = []
    s = []
    for tkn in operand(val,True):
        if tkn == '(': s.append(tkn)
        elif tkn == ')':
            while(s and s[-1] != '('): p.append(s.pop())
            if s and s[-1] == '(': s.pop()
        elif tkn in exp_ops:
            while(s and _precedence_(tkn,s[-1])): p.append(s.pop())
            s.append(tkn)
        else: p.append(tkn)
    while(s): p.append(s.pop())
    return p

def strip(val):
    """
    removes prefix operators from the value i.e. negate, plus, minus
    :param val: the value
    :return: the unadorned value
    """
    if val[0] in ["+","-",mtgl.NOT]: return val[1:]
    else: return val

re_complex_op = re.compile(r"[∧∨⊕→]")
def complex_ops(tkn):
    """
    returns a list of complex operators in the value tkn
    :param tkn: value to check
    :return: list of complex operators
    """
    return re_complex_op.findall(tkn)

re_conj_op = re.compile(r"[∧∨⊕]")
def conjunction_ops(tkn):
    """
    returns a list of conjunction operators in the value tkn
    :param tkn: value to check
    :return: list of conjunction operators
    """
    return re_conj_op.findall(tkn)

re_paren = re.compile(r"[\(\)]")
def is_wrapped(tkn):
    """
    determines if tkn is wrapped by paranethesis
    :param tkn: tkn to check
    :return: True if tkn is wrapped
    """
    return re_paren.search(tkn) is not None

def wrap(tkn):
    """
    encapsulates the tkn in parenthesis
    :param tkn: tkn to wrap
    :return: the wrapped token
    """
    return '('+tkn+')'

def unwrap(val):
    """
    removes OUTER parenthesis from tkn NOTE: only removes the outer paranethesis
    does not remove any internal
    :param val: value to uwrap
    :return: unwrapped token
    """
    if val.startswith('(') and val.endswith(')'): return val[1:-1]
    else: return val

def is_aligned(val):
    """
    determines if val is aligned. NOTE: only checks if there is a top level
    alignment. For example will return True for creature->artifact but False
    for creature&artifact->equipment since the top level operator is an 'and'
    :param val: value to check
    :return: returns True if val is aligned
    """
    # if value is converted to postfix and the last item in the postfix exp. is
    # an alignment, we have a top level alignment
    if postfix(val)[-1] == mtgl.ARW: return True
    else: return False

def split_align(val):
    """
    splits val on alignment operator. See above, will only split the top-level
    alignment if it exists
    :param val: value to split
    :return: aligned-type,aligned-characteristics
    """
    if not is_aligned(val): return val,''
    else:
        # once confirmed as a top-level alignment, the first alignment operator
        # is the one to split on. everything to the left is the aligned type &
        # everything to the right is the aligned characteristics
        exp = operand(val,True)
        i = exp.index(mtgl.ARW)
        atype = ''.join(exp[:i])
        aval = ''.join(exp[i+1:])
        return atype,aval

def merge_attrs(attrs,strict=1):
    """
     merges the attributes lists in attrs based on specified strictness level.
     if strict is True confirms all proplists have
     the same key->value pairs, otherwise adds unique key->value pairs and 'ands'
     differing values
    :param attrs: list of attribute lists
    :param strict: oneof:
      0 = LOW no checking on sameness across parameters/parameter values
      1 = MEDIUM parameter values across common parameters must be the same but
       parameters are not required to be shared across all attribute dicts
      2 = HIGH parameters and parameter values must be the same in each prop list
    :return: merged attribute dicts
    """
    if not attrs: return {} # don't bother if the list is empty
    mattrs = {}
    keys = list(set.union(*map(set,[attr.keys() for attr in attrs])))
    for key in keys:
        vals = set()

        # check each paraemter for existence if high strictness
        for attr in attrs:
            if not key in attr:
                if strict == 2:
                    raise lts.LituusException(
                        lts.ETAG,"Incompatible attribute {}".format(key)
                    )
            else: vals.add(attr[key])

        # check for same attribute values if strictness is not low
        if strict > 0 and len(vals) > 1:
            raise lts.LituusException(
                lts.ETAG, "Incompatible attribute values {}".format(key)
            )
        mattrs[key] = mtgl.AND.join([val for val in vals])
    return mattrs

def is_tgr_word(tkn):
    try:
        return untag(tkn)[0] == 'mt'
    except lts.LitussException:
        return False

def is_quality(tkn):
    try:
        if is_mtg_char(tkn): return True
        elif is_mtg_obj(tkn) and 'characteristics' in untag(tkn)[2]: return True
        else: return False
    except lts.LitussException:
        return False

# things are mtg objects, lituus objects, players, effects/events and zones
def is_thing(tkn):
    try:
        return untag(tkn)[0] in ['ef','ob','xp','xo','zn']
    except lts.LitussException:
        return False

def is_mtg_obj(tkn):
    try:
        return untag(tkn)[0] == 'ob'
    except lts.LitussException:
        return False

def is_lituus_obj(tkn):
    try:
        return untag(tkn)[0] == 'xo'
    except lts.LitussException:
        return False

# an object is a mtg object or a lituus object
def is_object(tkn):
    try:
        return untag(tkn)[0] in ['ob','xo']
    except lts.LitussException:
        return False

def is_player(tkn):
    try:
        return untag(tkn)[0] == 'xp'
    except lts.LitussException:
        return False

def is_zone(tkn):
    try:
        return untag(tkn)[0] == 'zn'
    except lts.LitussException:
        return False

def is_phase(tkn):
    try:
        return untag(tkn)[0] == 'ph'
    except lts.LitussException:
        return False

def is_event(tkn):
    try:
        return untag(tkn)[0] == 'ef'
    except lts.LitussException:
        return False

def is_property(tkn):
    try:
        return untag(tkn)[0] in ['ch','xc']
    except lts.LitussException:
        return False

def is_mtg_char(tkn):
    try:
        return untag(tkn)[0] == 'ch'
    except lts.LitussException:
        return False

def is_meta_char(tkn):
    try:
        val = untag(tkn)[1]
    except lts.LitussException:
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
    except lts.LitussException:
        return False

def is_action(tkn):
    try:
        return untag(tkn)[0] in ['ka','xa']
    except lts.LitussException:
        return False

def is_mtg_act(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except lts.LitussException:
        return False

def is_lituus_act(tkn):
    try:
        return untag(tkn)[0] == 'xa'
    except lts.LitussException:
        return False

def is_state(tkn):
    try:
        return untag(tkn)[0] in ['st','xs']
    except lts.LitussException:
        return False

def is_quantifier(tkn):
    try:
        return untag(tkn)[0] == 'xq'
    except lts.LitussException:
        return False

def is_sequence(tkn):
    try:
        return untag(tkn)[0] == 'sq'
    except lts.LitussException:
        return False

def is_preposition(tkn):
    try:
        return untag(tkn)[0] == 'pr'
    except lts.LitussException:
        return False

def is_conditional(tkn):
    try:
        return untag(tkn)[0] == 'cn'
    except lts.LitussException:
        return False

def is_number(tkn):
    try:
        return untag(tkn)[0] == 'nu'
    except lts.LitussException:
        return False

def is_variable(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'nu' and v in ['x','y','z']
    except lts.LitussException:
        return False

def is_expression(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'nu' and v in [mtgl.LT,mtgl.GT,mtgl.LE,mtgl.GE,mtgl.EQ]
    except lts.LitussException:
        return False

def is_operator(tkn):
    try:
        return untag(tkn)[0] == 'op'
    except lts.LitussException:
        return False

def is_keyword(tkn):
    try:
        return untag(tkn)[0] == 'kw'
    except lts.LitussException:
        return False

def is_keyword_action(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except lts.LitussException:
        return False

def is_ability_word(tkn):
    try:
        return untag(tkn)[0] == 'aw'
    except lts.LitussException:
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