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
__version__ = '0.0.3'
__date__ = 'June 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re

####
## MISCELLANEOUS
####

# use with split to break a line into sentences or clauses by the period or comma
# where the period is not enclosed in quotes. Grabs all characters upto the period
# Thanks to 'Jens' for the solution to this at
# https://stackoverflow.com/questions/6462578/regex-to-match-all-instances-not-inside-quotes
# which finds any periods followed by an even number of quotes
re_sentence = re.compile(r"\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

# clauses are separated by commas (may include an and that will be 'stripped'
re_clause = re.compile(r",(?: and)?")

####
## TYPE CHECKS
####

# an action clause will start with an action tag
re_is_act_clause = re.compile(r"^[kx]a<\w+>")

####
## LINE TYPES
####

# Ability word lines start with an ability word followed by a long hypen and then
# the ability clause and end with a sentence
re_aw_line = re.compile(r"^aw<([^>]+)> — (.+?)\.$")

# Keyword lines start with a keyword (or object keyword if landwalk) and contain
# one or more comma separated keyword claues
re_kw_line = re.compile(r"^((?:ob|xr)<[^>]+> )?(kw<[\w-]+>)")

# a non-standard keyword line will contain a long hypen and end with a period
# between the hypen and period is the non-standard cost i.e. Aboroth
#re_kw_line_ns = re.compile(r"^(kw<[\w-]+>)—(.+?)\.$")

# Ability lines (113.3) are not keyword lines or ability word lines. There are
# four subtypes:
#  113.3a Spell - an instant or sorcery
#  113.3b Activated - of the form cost : effect
#  113.3c Triggered - of the form TRIGGER PREAMBLE condition, effect [instrunctions]?
#   A delayed trigger (603.7) a result of replacement effects
#  113.3d static - none of the above

# Activated (602.1, 113.3b) contains a ':' which splits the cost and effect (cannot
# be inside double quotes) have the form:
#  [cost]: [effect]. [Instructions]?
# NOTE: knowing where effect and instructions split is difficult. For now we
#  are assuming the last sentence if present are instructions
re_act_check = re.compile(r"(?<!\"[^\"]+):")
re_act_line = re.compile(r"^(.+?): (.+?)(?:\. ([^.]+))?\.?$")

# Triggered (603.1) lines starts with a trigger preamble
# Triggered abilities have the form:
#  [When/Whenever/At] [condition], [effect]. [Instructions]?
# Some cards (Goblin Flotilla) have embedded triggered abilities of the form
#  [When/Whenever/At] [condition] [triggered-ability]
# NOTE: since we are basing our delimitation of the individual 'components',
#  have to build in checks for periods that are inclosed in double parenthesis
#  and single, double parenthesis (Reef Worm)
re_tgr_check = re.compile(r"^(tp<\w+>)")
re_tgr_line = re.compile(r"^tp<(\w+)> ([^\.]+), ([^\.]+)(?:\. (.+))?\.?$")
re_embedded_tgr_line = re.compile(r"^tp<(\w+)> ([^\.]+), (tp<\w+> [^\.]+)\.?$")

# Delayed Triggered (603.7) "do something at a later time - contains a trigger
# preamble but not usually at the beginning of the ability and end with a turn
# structure. See Prized Amalgam
# For now, look for lines having the form
#  [effect] [when/whenever/at] [condition]
#  where the condition ends with a turn structure
# NOTE: we ensure effect does not cross sentence/clause boundaries
re_delayed_tgr_check = re.compile(r"tp<\w+> (?:.+ )?ts<[^>]+>\.?$")
re_delayed_tgr_clause = re.compile(
    r"([^,|^\.]+) tp<(\w+)> ((?:[^\.]+ )?ts<[^>]+>)\.?$"
)

# conjunction of phrases (See Giant Oyster)
# These will have a phrase followed by a ", and" and another phrase. Have to check
# that the first phrase does not have commas (or periods). In other words, if
# there are commas preceding a ", and", this is part of a list otherwise, it
# signifies distinct parts
re_phrase_conjunction = re.compile(r"^([^,|^\.]+), and ([^\.]+)$")

# the following is not a defined line but needs to be handled carefully
# Quotation enclosed phrases preceded by 'have' (Coral Net) or 'gain' (Abnormal
# Endurance). Mentioned in 113.1a under effects that grant abilities
# NOTE: the duration may be in the front or in the back
# NOTE: handling situations like Diviner's Wand where more than one ability is
#  granted via an optional check for an 'and' followed by an enclosed phrase
# These have the form:
#  [duration],? [object] has/gains "[ability]" [and "ability"]? [duration]?.
re_enclosed_quote = re.compile(r'\"([^\"]+)\"') # drop the last period

# variable instantiates have the form
# [variable|variable attribute], where nu<x|y> is [instantiation]
# NOTE: have to stop on a period, comma, end of line or 'and'
# mana instantiates have the form (see Spell Rupture)
# {X}, where nu<x> is [instantiation]
re_variable_val = re.compile(
    r"(nu<\w>|xr<[^>]+ val=≡\w>), where nu<\w> xa<is> ([^\.|,]+?)(?=(?:\.|,| and|$))"
)
re_variable_mana = re.compile(
    r"({x}), where nu<\w> xa<is> ([^\.|,]+?)(?=(?:\.|,| and|$))"
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
    r"((?:xr|ob)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>)? ?"
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
    r"<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>)"
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
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>)? ?"
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
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>))?"
    r"(?:, pr<from> "
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>))?"
    r"(?:,? and pr<from> "
    r"((?:ob|xr)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>))?"
)

