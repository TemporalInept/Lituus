#!/usr/bin/env python
""" mtgl.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines regexes,strings and helper functions used in the mtgl format
"""

#__name__ = 'mtgl'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
from hashlib import md5

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
  Turn Structure: Phases & Steps (5) = st<T
  Effects (610.1), only covers damage/combat damage = ef<EFFECT>
  Status (110.6) = st<STATUS>
  Numbers (107.1, 107.3) (not inside mana symbols) = nu<NUMBER>
  Trigger Preambles (603.1) tp<TRIGGER>

 English
  Prepositions pr<PREPOSITION>
  Demonstratives dm<DEMONSTRATIVE>
  Sequence sq<SEQUENCE>
  Comparison Operator op<COMPARISON>
  Conditional cn<CONDITONAL>

 Special lituus tags
  Lituus Action = xa<LITUUS ACTION>
  Lituus Chacteristics = xc<LITUUS CHARACTERISTIC>
  Lituus Objects = xo<LITUUS OBJECT>
  Lituus Quantifiers = xq<LITUUS QUANTIFIER>
  Lituus Modifiers = xm<LITUUS MODIFIER>
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
ARW = '→' # property/alignment
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

####
# REGEX AND STRING MANIP FOR PARSING
####

# CATCHALLS
# re_dbl_qte = r'".*?"'                            # double quoted string
re_rem_txt = re.compile(r"\(.+?\)")                # reminder text
re_mana_remtxt = re.compile(r"\(({t}: add.+?)\)")  # find add mana inside ()
re_non = re.compile(r"non(\w)")                    # find 'non' without hyphen
re_un = re.compile(r"un(\w)")                      # find 'un'

# DELIMITER
re_tkn_delim = re.compile( # matches mtg punctuation & spaces not inside a tag
    r"([:,\.\"\'•—\s])"
    r"(?![\w\s\+\/\-=¬∧∨⊕⋖⋗≤≥≡→]+>)"
)

####
## CARD REFERENCES
## Named cards will have the form ob<card ref=#> where x can be self or a md5
####

# self references
def re_self_ref(name):
    """
     returns the pattern to tag card references to self
    :param name: the name of the card
    :return: the self ref regex pattern
    """
    return re.compile(
        r"\b(this spell|this permanent|this card|her|his|{}|{}|{})\b".format(
            name,name.split(',')[0],name.split(' ')[0]
        )
    )

# Token Names with special needs
# The majority of these can be found in the phrase
#   "create a token ... named TOKEN_NAME" except Marit Lage, Kaldra which have
# the form "create TOKEN NAME, .... token."
token_names = [
    # Tokens that have been printed as a non-token card.
    #  See https://mtg.gamepedia.com/Token/Full_List#Printed_as_non-token
    "Ajani's Pridemate","Spark Elemental","Llanowar Elves","Cloud Sprite",
    "Goldmeadow Harrier","Kobolds of Kher Keep","Metallic Sliver"
    "Festering Goblin",
    # Tokens that have not been printed as a non-token card
    # See https://mtg.gamepedia.com/Token/Full_List#Tokens
    "Etherium Cell","Land Mine","Mask","Marit Lage","Kaldra","Carnivore","Twin",
    "Minor Demon","Urami","Karox Bladewing","Ashaya, the Awoken World",
    "Lightning Rager","Stoneforged Blade","Tuktuk the Returned","Mowu","Stang Twin",
    "Butterfly","Hornet","Wasp","Wirefly","Ragavan","Kelp","Wood",
    "Wolves of the Hunt","Voja, Friend to Elves","Tombspawn"
]
TN2R = {n:md5(n.encode()).hexdigest() for n in token_names}

# "create a token .... named NAME"
re_tkn_ref1 = re.compile(
    r"([C|c]reate\s.+?\snamed)\s({})".format('|'.join(list(TN2R.keys())))
)

# "create TOKEN NAME, .... token."
re_tkn_ref2 = re.compile(
    r"[C|c]reate ({}),\s(.+?)\stoken".format('|'.join(list(TN2R.keys())))
)

# meld tokens from Eldritch Moon, found by the phrase "then meld them into NAME"
# however, since there are only three and no chance of conflict with other words
# we do a straight replacement re
meld_tokens = [
    'Brisela, Voice of Nightmares','Chittering Host','Hanweir, the Writhing Township'
]
MN2R = {n:md5(n.encode()).hexdigest() for n in meld_tokens}
re_tkn_ref3 = re.compile(r"({})".format('|'.join(list(MN2R.keys()))))

