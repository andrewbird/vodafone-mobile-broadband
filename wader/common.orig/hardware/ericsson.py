# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
# Author:  Andrew Bird
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
Common stuff for all Ericsson's cards
"""

__version__ = "$Rev: 1190 $"

import re

from wader.common.hardware.base import Customizer
from wader.common.netspeed import bps_to_human
from wader.common.middleware import SIMCardConnAdapter
import wader.common.notifications as notifications
from wader.common.sim import SIMBaseClass

from wader.common.plugin import DBusDevicePlugin

from wader.common.encoding import pack_ucs2_bytes, from_u

from wader.common.command import get_cmd_dict_copy, OK_REGEXP, ERROR_REGEXP
from twisted.python import log
from wader.common.command import ATCmd
import wader.common.exceptions as ex

ERICSSON_DICT = {
   'GPRSONLY' : 'AT+CFUN=5',
   '3GONLY'   : 'AT+CFUN=6',
   'GPRSPREF' : None,
   '3GPREF'   : 'AT+CFUN=1',
}

class EricssonSIMClass(SIMBaseClass):
    """
    Ericsson SIM Class
    """
    def __init__(self, sconn):
        super(EricssonSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):

        self.sconn.reset_settings()
        self.sconn.disable_echo()
        self.sconn.send_at('AT+CFUN=1') # Turn on the radio

        d = super(EricssonSIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # setup SIM storage defaults
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d.addCallback(init_callback)
        return d


class EricssonDBusDevicePlugin(DBusDevicePlugin):
    """DBusDevicePlugin for Ericsson"""
    simklass = EricssonSIMClass

    def __init__(self):
        super(EricssonDBusDevicePlugin, self).__init__()


class EricssonAdapter(SIMCardConnAdapter):
    """
    Adapter for all Ericsson cards
    """
    def __init__(self, device):
        log.msg("called EricssonAdapter::__init__")
        super(EricssonAdapter, self).__init__(device)

    def add_contact(self, contact):
        """
        Adds C{contact} to the SIM and returns the index where was stored

        @rtype: C{defer.Deferred}
        """ 
        name = from_u(contact.get_name())
        number =  from_u(contact.get_number())

        if 'UCS2' in self.device.sim.charset:
            name = pack_ucs2_bytes(name)
            number = pack_ucs2_bytes(number)

        # common arguments for both operations (name and number)
        args = [name, number]

        if contact.index:
            # contact.index is set, user probably wants to overwrite an
            # existing contact
            args.append(contact.index)
            d = super(SIMCardConnAdapter, self).add_contact(*args)
            d.addCallback(lambda _: contact.index)
            return d

        # contact.index is not set, this means that we need to obtain the
        # first slot free on the phonebook and then add the contact
        def get_next_id_cb(index):
            args.append(index)
            d2 = super(SIMCardConnAdapter, self).add_contact(*args)
            # now we just fake add_contact's response and we return the index
            d2.addCallback(lambda _: index)
            return d2

        d = super(SIMCardConnAdapter, self).get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

    def reset_settings(self):
        """
        Resets the settings to factory settings

        @rtype: C{Deferred}
        """
        cmd = ATCmd('AT&F', name='reset_settings')
        return self.queue_at_cmd(cmd)

    def get_signal_level(self):
        """
        On Ericsson, AT+CSQ only returns valid data in GPRS mode

        So we need to override and provide an alternative. +CIND
        returns an indication between 0-5 so let's just multiply
        that by 5 to get a very rough rssi

        @rtype: C{Deferred}
        """

        cmd = ATCmd('AT+CIND?',name='get_signal_indication')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda response: int(response[0].group('sig'))*5)
        return d

    def set_charset(self, charset):
        """
        Sets the character set used on the SIM

        The oddity here is that the set command needs to have its charset value
        encoded in the current character set
        """
        if (self.device.sim.charset == 'UCS2'):
            charset = pack_ucs2_bytes(charset)

        d = super(EricssonAdapter, self).set_charset(charset)
        return d

    def get_pin_status(self):
        """
        Returns 1 if PIN auth is active and 0 if its not

        @rtype: C{Deferred}
        """
        def ericsson_get_pin_status(facility):
            """
            Checks whether the pin is enabled or disabled
            """
            cmd = ATCmd('AT+CLCK="%s",2' % facility, name='get_pin_status')
            return self.queue_at_cmd(cmd)

        def pinreq_errback(failure):
            failure.trap(ex.CMEErrorSIMPINRequired)
            return 1

        def aterror_eb(failure):
            failure.trap(ex.ATError)
            # return the failure or wont work
            return failure

        facility = (self.device.sim.charset == 'UCS2') and pack_ucs2_bytes('SC') or 'SC'

        d = ericsson_get_pin_status(facility)                    # call the local one
        d.addCallback(lambda response: int(response[0].group('status')))
        d.addErrback(pinreq_errback)
        d.addErrback(aterror_eb)
        return d

    def change_pin(self, oldpin, newpin):
        """
        Changes C{oldpin} to C{newpin} in the SIM card

        @type oldpin: C{str}
        @type newpin: C{str}

        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the password is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        password is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        if (self.device.sim.charset == 'UCS2'):
            facility = pack_ucs2_bytes('SC')
            oldpin = pack_ucs2_bytes(oldpin)
            newpin = pack_ucs2_bytes(newpin)
        else:
            facility = 'SC'

        cmd = ATCmd('AT+CPWD="%s","%s","%s"' % (facility, oldpin, newpin),
                    name='change_pin')
        return self.queue_at_cmd(cmd)

    def disable_pin(self, pin):
        """
        Disables pin authentication at startup

        @type pin: C{int}
        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the PIN is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        PIN is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        if (self.device.sim.charset == 'UCS2'):
            facility = pack_ucs2_bytes('SC')
            pin = pack_ucs2_bytes(pin)
        else:
            facility = 'SC'

        cmd = ATCmd('AT+CLCK="%s",0,"%s"' % (facility, pin),
                    name='disable_pin')
        return self.queue_at_cmd(cmd)

    def enable_pin(self, pin):
        """
        Enables pin authentication at startup

        @type pin: C{int}
        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the PIN is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        PIN is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        if (self.device.sim.charset == 'UCS2'):
            facility = pack_ucs2_bytes('SC')
            pin = pack_ucs2_bytes(pin)
        else:
            facility = 'SC'

        cmd = ATCmd('AT+CLCK="%s",1,"%s"' % (facility, pin),
                    name='enable_pin')
        return self.queue_at_cmd(cmd)