# Partner (702.123) has no parameters but Partner with (702.123f) does
# Partner with [NAME]
re_kw_partner = re.compile(
    r"(?:pr<with> "
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>)"
    r")?"
)

# splice (702.46) splice onto [quality] [cost]
# TODO: the trailing period is not passed as parmater on non-standard costs
# TODO: cannot get rid of the 'hidden group' in the cost portion
re_kw_splice = re.compile(
    r"pr<onto> "
    r"(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)"
     r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\('\)]+?)*>)"
    r"(?: ((?:{[0-9wubrgscpx\/]+})+)|—(.+?)$)"
)

# forecast (702.56) forecast — [actiavated ability] and
# companion (702.139) companion - condition
re_kw_statement = re.compile(r" ?— (.+?)$")

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
    'forecast':re_kw_statement,      # 702.56
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
    'companion':re_kw_statement,     # 702.138
    'mutate':re_kw_cost,             # 702.139
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
    'companion':('condition',),
    'mutate':('cost','cost'),
}

####
## KEYWORD ACTIONS (701.2 - 701/43)
####

# some action clauses have trailing qualifying clauses
# extract these before processing the action clause
#  1. location i.e. Cremate
#   [action-clause] [prep] [zone-clause]
#  2. sequence i.e. Conqueror's Flail
#   [action-clause] [sequence] [phase]
#  3. duration i.e. Turf Wound
#   [quanitifer] [phase]
re_act_clause_zone = re.compile(r"^([^,|^\.]+) pr<([^>]+)> (.+ zn<[^>]+>)\.?$")
re_act_clause_sequence = re.compile(r"^([^,|^\.]+) (sq<[^>]+> (?:.* )?ts<[^>]+>)\.?$")
re_act_clause_duration = re.compile(r"^([^,|^\.]+) (xq<[^>]+> ts<[^>]+>)\.?$")

# keyword or lituus action clause - can have
#  1. a conjunction of actions
#    [thing] [action-word] [parameters] and [action-word] [parameters]
#  2. singular (may have optional thing and/or conditional
#   [thing]? [conditional]? [action word] [parameters]
#  3. an exceptions is control/own phrases of the form i.e. Synod Centurion
#   [player] [own|control] [clause]
#  will also be treated as action clause. NOTE: IOT not match "you control" and
#  the like, requires at least one character following the own/control tag
# TODO: this is not a perfect check but will cut out most none action clauses
re_act_clause_check = re.compile(
    r"((?:xa|ka)<[^>]+>|xp<[^>]+> xc<(?:own|control)(?: suffix=s)?>)"
)
re_conjunction_action_clause = re.compile(
    r"^(?:([^,|^\.]*?) )?(?:cn<([^>]+)> )?((?:xa|ka)<[^>]+>)"
    r"(?: ([^,|^\.]+))? (and|or) ((?:xa|ka)<[^>]+>)(?: ([^,|^\.]+))?\.?$"
)
re_action_clause = re.compile(
    r"^(?:([^,|^\.]*?) )?(?:cn<([^>]+)> )?"
    r"(?<!(?:ka|xa)<[^>]+>.*?)([xk]a<\w+(?: [^>]+)?>)" # cannot be preceded by an action
    r"(?: ([^,|^\.]+))?\.?$"
)
re_action_ply_poss = re.compile(
    r"^((?:xq<[^>]+> )?(?:xs<[^>]+> )?xp<[^>]+>) "
     r"xc<(own|control)(?: suffix=s)?>(?: ([^\.]+))\.?$"
)

####
## REPLACEMENT EFFECTS (614)
####

## INSTEAD CLAUSES (614.1a)
# These must be done in the order below or false positives will occur

# if would instead
# three variants
#  a. if [thing] would [action] or [thing] would [action], [action] instead i.e Anafenza
#  b. if [thing] would [action], [action] instead i.e. Abandoned Sarcophagus
#  c. if [thing] would [action], instead [action] i.e. Breathstealer's Crypt
re_if_would2_instead = re.compile(
    r"^cn<if> (.+) cn<would> (.+) or (.+) cn<would> ([^,]+), (.+) cn<instead>\.?$"
)
re_if_would_instead1 = re.compile(
    r"^cn<if> (.+) cn<would> ([^,]+), (.+) cn<instead>\.?$"
)
re_if_would_instead2 = re.compile(
    r"^cn<if> (.+) cn<would> ([^,]+), cn<instead> ([^\.]+)\.?$"
)

# that would instead i.e. Ali from Cairo
#  [original] that would [(action) original] (action) [replacment] instead.
# These cannot be handled by RegEx alone as the condition and replacement are
# separated by an action word
re_that_would_instead = re.compile(
    r"^([^,|\.]+) xq<that> cn<would> (.+) cn<instead>\.?$"
)

# would instead i.e. Aegis of honor
#  [duration] [condition] would [original], [replacment] instead.
# related to timing
re_would_instead = re.compile(r"^([^,|\.]+) cn<would> (.+), (.+) cn<instead>\.?$")

# may instead (limited replacement - have only seen 2) i.e. Abundance
# if [player] would [action], [player] may instead [action]
re_may_instead = re.compile(
    r"^cn<if> (.+) cn<would> ([^,]+), (.+) cn<may> cn<instead> ([^\.]+)\.?$"
)

# if instead of i.e. Pale Moon
#   if [action], [replacement] instead of [original]
re_if_instead_of = re.compile(r"^cn<if> (.+), (.+) cn<instead> of ([^\.]+)\.?$")

# instead of if i.e. Caravan Vigil
#  [replacement] instead of [orginal] if [condition]
re_instead_of_if = re.compile(r"^([^,|\.]+) cn<instead> of (.+) cn<if> ([^\.]+)\.?$")

