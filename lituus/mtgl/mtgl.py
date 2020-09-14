#!/usr/bin/env python
""" mtgl.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
Defines regexes,strings and helper functions used in the mtgl format
"""

# __name__ = 'mtgl'
__license__ = 'GPLv3'
__version__ = '0.1.10'
__date__ = 'August 2020'
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
 Comprehensive Rules (22 Jan 2020) are tagged in addition to words that are common 
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
  Lituus Qualifiers = xl<LITUUS QUALIFIER>
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
NOT = '¬'  # mtgl not
AND = '∧'  # mtgl and
OR = '∨'   # mtgl or
AOR = '⊕'  # mtgl and/or
LT = '⋖'   # mtgl less than
GT = '⋗'   # mtgl greater than
LE = '≤'   # mtgl less than or equal
GE = '≥'   # mtgl greater than or equal
EQ = '≡'   # mtgl equal to
EEQ = '⇔'  # exactly equal to
ARW = '→'  # alignment
ADD = '+'  # plus sign
SUB = '-'  # minus sign
# symbols defined in oracle text
HYP = '—'  # mtg long hyphen
BLT = '•'  # mtg bullet
# symbols that can be mixed up easily or hard to read
PER = '.'  # period
CMA = ','  # comma
DBL = '"'  # double quote
SNG = "'"  # single quote
# symbols used in mtgjson format
MIN = '−'  # not used yet (found in negative loyalty costs)

####
# REGEX AND STRING MANIP FOR PARSING
####

# CATCHALLS
# re_dbl_qte = r'".*?"'                                    # double quoted string
re_rem_txt = re.compile(r"\(.+?\)")                        # reminder text
re_mana_remtxt = re.compile(r"\(({t}: add.+?)\)")          # find add mana inside ()
re_melds_remtxt = re.compile(r"\((melds with [^\.]+\.)\)") # find melds ... inside ()
re_non = re.compile(r"non(\w)")                            # find 'non' without hyphen
re_un = re.compile(r"un(\w)")                              # find 'un'

# DELIMITERS

# matches mtgl punctuation & spaces not inside a tag
re_tkn_delim = re.compile(
    r"([:,\.\"\'•—\s])(?![\w \+\/\-=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+>)"
)

# matches mtgl conjoining operators in a mtgl tag parameter
re_param_delim_nop = re.compile(r"[∧∨⊕⋖⋗≤≥≡→\(\)]")  # w\o operators
re_param_delim_wop = re.compile(r"([∧∨⊕⋖⋗≤≥≡→\(\)])")  # w\ operators

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
    # NOTE: making the assumption that subtypes supercede self references
    self_refs = ['this card','this spell','this permanent','his','her']
    if name.lower() not in sub_characteristics:
        # covers creatures like Assembly-Worker
        self_refs.append(name)
    if name.lower().split(',')[0] not in sub_characteristics:
        # covers planeswalkers like Gideon, the Oathsworn
        self_refs.append(name.split(',')[0])
    if name.lower().split(' ')[0] not in sub_characteristics:
        self_refs.append(name.split(' ')[0])
    return re.compile(r"\b({})\b".format('|'.join(self_refs)))


# Token Names with special needs
# The majority of these can be found in the phrase
#   "create a token ... named TOKEN_NAME" except Marit Lage, Kaldra which have
# the form "create TOKEN NAME, .... token."
# Updated 03-Jul-20 to M21
token_names = [
    # Tokens that have been printed as a non-token card.
    #  See https://mtg.gamepedia.com/Token/Full_List#Printed_as_non-token
    "Ajani's Pridemate","Spark Elemental","Llanowar Elves","Cloud Sprite",
    "Goldmeadow Harrier","Kobolds of Kher Keep","Metallic Sliver",
    "Festering Goblin",
    # Tokens that have not been printed as a non-token card
    # See https://mtg.gamepedia.com/Token/Full_List#Tokens
    "Etherium Cell","Land Mine","Mask","Marit Lage","Kaldra","Carnivore","Twin",
    "Minor Demon","Urami","Karox Bladewing","Ashaya, the Awoken World",
    "Lightning Rager","Stoneforged Blade","Tuktuk the Returned","Mowu",
    "Stangg Twin","Butterfly","Hornet","Wasp","Wirefly","Ragavan","Kelp","Wood",
    "Wolves of the Hunt","Voja, Friend to Elves","Tombspawn","Feather",
]
TN2R = {n: md5(n.encode()).hexdigest() for n in token_names}

# "create a .... token named NAME" i.e. Cloudseeder
re_tkn_ref1 = re.compile(
    r"(.+? named) ({})".format('|'.join(list(TN2R.keys())))
)

# "create TOKEN NAME, .... token."
re_tkn_ref2 = re.compile(
    r"[C|c]reate ({}), (.+?) token".format('|'.join(list(TN2R.keys())))
)

# meld tokens from Eldritch Moon, found by the phrase "then meld them into NAME"
# however, since there are only three and no chance of conflict with other words
# we do a straight replacement re
meld_tokens = [
    'Brisela, Voice of Nightmares','Chittering Host','Hanweir, the Writhing Township'
]
MN2R = {n: md5(n.encode()).hexdigest() for n in meld_tokens}
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
NC2R = {n: md5(n.encode()).hexdigest() for n in named_cards}
re_oth_ref2 = re.compile(r"({})".format('|'.join(list(NC2R.keys()))))

