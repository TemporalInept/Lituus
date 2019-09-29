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
__version__ = '0.0.4'
__date__ = 'September 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
from itertools import tee

re_all = re.compile(r".+") # catchall for match any token
def ors(*args): return re.compile(r"{}".format('|'.join([arg for arg in args])))
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

def splicel(ls,ts):
    """
     finds sublists in ls between the terms in ts. The terms are found via matchl
     so they can be a single token or a list of tokens where each token can be a
     string, function or regular expression.
     NOTE: ts must contain at least two terms
    :param ls: the list to search in
    :param ts: iterable of terms
    :return: three lists idx,matches,phrases where
     idx is a list of the starting indices of matches for each term in ts
     matches is a list of the matches for each term in ts
     phrases is a list of the sublists 'between' t_i and t_j for each pairwise tuple
     of terms in ts
      such that phrases[0] is always the sublist of tokens occurring prior to the
      first term in ts, phrase[-1] is always the sublist following the last term
      in ts and phrase[1:-1] are the sublists between the terms

     As an example, consider the mtgl for the second line of Containment Priest
     ls = ['cn<if>', 'ob<¬token quantifier=a characteristics=creature>', 'cn<would>',
           'xa<enter>', 'zn<battlefield>', 'and', 'xo<it>', 'wasnt', 'ka<cast>', ',',
           'ka<exile>', 'xo<it>', 'cn<instead>', '.']

     and we want to splice on three conditionals (tag.is_conditional)
     idx,matches,phrases = splicel(
             ls,(tag.is_conditional,tag.is_conditional,tag.is_conditional)
     )

     returns:
      idx = [0, 2, 12]
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
    idx  = [] # starting indices of matches
    ms   = [] # the matched phrase
    bs   = [] # betweens (list of tokens between ti and tj
    last = 0  # stopping index of the last found match

    # get the first term
    term = ts[0] if isinstance(ts[0],list) else [ts[0]]
    i = matchl(ls,term)
    if i < 0: raise ValueError
    idx.append(i)
    ms.append(ls[i:i+len(term)])
    bs.append(ls[:i])  # this will be before
    last = i+len(term)

    # now try and match the remaining terms
    for term in ts[1:]:
        term = term if isinstance(term,list) else [term]
        j = matchl(ls,term,start=last)
        if j < 0: raise ValueError
        idx.append(j)
        ms.append(ls[j:j+len(term)])
        bs.append(ls[last:j])  # this will be between i and j
        last = j+len(term)
        i = j

    # get 'after'
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
    if i < 0 or i > len(ls) - 1: raise IndexError("splitl index out of range")
    return ls[:i],ls[i],ls[i+1:]

# TODO: changes this to use matchl
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

def endswithl(ls,e):
    """
     determines if the last element in the list of tokens is e. Uses matchl so,
     e can be a regex, function or string as well as a list of terms to match
     NOTE: returns False vice throwing an error if the list is empty
    :param ls: list of tokens
    :param e: element to check for
    :return: True if ls[-1] == e False otherwise
    """
    e = e if isinstance(e,list) else [e]
    le = len(e)
    return matchl(ls,e) == len(ls)-le

def indexl(ls,e,start=0):
    """
     finds the index of the first occurrence of element e in list ls after index
     start. NOTE: unlike list.index returns None vice throwing an error if the
    element is not in the list
     :param ls: the list to search
     :param e: the element to look for
     :param start: the index to start at
     :return: the left index of e in ls (or throws a ValueError)
    """
    try:
        return (ls[start+1:].index(e))+(start+1)
    except ValueError:
        return None

def rindexl(ls,e):
    """
     finds the right index of an element e in the list ls. NOTE: unlike list.index
     returns None vice throwing an error if the element is not in the list
    :param ls: the list to search
    :param e: the element to look for
    :return: the right index of e in ls (or throws a ValueError)
    """
    try:
        return len(ls) - ls[::-1].index(e) - 1
    except ValueError:
        return None

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