# instead of i.e. Feather, the Redeemed
#  [replacement] instead of [original]
# NOTE: these do not have a preceeding if/would
re_instead_of = re.compile(r"^([^,|\.]+) cn<instead> of ([^\.]+)\.?$")

# if instead i.e. Cleansing Medidation
#   if [event/condition] instead [replacement].
# the instead comes between the condiction and the replacement
re_if_instead = re.compile(r"^cn<if> (.+) cn<instead> ([^\.]+)\.?$")

# if instead fence i.e. Nyxbloom Ancient
#   if [event/condition], [replacement] instead
re_if_instead_fence = re.compile(r"^cn<if> (.+), (.+) cn<instead>\.?$")

# instead if i.e. Crown of Empires
#  [replacement] instead if [condition]
# the condition and replacement are switched
re_instead_if = re.compile(r"^([^,|\.]+) cn<instead> cn<if> ([^\.]+)\.?$")

## SKIP CLAUSES (614.1b)
# These must be done in the order below or false positives will occur

# skip clauses i.e. Stasis (Note as of IKO, I found 49) have the form
#  [player]? skip(s) [phase/step]
# where if player is not present there is an implied 'you'
re_skip = re.compile(r"^(?:(.+) )?xa<skip(?: suffix=s)?> ([^\.]+)\.$")

## ENTERS THE BATTLEFIELD CLAUSES (614.1c)
# Permanent enters the battlefield with ...
# As Permanent enters the battlefield ...
# Permanent enters the battlefield as ...
re_etb_repl_check = re.compile(r"xa<enter(?: suffix=s)?> xq<the> zn<battlefield>")

# Permanent enters the battlefield with ... i.e. Pentavus have the form
#  [permanent] enters the battlefield with [counters]
# these are all counters
re_etb_with = re.compile(
    r"^([^,|\.]+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> pr<with> ([^\.]+)\.?$"
)

# As permanent enters the battlefield ... i.e. Sewer Nemsis have the form
#  as [permanent] enters the battlefield, [event]
re_as_etb = re.compile(
    r"^pr<as> (.+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield>, ([^\.]+)\.?$"
)

# Permanent enters the battlefield as ... i.e. Clone
#  [Permanent] enters the battlefield as
re_etb_as = re.compile(
    r"^([^,|\.]+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> pr<as> ([^\.]+)\.?$"
)

## ENTERS THE BATTLEFIELD CLAUSES (614.1d) - continuous effects
# Permanent enters the battlefield ... i.e. Jungle Hollow (tapped), and
#  Gather Specimens (effect)
# Objects enter the battlefield ...
# NOTE: have to assume that after above, all remaining ETB fit this
#  Because enters tapped is so predominant, we add a special case
re_etb_status = re.compile(
    r"^([^,|\.]+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield> "
     r"st<([^>]+)>(?: cn<unless> ([^\.]+))?\.?$"
)
re_etb_1d = re.compile(
    r"^([^,|\.]+) xa<enter(?: suffix=s)?> xq<the> zn<battlefield>(?: ([^\.]+))?\.?$"
)

## TURNED FACE UP (614.1e)
# As Permanent is turned face up i.e. Gift of Doom
re_turn_up_check = re.compile(r"xa<turn suffix=ed> xm<face amplifier=up>")
re_turn_up = re.compile(
    r"^pr<as> (.+) xa<is> xa<turn suffix=ed> xm<face amplifier=up>, ([^\.]+)\.?$"
)

## (614.2) applying to damage from a source
# NOTE: some of these have already been handled during graphing of would-instead

# check for damage
re_repl_dmg_check = re.compile(r"(?:ef<damage>|ka<regenerate>)")

# similar to 'instead' but is a replacement under 614.2 i.e. Sphere of Purity
# this will catch regenerate i.e. Mossbridge Troll as well as prevention
# if [source] would [old], [new]
re_if_would = re.compile(r"^cn<if> (.+) cn<would> (.+), (.+)\.?$")

# the [time] [source] would [action] [to [target]]? [phase] [action] i.e.
# Awe Strike
re_repl_dmg = re.compile(
    r"^([^,]+ sq<(?:\w+)>) "
    r"(.+) cn<would> (.*?) (?:pr<to> (.+) )?(xq<(?:[^>]+)> ts<\w+>), ([^\.]+)\.?$"
)

# alternate playing costs (APC) (118.9,113.6c)
# Alternate costs are usually phrased:
#  You may [action] rather than pay [this object’s] mana cost,
# and
#  You may cast [this object] without paying its mana cost.

# optional APC (i.e. you may)
# (if [condition],)? [player] may [action] rather than pay [cost].
# NOTE: the condition may or may not be present see Ricochet Trap for a condition
#  and Bringer of the Red Dawn for a conditionless
# NOTE: the action may be an alternate/reduced mana payment i.e. Ricochet Trap or
#  other i.e. Sivvi's Valor
re_action_apc = re.compile(
    r"^(?:cn<if> (.+), )?([^,]+) cn<may> (.+) cn<rather_than> xa<pay> ([^\.]+)\.$"
)

# if [condition], you may cast [object] without paying its mana cost i.e. Massacre
# these are all condition based
re_cast_apc_nocost = re.compile(
    r"^cn<if> (.+), "
     r"xp<you> cn<may> ka<cast> ob<card ref=self> pr<without> ([^.]+)\.?$"
)

# alternate phrasing found in three cards (Skyshroud Cutter, Reverent Silence &
# Invigorate).
#  if [condition], rather than pay self's mana cost you may [action].
# this is alternate phrasing of re_action_apc
re_alt_action_apc = re.compile(
    r"^cn<if> (.+), cn<rather_than> xa<pay> ([^,]+), xp<you> cn<may> (.+)\.?$"
)