def set_n2r(n2r):
    # call global IOT calculate the lengthy regex once during the first call
    # to tag (Could objectify the tagger and avoid this)
    global re_oth_ref
    global N2R
    if re_oth_ref is None:
        # IOT to avoid tagging cards like Sacrifice (an action and a card name) with
        # this expression have to search for card names preceded by 'named',
        # Partner with or Melds with
        re_oth_ref = re.compile(
            r"(named|Partner with|Melds with) ({})\b".format('|'.join(list(n2r.keys())))
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
re_cycling_pre = re.compile(r"\b(\w+?)cycling\b")  # seperate type & cycling
re_landwalk_pre = re.compile(r"(\w+?)(?<! land)walk(?!er)")  # seperate type & landwalk

####
## WORD HACKS
## word hacks 1) replace contractions with full words, 2) common mtg phrases with
## acronyms 3) idiosyncratic conjugations, contractions
##
####

word_hacks = {
    # contractions
    "can't":"can not","don't":"do not","didn't":"doed not","it's":"it is",
    "isn't":"is not","haven't":"have not","hasn't":"have not","aren't":"are not",
    "you're":"you are","couldn't":"could not","they're":"they are",'their':"they's",
    "doesn't":"dos not","you've":"you have","your":"you's","that's":"that is",
    "wasn't":"was not","weren't":"were not",
    # special
    'an':"a","command zone":"command",
    # plural
    "wolves":"wolfs","werewolves":"werewolfs","allies":"allys","elves":"elfs",
    "abilities":"abilitys","sorceries":"sorcerys","libraries":"librarys",
    "armies":"armys","aurochses":"aurochss","cyclopes":"cyclops","fishes":"fishs",
    "fungi":"fungess","homunculuses":"homunculuss","jellyfishes":"jellyfishs",
    "leeches":"leechs","mercenaries":"mercenarys","mongeese":"mongooss",
    "mice":"mouses","foxes":"foxs","nautiluses":"nautiluss","octopuses":"octopuss",
    "sphinxes":"sphinxs","thalakoses":"thalokoss",
    # acronyms
    "end of turn":"eot","converted mana cost":"cmc","converted mana costs":"cmcs",
    # suffixes/tense/possessive (ing,ed,s,'s)
    "activating":"activateing","activated":"activateed","activation":"activateion",
    "creating":"createing","created":"createed",
    "doubling":"doubleing","doubled":"doubled",
    "exchanging":"exchangeing","exchanged":"exchangeed",
    "equipped":"equiped",
    "exiling":"exileing","exiled":"exileed",
    "spliced":"spliceed",
    "fought":"fighted",
    "regenerating":"regenerateing","regenerated":"regenerateed",
    "sacrificing":"sacrificeing","sacrificed":"sacrificeed",
    "shuffling":"shuffleing","shuffled":"shuffleed",
    "dealt":"dealed",
    "leaving":"leaveing","left":"leaveed",
    "won":"wined","winning":"winned",
    "tied": 'tieed',
    "lost":"loseed","losing":"loseing",
    "its":"it's",
    "died":"dieed","dying":"dieing",
    "choosing":"chooseing","chose":"chooseed",
    "drawn":"drawed",
    "spent":"spended","unspent":"unspended",
    "proliferating":"proliferateing","proliferated":"proliferateed",
    "populating":"populateing","populated":"populateed",
    "voting":"voteing","voted":"voteed",
    "investigating":"investigateing","investigated":"investigateed",
    "exploring":"exploreing","explored":"explored",
    "copied":"copyed","copies":"copys",
    "removing":"removeing","removed":"removeed",
    "distributing":"distributeing","distributed":"distributeed",
    "got":"getted","getting":"geting",
    "moving":"moveing","moved":"moveed",
    "paid":"payed",
    "taking":"takeing","took":"takeed",
    "cycled":"cyclinged",  # IOT to match it as the past tense of a keyword
    "monstrous":"monstrosityed",
    "reducing":"reduceing","reduced":"reduceed",
    "declaring":"declareing","declared":"declareed",
    "has":"haves","had":"haveed","having":"haveing",
    "putting":"puting",
    "skipped": '"skiped', "skipping":"skiping",
    "produced":"produceed","producing":"produceing",
    "resolved":"resolveed","resolving":"resolveing",
    "did":"doed","does":"dos",
    "controlled":"controled",
    "caused":"causeed",
    "guesses":"guesss",
    "made":"maked","making":"makeing",
    "once":"1 time", "twice":"2 times",
    # status related
    "tapping":"taping","tapped":"taped","untapping":"untaped","untapped":"untaped",
    "flipping":"fliping","flipped":"fliped",
    "phased":"phaseed",
    "kicked":"kickered",

}
word_hack_tkns = '|'.join(word_hacks.keys())
re_word_hack = re.compile(r"\b({})\b".format(word_hack_tkns))

####
## EHGLISH WORD NUMBERS
####

E2I = { # twenty is Ulamog
    'one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7',
    'eight':'8','nine':'9','ten':'10','eleven':'11','twelve':'12','thirteen':'13',
    'fourteen':'14','fifteen':'15','sixteen':'16','seventeen':'17','eighteen':'18',
    'nineteen':'19','twenty':'20',
}
e2i_tkns = '|'.join(list(E2I.keys()))
re_wd2int = re.compile(r"\b({})\b".format(e2i_tkns))

####
## MISC
####

# reminder text including the space preceding
re_reminder = re.compile(r" ?\(.+?\)")

# modify modal spells IOT facilitate graphing:
#  1. find occurrences of ".•", as period is used by the grapher to delimit clauses
#  2. periods inside modal lines signify instructions to that option, find all
#   periods that are the last one
re_modal_blt = re.compile(r"\.•")
re_modal_lvl_instr_fix = re.compile(r"\.(?= )")

# modify level ups IOT facilitate graphing.
re_lvl_up = re.compile(r"^(level up {[^\n]+})\n")
re_lvl_blt = re.compile(r"\n(?=level)")

# modify sagas IOT facilitate graphing
re_saga_chapter = re.compile(r"\n([iv]+[,iv]*) — ")

####
## BEGIN MTGL REG EX
####

####
## QUANTIFIERS
####

# Quantifying words
# TODO:  combine "that is" and "that are" as a  single  quantifier?
lituus_quantifiers = [
    'a','target','each','all','any','every','another','other than','other','this',
    'that','additional','those','these','the','extra','first','second','third',
    'fourth','fifth','sixth','seventh','eighth','ninth','tenth','half','new',
    'single','same','different','next','last','opening','which',"chosen",'both',
    'either',
]
quantifier_tkns = '|'.join(lituus_quantifiers)
re_quantifier = re.compile(r"\b({})\b".format(quantifier_tkns))

####
## QUALFIERS
####

# Qualifying words
# TODO: not sure if this is the best place for 'back' or not

lituus_qualifiers = [
    'less','greater','lesser','highest','lowest','more','back','many','random',
    'also','maximum','most','much','alone',
]
qualifier_tkns = '|'.join(lituus_qualifiers)
re_qualifier = re.compile(r"\b({})\b".format(qualifier_tkns))

####
## NUMBERS
####

# numbers are 1 or more digits or one of the variable x, y, z which. Only those
# that are preceded by whitespace, a '/','+','-' or start a line and that are
# followed by whitespace '/' or '.' are matched.
re_number = re.compile(
    r"(?<=(?:^|[\s\/+-]))(\d+|x|y|z])(?=(?:[—\s\/+-\.:\n]|$))"
)

####
## ENTITIES
####

# keep suffix but check word boundary in beginning
objects = [  # objects 109.1 NOTE target can also be an object (115.1)
    'ability','card','copy','token','spell','permanent','emblem','source'
]
obj_tkns = '|'.join(objects)
re_obj = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(obj_tkns)
)

# keep suffix but check word boundary in beginning
# TODO: rest does not belong here
lituus_objects = [  # lituus objects
    "city's blessing", 'game','mana pool','mana cost','commander','mana','attacker',
    'blocker','itself','it','them','coin','choice','cost', "amount",'life total',
    'life','symbol','rest','monarch','pile','team','mode','level','value','number',
    'him','her','loyalty',
]
lobj_tkns = '|'.join(lituus_objects)
re_lituus_obj = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(lobj_tkns)
)

# lituus players - keep suffix but check word boundary in beginning
lituus_players = [
    'you','opponent','teammate','player','owner','controller','they',
]
ply_tkns = '|'.join(lituus_players)
re_lituus_ply = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(ply_tkns)
)

####
## TURN STRUCTURE
####

# phases 500.1 & 505.1 (collective Main Phase) Note: this will drop the word phase
phases = [
    'beginning','precombat main','combat','postcombat main','ending','main'
]
re_phase = re.compile(r"\b({}) phase".format('|'.join(phases)))

# because there are cases where combat is not followed by phase, have to do
# additional checks.
#  1. preceded by a quantifier this, each or that
#  2. preceded by a sequence (NOTE: they have not been tagged yet)
re_combat_phase = re.compile(r"\b(?<!<[^>]*)combat(?! damage)")

# steps
# 501.1 beginning phase steps - untap, upkeep, draw
# 506.1 combat phase steps - beginning of combat,  declare attackers,
#  declare blockers, combat damage, end of combat
# Note: this will drop the word step
# Note: because some steps do not include the word 'step' and some steps may mean
#  multiple things (i.e. untap, draw, end), there are two regexs
steps1 = ['untap','draw','end','combat damage']  # must be followed by 'step'
steps2 = [  # may or may not be followed by 'step'
    'upkeep','declare attackers','declare blockers','cleanup',
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
    "less than or equal to":LE,
    "no more than":LE,
    "greater than or equal to":GE,
    "less than":LT,
    "more than":GT,
    "greater than":GT,
    "equal to":EQ,
    "equal":EQ,
    "at least":GE,
    "plus":'+',
    "minus":'-',
    "exactly":EEQ,
}
op_keys = [
    "less than or equal to","no more than","greater than or equal to","less than",
    "more than","greater than","equal to","equal","at least","plus","minus",
    "exactly",
]
re_op = re.compile(r"\b({})\b".format('|'.join(list(op_keys))))
re_upto_op = re.compile(r"pr<up_to>(?= nu<[^>]+>)")
re_only_upto = re.compile(r"(op<≤> nu<([^>]+)> sq<time suffix=s>)")