class EricssonCustomizer(Customizer):
    """
    Base Customizer class for Ericsson cards
    """

    adapter = EricssonAdapter

    # Multiline so we catch and remove the ESTKSMENU
#    async_regexp = re.compile(r"""\r\n(?P<signal>\*[A-Z]{3,}):(?P<args>.*)\r\n""",
#                        re.MULTILINE)

    ignore_regexp = [ re.compile(r"""\r\n(?P<ignore>\*ESTKSMENU:.*)\r\n""", re.MULTILINE|re.DOTALL),
                      re.compile(r"""\r\n(?P<ignore>\*EMWI.*)\r\n"""),
                      re.compile(r"""\r\n(?P<ignore>\+PACSP0.*)\r\n"""),
                    ]

    conn_dict = ERICSSON_DICT

    cmd_dict = get_cmd_dict_copy()

    cmd_dict['get_card_model'] = dict(echo=None,
                    end=OK_REGEXP,
                    error=ERROR_REGEXP,
                    extract=re.compile('\s*(?P<model>\S*)\r\n'))

    # +CIND: 5,5,0,0,1,0,1,0,1,1,0,0
    cmd_dict['get_signal_indication'] = dict(echo=None,
                    end=OK_REGEXP,
                    error=ERROR_REGEXP,
                    extract=re.compile('\s*\+CIND:\s+[0-9]*,(?P<sig>[0-9]*),.*'))

    cmd_dict['get_network_info'] = dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                          \r\n
                          \+COPS:\s+
                          (
                          (?P<error>\d) |
                          \d,\d,             # or followed by num,num,str,num
                          "(?P<netname>[\w\S ]*)",
                          (?P<status>\d)
                          )                  # end of group
                          \s*
                          \r\n
                          """, re.VERBOSE))

    # +CPBR: 1,"002B003500350035",145,"0041004A0042"\r\n'
    cmd_dict['get_contacts'] = dict(echo=None,
                 end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                       \r\n
                       \+CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?[0123456789ABCDEFabcdef]+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)"
                       """, re.VERBOSE))

