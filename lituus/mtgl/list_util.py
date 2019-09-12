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
__version__ = '0.0.1'
__date__ = 'August 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re

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
     finds sublists in ls between the tokens t1, t2 and t3 (if present).
     NOTE:
      o each token t1 - t3 can appear no more than once in the ls
      o the tokens t1 - t3 are found via matchl so they can be a string, function
       or regeular expression
    :param ls: the list to search in
    :param t1: the first token
    :param t2: the second  (or last token)
    :param t3: the third and last token if present
    :return: a list l and tuple t where
      l = list of indexes where the tokens are located in ls
      t = (variable length)
       (before, - list of tokens before t1
        t1, - match for t1
        between1, - list of tokens between t1 and t2
        t2, - match for t2
        [ if t3 is set
         between2, list of tokens between t2 and t3
         t3 - mathc for t3
        ]
        after, - list of tokens after t3 (or t2)
    """
    # TODO: using functions will fail if they are the same function (note 1)
    #  i.e splicel(ls,tag.is_conditional,tag.is_conditional,tag.is_conditional)
    #  because the functions works 'right' to 'left' (i.e. from t3 to t1 and
    #  matchl works 'left' to 'right'. We'd have to start 'left' to 'right' (i.e.
    #  from t1 to t3) and matchl would have to include a 'start at' parameter
    # put the tokens in a list in reverse order
    ts = [t2,t1]
    if t3: ts.insert(0,t3)

    # starting from last to first
    k = matchl([ts[0]],ls)
    if k < 0: raise ValueError # technically could check for < # of tokens

    # find the next token
    j = matchl([ts[1]],ls,k-1)
    if j < 0: raise ValueError

    # find the last token (unless only two were queried for)
    if len(ts) < 3: return [j,k], (ls[:j],ls[j],ls[j+1:k],ls[k],ls[k+1:])
    i = matchl([ts[2]],ls,j-1)
    if i < 0: raise ValueError
    return [i,j,k], (ls[:i],ls[i],ls[i+1:j],ls[j],ls[j+1:k],ls[k],ls[k+1:])

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