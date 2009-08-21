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
Common stuff for all Novatel's cards
"""

__version__ = "$Rev: 1172 $"

from wader.common.hardware.base import Customizer
from wader.common.sim import SIMBaseClass
from wader.common.plugin import DBusDevicePlugin

# Sphere changes 
# 1/ Preferred modes were actually forced
# 2/ No such thing as 'GPRS pref' on NVTL, just 'Automatic' which is '3G pref'
# 3/ Domains now all CS+PS
NOVATEL_DICT = {
   'GPRSONLY' : 'AT$NWRAT=1,2',
   '3GONLY'   : 'AT$NWRAT=2,2',
   'GPRSPREF' : None,
   '3GPREF'   : 'AT$NWRAT=0,2',
}

class NovatelSIMClass(SIMBaseClass):
    """
    Novatel SIM Class
    """
    def __init__(self, sconn):
        super(NovatelSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        d = super(NovatelSIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # make sure we are in 3g pref before registration
            self.sconn.send_at(NOVATEL_DICT['3GPREF'])
            # setup SIM storage defaults
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d.addCallback(init_callback)
        return d


class NovatelDBusDevicePlugin(DBusDevicePlugin):
    """DBusDevicePlugin for Novatel"""
    simklass = NovatelSIMClass

    def __init__(self):
        super(NovatelDBusDevicePlugin, self).__init__()


class NovatelCustomizer(Customizer):
    async_regexp = None
    conn_dict = NOVATEL_DICT