# finds number or greater, less, more or fewer
re_num_op = re.compile(r"(nu<(?:\d+|x|y|z)>) or (greater|less|more|fewer)")

# prepositions (check for ending tags)
prepositions = [
    'top','bottom','up to','from','to','into','in','on','out','under','onto',
    'without','with','for','up','down','by','as though','as','of',
]
re_prep = re.compile(r"\b(?<!<[^>]*)({})\b(?!>)".format('|'.join(prepositions)))

# conditional/requirement related
conditionals = [
    'only if','if','would','could','unless','rather than','instead','may','except',
    'not','only','otherwise',
]
re_cond = re.compile(r"\b({})\b".format('|'.join(conditionals)))

# sequence/time related  words
sequences = [
    'before','after','until','beginning','end','ending','then','during',
    'as long as','simultaneously','time','again',
]
seq_tkns = '|'.join(sequences)
re_seq = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(seq_tkns)
)

####
## TRIGGER PREAMBLES
###

# trigger preambles 603.1
re_trigger = re.compile(r"\b(at|whenever|when)\b")

####
## COUNTERS
####

# counters 122.1 Updated 03-Julu-20 with M21
# two types p/t counters i.e +/-M/+/-N or a named counters (122 total ATT)
# see (https://mtg.gamepedia.com/Counter_(marker)/Full_List)
# Ikoria introduced keyword counters which will be kept separate
# NOTE: this must be done prior to keyword actions processing
re_pt_ctr = re.compile(r"(\+|-)nu<(\d+)>/(\+|-)nu<(\d+)> (counters*)\b")
named_counters = [
    'age','aim','arrow','arrowhead','awakening','blaze','blood','bounty','bribery',
    'brick','cage','carrion','charge','coin','credit','corpse','crystal','cube',
    'currency','death','delay','depletion','despair','devotion','divinity','doom',
    'dream','echo','egg','elixir','energy','eon','experience','eyeball','fade',
    'fate','feather','filibuster','flood','flying','fungus','fuse','gem','glyph',
    'gold','growth','hatchling','healing','hit','hoofprint','hour','hourglass',
    'hunger','ice','incarnation','incubation','infection','intervention',
    'isolation','javelin','ki','knowledge','level','lore','loyalty','luck',
    'magnet','manifestation','mannequin','mask','matrix','mine','mining','mire',
    'music','muster','net','omen','ore','page','pain','paralyzation','petal',
    'petrification','phylactery','pin','plague','poison','polyp','pressure','prey',
    'pupa','quest','rust','scream','shell','shield','silver','shred','sleep',
    'sleight','slime','slumber','soot','soul','spark','spore','storage','strife',
    'study','task','theft','tide','time','tower','training','trap','treasure',
    'velocity','verse','vitality','volatile','wage','winch','wind','wish',

]
named_ctr_tkns = '|'.join(named_counters)
re_named_ctr = re.compile(r"\b({}) counter(s)?\b".format(named_ctr_tkns))
iko_counters = [
    'deathtouch','double strike','first strike','flying','hexproof',
    'indestructible','lifelink','menace','reach','trample','vigilance',
]
iko_ctr_tkns = '|'.join(iko_counters)
re_iko_ctr = re.compile(r"\b({}) counter\b".format(iko_ctr_tkns))

# two of these coin and time will have already been misstagged as xo<coin>

####
## ABILITY WORDS, KEYWORDS, KEYWORD ACTIONS
####

ability_words = [  # ability words 207.2c Updated 25-May-20 with IKO
    "adamant","addendum","battalion","bloodrush","channel","chroma","cohort",
    "constellation","converge","council's dilemma","delirium","domain","eminence",
    "enrage","fateful hour","ferocious","formidable","grandeur","hellbent",
    "heroic","imprint","inspired","join forces","kinship","landfall","lieutenant",
    "metalcraft","morbid","parley","radiance","raid","rally","revolt",
    "spell mastery","strive","sweep","tempting offer","threshold","undergrowth",
    "will of the council",
]
aw_tkns = '|'.join(ability_words)
re_aw = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(aw_tkns)
)

keyword_actions = [  # (legal) Keyword actions 701.2 - 701.43 Updated IKO 25-May-20
    'activate','attach','unattach','cast','counter','create','destroy','discard',
    'double','exchange','exile','fight','play','regenerate','reveal','sacrifice',
    'scry','search','shuffle','tap','untap','fateseal','clash','abandon',
    'proliferate','transform','detain','populate','monstrosity','vote','bolster',
    'manifest','support','investigate','meld','goad','exert','explore','surveil',
    'adapt','amass','mill',
]
kwa_tkns = '|'.join(keyword_actions)
re_kw_act = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(kwa_tkns)
)

keywords = [  # (legal) Keyword Abilties 702.2 - 702,139 Updated IKO 25-May-20
    'deathtouch','defender','double strike','enchant','equip','first strike',
    'flash','flying','haste','hexproof','indestructible','intimidate','landwalk',
    'lifelink','protection','reach','shroud','trample','vigilance','banding',
    'rampage','cumulative upkeep','flanking','phasing','buyback','shadow',
    'cycling','cycle','echo','horsemanship','fading','kicker','multikicker',
    'flashback','madness','fear','morph','megamorph','amplify','provoke','storm',
    'affinity','entwine','modular','sunburst','bushido','soulshift','splice',
    'offering','ninjutsu','commander ninjutsu','epic','convoke','dredge',
    'transmute','bloodthirst','haunt','replicate','forecast','graft','recover',
    'ripple','split second','suspend','vanishing','absorb','aura swap','delve',
    'fortify','frenzy','gravestorm','poisonous','transfigure','champion',
    'changeling','evoke','hideaway','prowl','reinforce','conspire','persist',
    'wither','retrace','devour','exalted','unearth','cascade','annihilator',
    'level up','rebound','totem armor','infect','battle cry','living weapon',
    'undying','miracle','soulbond','overload','scavenge','unleash','cipher',
    'evolve','extort','fuse','bestow','tribute','dethrone','outlast','prowess',
    'dash','exploit','menace','renown','awaken','devoid','ingest','myriad',
    'surge','skulk','emerge','escalate','melee','crew','fabricate','partner with',
    'partner','undaunted','improvise','aftermath','embalm','eternalize','afflict',
    'ascend','assist','jump-start','mentor','afterlife','riot','spectacle',
    'escape','companion','mutate',
]
kw_tkns = '|'.join(keywords)
re_kw = re.compile(
    # NOTE: we have to add checks for the long hyphen and end of string to
    # ensure we tag all keywords
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(kw_tkns)
)

lituus_actions = [  # words not defined in the rules but important any way
    'put','remove','distribute','get','return','draw','move','look','pay','deal',
    'gain','attack','defend','unblock','block','add','enter','leave','choose',
    'die','spend','unspend','take','reduce','trigger','prevent','declare','have',
    'switch','assign','win','lose','tie','skip','flip','cycle','phase','become',
    'share','turn','produce','round','resolve','do','repeat','change','bid',
    'select','reselect','begin','separate','note','reorder','remain','can',
    'count','divide','cause','pair','guess','make','affect',
    'copy',  # will have already been tagged?
    'named',  # Special case we only want this specific conjugation
    'cost',  # will have already been tagged as an object
]
la_tkns = '|'.join(lituus_actions)
re_lituus_act = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(la_tkns)
)

# because target is primarily a quantifier we will only tag the verb version
# with suffix 's','ing' or 'ed' NOTE: currently have only seen 's'
re_lituus_target_verb = re.compile(r'\btarget(s|ing|ed)\b')

