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
Common stuff for all Option's datacards/devices
"""
__version__ = "$Rev: 1172 $"

import re

from wader.common.command import get_cmd_dict_copy, OK_REGEXP, ERROR_REGEXP
from wader.common.hardware.base import Customizer
from wader.common.sim import SIMBaseClass
from wader.common.plugin import DBusDevicePlugin
import wader.common.notifications as N

OPTION_DICT = {
   'GPRSONLY' : 'AT_OPSYS=0,2',
   '3GONLY'   : 'AT_OPSYS=1,2',
   'GPRSPREF' : 'AT_OPSYS=2,2',
   '3GPREF'   : 'AT_OPSYS=3,2',
}


# Option devices like to append its serial number after the IMEI, ignore it
OPTION_CMD_DICT = get_cmd_dict_copy()
info = dict(echo=None,
            end=OK_REGEXP,
            error=ERROR_REGEXP,
            extract=re.compile("\r\n(?P<imei>\d+),\S+\r\n"))

OPTION_CMD_DICT['get_imei'] = info

class OptionSIMClass(SIMBaseClass):
    """
    Nozomi SIM Class

    I just activate unsolicited notifications for ya
    """
    def __init__(self, sconn):
        super(OptionSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        d = super(OptionSIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # make sure we are in 3g pref before registration
            self.sconn.send_at(OPTION_DICT['3GPREF'])
            # setup asynchronous notifications
            self.sconn.send_at('AT_OSSYS=1')
            return size

        d.addCallback(init_callback)
        return d


class OptionDBusDevicePlugin(DBusDevicePlugin):
    """DBusDevicePlugin for Option"""
    simklass = OptionSIMClass

    def __init__(self):
        super(OptionDBusDevicePlugin, self).__init__()


def new_conn_mode_cb(args):
    """
    Translates Option's unsolicited notifications to VMC's representation
    """
    ossysi_args_dict = {
        '0' : N.GPRS_SIGNAL,
        '2' : N.UMTS_SIGNAL,
        '3' : N.NO_SIGNAL,
    }
    return ossysi_args_dict[args]

class OptionCustomizer(Customizer):
    """Customizer for Option's cards"""
    async_regexp = re.compile('\r\n(?P<signal>_OSSYSI):\s(?P<args>\d+)\r\n')
    conn_dict = OPTION_DICT
    cmd_dict = OPTION_CMD_DICT
    device_capabilities = [N.SIG_NEW_CONN_MODE]
    signal_translations = {
        '_OSSYSI' : (N.SIG_NEW_CONN_MODE, new_conn_mode_cb),
    }

