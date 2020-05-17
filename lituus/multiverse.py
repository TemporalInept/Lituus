#!/usr/bin/env python
""" multiverse.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

MTGCard generator for all cEDH legal cards in the multiverse
"""

#__name__ = 'multiverse'
__license__ = 'GPLv3'
__version__ = '0.2.4'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import os
import sys
import pickle
import json
import requests
from hashlib import md5
import regex as re
import lituus as lts
import lituus.mtg as mtg
import lituus.pack as pack
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.tagger as tagger
import lituus.mtgl.lexer as lexer
import lituus.mtgl.parser as parser
import lituus.mtgl.grapher as grapher
import lituus.mtgl.mtgt as mtgt
import lituus.mtgcard as mtgcard

# file paths and urls
url_cards = "https://mtgjson.com/json/AllCards.json"
jpath     = os.path.join(mtg.pth_resources,'AllCards.json')
mvpath    = os.path.join(mtg.pth_sto,'multiverse.pkl')
tcpath    = os.path.join(mtg.pth_sto,'transformed.pkl')
n2rpath   = os.path.join(mtg.pth_sto,'n2r.pkl')

def multiverse(update=0):
    """
     :param update: one of
        0 = load saved multiverse
        1 = reparse json file and create new multiverse
        2 = download json file and create new multiverse
      https://mtgjson.com/json/AllSets.json 
     :returns multiverse dict
    """
    # files to create
    mv = pack.Pack() # multiverse
    tc = {}          # transformed cards
    n2r = {}         # name to reference dict

    if update == 0:
        fin = None
        try:
            fin = open(mvpath,'rb')
            mv = pickle.load(fin)
            fin.close()
            return mv
        except FileNotFoundError:
            raise lts.LituusException(lts.EIOIN,"Multiverse file does not exist")
        except pickle.PickleError:
            raise lts.LituusException(lts.EIOIN,"Error loading multiverse")
        finally:
            if fin: fin.close()

    # there is no version checking. on update, downloads AllCards.json & reparses
    # TODO: Downloading allcards disabled until debugging is complete
    if update == 2 and False:
        fout = None
        try:
            print("Requesting AllCards.json")
            jurl = requests.get(url_cards)
            if jurl.status_code != 200: raise RuntimeError
            fout = open(jpath,'w')
            fout.write(jurl.json())
            fout.close()
            print("AllCards.json updated")
        except RuntimeError:
            raise lts.LituusException(lts.ENET,"Failed to download AllCards.json")
        except OSError:
            raise lts.LituusException(lts.EIOOUT,"Failed to save AllCards.json")
        finally:
            if fout: fout.close()

    # read in AllCards.json
    fin = None
    try:
        print("Loading the Multiverse")
        fin = open(jpath,'r')
        mverse = _hack_cards_(json.load(fin)) # fix errors in cards
        fin.close()
    except IOError:
        raise lts.LituusException(lts.ERRIOIN,"Error reading AllCards.json")
    finally:
        if fin: fin.close()

    # parse the mverse
    print('Parsing the Multiverse')
    import_cards(mv,tc,n2r,mverse)
    print("Imported {} cards and {} transformed cards.".format(mv.qty(),len(tc)))

    # pickle the multiverse
    fout = None
    try:
        print("Writing multiverse file")
        fout = open(mvpath,'wb')
        pickle.dump(mv,fout)
        fout.close()
    except pickle.PickleError:
        raise lts.LituusException(lts.EIOOUT,"Failed pickling multiverse")
    except IOError as e:
        raise lts.LituusException(lts.EIOOUT,"Failed saving multiverse")
    finally:
        if fout: fout.close()

    # & then transformed
    fout = None
    try:
        print("Writing transformed file")
        fout = open(tcpath,'wb')
        pickle.dump(tc, fout)
        fout.close()
    except pickle.PickleError as e:
        raise lts.LituusException(lts.EIOOUT,"Failed pickling transformed")
    except IOError as e:
        raise lts.LituusException(lts.EIOOUT,"Failed saving transformed")
    finally:
        if fout: fout.close()

    # & then the n2r dict
    fout = None
    try:
        print("Writing Name Reference file")
        fout = open(n2rpath,'wb')
        pickle.dump(n2r,fout)
        fout.close()
    except pickle.PickleError as e:
        raise lts.LituusException(lts.EIOOUT,"Failed pickling name reference")
    except IOError as e:
        raise lts.LituusException(lts.EIOOUT,"Failed saving name reference")
    finally:
        if fout: fout.close()

    return mv