# contains "rather than" - a reverse of re_action_apc i.e. Dream Halls
#  1. rather than pay [cost], [player] may [action]
re_rather_than_apc = re.compile(
    r"^cn<rather_than> xa<pay> ([^,]+), (.+) cn<may> ([^\.]+)\.?$"
)

# Additionally, some cards "grant" alternate playing costs i.e Once Upon a Time
#  and Isochron Scepter
# [player] may cast [thing] without paying [thing's] mana cost
re_grant_nocost = re.compile(
    r"^([^,|*\.]+) cn<may> (ka<(?:cast|play)> .+) pr<without> "
     r"(xa<pay suffix=ing> .+ xo<cost type=mana>)\.?$"
)

## ADDITIONAL COSTS
# (mentioned throughout but phrased in 604.5 "As an additional cost to cast..."
# As an additional cost to cast [thing], [add-cost]
re_add_cost_check = re.compile(r"xq<a∧additional> xo<cost>")
re_add_cost = re.compile(
    r"^pr<as> xq<a∧additional> xo<cost> pr<to> ka<cast> ([^,]+), ([^\.]+)\.?$"
)

## MODAL PHRASES
# (700.2) modal phrases i.e. Charming Prince have two or more options in a bulleted
# list & have the form
#  choose [number] —(•[choice])+
# And, 700.2d defines modal spells allowing players to the same mode more than
# once, these will have the phrase “You may choose the same mode more than once.”
# See Mystic Confluence and have the form:
# choose [operator]? [number]. [Instructions] (•[choice])+
# Vindictive Lich is an exception where the instructions differ and the number
# includes an operator
re_modal_check = re.compile(r"^xa<choose> nu<([^>]+)>.+•")
re_modal_phrase = re.compile(r"^xa<choose> nu<([^>]+)> —([^\.]+)\.?$")
re_modal_phrase_instr = re.compile(
    r"^xa<choose> nu<([^>]+)>\. ([^•]+) ([^\.]+)\.?$"
)
re_opt_delim = re.compile(r" ?•")

## LEVELER PHRASES
# (710.2a) (NOTE: the form as specified in 710.2a has [Abilities] [P/T] whereas
# the oracle text has [P/T] [Abilities]
# Level lines consist of one or more level clauses each having the form:
#  •[level symbol] [P/T]? [Abilities]
re_lvl_up_check = re.compile(r"^•xo<level>")
re_lvl_up_lvl = re.compile(
    r"^xo<level> nu<([^>]+)>(\+|-)(?:nu<([^>]+)>)?"
     r"(?: xr<p/t val=(\d+/\d+)>)?(?: (.+))?$"
)

## SAGA PHRASES
# (714.2)
re_saga_check = re.compile(r"^i.* — ") # there is a hanging newline
re_chapter_delim = re.compile(r"(i[iv]*(?:, i[iv]+)*) — ")
#re_saga_chapter = re.compile(r"(i[iv]*(?:, i[iv]+)?) — (.+?)(?=(?:\.[iv]+|$))")

####
## LITUUS PHRASE TYPES
####

# sequences
#  Checks
#   a - any phrase with a sequence will be considered a sequence phrase
#   b - for time, if the phrase ends with a turn-structure or starts w/ the form
#   [quanitifier] [turn-structure], ...
#  1. dual - [sequence-clause], [sequence-clause] i.e. Templar Elder
#  2. then [action] i.e. Barishi possibly ended with an again see Roalesk
#  3. duration -
#     [sequence] [playes]? [phase/step], [action]
#  4. condition - [sequence] [condition], [action] i.e. Hungering Yetis
#  5. until -  [action] until [condition]
#  6. trailing sequence from delayed triggers i.e. Prized Amalgam
#   [quanitifer] [sequence] of [clause]? [quanitifier] [turn structure]
#  7. time variation 2 i.e. Delfin's Cube
#   this turn, (effect)
#  8. as long as 2 variations
#   a. [for]? as long as [condition], [effect] i.e Release to the Wind
#   b. [effect] as long as [condition] i.e. Hooded Horror
re_sequence_check = re.compile(r"sq<[^>]+>")
re_time_check_start = re.compile(r"^xq<[^>]+> ts<[^>]+>,")
re_time_check_end = re.compile(r"ts<([^>]+)>$")
re_dual_sequence = re.compile(r"^(sq<[^>]+> [^,]+), (sq<[^>]+> [^\.]+)\.?$")
re_sequence_then = re.compile(
    r"^(?:([^\.]+) )?(sq<then>) ([^\.]*?)(?: (sq<again>))?\.?$"
)
re_sequence_dur = re.compile(
    r"^(sq<[^>]+> (?:.*xp<[^>]+>.* )?ts<[^,]+>), ([^\.]+)\.?$"
)
re_sequence_cond = re.compile(r"^sq<([^>]+)> ([^,]+), ([^\.]+)\.?$")
re_sequence_until = re.compile(r"([^,|^\.]+) sq<(until)> ([^,|^\.]+)\.?$")
re_sequence_time = re.compile(
    r"^xq<([^>]+)> sq<([^>]+)> pr<of> (?:([^,|^\.]+) )?xq<([^>]+)> ts<([^>]+)>\.?$"
)
re_sequence_time2 = re.compile(r"^(xq<[^>]+> ts<[^>]+>), (.+)\.?$")
re_sequence_as_long_as1 = re.compile(
    r"^(?:(pr<for>) )?sq<as_long_as> ([^,]+), ([^\.]+)\.?$"
)
re_sequence_as_long_as2 = re.compile(r"^([^,|^\.]+) sq<as_long_as> ([^\.]+)\.?$")

