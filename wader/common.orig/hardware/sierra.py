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
Common stuff for all SierraWireless's cards
"""

__version__ = "$Rev: 1172 $"

import re

from wader.common.command import get_cmd_dict_copy, OK_REGEXP, ERROR_REGEXP
from wader.common.hardware.base import Customizer

SIERRAWIRELESS_DICT = {
    '3GONLY'   : 'AT!SELRAT=01',
    '3GPREF'   : 'AT!SELRAT=03',
    'GPRSONLY' : 'AT!SELRAT=02',
    'GPRSPREF' : 'AT!SELRAT=04',
}

# Sierra devices like to append garbage after CREG like:
# [-] SIMCardConnAdapter: SENDING ATCMD 'AT+CREG?\r\n'
# [-] SIMCardConnAdapter: NEW STATE: waiting
# [-] SIMCardConnAdapter: DATA_RCV: '\r\n+CREG: 0,1,03F3,2993\r\n\r\nOK\r\n'
SIERRA_CMD_DICT = get_cmd_dict_copy()

info = dict(echo=None,
            end=OK_REGEXP,
            error=ERROR_REGEXP,
            extract=re.compile(r"""
                \r\n
                \+CREG:\s
                (?P<mode>\d),(?P<status>\d+)(,[0-9a-fA-F]*,[0-9a-fA-F]*)?
                \r\n
                """, re.VERBOSE))

SIERRA_CMD_DICT['get_netreg_status'] = info

class SierraWirelessCustomizer(Customizer):
    async_regexp = None
    conn_dict = SIERRAWIRELESS_DICT
    cmd_dict = SIERRA_CMD_DICT

