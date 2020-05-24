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
## MISCELLANEOUS
####

# use with split to break a line into sentences by the period. Grabs all
# characters upto and including the period
# TODO: anyway to not include the preceding space on subsequent sentences
re_sentence = re.compile(r"([^\.]+\.)")

####
## LINE TYPES
####

# Ability word lines start with an ability word followed by a long hypen and then
# the ability clause and end with a sentence
re_aw_line = re.compile(r"^aw<([\w-]+)> — (.+?)\.$")

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

# Activated (113.3b) contains a ':' which splits the cost and effect
re_act_check = re.compile(r":")
re_act_line = re.compile(r"^(.+?): (.+?)$")

# Triggered (603.1) lines starts with a trigger preamble
# Triggered abilities have the form:
#  [When/Whenever/At] [condition], [effect]. [Instructions]?
# NOTE: since we are basing our delimitation of the individual 'components',
#  have to build in checks for periods that are inclosed in double parenthesis
#  and single, double parenthesis (Reef Worm)
re_tgr_check = re.compile(r"^(tp<\w+>)")
re_tgr_line = re.compile(
    r"^tp<(at|whenever|when)> "
    r"(.+?), "
    r"([^\.]+)(?:\.|\.\"|\.\'\")"
    r"(?: (.+)(?:\.|\.\"|\.\'\"))?"
    r"$"
)

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

# generic parameters

# kewords of the form KEYWORD [optional word] [QUALITY]
# This covers generic keyword QUALITY but also matches
#  Affinity (702.40) Affinity for [QUALITY]
#  Champion (702.71) Champion a [QUALITY]
# keywords of the form KEYWORD for [quality] (affinity)
re_kw_thing = re.compile(
    r"(?:pr<for>|sq<an?>)? ?"
    r"((?:ob|xp|xo)"
    r"<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)"
)

# keywords of the form KEYWORD N
# first includes a non-standard n for the card Arcbound Wanderer
# second pattern is for Vanishing (706.62) one of which (Tidewalker) does not
# have a 'N'
# TODO: could just remove the fist pattern and use the optional 'N' but not
#  sure if I like that
re_kw_n = re.compile(r"(?:nu<(\d+|x|y|z])>|—(.+?)$)")
re_kw_n2 = re.compile(r"(?:nu<(\d+|x|y|z])>)?")

# keywords of the form KEYWORD [cost]
# This will capture cost where cost is a mana string or a non-standard cost
# mana costs will be in group 1 and non-standard will be in group 2
re_kw_cost = re.compile(r"(?:((?:{[0-9wubrgscpx\/]+})+)|—(.+?)$)")

# same as above but adds an additional optional cost preceded by 'and/or'
# seen in some kicker keyword lines
re_kw_cost2 = re.compile(
    r"(?:((?:{[0-9wubrgscpx\/]+})+)|—(.+?)$)"
    r"(?: and/or ((?:{[0-9wubrgscpx\/]+})+))?"
)

# special parameters for specific keywords

# 702.6 Equip ([quality])? [cost] cost may be nonstandard
re_kw_equip = re.compile(
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)? ?"
    r"(?:((?:{[0-9wubrgscpx\/]+})+)|—(.+?)$)"
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

# Partner (702.123) has no parameters but Partner with (702.123f) does
# Partner with [NAME]
re_kw_partner = re.compile(
    r"(?:pr<with> "
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)"
    r")?"
)

# splice (702.46) splice onto [quality] [cost]
# TODO: the trailing period is not passed as parmater on non-standard costs
# TODO: cannot get rid of the 'hidden group' in the cost portion
re_kw_splice = re.compile(
    r"pr<onto> "
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→'\('\)]+?)*>)"
    r"(?: ((?:{[0-9wubrgscpx\/]+})+)|—(.+?)$)"
)

# forecast (702.56) forecast — [actiavated ability]
re_kw_forecast = re.compile(r"— (.+?)$")

# suspend (702.61) suspend [N] — [cost] [optional inst]
re_kw_suspend = re.compile(
    r"nu<(\d+|x|y|z])>"
    r"—"
    r"((?:{[0-9wubrgscpx\/]+})+)"
    r"(?:\. (.+?)$)?"
)