# duration/times/sequences
# [sequence|quantifier] [phase]
re_duration_ts = re.compile(r"^((?:sq|xq)<[^>]+>) ts<(\w+)>$")

##
# optionals, conditions and restrictions

# [player] may [action] as though [action] [if [condition]]? i.e. Lone Wolf
re_may_as_though = re.compile(
    r"^((?:.+ )?xp<[^>]+>) cn<may> (.+) pr<as_though> ([^\.]+)\.?$"
)

# [player] may have [clause] i.e. Browbeat
re_may_have = re.compile(
    r"^((?:[^,|\.]+)?xp<\w+(?: suffix=[^>]+)?>) "
     r"cn<may> xa<have(?: suffix=[^>]+)?> ([^\.]+)\.?$"
)

# contains 'may' [player] may [action] i.e. Ad Nauseam
re_optional_may = re.compile(
    r"^((?:[^,|\.]+)?xp<\w+(?: suffix=\w+)?>(?:[^,|\.]+)?) "
     r"cn<may> ([x|k]a<\w+>(?:[^\.]+))\.?$"
)

# starts with if
#  a) if-player-does has two formation
#   i. if [player] does [not]? [action] i.e. Decree of Justice
#   ii. if [player] does [trigger] i.e. Providence
#  b) if [player] cannot, [action] i.e. Brain Pry
#  c) if [condition], [action] i.e Ordeal of Thassa
#  d) [action] if [condition] i.e. Ghastly Demise
#  e) if [condition], [action]. otherwise, [action]
#   NOTE: we need to catch this prior to lines being broken down into sentences
#   so we catch previous sentences if present
#  f) generic if condition
#  if [condition]
re_if_ply_does  = re.compile(
    r"^cn<if> ([^,|^\.]+) xa<do(?: suffix=\w+)?>(?: (cn<not>))?, ([^\.]+)\.?$"
)
re_if_ply_cant = re.compile(r"^cn<if> ([^,|^\.]+) cn<cannot>, ([^\.]+)\.?$")
re_if_cond_act = re.compile(r"^cn<if> ([^,|^\.]+), ([^\.]+)\.?$")
re_act_if_cond = re.compile(r"^([^,|^\.]+) cn<if> ([^,|\.]+)\.?$")
re_if_otherwise = re.compile(
    r"^(?:(.+?\.) )?cn<if> ([^,|^\.]+), ([^\.]+)\. "
     r"cn<otherwise>, ([^\.]+)\.?(?: ([^\.]+)\.?)?$"
)
re_if_condition = re.compile(r"^cn<if> ([^,|\.]+)\.?$")

# ends with if
# [action] if able i.e. Aggravate
#re_act_if_able = re.compile(r"^([^,|^\.]+) (cn<if> able)$")

# contains unless
# The rules only mention unless in 722.6 "[A] unless [B]" However going through
# them while B always appears to always be a condition there are five flavors
# regarding A, depending on the context.
#  1. [thing] cannot [action] unless [condition] i.e. Okk
#  2. [action] unless [condition] i.e. Bog Elemental
#  3. [status] unless [condition] i.e. Bountiful Promenade
#  4. [player] may [action] unless [condition] i.e Mystic Remora (only 5 of these)
# NOTE: unless is generally part of a clause that is part of a phrase therefore
#  we do not want to grab anything that extends to the left past a clause (",")
#  or sentence (".") boundary
re_cannot_unless = re.compile(
    r"^([^,|\.]+) cn<cannot> (.+) cn<unless> ([^,|\.]+)\.?$")
re_action_unless = re.compile(
    r"^((?:[^,|^\.]+ )?[kx]a<\w+(?: [^>]+)?>.+) cn<unless> ([^,|\.]+)\.?$"
)
re_status_unless = re.compile(r"^(?:st|xs])<(\w+)> cn<unless> ([^,|\.]+)\.?$")
re_may_unless = re.compile(r"^([^,|\.]+) cn<may> (.+) cn<unless> ([^,|\.]+)\.?$")

# standalone otherwise i.e. primal empathy
re_otherwise = re.compile(r"^cn<otherwise>, ([^\.]+)\.?$")

# for each condition see
#  1. for each [condition], [action] i.e. From the Ashes
#  2. [action] for each [condition] i.e. Gnaw to the Bone
re_for_each_cond1 = re.compile(r"pr<for> xq<each> ([^,|^\.]+), ([^,|\.]+)\.?$")
re_for_each_cond2 = re.compile(r"^([^,|^\.]+) pr<for> xq<each> ([^,|\.]+)\.?$")

# some restrictions have a conjunction of only restrictions with the basic form
#  [action] only|only_if [clause] and only|only_if [clause]
# for each of the clauses, have to look at the condition type. If it is only
#  the clause is timing related. If it is only_if, the clause is a condition
# TODO: Capricorn is an exception to the pattern and is of the form
#  only [player] may [action] and only during [timing]
# I think only ands are present but just case check for 'or' and 'and/or'
re_only_conjunction = re.compile(
    r"^([^,|\.]+) (cn<(?:only|only_if)> [^,|^\.]+) (and|or|and/or) "
     r"(cn<(?:only|only_if)> [^,|^\.]+)\.?"
)

