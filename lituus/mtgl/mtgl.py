#!/usr/bin/env python
""" mtgl.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines regexes,strings and helper functions used in the mtgl format
"""

__name__ = 'mtgl'
__license__ = 'GPLv3'
__version__ = '0.0.6'
__date__ = 'September 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re

"""
 Defines a series of regular of expressions and string replacements for tagging
 of MTG words and phrases.

 Once tagged there are several combinations
  Entity: a player (xp), a mtg object (ob) or a lituus object (xo)
  Thing: an Entity, or a zone (zn)
  Property: a characteristic (ch) or a lituus characteristic (xc)

 Mana symbols (energy, tap and untap) are already enclosed by braces '{' and '}', 
 continue this concept using '<' and '>' to tag important words. All text is 
 lowered  cased. Then special words as defined in the Magic: The Gathering 
 Comprehensive Rules (3-May 2019) are tagged in addition to words that are common 
 throughout mtg card oracles. 
 
 Each tag is a two letter identifier followed by a '<', the word and a '>' 
 Identifiers beggining with 'x', specifies words that lituus treats as special or 
 common enough to warrant being tagged

  Keyword Actions (701.2 through 701.43) = ka<KEYWORD ACTION>
  Keywords (702.2 through 702.136) = kw<KEYWORD>
  Ability Words (207.2c} = aw<ABILITY WORD>
  Zone (4) = zn<ZONE>
  Objects (109) = ob<OBJECT>
  Characteristics (109.3) ch<characteristic>
  Phases & Steps (5) = ph<PHASE>
  Effects (610.1), only covers damage/combat damage = ef<EFFECT>
  Status (110.6) = st<STATUS>
  Numbers (107.1, 107.3) (not inside mana symbols) = nu<NUMBER> #TODO add X
  Trigger Preambles (603.1) mt<TRIGGER>

 English
  Prepositions pr<PREPOSITION>
  Demonstratives dm<DEMONSTRATIVE>
  Sequence sq<SEQUENCE>
  Comparison Operator op<COMPARISON>
  Conditional cn<CONDITONAL>

 Special lituus tags
  Lituus Status = xs<LITUUS STATUS>
  Lituus Action = xa<LITUUS ACTION>
  Lituus Chacteristics = xc<LITUUS CHARACTERISTIC>
  Lituus Objects = xo<LITUUS OBJECT>
  Lituus Quantifiers = xq<LITUUS QUANTIFIER>
"""

####
# EXCEPTIONS
####

class MTGLException(Exception):
    def __init__(self,message): Exception.__init__(self,message)
class MTGLParseException(MTGLException):
    def __init__(self,message): MTGLException.__init__(self,message)
class MTGLTagException(MTGLParseException):
    def __init__(self,message): MTGLParseException.__init__(self,message)
class MTGLGraphException(MTGLException):
    def __init__(self,message): MTGLException.__init__(self,message)

####
# TAGS AND SUMBOLS
####

# UNICODE SYMBOLS
# ¬∧∨⊕⋖⋗≤≥≡
# our defined symbols
NOT = '¬' # mtgl not
AND = '∧' # mtgl and
OR  = '∨' # mtgl or
AOR = '⊕' # mtgl and/or
LT  = '⋖' # mtgl less than
GT  = '⋗' # mtgl greater than
LE  = '≤' # mtgl less than or equal
GE  = '≥' # mtgl greater than or equal
EQ  = '≡' # mtgl equal to
ARW = '→' # property
# symbols defined in oracle text
HYP = '—' # mtg long hyphen
BLT = '•' # mtg bullet
# symbols that can be mixed up easily or hard to read
PER = '.' # period
CMA = ',' # comma
DBL = '"' # double quote
SNG = "'" # single quote
# symbols used in mtgjson format
MIN = '−' # not used yet (found in negative loyalty costs)

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

# TODO: check if we need the single quote in the parameters
# TODO: can this be simplified
re_tkn_delim = re.compile( # matches all mtg punctuation and spaces not inside a tag
    r"([:,\.\"\'•—\s])"
    r"(?![\w\s\+\/\-=¬∧∨⊕⋖⋗≤≥≡→]+>)"
)

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
    if tkn in [':', CMA, PER, DBL, SNG, BLT, HYP]: return MTGL_PUN
    return MTGL_WRD