def import_cards(mv,tc,n2r,mverse):
    """
     imports cards into multiverse mv and transformed cards tc from json mverse
     :param mv: multiverse dict
     :param tc: transformed dict
     :param n2r: the name to reference hash
     :param mverse: json multiverse
    """
    # calculate the name to ref-id dict and initialize it, skipping banned cards
    for cname in mverse:
        try:
            if mverse[cname]['legalities']['commander'] != 'Legal': continue
            n2r[cname] = md5(cname.encode()).hexdigest()
        except KeyError:
            continue
    mtgl.set_n2r(n2r)

    temp = {}   # tempory dict for cards until splits are combined
    splits = []
    i = 0
    ttl = len(n2r)
    for cname in n2r: # only enumerate legal names
        # get the parameters and parse the oracle
        # TODO: once debugging is done, dont store intermidiate parsing artifacts
        jcard = dcard = None
        try:
            # harvest the json card dict and parse the oracle text
            jcard = mverse[cname]
            dcard = harvest(cname,jcard)
            dcard['tag'] = tagger.tag(cname,dcard['oracle'])
        except KeyError as e:
            # shouldn't get this
            print("Multiververse error, lost card {}".format(e))

        # determine if the card goes in the multiverse dict or transformed
        if jcard['layout'] == 'transform' and jcard['side'] == 'b':
            tc[cname] = mtgcard.MTGCard(dcard)
        elif jcard['layout'] == 'meld' and jcard['side'] == 'c':
            tc[cname] = mtgcard.MTGCard(dcard)
        else: temp[cname] = dcard

        # save split cards for combining later
        if jcard['layout'] in ['split','aftermath','adventure']:
            if not jcard['names'] in splits: splits.append(jcard['names'])

        # update progress
        i += 1
        progress_bar(i,ttl)

    # combine split cards & add to multiverse deleting the original halves
    for split in splits:
        name = " // ".join(split)
        a,b = split[0],split[1]
        dcard = {
            'rid': "{} // {}".format(temp[a]['rid'],temp[b]['rid']),
            'name':name,
            'mana-cost':"{} // {}".format(temp[a]['mana-cost'],temp[b]['mana-cost']),
            'oracle':"{} // {}".format(temp[a]['oracle'],temp[b]['oracle']),
            'tag':"{} // {}".format(temp[a]['tag'],temp[b]['tag']),
            'super-type':list(set(temp[a]['super-type']+temp[b]['super-type'])),
            'type':list(set(temp[a]['type'] + temp[b]['type'])),
            'sub-type':list(set(temp[a]['sub-type'] + temp[b]['sub-type'])),
            'face-cmc':(temp[a]['face-cmc'],temp[b]['face-cmc']),
            'cmc':temp[a]['cmc'], # same for both cards
            'colors':list(set(temp[a]['colors']+temp[b]['colors'])),
            'color-ident':temp[a]['color-ident'],
            'sets':temp[a]['sets'],
            'P/T':None,
            'loyalty':None
        }
        del temp[a]
        del temp[b]
        temp[name] = dcard

    # release the global n2r in mtgl
    mtgl.release_n2r()

    # create the multiverse
    for cname in temp: mv.add_card(mtgcard.MTGCard(temp[cname]))

def harvest(name,jcard):
    """
     extract details from the json card and return the card dict
    :param name: the name of the card
    :param jcard: json card dict
    :return: card dict
    """
    try:
        dcard = {
            'rid':md5(name.encode()).hexdigest(),
            'name':name,
            'layout': jcard['layout'],
            'super-type': jcard['supertypes'],
            'type': jcard['types'],
            'sub-type': jcard['subtypes'],
            'cmc':int(jcard['convertedManaCost']) if 'convertedManaCost' in jcard else 0,
            'mana-cost': jcard['manaCost'] if 'manaCost' in jcard else '{0}',
            'P/T': None,
            'loyalty':None,
            'color-ident': jcard['colorIdentity'],
            'colors': jcard['colors'],
            'oracle': jcard['text'] if 'text' in jcard else "",
            'tag': "",
            'tkn':[],
            'mtgl':[],
            'mtgt':None,
            'sets': jcard['printings'],
        }
    except KeyError as e:
        raise lts.LituusException(lts.EDATA,"{}->{}".format(name,e))

    # check for existence before setting the following
    if 'Planeswalker' in jcard['types'] and 'loyalty' in jcard:
        dcard['loyalty'] = jcard['loyalty']
    elif 'Creature' in jcard['types']:
        dcard['P/T'] = "{}/{}".format(jcard['power'],jcard['toughness'])
    if 'faceConvertedManacost' in jcard:
        dcard['face-cmc'] = jcard['faceConvertedManacost']
    else: dcard['face-cmc'] = dcard['cmc']

    return dcard