# other card referencing will be initialized once in the call to set n2r due to
# size of name to ref-id dict
re_oth_ref = None
N2R = None

# basically a hack to catch card names we know are referenced in other cards
# but are not preceded by 'named' or 'Partner with'
named_cards = [
    "Urza's Power Plant","Urza's Mine","Urza's Tower",
    "Throne of Empires","Crown of Empires","Scepter of Empires",
]
NC2R = {n:md5(n.encode()).hexdigest() for n in named_cards}
re_oth_ref2 = re.compile(r"({})".format('|'.join(list(NC2R.keys()))))

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

def release_n2r():
    # release/delete the global N2R file (once its no longer needed)
    global re_oth_ref
    global N2R
    if not N2R is None:
        N2R = {}
        del N2R
        re_oth_ref = None

####
## SPECIAL KEYWORD PREPROCESSING
####
re_cycling_pre = re.compile(r"\b(\w+?)cycling\b")             # seperate type & cycling
re_landwalk_pre = re.compile(r"(\w+?)(?<!\sland)walk(?!er)")  # seperate type & landwalk

####
## WORD HACKS
## word hacks 1) replace contractions with full words, 2) common mtg phrases with
## acronyms 3) idiosyncratic conjugations, contractions
##
####

word_hacks = {
    # contractions
    "can't":"cannot","don't":"do not","didn't":"did not","it's":"it is",
    "isn't": "is not","haven't":"have not","hasn't":"has not","aren't":"are not",
    "you're":"you are","couldn't":"could not","they're":"they are",
    "doesn't":"does not","you've":"you havve",
    "that's":"that is","wasn't":"was not","weren't":"were not",
    # special
    'an':"a",
    # plural
    "werewolves":"werewolfs","allies":"allys","elves":"elfs","abilities":"abilitys",
    "sorceries":"sorcerys","libraries":"librarys","armies":"armys",
    "aurochses":"aurochss","cyclopes":"cyclops","fishes":"fishs","fungi":"fungess",
    "homunculuses":"homunculuss","jellyfishes":"jellyfishs","leeches":"leechs",
    "mercenaries":"mercenarys","mongeese":"mongooss","mice":"mouses","foxes":"foxs",
    "nautiluses":"nautiluss","octopuses":"octopuss","sphinxes":"sphinxs",
    "thalakoses":"thalokoss",
    # acronyms
    "end of turn":"eot","converted mana cost":"cmc",
    # suffixes/tense/possessive (ing,ed,s,'s)
    "activating":"activateing","activated":"activated",
    "creating":"createing","created":"createed",
    "doubling":"doubleing","doubled":"doubled",
    "exchanging":"exchangeing","exchanged":"exchangeed",
    "exiling":"exileing","exiled":"exileed",
    "fought":"fighted",
    "regenerating":"regenerateing","regenerated":"regenerateed",
    "sacrificing":"sacrificeing","sacrificed":"sacrificeed",
    "shuffling":"shuffleing","shuffled":"shuffleed",
    "dealt":"dealed",
    "leaving":"leaveing","left":"leaveed",
    "lost":"loseed","losing":"loseing",
    "its":"it's",
    "died":"dieed","dying":"dieing",
    "choosing":"chooseing","chosen":"chooseed",
    "drawn":"drawed",
    "spent":"spended","unspent":"unspended",
    "proliferating":"proliferateing","proliferated":"proliferateed",
    "populating":"populateing","populated":"populateed",
    "voting":"voteing","voted":"voteed",
    "investigating":"investigateing","investigated":"investigateed",
    "exploring":"exploreing","explored":"explored",
    "copied":"copyied","copies":"copys",
    "removing":"removeing","removed":"removeed",
    "distributing":"distributeing","distributed":"distributeed",
    "got":"getted","getting":"geting",
    "moving":"moveing","moved":"moveed",
    "paid":"payed",
    "taking":"takeing","took":"takeed",
    "cycled":"cycleed",
    #"cycled":"cyclinged", # IOT to match it as the past tense of a keyword
    "reducing":"reduceing","reduced":"reduceed",
    "declaring":"declareing","declared":"declareed",
    "has":"haves","had":"haveed","having":"haveing",
    "putting":"puting",
    "won":"wined","winning":"winned",
    "skipped":'"skiped',"skipping":"skiping",
    # status related
    "tapping":"taping","tapped":"taped","untapping":"untaped","untapped":"untaped",
    "flipping":"fliping","flipped":"fliped",
    "phased":"phaseed",
}
word_hack_tkns = '|'.join(word_hacks.keys())
re_word_hack = re.compile(r"\b({})\b".format(word_hack_tkns))

