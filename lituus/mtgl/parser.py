#!/usr/bin/env python
""" parser.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Parses tagged oracle text and resolves tagger errors using contextual information
"""

#__name__ = 'parser'
__license__ = 'GPLv3'
__version__ = '0.2.0'
__date__ = 'March 2020'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import re
import lituus.mtgl.mtgl as mtgl
import lituus.mtgl.list_util as ll
import lituus.mtgl.mtgltag as tag

# constants/helpers
re_draft = re.compile(r"draft(ing|ed)?")

def parse(txt): return