# match a mtg symbol
def is_mtg_symbol(tkn): return re_mtg_sym.match(tkn) is not None

# match a mtg mana string
def is_mana_string(tkn): return re_mtg_mstring.match(tkn) is not None

def is_tag(tkn):
    try:
        _ = untag(tkn)
        return True
    except MTGLTagException:
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
        raise MTGLTagException(tkn)

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

def is_tgr_word(tkn):
    try:
        return untag(tkn)[0] == 'mt'
    except MTGLTagException:
        return False

def is_quality(tkn):
    try:
        if is_mtg_char(tkn): return True
        elif is_mtg_obj(tkn) and 'characteristics' in untag(tkn)[2]: return True
        else: return False
    except MTGLTagException:
        return False

def is_thing(tkn):
    try:
        return untag(tkn)[0] in ['ob','xp','xo','zn']
    except MTGLTagException:
        return False

def is_mtg_obj(tkn):
    try:
        return untag(tkn)[0] == 'ob'
    except MTGLTagException:
        return False

def is_lituus_obj(tkn):
    try:
        return untag(tkn)[0] == 'xo'
    except MTGLTagException:
        return False

def is_player(tkn):
    try:
        return untag(tkn)[0] == 'xp'
    except MTGLTagException:
        return False

def is_zone(tkn):
    try:
        return untag(tkn)[0] == 'zn'
    except MTGLTagException:
        return False

def is_property(tkn):
    try:
        return untag(tkn)[0] in ['ch','xc']
    except MTGLTagException:
        return False

def is_mtg_char(tkn):
    try:
        return untag(tkn)[0] == 'ch'
    except MTGLTagException:
        return False

def is_meta_char(tkn):
    try:
        val = untag(tkn)[1]
    except MTGLTagException:
        return False

    if OR in val: val = val.split(OR)
    elif AND in val: val = val.split(AND)
    else: val = [val]
    for v in val:
        if v.replace('_',' ') not in meta_characteristics: return False
    return True

def is_lituus_char(tkn):
    try:
        return untag(tkn)[0] == 'xc'
    except MTGLTagException:
        return False

def is_action(tkn):
    try:
        return untag(tkn)[0] in ['ka','xa']
    except MTGLTagException:
        return False