# timing restrictions only during ...
# 1. [action] only any time you could cast a sorcery
# 2. [action] only during [phase/step]
# 3. [action] only [number] times [phase/step]
#  2.a variant due to tagging comes from no more than as an operator (translates
#  to only up to x times
#  TODO: see Sewer Rats no more
# 4. Generic only i.e. Temple Elder these may fit one of the above but include
#  additional phrases, clauses etc
#  [action] only [condition]
#  NOTE: as in Temple Elder, we do not want to break on commas
re_restriction_time = re.compile(
    r"^(?:([^,|\.]+) )?cn<only> (xq<any> sq<time> [^,|\.]+)\.?$"
)
re_restriction_timing = re.compile(
    r"^(?:([^,|\.]+) )?cn<only> sq<(\w+)> ((?:[^,|\.]+ )?ts<[^>]+>)\.?$"
)
re_restriction_number = re.compile(
    "^(?:([^,|\.]+) )?cn<only> nu<([^>]+)> sq<time(?:[^>]+)?>"
     "(?: ((?:[^,|\.]+ )?ts<[^>]+>))?\.?$"
)
re_restriction_only = re.compile(
    r"^([^\.]+) cn<only> ([^\.]+)\.?$"
)

# condition restrictions only_if
re_only_if = re.compile(r"^(?:([^,|\.]+) )?cn<only_if> ([^,|\.]+)\.?$")

# but condition restrictions i.e. Haakon
# [action],? but [condition-word] [restriction]
re_restriction_but = re.compile(r"^(.+?),? but cn<(\w+)> ([^,|\.]+)\.?$")

# Exception: contains except - the opposite of a restriction, it provides
# additional abilities, characteristics see Lazav, the Multifarious
re_exception_check = re.compile(r"cn<except>")
re_exception_phrase = re.compile(r"(.+?), cn<except> ([^\.]+)\.?$")

####
## CLAUSES
####

# TODO: i don't like doing these twice but unlike sequence phrases, these are
#  standalone that is there are no preceding or following structures
re_sequence_clause_check = re.compile(r"^sq<[^>]+>")
re_sequence_clause = re.compile(
    r"^sq<([^>]+)> ([^,|^\.]+)$"
)

# two separate clauses conjoined by a conjunction word (will not cross boundaries
# i.e., commas or periods
# TODO: are we still using this
re_ntimes = re.compile(r"^(nu<[^>]+>|xq<[^>]+>) sq<time(?: suffix=s)?>$")
re_again = re.compile(r"^sq<(again)>$")
re_until_phase = re.compile(r"^sq<(until)> (ts<\w+>)$")

####
## PHASES/STEPS
####

# NOTE: these are very similar to the graphing of things and we could consider the
# phases/steps graphed here as 'things' i.e. your turn.
# TODO: push graphing of all phases/steps here (the beginning of your end step etc)
# has the form
#  [player-possessive] [phase/step]
re_phase_clause_check = re.compile(r"ts<([^>]+)>$")
re_phase = re.compile(
    r"^(?:(xq<[^>]+>) )?(?:(xp<[^>]+ suffix=(?:r|'s)>) )?ts<([^>]+)>$"
)

####
## THINGS
####

# find phrases of the form: i.e. Wintermoor Commander
#  [quanitifier]? [status]? [thing's] [attribute]
# in this case, the attribute is the 'subject' or the thing
re_reified_attribute = re.compile(
    r"^(?:(xq<[^>]+>) )?(?:(xs<[^>]+>) )?"
     r"((?:xo|ob)<[^>]+ (?:[^>]*suffix=(?:r|'s)[^>]*)>) xr<([^>]+)>\.?$"
)

# find phrases of the form i.e. Ethereal Ambush (top) Phyrexian Furnace (bottom)
# [quantifier] [top|bottom] [number]? [thing] [zone-clause] [amplifier]?
# NOTE:
#  quantifier should always be the
#  thing will always be card
# quanitifier may be after the number see Scarab Feast
re_qtz = re.compile(
    r"^xq<([^>]+)> (?:pr<(\w+)> )?(?:nu<([^>]+)> )?"
     r"(ob<[^>]+>) pr<(\w+)> ([^,|^\.]+zn<[^>]+>)(?: xm<face amplifier=(up|down)>)?$"
)

# find phrases of the form
#  [number]? [quantifier]? [status]? [THING] [possession]? [qualifying]? [possession]?
# where:
#  THING can be a single thing, a dual conjunction of things or a multi-conjunction
#   of things.
#  possession-clause has the form: [player] [owns|controls]
#  qualifying-clause has the form:
#   [preposition] [qualifiers] and/or
#   that_is/are [qualifiers]
# IOT to merge everything under the thing
# NOTE: if possession-clause and/or preposition-clause are present, the whole is
#  returned & must further be parsed w/ re_possesson_clause, re_qualifying_clause
#  or re_dual_qualifying_clause
re_qst = re.compile(
    r"^(?:nu<([^>]+)> )?(?:xq<([^>]+)> )?(?:(?:xs|st)<([^>]+)> )?"
    r"((?:[^\.]*?)?(?:ob|xp|xo|zn)<[^>]+>)"
    r"(?: ((?:xq<[^>]+> )?(?:(?:st|xs)<[^>]+> )?"
     r"xp<[^>]+> (?:xa<do[^>]*> cn<not> )?xc<[^>]+>))?"
    r"(?: ((?:pr|xq)<(?:with|without|from|of|other_than|that|at)> "
     r"[^\.|^,]+?))?"
    r"(?: ((?:xq<[^>]+> )?(?:(?:st|xs)<[^>]+> )?"
     r"xp<[^>]+> (?:xa<do[^>]*> cn<not> )?xc<[^>]+>))?"
    r"\.?$"
)

