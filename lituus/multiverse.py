#!/usr/bin/env python
""" multiverse.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Parser and MTGCard generator for all cEDH legal cards in the multiverse
"""

__name__ = 'multiverse'
__license__ = 'GPLv3'
__version__ = '0.2.2'
__date__ = 'July 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import os
import pickle
import json
import requests
from hashlib import md5
import lituus.mtg as mtg
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.parser as parser
import lituus.mtgl.mtgt as mtgt
import lituus.mtgcard as mtgcard

# file paths and urls
url_cards = "https://mtgjson.com/json/AllCards.json"
mvpath    = os.path.join(mtg.pth_sto,'multiverse.pkl')
tcpath    = os.path.join(mtg.pth_sto,'transformed.pkl')

def multiverse(update=False):
    """
     :param update: if set, will download and use multiverse data from 
      https://mtgjson.com/json/AllSets.json 
     :returns error multiverse dict
    """
    # files to create
    mv = {}  # multiverse
    tc = {}  # transformed cards

    # don't reparse the mutliverse unless update is set
    if os.path.exists(mvpath) and not update:
        fin = None
        try:
            fin = open(mvpath,'rb')
            mv = pickle.load(fin)

            # create the n2r file
            n2r = {} # name to ref-id hash
            for cname in mv: n2r[cname] = md5(cname.encode()).hexdigest()
            mtgl.set_n2r(n2r)

            # Because of pickling errors with self defined classes issue #124
            # we have to objectify (create mtglo objects) here and convert
            # the dict to MTGCards
            return {name:mtgcard.MTGCard(mv[name]) for name in mv}
        except pickle.PickleError as e:
            print("Error loading multiverse: {}. Loading from JSON".format(e))
        finally:
            if fin: fin.close()

    # there is no version checking. on update, downloads AllCards.json & reparses
    if update and False: # TODO: disable downloading allcards until debugging is complete
        fout = None
        try:
            print("Requesting AllCards.json")
            jurl = requests.get(url_cards)
            if jurl.status_code != 200: raise RuntimeError
            fout = open(os.path.join(mtg.pth_resources,'AllCards.json'),'w')
            fout.write(jurl.json())
            fout.close()
            print("AllCards.json updated")
        except RuntimeError:
            print("Failed to download AllCards.json")
        except OSError as e:
            print("Failed to save AllCards.json: {}".format(e))
        finally:
            if fout: fout.close()

    # parse the cards json file
    fin = None
    try:
        # get the AllCards.json and import
        print("Parsing local copy AllCards")
        fin = open(os.path.join(mtg.pth_resources,'AllCards.json'),'r')
        mverse = json.load(fin)
        fin.close()
        import_cards(mv,tc,mverse)
        print("Imported {} cards and {} transformed cards.".format(len(mv),len(tc)))
    except IOError as e:
        print("Error reading the cards file {}".format(e))
    finally:
        if fin: fin.close()

    # pickle the multiverse
    fout = None
    try:
        print("Writing multiverse file")
        fout = open(mvpath,'wb')
        pickle.dump(mv,fout)
        fout.close()
    except pickle.PickleError as e:
        print("Failed to pickle multiverse: {}".format(e))
        raise
    except IOError as e:
        print("Failed to save multiverse: {}".format(e))
        raise
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
        print("Failed to pickle transformed: {}".format(e))
        raise
    except IOError as e:
        print("Failed to save transformed: {}".format(e))
        raise
    finally:
        if fout: fout.close()

    # Because of pickling errors with self defined classes issue #124 we have
    # to objectify here converting the dictto MTGCards prior to returning
    return {name:mtgcard.MTGCard(mv[name]) for name in mv}