## KEYWORD ABILITY PARAMETER TEMPLATES
# NOTE: for banding, 702.21b specifies "bands with other", this phrase is not
#  found in keyword lines but is granted by one of a few cards (Catherdal of Serra)
kw_param = {
    'deathtouch':re_kw_empty,        # 702.2
    'defender':re_kw_empty,          # 702.3
    'double_strike':re_kw_empty,     # 702.4
    'enchant':re_kw_thing,           # 702.5
    'equip':re_kw_equip,             # 702.6
    'first_strike':re_kw_empty,      # 702.7
    'flash':re_kw_empty,             # 702.8
    'flying':re_kw_empty,            # 702.9
    'haste':re_kw_empty,             # 702.10
    'hexproof':re_kw_from_qual,      # 702.11
    'indestructible':re_kw_empty,    # 702.12
    'intimidate':re_kw_empty,        # 702.13
    'landwalk':re_kw_empty,          # 702.14
    'lifelink':re_kw_empty,          # 702.15
    'protection':re_kw_from_qual,    # 702.16
    'reach':re_kw_empty,             # 702.17
    'shroud':re_kw_empty,            # 702.18
    'trample':re_kw_empty,           # 702.19
    'vigilance':re_kw_empty,         # 702.20
    'banding':re_kw_empty,           # 702.21
    'rampage':re_kw_n,               # 702.22
    'cumlative_upkeep':re_kw_cost,   # 702.23
    'flanking':re_kw_empty,          # 702.24
    'phasing':re_kw_empty,           # 702.25
    'buyback':re_kw_cost,            # 702.26
    'shadow':re_kw_empty,            # 702.27
    'cycling':re_kw_cost,            # 702.28
    'echo':re_kw_cost,               # 702.29
    'horsemanship':re_kw_empty,      # 702.30
    'fading':re_kw_n,                # 702.31
    'kicker':re_kw_cost2,            # 702.32
    'multikicker':re_kw_cost2,       # 702.32c
    'flashback':re_kw_cost,          # 702.33
    'madness':re_kw_cost,            # 702.34
    'fear':re_kw_empty,              # 702.35
    'morph':re_kw_cost,              # 702.36,
    'megamorph':re_kw_cost,          # 702.36b
    'amplify':re_kw_n,               # 702.37
    'provoke':re_kw_empty,           # 702.38
    'storm':re_kw_empty,             # 702.39
    'affinity':re_kw_thing,          # 702.40
    'entwine':re_kw_cost,            # 702.41
    'modular':re_kw_n,               # 702.42
    'sunburst':re_kw_empty,          # 702.43
    'bushido':re_kw_n,               # 702.44
    'soulshift':re_kw_n,             # 702.45
    'splice':re_kw_splice,           # 702.46
    'offering':re_kw_empty,          # 702.47
    'ninjutsu':re_kw_cost,           # 702.48
    'commander_ninjutsu':re_kw_cost, # 702.48
    'epic':re_kw_empty,              # 702.49
    'convoke':re_kw_empty,           # 702.50
    'dredge':re_kw_n,                # 702.51
    'transmute':re_kw_cost,          # 702.52
    'bloodthirst':re_kw_n,           # 702.53
    'haunt':re_kw_empty,             # 702.54
    'replicate':re_kw_cost,          # 702.55
    'forecast':re_kw_forecast,       # 702.56
    'graft':re_kw_n,                 # 702.57
    'recover':re_kw_cost,            # 702.58
    'ripple':re_kw_n,                # 702.59
    'split_second':re_kw_empty,      # 702.60
    'suspend':re_kw_suspend,         # 702.61
    'vanishing':re_kw_n2,            # 702.62
    'absorb':re_kw_n,                # 702.63
    'aura_swap':re_kw_cost,          # 702.64
    'delve':re_kw_empty,             # 702.65
    'fortify':re_kw_cost,            # 702.66
    'frenzy':re_kw_n,                # 702.67
    'gravestorm':re_kw_empty,        # 702.68
    'poisonous':re_kw_n,             # 702.69
    'transfigure':re_kw_cost,        # 702.70
    'champion':re_kw_thing,          # 702.71
    'changeling':re_kw_empty,        # 702.72
    'evoke':re_kw_cost,              # 702.73
    'hideaway':re_kw_empty,          # 702.74
    'prowl':re_kw_cost,              # 702.75
    'reinforce':re_kw_n,             # 702.76
    'conspire':re_kw_empty,          # 702.77
    'persist':re_kw_empty,           # 702.78
    'wither':re_kw_empty,            # 702.79
    'retrace':re_kw_empty,           # 702.80
    'devour':re_kw_n,                # 702.81
    'exalted':re_kw_empty,           # 702.82
    'unearth':re_kw_cost,            # 702.83
    'cascade':re_kw_empty,           # 702.84
    'annihilator':re_kw_n,           # 702.85
    'level_up':re_kw_cost,           # 702.86
    'rebound':re_kw_empty,           # 702.87
    'totem_armor':re_kw_empty,       # 702.88
    'infect':re_kw_empty,            # 702.89
    'battle_cry':re_kw_empty,        # 702.90
    'living_weapon':re_kw_empty,     # 702.91
    'undying':re_kw_empty,           # 702.92
    'miracle':re_kw_cost,            # 702.93
    'soulbond':re_kw_empty,          # 702.94
    'overload':re_kw_cost,           # 702.95
    'scavenge':re_kw_cost,           # 702.96
    'unleash':re_kw_empty,           # 702.97
    'cipher':re_kw_empty,            # 702.98
    'evolve':re_kw_empty,            # 702.99
    'extort':re_kw_empty,            # 702.100
    'fuse':re_kw_empty,              # 702.101
    'bestow':re_kw_cost,             # 702.102
    'tribute':re_kw_n,               # 702.103
    'dethrone':re_kw_empty,          # 702.104
    #'hidden_agenda':re_kw_empty, # 702.105 (wont' see these)
    'outlast':re_kw_cost,            # 702.106
    'prowess':re_kw_empty,           # 702.107
    'dash':re_kw_cost,               # 702.108
    'exploit':re_kw_empty,           # 702.109
    'menace':re_kw_empty,            # 702.110
    'renown':re_kw_n,                # 702.111
    'awaken':re_kw_cost,             # 702.112
    'devoid':re_kw_empty,            # 702.113
    'ingest':re_kw_empty,            # 702.114
    'myriad':re_kw_empty,            # 702.115
    'surge':re_kw_cost,              # 702.116
    'skulk':re_kw_empty,             # 702.117
    'emerge':re_kw_cost,             # 702.118
    'escalate':re_kw_cost,           # 702.119
    'melee':re_kw_empty,             # 702.120
    'crew':re_kw_n,                  # 702.121
    'fabricate':re_kw_n,             # 702.122
    'partner':re_kw_partner,         # 702.123
    'undaunted':re_kw_empty,         # 702.124
    'improvise':re_kw_empty,         # 702.125
    'aftermath':re_kw_empty,         # 702.126
    'embalm':re_kw_cost,             # 702.127
    'eternalize':re_kw_cost,         # 702.128
    'afflict':re_kw_n,               # 702.129
    'ascend':re_kw_empty,            # 702.130
    'assist':re_kw_empty,            # 702.131
    'jump-start':re_kw_empty,        # 702.132
    'mentor':re_kw_empty,            # 702.133
    'afterlife':re_kw_n,             # 702.134
    'riot':re_kw_empty,              # 702.135
    'spectacle':re_kw_cost,          # 702.136
    'escape':re_kw_cost,             # 702.137
}