####
## EFFECTS
####

# (609) we only tag the word effect, combat damage and effect
# NOTE: These should not have already been tagged, but just in case
effects = ["combat damage","damage","effect"]
eff_tkns = '|'.join(effects)
re_effect = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(eff_tkns)
)

####
## CHARACTERISTICS
####

meta_characteristics = [  # 200.1 These are parts of a card
    'p/t','everything','text','name','mana cost','cmc','power','toughness',
    'color identity','color','type','kind',
]
re_meta_char = re.compile(r"{}".format('|'.join(meta_characteristics)))
re_meta_attr = re.compile(  # for meta characteristics
    r"(ch<(?:p/t|everything|text|name|mana cost|cmc|power|toughness|"
    r"color_identity|color|type)(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)*>)"
)

color_characteristics = [  # 105.1, 105.2a, 105.2b, 105.2c
    'white','blue','black','green','red','colorless','multicolored','monocolored'
]
re_clr_char = re.compile(r"{}".format('|'.join(color_characteristics)))

super_characteristics = ['legendary','basic','snow','world']  # 205.4a
re_super_char = re.compile(r"{}".format('|'.join(super_characteristics)))

type_characteristics = [  # 300.1, NOTE: we added historic
    'artifact','creature','enchantment','instant','land','planeswalker',
    'sorcery','tribal','historic',
]
re_type_char = re.compile(r"{}".format('|'.join(type_characteristics)))

# sub characteristics (updated 25-Jan-20 with IKO).

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
    "desert","forest","gate","island","lair","locus","mine","mountain",
    "plains","power-plant","swamp","tower","urza’s",
]
re_subtype_land_char = re.compile(r"{}".format('|'.join(subtype_land_characteristics)))

# 205.3j planeswalker types
subtype_planeswalker_characteristics = [
    "ajani","aminatou","angrath","arlinn","ashiok","bolas","calix","chandra",
    "dack","daretti","davriel","domri","dovin","elspeth","estrid","freyalise",
    "garruk","gideon","huatli","jace","jaya","karn","kasmina","kaya","kiora",
    "koth","liliana","lukka","nahiri","narset","nissa","nixilis","oko","ral",
    "rowan","saheeli","samut","sarkhan","serra","sorin","tamiyo","teferi","teyo",
    "tezzeret","tibalt","ugin","venser","vivien","vraska","will","windgrace",
    "wrenn","xenagos","yanggu","yanling",
]
re_subtype_planeswalker_char = re.compile(
    r"{}".format('|'.join(subtype_planeswalker_characteristics))
)

# 205.3k instant/sorcery subtypes
subtype_instant_sorcery_characteristics = ["adventure","arcane","trap", ]
re_subtype_instant_sorcery_char = re.compile(
    r"{}".format('|'.join(subtype_instant_sorcery_characteristics))
)

# 205.3m creature subtypes (updated 03-Jul-20 with M21)
subtype_creature_characteristics = [
    "advisor","aetherborn","ally","angel","antelope","ape","archer","archon",
    "army","artificer","assassin","assembly-worker","atog","aurochs","avatar",
    "azra","badger","barbarian","basilisk","bat","bear","beast","beeble",
    "berserker","bird","blinkmoth","boar","bringer","brushwagg","camarid","camel",
    "caribou","carrier","cat","centaur","cephalid","chimera","citizen","cleric",
    "cockatrice","construct","coward","crab","crocodile","cyclops","dauthi",
    "demigod","demon","deserter","devil","dinosaur","djinn","dog","dragon","drake",
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
    "noggle","nomad","nymph","octopus","ogre","ooze","orb","orc","orgg","otter",
    "ouphe","ox","oyster","pangolin","peasant","pegasus","pentavite","pest",
    "phelddagrif","phoenix","pilot","pincher","pirate","plant","praetor","prism",
    "processor","rabbit","rat","rebel","reflection","rhino","rigger","rogue",
    "sable","salamander","samurai","sand","saproling","satyr","scarecrow","scion",
    "scorpion","scout","sculpture","serf","serpent","servo","shade","shaman",
    "shapeshifter","shark","sheep","siren","skeleton","slith","sliver","slug",
    "snake","soldier","soltari","spawn","specter","spellshaper","sphinx","spider",
    "spike","spirit","splinter","sponge","squid","squirrel","starfish","surrakar",
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
subtypes_of = [
    'artifact','enchantment','land','planeswalker','instant∨sorcery','creature'
]
TYPE_ARTIFACT = 0
TYPE_ENCHANTMENT = 1
TYPE_LAND = 2
TYPE_PLANESWALKER = 3
TYPE_INSTANT_SORCERY = 4
TYPE_CREATURE = 5

def subtype(st):
    """
    given a subtype st returns the type
    :param st: string subtype
    :return: TYPE code
    """
    if st in subtype_artifact_characteristics:
        return TYPE_ARTIFACT
    elif st in subtype_enchantment_characteristics:
        return TYPE_ENCHANTMENT
    elif st in subtype_land_characteristics:
        return TYPE_LAND
    elif st in subtype_planeswalker_characteristics:
        return TYPE_PLANESWALKER
    elif st in subtype_instant_sorcery_characteristics:
        return TYPE_INSTANT_SORCERY
    elif st in subtype_creature_characteristics:
        return TYPE_CREATURE
    else:
        raise lts.LituusException(lts.EMTGL, "{} is not a subtype".format(st))

def subtype_of(st, mt):
    """
    determines if subtype st is a subtype of type mt
    :param st: the subtyype i.e 'dragon'
    :param mt: the type i.e. 'creature'
    :return: True if st is a subtype of mt, False otherwise
    """
    tc = subtype(st)
    if tc == TYPE_ARTIFACT and mt == 'artifact':
        return True
    elif tc == TYPE_ENCHANTMENT and mt == 'enchantment':
        return True
    elif tc == TYPE_LAND and mt == 'land':
        return True
    elif tc == TYPE_PLANESWALKER and mt == 'planeswalker':
        return True
    elif tc == TYPE_INSTANT_SORCERY and mt == 'instant':
        return True
    elif tc == TYPE_INSTANT_SORCERY and mt == 'sorcery':
        return True
    elif tc == TYPE_CREATURE and mt == 'creature':
        return True
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
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(char_tkns)
)

# seperate procedure for tagging p/t has to be done after numbers are tagged
re_ch_pt = re.compile(r"(\+|-)?nu<(\d+|x|y|z)>/(\+|-)?nu<(\d+|x|y|z)>(?! counter)")

# meta 'attribute' values see Rathi Intimidator picks out three values 1) the
# attribute, 2) the operator and 3) the value of the attribute
re_attr_val = re.compile(r"xr<([^>]+)> op<([⊕⋖⋗≤≥≡])> nu<(\d+|x|y|z)>")

# meta 'attribute' values see Triskaidekaphobia where a lituus object preceded
# by a number can be instantiated as an attribute. We only want vanilla lituus
# objects, that is, they do not have an attribute list
# NOTE: this should only be life or mana
# TODO: may need to relook 'mana'
re_op_num_lo = re.compile(r"op<(.)> nu<([^>]+)> xo<(\w+)>")

# damage preceded by a number should be combined
re_num_dmg = re.compile(r"nu<([^>]+)> ef<(\w*damage)>")

# exception cases for three cards Void Winnower, Gyruda and Isperia
# TODO: could we add 'different' here as well, perhaps some other quantifiers
re_attr_val_wd = re.compile(r"(?:xq<a> )?xc<(odd|even)> xr<([^>]+)( suffix=s)?>")

# meta 'attribute' value see Repeal where no operator is present
re_attr_val_nop = re.compile(r"xr<([^>]+)> nu<(\d+|x|y|z)>")

