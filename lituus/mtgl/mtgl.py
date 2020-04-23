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
__version__ = '0.1.3'
__date__ = 'April 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import regex as re
from collections import OrderedDict
from hashlib import md5
import lituus as lts

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
  Lituus Thing = xt<LITUUS THING>
  Lituus Attribute = xr<META-CHARACTERISTIC>
  
Ultimately, the intent is to break oracle text into three main components:
 Things - tanglible entities that can be interacted with
 Attributes - properties of Things
 Actions - events, effects that manipulate Things and the game  
"""

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
ARW = '→' # alignment
SUB = '⭰' # subclass/inheritance
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
re_rem_txt = re.compile(r"\(.+?\)\n?")             # reminder text
re_mana_remtxt = re.compile(r"\(({t}: add.+?)\)")  # find add mana inside ()
re_non = re.compile(r"non(\w)")                    # find 'non' without hyphen
re_un = re.compile(r"un(\w)")                      # find 'un'

# DELIMITERS

# matches mtgl punctuation & spaces not inside a tag
re_tkn_delim = re.compile(
    r"([:,\.\"\'•—\s])"
    r"(?![\w\s\+\/\-=¬∧∨⊕⋖⋗≤≥≡→⭰]+>)"
)

# matches mtgl conjoining operators in a mtgl tag parameter
re_param_delim_nop = re.compile(r"[∧∨⊕⋖⋗≤≥≡→⭰]")    # w\o operators
re_param_delim_wop = re.compile(r"([∧∨⊕⋖⋗≤≥≡→⭰])")  # w\ operators

# matches prefix operators
re_param_prefix = re.compile(r"[\+\-¬]")

# conjunction operators
conj_op = {'and':AND,'or':OR,'and/or':AOR}
conj_op_tkns = '|'.join(conj_op)
re_conj_op = re.compile(r"\b({})\b".format(conj_op_tkns))

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
        r"\b(this spell|this permanent|this card|her|his|{}|{})\b".format(
            name,name.split(',')[0]
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
    "activating":"activateing","activated":"activateed",
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
    "produced":"produceed","producing":"produceing",
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
    'additional','those','these','their','the','extra','first','second','third',
    'fourth','fifth','sixth','seventh','eighth','ninth','tenth',
]
quantifier_tkns = '|'.join(lituus_quantifiers)
re_quantifier = re.compile(r"\b({})\b".format(quantifier_tkns))

####
## NUMBERS
####

# numbers are 1 or more digits or a variable X, Y, Z and are not preceded by a brace,
# '{', which indicates a mana symbol or another
re_number = re.compile(r"(?<![a-z{])(\d+|x|y|z)\b")

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
    'it','them','coin','choice',
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

## OPERATORS

# TODO: need to tag less, more?
#  TODO:
#   In cases where the order of dicts should be preserved or as in the case of
#   'less than' versus "less than or equal to" an additional ordered list of
#   keys is provided. Since OrderedDict implementation varies across Python 3.x
#   versions this is preferable to having non-portable code
op = {
    "less than or equal to":LE,"greater than or equal to":GE,
    "less than":LT,"greater than":GT,"equal to":EQ,"equal":EQ,
    "plus":'+',"minus":'-',
}
op_keys = [
    "less than or equal to","greater than or equal to","less than",
    "greater than","equal to","equal","plus","minus",
]
re_op = re.compile(r"\b({})\b".format('|'.join(list(op_keys))))

# finds number or greater and number or less
re_num_op = re.compile(r"(nu<(?:\d+|x|y|z)>)\sor\s(greater|less)")

# prepositions (check for ending tags)
prepositions = [
    'on top of','up to','on bottom of','from','to','into','in','on','out','under',
    'onto','top of','top','bottom of','bottom','without','with','for','up','down',
]
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
    'during','as long as','simultaneously','time'
]
seq_tkns = '|'.join(sequences)
re_seq = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(seq_tkns)
)

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
    'assign','win','defend','cost','skip','flip','cycle','phase','become','share',
    'turn','produce',
    'named', # Special case we only want this specific conjugation
]
la_tkns = '|'.join(lituus_actions)
re_lituus_act = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(la_tkns)
)

####
## EFFECTS
####

# (609) we only tag the word effect, combat damage and effect
# NOTE: These should not have already been tagged, but just in case
effects = ["combat damage","damage","effect"]
eff_tkns = '|'.join(effects)
re_effect = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(eff_tkns)
)

####
## CHARACTERISTICS
####

meta_characteristics = [ # 100.3
    'p/t','everything','text','name','mana cost','cmc','power','toughness',
    'color identity','color','type'
]
re_meta_char = re.compile(r"{}".format('|'.join(meta_characteristics)))
re_meta_attr = re.compile( # for meta characteristics
    r"(ch<(?:p/t|everything|text|name|mana cost|cmc|power|toughness|"
      r"color_identity|color|type)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

color_characteristics = [ # 105.1, 105.2a, 105.2b, 105.2c
    'white','blue','black','green','red','colorless','multicolored','monocolored'
]
re_clr_char = re.compile(r"{}".format('|'.join(color_characteristics)))

super_characteristics = ['legendary','basic','snow','world'] # 205.4a
re_super_char = re.compile(r"{}".format('|'.join(super_characteristics)))

type_characteristics = [  # 300.1, NOTE: we added historic
    'artifact','creature','enchantment','instant','land','planeswalker',
    'sorcery','tribal','historic',
]
re_type_char = re.compile(r"{}".format('|'.join(type_characteristics)))

# sub characteristics (updated 24-Jan-20 with TBD). Must be updated with relaase
# of new sets to include adding any token specific types i.e. does not appear on
# any card

# 205.3g artifact subtypes
subtype_artifact_characteristics = [
    "clue","equipment","food","fortification","gold","treasure","vehicle",
]
re_subtype_artifact_char = re.compile(
    r"{}".format('|'.join(subtype_artifact_characteristics))
)

# 205.3h enchantment subtypes
subtype_enchantment_characteristics = [
    "aura","cartouche","curse","saga","shrine",
]
re_subtype_enchantment_char = re.compile(
    r"{}".format('|'.join(subtype_enchantment_characteristics))
)

# 205.3i land subtypes
subtype_land_characteristics = [
    "desert", "forest", "gate", "island", "lair", "locus", "mine", "mountain",
    "plains","power-plant", "swamp", "tower", "urza’s",
]
re_subtype_land_char = re.compile(
    r"{}".format('|'.join(subtype_land_characteristics))
)

# 205.3j planeswalker types
subtype_planeswalker_characteristics = [
    "ajani","aminatou","angrath","arlinn","ashiok","bolas","calix,chandra","dack",
    "daretti","davriel","domri","dovin","elspeth","estrid","freyalise","garruk",
    "gideon,huatli","jace","jaya","karn","kasmina","kaya","kiora","koth","liliana",
    "nahiri","narset","nissa","nixilis","oko","ral","rowan","saheeli","samut",
    "sarkhan","serra","sorin","tamiyo","teferi","teyo","tezzeret,tibalt","ugin",
    "venser","vivien","vraska","will","windgrace","wrenn","xenagos","yanggu",
    "yanling",
]
re_subtype_planeswalker_char = re.compile(
    r"{}".format('|'.join(subtype_planeswalker_characteristics))
)

# 205.3k instant/sorcery subtypes
subtype_instant_sorcery_characteristics = ["adventure","arcane","trap",]
re_subtype_instant_sorcery_char = re.compile(
    r"{}".format('|'.join(subtype_instant_sorcery_characteristics))
)

# 205.3m creature subtypes
subtype_creature_characteristics = [
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
    "golem","gorgon","graveborn","gremlin","griffin","hag","harpy","hellion",
    "hippo","hippogriff","homarid","homunculus","horror","horse","hound","human",
    "hydra","hyena","illusion","imp","incarnation","insect","jackal","jellyfish",
    "juggernaut","kavu","kirin","kithkin","knight","kobold","kor","kraken","lamia",
    "lammasu","leech","leviathan","lhurgoyf","licid","lizard","manticore",
    "masticore","mercenary","merfolk","metathran","minion","minotaur","mole",
    "monger","mongoose","monk","monkey","moonfolk","mouse","mutant","myr","mystic",
    "naga","nautilus","nephilim","nightmare","nightstalker","ninja","noble",
    "noggle","nomad","nymph","octopus","ogre","ooze","orb","orc","orgg","ouphe",
    "ox","oyster","pangolin","peasant","pegasus","pentavite","pest","phelddagrif",
    "phoenix","pilot","pincher","pirate","plant","praetor","prism","processor",
    "rabbit","rat","rebel","reflection","rhino","rigger","rogue","sable",
    "salamander","samurai","sand","saproling","satyr","scarecrow","scion",
    "scorpion","scout","sculpture","serf","serpent","servo","shade","shaman",
    "shapeshifter","sheep","siren","skeleton","slith","sliver","slug","snake",
    "soldier","soltari","spawn","specter","spellshaper","sphinx","spider","spike",
    "spirit","splinter","sponge","squid","squirrel","starfish","surrakar",
    "survivor","tentacle","tetravite","thalakos","thopter","thrull","treefolk",
    "trilobite","triskelavite","troll","turtle","unicorn","vampire","vedalken",
    "viashino","volver","wall","warlock","warrior","weird","werewolf","whale",
    "wizard","wolf","wolverine","wombat","worm","wraith","wurm","yeti","zombie",
    "zubera",
]
re_subtype_creature_char = re.compile(
    r"{}".format('|'.join(subtype_creature_characteristics))
)

# combined
sub_characteristics = subtype_artifact_characteristics + \
                      subtype_enchantment_characteristics + \
                      subtype_land_characteristics + \
                      subtype_planeswalker_characteristics + \
                      subtype_instant_sorcery_characteristics + \
                      subtype_creature_characteristics
re_sub_char = re.compile(r"{}".format('|'.join(sub_characteristics)))

# subtype of
TYPE_ARTIFACT        = 0
TYPE_ENCHANTMENT     = 1
TYPE_LAND            = 2
TYPE_PLANESWALKER    = 3
TYPE_INSTANT_SORCERY = 4
TYPE_CREATURE        = 5
def subtype(st):
    """
    given a subtype st returns the type
    :param st: string subtype
    :return: TYPE code
    """
    if st in subtype_artifact_characteristics: return TYPE_ARTIFACT
    elif st in subtype_enchantment_characteristics: return TYPE_ENCHANTMENT
    elif st in subtype_land_characteristics: return TYPE_LAND
    elif st in subtype_planeswalker_characteristics: return TYPE_PLANESWALKER
    elif st in subtype_instant_sorcery_characteristics: return TYPE_INSTANT_SORCERY
    elif st in subtype_creature_characteristics: return TYPE_CREATURE
    else:
        raise lts.LituusException(lts.EMTGL,"{} is not a subtype".format(st))

def subtype_of(st,mt):
    """
    determines if subtype st is a subtype of type mt
    :param st: the subtyype i.e 'dragon'
    :param mt: the type i.e. 'creature'
    :return: True if st is a subtype of mt, False otherwise
    """
    tc = subtype(st)
    if tc == TYPE_ARTIFACT and mt == 'artifact': return True
    elif tc == TYPE_ENCHANTMENT and mt =='enchantment': return True
    elif tc == TYPE_LAND and mt == 'land': return True
    elif tc == TYPE_PLANESWALKER and mt == 'planeswalker': return True
    elif tc == TYPE_INSTANT_SORCERY and mt == 'instant': return True
    elif tc == TYPE_INSTANT_SORCERY and mt == 'sorcery': return True
    elif tc == TYPE_CREATURE and mt == 'creature': return True
    return False

# all characteristics
char_tkns = '|'.join(
    meta_characteristics +
    color_characteristics +
    super_characteristics +
    type_characteristics +
    sub_characteristics
)
re_ch = re.compile(
    r"\b(?<!<[¬∧∨⊕⋖⋗≤≥≡→\w\s]*)({})(?=r|s|ing|ed|'s|:|\.|,|\s)".format(char_tkns)
)

# seperate procedure for tagging p/t has to be done after numbers are tagged
re_ch_pt = re.compile(r"(\+|-)?nu<(\d+|x|y|z)>/(\+|-)?nu<(\d+|x|y|z)>(?!\scounter)")

# meta 'attribute' values see Rathi Intimidator picks out three values 1) the
# attribute, 2) the operator and 3) the value of the attribute
re_attr_val = re.compile(
    r"xr<([\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)>"
    r"\s"
    r"op<([⊕⋖⋗≤≥≡])>"
    r"\s"
    r"nu<(\d+|x|y|z)>"
)

# meta 'attribute' value see Repeal where no operator is present
re_attr_val_nop = re.compile(r"xr<([\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)>\snu<(\d+|x|y|z)>")

# ... base power and toughness X/Y i.e. Godhead of Awe then power and toughness
# i.e Transmutation
re_base_pt = re.compile(
    r"base\sch<power>\sand\sch<toughness>\s"
    r"(ch<p/t(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)
re_single_pt = re.compile(r"ch<power>\sand\sch<toughness>")

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
# NOTE: the tagger is looking for these phrases inside tags so it will not catch
# Will of the Council which will be tagged
# we do this mid-pass because the tagger is looking untagged words. As such,
#  we have to look for the tagged phrase for will of the Council which will be
#  tagged ch<will> of xq<the> council have to handjam this for now
val_join = {
    "city's blessing":"city's_blessing","precombat main":"precombat_main",
    "postcombat main":"postcombat_main","beginning of combat":"beginning_of_combat",
    "declare attackers":"declare_attackers","declare blockers":"declare_blockers",
    "end of combat":"end_of_combat","combat damage":"combat_damage",
    "on top of":"on_top_of","up to":"up_to","on bottom of":"on_bottom_of",
    "top of":"top_of","bottom of":"bottom_of","only if":"only_if",
    "as long as":"as_long_as","council's dilemma":"council's_dilemma",
    "fateful hour":"fateful_hour","join forces":"join_forces",
    "spell mastery":"spell_master","tempting offer":"tempting_offer",
    "will of the council":"will_of_the_council",
    "double strike":"double_strike","first strike":"first_strike",
    "commander ninjutsu":"commander_ninjutsu","split second":"split_second",
    "living weapon":"living_weapon","totem armor":"totem_armor",
    "jump-start":"jump_start","assembly-worker":"assembly_worker",
    "color identity":"color_identity",
}
val_join_tkns = '|'.join(val_join.keys())
re_val_join = re.compile(r"(?<=<)({})(?=>)".format(val_join_tkns))

# Negated tags i.e. non-XX<...>
re_negate_tag = re.compile(r"non-(\w\w)<(.+?)>")

# Hanging Basic finds the supertype not followed by an explicit land
re_hanging_basic = re.compile(
    r"(ch<¬?basic>)(?!\sch<land(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# Hanging Snow finds the supertype that is followed by a land subtype (with no
# explicit 'land' inbetween NOTE: we are only checking the FIVE basic subtypes
re_hanging_snow = re.compile(
    r"(ch<¬?snow>)"
    r"(?=\sch<¬?(?:forest|island|mountain|plains|swamp)"
      r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# phrases related to number of something
#  1. use nu<y> to denote "the number of" i.e. Beseech the Queen "less than or
#   equal to the number of lands"
#  2. use nu<z> to denote "any number of" i.e. Ad Nauseum "any number of times"
#  3. remove "are each" if followed by an operator
re_equal_y = re.compile(r"(?<=op<[⊕⋖⋗≤≥≡]>\s)(xq<the>\snumber\sof)")
re_equal_z = re.compile(r"xq<any> number of")
re_are_each = re.compile(r"are\sxq<each>\s(?=op<[⊕⋖⋗≤≥≡]>)")

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

# only looking at tap and flip - it will be a status only if there is a suffix
# of 'ed' and it is not preceded by 'is'
re_status = re.compile(
    r"(?<!is\s)"
    r"([kx]a)<(un)?({})>(ed)".format('|'.join(status[0:2]))
)

# Phase can be Status, Action or Turn Structure
re_status_phase = re.compile(r"(xa<phase>ed-)pr<(in|out)>") # all status have a hyphen
re_action_phase = re.compile(r"xa<phase>(s|ed)?\spr<(in|out)>")
re_ts_phase = re.compile(r"xa<phase>(s?)(?=\W)")

# face can be a Status (has a hyphen) or a modifier to an action i.e. Bomat Courier
# "...exile the top card of your library face down.", generally 'turn'
re_status_face = re.compile(r"face-pr<(up|down)>")
re_mod_face = re.compile(r"face pr<(up|down)>")

####
## X/Y COUNTER DECONFLICTION
####

# NOTE: Frankenstein's Monster is the only one that exhibits this anamoly so for
#  now the change is hardcoded in multiverse
# chained counters mistagged as characteristics i.e. Frankenstein's Monster
# xq<a> ch<p/t val=+2/+0>, ch<p/t val=+1/+1>, or xo<ctr type=+0/+2>
#re_ctr_chain = re.compile(
#    r"(ch<p/t(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>,\s){2}"
#    r"or\s"
#    r"(xo<ctr(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)>)"
#)

####
## TURN (ACTION) DECONFLICTION
####

# turn is an action if it is followed by a 'xm' (modifier) or 'xq' (quantifier)
# NOTE:
#  1) suffices are not tagged yet, have to account for them in positive lookahead
#  2) only capture the 'ts' tag id IOT replace it with 'xa' lituus action
re_turn_action = re.compile(
    r"(ts)"
    r"(?=<turn(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>(?:r|s|ing|ed|'s)?\s"
    r"x[m|q]<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

####
## SUFFICES
####

# move any suffices 'r', 's', 'ing' 'ed' or "'s" to parameters inside tags
re_suffix = re.compile(r"(\w\w)<(.+?)>(r|s|ing|ed|'s)")

####
## ALIGNMENTS
####

# There are two types of alignments (1) type and super-type alignment and (2)
# type with other criteria. We'll use the unicode arrow ('→') to denote alignment.
# Alignment will always take the form TYPE→CRITERIA. The arrow can be read as
# 'that is'. For example:
#  Terror ... creature→¬artifact∧¬black ... reads creature that is not artifact
#  and not black
#  Wave of Vitriol ... land→¬basic ... reads land that is not basic
# Alignment assists in chaining characteristics and puts the focus on the target
# of an effect.

# 205.4b ... some supertypes are closely identified with specific card types...
# when we have a supertype followed immediately by a card type, combine these as
# the supertype applies to the card type and to the object (implied or explicit)
# For example Wave of Vitriol, "...all artifacts, enchantments, and nonbasic
# lands they control... nonbasic applies to lands and not to permanents that
# must sacrified
# NOTE: We are assuming that super-type alignments are all space-delimited
re_align_super = re.compile(
    r"(ch<¬?(?:legendary|basic|snow|world)>\s)+"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|"
      r"planeswalker|sorcery|tribal|historic)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# space delimited subtypes followed by a type will be aligned
# NOTE: as above we assume sub-type alignments are all space-delimited
# NOTE: see "Quest for Ula's Temple" after alignment we have:
# ... xa<put> xq<a> ch<kraken>, ch<leviathan>, ch<octopus>, or ch<creature→serpent>
# ob<card>. Only serpent has been aligned to creature. During chaining, the
# remaining subtypes will be chained
re_align_sub = re.compile(
    r"(ch<¬?(?:" + re_sub_char.pattern + ")>\s)+"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|"
      r"planeswalker|sorcery|tribal|historic)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# special case of subtype alignment where we have subtype characteristic type
re_align_sub_sc = re.compile(
    r"(ch<¬?(?:" + re_sub_char.pattern + ")>)"
    r"\s"
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)>)"
    r"\s"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|"
      r"planeswalker|sorcery|tribal|historic)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

####
## REIFICATION
####

# find singleton types, characteristics that have
#  one or more logical operator joined types
#  are not preceded by a characteristic (and a comma or conjuction)
#  may be followed by an object
#  are not followed by a characteristic
re_singleton_type = re.compile(
    r"(?<!ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>"
     r",?(?:\s(?:and|or|and/or))?\s)"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
     r"(?:¬?[∧∨⊕](?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))*"
     r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"(?:\s(ob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>))?"
    r"(?!,?\sch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

####
## CHAINS
# Sequential characteristics
####

# ... p/t X/Y or p/t A/B ...
re_pt_chain = re.compile(
    r"(ch<p/t(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"\sor\s"
    r"(ch<p/t(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# Three or more comma-delimited color characteristics with conjunction i.e. Hazezon
# Tamar As of IKO there are only 6
re_nchain_clr = re.compile(
    r"(ch<¬?(white|blue|black|green|red|colorless|multicolored|monocolored)>,\s){2,}"
    r"(and|or|and/or)\s"
    r"(ch<¬?(white|blue|black|green|red|colorless|multicolored|monocolored)>)"
)

# Two color characteristics separated by conjunction i.e. Cavern Harpy
re_2chain_clr = re.compile(
    r"ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored))>"
    r"\s?(and|or|and/or)\s"
    r"ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored))>"
)

# Three or more comma-delimited type characteristics w/ conjunction i.e. Swan Song
# NOTE: We do not check for tribal or historic
re_nchain_type = re.compile(
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
      r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>,\s){2,}"
    r"(and|or|and/or)\s"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
      r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# Two type characteristics separated by conjunction i.e. Aura of Silence but not
# followed by a characteristic i.e. Temple Thief
re_2chain_type = re.compile(
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
      r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"\s?(and|or|and/or)\s"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
      r"(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"(?!\sch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# phrases of the form CHAR, CHAR OBJ|CHAR where:
#  the phrase is preceded by a quantifier
#  the phrase is not followed by an object or characteristic
#  the first characteristic is either a color, type or super-type
#  the first two characteristics do not have attributes
# these take two forms:
#  1) See Terror, 3 characteristics (ch<¬artifact>, ch<¬black> ch<creature>) will
#  will be aligned under creature
#  2) see Druidic Satchel, last token is an object (ch<¬creature>, ch<¬land> ob<card>)
#  the two characteristics will be chained
# It will not match cards like Royal Decree (ch<mountain>, ch<black> ob<permanent>)
# in which mountain is disjoint from black permanent
re_2chain_special = re.compile(
    r"(?<=xq<\w+>\s)"
    r"(?:ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored|"
      r"artifact|creature|enchantment|instant|land|planeswalker|sorcery|tribal|"
      r"historic|legendary|basic|snow|world))>)"
    r",\s(?:ch<(¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)>)\s"
    r"((?:ch|ob)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"(?!\s,?(?:ch|ob)<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

#**** TODO UNDER RCONSTRUCTION ****#

# Two characteristics separated by a conjunction ie. Sphinx of the Final Word
# but cannot be preceded and/or followed by a characteristic i.e. Purge
# TODO: does this stop legitimate conjunctions?
re_2chain_conj = re.compile(
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"                            
    r"\s(and|or|and/or)\s"
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

re_2chain_conj2 = re.compile(
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>\s){0,1}"
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"                            
    r"\s(and|or|and/or)\s"
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    r"(\sch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>){0,1}"
)

# two or more comma-delimited characteristics with a conjunction
# three variants
#  a) Followed by one or more characteristics and an object i.e. Quest for Ula's
#  Temple xq<a> ch<kraken>, ch<leviathan>, ch<octopus>, or ch<serpent>
#   ch<creature> ob<card> '
#  b) Followed by an object i.e. God-Pharaoh's Faithful ch<blue>, ch<black>, or
#   ch<red> ob<spell>
#  c) Not followed by anything i.e. Frozen Aether ch<artifact suffix=s>,
#   ch<creature suffix=s>, and ch<land suffix=s>
re_nchain_conj = re.compile(
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>,\s){1,}" 
    r"(and|or|and/or)\s"                                                
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
)

# three or more space delimted characteristics followed by an object i.e.
# Spawning Pit ch<p/t val=2/2> ch<colorless> ch<spawn> ch<artifact> ch<creature>
re_nchain_space = re.compile(
    # have a last characteristic IOT not capture the last space if there is no object
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>\s){1,}"
    r"(ch<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)"
    #r"(\sob<(?:¬?[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)(?:\s[\w\+\-/=¬∧∨⊕⋖⋗≤≥≡→⭰']+?)*>)?"
)