# assigns expected group names from regex match
kw_param_template = {
    'enchant':('quality',),
    'equip':('quality','cost'),
    'hexproof':('quality','quality','quality'),
    'protection':('quality','quality','quality'),
    'rampage':('n',),
    'cumlative_upkeep':('cost','cost'),
    'buyback':('cost','cost'),
    'cycling':('cost','cost'),
    'echo':('cost','cost'),
    'fading':('n',),
    'kicker':('cost','cost'),
    'multikicker':('cost','cost'),
    'flashback':('cost','cost'),
    'madness':('cost','cost'),
    'morph':('cost','cost'),
    'megamorph':('cost','cost'),
    'amplify':('n',),
    'affinity':('quality',),
    'entwine':('cost','cost'),
    'modular':('n',),
    'bushido':('n',),
    'soulshift':('n',),
    'splice':('quality','cost','cost',),
    'ninjutsu':('cost','cost'),
    'commander_ninjutsu':('cost','cost'),
    'dredge':('n',),
    'transmute':('cost','cost'),
    'bloodthirst':('n',),
    'replicate':('cost','cost'),
    'forecast':('activated-ability',),
    'graft':('n',),
    'recover':('cost','cost'),
    'ripple':('n',),
    'suspend':('n','cost','instruction',),
    'vanishing':('n',),
    'absorb':('n',),
    'aura_swap':('cost','cost'),
    'fortify':('cost','cost'),
    'frenzy':('n',),
    'poisonous':('n',),
    'transfigure':('cost','cost'),
    'champion':('quality',),
    'evoke':('cost','cost'),
    'prowl':('cost','cost'),
    'reinforce':('n',),
    'devour':('n',),
    'unearth':('cost','cost'),
    'annihilator':('n',),
    'level_up':('cost','cost'),
    'miracle':('cost','cost'),
    'overload':('cost','cost'),
    'scavenge':('cost','cost'),
    'bestow':('cost','cost'),
    'tribute':('n',),
    'outlast':('cost','cost'),
    'dash':('cost','cost'),
    'renown':('n',),
    'awaken':('cost','cost'),
    'surge':('cost','cost'),
    'emerge':('cost','cost'),
    'escalate':('cost','cost'),
    'crew':('n',),
    'fabricate':('n',),
    'partner':('with',),
    'embalm':('cost','cost'),
    'eternalize':('cost','cost'),
    'afflict':('n',),
    'afterlife':('n',),
    'spectacle':('cost','cost'),
    'escape':('cost','cost'),
}

