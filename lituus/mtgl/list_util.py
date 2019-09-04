#!/usr/bin/env python
""" list_util.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Defines helper functions for list processing
"""

__name__ = 'list_util'
__license__ = 'GPLv3'
__version__ = '0.0.1'
__date__ = 'August 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re

def subl(ss,ls):
    """
     determines whether the list of tokens ss can be found in the list ls
    :param ss: the sublist
    :param ls: the ls
    :return: index that sub starts in line or -1
    """
    if len(ss) > len(ls): return -1
    for i in range(0,len(ls)-len(ss)+1):
        if ls[i:i+len(ss)] == ss: return i
    return -1

# TODO: no need for below, make it a constant, and if found in sublist, it matches
re_all = re.compile(r".+") # catchall for match any token
def matchl(ss,ls,a=None):
    """
     attempts to match the elements in ss to a sublist of ls.
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
    :param ss: a list of functions, compiled re and/or strings
    :param ls: the list to match against
    :param a: stop at index a. if present, matchl will not attempt to match
     after the index
    :return: starting index of ss in ls or -1 if there is no match
    """
    if len(ss) > len(ls): return -1 # the sublist cannot have more elements
    elif len(ss) == 0: return -1    # don't allow empty sublists
    for i in range(0,len(ls)-len(ss)+1):
        if a is not None and i > a: break
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
            else: raise TypeError("matchl: invalid type {}".format(type(s)))
        if found: return i
    return -1

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
     :return: the right index of e in ls (or throws a ValueError)
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