def is_mtg_act(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except MTGLTagException:
        return False

def is_lituus_act(tkn):
    try:
        return untag(tkn)[0] == 'xa'
    except MTGLTagException:
        return False

def is_state(tkn):
    try:
        return untag(tkn)[0] in ['st', 'xs']
    except MTGLTagException:
        return False

def is_quantifier(tkn):
    try:
        return untag(tkn)[0] == 'xq'
    except MTGLTagException:
        return False

def is_preposition(tkn):
    try:
        return untag(tkn)[0] == 'pr'
    except MTGLTagException:
        return False

def is_conditional(tkn):
    try:
        return untag(tkn)[0] == 'cn'
    except MTGLTagException:
        return False

def is_number(tkn):
    try:
        return untag(tkn)[0] == 'nu'
    except MTGLTagException:
        return False

def is_variable(tkn):
    try:
        t,v,_ = untag(tkn)
        return t == 'nu' and v in ['x','y','z']
    except MTGLTagException:
        return False

def is_operator(tkn):
    try:
        return untag(tkn)[0] == 'op'
    except MTGLTagException:
        return False

def is_keyword(tkn):
    try:
        return untag(tkn)[0] == 'kw'
    except MTGLTagException:
        return False

def is_keyword_action(tkn):
    try:
        return untag(tkn)[0] == 'ka'
    except MTGLTagException:
        return False

def is_ability_word(tkn):
    try:
        return untag(tkn)[0] == 'aw'
    except MTGLTagException:
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

####
# REGEX AND STRING MANIP FOR PARSING
####

# CATCHALLS
# re_dbl_qte = r'".*?"'                          # double quoted string
re_rem_txt = re.compile(r"\(.+?\)")              # reminder text
re_mana_rtxt = re.compile(r"\(({t}: add.+?)\)")  # find add mana inside parenthesis
re_non = re.compile(r"non(\w)")                  # find non not followed by hyphen

# CARD REFERENCES

def re_self_ref(name):
    """
     returns the pattern to tag card references to self
    :param name: the name of the card
    :return: the self ref regex pattern
    """
    return re.compile(
        r"\b(this spell|this permanent|this card|her|his|{}|{})\b".format(name,name.split(',')[0])
    )

# other card referencing will be initialized once due to size of name to ref-id
# dict
re_oth_ref = None
N2R = None

def set_n2r(n2r):
    # call global IOT calculate the lengthy regex once during the first call
    # to tag (Could objectify the tagger and avoid this)
    global re_oth_ref
    global N2R
    if re_oth_ref is None:
        # IOT to avoid tagging cards like Sacrifice (an action and a card name) with
        # this expression have to search for card names preceded by either named
        # or Partner with
        re_oth_ref = re.compile(
            r"(named|Partner with) ({})\b".format('|'.join(list(n2r.keys())))
        )
        N2R = n2r

# SPECIAL KEYWORD PREPROCESSING
re_cycling_pre = re.compile(r"\b(\w+?)cycling\b")             # seperate type & cycling
re_landwalk_pre = re.compile(r"(\w+?)(?<!\sland)walk(?!er)")  # seperate type & landwalk

# WORD HACKS

# word hacks 1) replace contractions with full words, 2) common mtg phrases with
# acronyms and 3) idiosyncratic conjugations and 4) categories with a limited
# number of items
word_hacks = {
    "can't":"cannot","don't":"dont","didn't":"didnt","it's":"it is","isn't": "isnt",
    "haven't":"havent","its":"it","aren't":"arent","you're":"youre","couldn't":"couldnt",
    "they're":"theyre","doesn't":"doesnt","you've":"youve","that's":"thats",
    "wasn't":"wasnt","weren't":"werent",'an':"a","werewolves":"werewolf",
    "allies":"ally","end of turn":"eot","converted mana cost":"cmc","paid":"pay",
    "spells":"spell","abilities":"ability","cards":"card","copies":"copy",
    "tokens":"token","permanents":"permanent","emblems":"emblem","sorceries":"sorcery",
    "dealt":"deal","left":"leave","lost":"lose","sources":"source","targets":"target",
    "controls": "control","your":"you","opponents":"opponent","teammates":"teammate",
    "players":"player","libraries":"library","owners":"owner","controllers":"controller",
    "phases":"phase","turns":"turn","steps":"step","spent":"spend","dying":"die",
    "chosen":"choose","attackers":"attacker","blockers":"blocker","graveyards":"graveyard",
}
re_wh = re.compile(r"\b({})\b".format('|'.join(word_hacks.keys())))

# replace english words for 0 to 10 with corresponding integers
E2I = {
    'one':'1','two':'2','three':'3','four':'4','five':'5',
    'six':'6','seven':'7','eight':'8','nine':'9','ten':'10',
    'eleven':'11','twelve':'12','thirteen':'13','fourteen':'14','fifteen':'15',
}
re_wint = re.compile(r"\b({})\b".format('|'.join(list(E2I.keys()))))

# STATUS

# status 110.6 may include hyphens or spaces (after tagging, replace the hyphen)
status = [
    'tapped','untapped','flipped','unflipped',
    'face[ |-]up','face[ |-]down','phased[ |-]in','phased[ |-]out'
]
re_stat = re.compile(r"\b({})\b".format('|'.join(status)))
re_stat_fix = re.compile(r"(face|phased)(-)(up|down|in|out)")

# lituus status
# TODO: add these 'suspended','unattached'
lituus_status = [
    'attacking','blocking','defending','transformed','enchanted','equipped',
    'exiled','attached','activated','revealed'
]
re_lituus_stat = re.compile(r"\b({})\b".format('|'.join(lituus_status)))

# PHASES

# phases 501 to 514 (including steps and turns)
# requires two regex, the second to capture singleton upkeep and combat
phases = [
    "untap step","upkeep step","draw step","main phase","combat phase",
    "beginning of combat step","beginning of combat","declare attackers step",
    "declare blockers step","combat damage step","end of combat step",
    "end step","cleanup step","eot","turn","phase","step"
]
re_phase = re.compile(r"\b({}\b)".format('|'.join(phases)))
re_phase2 = re.compile(r"(?<!<)(upkeep(?!>\sstep)|combat(?!>\sdamage|step))(?!>)")

# COUNTERS

# counters (mtg.gamepedia.com/Counter_(marker)/List_of_Counters)
# two types p/t counters i.e +/-M/+/-N or one of 119 named counters
# NOTE: this must be done prior to keyword actions processing
re_pt_ctr = re.compile(r"(\+|-)nu<(\d+)>/(\+|-)nu<(\d+)> (counters*)\b")
named_counters = [
    "age","aim","arrow","arrowhead","awakening","blaze","blood","bounty","bribery",
    "brick","carrion","charge","credit","corpse","crystal","cube","currency","death",
    "delay","depletion","despair","devotion","divinity","doom","dream","echo","egg",
    "elixir","energy","eon","experience","eyeball","fade","fate","feather","filibuster",
    "flood","fungus","fuse","gem","glyph","gold","growth","hatchling","healing","hit",
    "hoofprint","hour","hourglass","hunger","ice","incubation","infection","intervention",
    "isolation","javelin","ki","level","lore","loyalty","luck","magnet","manifestation",
    "mannequin","mask","matrix","mine","mining","mire","music","muster","net","omen",
    "ore","page","pain","paralyzation","petal","petrification","phylactery","pin",
    "plague","poison","polyp","pressure","prey","pupa","quest","rust","scream","shell",
    "shield","silver","shred","sleep","sleight","slime","slumber","soot","spore",
    "storage","strife","study","theft","tide","time","tower","training","trap",
    "treasure","velocity","verse","vitality","volatile","wage","winch","wind","wish"
]
re_named_ctr = re.compile(r"\b({}) (counters*)\b".format('|'.join(named_counters)))

# NUMBERS

# numbers all integers and the variable X (not preceded by a brace which indicates
# a mana symbol or T, Q, E symbols or a letter
re_mint = re.compile(r"(?<!{|\w|=)(\d+|x)(?!\w<)")

# Quantifying words i.e. target, each, all, any, every,
lituus_quantifiers = [
    'target','each','all','any','every','another','other',
    'this','that','those','these'
    'first','second','third','fourth','fifth','sixth',
    'seventh','eighth','ninth','tenth'
]
re_lituus_qu = re.compile(r"\b({})\b".format('|'.join(lituus_quantifiers)))

# EFFECTS

# effects 610.1 ensure the effects are not already tagged
re_ef = re.compile(r"(?<!combat\s)(damage)(?!>)")

# ENTITIES

# lituus players
# NOTE: teammate is only referenced once outside of reminder text (Imperial Mask)
lituus_players = ['you','opponent','teammate','player','owner','controller','their']
re_lituus_ply = re.compile(r"\b({})\b".format('|'.join(lituus_players)))

# lituus objects
lituus_objects = [
    'city blessing','game','mana pool','commander','mana','attacker','blocker',
    'it','them'
]
re_lituus_obj = re.compile(r"\b({})\b(?!>)".format('|'.join(lituus_objects)))

# objects (109)
objects = ['ability','card','copy','token','spell','permanent','emblem','source']
re_obj = re.compile(r"(?<!<)\b({}\b)".format('|'.join(objects)))

# CHARACTERISTICS
# NOTE: sub_characteristics must be updated with the release of new sets to
#  include adding any token specific types

# characteristics 109.3
meta_characteristics = [
    'p/t','everything','text','name','mana cost','cmc','power','toughness',
    'color identity','color','type'
]
color_characteristics = [
    'white','blue','black','green','red','colorless','multicolored','monocolored'
]
super_characteristics = ['legendary','basic','snow','world','tribal']
type_characteristics = [  # NOTE: we added historic
    'instant','creature','sorcery','planeswalker',
    'enchantment','land','artifact','historic'
]
sub_characteristics = [
    'dryad','wurm','wall','horse','dovin','ogre','shaman','dragon','zombie','human',
    'warrior','aura','desert','beast','angel','djinn','soldier','spirit','rhino',
    'cleric','treefolk','centaur','scarecrow','rat','drake','knight','goblin',
    'rogue','bird','monk','gremlin','elephant','naga','archer','gargoyle','lizard',
    'equipment','golem','myr','elemental','demon','merfolk','wizard','phoenix',
    'nightstalker','snake','elf','druid','insect','advisor','horror','dwarf',
    'nomad','crocodile','construct','cat','cephalid','giant','volver','imp',
    'spider','mercenary','kiora','shapeshifter','pirate','minotaur','avatar',
    'scout','skeleton','berserker','nissa','sliver','frog','spellshaper','atog',
    'kithkin','swamp','manticore','eldrazi','kor','arcane','spike','mountain',
    'vampire','leviathan','artificer','curse','metathran','ally','hippo','assassin',
    'plains','mutant','ooze','specter','fungus','gnome','hellion','karn','cyclops',
    'pilot','gorgon','vedalken','ape','hippogriff','gideon','carrier','egg',
    'samurai','wolf','minion','kobold','vehicle','kavu','serpent','hound',
    'nightmare','antelope','salamander','orc','werewolf','plant','troll','fish',
    'dinosaur','eye','elspeth','faerie','shade','griffin','juggernaut','elk',
    'devil','boar','aetherborn','viashino','tezzeret','barbarian','rebel','pegasus',
    'thopter','satyr','thrull','worm','aminatou','illusion','yeti','homunculus',
    'drone','sphinx','trap','saga','nymph','homarid','kirin','bear','weird',
    'incarnation','pest','hydra','lhurgoyf','gate','ajani','jace','turtle','kaya',
    'siren','liliana','slith','god','chimera','badger','camel','scorpion','crab',
    'zubera','teferi','hag','squirrel','samut','nixilis','kraken','nephilim',
    'chandra','masticore','wraith','jackal','azra','ninja','moonfolk','garruk',
    'orgg','licid','cartouche','ashiok','archon','processor','shrine','wolverine',
    'praetor','efreet','urza','tower','dreadnought','nautilus','thalakos',
    'nahiri','ugin','tibalt','dauthi','ouphe','freyalise','phelddagrif','island',
    'teyo','elder','forest','bat','fox','ral','sheep','sarkhan','wombat','hyena',
    'dack','xenagos','yanggu','soltari','sponge','aurochs','ox','lair','unicorn',
    'huatli','slug','bolas','squid','harpy','octopus','trilobite','mystic',
    'windgrace','davriel','whale','basilisk','assembly-worker','daretti',
    'jellyfish','monger','domri','monkey','goat','sorin','leech','saheeli','tamiyo',
    'bringer','starfish','estrid','sable','narset','ferret','vraska','power-plant',
    'surrakar','noggle','beeble','mongoose','rabbit','cockatrice','jaya','lammasu',
    'reflection','angrath','kasmina','rowan','arlinn','mine','spawn','venser',
    'pangolin','koth','vivien','oyster','yanling','flagbearer','rigger','lamia',
    'mole','locus','brushwagg','fortification','will',
    # added tokens
    'army','camarid','caribou','citizen','clue','deserter','germ','graveborn',
    'orb','pentavite','pincher','prism','sand','saproling','scion','sculpture',
    'serf','servo','splinter','survivor','tetravite','triskelavite'
]
characteristics = meta_characteristics + \
                  color_characteristics + \
                  super_characteristics + \
                  type_characteristics + \
                  sub_characteristics
re_ch = re.compile(r"\b({})\b".format('|'.join(characteristics)))

# seperate procedure for tagging p/t
re_ch_pt = re.compile(r"(\+|-)?nu<(\d+)>/(\+|-)?nu<(\d+)>(?!\scounter)")

# lituus characteristics - have to make sure it has not already been tagged
lituus_characteristics = [  # NOTE: these apply primarily to player
    'life_total','control','own','life','cost','hand size','devotion'
]
re_lituus_ch = re.compile(r"\b({})\b(?!>)".format('|'.join(lituus_characteristics)))

# get rid of all plurals
all_characteristics = characteristics + lituus_characteristics
all_characteristics = {
    **{w+'s':w for w in all_characteristics if w[-1] not in ['s','h']},
    **{w+'es':w for w in all_characteristics if w[-1] in ['s','h']},
}
re_characteristics_conj = re.compile(r"\b({})\b".format('|'.join(all_characteristics)))

# ABILITY WORDS, KEYWORDS, KEYWORD ACTIONS

# ability words defined in 207.2c
ability_words = [
    'addendum','battalion','bloodrush','channel','chroma','cohort','constellation',
    'converge',"council's dilemma", 'delirium','domain','eminence','enrage',
    'fateful hour','ferocious','formidable','grandeur','hellbent','heroic','imprint',
    'inspired','join forces','kinship','landfall','lieutenant','metalcraft','morbid',
    'parley','radiance','raid','rally','revolt','spell mastery','strive','sweep',
    'tempting offer','threshold','will of the council'
]
re_aw = re.compile(r"\b({})\b".format('|'.join(ability_words)))

# Keyword actions defined in 701.2 through 701.43.
# for these, we want to make sure that they have not already been tagged first
# so we'll check for '<' prior to the word.
keyword_actions = [
    'activate','unattach','attach','cast','counter','create','destroy','discard',
    'double','exchange','exile','fight','play','regenerate','reveal','sacrifice',
    'scry','search','shuffle','tap','untap','fateseal','clash','abandon',
    'proliferate','transform','detain','populate','monstrosity','vote','bolster',
    'manifest','support','investigate','meld','goad','exert','explore','surveil',
    'adapt','amass'
]
re_kw_act = re.compile(r"(?<!<)\b({})\b".format('|'.join(keyword_actions)))

# lituus actions actions which appear often in oracle text
lituus_actions = [
    'put','remove','distribute','get','return','draw','move','copy','look','pay',
    'deal','gain','lose','attack','block','add','enter','leave','choose','die',
    'spend','take','skip','cycle','reduce','trigger','prevent','declare',
    'has','have','switch','phase in','phase out','flip','assign','win'
]
re_lituus_act = re.compile(r"(?<!<)\b({})\b".format('|'.join(lituus_actions)))

# get rid of all conjugative endings with regards to actions
# have to hack some cards to avoid removing 'ing' or 'd' as required
all_acts = keyword_actions + lituus_actions
all_acts = {
    **{w+'s':w for w in all_acts if w[-1] not in ['s','h']},
    **{w+'es':w for w in all_acts if w[-1] in ['s','h']},
    **{w+'d':w for w in all_acts if w not in ['activate','exile'] and w[-1] == 'e'},
    **{w+'ed':w for w in all_acts if w not in ['reveal','attach'] and w[-1] != 'e'},
    **{w+'ing':w for w in all_acts if w not in ['attack','block'] and w[-1] != 'e'},
    **{w[:-1]+'ing': w for w in all_acts if w not in ['vote','cycle'] and w[-1] == 'e'}
}
re_acts_conj = re.compile(r"\b({})\b".format('|'.join(all_acts)))

keywords = [
    'deathtouch','defender','double strike','enchant','equip','first strike','flash',
    'flying','haste','hexproof','indestructible','intimidate','landwalk','lifelink',
    'protection','reach','shroud','trample','vigilance','banding','rampage',
    'cumulative upkeep','flanking','phasing','buyback','shadow','cycling','echo',
    'horsemanship','fading','kicker','multikicker','flashback','madness','fear',
    'morph','megamorph','amplify','provoke','storm','affinity','entwine','modular',
    'sunburst','bushido','soulshift','splice','offering','ninjutsu','commander ninjutsu',
    'epic','convoke','dredge','transmute','bloodthirst','haunt','replicate','forecast',
    'graft','recover','ripple','split second','suspend','vanishing','absorb',
    'aura swap','delve','fortify','frenzy','gravestorm','poisonous','transfigure',
    'champion','changeling','evoke','hideaway','prowl','reinforce','conspire',
    'persist','wither','retrace','devour','exalted','unearth','cascade','annihilator',
    'level up','rebound','totem armor','infect','battle cry','living weapon',
    'undying','miracle','soulbond','overload','scavenge','unleash','cipher',
    'evolve','extort','fuse','bestow','tribute','dethrone','outlast','prowess',
    'dash','exploit','menace','renown','awaken','devoid','ingest','myriad','surge',
    'skulk','emerge','escalate','melee','crew','fabricate','partner with','partner',
    'undaunted','improvise','aftermath','embalm','eternalize','afflict','ascend',
    'assist','jump-start','mentor','afterlife','riot','spectacle']
re_kw = re.compile(r"\b({})\b".format('|'.join(keywords)))

# ZONES

# zones are covered in 4
zones = [
    'library','hand','battlefield','graveyard','stack','exile','command','anywhere'
]
re_zone = re.compile(r"(?<!<)\b({})\b".format('|'.join(zones)))

# TRIGGER

# trigger preambles 603.1
re_trigger = re.compile(r"\b(at|whenever|when)\b")

# ENGLISH

# English words, tag important reoccuring english words, preoposition,
# operator hacks replace quantity comparison english words with operators
# TODO: not currently tagging less/greater by themselves
OP = {
    "less than or equal to":LE,"greater than or equal to":GE,
    "less than":LT,"greater than":GT,"equal to":EQ,"equal":EQ,
    "plus":'+',"minus":'-',"and/or":AOR
}
re_op = re.compile(r"\b({})\b".format('|'.join(list(OP.keys()))))

# post processing rearrangment and taggging of operator sequences
# TODO: would like to combine ge and le somehow
re_le = re.compile(r"ch<([\w+¬∧∨]+)> nu<([\dxyz]+)> or less")   # ch<CH> nu<D> or op<less>
re_ge = re.compile(r"ch<([\w¬∧∨]+)> nu<([\dxyz]+)> or greater") # ch<CH> nu<D> or op<greater>
re_is_op = re.compile(r"is (op<[⋖⋗≤≥≡]+>)")                     # is op<...>
re_op_to = re.compile(r"(op<[⋖⋗≤≥≡]+>) pr<to>")                 # op<...> pr<to>
re_up_to = re.compile(r"pr<up to> nu<([\dxyz]+)>")               # pr<up_to> nu<D>

# prepositions (check for ending tags)
prepositions = [
    'on top of','up to','on bottom of','from','to','into','in','on','under','onto',
    'top of','top','bottom of','bottom','without','with','for'
]
re_prep = re.compile(r"\b({})\b(?!>)".format('|'.join(prepositions)))

# conditional/requirement related
conditionals = [
    'only if','if','would','unless','rather than','instead','may','except','not',
    'only','cannot'
]
re_cond = re.compile(r"\b({})\b".format('|'.join(conditionals)))

# sequence/time related  words
sequences = [
    'before','next','after','until','begin','beginning',
    'end','ending','then','during','as long as'
]
re_seq = re.compile(r"(?<!<)\b({})\b".format('|'.join(sequences)))

# POST-PROCESSING

# find spaces/hyphens inside tags that join two (or more) words
re_tag_prep = re.compile(r"<(\w+?)(\s|-)([\w|\s]+?)>")

# find tags preceded by non-
re_negate_tag = re.compile(r"non-(\w\w)<(\w+?)>")

# find negated possessives
re_non_possessive = re.compile(r"dont xc<(control|own)>")

# make protection uniform (two cards Elite Inquistor and Oversould of Dusk)
# are written as protection from quality, from quality, and from quality
# fix this to be protection from quality and from quality and from quality
re_pro_fix = re.compile(
    r"kw<protection> pr<from> ch<(\w+)>, pr<from> ch<(\w+)>, and pr<from>"
)

# TODO: need to scrub this for relevance
# TODO: annotate use of ch (mtg_characteritistic) as id for activated and
#  triggered
rephrase = {
    "ph<turn> sq<after> dm<this> nu<1>":"ph<turn> sq<after> dm<this> ph<turn>",
    "xo<mana> xc<cost>":"ch<mana_cost>",
    "ph<combat> ef<damage>":"ef<combat_damage>",
    "xo<mana> ob<ability>":"xo<mana_ability>",
    "xa<declare> xo<blocker> step":"ph<declare_blockers_step>",
    "xa<declare> xo<attacker> step":"ph<declare_attackers_step>",
    "ch<power> or ch<toughness>":"ch<power∨toughness>",
    "ch<power> and ch<toughness>":"ch<power∧toughness>",
    "the zn<battlefield>":"zn<battlefield>",
    "xq<any> number of":"nu<y>",
    "a number of":"nu<z>",
    "thats st<tapped> and xs<attacking>":"st<tapped> and xs<attacking>",
    "xq<that> are st<tapped> and xs<attacking>":"st<tapped> and xs<attacking>",
    "ch<aura> swap":"kw<aura_swap>",
    "cumulative ph<upkeep>":"kw<cumulative_upkeep>",
    "ka<activate> or xa<trigger> ob<ability>":"ch<activated> or ch<triggered> ob<ability>",
    "ch<will> of the council":"aw<will_of_the_council>",
    "council dilemma":"aw<council's_dilemma>",
    "ph<phase> out":"xa<phase_out>",
    "ph<phase> in":"xa<phase_in>",
    #"xq<that> xq<target>":"that xa<target>"
}

# don't get the tagged level_up
re_lvl = re.compile(r"level(?!_)")