####
## EHGLISH WORD NUMBERS
####

E2I = {
    'one':'1','two':'2','three':'3','four':'4','five':'5',
    'six':'6','seven':'7','eight':'8','nine':'9','ten':'10',
    'eleven':'11','twelve':'12','thirteen':'13','fourteen':'14','fifteen':'15',
}
e2i_tkns = '|'.join(list(E2I.keys()))
re_wd2int = re.compile(r"\b({})\b".format(e2i_tkns))

####
## BEGIN MTGL REG EX
####

"""
 intag = "\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)" a word bounary and not preceded by an 
  opening tag mark follwoed by 0 or more tag characters or spaces
 allowed suffixes are:
  "r", "s", "ing", "ed", "'s" a space or the punctuation ':', ',', '.', 
 the below will tag only tokens that are not already tagged and are followed only
 by allowed suffixes 
  r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)"
  (\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*) -> preceded by a word boundary and not inside a tag
  ({}) -> group to catch specified tokens 
  (?=r|s|ing|ed|'s|:|\.|,|\s) -> only followed by allowed suffixes
"""

####
## QUANTIFIERS
####

# Quantifying words
lituus_quantifiers = [
    'a','target','each','all','any','every','another','other','this','that',
    'additional','those','these','their','extra','first','second','third','fourth',
    'fifth','sixth','seventh','eighth','ninth','tenth'
]
quantifier_tkns = '|'.join(lituus_quantifiers)
re_quantifier = re.compile(r"\b({})\b".format(quantifier_tkns))

####
## NUMBERS
####

# numbers are 1 or more digits or the variable X and are not preceded by a brace,
# '{', which indicates a mana symbol
#re_number = re.compile(r"(?<!{|\w|=)(\d+|x)(?!\w|>)")
re_number = re.compile(r"(?<!{)(\d+|x)\b")

####
## ENTITIES
####

# keep suffix but check word boundary in beginning
objects = [ # objects 109.1
    'ability','card','copy','token','spell','permanent','emblem','source'
]
obj_tkns = '|'.join(objects)
re_obj = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(obj_tkns)
)

# keep suffix but check word boundary in beginning
lituus_objects = [ # lituus objects
    "city's blessing",'game','mana pool','commander','mana','attacker','blocker',
    'it','them','coin'
]
lituus_obj_tkns = '|'.join(lituus_objects)
re_lituus_obj = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(lituus_obj_tkns)
)

# lituus players - keep suffix but check word boundary in beginning
lituus_players = ['you','opponent','teammate','player','owner','controller']
lituus_ply_tkns = '|'.join(lituus_players)
re_lituus_ply = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(lituus_ply_tkns)
)

####
## TURN STRUCTURE
####

# phases 500.1 & 505.1 (collective Main Phase) Note: this will drop the word phase
phases = [
    'beginning','precombat main','combat','postcombat main','ending','main'
]
re_phase = re.compile(r"\b({}) phase".format('|'.join(phases)))

# steps
# 501.1 beginning phase steps - untap, upkeep, draw
# 506.1 combat phase steps - beginning of combat,  declare attackers,
#  declare blockers, combat damage, end of combat
# Note: this will drop the word step
# Note: because some steps do not include the word 'step' and some steps may mean
#  multiple things (i.e. untap, draw, end), there are two regexs
steps1 = ['untap','draw','end','combat damage'] # must be followed by 'step'
steps2 = [ # may or may not be followed by 'step'
    'upkeep','beginning of combat','declare attackers',
    'declare blockers','end of combat','cleanup',
]
re_step1 = re.compile(r"\b({}) step".format('|'.join(steps1)))
re_step2 = re.compile(r"\b({})( step)?".format('|'.join(steps2)))

# generic terms NOTE: standalone 'phase' is handled later in Status)
generic_turns = ["turn","step","eot"]
re_generic_turn = re.compile(r"\b({})".format('|'.join(generic_turns)))

####
## ENGLISH
## tag important reoccuring english words, preoposition, & sequence/time
####