####
## REPLACEMENT EFFECTS (614)
####

## INSTEAD CLAUSES (614.1a)
# These must be done in the order below or false positives will occur

# if would instead i.e. Abandoned Sarcophagus
#  if [thing] would [a], [b] instead
re_if_would_instead = re.compile(
    r"^cn<if> (.+) cn<would> (.+), (.+) cn<instead>\.?$"
)

# if instead i.e. Cleansing Medidation
#   if [event/condition] instead [replacement].
# the instead comes between the condiction and the replacement
re_if_instead = re.compile(r"^cn<if> (.+) cn<instead> (.+)\.?$")

# if instead fence i.e. Nyxbloom Ancient
#   if [event/condition], [replacement] instead
# the instead comes last and the condition and replacment are found by splitting
# on the last comma
re_if_instead_fence = re.compile(r"^cn<if> (.+), (.+) cn<instead>\.?$")

# if instead of i.e. Pale Moon
#   if [event], [replacement] instead of [original]
re_if_instead_of = re.compile(r"^cn<if> (.+), (.+) cn<instead> of (.+)\.?$")

# instead if i.e. Crown of Empires
#  [replacement] instead if [condition]
# the condition and replacement are switched
re_instead_if = re.compile(r"^(.+) cn<instead> cn<if> (.+)\.?$")

# instead of if i.e. Caravan Vigil
#  [replacement] instead of [orginal] if [condition]
re_instead_of_if = re.compile(r"^(.+) cn<instead> of (.+) cn<if> (.+)\.?$")

# that would instead i.e. Ali from Cairo
#  [original] that would [(action) original] (action) [replacment] instead.
# These cannot be handled by RegEx alone as the condition and replacement are
# separated by an action word
re_that_would_instead = re.compile(
    r"^(.+) xq<that> cn<would> (.+) cn<instead>\.?$"
)

# would instead i.e. Aegis of honor
#  [timing] [condition] would [original], [replacment] instead.
# related to timing
re_would_instead = re.compile(r"^(.+) cn<would> (.+), (.+) cn<instead>\.?$")

# instead of i.e. Feather, the Redeemed
# NOTE: these do not have a preceeding if/would
re_instead_of = re.compile(r"^(.+) cn<instead> of (.+)\.?$")

## SKIP CLAUSES (614.1b)
# These must be done in the order below or false positives will occur

# skip clauses i.e. Stasis (Note as of IKO, I found 49) have the form
#  [player]? skip(s) [phase/step]
# where if player is not present there is an implied 'you'
re_skip = re.compile(r"^(?:(.+) )?xa<skip(?: suffix=s)?> (.+)\.?$")

## ENTERS THE BATTLEFIELD CLAUSES (614.1c)
# Permanent enters the battlefield with ...
# As Permanent enters the battlefield ...
# Permanent enters the battlefield as ...

# Permanent enters the battlefield with ... i.e. Pentavus have the form
#  [permanent] enters the battlefield with [counters]
# these are all counters
re_etb_with = re.compile(
    r"^(.+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> pr<with> (.+)\.?$"
)

# As permanent enters the battlefield ... i.e. Sewer Nemsis have the form
#  as [permanent] enters the battlefield, [event]
re_as_etb = re.compile(
    r"^as (.+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield>, (.+)\.$"
)

# Permanent enters the battlefield as ... i.e.
#  [Permanent] enters the battlefield as
re_etb_as = re.compile(
    r"^(.+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> as (.+)\.$"
)

## ENTERS THE BATTLEFIELD CLAUSES (614.1d) - continuous effects
# TODO: how to not tag etb triggers ??? (Check for comma maybe)
# Permanent enters the battlefield ...
# Objects enter the battlefield ...
# NOTE: have to assume that after above, all remaining ETB fit this
re_etb_1d = re.compile(
    r"^(.+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> (.+)\.$"
)

## TURNED FACE UP
# As Permanent is turned face up
re_turn_up = re.compile(
    r"^as (.+) is xa<turn suffix=ed> xm<face amplifier=up>, (.+)\.$"
#as ob<card ref=self> is xa<turn suffix=ed> xm<face amplifier=up>,
)