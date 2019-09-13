#!/usr/bin/env python
""" list_util.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines helper functions for list processing
"""

#__name__ = 'list_util'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'September 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
from itertools import tee

re_all = re.compile(r".+") # catchall for match any token
def ors(tkns): return re.compile(r"{}".format('|'.join([t for t in tkns])))
def matchl(ls,ss,start=0,stop=None):
    """
     attempts to match the elements in ss to a sublist of ls. If set, the values
     start and stop are used to limit the indexes of the list to look for a match
     to ls[start:stop+1]. The elements of ss can be strings, functions (that
     return True or False), and/or regular expressions)
     NOTE:
      1. This is a token for token match so it cannot be used to find for example
       a list of any length beginning with a specified regex and ending with a
       specified regex
      2. any regex passed in ss must be compiled and the underlying function uses
       the regex 'match'
    While slower than a check against each element in a list i.e. if
     ls[0] == a and ls[1] == b ... and ls[n] = n it is much cleaner, it
     eliminates the need for IndexError check and eliminates the need to know
     what indices to check
    :param ls: the list to match against
    :param ss: a list of functions, compiled re and/or strings
    :param start: the first index in the list look for a match
    :param stop: the last index to look for a match. if present, matchl will not
     attempt to match after the index
    :return: starting index of ss in ls or -1 if there is no match
    """
    if len(ss) > len(ls) or len(ss) == 0: return -1 # don't bother with these
    if start >= len(ls): return -1
    if stop and start > stop: return -1
    for i in range(start,len(ls)-len(ss)+1):
        if stop and i > stop: return -1
        ls1 = ls[i:i+len(ss)]
        found = True
        for j,s in enumerate(ss):
            if callable(s):
                if not s(ls1[j]):
                    found = False
                    break
            elif type(s) is type(re_all):
                if not s.match(ls1[j]):
                    found = False
                    break
            elif type(s) is type(''):
                if not s == ls1[j]:
                    found = False
                    break
        if found: return i
    return -1

def splicel(ls,t1,t2,t3=None):
    """
     finds sublists in ls between the terms t1, t2 and t3 (if present). The terms
     are found via matchl so they can be a single token or a list of tokens where
     each token can be a string, function or regular expression.
    :param ls: the list to search in
    :param t1: the first term
    :param t2: the second  (or last) term
    :param t3: the third and last term if present
    :return: three lists idx,matches,phrases where
     idx is a list of the starting indices of matches for t1, t2, and t3
     matches is a list of the matches for t1, t2 and t3
     phrases is a list of the sublists 'between' t1, t2 and t3
      such that phrases[0] is always the sublist of tokens occurring prior to t1
      and phrase[-1] is always the sublast following the last term t2 or t3
      and phrase[1:-1] are the sublists between t1 and t2 and t2 and t3 (if present)

    As an example, consider the mtgl for the second line of Containment Priest
    ls = ['cn<if>', 'ob<¬token quantifier=a characteristics=creature>', 'cn<would>',
          'xa<enter>', 'zn<battlefield>', 'and', 'xo<it>', 'wasnt', 'ka<cast>', ',',
          'ka<exile>', 'xo<it>', 'cn<instead>', '.']

    and we want to splice on three conditionals (tag.is_conditional)
    idx,matches,phrases = splicel(ls,tag.is_conditional,tag.is_conditional,tag.is_conditional)

    returns:
     idx = [0, 2, 13]
     matches = [
          match for t1 = ['cn<if>'],
          match for t2 = ['cn<would>'],
          match for t3 = ['cn<instead>']
     ]
     phrases = [
         before = [],
         between t1 and t2 = ['ob<¬token quantifier=a characteristics=creature>'],
         between t2 and t3 = ['xa<enter>', 'zn<battlefield>', 'and', 'xo<it>', 'wasnt', 'ka<cast>',
          ',', 'ka<exile>', 'xo<it>'],
        after = ['.']
     ]

    """
    # TODO: generalize this so we can use a list instead of t1, t2 and t3
    idx  = [] # starting indices of matches
    ms   = [] # the matched phrase
    bs   = [] # betweens (list of tokens between ti and tj
    last = 0  # stopping index of the last found match

    # start at first term and work left to right
    t1 = t1 if isinstance(t1,list) else [t1]
    i = matchl(ls,t1)
    if i < 0: raise ValueError
    idx.append(i)
    ms.append(ls[i:i+len(t1)])
    bs.append(ls[:i]) # this will be before

    # get the match for the second term
    t2 = t2 if isinstance(t2,list) else [t2]
    j = matchl(ls,t2,start=i+len(t1))
    if j < 0: raise ValueError
    idx.append(j)
    ms.append(ls[j:j+len(t2)])
    bs.append(ls[i+1:j]) # this will be between1
    last = j+len(t2)

    # if the third term is present get the match
    if t3:
        t3 = t3 if isinstance(t3,list) else [t3]
        k = matchl(ls,t3,start=j+len(t2))
        if k < 0: raise ValueError
        idx.append(k)
        ms.append(ls[k:k+len(t3)])
        bs.append(ls[j+1:k]) # this will be between2
        last = k+len(t3)

    # append 'after'
    bs.append(ls[last:])

    return idx,ms,bs


