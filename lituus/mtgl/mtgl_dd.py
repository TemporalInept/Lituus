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
__version__ = '0.0.4'
__date__ = 'July 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re

####
## MISCELLANEOUS
####

####
# TAG ID CONSTANTS
####
TID = {
    # entities
    'ob':'mtg-object','xo':'lituus-object','xp':'player','zn':'zone','ef':'effect',
    #actions
    'ka':'keyword-action','xa':'lituus-action','kw':'keyword',
}

####
# PHASE OR STEP
####
# TODO: this needs work for example
#  should turn be considered a phase?
#  should eot be considered a step
MTG_PHASES = [
    'beginning','precombat main','combat','postcombat main','ending','main','turn',
]

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

# complex activated (contain an 'and' or 'or'
# 2. the conjunction operator separates two phrases, the second being a triggered
#  ability i.e. Chaos Moon
re_complex_tgr_check = re.compile(r"^[^,]+,? (and|or) tp<[^>]+> [^\.]+\.?$")
re_complex_tgr = re.compile(
    r"^([^,]+),? (and|or) (tp<[^>]+> [^\.]+)\.?$"
)

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
# Some cards:
#  (Goblin Flotilla) have embedded triggered abilities of the form
#  [When/Whenever/At] [condition] [triggered-ability]
#  (Wildfire Devils) have conjoined conditions
#  [When/Whenever/At] [condition] and|or [When/Whenever/At] [condition] ...
re_tgr_check = re.compile(r"^(tp<\w+>)")
re_tgr_line = re.compile(r"^tp<(\w+)> ([^,|^\.]+), ([^\.]+)(?:\. (.+))?\.?$")
re_embedded_tgr_line = re.compile(r"^tp<([^>+)> ([^\.]+), (tp<[^>]+> [^\.]+)\.?$")
re_conjoined_tgr_condition_line = re.compile(
    r"^(tp<[^>]+> [^,]+) (and|or) (tp<[^>]+> [^,]+), (.+)\.?$"
)

# some cards have additional conditional phrases in the trigger condition
# such as Faerie Miscreant where the trigger condition clause will have the form
# [condition], if [condition]
re_split_tgr_condition = re.compile(r"^(.+), (cn<if> .+)$")

# Delayed Triggered (603.7) "do something at a later time - contains a trigger
# preamble but not usually at the beginning of the ability and end with a turn
# structure. See Prized Amalgam
# For now, look for lines having the form
#  [effect] [when/whenever/at] [condition]
#  where the condition ends with a turn structure
# NOTE: we ensure effect does not cross sentence/clause boundaries
re_delayed_tgr_check = re.compile(r"tp<\w+> (?:.+ )?ts<[^>]+>\.?$")
re_delayed_tgr_clause = re.compile(
    r"^([^,|^\.]+) tp<(\w+)> ((?:[^\.]+ )?ts<[^>]+>)\.?$"
)

# conjunction of phrases (See Giant Oyster)
# These will have a phrase followed by a ", and" and another phrase. Have to check
# that the first phrase does not have commas (or periods). In other words, if
# there are commas preceding a ", and", this is part of a list otherwise, it
# signifies distinct parts
re_conjoined_phrase_dual = re.compile(r"^([^,|^\.]+), and ([^\.]+)$")

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
# For certain cases (Magus of the Mind), we have to graph everything prior to
# the variable and after the variable IOT to return it
re_variable_val = re.compile(
    r"^(.*?)"
    r"(nu<\w>|xr<[^>]+ val=\w>|\w\w<[^>]+ quantity=\w>)"
    r"([^,]*?), where nu<\w> xa<is> ([^\.|,]+?)"
    r"(?=(?:\.|,| and|$))"
)

# mana instantiates have the form (see Spell Rupture)
# {X}, where nu<x> is [instantiation]
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
## KEYWORD ACTIONS (701.2 - 701/43) AND LITUUS ACTIONS
####

# A conjunction of multiple action-clauses. There are three variations:
#  1. An implied subject (namely xp<you>) i.e. Liliana of the Dark Realms
#   [action],? [action], [action], [and|or|and/or] [action]
#  2. A common subject i.e. Assault Suit
#  [thing] [action],? [action], [action], [and|or|and/or] [action]
#  3. Each action clause has a subject i.e. Lazav, the Multifarious
#   [action],? [action], [action], [and|or|and/or] [action]
#  where action = [thing] [action] [action-parameters]
# NOTE: for 1 and 2, we write two distinct regex due to mismatches caused by
#  having an optional thing
# TODO: this assumes that there will never be more than 4 conjoined action clauses
re_conjoined_act_phrase_implied = re.compile(
    r"^(?:((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), )?"
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"(and|or|and/or) "
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?)\.?$"
)
re_conjoined_act_phrase_common = re.compile(
    r"^(?:([^,|^\.]*?) )"
    r"(?:((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), )?"
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"(and|or|and/or) "
    r"((?:xa|ka)<[^>]+>(?: [^,|^\.]+)?)\.?$"
)
re_conjoined_act_phrase_distinct = re.compile(
    r"^(?:([^,|^\.]*?(?:ob|xp|xo)<[^>]+>[^,|^\.]* (?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), )?"
    r"([^,|^\.]*?(?:ob|xp|xo)<[^>]+>[^,|^\.]* (?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"([^,|^\.]*?(?:ob|xp|xo)<[^>]+>[^,|^\.]* (?:xa|ka)<[^>]+>(?: [^,|^\.]+)?), "
    r"(and|or|and/or) "
    r"([^,|^\.]*?(?:ob|xp|xo)<[^>]+>[^,|^\.]* (?:xa|ka)<[^>]+>(?: [^,|^\.]+)?)\.?$"
)

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