# colored will be tagged as xr<color suffix=ed> need to switch this
re_attr_colored = re.compile(r"xr<((?:mono)?color) suffix=ed>")

# ... base power and toughness X/Y i.e. Godhead of Awe then power and toughness
# i.e Transmutation
re_base_pt = re.compile(r"base ch<power> and ch<toughness> (ch<p/t[^>]*>)")

# if after instantiatiating attributes we want to 'chain' cases of
#  power and/or toughness where toughness has a value i.e. Tetsuko Umezawa,
#  Fugitive
re_combine_pt = re.compile(r"xr<power> (and|or|and/or) xr<toughness val=([^>]+)>")

# lituus characteristics
# TODO: keep control, own?
lituus_characteristics = [
    'life total','control','own','life','hand size','devotion','odd','even',
]
lch_tkns = '|'.join(lituus_characteristics)
re_lituus_ch = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(lch_tkns)
)

####
## ZONES
####

# zones 400.1
zones = [
    'library','hand','battlefield','graveyard','stack','exile','command',
    'anywhere','zone',
]
zn_tkns = '|'.join(zones)
re_zone = re.compile(
    r"\b(?<!<[^>]*)({})(?=(?:s|ing|ed|ion|\'s|s\'|:|\.|,|\n|\"|\'| |—|$))".format(zn_tkns)
)

####
## STATUS
####

# Status 110.5, is hard as they are status words only in past tense except for
# face up/face down which have hyphens (see Break Open) As status they appear:
#  'tapped','untapped',
#  'flipped','unflipped',
#  'face-up','face-down',
#  'phased-in','phased-out'
# NOTE: excluding reminder text (which we remove) there is only 1 card, Time and
#  Tide that has a status involving Phasing
# Status will have already been tagged as something else therefore, we list them
# here and provide Status Deconfliction further on

status = ['tap','flip','phase','face']

# lituus status
# As above, these will have already been tagged as something and will have to
# be deconficted - they are only listed here for reference
lituus_status = [
    'attacking','blocking','defending','transformed','enchanted','equipped',
    'exiled','unattached','attached','activated','triggered','revealed',
    'suspended','kicked','discarded','cycled',
]

####
## DECONFLICTIONS
####

## Action/Status

# Past tense deconflictions: transform, suspend, [un]attach. reveal are keywords
# /keyword actions that are statuses if they have an 'ed' suffix
re_ed_lituus_status = re.compile(
    r"(k[aw])(?=<(?:transform|suspend|(?:un)?attach|reveal) suffix=ed>)"
)

# Past tense deconflictions: enchant, equip and exile are keywords/keyword actions
# that are statuses if they have an 'ed' suffix and precede a Thing (have to check
# for players as well as objects - don't think lituus objects but check hough)
re_ed_thing_lituus_status = re.compile(
    r"(k[aw])(?=<(?:enchant|equip|exile) suffix=ed> (?:ob|xp|xo))"
)

# combat related attacking, blocking, and tapped that are conjoined. In the first
# term we have to check for both ka and st with regards to tapped because cards
# like Geist of Saint Traft have incorrectly tagged status.
# This matches the phrases "tapped and attacking","attacking or blocking and
# "unblocked attacking"
re_combat_status_chain = re.compile(
    r"(st|ka|xa)<((?:un)?(?:tap|attack|block)) suffix=(ed|ing)>"
    r"(?: ?(and|or|and/or)? )"
    r"xa<(attack|block) suffix=ing>"
)

# the remainder of attacking, blocking, and defending will be considered statuses
# unless they are preceded by an is/not or a Thing or followed by a "does not"
# (Johan) and
#
re_combat_status = re.compile(
    r"(?<!(?:(?:ob|xo|xp)<\w+?>|is|are|was|be)(?: cn<not>)? )"
    r"xa<((?:un|¬)?attack|block|defend) suffix=ing>"
    r"(?! does cn<not>)"
)
# TODO: commented out for now (un)blocked will be always be considered a status
#  if not preced by is/is not
#re_blocked_status = re.compile(
#    r"(?<!(xa<(?:is|be|become)[^>]*>)(?: cn<not>)? )"
#    r"xa<(un)?block suffix=ed>"
#)

# activated/triggered
# finds the phrase "activated or triggered i.e. Stifle (5 total)
re_ab_type_chain = re.compile(r"ka<activate suffix=ed> or xa<trigger suffix=ed>")

# when activate or trigger with suffex ed is followed by an object it is a status
re_ab_status = re.compile(r"[kx]a<(activate|trigger) suffix=ed>(?= ob)")

# activation cost - combine this as activation_cost
re_activation_cost = re.compile(r"ka<activate suffix=ion> xo<cost( suffix=s)?>")

# Target
# target may be a quantifier, an object (115.1) or an action (Bronze Horze).

# special case (2 cards Meddle, Quicksilver Dragon) that contain the phrase
# "target and that target" - here both are objects
re_target_sc = re.compile(r"xq<target> and xq<that> xq<target>")

# that target (aside from above), could target and can target are references to an action
re_target_act = re.compile(r"(?<=(?:xq<that>|cn<could>|xa<can>) )(xq<target>)")

# Find target quantifier that is not followed by an mtg object, a status or
# a player/opponent - these are objects
re_target_obj = re.compile(
    r"(xq<target>)"
    r"(?! (?:ob|st|xs|xo<commander>|(?:xp<(?:player|opponent(?: suffix=(?:s|s'|'s))?))))"
)

# Copy
# copy by default is tagged as an object but can be an action. NOTE: some
# deconfliction has already occurred in consecutive object handling

# copy followed by a quantifier or 'it' is an action
re_copy_act = re.compile(r"(ob<copy( suffix=s)?>)(?= (?:xq<|xo<it>))")

## Keywords that may be actions and/or statuses

# three steps:
# 1. kicker: (see Tempest Owl) if kicker has a suffix of 'ed' and is preceded
#  by "was" it is an action
# 2. be or it: (see Tetravus,Tar Fiend) if a keyword has a suffix of 'ed' and is
#  preceded by 'be' or 'it', it is an action
# 3. is: (see Kor Duelist) if a keyword has a suffix of 'ed' and is preceded by
#  'is' it is a status
#  TODO: unless preceded by be
# 4. suffix=s: (see Sidis, Undead Vizier) a keyword with suffix 's' preceded by
#  a Thing will be considered and action
re_kicker_act = re.compile(r"(?<=was )kw<kicker suffix=ed>")
re_be_kw = re.compile(r"(?<=(?:be|xo<it>) )kw<([^>]+?) suffix=ed>")
re_kw_status = re.compile(r"(?<=is )kw<([^>]+?) suffix=ed>")
re_kw_action = re.compile(r"(?<=(?:xp|ob|xo)<[^>]+> )kw<([^>]+?) suffix=s>")

# action words that are statuses
# action words with a suffix of 'ed' that are preceded by a quantifier and
# followed by an object are statuses i.e. Xathrid Demon
re_action_status = re.compile(
    r"(?<=xq<[^>]+> )(?:ka|xa)<([^ ]+ suffix=ed)>(?= ob<[^>]+>)"
)

# consecutive (non-possessive) turn structures i.e. Dwarven Sea Clan
re_consecutive_ts = re.compile(r"ts<(\w+)> ts<step>")

# declare attackers|blockers
re_declare_step = re.compile(r"xa<declare> xo<([^>]+?) suffix=s> ts<step>")

# incorrectly tagged draw
re_draw_step = re.compile(r"(xq<[^>]+>) xa<draw>")

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
    "color identity":"color_identity",  # "mana cost":"mana_cost",
    "life total":"life_total","rather than":"rather_than","as though":"as_though",
    "did not":"did_not","other than":"other_than"
}
val_join_tkns = '|'.join(val_join.keys())
re_val_join = re.compile(r"(?<=[<=])({})(?=>)".format(val_join_tkns))
# TODO: this would be better done via a regular expression vice a dict