def import_cards(mv,tc,mverse):
    """
     imports cards into multiverse mv and transformed cards tc from json mverse
     :param mv: multiverse dict
     :param tc: transformed dict
     :param mverse: json multiverse
    """
    # calculate the name to ref-id dict and initialize it
    n2r = {} # name to ref-id hash
    for cname in mverse:
        # skip banned cards
        try:
            if mverse[cname]['legalities']['commander'] != 'Legal': continue
            n2r[cname] = md5(cname.encode()).hexdigest()
        except KeyError:
            continue
    mtgl.set_n2r(n2r)

    splits = []
    for cname in mverse:
        # skip banned cards
        try:
            if mverse[cname]['legalities']['commander'] != 'Legal': continue
        except KeyError:
            continue

        # get the parameters and parse the oracle
        # TODO: once the bugs, are worked out, change reraise of error to print
        #  and continue
        jcard = mverse[cname]
        dcard = parse_card(cname,jcard)
        try:
            parser.parse(cname,dcard)
        except mtgl.MTGLException:
            print("Error parsing {}. Skipping...".format(cname))
            raise
        except Exception as e:
            print("Unknown Error of type {} parsing {}. Skipping...".format(type(e),cname))
            raise

        # determine if the card goes in the multiverse dict or transformed
        if jcard['layout'] == 'transform' and jcard['side'] == 'b':
            tc[cname] = dcard
        elif jcard['layout'] == 'meld' and jcard['side'] == 'c':
            tc[cname] = dcard
        else: mv[cname] = dcard

        # save split cards for combing later
        if jcard['layout'] == 'split':
            if not jcard['names'] in splits: splits.append(jcard['names'])

    # combine the split cards and add to multiverse deleting the halves
    for split in splits:
        name = " // ".join(split)
        a,b = split[0],split[1]
        dcard = {
            'rid':"{} // {}".format(mv[a]['rid'],mv[b]['rid']),
            'name': "{} // {}".format(mv[a]['name'], mv[b]['name']),
            'mana-cost':"{} // {}".format(mv[a]['mana-cost'],mv[b]['mana-cost']),
            'oracle':"{} // {}".format(mv[a]['oracle'],mv[b]['oracle']),
            'tag':"{} // {}".format(mv[a]['tag'],mv[b]['tag']),
            'tkn':mv[a]['tkn'] + [['//']] + mv[b]['tkn'],
            'mtgl':mv[a]['mtgl'] + [['//']] + mv[b]['mtgl'],
            'mtgt':mtgt.fuse_tree(mv[a]['mtgt'],mv[b]['mtgt']),
            'super-type':mv[a]['super-type'] + mv[b]['super-type'],
            'type':mv[a]['type'] + mv[b]['type'],
            'sub-type':mv[a]['sub-type'] + mv[b]['sub-type'],
            'cmc':mv[a]['cmc'],
            'color-ident':mv[a]['color-ident'],
            'sets':mv[a]['sets'],
            'P/T':None,
            'loyalty':None
        }
        del mv[a]
        del mv[b]
        mv[name] = dcard

def parse_card(name,jcard):
    """
     extract details from the json card and return the card dict
    :param name: the name of the card
    :param jcard: json card dict
    :return: card dict
    """
    # extract characteristics from card
    try:
        dcard = {
            'rid':md5(name.encode()).hexdigest(),
            'name':name,
            'super-type': jcard['supertypes'],
            'type': jcard['types'],
            'sub-type': jcard['subtypes'],
            'cmc':int(jcard['convertedManaCost']) if 'convertedManaCost' in jcard else 0,
            'mana-cost': jcard['manaCost'] if 'manaCost' in jcard else '{0}',
            'P/T': None,
            'loyalty':None,
            'color-ident': jcard['colorIdentity'],
            'colors': jcard['colors'],
            'oracle':_hack_oracle_(name,jcard['text']) if 'text' in jcard else "",
            'tag': "",
            'tkn':[],
            'mtgl':[],
            'mtgt':None,
            'sets': jcard['printings'],
        }
    except KeyError as e:
        print("{}->{}".format(name,e))
        raise

    # check for existence before setting the following
    if 'Planeswalker' in jcard['types'] and 'loyalty' in jcard:
        dcard['loyalty'] = jcard['loyalty']
    elif 'Creature' in jcard['types']:
        dcard['P/T'] = "{}/{}".format(jcard['power'],jcard['toughness'])

    # return the card dict
    return dcard

def _hack_oracle_(name,txt):
    """
    Hard coded hacks to modify card contents to enable better
    processing
    :param name: the name of the card
    :param txt: the oracle text
    :return: modified oracle text
    """
    if name == "Urborg, Tomb of Yawgmoth": txt += "\n{T}: Add {B}.\n"
    elif name == "Drayd Arbor": # rewrite the oracle
        txt = "Dryad Arbor isn't a spell, it's affected by summoning sickness.\n{T}: Add {G}\n"
    return txt

def _precompile_types_(mv):
    """
     writes a precompiled list of super types, types and subtypes
     :param mv: the multiverse dict
     :return: a types dict
     NOTE: this is only necessary to check after set updates for new subtypes
    """
    # TODO: after adding mtgcard, will have to convert the below to use the
    # card object vice the dict
    types = {'super':[],'main':[],'sub':[]}
    for card in mv:
        for stype in mv[card]['super-type']:
            if not stype.lower() in types['super']: types['super'].append(stype.lower())
        for stype in mv[card]['type']:
            if not stype.lower() in types['main']: types['main'].append(stype.lower())
        for stype in mv[card]['sub-type']:
            if not stype.lower() in types['sub']: types['sub'].append(stype.lower())
    return types