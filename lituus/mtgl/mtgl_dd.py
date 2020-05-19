#!/usr/bin/env python
""" mtgl_dd.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines a data dictionary (ala "templates") for mtg oracle text
"""

#__name__ = 'mtgl_dd'
__license__ = 'GPLv3'
__version__ = '0.0.1'
__date__ = 'May 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re

####
## LINE TYPES
####

# Ability word lines start with an ability word followed by a long hypen and then
# the ability clause and end with a sentence
re_aw_line = re.compile(r"^(aw<[\w-]+>) —")

# Keyword lines start with a keyword (or object keyword if landwalk) and contain
# one or more comma separated keyword claues
re_kw_line = re.compile(
    r"^"
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*> )?"
    r"(kw<[\w-]+>)"
)

# a non-standard keyword line will contain a long hypen and end with a period
# between the hypen and period is the non-standard cost i.e. Aboroth
re_kw_line_ns = re.compile(r"^(kw<[\w-]+>)—(.+?)\.$")

# Ability lines (113.3) are not keyword lines or ability word lines. There are
# four subtypes:
#  113.3a Spell - an instant or sorcery
#  113.3b Activated - of the form cost : effect
#  113.3c Triggered - of the form TRIGGER
#  113.3d static - none of the above

# Activated (112.3b) contain a ':' which splits the cost and effect
re_activated_line = re.compile(r":")

# Triggered (112.3c) lines starts with a trigger preamble
re_triggered_line = re.compile(r"^(tp<\w+>)")

####
## KEYWORDS
####

#### KEYWORD ABILITIES (702)

# A keyword line is one or more comma separated keyword clauses where a keyword
# clause is defined:
#  [QUALITY] KEYWORD KEYWORD_TEXT
# Use findall to grab tuples of keyword clauses where t = (QUALITY,KEYWORD,TEXT)
# NOTE: some keywords have commas in their parameters - have to make sure we
#  split the clauses only if the comma is followed by another keyword
re_kw_clause = re.compile(
    r"((?:xr|ob)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)? ?"
    r"kw<([\w-]+)>"
    r"(?: ?(.*?))"
    r"(?=(?:$|\.$|, (?:kw|ob)))"
)

## KEYWORD ABILITY PARAMETER PARSING
# NOTE: when possible, generic patterns will be used as most keywords follow
#  one of several formats i.e. KEYWORD COST. When necessary, such as equip
#  a specific pattern for that keyword will be used

# no parameters
re_kw_empty = re.compile('')

# kewords of the form KEYWORD THING
re_kw_thing = re.compile(
    r"((?:ob|xp|xo)"
    r"<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)"
)

# 702.6 Equip ([quality])? [cost]
# TODO: make this keyword_cost
re_kw_equip = re.compile(
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)? ?"
    r"({[0-9wubrgscpx\/]+})+"
)

# keywords of the form KEWYWORD (from [quality])? i.e. protection, hexproof
# quality is an object or a color
#  TODO: 702.11f mentions Hexproof from [quality A] and from [quality B] but
#   have not seen a card with this phrasing
# these have multiple forms:
#  1. from quality
#  2. from quality a and from quality b
#  3. from quality a, from quality b and from quality c
# NOTE: due to using this with Hexproof which may not have any qualities, all
#  three qualities are captured as optional
re_kw_from_qual = re.compile(
    r"(?:pr<from> "
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>))?"
    r"(?:, pr<from> "
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>))?"
    r"(?:,? and pr<from> "
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>))?"
)

# keywords of the form KEYWORD N
re_kw_n = re.compile(r"nu<(\d+|x|y|z])>")

# keywords of the form KEYWORD [cost]
# TODO: these may be non-standard i.e. non-mana costs
re_kw_cost = re.compile(
    r"((?:{[0-9wubrgscpx\/]+})+)"
)

# same as above but adds an additional optional cost preceded by 'and/or'
# seen in some kicker keyword lines
re_kw_cost2 = re.compile(
    r"((?:{[0-9wubrgscpx\/]+})+)"
    r"(?: and/or ((?:{[0-9wubrgscpx\/]+})+))?"
)