# Negated tags i.e. non-XX<...>
re_negate_tag = re.compile(r"non-(\w\w)<([^>]+)>")

# Hanging Basic finds the supertype not followed by an explicit land
re_hanging_basic = re.compile(r"(ch<¬?basic>)(?! ch<land[^>]*>)")

# Hanging Snow finds the supertype that is followed by a land subtype (with no
# explicit 'land' inbetween NOTE: we are only checking the FIVE basic subtypes
re_hanging_snow = re.compile(
    r"(ch<¬?snow>)(?= ch<¬?(?:forest|island|mountain|plains|swamp)[^>]*>)"
)

# phrases related to number of something
#  1. use nu<y> to denote "the number of" i.e. Beseech the Queen "less than or
#   equal to the number of lands"
#  2. use nu<z> to denote "any number of" i.e. Ad Nauseum "any number of times"
#  3. remove "are each" if followed by an operator
re_equal_y = re.compile(r"(?<=op<[⊕⋖⋗≤≥≡]> )(xq<the> number of)")
re_equal_z = re.compile(r"xq<any> number of")
re_are_each = re.compile(r"are xq<each> (?=op<[⊕⋖⋗≤≥≡]>)")

# find xo<mana cost> for conversion
re_mana_cost = re.compile(r"xo<mana cost( suffix=s)?>")

# find 'no' followed by a thing or quanitifier
re_no_thing = re.compile(r"no(?= (?:ob|xp|xo|zn|xq))")

####
## STATUS DECONFLICTION
####

# only looking at tap and flip - it will be a status only if there is a suffix
# of 'ed' and it is not preceded by 'is'
re_status = re.compile(
    r"(?<!is )(?:[kx]a)<(un)?({}) suffix=ed>".format('|'.join(status[0:2]))
)

# in some cases, if 'tapped' is preceded by an 'is', it is a status but only if
# it is not followed by a 'for'
re_status_tap = re.compile(r"(?<=is )(?:[kx]a)<(un)?tap suffix=ed>(?! pr<for>)")

# Phase can be Status, Action or Turn Structure
# See Time and Tide for example of phased as a status and as an action
re_status_phase = re.compile(r"xa<phase suffix=ed>-pr<(in|out)>")  # all status have a hyphen
re_action_phase = re.compile(r"xa<phase(?: suffix=(s|ed))?> pr<(in|out)>")
re_ts_phase = re.compile(r"xa<phase>(s?)(?=\W)")

# face can be a Status (has a hyphen) i.e. Pull from Eternity or a modifier to
# an action i.e. Bomat Courier
#  "...exile the top card of your library face down.", generally 'turn'
re_status_face = re.compile(r"face-pr<(up|down)>")
re_mod_face = re.compile(r"face pr<(up|down)>")

####
## TURN (ACTION|OBJECT) DECONFLICTION
####

# turn is an action if it is followed by a 'xm' (modifier) or 'xq' (quantifier)
re_turn_action = re.compile(r"ts<(turn[^>]*)>(?= (?:xm|xq)<[^>]+>)")

# turn can be considered an object if preceded by a
#  [a][conjoined quantifiers] [turn structure]
# TODO: need to consider other quantifiers possibley this|that
# TODO: need to consider possessive turn structure see Gisa and Geralf "your turn"
# TODO: do we want to retag the turn strucutre i.e. turn-phase
re_turn_object = re.compile(r"(xq<(?:a(?:[∧∨⊕][^>]+)?)>) ts<([^>]+)>")

####
## ZONE DECONFLICTION
####
# find exile preceded by a preposition
re_zn_exile = re.compile(r"(?<=pr<[^>]+> )(ka<exile>)")

####
## COST DECONFLICTION
####

# cost as object vs action
# Cost is tagged as an object by default. Any 'cost' followed by a mana symbol or
# "up to" and a mana symbol can be changed as can costs followed by a number or
# operator number (i.e. Trinisphere)
# Activated Abilities reduction (Training Grounds, Biomancer's Familiar, Heartstone
# & Power Artifact)
# "...mana an ability/object costs to...'
# After this there are 3 'exceptions' Valiant Changleling, Brutal Suppression,
#  and Drought
re_cost_mana = re.compile(
    r"xo<cost( suffix=s)?>(?= (?:pr<up_to> )?{(?:[0-9wubrgscpx\/]+)})"
)
re_cost_num = re.compile(
    r"xo<cost( suffix=s)?>(?= (?:op<[⊕⋖⋗≤≥≡]> )?nu<(?:[0-9wubrgscpx\/]+)>)"
)
re_cost_aa = re.compile(r"(?<=ob<[^>+]> )xo<cost( suffix=s)?>")
re_cost_except = re.compile(  # Drought and Brutal Suppresion and Valiant Changeling
    r"xo<cost( suffix=s)?>(?= (?:xq<a> xq<additional>|by more than))"
)

# flip as action vs object
#  1. flip is an object if it is preceded by a quantifier or a number
#  2. flip is an object if preceded by coin
re_flip_object = re.compile(r"(?<=(?:xq<[^>]+>|nu<[^>]+>) )xa<flip( suffix=s)?>")
re_coin_flip = re.compile(r"xo<coin> xa<flip>")

# 'counters' as action vs lituus object
# two cards Baral and Lullmage mentor have counters that is an action all others
# are counters that put on a permanent
# in the case of ka<counter> if it is preceded by xq<a> or a preposition (Soul
# Diviner, Vorel) it as an object counter
re_counters_obj = re.compile(r"ka<counter suffix=s>(?! xq<(?:target|a))")
re_counter_obj = re.compile(r"(?<=(xq<a>|pr<[^>]+>) )(ka<counter>)")

####
## MISC DECONFLICTION
####

# misstagged - because of the order in which tags are applied some portions of
# tags are incorrectly tagged i.e. Cumulative Upkeep which is tagged as
# cummulative ts<upkeep>
misstag = {
    "ch<will> pr<of> xq<the> council":"aw<will_of_the_council>",
    "xq<first> strike":"kw<first_strike>",
    "cumulative ts<upkeep>":"kw<cumlative_upkeep>",
    "xo<commander> kw<ninjutsu>":"kw<commander ninjutsu>",
    "xo<level> pr<up>":"kw<level_up>","split xq<second>":"kw<split_second>",
    "pr<as> long pr<as>":"sq<as_long_as>","ob<spell> mastery":"aw<spell_mastery>",
}
misstag_tkns = '|'.join(misstag.keys())
re_misstag = re.compile(r"({})".format(misstag_tkns))

# from combat find untagged combat preceded by from
re_from_combat = re.compile(r"(?<=pr<from> )ts<combat>")

# finds phrase tapped and attacking (suffixes have not been handled yet)
# re_tna = re.compile(r"(?<=st<tapped> and )(xa)(?=<attack>ing)")

# discarded is a status if it is preceded by the and followed by card
re_discard_stat = re.compile(r"(?<=xq<the> )ka<discard suffix=ed>(?= ob<)")

# enchated is a status if it is preceded by that_is/that_are
re_enchant_stat = re.compile(
    r"(?<=xq<that> xa<is(?:[^>]+)?> )kw<enchant suffix=ed>"
)

# (un)spent is a status if followed by mana
re_spend_stat = re.compile(r"xa<(un)?spend suffix=ed>(?= xo)")

# 'at' is a preposition if followed by a qualifier (random) i.e. Black Cat or
#  status i.e. Lens of Clarity or preceeded by 'look' i.e. Lens of Clarity
re_at_prep = re.compile(r"(tp<at>)(?= (?:xl|st)<[^>]+>)")
re_at_prep2 = re.compile(r"(?<=xa<look> )(tp<at>)")

