# ![Lituus Logo](https://github.com/TemporalInept/Lituus/blob/master/docs/lituus%20banner.png)
## A parser and pseudo-scientific analyzer of MTG cards.

Lituus, a curved staff or wand used by Roman augurs to define a templum in the sky and interpret the passage of birds and divine omens.

## 1 DESCRIPTION

Lituus is a proof of concept that aims to:

 1. Parse and graph Magic: The Gathering (MTG) oracle text,
 2. Compile and collate the parsed oracle text and other card data,
 3. Analyze the collated data in terms of Competitive Elder Highlander (cEDH) decks,
 4. and use the data in Ertai's Study of Lesser Wizards (ESoLW) <https://github.com/TemporalInept/ESoLW> Quarterly and Annual Reports.

Lituus is written Python and requires Python 3 to run. It has only been tested on my personal computer is not guaranteed to work on anything else. 

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

***
Lituus is unofficial Fan Content permitted under the Fan Content Policy. Not
approved/endorsed by Wizards. Portions of the materials used are property of Wizards
of the Coast. &copy; Wizards of the Coast LLC.