# duration/times/sequences
#  [quantifier] [turn-structure] i.e Relentless Raptor
re_quant_duration_clause = re.compile(r"^(xq<[^>]+> ts<\w+>)$")

# keyword or lituus action clause
# TODO: this is not a perfect check but will eliminate most none action clauses
re_act_clause_check = re.compile(
    r"((?:xa|ka|kw)<[^>]+>|xp<[^>]+> xc<(?:own|control)(?: suffix=s)?>)"
)

## Simple (two) conjunctions - three variations

# 1. a conjunction of predicates (possibly negated) with a common (or implied)
# subject and parameters i.e. Twiddle
#  [thing] [predicate1] [not1]? and|or [predicate2] [not]? [parameters]?
# NOTE: for now we are assuming that there will always be a subject but parameters
#  may be empty
# TODO: handle stuff like Changleing Outcast "can't block and can't be blocked"
re_conjoined_act_predicate = re.compile(
    r"^([^,|^\.]+?) "
    r"((?:(?:xa|ka)<[^>]+>)(?: cn<not>)?){1} or ((?:(?:xa|ka)<[^>]+>)(?: cn<not>)?){1}"
    r"(?: ([^,|^\.]+))?\.?$"
)

# 1.b where the subjects are different for each action i.e Abyssal Persecuter
#  [thing] [action] and [thing] [action]
# NOTE:
#  1. this is a misnomer as both things could the same
#  2. the first action clause may have an implied subject but we force the second
#   action clause to have a subject
re_conjoined_act_clause_unique = re.compile(
    r"^([^,|^\.]*?(?:xa|ka|kw)<[^>]+>[^,|^\.]*)? (and|or) "
    r"([^,|^\.]*(?:ob|xp|xo)<[^>]+>[^,|^\.]* (?:xa|ka|kw)<[^>]+>(?: [^,|^\.]+)?)\.?$"
)

# conjunction of actions
# 1.c where the subject is the same and there are exactly two actions
#  i.e. Lost Auramancers
#    [thing] [action] and [action]
re_conjoined_act_clause_common = re.compile(
    r"^(?:([^,|^\.]*?) )?((?:xa|ka|kw)<[^>]+>(?: [^,|^\.]+)?) "
    r"(and|or|and/or) ((?:xa|ka|kw)<[^>]+>(?: [^,|^\.]+)?)\.?$"
)

#  2. singular
#   [thing]? [can|do]? [conditional]? [action-word] [action-parameters]
#  NOTE: have to make sure that the action(s) are not preceded by another action
re_action_clause = re.compile(
    r"^(?:([^,|^\.]+?) )?(?:xa<(can|do)[^>]*> )?(?:cn<(not)> )?"
     r"((?:xa|ka|kw)<[^>]+>)(?: ([^,|^\.]+))?\.?$"
)

## 2.a tap or untap is a special phrasing i.e. Twiddle
#re_tq_action_clause = re.compile(
#    r"^(?:([^,|^\.]*?) )?(ka<tap> or ka<untap>) ([^,|^\.]+)\.?$"
#)

# 2.c do the same is another special phrasing i.e. Guild Fued (only 5 cards as
# of IKO)
# [player]? do the same [preposition] [thing]
re_do_the_same_action_clause = re.compile(
    r"^(?:([^,|^\.]*xp<[^>]+>) )?xa<do[^>]*> xq<the∧same> pr<([^>]+)> ([^,|^\.]+)\.?$"
)

#  3. an exception is control/own phrases of the form i.e. Synod Centurion
#   [player] [own|control] [clause]
#  will also be treated as action clause. NOTE: IOT not match "you control" and
#  the like, requires at least one character following the own/control tag
# TODO: relook at this after changing own|control tagging
re_action_ply_poss = re.compile(
    r"^((?:xq<[^>]+> )?(?:xs<[^>]+> )?xp<[^>]+>) "
     r"xc<(own|control)(?: suffix=s)?>(?: ([^\.]+))\.?$"
)

# action word can be a single action word or preceded by not or can
# the only card I found with a negated action is Escaped Shapeshifter
re_action_word = re.compile(r"(?:([^>]+) )?((?:xa|ka|kw)<[^>]+>)")

####
## REPLACEMENT EFFECTS (614)
####

## SEQUENCE WOULD CLAUSE
# next time ... this turn ... replacement effect phrasing of the form
# [time] [thing] would [action] [phase], [action] instead?
# this may be replated to
#  damage replacement i.e. Awe Strike or Aegis of Honor
#  other i.e. Words of Worship
# and may be followed by an optional instead
re_repl_time_turn_check = re.compile(r"^[^,]+ sq<\w+>.+cn<would>.+ts<\w+>,")
re_repl_time_turn = re.compile(
    r"^([^,|^\.]+sq<(?:\w+)>) ([^,|^\.]+) cn<would> ([^,|^\.]+) ([^,|^\.]+ts<\w+>), "
     r"([^,|^\.]+?)(?: (cn<instead>))?\.?$"
)

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
# I cannot handle these by RegEx alone as the condition and replacement are
# separated by an action word
re_that_would_instead = re.compile(
    r"^([^,|\.]+) xq<that> cn<would> (.+) cn<instead>\.?$"
)

# that would instead variant i.e. False Dawn
# [sequence] [thing] [action (original)] instead [action (new)]
re_seq_that_would_instead = re.compile(
    r"^([^,|\.]+), (.+) xq<that> cn<would> ([^\.]+) cn<instead> ([^\.]+)\.?$"
)

# may instead (limited replacement - have only seen 3 i.e. Abundance
# if [player] would [action], [player] may instead [action]
re_if_may_instead = re.compile(
    r"^cn<if> (.+) cn<would> ([^,]+), (.+) cn<may> cn<instead> ([^\.]+)\.?$"
)