# TODO: need to tag less, more?
OP = {
    "less than or equal to":LE,"greater than or equal to":GE,
    "less than":LT,"greater than":GT,"equal to":EQ,"equal":EQ,
    "plus":'+',"minus":'-',"and/or":AOR,
}
re_op = re.compile(r"\b({})\b".format('|'.join(list(OP.keys()))))

# prepositions (check for ending tags)
prepositions = [
    'on top of','up to','on bottom of','from','to','into','in','on','out','under',
    'onto','top of','top','bottom of','bottom','without','with','for','up','down',
]
#re_prep = re.compile(r"\b(?<![<|-])({})\b(?!>)".format('|'.join(prepositions)))
re_prep = re.compile(r"\b(?<!<)({})\b(?!>)".format('|'.join(prepositions)))

# conditional/requirement related
conditionals = [
    'only if','if','would','unless','rather than','instead','may','except','not',
    'only','cannot'
]
re_cond = re.compile(r"\b({})\b".format('|'.join(conditionals)))

# sequence/time related  words
sequences = [
    'before','next','after','until','begin','beginning','end','ending','then',
    'during','as long as','simultaneously',
]
re_seq = re.compile(r"\b({})\b".format('|'.join(sequences)))

####
## TRIGGER PREAMBLES
###

# trigger preambles 603.1
re_trigger = re.compile(r"\b(at|whenever|when)\b")

####
## COUNTERS
####

# counters 122.1 Updated 24-Jan-20 with Theros Beyond Death
# two types p/t counters i.e +/-M/+/-N or a named counters (122 total ATT)
# see (https://mtg.gamepedia.com/Counter_(marker)/Full_List)
# NOTE: this must be done prior to keyword actions processing
re_pt_ctr = re.compile(r"(\+|-)nu<(\d+)>/(\+|-)nu<(\d+)> (counters*)\b")
named_counters = [
    'age','aim','arrow','arrowhead','awakening','blaze','blood','bounty','bribery',
    'brick','cage','carrion','charge','coin','credit','corpse','crystal','cube',
    'currency','death','delay','depletion','despair','devotion','divinity','doom',
    'dream','echo','egg','elixir','energy','eon','experience','eyeball','fade',
    'fate','feather','filibuster','flood','flying','fungus','fuse','gem','glyph',
    'gold','growth','hatchling','healing','hit','hoofprint','hour','hourglass',
    'hunger','ice','incubation','infection','intervention','isolation','javelin',
    'ki','level','lore','loyalty','luck','magnet','manifestation','mannequin',
    'mask','matrix','mine','mining','mire','music','muster','net','omen','ore',
    'page','pain','paralyzation','petal','petrification','phylactery','pin',
    'plague','poison','polyp','pressure','prey','pupa','quest','rust','scream',
    'shell','shield','silver','shred','sleep','sleight','slime','slumber','soot',
    'spark','spore','storage','strife','study','task','theft','tide','time','tower',
    'training','trap','treasure','velocity','verse','vitality','volatile','wage',
    'winch','wind','wish'
]
named_ctr_tkns = '|'.join(named_counters)
re_named_ctr = re.compile(r"\b({}) (counters*)\b".format(named_ctr_tkns))

####
## ABILITY WORDS, KEYWORDS, KEYWORD ACTIONS
####

ability_words = [ # ability words 207.2c Updated 24-Jan-20 with Theros Beyond Death
    "adamant","addendum","battalion","bloodrush","channel","chroma","cohort",
    "constellation","converge","council's dilemma","delirium","domain","eminence",
    "enrage","fateful hour","ferocious","formidable","grandeur","hellbent","heroic",
    "imprint","inspired","join forces","kinship","landfall","lieutenant","metalcraft",
    "morbid","parley","radiance","raid","rally","revolt","spell mastery","strive",
    "sweep","tempting offer","threshold","undergrowth","will of the council"
]
aw_tkns = '|'.join(ability_words)
re_aw = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(aw_tkns)
)

keyword_actions = [ # (legal) Keyword actions 701.2 through 701.43 Updated 24-Jan-20
    'activate','attach','unattach','cast','counter','create','destroy','discard',
    'double','exchange','exile','fight','play','regenerate','reveal','sacrifice',
    'scry','search','shuffle','tap','untap','fateseal','clash','abandon',
    'proliferate','transform','detain','populate','monstrosity','vote','bolster',
    'manifest','support','investigate','meld','goad','exert','explore','surveil',
    'adapt','amass',
]
kw_act_tkns = '|'.join(keyword_actions)
re_kw_act = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(kw_act_tkns)
)