## KEYWORD ABILITY PARAMETER TEMPLATES
# NOTE: for banding, 702.21b specifies "bands with other", this phrase is not
#  found in keyword lines but is granted by one of a few cards (Catherdal of Serra)
kw_param = {
    'deathtouch':re_kw_empty,      # 702.2
    'defender':re_kw_empty,        # 702.3
    'double_strike':re_kw_empty,   # 702.4
    'enchant':re_kw_thing,         # 702.5
    'equip':re_kw_equip,           # 702.6
    'first_strike':re_kw_empty,    # 702.7
    'flash':re_kw_empty,           # 702.8
    'flying':re_kw_empty,          # 702.9
    'haste':re_kw_empty,           # 702.10
    'hexproof':re_kw_from_qual,    # 702.11
    'indestructible':re_kw_empty,  # 702.12
    'intimidate':re_kw_empty,      # 702.13
    'landwalk':re_kw_empty,        # 702.14
    'lifelink':re_kw_empty,        # 702.15
    'protection':re_kw_from_qual,  # 702.16
    'reach':re_kw_empty,           # 702.17
    'shroud':re_kw_empty,          # 702.18
    'trample':re_kw_empty,         # 702.19
    'vigilance':re_kw_empty,       # 702.20
    'banding':re_kw_empty,         # 702.21
    'rampage':re_kw_n,             # 702.22
    'cumlative_upkeep':re_kw_cost, # 702.23
    'flanking':re_kw_empty,        # 702.24
    'phasing':re_kw_empty,         # 702.25
    'buyback':re_kw_cost,          # 702.26
    'shadow':re_kw_empty,          # 702.27
    'cycling':re_kw_cost,          # 702.28
    'echo':re_kw_cost,             # 702.29
    'horsemanship':re_kw_empty,    # 702.30
    'fading':re_kw_n,              # 702.31
    'kicker':re_kw_cost2,          # 702.32
    'multikicker':re_kw_cost2,     # 702.32c
    'flashback':re_kw_cost,        # 702.33
    'madness':re_kw_cost,          # 702.34
    'fear':re_kw_empty,            # 702.35
    'morph':re_kw_cost,            # 702.36,
    'megamorph':re_kw_cost,        # 702.36b
    'amplify':re_kw_n,             # 702.37
    'provoke':re_kw_empty,        # 702.38
    'storm':re_kw_empty,          # 702.39
    'affinity':None,              # 702.40
    'entwine':None,               # 702.41
    'modular':None,               # 702.42
    'sunburst':re_kw_empty,       # 702.43
    'bushido':None,               # 702.44
    'soulshift':None,             # 702.45
    'splice':None,                # 702.46
    'offering':re_kw_empty,       # 702.47
    'ninjutsu':None,              # 702.48
    'epic':re_kw_empty,           # 702.49
    'convoke':re_kw_empty,        # 702.50
    'dredge':None,                # 702.51
    'transmute':None,             # 702.52
    'bloodthirst':None,           # 702.53
    'haunt':re_kw_empty,          # 702.54
    'replicate':None,             # 702.55
    'forecast':None,              # 702.56
    'graft':None,                 # 702.57
    'recover':None,               # 702.58
    'ripple':None,                # 702.59
    'split_second':re_kw_empty,   # 702.60
    'suspend':None,               # 702.61
    'vanishing':None,             # 702.62
    'absorb':None,                # 702.63
    'aura_swap':None,             # 702.64
    'delve':re_kw_empty,          # 702.65
    'fortify':None,               # 702.66
    'frenzy':None,                # 702.67
    'gravestorm':re_kw_empty,     # 702.68
    'poisonous':None,             # 702.69
    'transfigure':None,           # 702.70
    'champion':None,              # 702.71
    'evoke':None,                 # 702.73
    'hideaway':re_kw_empty,       # 702.74
    'prowl':None,                 # 702.75
    'reinforce':None, # 702.76
    'conspire':re_kw_empty, # 702.77
    'persist':re_kw_empty, # 702.78
    'wither':re_kw_empty, # 702.79
    'retrace':re_kw_empty, # 702.80
    'devour':None, # 702.81
    'exalted':re_kw_empty, # 702.82
    'unearth':None, # 702.83
    'cascade':re_kw_empty, # 702.84
    'annihilator':None, # 702.85
    'level_up':None, # 702.86
    'totem_armor':re_kw_empty, # 702.88
    'infect':re_kw_empty, # 702.89
    'battle_cry':re_kw_empty, # 702.90
    'living_weapon':re_kw_empty, # 702.91
    'undying':re_kw_empty, # 702.92
    'miracle':None, # 702.93
    'soulbond':re_kw_empty, # 702.94
    'overload':None, # 702.95
    'scavenge':None, # 702.96
    'unleash':re_kw_empty, # 702.97
    'cipher':re_kw_empty, # 702.98
    'evolve':re_kw_empty, # 702.99
    'extort':re_kw_empty, # 702.100
    'fuse':re_kw_empty, # 702.101
    'bestow':None, # 702.102
    'tribute':None, # 702.103
    'dethrone':re_kw_empty, # 702.104
    #'hidden_agenda':re_kw_empty, # 702.105 (wont' see these)
    'outlasat':None, # 702.106
    'prowess':re_kw_empty, # 702.107
    'dash':None, # 702.108
    'exploit':re_kw_empty, # 702.109
    'menace':re_kw_empty, # 702.110
    'renown':None, # 702.111
    'awaken':None, # 702.112
    'devoid':re_kw_empty, # 702.113
    'ingest':re_kw_empty, # 702.114
    'myriad':re_kw_empty, # 702.115
    'surge':None, # 702.116
    'skulk':re_kw_empty, # 702.117
    'emerge':None, # 702.118
    'escalate':None, # 702.119
    'melee':re_kw_empty, # 702.120
    'crew':None, # 702.121
    'fabricate':None, # 702.122
    'partner':None, # 702.123
    #'partner_with':None # 702.123f not captured as such
    'undaunted':re_kw_empty, # 702.124
    'improvise':re_kw_empty, # 702.125
    'aftermath':re_kw_empty, # 702.126
    'embalm':None, # 702.127
    'eternalize':None, # 702.128
    'afflict':None, # 702.129
    'ascend':re_kw_empty, # 702.130
    'assist':re_kw_empty, # 702.131
    'jump-start':re_kw_empty, # 702.132
    'mentor':re_kw_empty, # 702.133
    'afterlife':None, # 702.134
    'riot':re_kw_empty, # 702.135
    'spectacle':None, # 702.136
    'escape':None, # 702.137
}

kw_param_template = {
    'enchant':('quality',),
    'equip':('quality','cost'),
    'hexproof':('quality','quality','quality'),
    'protection':('quality','quality','quality'),
    'rampage':('n',),
    'cumlative_upkeep':('cost',),
    'buyback':('cost',),
    'cycling':('cost',),
    'echo':('cost',),
    'fading':('n',),
    'kicker':('cost','cost'),
    'multikicker':('cost','cost'),
    'flashback':('cost',),
    'madness':('cost',),
    'morph':('cost',),
    'megamorph':('cost',),
    'amplify':('n',),
}