# no nu<1> needs to be retagged
re_no_one = re.compile(r"no nu<1>")

# pw<with> nu<0> needs to be retagged (only 2 Hindervines & Muraganda Petroglyphs)
re_with_null = re.compile(r"pr<with> nu<0>")

# no followed by damage
re_no_dmg = re.compile(r"no (ef<(?:combat_)?damage>)")

####
## SUFFICES
####

# move any suffices 'r','s','ing' 'ed' or "'s" to parameters inside tags
re_suffix = re.compile(r"(\w\w)<([^>]+)>(s'|s|ion|ing|ed|'s)")

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

# two consecutive types (separated by a space) or a conjuction i.e. Grisly Spectacle
# and Mox Amber. This is commonly artifact creature
# NOTE: on the first type we should not see any attributes
re_align_dual = re.compile(
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    r" (?:(and|or|and/or) )?"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
)

# 2 or more consecutive types. Cards like Warden of the First Tree and Figure of
# Destiny, We capture it here just in case future cards display this behavior.
# This will default to dual types as above for exactly 2 consecutive types
re_align_n = re.compile(
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    r" (?:(and|or|and/or) )?"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    r"(?: (ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>))*"
)

# 205.4b ... some supertypes are closely identified with specific card types...
# Basic imply lands and world implies enchantment
# when we have a supertype followed immediately by a card type, combine these as
# the supertype applies to the card type and to the object (implied or explicit)
# For example Wave of Vitriol, "...all artifacts, enchantments, and nonbasic
# lands they control... nonbasic applies to lands and not to the permanents that
# must be sacrified
# NOTE: We are assuming that super-type alignments are all space-delimited
re_align_super = re.compile(
    r"(ch<¬?(?:legendary|basic|snow|world)> )+"
     r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
    r"(?:[∧∨⊕→]¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))*[^>]*>)"
)

# on or more space delimited subtypes followed by a type will be aligned. We have
# to account for dual types that may already be aligned
# NOTE: as above we assume sub-type alignments are all space-delimited
# NOTE: see "Quest for Ula's Temple" after alignment we have:
# ... xa<put> xq<a> ch<kraken>, ch<leviathan>, ch<octopus>, or ch<creature→serpent>
# ob<card>. Only serpent has been aligned to creature. During chaining, the
# remaining subtypes will be chained
re_align_sub = re.compile(
    r"(ch<¬?(?:" + re_sub_char.pattern + ")> )+"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)"
    r"(?:[∧∨⊕→]¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))*"
    r"(?: [\w\+\-/=¬∧∨⊕⋖⋗≤≥≡⇔→'\(\)]+?)*>)"
)

# hanging subtypes are those subtype characteristics that are not followed by
# a type characteristic.
re_hanging_subtype = re.compile(
    r"(ch<¬?(?:" + re_sub_char.pattern + ")[^>]*>)"
     r"(?! ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
)

# An anamoulous phrasing found in 3 cards (Assassin's Blade, Exile, Tilonalli's
# Skinshifter) where characteristics are separated by an action (attacking)
# TODO: so far have only found cases where the action is attacking. have to be
#  on the lookout for other tokens
re_disjoint_ch = re.compile(
    r"(ch<(?:¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored|"
     r"historic|legendary|basic|snow|world))>) (xa<[^>]+>) (ch<[^>]+>)"
)

####
## CHAINS
# Sequential characteristics
####

# ... p/t X/Y or p/t A/B ...
re_pt_chain = re.compile(r"(ch<p/t[^>]+>) or (ch<p/t[^>]+>)")

# chain two or more sequential tags of the same id having the form
#   [tid 1, ..., tid n-2] tid n-1[,] conjunction op tid n
# that can be combined into a single tag
def re_chain(tid):
    """
    compiles a conjunction chaing pattern of type tid
    :param tid: the two letter tag-id to search for
    :return: regex.Pattern
    """
    return re.compile(
        r"((?:{0}<[^>]+>, )*)({0}<[^>]+>),? (and|or|and/or) ({0}<[^>]+>)".format(tid)
    )

# above not working for quantifiers TODO: why
re_chain_quantifiers = re.compile(r"xq<[^>]+> xq<[^>]+>( xq<[^>]+>)*")

# a subset of the conjunction_chain that matches only color chains
re_clr_conjunction_chain = re.compile(
    r"((?:ch<¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)>, )*)"
    r"(ch<¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)>)"
    r",? (and|or|and/or) "
    r"(ch<¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)>)"
)

# currently only 1 card found with this pattern, Seize the Soul, Destroy target
# nonwhite, nonblack creature.
re_clr_conjunction_chain_special = re.compile(
    r"(ch<¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)>), "
     r"(ch<¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)>)"
)

# search for color conjunction type only 2, Soldevi Adnate and Tezzeret's
# Gatebreaker. These are special cases
re_clr_conj_type = re.compile(
    r"ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored))>"
    r" (and|or|and\or) "
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
)

# a subset of the conjunction_chain that matches only type chains
re_type_conjunction_chain = re.compile(
    r"((?:ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>, )*)"
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    r",? (and|or|and/or) "
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
)

# color type pairs where the pair is not preceded by or followed by a characteristic
# matches the color value and the type tag
re_clr_type_chain = re.compile(
    r"(?<!ch<[^>]+> )"
    r"(?:ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)"
    r"(?:[∧∨⊕]¬?(?:white|blue|black|green|red))*)>)"
    r" "
    r"(ch<¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    r"(?! ch<[^>]+>)"
)

# phrases of the form CHAR, TYPE[...] where CHAR is predominately a type except
# in Lay Bare the Heart (supertype) and Urborg Stalker (color). Several of these
# i.e. Martyrdom are part of a larger or clause (arget creature, planeswalker, or
# player) so it also captures any trailing conjunctions
re_conjunction_chain_special = re.compile(
    r"ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored|"
    r"artifact|creature|enchantment|instant|land|planeswalker|sorcery|tribal|"
    r"historic|legendary|basic|snow|world))>"
    r", (ch<[^>]+>)(?:, (and|or|and/or))?"
)

# Price of Betrayal is an exception handled here
# NOTE: after above Price of Betrayal will look like
#  ... ob<permanent characteristics=artifact∧creature>,
#    ob<permanent characteristics=planeswalker>, or xp<opponent>.
# we will have one characteristic that is anded and one not. Additionally the last
# object on the right of the conjuunction operator is a player so it won't be joined
re_pob_chain = re.compile(
    r"ch<(¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))"
    r"[∧∨⊕](¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))>"
    r", "
    r"ch<(¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery))>"
    r"(?:, (and|or|and/or))"
)

####
## REIFICATION
####

# Phrases of the form [SUPER] [P/T] [COLOR] TYPE [OBJECT]. This requires colors
# types have been chained and aligned
re_reify_phrase = re.compile(
    # optional super-type (value only)
    r"(?:ch<(¬?legendary|basic|snow|world)> )?"
    # optional p/t (value only)
    r"(?:ch<p/t val=([\d|x|y|z]+/[\d|x|y|z]+)> )?"
    # optional a color characteristic followed by 0 or more conjunction, color pairs
    r"(?:ch<(¬?(?:white|blue|black|green|red|colorless|multicolored|monocolored)"
    r"(?:[∧∨⊕]¬?(?:white|blue|black|green|red))*)> )?"
    # mandatory type characteristic
    r"(ch<\(?¬?(?:artifact|creature|enchantment|instant|land|planeswalker|sorcery)[^>]*>)"
    # optional object
    r"(?: (ob<[^>]+>))?"
)

# after above we have some non-type characteristics followed by an object i.e.
# Unmask. The characteristic may be complex but will not have an attribute dict.
# matches the tag-value of the characteristic and the complete tag of the object
re_reify_single = re.compile(r"ch<([^>]+)> (ob<[^>]+>)")

