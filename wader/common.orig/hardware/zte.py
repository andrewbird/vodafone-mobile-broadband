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
Common stuff for all zte's cards
"""

__version__ = "$Rev: 1209 $"

import re

from wader.common.command import get_cmd_dict_copy, OK_REGEXP, ERROR_REGEXP
from wader.common.hardware.base import Customizer
from wader.common.sim import SIMBaseClass
from wader.common.plugin import DBusDevicePlugin

ZTE_DICT = {
   'GPRSONLY' : 'AT+ZSNT=1,0,0',
   '3GONLY'   : 'AT+ZSNT=2,0,0',
   'GPRSPREF' : 'AT+ZSNT=0,0,1',
   '3GPREF'   : 'AT+ZSNT=0,0,2',
}


ZTE_CMD_DICT = get_cmd_dict_copy()

info = dict(echo=None,
            end=OK_REGEXP,
            error=ERROR_REGEXP,
            extract=re.compile(r"""
                \r\n
                \+CREG:\s
                (?P<mode>\d),(?P<status>\d+)(,[0-9a-fA-F]*,[0-9a-fA-F]*)?
                \r\n
                """, re.VERBOSE))

ZTE_CMD_DICT['get_netreg_status'] = info


class ZTESIMClass(SIMBaseClass):
    """
    ZTE SIM Class
    """
    def __init__(self, sconn):
        super(ZTESIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        d = super(ZTESIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # make sure we are in 3g pref before registration
            self.sconn.send_at(ZTE_DICT['3GPREF'])
            # setup SIM storage defaults
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d.addCallback(init_callback)
        return d


class ZTEDBusDevicePlugin(DBusDevicePlugin):
    """DBusDevicePlugin for ZTE"""
    simklass = ZTESIMClass

    def __init__(self):
        super(ZTEDBusDevicePlugin, self).__init__()


class ZTECustomizer(Customizer):
    async_regexp = None
    ignore_regexp = [ re.compile('\r\n(?P<ignore>\+ZPSTM:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\+ZEND)\r\n'), ]
    conn_dict = ZTE_DICT
    cmd_dict = ZTE_CMD_DICT