# four possibilities for the THING returned from above
#  1. a single object i.e. ob<card ref=self> as in Acid-Spewer Dragon
#  2. a dual conjunction where the second thing may have a preceding quanitifer
#   i.e. ob<card ref=self> or xq<another> ob<permanent characteristics=creature>
#   as in Gruul Ragebeasat
#  3. a multi-conjunction 3 or more comma-separated things i.e. ob<spell>,
#   ob<ability type=activated>, or ob<ability type=triggered> as in Disallow
#   See Royal Decree for a quad-conjunction (NOTE: these were not joined in the
#   tagger because they are not 'like' objects
#  4. Invalid - does not match one of the above
re_singleton_thing = re.compile(r"^((?:ob|xp|xo|zn)<[^>]+>)$")
re_dual_conjunction_thing = re.compile(
    r"^(?:((?:ob|xp|xo|zn)<[^>]+>) (and|or|and/or) (?:xq<([^>]+)> )?)?"
     r"((?:ob|xp|xo|zn)<[^>]+>)$"
)
re_multi_conjunction_thing = re.compile(
    r"^((?:(?:ob|xp|xo|zn)<[^>]+>, ){2,})(and|or|and/or) ((?:ob|xp|xo|zn)<[^>]+>)$"
)

# possessive and qualifying clauses
re_possession_clause = re.compile(
    r"((?:xq<\w*?> )?(?:(?:st|xs)<[^>]+> )?"
     r"xp<[^>]+>) (?:(xa<do[^>]*> cn<not>) )?xc<([^>]+)(?: suffix=s)?>"
)
re_qualifying_clause = re.compile(
    r"^(?:pr|xq)<(with|without|from|of|in|other_than|on|that|at)> (.+)$"
)
re_dual_qualifying_clause = re.compile(
    r"^(pr<(?:with|without|of)> .+) "
     r"((?:pr|xq)<(?:from|with|without|on|of|as|in|that)> .+)$"
)

# finds consecutive things to determine if they are possessive
#  TODO: need to determine if we only need to check for a suffix of "'s" or "r"
#   in the first thing(s)
#  NOTE: in some cases we have three consecutive things (see Trial of Ambition)
#   it's owner's hand so check for three with first being optional and ignored
re_consecutive_things = re.compile(
    r"^(?:xq<(\w+?)> )?(?:((?:ob|xp|xo|zn)<[^>]+>) )?"
     r"((?:ob|xp|xo|zn)<[^>]+>) ((?:ob|xp|xo|zn)<[^>]+>)$"
)

# Qualifying clauses for exapmple with flying

# with/without can have one of the following forms
#  1. with [keyword] - ability clause i.e. with flying (have to check for a
#   preceding object to catch landwalks) i.e. Sidar Kondo
#  TODO: this won't catch nonbasic landwalks like Livonya Silone
#  2. with [attribute] - instantiated attribute i.e. xr<cmc val=≥6>
#   has the form x<attribute_name val=OPVALUE.
#   2.a variant (Azor's Gateway) [num] [quantifier] [attribute]
#  3. with [a|number] [counter] on it/them
#  4. with [quantifier] [attribute] Isperia the Inscrutable attribute is name
#   this is the same as of attribute
#  5 a variation of above
#   with the [qualifier] [lituus object] i.e. Ghazban Ogre
re_qual_with_ability = re.compile(r"^(?:(ob<[^>]+>) )?kw<([^>]+)>$")
re_qual_with_dual_attribute = re.compile(
    r"^(xr<[^>]+>) (and|or|and/or) (xr<[^>]+>)$"
)
re_qual_with_attribute = re.compile(r"^(xr<[^>]+>)$")
re_qual_with_attribute2 = re.compile(r"^nu<([^>]+)> xq<([^>]+)> (xr<[^>]+>)$")
re_qual_with_ctrs = re.compile(r"^(?:(?:xq|nu)<([^>]+)>) (xo<ctr[^>]+>)")
re_qual_with_attribute_xq = re.compile(r"^xq<([^>]+)> xr<([^>]+)>$")
re_qual_with_attribute_lo = re.compile(r"^xq<the> xl<(\w+)> (?:xo|xr)<(\w+)>$")
re_qual_with_object = re.compile(r"^((?:xq<[^>]+> )?ob<[^>]+>)$")

# from and in - applies to zones can take on multiple forms
# from [quantifier] [zone]
# from [quanitifer]? player['s]? zone
# may be followed by a modifier i.e. xm<face amplifier=down>
#re_qual_from = re.compile(r"")

# of - multiple forms
#  1. [quanitifier] [attribute] (includes xo like value, life etc)
#  2. objects i.e. Heartstone (have to check for preceding quantifiers, status)
#  3. possesive i.e. Pilgrim of Virtue
#  4. possessive i.e. Biomancer's Familiar
re_qual_of_attribute = re.compile(
    r"^xq<([^>]+)> (?:xr<([^>]+)>|xo<(life_total|life|mana_cost|mana|value)>)$"
)
re_qual_of_object = re.compile(
    r"^^((?:xq<\w+> )?(?:(?:xs|st)<\w+> )?(?:ob|zn|xp|xo)<[^>]+>)$"
)
re_qual_of_possessive = re.compile(
    r"^((?:xq<[^>]+> )?xp<\w+ suffix=(?:r|'s)> (?:(?:ob|zn|xp|xo)<[^>]+>))$"
)
re_qual_of_possessive2 = re.compile(
    r"^((?:xq<[^>]+> )?ob<[^>]+> (?:.+? )?xp<[^>]+> xc<[^>]+>)$"
)