# finds singleton characteristics left over after reify_phrase, reify_single
# these can reified into an attribute
re_reify_singleton_char = re.compile(r"(ch<[^>]+>)")

# finds two consecutive space delimited objects. This may be permanent card i.e.
# Celestial Gatekeeper possesive i.e Teferi's Response or nontoken permanent i.e.
# City in a Bottle
re_consecutive_obj = re.compile(r"(ob<[^>]+>) (ob<[^>]+>)")

####
## MISC POST CHAIN OPERATIONS
####

# find 'no' followed by an object
re_no2num = re.compile(r"(no)(?= ob<)")

# find phrases of the form ATTR OP with no following number
re_uninit_attr = re.compile(
    r"xr<(p/t|everything|text|name|mana cost|cmc|power|toughness|"
    r"color_identity|color|type)> op<(.)>(?! nu)"
)

####
## MERGE
####

# phrases of the form OBJECT with KEYWORD (assumes chained keywords)
re_obj_with_kw = re.compile(r"(ob<[^>]+>) pr<with> kw<([^>]+)>")

# abilities can be preceded by mana, triggered, activated and in one case "bands
# with other"
# NOTE: Assumes that statuses have had their stem and suffix combined
re_ability_type = re.compile(
    r"(?:(?:xs|xo)<(\w+)>|(\"bands pr<with> xq<other>\")) (ob<ability[^>]*>)"
)

####
## POST PROCESS
####

# find cost preceded by a keyword i.e. Rafter Demon
re_cost_type = re.compile(r"(kw<[\w-]+>) (xo<cost[^>]*>)")

# find punctuation immediately followed by quotations
re_encl_punct = re.compile(r"([\.\,])(\'\"|\'|\")")

# find status with suffix (these should all be (un)tap but catch
# everything just in case
re_status_suffix = re.compile(r"(st|xs)<(\w+) suffix=(\w+)>")

# tagging verb "to be" forms: 'is', 'are' and 'was', 'were' doing this after
# other tagging to avoid rewriting a lot of patterns
is_forms = {
    'is':'xa<is>','are':'xa<is>','was':'xa<is suffix=ed>','were':'xa<is suffix=ed>',
    'be':'xa<be>','been':'xa<be suffix=ed>',
}
is_forms_tkns = '|'.join(list(is_forms.keys()))
re_is2tag = re.compile(r"\b({})\b".format(is_forms_tkns))

# OPERATOR NUMBER
re_op_num = re.compile(r"op<(.)> nu<([^>]+)>")

# power and toughness = y - have to check that it is not preceded by a power = y
re_pt_value = re.compile(
    r"(?<!xr<power val=[^>]+>[^\.]+)xr<power> and xr<toughness val=([^>]+)>"
)

####
## PHRASING
####

# find common phrases that can be replaced by keyword actions or slang

# mill
#  can be targeted i.e. their library or the player i.e. your library
#  can specify the number of cards "top 2 cards" or not "top card"
re_mill = re.compile(
    r"xa<put( suffix=\w+)?> xq<the> pr<top> (?:(nu<[^>]+>) )?ob<card[^>]*> "
    r"pr<of> (xp|xq)<[^>]+> zn<library> pr<into> (xp|xq)<[^>]+> zn<graveyard>"
)

# detain i.e. Mythos of Vadrok
# [thing] can't attack or block and its activated abilities cant be activated
re_detain = re.compile(
    r"(?<=[,|\.|\n] )([^,|^\.]+) xa<can> cn<not> xa<attack> or xa<block> and "
     r"([^,|^\.]+) ob<ability[^>]+> xa<can> cn<not> xa<be> ka<activate[^>]+>"
)

# loot i.e. Merfolk Looter
# [draw] [cards],? then [discard] [cards]
#re_loot = re.compile(
#    r"xa<draw> (xq<a>|nu<[^>]+>) ob<card(?: suffix=s)?>,? "
#     r"sq<then> ka<discard> (xq<a>|nu<[^>]+>) ob<card(?: suffix=s)?>"
#)

# flicker i.e. Essence Flux
# exile [thing] then return it to the battlefield [status]? under it's owner control
re_flicker = re.compile(
    r"ka<exile> ([^,]+),? sq<then> xa<return> ([^,|\.]+) pr<to> xq<the> "
     r"zn<battlefield> (?:([^,|\.]+) )?pr<under> xo<it suffix='s> "
     r"xp<owner suffix='s> xc<control>"
)

# blink (long flicker)
# re_blink = re.compile(r"")

# etb and ltb (NOTE: matching any suffix which should only be 'tense'
re_etb = re.compile(r"xa<enter( [^>]+)?> xq<the> zn<battlefield>")
re_ltb = re.compile(r"xa<leave( [^>]+)?> xq<the> zn<battlefield>")

# [thinb] able to block [thing] do so is difficult for the grapher
# NOTE: prefixes have not been applied to action verbs yet
re_able_to_block = re.compile(r"(.+) able pr<to> xa<block> (.+) xa<do> so")

# your opponents can be combined
re_your_opponents = re.compile(r"xp<you suffix='s> xp<opponent suffix=s>")
re_one_of_opponents = re.compile(r"nu<1> pr<of> xp<opponent suffix=s>")

# own, control related - We want to remove "do not" replaceing it with the negation
# sign and standarize others
# a. both own and control (Graf Rats) -can remove 'both'
# b. neither own nor control (Conjured Currency) -replace neither with "do not"
# c you control but do not own (Thieving Amalgam) -and the own & control negating control
# d. you don't control (Aether tradewinds) and don't own (Agent of Treachery)
re_both_ownctrl = re.compile(r"xq<both> (xc<own∧control>)")
re_neither_ownctrl = re.compile(r"neither xc<own> nor xc<control>")
re_own_not_ctrl = re.compile(r"xc<control> but xa<do> cn<not> xc<own>")
re_dont_ownctrl = re.compile(r"xa<do[^>]*> cn<not> xc<(own|control)>")

# action word prefixs
#  either a form of 'to be' 'action-word' or 'to' 'action-word'
re_prefix_aw = re.compile(
    r"((?:xa|pr)<(?:is|be|become|to)[^>]*>) (?:(cn<not>) )?((?:xa|ka)<[^>]+>)"
)

# player's own phase (own is redudndant) - only found in Dosan and City of Solitude
re_ply_own_phase = re.compile(r"(xp<[^>]+>) xc<own> (ts<[^>]+>)")

# related to voting/votes
re_vote_check = re.compile(r"ka<vote[^>]*>")

# named votes i.e. Magister of Worth 'grace' and 'condemnation
# 1: extract the two named candidates
re_vote_candidates = re.compile(
    r"starting pr<with> xp<you>, xq<each> xp<player> ka<vote suffix=s> pr<for> "
    r"([^\.]+) or ([^\.]+)."
)

# 2: grab the whole sub-phrase 'candidate1 or candidate2'
re_vote_choice = re.compile(
    r"(?<=starting pr<with> xp<you>, xq<each> xp<player> ka<vote suffix=s> pr<for> )"
    r"([^\.]+ or [^\.]+.)"
)

# deconflict 'vote' as an object
# 1. vote preceded by a candidate
# 2. candidate followed by 'gets more'
# 3. any vote preceded by a quantifier or qualifier
def vote_obj1(tkn): return re.compile(r"{} ka<vote>".format(tkn))
def vote_obj2(tkn): return re.compile("{}(?= xa<get suffix=s> xl<more>)".format(tkn))
re_vote_obj3 = re.compile(r"(?<=(?:xl|xq)<[^>]*> )ka<vote([^>]*)>")

# find landwalk preceded by an object or attribute
re_landwalk = re.compile(r"((?:ob|xr)<[^>]+>) (kw<landwalk>)")