def replacel(ls,ss,ns):
    """
     replaces occurences of the sublist ms in the list ls with the new sublist n.
     Uses matchl to find ms so it does not have to be list of exact tokens. The
     changes create a new list
    :param ls: the list to search in
    :param ss: the sublist to match
    :param ns: the list to replace sublist with
    """
    ls1 = ls[:]
    j = matchl(ss,ls1)
    while j > -1:
        ls1[j:j+len(ss)] = ns
        j = matchl(ss,ls1)
    return ls1

def splitl(ls,i):
    """
     splits the list of tokens ls at index i returning the tokens to the left of i,
     the token at i and tokens to the right of i. In other words, to recombine ls
     into its orginal left + [ls_i] + right
    :param ls: the list to split
    :param i: the index to split on
    :return: left,tkn,right
    """
    if i < 0 or i > len(ls) - 1:
        raise IndexError("splitl: invalid index {} out of range".format(i))
    return ls[:i],ls[i],ls[i+1:]

def indicesl(ls,e):
    """
     finds all indices of the element e in ls
    :param ls: the list
    :param e: element
    :return: a list of indices of e in ls
    """
    return [i for i,v in enumerate(ls) if v == e]

def joinl(ls,e):
    """
     joins the sublists in ls with the tkn e such that the joined list js will be
       ls[0] + [e] + ls[1] + e ... + ls[n]
    :param ls: list of lists
    :param e: string token to join
    :return: the joined list
    """
    js = []
    for i,ss in enumerate(ls):
        js += ss
        if i < len(ls)-1: js += [e]
    return js

def indexl(ls,e,start=0):
    """
     finds the index of the first occurrence of element e in list ls after index
     start
     :param ls: the list to search
     :param e: the element to look for
     :param start: the index to start at
     :return: the left index of e in ls (or throws a ValueError)
    """
    return (ls[start+1:].index(e))+(start+1)

def rindexl(ls,e):
    """
     finds the right index of an element e in the list ls
    :param ls: the list to search
    :param e: the element to look for
    :return: the right index of e in ls (or throws a ValueError)
    """
    return len(ls) - ls[::-1].index(e) - 1

def _pairwise_(ls,idx):
    """
     uses the pairwise recipe in python docs itertools to return
    :param ls: the list
    :param idx: the indexes to split on
    :return: ls[s0:s1], ls[s1+1,s2], ... ,ls[sn:sn]) for s = i in idx
    """
    k,l = tee(idx)
    next(l,None)
    return [ls[i+1:j] for i,j in zip(k,l)]
    # below will return the phrases interspersed with the elements at the indices
    # in idx
    #bs = [ls[i+1:j] for i,j in zip(k,l)]
    #rs = [bs[0]] # gives us before
    #for i,j in enumerate(bs[1:]): rs.extend([ls[idx[i+1]],j])
    #return rs