# TODO: removed that_is, that_are as tags
# that_is/that_are
#  1. that_is [keyword] (with suffix)
#  2. that_is [attribute] (same as with_attribute)
#  3. that_is [not]? on [quantifier] [zone]
#   TODO: looking at Teferi, Mage of Zhalfir] are there different phrasings
#    i.e. in target player's hand
#re_qual_thatis_status = re.compile(r"^xs<([^>]+)>$")
#re_qual_thatis_attribute = re.compile(r"^(cn<not> )?xr<([^>]+) val=([^>]+)>$")
#re_qual_thatis_zone = re.compile(r"^(?:(cn<not>) )?pr<on> (xq<[^>]+> zn<[^>]+>)$")

# other_than - should be an object primarily self i.e. Wormfang Drake but could
#  be other i.e. Haunting Echos
re_qual_otherthan_thing = re.compile(r"^(ob<[^>]+>)$")

####
## KEYWORD/LITUUS ACTION
####

# numbers
re_number = re.compile(r"^nu<([^>]+)>$")
#re_number_vanilla = re.compile(r"^nu<([0-9xyz]+)>$")

# attach 701.3 attach [object] to [object] where the first object is self
re_attach_clause = re.compile(r"^([^\.]+) pr<to> ([^\.]+)$")

# create 701.6 sometimes has a trailing clause named ...
re_create_clause = re.compile(
    r"^([^\.]+?)(?: xa<name suffix=ed> ob<token ref=(\w+)>)?\.?$"
)

# double 701.9 four variations
# 1. p/t - two variations
#   a. [creature]? [power and/or toughness]
#   b. the [power and/or toughness] of [creature]
# 2. life total - [player] life-total
# 3. countters - the number of [counters] on [thing]
# 4. mana - the [amount|value] of [mana-clause]
re_double_clause1 = re.compile(r"^xr<(power)> (and|or) xr<(toughness)>$")
re_double_clause2 = re.compile(r"^([^\.]+) xo<life_total>$")
re_double_clause3 = re.compile(
    r"^xq<the> xo<number> pr<of> ((?:.*? )?xo<ctr(?: [^>]+)?>) pr<on> ([^,|^\.]+)$"
)
re_double_clause4 = re.compile(r"^xq<the> xo<(amount|value)> pr<of> ([^,|^\.]+)$")

# exchange 701.10
# 1. exchange control of [thing] (and [thing])?
# 2. exchange life total [Thing]? life_total (with [Thing])?
re_exchange_ctrl_clause = re.compile(
    r"^xc<control> pr<of> ([^,|^\.]+?)(?: and ([^,|^\.]+))?$"
)
re_exchange_lt_clause = re.compile(
    r"^(?:(.*?) )?(xo<life_total(?: suffix=s)?>)(?: pr<with> (.+))?\.?$"
)

# reveal 701.15
# has multiple forms commonly
#  1. their hand
#  2.
# TODO

# search 701.18
# has the form [zone] for [thing]
re_search_clause = re.compile(r"^((?:[^\.]+ )?zn<[^>]+>) pr<for> ([^\.]+)\.?$")

# tap 701.20
# has the form [thing] (for thing)?
re_tap_clause = re.compile(r"^(?:(.+?) ?)(?:pr<for> ([^\.]+))?\.?$")

# clash 701.22 has the form with [player] (always an opponennt)
re_clash_clause = re.compile(r"^pr<with> ([^\.]+)$")

# vote 701.31 has three forms
#  1. vote for attribute (the votes are in the val attribute)
#  2. vote for token1 or token2 (one or both of the tokens may have been inadverntly
#   tagged. see Lieutenants of the Guard)
#  3. vote for Thing
re_vote_clause1 = re.compile(r"^pr<for> xr<(\w+) val=([^>]+)>$")
re_vote_clause2 = re.compile(r"^pr<for> (.+?) or (.+?)$")
re_vote_clause3 = re.compile(r"^pr<for> ([^\.]+)$")

# meld 701.36 has two forms
#  1. meld them into [object]
#  2. melds with [object]
re_meld_clause1 = re.compile(r"^xo<them> pr<into> (ob<[^>]+>)$")
re_meld_clause2 = re.compile(r"^pr<with> (ob<[^>]+>)$")

# exert 701.38 exert ob [as it attacks]?
re_exert_clause = re.compile(r"^(.+?)(?: pr<as> ([^\.]+))?$")

# related to 'add' mana

# same as chains but for mana (for add)
# matches forms of {X} (and {X}{Y}), {X} or {Y} and {X}, {Y}, or {Z}
re_mana_check = re.compile(r"{[^t|^e|^]+}$")
re_mana_chain = re.compile(
    r"^(?:(xq<[^>]+>) )?"
     r"(?:({[^t|^e|^]+}), )?(?:({[^t|^e|^}]+}),? or )?({[^t|^e|^]+}+)$"
)

# mana phrases of the form
# 1. [quanitifer]? [number] mana [qualifying info]
# 2. [mana] [specifying-clause] - always for each
# 3. an amount of [mana] [clause]
re_nadditional_mana = re.compile(
    r"^(?:(xq<[^>]+>) )?nu<([^>]+)> xo<mana> (pr<(?:of|in)> [^,|\.]+)$"
)
re_mana_trailing = re.compile(r"^((?:xq<[^>]+> )?{[^t|^e|^]+}+) ([^\.]+)\.?$")
re_amount_of_mana = re.compile(
    r"^xq<a> xo<amount_of> ({[^t|^e|^]+}+) ([^\.]+)\.?$"
)
re_that_much_mana = re.compile(
    # TODO: Grand Warlord Radha is very similar
    r"^xq<that> xl<much> ({[^t|^e|^]+}+)(?: ([^\.]+))?\.?$"
)

####
## TEST SPACE
####