keywords = [ # (legal) Keyword Abilties 702.2 through 702,137 Updated 24-Jan-20
    'deathtouch','defender','double strike','enchant','equip','first strike',
    'flash','flying','haste','hexproof','indestructible','intimidate','landwalk',
    'lifelink','protection','reach','shroud','trample','vigilance','banding',
    'rampage','cumulative upkeep','flanking','phasing','buyback','shadow','cycling',
    'cycle','echo','horsemanship','fading','kicker','multikicker','flashback',
    'madness','fear','morph','megamorph','amplify','provoke','storm','affinity',
    'entwine','modular','sunburst','bushido','soulshift','splice','offering',
    'ninjutsu','commander ninjutsu','epic','convoke','dredge','transmute',
    'bloodthirst','haunt','replicate','forecast','graft','recover','ripple',
    'split second','suspend','vanishing','absorb','aura swap','delve','fortify',
    'frenzy','gravestorm','poisonous','transfigure','champion','changeling','evoke',
    'hideaway','prowl','reinforce','conspire','persist','wither','retrace','devour',
    'exalted','unearth','cascade','annihilator','level up','rebound','totem armor',
    'infect','battle cry','living weapon','undying','miracle','soulbond','overload',
    'scavenge','unleash','cipher','evolve','extort','fuse','bestow','tribute',
    'dethrone','outlast','prowess','dash','exploit','menace','renown','awaken',
    'devoid','ingest','myriad','surge','skulk','emerge','escalate','melee','crew',
    'fabricate','partner with','partner','undaunted','improvise','aftermath',
    'embalm','eternalize','afflict','ascend','assist','jump-start','mentor',
    'afterlife','riot','spectacle','escape'
]
kw_tkns = '|'.join(keywords)
re_kw = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(kw_tkns)
)

# TODO: what to do with cycle, phase in, phase out, copy, flip
lituus_actions = [ # words not defined in the rules but important any way
    'put','remove','distribute','get','return','draw','move','look','pay','deal',
    'gain','lose','attack','block','add','enter','leave','choose','die','spend',
    'unspend','take','reduce','trigger','prevent','declare','have','switch',
    'assign','win','defend','cost','skip','flip','cycle','phase',
]
la_tkns = '|'.join(lituus_actions)
re_lituus_act = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(la_tkns)
)

####
## EFFECTS
####

# effects ensure the effects are not already tagged
# TODO: not sure if this necessary
re_effect = re.compile(r"(?<!combat\s)(damage|effect)(?!\w|>)")

####
## CHARACTERISTICS
####

meta_characteristics = [ # 100.3
    'p/t','everything','text','name','mana cost','cmc','power','toughness',
    'color identity','color','type'
]
re_meta_char = re.compile(r"({})".format('|'.join(meta_characteristics)))

color_characteristics = [ # 105.1, 105.2a, 105.2b, 105.2c
    'white','blue','black','green','red','colorless','multicolored','monocolored'
]
re_clr_char = re.compile(r"{}".format('|'.join(color_characteristics)))

super_characteristics = ['legendary','basic','snow','world'] # 205.4a
re_super_char = re.compile(r"({})".format('|'.join(super_characteristics)))

type_characteristics = [  # 300.1, NOTE: we added historic
    'artifact','creature','enchantment','instant','land','planeswalker',
    'socrcery','tribal'
]
re_type_char = re.compile(r"({})".format('|'.join(type_characteristics)))

