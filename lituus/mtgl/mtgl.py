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
__version__ = '0.1.0'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
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

####
# REGEX AND STRING MANIP FOR PARSING
####

# CATCHALLS
# re_dbl_qte = r'".*?"'                            # double quoted string
re_rem_txt = re.compile(r"\(.+?\)")                # reminder text
re_mana_remtxt = re.compile(r"\(({t}: add.+?)\)")  # find add mana inside ()
re_non = re.compile(r"non(\w)")                    # find 'non' without hyphen

# DELIMITER
re_tkn_delim = re.compile( # matches mtg punctuation & spaces not inside a tag
    r"([:,\.\"\'•—\s])"
    r"(?![\w\s\+\/\-=¬∧∨⊕⋖⋗≤≥≡→]+>)"
)

# CARD REFERENCES
# Named cards will have the form ob<card ref=#> where x can be self or a md5
# has of the card name

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

# SPECIAL KEYWORD PREPROCESSING
re_cycling_pre = re.compile(r"\b(\w+?)cycling\b")             # seperate type & cycling
re_landwalk_pre = re.compile(r"(\w+?)(?<!\sland)walk(?!er)")  # seperate type & landwalk

# WORD HACKS

# word hacks 1) replace contractions with full words, 2) common mtg phrases with
# acronyms and 3) idiosyncratic conjugations and 4) categories with a limited
# number of items
# TODO: could we just standarize a regular expression to catch anamolies
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
    "copies":"copys","sorceries":"sorcerys","libraries":"librarys","armies":"armys",
    "aurochses":"aurochss","cyclopes":"cyclops","fishes":"fishs","fungi":"fungess",
    "homunculuses":"homunculuss","jellyfishes":"jellyfishs","leeches":"leechs",
    "mercenaries":"mercenarys","mongeese":"mongooss","mice":"mouses","foxes":"foxs",
    "nautiluses":"nautiluss","octopi":"octopuss","sphinxes":"sphinxs",
    "thalakoses":"thalokoss",
    # acronyms
    "end of turn":"eot","converted mana cost":"cmc",
    # suffixes/tense/possessive
    "dealt":"dealed","left":"leaveed","lost":"loseed","its":"it's","spent":"spended",
    "dying":"dieing","died":"dieed","chosen":"chooseed","drawn":"drawed",
}
re_wh = re.compile(r"\b({})\b".format('|'.join(word_hacks.keys())))

# replace english words for 0 to 10 with corresponding integers
E2I = {
    'one':'1','two':'2','three':'3','four':'4','five':'5',
    'six':'6','seven':'7','eight':'8','nine':'9','ten':'10',
    'eleven':'11','twelve':'12','thirteen':'13','fourteen':'14','fifteen':'15',
}
re_wd2int = re.compile(r"\b({})\b".format('|'.join(list(E2I.keys()))))

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
super_characteristics = ['legendary','basic','snow','world','tribal'] # 205.4a
type_characteristics = [  # NOTE: we added historic
    'instant','creature','sorcery','planeswalker',
    'enchantment','land','artifact','historic'
]
sub_characteristics = [ # Updated 24-Jan-20 with Theros Beyond Death
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
characteristics = meta_characteristics + \
                  color_characteristics + \
                  super_characteristics + \
                  type_characteristics + \
                  sub_characteristics
re_ch = re.compile(r"\b({})\b".format('|'.join(characteristics)))

# status 110.6 may include hyphens or spaces (after tagging, replace the hyphen)
status = [
    'tapped','untapped','flipped','unflipped',
    'face[ |-]up','face[ |-]down','phased[ |-]in','phased[ |-]out'
]
re_stat = re.compile(r"\b({})\b".format('|'.join(status)))
re_stat_fix = re.compile(r"(face|phased)(-)(up|down|in|out)")

# lituus status
lituus_status = [
    'attacking','blocking','blocked','defending','transformed','enchanted',
    'equipped','exiled','attached','unattached','activated','triggered','revealed',
    'suspended',
]
re_lituus_stat = re.compile(r"\b({})\b".format('|'.join(lituus_status)))