re_draft = re.compile(r"[Dd]raft(?:ing|ed)?")
def _hack_cards_(jv):
    """
    Fixes errors in json representation and hard codes hacks to modify card
    contents to enable easier processing
    :param jv: the json multiverse
    :return: the modified json multiverse
    """
    for cname in jv:
        # older versions of cards may have semi-colon rather than a comma
        # modify modal spells removing newlines betweem modes
        if 'text' in jv[cname]:
            jv[cname]['text'] = jv[cname]['text'].replace(';',',')
            jv[cname]['text'] = jv[cname]['text'].replace("\n• ",mtgl.BLT)

        # remove any lines in draft cards that reference draft(ing|ed) or
        # 'you noted'
        if cname in mtg.draft_cards:
            lines = []
            for line in jv[cname]['text'].split('\n'):
                #if 'draft' in line: continue
                if re_draft.search(line): continue
                if 'you noted' in line: continue
                if 'you guessed' in line: continue
                lines.append(line)
            jv[cname]['text'] = '\n'.join(lines)

        # hard-coded hacks for easier processing
        if cname == "Urborg, Tomb of Yawgmoth":
            # Urborg has an implied "Add B" because it makes itself a swamp
            jv[cname]['text'] += "\n{T}: Add {B}.\n"
        elif cname == "Drayd Arbor":
            # all reminded text is removed because it is in most cases redudant. But
            # Dryad's arbor oracle text in its entirety is reminder text
            jv[cname]['text'] = "Dryad Arbor isn't a spell, it's affected by summoning sickness.\n{T}: Add {G}\n"
        elif cname == "Raging River":
            # Raging River double-quote encloses the left and right labels which
            # interact negatively with the grapher. Remove the quotes from left and
            # right labels
            jv[cname]['text'] = jv[cname]['text'].replace('"left"','left')
            jv[cname]['text'] = jv[cname]['text'].replace('"right"','right')
        elif cname == 'Worship':
            # Worship is the only if-would-instead card that does not have a comma
            # between the original effect and the replacement effect
            jv[cname]['text'] = jv[cname]['text'].replace(
                "than 1 reduces it", "than 1, reduces it"
            )
        elif cname == 'Hall of Gemstone':
            # has "Until end of turn, lands tapped for mana..." the tapped is tagged
            # as a status and merged with the preceding
            jv[cname]['text'] = jv[cname]['text'].replace(
                "lands tapped for mana produce",
                "if a land is tapped for mana, it produces"
            )
        elif cname == "Frankenstein's Monster":
            # add counter behind he first two so they are not incorrectly
            # tagged as characteristics
            jv[cname]['text'] = jv[cname]['text'].replace(
                "with a +2/+0, +1/+1, or +0/+2 counter",
                "with a +2/+0 counter, +1/+1 counter, or +0/+2 counter",
            )
        elif cname == "Cloudseeder":
            # replace "Cloud Sprite can block... with a self-ref
            jv[cname]['text'] = jv[cname]['text'].replace(
                "Cloud Sprite can block",
                "ob<card ref=self> can block"
            )

        """
         bugs in mtgjson for Start // Finish related to side A, Start
          1. names listed as ['Start','Fire'] 
          2. incorrect layout 'split' vice 'aftermath'
          3. legalities is empty
          4. converted mana cost is wrong
          5. color identity states R & W
          6. printings say CMB1 vice AKH
        """
        if cname == 'Start':
            jv[cname]['legalities']['commander'] = 'Legal'
            jv[cname]['names'] = ['Start', 'Finish']
            jv[cname]['layout'] = 'aftermath'
            jv[cname]['convertedManaCost'] = 6.0
            jv[cname]['colorIdentity'] = ['W', 'B']
            jv[cname]['printings'] = ['AKH']
    return jv

def progress_bar(i,ttl):
    """
    prints a progress bar to console for step i with ttl steps, using carriage feed
    to overwrite the previous progress bar.
    CREDIT Greenstick (https://stackoverflow.com/users/2206251/greenstick)
    :param i: current step
    :param ttl: total steps
    """
    width = 60
    p = ("{0:.1f}").format(100 * (i/float(ttl)))
    filledLength = int(width*i//ttl)
    bar = '=' * filledLength + '-' * (width-filledLength)
    x = i%3
    if x == 0: s = '/'
    elif x == 1: s = '|'
    else: s = '\\'
    print('{}|{}| {}%'.format(s,bar,p),end='\r')
    if i == ttl: print()