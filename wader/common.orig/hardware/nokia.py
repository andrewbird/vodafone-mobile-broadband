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
Common stuff for all Nokia's devices
"""

__version__ = "$Rev: 1172 $"

from twisted.python import log

import wader.common.exceptions as ex
from wader.common.hardware.base import Customizer
from wader.common.sim import SIMBaseClass

NOKIA_DICT = {
   'GPRSONLY' : None,
   '3GONLY'   : None,
   'GPRSPREF' : None,
   '3GPREF'   : None,
}

class NokiaCustomizer(Customizer):
    async_regexp = None
    conn_dict = NOKIA_DICT
    device_capabilities = list()
    signal_translations = dict()

class NokiaSIMBaseClass(SIMBaseClass):

    def __init__(self, sconn):
        super(NokiaSIMBaseClass, self).__init__(sconn)

    def init(self, ucs2=True):
        """
        Returns a C{Deferred} that will be callbacked when the SIM is ready

        @param ucs2: If True, it will set the SIM's enconding to UCS2

        The response must be the SIM size
        """
        d = self.sconn.disable_echo()
        def disable_echo_cb(_):
            pass
        def disable_echo_eb(failure):
            failure.trap(ex.CMEErrorOperationNotAllowed)
            log.err(failure)

        d.addCallbacks(disable_echo_cb, disable_echo_eb)

        if ucs2:
            # Huawei E220's firmware is buggy and if we set encoding to
            # UCS2 before asking for the SMSC, the card will reset
            def set_ucs2_charset_cb(ignored):
                pass
            def set_ucs2_charset_eb(failure):
                failure.trap(ex.CMEErrorOperationNotAllowed)
                log.err(failure)

            d = self.sconn.set_charset("UCS2")
            d.addCallbacks(set_ucs2_charset_cb, set_ucs2_charset_eb)

        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(2, 1)
        # set PDU mode
        self.sconn.set_sms_format(0)

        def phonebook_size_cb(size):
            self.set_size(size)
            return size

        d = self.sconn.get_phonebook_size()
        d.addCallback(phonebook_size_cb)
        return d