sub_characteristics = [ # Updated 24-Jan-20 with Theros Beyond Death
    # NOTE: sub_characteristics must be updated with the release of new sets to
    #  include adding any token specific types
    # 205.3g artifact subtypes
    "clue","equipment","food","fortification","gold","treasure","vehicle",
    # 205.3h enchantment subtypes
    "aura","cartouche","curse","saga","shrine",
    # 205.3i land subtypes
    "desert","forest","gate","island","lair","locus","mine","mountain","plains",
    "power-plant","swamp","tower","urza’s",
    # 205.3j planeswalker types
    "ajani","aminatou","angrath","arlinn","ashiok","bolas","calix,chandra","dack",
    "daretti","davriel","domri","dovin","elspeth","estrid","freyalise","garruk",
    "gideon,huatli","jace","jaya","karn","kasmina","kaya","kiora","koth","liliana",
    "nahiri","narset","nissa","nixilis","oko","ral","rowan","saheeli","samut",
    "sarkhan","serra","sorin","tamiyo","teferi","teyo","tezzeret,tibalt","ugin",
    "venser","vivien","vraska","will","windgrace","wrenn","xenagos","yanggu",
    "yanling",
    # 205.3k instant/sorcery subtypes
    "adventure","arcane","trap",
    # 205.3m creature subtypes
    "advisor","aetherborn","ally","angel","antelope","ape","archer","archon",
    "army","artificer","assassin","assembly-worker","atog","aurochs","avatar",
    "azra","badger","barbarian","basilisk","bat","bear","beast","beeble",
    "berserker","bird","blinkmoth","boar","bringer","brushwagg","camarid","camel",
    "caribou","carrier","cat","centaur","cephalid","chimera","citizen","cleric",
    "cockatrice","construct","coward","crab","crocodile","cyclops","dauthi",
    "demigod","demon","deserter","devil","dinosaur","djinn","dragon","drake",
    "dreadnought","drone","druid","dryad","dwarf","efreet","egg","elder","eldrazi",
    "elemental","elephant","elf","elk","eye","faerie","ferret","fish","flagbearer",
    "fox","frog","fungus","gargoyle","germ","giant","gnome","goat","goblin","god",
    "golem","gorgon","graveborn","gremlin","griffin","hag","harpy","hellion","hippo",
    "hippogriff","homarid","homunculus","horror","horse","hound","human","hydra",
    "hyena","illusion","imp","incarnation","insect","jackal","jellyfish","juggernaut",
    "kavu","kirin","kithkin","knight","kobold","kor","kraken","lamia","lammasu",
    "leech","leviathan","lhurgoyf","licid","lizard","manticore","masticore",
    "mercenary","merfolk","metathran","minion","minotaur","mole","monger","mongoose",
    "monk","monkey","moonfolk","mouse","mutant","myr","mystic","naga","nautilus",
    "nephilim","nightmare","nightstalker","ninja","noble","noggle","nomad","nymph",
    "octopus","ogre","ooze","orb","orc","orgg","ouphe","ox","oyster","pangolin",
    "peasant","pegasus","pentavite","pest","phelddagrif","phoenix","pilot","pincher",
    "pirate","plant","praetor","prism","processor","rabbit","rat","rebel",
    "reflection","rhino","rigger","rogue","sable","salamander","samurai","sand",
    "saproling","satyr","scarecrow","scion","scorpion","scout","sculpture","serf",
    "serpent","servo","shade","shaman","shapeshifter","sheep","siren","skeleton",
    "slith","sliver","slug","snake","soldier","soltari","spawn","specter",
    "spellshaper","sphinx","spider","spike","spirit","splinter","sponge","squid",
    "squirrel","starfish","surrakar","survivor","tentacle","tetravite","thalakos",
    "thopter","thrull","treefolk","trilobite","triskelavite","troll","turtle",
    "unicorn","vampire","vedalken","viashino","volver","wall","warlock","warrior",
    "weird","werewolf","whale","wizard","wolf","wolverine","wombat","worm","wraith",
    "wurm","yeti","zombie","zubera",
]
re_sub_char = re.compile(r"({})".format('|'.join(sub_characteristics)))

# all characteristics
char_tkns = '|'.join(
    meta_characteristics + color_characteristics + super_characteristics + \
    type_characteristics + sub_characteristics
)
re_ch = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(char_tkns)
)

# 205.4b ... some supertypes are closely identified with specific card types...
# when we have a supertype followed immediately by a card type, combine these as
# the supertype applies to the card type and to the object (implied or explicit)
# For example Wave of Vitriol, "...all artifacts, enchantments, and nonbasic
# lands they control... nonbasic applies to lands and not to permanents that
# must sacrified
re_align_type = re.compile( # have to take into account negated characteristics
    r"ch<(¬?)({})> ch<(¬?)({})>".format(
        '|'.join(super_characteristics),'|'.join(type_characteristics)
    )
)

# seperate procedure for tagging p/t has to be done after numbers are tagged
re_ch_pt = re.compile(r"(\+|-)?nu<(\d+)>/(\+|-)?nu<(\d+)>(?!\scounter)")

