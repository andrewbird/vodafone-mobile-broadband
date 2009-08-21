# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
# Author:  Pablo Martí
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
AT Commands related classes and help functions
"""
__version__ = "$Rev: 1172 $"

import re

from twisted.python import log
import wader.common.exceptions as ex

ERROR_REGEXP = re.compile(r"""
# This regexp matches the following patterns:
# ERROR
# +CMS ERROR: 500
# +CME ERROR: foo bar
#
\r\n
(?P<error>                            # group named error
\+CMS\sERROR:\s\d{3}              |   # CMS ERROR regexp
\+CME\sERROR:\s\S+(\s\S+)*        |   # CME ERROR regexp
INPUT\sVALUE\sIS\sOUT\sOF\sRANGE  |   # INPUT VALUE IS OUT OF RANGE
ERROR                                 # Plain ERROR regexp
)
\r\n
""", re.VERBOSE)

ERROR_DICT = {
  # Generic error
  'ERROR' : ex.ATError,

  # CME Errors
  '+CME ERROR: incorrect password' : ex.CMEErrorIncorrectPassword,
  '+CME ERROR: invalid characters in dial string' : \
              ex.CMEErrorInvalidCharactersInDialString,
  '+CME ERROR: no network service' : ex.CMEErrorNoNetworkService,
  '+CME ERROR: not found' : ex.CMEErrorNotFound,
  '+CME ERROR: operation not allowed' : ex.CMEErrorOperationNotAllowed,
  '+CME ERROR: text string too long': ex.CMEErrorStringTooLong,
  '+CME ERROR: SIM busy' : ex.CMEErrorSIMBusy,
  '+CME ERROR: SIM failure' : ex.CMEErrorSIMFailure,
  '+CME ERROR: SIM interface not started' : ex.CMEErrorSIMNotStarted,
  '+CME ERROR: SIM interface not started yet' : ex.CMEErrorSIMNotStarted,
  '+CME ERROR: SIM not inserted' : ex.CMEErrorSIMNotInserted,
  '+CME ERROR: SIM PIN required' : ex.CMEErrorSIMPINRequired,
  '+CME ERROR: SIM PUK required' : ex.CMEErrorSIMPUKRequired,
  '+CME ERROR: SIM PUK2 required' : ex.CMEErrorSIMPUK2Required,

  # CMS Errors
  '+CMS ERROR: 300' : ex.CMSError300,
  '+CMS ERROR: 301' : ex.CMSError301,
  '+CMS ERROR: 302' : ex.CMSError302,
  '+CMS ERROR: 303' : ex.CMSError303,
  '+CMS ERROR: 304' : ex.CMSError304,
  '+CMS ERROR: 305' : ex.CMSError305,
  '+CMS ERROR: 310' : ex.CMSError310,
  '+CMS ERROR: 311' : ex.CMSError311,
  '+CMS ERROR: 313' : ex.CMSError313,
  '+CMS ERROR: 314' : ex.CMSError314,
  '+CMS ERROR: 315' : ex.CMSError315,
  '+CMS ERROR: 320' : ex.CMSError320,
  '+CMS ERROR: 321' : ex.CMSError321,
  '+CMS ERROR: 322' : ex.CMSError322,
  '+CMS ERROR: 330' : ex.CMSError330,
  '+CMS ERROR: 331' : ex.CMSError331,
  '+CMS ERROR: 332' : ex.CMSError332,
  '+CMS ERROR: 500' : ex.CMSError500,

  # USER GARBAGE ERRORS
  'INPUT VALUE IS OUT OF RANGE' : ex.InputValueError,
}

def extract_error(errorstr):
    """
    Scans C{errorstr} looking for AT Errors and returns exception if found
    """
    try:
        match = ERROR_REGEXP.search(errorstr)
        if match:
            try:
                error = match.group('error')
                exception = ERROR_DICT[error]
                return exception, error, match
            except KeyError:
                log.err("%r didn't map to any of my keys" % error)

    except AttributeError:
        return None #XXX: SAMURAI?