# if instead of i.e. Pale Moon
#   if [action], [replacement] instead of [original]
re_if_instead_of = re.compile(
    r"^(cn<if> .+), (.+) cn<instead> pr<of> ([^\.]+)\.?$"
)

# instead of if i.e. Caravan Vigil
#  [replacement] instead of [orginal] [conditional-phrase]
re_instead_of_if = re.compile(
    r"^([^,|\.]+) cn<instead> pr<of> (.+) (cn<if> [^\.]+)\.?$"
)

# instead of i.e. Feather, the Redeemed
#  [replacement] instead of [original]
# NOTE: these do not have a preceeding if/would
re_instead_of = re.compile(r"^([^,|\.]+) cn<instead> pr<of> ([^\.]+)\.?$")

# if instead i.e. Cleansing Meditation
#   if [event/condition] instead [replacement].
# the instead comes between the condition and the replacement
re_if_instead = re.compile(r"^cn<if> (.+) cn<instead> ([^\.]+)\.?$")

# if instead fence i.e. Nyxbloom Ancient
#   if [event/condition], [replacement] instead
re_if_instead_fence = re.compile(r"^cn<if> (.+), (.+) cn<instead>\.?$")

# instead if i.e. Crown of Empires
#  [replacement] instead if [condition]
# the condition and replacement are switched
re_instead_if = re.compile(r"^([^,|\.]+) cn<instead> cn<if> ([^\.]+)\.?$")

## SKIP CLAUSES (614.1b)
# skip clauses i.e. Stasis (Note as of IKO, I found 49) have the form
#  [player]? skip(s) [phase/step]
# where if player is not present there is an implied 'you'
# Additionaly some cards (4 total as of IKO) i.e. Fasting include an optional 'may'
re_skip = re.compile(r"^(?:(.+?) )?(?:cn<(may)> )?xa<skip[^>]*> ([^\.]+)\.?$")

## ENTERS THE BATTLEFIELD CLAUSES (614.1c)
# Permanent enters the battlefield with ...
# As Permanent enters the battlefield ...
# Permanent enters the battlefield as ...
re_etb_repl_check = re.compile(r"xa<etb(?: suffix=s)?>")

# Permanent enters the battlefield with ... i.e. Pentavus have the form
#  [permanent] enters the battlefield with [counters]
# these are all counters
re_etb_with = re.compile(r"^([^,|\.]+) xa<etb(?: suffix=s)?> pr<with> ([^\.]+)\.?$")

# As permanent enters the battlefield ... i.e. Sewer Nemesis have the form
#  as [thing] enters the battlefield, [event]
re_as_etb = re.compile(r"^pr<as> ([^,|\.]+) (xa<etb(?: suffix=s)?>), ([^\.]+)\.?$")

# Permanent enters the battlefield as ... i.e. Clone
#  [Player may have]? [thing] enters the battlelfield as [thing]
re_etb_as = re.compile(
    r"^(?:([^,|\.]+) cn<may> xa<have> )?"
     r"([^,|\.]+) xa<etb(?: suffix=s)?> pr<as> ([^\.]+)\.?$"
)

## ENTERS THE BATTLEFIELD CLAUSES (614.1d) - continuous effects
# Permanent enters the battlefield ...
#  Status Jungle Hollow (statement enters tapped)
#  Effect Gather Specimens
# Objects enter the battlefield ...
#  NOTE: have to assume that after above, all remaining ETB fit this
re_etb_status = re.compile(r"^([^,|\.]+) xa<etb(?: suffix=s)?> st<([^>]+)>\.?$")
re_etb_1d = re.compile(r"^([^,|\.]+ xa<etb(?: suffix=s)?>)(?: ([^\.]+))?\.?$")

## TURNED FACE UP (614.1e)
# As Permanent is turned face up i.e. Gift of Doom
re_turn_up_check = re.compile(r"xa<turn suffix=ed> xm<face amplifier=up>")
re_turn_up = re.compile(
    r"^pr<as> (.+ xa<is> xa<turn suffix=ed> xm<face amplifier=up>), ([^\.]+)\.?$"
)

## (614.2) applying to damage from a source
# NOTE: some of these have already been handled during graphing of would-instead
# similar to 'instead' but is a replacement under 614.2 i.e. Sphere of Purity
# this will catch regenerate i.e. Mossbridge Troll as well as prevention
# if [source] would [old], [new]
re_repl_dmg_check = re.compile(r"(?:ef<[^>]*damage[^>]*>|ka<regenerate>)")
re_repl_dmg = re.compile(r"^cn<if> (.+) cn<would> (.+), (.+)\.?$")

# and (615) Prevention Effects
#  Prevention effects will start with 'prevent', contain damage and will have a
#   target and/or source having the form
#  prevent [damage] (that would be dealt to [target)?
#   [sequence]? ([except]? by [source])?
# Examples:
# both target and source are Comeuppance (w/ sequence) and Uncle Istavn (w/o sequence)
# only target Abuna Acolyte
# neither target nor source see Revealing Wind
# except by see Insprie Awe (this is the only one I've seen
re_prevent_dmg = re.compile(
    r"^xa<prevent> ([^,|^\.]*ef<[^>]*damage[^>]*>)"
     r" xq<that> cn<would> xa<be> xa<deal[^>]*>"
     r"(?: pr<to> ([^,|^\.]+?))?"
     r"(?: ((?:xq|sq)<[^>]+> ts<[^>]+>))?"
     r"(?: (cn<except> )?pr<by> ([^,|^\.]+))?\.?$"
)

# variation where target and source are the same i.e. Moonlight Geist has the form
#  prevent [damage] that would be dealt to and dealt by [thing] [sequence]?
re_prevent_dmg2 = re.compile(
    r"^xa<prevent> ([^,|^\.]*ef<[^>]*damage[^>]*>)"
     r" xq<that> cn<would> xa<be> xa<deal[^>]+> pr<to> and xa<deal[^>]+> pr<by>"
     r" ([^,|^\.]+?)(?: ((?:xq|sq)<[^>]+> ts<[^>]+>))?\.?$"
)