# lituus characteristics
# TODO: keep control, own?
lituus_characteristics = ['life total','control','own','life','hand size','devotion']
lituus_ch_tkns = '|'.join(lituus_characteristics)
re_lituus_ch = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(lituus_ch_tkns)
)

####
## ZONES
####

# zones 400.1
zones = [
    'library','hand','battlefield','graveyard','stack','exile','command','anywhere'
]
zn_tkns = '|'.join(zones)
re_zone = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(zn_tkns)
)

####
## MID-PASS CLEANUP
####

# SPACES/HYPHENS between tokens
# For now, we are using a simple table to do so vice a regex but this will require
# an updated table for each release
tkn_delimit = {
    "city's blessing":"city's_blessing","precombat main":"precombat_main",
    "postcombat main":"postcombat_main","beginning of combat":"beginning_of_combat",
    "declare attackers":"declare_attackers","declare blockers":"declare_blockers",
    "end of combat":"end_of_combat","on top of":"on_top_of","up to":"up_to",
    "on bottom of":"on_bottom_of","top of":"top_of","bottom of":"bottom_of",
    "only if":"only_if","as long as":"as_long_as",
    "council's dilemma":"council's_dilemma","fateful hour":"fateful_hour",
    "join forces":"join_forces","spell mastery":"spell_master",
    "tempting offer":"tempting_offer","will of the council":"will_of_the_council",
    "double strike":"double_strike","first strike":"first_strike",
    "commander ninjutsu":"commander_ninjutsu","split second":"split_second",
    "living weapon":"living_weapon","totem armor":"totem_armor",
    "jump-start":"jump_start","assembly-worker":"assembly_worker",
}
tkn_delimit_tkns = '|'.join(tkn_delimit.keys())
re_tkn_delimit = re.compile(r"(?<=<)({})(?=>)".format(tkn_delimit_tkns))

# Negated tags i.e. non-XX<...>
re_negate_tag = re.compile(r"non-(\w\w)<(.+?)>")

####
## STATUS DECONFLICTION
####

# Status 110.5, is relatively hard as they are status words only in past tense except
# for face up/face down which have hyphens (see Break Open) As status they appear:
#  'tapped','untapped',
#  'flipped','unflipped',
#  'face-up','face-down',
#  'phased-in','phased-out'
# NOTE: excluding reminder text (which we remove) there is only 1 card, Time and
#  Tide that has a status involving Phasing

status = ['tap','flip','phase','face']
re_status = re.compile(r"([kx]a)<(un)?({})>(ed)".format('|'.join(status[0:2])))

# Phase can be Status, Action or Turn Structure
re_status_phase = re.compile(r"(xa<phase>ed-)pr<(in|out)>") # all status have a hyphen
re_action_phase = re.compile(r"xa<phase>(s|ed)?\spr<(in|out)>")
re_ts_phase = re.compile(r"xa<phase>(s?)(?=\W)")

# face can be a Status (has a hyphen) or a modifier to an action i.e. Bomat Courier
# "...exile the top card of your library face down.", generally 'turn'
re_status_face = re.compile(r"face-pr<(up|down)>")
re_mod_face = re.compile(r"face pr<(up|down)>")

####
## SUFFICES
####

# move any suffices 'r', 's', 'ing' 'ed' or "'s" to parameters inside tags
re_suffix = re.compile(r"(\w\w)<(.+?)>(r|s|ing|ed|'s)")

####
## CHAINS
# Sequential characteristics
###

# three or more and-ed/or-ed sequential characteristics
re_nchain = re.compile(
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>,\s){2,}" 
    r"(and|or)\s"                                                
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r"(\sob<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)?"
)

#Two characteristics separated by and/or i.e Saprazzan Bailiff & Ceta Sanctuary
re_2chain = re.compile(
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"                            
    r"\s(and|or)\s"                                                
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r"(\sob<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
)

# Two characteristics separated by comma i.e Chrome Mox treat this as an 'and'
# must be followed by an object
re_2chain_comma = re.compile(
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r",\s"
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r"(\sob<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
)

#Two characteristics separated by a space
# TODO: this will match cards with more than two space delimited characteristics
re_2chain_space = re.compile(
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r"\s"
    r"(ch<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
    r"(?=\sob<(?:¬?[\+\-/\w∧∨⊕⋖⋗≤≥≡→']+?)(?:\s[\w\+/\-=¬∧∨⊕⋖⋗≤≥≡→]+?)*>)"
)