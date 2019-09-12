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
__version__ = '0.0.6'
__date__ = 'September 2019'
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
# re_dbl_qte = r'".*?"'                          # double quoted string
re_rem_txt = re.compile(r"\(.+?\)")              # reminder text
re_mana_rtxt = re.compile(r"\(({t}: add.+?)\)")  # find add mana inside ()
re_non = re.compile(r"non(\w)")                  # find 'non' without hyphen

# TODO: check if we need the single quote in the parameters
# TODO: can this be simplified
re_tkn_delim = re.compile( # matches mtg punctuation & spaces not inside a tag
    r"([:,\.\"\'•—\s])"
    r"(?![\w\s\+\/\-=¬∧∨⊕⋖⋗≤≥≡→]+>)"
)

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

# these are names of tokens that do exist in the multiverse including nont-token
# copy cards (i.e. Ajani's Pridemante created by Ajani, Stength of the Pride
# The majority of these can be found in the phrase
#   "create a token ... named TOKEN_NAME" except
# exceptions are Marit Lage, Kaldra which have the form
#   "create TOKEN NAME, .... token."
token_names = [
    "Ajani's Pridemate","Minor Demon","Cloud Sprite","Gold","Mask","Rabid Sheep",
    "Twin","Land Mine","Goldmeadow Harrier","Wood","Kobolds of Kher Keep",
    "Llanowar Elves","Wolves of the Hunt","Stoneforged Blade","Lightning Rager",
    "Festering Goblin","Metallic Sliver","Spark Elemental","Etherium Cell",
    "Carnivore","Urami","Crow Storm","Butterfly","Hornet","Wirefly","Kelp",
    "Tombspawn","Hive","Mowu","Kaldra","Marit Lage",
]
#TODO: break up the list of tokens by how they can be matched?
TN2R = {n:md5(n.encode()).hexdigest() for n in token_names}

# "create a token .... named NAME"
re_tkn_ref1 = re.compile(
    r"([C|c]reate\s.+?\snamed)\s({})".format('|'.join(list(TN2R.keys())))
)

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
re_tkn_ref3 = re.compile(
    r"({})".format('|'.join(list(MN2R.keys())))
)

# other card referencing will be initialized once in the call to set n2r due to
# size of name to ref-id dict
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

def release_n2r():
    global N2R
    if not N2R is None:
        N2R = {}
        del N2R

# SPECIAL KEYWORD PREPROCESSING
re_cycling_pre = re.compile(r"\b(\w+?)cycling\b")             # seperate type & cycling
re_landwalk_pre = re.compile(r"(\w+?)(?<!\sland)walk(?!er)")  # seperate type & landwalk

# WORD HACKS

# word hacks 1) replace contractions with full words, 2) common mtg phrases with
# acronyms and 3) idiosyncratic conjugations and 4) categories with a limited
# number of items
word_hacks = {
    "can't":"cannot",
    "don't":"dont",
    "didn't":"didnt",
    "it's":"it is",
    "isn't": "isnt",
    "haven't":"havent",
    "hasn't":"hasnt",
    "its":"it",
    "aren't":"arent",
    "you're":"youre",
    "couldn't":"couldnt",
    "they're":"theyre",
    "doesn't":"doesnt",
    "you've":"youve",
    "that's":"thats",
    "wasn't":"wasnt",
    "weren't":"werent",
    'an':"a",
    "werewolves":"werewolf",
    "allies":"ally",
    "elves":"elf",
    "end of turn":"eot",
    "converted mana cost":"cmc",
    "spells":"spell",
    "abilities":"ability",
    "cards":"card","copies":"copy",
    "tokens":"token",
    "permanents":"permanent",
    "emblems":"emblem",
    "sorceries":"sorcery",
    "dealt":"deal",
    "left":"leave",
    "lost":"lose",
    "sources":"source",
    "targets":"target",
    "controls":"control",
    "your":"you",
    "opponents":"opponent",
    "teammates":"teammate",
    "players":"player",
    "libraries":"library",
    "owners":"owner",
    "controllers":"controller",
    "phases":"phase",
    "turns":"turn",
    "steps":"step",
    "spent":"spend",
    "dying":"die",
    "chosen":"choose",
    "attackers":"attacker",
    "blockers":"blocker",
    "graveyards":"graveyard",
    "hands":"hand",
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
    'attacking','blocking','blocked','defending','transformed','enchanted',
    'equipped','exiled','attached','activated','triggered','revealed'
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

# lituus players # TODO: not sure if their should be tagged it can reference objs tool
# NOTE: teammate is only referenced once outside of reminder text (Imperial Mask)
lituus_players = ['you','opponent','teammate','player','owner','controller','their']
re_lituus_ply = re.compile(r"\b({})\b".format('|'.join(lituus_players)))

# lituus objects
lituus_objects = [
    'city blessing','game','mana pool','commander','mana','attacker','blocker',
    'it','them','coin'
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
    'life total','control','own','life','cost','hand size','devotion'
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
# NOTE: we differiante between pay and paid but still want paid tagged for now at
# least
lituus_actions = [
    'put','remove','distribute','get','return','draw','move','copy','look','pay',
    'paid','deal','gain','lose','attack','block','add','enter','leave','choose','die',
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
    **{w+'ed':w for w in all_acts if w not in ['block','trigger','reveal','attach'] and w[-1] != 'e'},
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
    "ch<will> of the council":"aw<will_of_the_council>",
    "council dilemma":"aw<council's_dilemma>",
    "ph<phase> out":"xa<phase_out>",
    "ph<phase> in":"xa<phase_in>",
    "xa<deal> ka<double> xq<that>":"xa<deal> twice xq<that>" # double is not a keyword action here
}

# don't get the tagged level_up
re_lvl = re.compile(r"level(?!_)")