# variation on wording that may or may not have a target
#  Refraction Trap has a target
#  Guard Dogs does not
#  prevent [damage] [source] would [action] [sequence]?
re_prevent_dmg3 = re.compile(
    r"^xa<prevent> ([^,|^\.]*ef<[^>]*damage[^>]*>)(?: xq<that[^>]*>)? (.+)"
    r" cn<would> xa<deal[^>]*>(?: pr<to> (.+?))?"
    r"(?: ((?:xq|sq)<[^>]+> ts<[^>]+>))?\.?$"
)

# variation to prevent damage to target only, see Angel of Salvation has the form
# prevent [damage] that would be dealt [sequence]? to [target]
re_prevent_dmg_tgt = re.compile(
    r"^xa<prevent> ([^,|^\.]+?) xq<that> cn<would> xa<be> xa<deal[^>]*>"
     r"(?: ((?:xq|sq)<[^>]+> ts<[^>]+>))? pr<to> ([^,|^\.]+)\.?$"
)

# variation to prevent damage by source only, see Barbed Wire has the form
# prevent [damage] that would be dealt by [source] [sequence]
re_prevent_dmg_src = re.compile(
    r"^xa<prevent> ([^,|^\.]+?) xq<that> cn<would> xa<be> xa<deal[^>]*> "
     r"pr<by> ([^,|^\.]+) ((?:xq|sq)<[^>]+> ts<[^>]+>)\.?$"
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
#  other i.e. Sivvi's Valoryu76
re_action_apc = re.compile(
    r"^(?:cn<if> (.+), )?([^,]+) cn<may> ([^,]+) cn<rather_than> (xa<pay> [^\.]+)\.$"
)

# alternate phrasing found in three cards (Skyshroud Cutter, Reverent Silence &
# Invigorate).
#  if [condition], rather than pay self's mana cost you may [action].
# this is alternate phrasing of re_action_apc and always has a condition
re_alt_action_apc = re.compile(
    r"^cn<if> (.+), cn<rather_than> (xa<pay> [^,]+), (xp<you>) cn<may> ([^\.]+)\.?$"
)

# two alternate phrasing that do not contain a conditional
#  rather than pay [cost], [player] may [action] see Dream Halls
re_rather_than_may_apc = re.compile(
    r"^cn<rather_than> (xa<pay> [^,]+), ([^\.]+) cn<may> ([^\.]+)\.?$"
)

# see i.e. Scourge of Nel Toth
# [player] may [action] pr<by> [alt-cost] rather than [cost]
re_may_rather_than_apc = re.compile(
    r"^([^,]+) cn<may> ([^,]+) pr<by> (xa<pay[^>]*> [^,]+) "
     r"cn<rather_than> (xa<pay[^>]*> [^,]+)\.?$"
)

# 3rd alternate phrasing found (so far only in Bolas's Citadel)
#  if [player] [cond], [apc] rather than [cost]
# These are not optional apcs
re_rather_than_mand_apc = re.compile(
    r"^cn<if> (.*xp<[^>]+>) (.+), "
     r"(xa<pay> [^,]+) cn<rather_than> (xa<pay> [^,]+)\.?$"
)

# if [condition], [you may cast object] without [paying its mana cost] i.e. Massacre
# these are all condition based
re_cast_apc_nocost = re.compile(
    r"^cn<if> ([^,]+), ([^,]+) cn<may> ([^,]+) pr<without> ([^.]+)\.?$"
)

## ADDITIONAL COSTS
# (mentioned throughout but phrased in 604.5 "As an additional cost to cast..."
# As an additional cost to cast [thing], [add-cost] see Abjure
re_add_cost_check = re.compile(r"xq<a∧additional> xo<cost>")
re_add_cost = re.compile(
    r"^pr<as> xq<a∧additional> xo<cost> ka<cast prefix=to> ([^,]+), ([^\.]+)\.?$"
)

## MODAL PHRASES
# (700.2) modal phrases i.e. Charming Prince have two or more options in a bulleted
# list & have the form
#  choose [number] —(•[choice])+
# And, 700.2d defines modal spells allowing players to the same mode more than
# once, these will have the phrase “You may choose the same mode more than once.”
# See Mystic Confluence and have the form:
#   choose [operator]? [number]. [Instructions] (•[choice])+
# See Vindictive Lich for an exception where the instructions differ and the number
# includes an operator
# NOTE: Some cards i.e. Arful Takedown have the form:
#  choose [number] or both. [Instructions] (•[choice])+
re_modal_check = re.compile(r"^xa<choose> nu<([^>]+)>.+•")
re_modal_phrase = re.compile(r"^xa<choose> nu<([^>]+)>(?: or xq<(both)> )?—([^\.]+)\.?$")
re_modal_phrase_instr = re.compile(r"^xa<choose> nu<([^>]+)>\. ([^•]+) ([^\.]+)\.?$")
re_opt_delim = re.compile(r" ?•")

## LEVELER PHRASES
# (710.2a) (NOTE: the form as specified in 710.2a has [Abilities] [P/T] whereas
# the oracle text has [P/T] [Abilities]
# Level lines consist of one or more level clauses each having the form:
#  •[level symbol] [P/T]? [Abilities]
# see Enclave Cryptologist
re_lvl_up_check = re.compile(r"^•xo<level>")
re_lvl_up_lvl = re.compile(
    r"^xo<level> nu<([^>]+)>(\+|-)(?:nu<([^>]+)>)?"
     r"(?: xr<p/t val=(\d+/\d+)>)?(?: (.+))?$"
)

## SAGA PHRASES
# (714.2)
re_saga_check = re.compile(r"^i.* — ") # there is a hanging newline
re_chapter_delim = re.compile(r"(i[iv]*(?:, i[iv]+)*) — ")

####
## LITUUS PHRASE TYPES
####

# sequences
#  Checks - any line with a sequence tag will be considered a sequence
re_sequence_check = re.compile(r"(?:ts|sq)<[^>]+>")

# 'then' flow of actions has the forms
# [action]?,? then [action] again?
#  Roalesk, Apex Hybrid has a terminating 'again'
#  Barishi is a action-then-action w/o comma, Entomb is a action-then-action w/ comma
#  Endless Horizons does not have an initial action
re_seq_then = re.compile(
    r"^(?:([^,|^\.]+),? )?sq<then> ([^,|^\.]+?)(?: (sq<again>))?\.?$"
)

# dual - [sequence] [clause], [sequence] [clause] i.e. Temple Elder
# NOTE:
#  1. there are no effects associated with these sequences
#  2. these are generally of the form "during your turn, before attackers are
#  declared" but we will generalize as much as possible (see Blaze of Glory)
re_seq_dual = re.compile(r"^sq<([^>]+)> ([^,]+),? sq<([^>]+)> ([^\.]+)\.?$")

# conjoined distinct sequence phrases
# [clause] [turn structure],? and [clause] [turn structure]
#  where each turn structure has the form:
#  [quantifier] [turn-structure] or [sequence] [turn-structure]
# There are two cases:
#  1. the turn-structures is the same i.e. Battlegate Mimic
#  2. the turn-structures are different i.e. Veil of Secrecy
re_conjoined_seq = re.compile(
    r"^([^,|^\.]+) ((?:xq|sq)<[^>]+> ts<[^>]+>),? and "
     r"([^,|^\.]+) ((?:xq|sq)<[^>]+> ts<[^>]+>)\.?$"
)

# for the first time each turn i.e. Vengeful Warchief has the form
# [clause] for the first time each turn
# TODO: do we need to changes this for Skull Storm "for each time"
re_seq_first_time = re.compile(
    r"^([^,|^\.]+) pr<for> xq<the∧first> sq<time> (xq<each> ts<turn>)\.?$"
)

# until phase, effect have the form i.e. Volrath, the Shapeshifter
# until [phase], [effect]
re_seq_until_phase = re.compile(r"sq<(until)> ([^,|^\.]*ts<[^>]+>), ([^,|^\.]+)")

# during, as-long-as, until, after have the form
# [effect] for? [seq-word] [condition]
#  NOTE: for will only appear in some as-long-as phrasing
# during: Callous Oppressor
# as-long-as: Angelic Field
# until: Rage Weaver
# after: Paradox Haze
re_seq_effect_cond = re.compile(
    r"^(?:([^,|^\.]+) )?(?:pr<for> )?sq<(during|as_long_as|until|after)> ([^,|^\.]+)$"
)

# terminal phases i.e. beginning of phase or end of phase
# the? [beginning|end] of [phase]
# NOTE: these are standalone sequence conditions, generally part of a triggered
#  ability
re_seq_terminal_phase = re.compile(
    r"^(?:xq<the> )?sq<(beginning|end)> pr<of> ([^,|^\.]*ts<[^>]+>)$"
)

# clause turn-structure have the form
#  [effect] [turn-structure] where turn-structure is simple [quanitifier] [phase]
# NOTE: in some cases, there will be no effect see Interdict
re_seq_phase_end = re.compile(r"^(?:([^,|^\.]+) )?(xq<[^>]+> ts<[^>]+>)$")

##
# optionals, conditions and restrictions
re_optional_check = re.compile(r"cn<may>")

# conjoined optionals i.e. Hostage Taker
#  [optional] and|or [optional]
re_conjoined_optional_phrase = re.compile(
    r"^((?:[^,|\.]+)?xp<[^>]+>(?:[^,|\.]+)? cn<may> [^,|\.]+)"
    r", (and|or|and/or) "
    r"((?:[^,|\.]+)?xp<[^>]+>(?:[^,|\.]+)? cn<may> [^,|\.]+)\.?$"
)

# [player] may [action] as though [action] [if [condition]]? i.e. Lone Wolf
re_may_as_though = re.compile(
    r"^((?:[^,|\.]+ )?xp<[^>]+>) cn<may> (.+) pr<as_though> ([^\.]+)\.?$"
)

# contains 'may' [player] may [action] i.e. Ad Nauseam
#  NOTE: This also covers [player] may have [effect] such as Browbeat
re_player_may = re.compile(
    r"^((?:[^,|\.]+)?xp<[^>]+>(?:[^,|\.]+)?) "
     r"cn<may> ([x|k]a<\w+>(?:[^\.]+))\.?$"
)

# starts with if

# a) if [thing] can|do [not]?, [action] i.e. Decree of Justice, Brain Pry
#  if [player] can|do not?, [effect]
# TODO:
#   Gilded drake is an exception in that it has "do not or can not" and it has
#   a action clause prior to the comma
# NOTE:
#  1. in almost all cases, the cando contition applies to a previous clause
#  2. this is a subset of re_if_cond_act but it requires special handling
#  3. In almost all cases the thing is a player however sometimes (Condundrum
#   Sphinx) it is an object
re_if_thing_cando = re.compile(
    r"^cn<if> ([^,|^\.]*(?:ob|xo|xp)<[^>]+>) "
     r"xa<(can|do)[^>]*>(?: cn<(not)>)?, ([^\.]+)\.?$"
)

# b) if-able phrasings
#  b.1 ends with "if able" i.e. Monstrous Carabid In these cases, the condition
#  is 'if able'
#   [effect] if able
re_if_able = re.compile(r"^([^,|^\.]+) cn<if> able\.?$")

# b.2 if able unless is in the middle i.e. Reckless Cohort
re_if_able_unless = re.compile(
    r"^([^,|^\.]+) cn<if> able cn<unless> ([^,|^\.]+)\.?$"
)

# c) if [condition], [action] i.e Ordeal of Thassa
re_if_cond_act = re.compile(r"^cn<if> ([^,|^\.]+), ([^\.]+)\.?$")

# d) if [condition], [action]. otherwise, [action] i.e Advice from the Fae
#   NOTE: we need to catch this prior to lines being broken down into sentences
#   so we catch previous sentences if present
re_if_otherwise = re.compile(
    r"^(?:(.+?\.) )?cn<if> ([^,|^\.]+), ([^\.]+)\. "
     r"cn<otherwise>, ([^\.]+)\.?(?: ([^\.]+)\.?)?$"
)

# e) [action] if [condition] i.e. Ghastly Demise
re_act_if_cond = re.compile(r"^([^,|^\.]+),? cn<if> ([^,|\.]+)\.?$")

# f) hanging if would
re_if_would = re.compile(r"^cn<if> ([^,|^\.]+) cn<would> ([^,|^\.]+)\.?$")

# g) hanging if (fragmentary, that is, there is no effect) these are generally
#  part of a higher level construct such as a triggered effect i.e. Nim Abomination
#   if [condition]
re_if_cond = re.compile(r"^cn<if> ([^\.]+)\.?$")

# contains unless
# The rules only mention unless in 722.6 "[A] unless [B]" However going through
# them while B appears to always be a condition there are five flavors
# regarding A, depending on the context.
#  1. [thing] cannot [action] unless [condition] i.e. Okk
#  2. [action] unless [condition] i.e. Bog Elemental
#  3. [status] unless [condition] i.e. Bountiful Promenade
#  4. [player] may [action] unless [condition] i.e Mystic Remora (only 5 of these)
# NOTE: unless is generally part of a clause that is part of a phrase therefore
#  we do not want to grab anything that extends to the left past a clause (",")
#  or sentence (".") boundary
re_action_unless = re.compile(
    r"^((?:[^,|^\.]+ )?[kx]a<[^>]+>.+) cn<unless> ([^,|\.]+)\.?$"
)

# standalone otherwise i.e. primal empathy
re_otherwise = re.compile(r"^cn<otherwise>, ([^\.]+)\.?$")

# for each condition see
#  1. for each [condition], [action] i.e. From the Ashes
#  2. [action] for each [condition] i.e. Gnaw to the Bone
# NOTE: we check the quantifier for chains
re_for_each_cond_start = re.compile(
    r"pr<for> xq<each(?:[∧∨⊕]([^>]+))?> ([^,|^\.]+), "
    r"([^\.]+)\.?$"
)
re_for_each_cond_mid = re.compile(
    r"^([^,|^\.]+) pr<for> xq<each(?:[∧∨⊕]([^>]+))?> ([^\.]+)\.?$"
)

# generic would/could phrases
#  See Dimir Guildmange for a could, Rock Hydra for a would
#  [thing] that? would|could not? [action]
re_gen_cond = re.compile(
    r"^([^,|^\.]+?) (?:xq<(that)> )?cn<([wc]ould)> (?:cn<(not)> )?([^,|\.]+)\.?$"
)

## RESTRICTION PHRASES

# but condition restrictions i.e. Haakon
# [action],? but [condition-word] [restriction]
re_restriction_but = re.compile(r"^(.+?),? but cn<(\w+)> ([^,|\.]+)\.?$")

# can/do not
# two forms
#  1. [thing] can/do not [action] unless [condition] i.e. Howlpack Wolf
# these are a restriction with a condition
#  2. [thing] that would [action] can/do not [action] i.e. Questing Beast
#  3. [thing] can/do not [action] i.e. Suleiman's Legacy
# these are blanket restriction
re_restriction_cando_check = re.compile(r"xa<(?:can|do)> cn<not>")
re_restriction_cando_unless = re.compile(
    r"^([^,|^\.]+) xa<(can|do)> cn<not> ([kx]a<[^>]+>.*) cn<unless> ([^,|\.]+)\.?$"
)
re_restriction_would_cando = re.compile(
    r"^([^,|^\.]+) xq<that> cn<would> ([^,|\.]+) xa<(can|do)> cn<not> ([^,|\.]+)\.?$"
)
re_restriction_cando = re.compile( # TODO: NOT BEING USD
    r"^([^,|^\.]+) xa<(can|do)> cn<not> ([kx]a<[^>]+>.*)\.?$"
)

# some restrictions have a conjunction of only restrictions with the basic form
#  [action] only|only_if [clause] and only|only_if [clause]
# i.e. Security Detail
#  NOTE: only 16 cards at time of IKO
# for each of the clauses, have to look at the condition type. If it is only
#  the clause is timing related. If it is only_if, the clause is a condition
# TODO: Capricopian is an exception to the pattern and is of the form
#  only [player] may [action] and only during [timing]
# I think only ands are present but just case check for 'or' and 'and/or'
re_conjoined_restriction_only = re.compile(
    r"^([^,|\.]+) (cn<(?:only|only_if)> [^,|^\.]+) (and|or|and/or) "
     r"(cn<(?:only|only_if)> [^,|^\.]+)\.?"
)

# may-only see Mystic Barrier has the form
# [thing] may [action] only [restriction]
re_restriction_may_only = re.compile(
    r"^([^,|\.]+) cn<may> ([^,|\.]+) cn<only> ([^,|\.]+)\.?$"
)

# timing restrictions ...

# [action] only any time [timing]
#  see Dimir Guildmage, see Teferi Mage of Zhalfir for a restriction on opponents
# NOTE: the timing clause contains a 'could' which will be graphed as a conditional
re_restriction_anytime = re.compile(
    r"^(?:([^,|\.]+) )?cn<only> xq<any> sq<time> ([^,|\.]+)\.?$"
)

# [action] only during [phase/step] i.e. Aven Auger
re_restriction_phase = re.compile(
    r"^(?:([^,|\.]+) )?cn<only> (sq<[^>]+> [^,|\.]*ts<[^>]+>)\.?$"
)

# [action] only [number] times [phase/step]? i.e. Phyrexian Battleflies
# Variant does not have a phase/step i.e. Stalking Leonin
re_restriction_number = re.compile(
    "^(?:([^,|\.]+) )?cn<only> nu<([^>]+)> sq<time(?:[^>]+)?>"
     "(?: ((?:[^,|\.]+ )?ts<[^>]+>))?\.?$"
)

# Generic only i.e. Temple Elder these may fit one of the above but include
#  additional phrases, clauses etc
#  [action] only [condition]
#  NOTE: as in Temple Elder, we do not want to break on commas
re_restriction_only = re.compile(r"^([^\.]+) cn<only> ([^\.]+)\.?$")

# condition restrictions only_if i.e. Tainted Isle
#  [action] only_if [condition]
re_only_if = re.compile(r"^(?:([^,|\.]+) )?cn<only_if> ([^,|\.]+)\.?$")

# Exception: contains except - the opposite of a restriction, it provides
# additional abilities, characteristics or exclusions from an action
# Two variations
#  [action], except [exception] i.e. Lazav, the Multifarious
#  [action], except for [exception] i.e. Season of the Witch
re_exception_check = re.compile(r"cn<except>")
re_exception_phrase = re.compile(r"(.+?), cn<except> ([^\.]+)\.?$")
re_exclusion_phrase = re.compile(r"(?:([^,|^\.]+),? )?cn<except> pr<for> ([^\.]+)\.?$")

####
## CLAUSES
####

# TODO: i don't like doing these twice but unlike sequence phrases, these are
#  standalone, there are no preceding or following structures
re_sequence_clause_check = re.compile(r"^sq<[^>]+>")
re_sequence_clause = re.compile(r"^sq<([^>]+)> ([^,|^\.]+)$")

# a 'when' clause i.e. 'before', 'after', 'during', 'until' condition
re_seq_when_clause = re.compile(r"^sq<(before|after|during|until)> ([^,|^\.]+)\.?$")

# turn structure - similar to graphing of things
# [player's]? [turn-structure]
#  i.e eot, target player's turn, your turn
re_ts_check = re.compile(r"ts<[^>]+>$") # ends with a turn structure

# basic turn structure has the form
# [player's]? [quanitifier]? [phase]
#  Temple's Elder has a player phase form, Angel's Grace has a only a phase
# NOTE: assuming player is basic at most a quanitifier or status and then a
#  possessive player
re_turn_structure_basic = re.compile(
    r"^(?:((?:(?:xq|xs)<[^>]+> )?xp<[^>]+>) )?(?:xq<([^>]+)> )?(ts<[^>]+>)$"
)

# possessive consecutive phases have the form
# [quantifier] turns [step] i.e. Scarab of the Unseen
re_turn_structure_step = re.compile(
    r"^(xq<[^>]+> ts<turn suffix='s>) (ts<[^>]+>)$"
)

# player's step has the form
# [step] on [player's] [phase] i.e. Battering Ram
re_turn_structure_player_step = re.compile(
    r"^((?:xq<[^>]+> )?ts<[^>]+>) pr<on> ([^,|^\.]*xp<[^>]+>) ([^,|^\.]*ts<[^>]+>)$"
)

####
## PHASES/STEPS
####

# NOTE: these are very similar to the graphing of things and we could consider the
# phases/steps graphed here as 'things' i.e. your turn. Has the forms
#  1. [number] time(s) [phase] i.e. Mairsil, the Pretender
#  2. [time] [phase]
#  3. [thing]? [phase/step] i.e Apathy
#   NOTE: have to make sure that a Thing is present in the first match
re_phase_clause_check = re.compile(r"ts<([^>]+)>$")
re_num_times_phase = re.compile(
    r"^nu<([^>]+)> sq<(time[^>]*)> (?:xq<([^>]+)> )?ts<([^>]+)>$"
)
re_time_phase_clause = re.compile(
    r"^xq<([^>]+)> sq<([^>]+)> (?:xq<([^>]+)> )?ts<([^>]+)>$"
)
re_thing_phase_clause = re.compile(
    r"(?:(.*?(?:ob|xp|xo|zn|ef)<[^>]+>.*?) )?(?:xq<([^>]+)> )?ts<([^>]+)>$"
)

####
## THINGS
####

# find phrases of the form: i.e. Wintermoor Commander
#  [quanitifier]? [status]? [thing's] [attribute]
# in this case, the attribute is the 'subject' or the thing
re_reified_attribute = re.compile(
    r"^(?:(xq<[^>]+>) )?(?:(xs<[^>]+>) )?"
     r"((?:xo|ob)<[^>]+ (?:[^>]*suffix=(?:'s)[^>]*)>) xr<([^>]+)>\.?$"
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
    r"((?:[^\.]*?)?(?:ob|xp|xo|zn|ef)<[^>]+>)"
    r"(?: ((?:xq<[^>]+> )?(?:(?:st|xs)<[^>]+> )?"
     r"xp<[^>]+> (?:xa<do[^>]*> cn<not> )?xc<[^>]+>))?"
    r"(?: ((?:pr|xq)<(?:with|without|from|of|other_than|that|at)> "
     r"[^\.|^,]+?))?"
    r"(?: ((?:xq<[^>]+> )?(?:(?:st|xs)<[^>]+> )?"
     r"xp<[^>]+> (?:xa<do[^>]*> cn<not> )?xc<[^>]+>))?"
    r"\.?$"
)
re_qst1 = re.compile(
    r"^(?:nu<([^>]+)> )?(?:xq<([^>]+)> )?(?:(?:xs|st)<([^>]+)> )?"
    r"((?:[^\.]*?)?(?:ob|xp|xo|zn|ef)<[^>]+>)(?! (?:or|and|and/or))(?: ([^\.]+))?\.?$"
)
re_qst2 = re.compile(
    r"^(?:nu<([^>]+)> )?"
    r"(?:xq<([^>]+)> )?"
    r"(?:(?:xs|st)<([^>]+)> )?"
    r"((?:ob|xp|xo|zn|ef)<[^>]+>)"
    r"(?: ([^\.]+))?\.?$"
)

# handles 1 to 3 things # TODO: not strict enough
re_thing_clause = re.compile(
    r"^(?:((?:nu<[^>]+> )?(?:xq<[^>]+> )?(?:(?:xs|st)<[^>]+> )?"
     r"(?:ob|xp|xo|zn|ef)<[^>]+>(?: [^\.]+?)?), )?"
    r"(?:((?:nu<[^>]+> )?(?:xq<[^>]+> )?(?:(?:xs|st)<[^>]+> )?"
     r"(?:ob|xp|xo|zn|ef)<[^>]+>(?: [^\.]+?)?)"
    r",? (and|or|and/or) )?"
    r"((?:nu<[^>]+> )?(?:xq<[^>]+> )?(?:(?:xs|st)<[^>]+> )?"
     r"(?:ob|xp|xo|zn|ef)<[^>]+>(?: [^\.]+?)?)\.?$"
)

# finds consecutive things to determine if they are possessive
#  TODO: need to determine if we only need to check for a suffix of "'s" or "r"
#   in the first thing(s)
#  NOTE: in some cases we have three consecutive things (see Trial of Ambition)
#   it's owner's hand so check for three with first being optional and ignored
re_consecutive_things = re.compile(
    r"^(?:xq<(\w+?)> )?(?:((?:ob|xp|xo|zn|ef)<[^>]+>) )?"
     r"((?:ob|xp|xo|zn|ef)<[^>]+>) ((?:ob|xp|xo|zn|ef)<[^>]+>)$"
)

# Qualifying clauses for example with flying

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
    r"^((?:xq<[^>]+> )?xp<\w+ suffix=(?:'s)> (?:(?:ob|zn|xp|xo)<[^>]+>))$"
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

# attribute clauses - two forms (NOTE: we consider life-total in some cases to
# be an attribute of a player
re_attr_clause_check = re.compile(r"(xo<life_total>|xr<[^>]+>)")

# [thing]'s [attribute] i.e. Okaun, Eye of Chaos
re_things_attr = re.compile(
    r"^(.*(?:ob|xp|xo)<[^>]+>) (?:(?:xr|xo)<([^>]+)> (and|or) )?(?:xr|xo)<([^>]+)>$"
)

# [attribute] of [thing] i.e. God-Eternal Rhonas
re_attr_of_thing = re.compile(
    r"^(?:.*)?(?:(?:xr|xo)<([^>]+)> (and|or) )?((?:xr|xo)<[^>]+>) pr<of> ([^\.]+)\.?$"
)

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

# double 701.9 three variations
# attribute of a thing (to include life_total) is handled by re_attr_clause

# the number of [counters] on [thing], see Primordial Hydra, Gilder Bairn
re_double_ctr_clause = re.compile(
    r"^xq<the> xo<number> pr<of> (xq<each>.*? )?(xo<ctr[^>]*>) pr<on> ([^,|^\.]+)$"
)

# mana - the [amount|value] of [mana-clause] see Unbound Flourishing
re_double_mana_clause = re.compile(
    r"^xq<the> xo<(amount|value)> pr<of> ([^,|^\.]+)$"
)

# exchange 701.10
# 1. exchange control of [thing] (and [thing])? i.e. Spawnbroker
# 2. exchange life total [Thing]? life_total (with [Thing])? i.e. Magus of the Mirror
re_exchange_ctrl_clause = re.compile(
    r"^xc<control> pr<of> ([^,|^\.]+?)(?: and ([^,|^\.]+))?$"
)
re_exchange_lt_clause = re.compile(
    r"^(?:(.*?) )?(?:xo<life_total(?: suffix=s)?>)(?: pr<with> (.+))?\.?$"
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
re_tap_clause = re.compile(r"^(?:(.*?) ?)?(?:pr<for> ([^\.]+))?\.?$")

# clash 701.22 has the form with [player] (always an opponennt)
re_clash_clause = re.compile(r"^pr<with> ([^\.]+)$")

# vote 701.31 has three forms
#  1. vote forki attribute (the votes are in the val attribute) i.e. Council Guardian
#  2. vote for token1 or token2 (one or both of the tokens may have been inadverntly
#   tagged. see Lieutenants of the Guard)
#  3. vote for Thing i.e. Custodi Squire
re_vote_attribute_clause = re.compile(r"^pr<for> xr<(\w+) val=([^>]+)>$")
re_vote_tokens_clause = re.compile(r"^pr<for> (.+?) or (.+?)$")
re_vote_thing_clause = re.compile(r"^pr<for> ([^\.]+)$")

# meld 701.36 has two forms
#  1. meld them into [object] i.e. Midnight Scavengers
#  2. melds with [object] i.e. Graf Rats
re_meld_clause1 = re.compile(r"^xo<them> pr<into> (ob<[^>]+>)$")
re_meld_clause2 = re.compile(r"^pr<with> (ob<[^>]+>)$")

# exert 701.38
#  exert ob [as it attacks]?
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
