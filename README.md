# ![Lituus Logo](https://github.com/TemporalInept/Lituus/blob/master/docs/lituus%20banner.png)
## A parser and pseudo-scientific analyzer of MTG cards.

Lituus, a curved staff or wand used by Roman augurs to define a templum in the sky and interpret the passage of birds and divine omens.

## 1 DESCRIPTION

**NOTE: Lituus in its current state does not work**

Lituus is a proof of concept that aims to:

 1. Grab the characteristics of each card,
 2. Parse and graph Magic: The Gathering (MTG) oracle text,
 3. Compile and collate the parsed oracle text and card characteristics,
 3. Analyze the collated data in terms of Competitive Elder Highlander (cEDH) decks,
 5. and use the data in Ertai's Study of Lesser Wizards (ESoLW) <https://github.com/TemporalInept/ESoLW> Quarterly and Annual Reports. 

Sources:

 1. The MTG card database at <https://mtgjson.com> 
 2. AverageDragon's (<https://tappedout.net/users/AverageDragon/>) cEDH conglomerate at <http:cedh-decklist-database.xyz/primary.html>
 3. MTG Comprehensive Rules at <https://magic.wizards.com/en/game-info/gameplay/rules-and-formats/rules>

Lituus is a follow on to a personal project I had written that attempted to do the
above but had become grossly unmaintable due to a mess of regular expressions and string finds. Furthermore, the final aim of Lituus is to compare cEDH decks to each other in a quantifiable way and programmatically discern their Archetypes which requires a more robust method.

Once complete, Lituus will be able to conceptualize oracle text as trees

<pre>
Dark Ritual
root
└ line:0
   └ability-line:0
    └spell-ability:0
     ├lituus-action-clause:0
     │├lituus-action:0(word=add)
     │└mana:0
     │ └mana-string:0(mana={b}{b}{b})
     └punctuation:0(symbol=.)
</pre>

which, when combined with other characterisitics of cards, will give us the tools to meet our objectives.

## 2 DEPENDENCIES

 1. **Python 3.x** It has only been tested on my machine using Python 3.5.2 is not guaranteed to work on anything else. I have no intention of trying to port it to Python 2.x
 2. **networkx** (https://networkx.github.io) to create parse trees
 3. **BeautifulSoup** (https://www.crummy.com/software/BeautifulSoup/) for scraping online decklists

## 3 INSTALLION/USING

## 4 ARCHITECTURE

## 5. FILE STRUCTURE:
Brief Overview of the project file structure. Directories and/or files annotated
with (-) are not included in pip installs or PyPI downloads

* Lituus                    root Distribution directory
  - \_\_init\_\_.py         initialize distrubution Lituus module
  - docs                    README resources
    + lituus banner.png     banner image for README
    + lituus logo small.png Small logo for Lituus
  - README.md               this file
  - LICENSE                 GPLv3 License
  - TODO                    things I want to implement/change
  - lituus                  package directory
    + \_\_init\_\_.py       initialize lituus module
    + mtg.py                constants and general functions
    + multiverse.py         mtgjson interface
    + mtgcard.py            defines our concept of a card
    + mtgl                  Parsing/Graphing functuality
     * \_\_init\_\_.py      initialize mtgl module
     * mtgl.py              regexes, strings & helper functions for the mtgl format
     * tagger.py            tags (annotates) MTG oracle text in the mtgl format
     * lexer.py             tokenized tagged text
     * parser.py            parses tagged and tokenized text
     * grapher.py           turns parsed text into parse trees
     * mtgt.py              wrapper for networkx trees
     * list_util.py         useful list functions
    + resources             local copies of other peoples work
      * AllCards.json       All the cards
      * Primary Database    cEDH decks details
    + sto                   Saved data
      * multiverse.pkl      Saved multiverse after parsing
      * transformed.pkl     Saved transformed cards after parsing

***
Lituus is unofficial Fan Content permitted under the Fan Content Policy. Not
approved/endorsed by Wizards. Portions of the materials used are property of Wizards
of the Coast. &copy; Wizards of the Coast LLC.


