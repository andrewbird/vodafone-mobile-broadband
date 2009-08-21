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
Common stuff for all Huawei's cards
"""

__version__ = "$Rev: 1190 $"

import re

from wader.common.hardware.base import Customizer
from wader.common.netspeed import bps_to_human
from wader.common.middleware import SIMCardConnAdapter
import wader.common.notifications as notifications
from wader.common.sim import SIMBaseClass
from wader.common.plugin import DBusDevicePlugin

from wader.common.encoding import (from_ucs2, from_u,
                                unpack_ucs2_bytes_in_ts31101_80,
                                unpack_ucs2_bytes_in_ts31101_81,
                                unpack_ucs2_bytes_in_ts31101_82,
                                pack_ucs2_bytes)

from wader.common.command import get_cmd_dict_copy, OK_REGEXP, ERROR_REGEXP
from twisted.python import log
from wader.common.command import ATCmd
import wader.common.exceptions as ex

HUAWEI_DICT = {
   'GPRSONLY' : 'AT^SYSCFG=13,1,3FFFFFFF,2,4',
   '3GONLY'   : 'AT^SYSCFG=14,2,3FFFFFFF,2,4',
   'GPRSPREF' : 'AT^SYSCFG=2,1,3FFFFFFF,2,4',
   '3GPREF'   : 'AT^SYSCFG=2,2,3FFFFFFF,2,4',
}

def huawei_new_conn_mode(args):
    """Translates C{arg} to VMC's language"""
    mode_args_dict = {
        '0,0' : notifications.NO_SIGNAL,
        '3,0' : notifications.NO_SIGNAL,
        '3,1' : notifications.GPRS_SIGNAL,
        '3,2' : notifications.GPRS_SIGNAL,
        '3,3' : notifications.GPRS_SIGNAL,
        '5,0' : notifications.NO_SIGNAL,
        '5,4' : notifications.UMTS_SIGNAL,
        '5,5' : notifications.HSDPA_SIGNAL,
        '5,6' : notifications.HSUPA_SIGNAL,
        '5,7' : notifications.HSPA_SIGNAL, # doc says HSDPA + HSUPA ain't that
                                           # just HSPA?
        '5,9' : notifications.HSPA_SIGNAL, # doc says HSPA+
    }
    return mode_args_dict[args]

def huawei_radio_switch(args):
    state_args_dict = {
        '0,0' : notifications.RADIO_OFF,
        '0,1' : notifications.RADIO_OFF,
        '1,0' : notifications.RADIO_OFF,
        '1,1' : notifications.RADIO_ON,
    }
    return state_args_dict[args]

def huawei_new_speed_link(args):
    converted_args = map(lambda hexstr: int(hexstr, 16), args.split(','))
    time, tx, rx, tx_flow, rx_flow, tx_rate, rx_rate = converted_args
    return bps_to_human(tx * 8, rx * 8)

class HuaweiSIMClass(SIMBaseClass):
    """
    Huawei SIM Class
    """
    def __init__(self, sconn):
        super(HuaweiSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):

        d = super(HuaweiSIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # make sure we are in 3g pref before registration
            self.sconn.send_at(HUAWEI_DICT['3GPREF'])
            # setup SIM storage defaults
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d.addCallback(init_callback)
        return d


class HuaweiDBusDevicePlugin(DBusDevicePlugin):
    """DBusDevicePlugin for Huawei"""
    simklass = HuaweiSIMClass

    def __init__(self):
        super(HuaweiDBusDevicePlugin, self).__init__()


class HuaweiAdapter(SIMCardConnAdapter):
    """
    Adapter for all Huawei E2XX cards
    """
    def __init__(self, device):
        super(HuaweiAdapter, self).__init__(device)

    def set_smsc(self, smsc):
        """
        Sets the SIM's smsc to C{smsc}

        We wrap the operation with set_charset('IRA') and set_charset('UCS2')
        """
        # XXX: The return value of this method is actually the return value
        # of the set_charset("UCS2") operation
        d = self.set_charset('IRA')
        d.addCallback(lambda _: super(HuaweiAdapter, self).set_smsc(smsc))
        d.addCallback(lambda _: self.set_charset('UCS2'))
        return d

    def add_contact(self, contact):
        """
        Adds C{contact} to the SIM and returns the index where was stored

        @rtype: C{defer.Deferred}
        """

        def hw_add_contact(name, number, index):
            """
            Adds a contact to the SIM card
            """
            try:     # are all ascii chars
                name.encode('ascii')
                raw = 0
            except:  # write in TS31.101 type 80 raw format
                name = '80' + pack_ucs2_bytes(name) + 'FF'
                raw = 1

            category = number.startswith('+') and 145 or 129
            args = (index, number, category, name, raw)
            cmd = ATCmd('AT^CPBW=%d,"%s",%d,"%s",%d' % args, name='add_contact')
            return self.queue_at_cmd(cmd)

        name = from_u(contact.get_name())

        # common arguments for both operations (name and number)
        args = [name, from_u(contact.get_number())]

        if contact.index:
            # contact.index is set, user probably wants to overwrite an
            # existing contact
            args.append(contact.index)
            d = hw_add_contact(*args)
            d.addCallback(lambda _: contact.index)
            return d

        # contact.index is not set, this means that we need to obtain the
        # first slot free on the phonebook and then add the contact
        def get_next_id_cb(index):
            args.append(index)
            d2 = hw_add_contact(*args)
            # now we just fake add_contact's response and we return the index
            d2.addCallback(lambda _: index)
            return d2

        d = super(HuaweiAdapter, self).get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

    def hw_process_contact_match(self, match):
        """I process a contact match and return a C{Contact} object out of it"""
        from wader.common.persistent import Contact
        if int(match.group('raw')) == 0:
            name = match.group('name').decode('utf8','ignore').rstrip('\x1f')
        else:
            encoding = match.group('name')[:2]
            hexbytes = match.group('name')[2:]
            if encoding == '80':   # example '80058300440586FF'
                name = unpack_ucs2_bytes_in_ts31101_80(hexbytes)
            elif encoding == '81': # example '810602A46563746F72FF'
                name = unpack_ucs2_bytes_in_ts31101_81(hexbytes)
            elif encoding == '82': # example '820505302D82D32D31'
                name = unpack_ucs2_bytes_in_ts31101_82(hexbytes)
            else:
                name = "Unsupported encoding"

        number = from_ucs2(match.group('number'))
        index = int(match.group('id'))

        return Contact(name, number, index=index)

    def get_contacts(self):
        """Returns a list with all the contacts in the SIM"""
        def hw_get_contacts():
            cmd = ATCmd('AT^CPBR=1,%d' % self.device.sim.size, name='get_contacts')
            return self.queue_at_cmd(cmd)

        d = hw_get_contacts()
        def not_found_eb(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d.addCallback(lambda matches: [self.hw_process_contact_match(m) for m in matches])
        d.addErrback(not_found_eb)
        return d

    def get_contact_by_index(self, index):
        def hw_get_contact_by_index(index):
            cmd = ATCmd('AT^CPBR=%d' % index, name='get_contact_by_index')
            return self.queue_at_cmd(cmd)

        d = hw_get_contact_by_index(index)
        d.addCallback(lambda match: self.hw_process_contact_match(match[0]))
        return d


class HuaweiCustomizer(Customizer):
    """
    Base Customizer class for Huawei cards
    """
    adapter = HuaweiAdapter

    async_regexp = re.compile('\r\n(?P<signal>\^MODE|\^RSSI|\^DSFLOWRPT|\^RFSWITCH):(?P<args>.*)\r\n')
    ignore_regexp = [ re.compile('\r\n(?P<ignore>\^BOOT:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^CSNR:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^EARST:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^SRVST:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^SIMST:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^STIN:.*)\r\n'),
                      re.compile('\r\n(?P<ignore>\^SMMEMFULL:.*)\r\n'), ]
    conn_dict = HUAWEI_DICT
    device_capabilities = [notifications.SIG_NEW_CONN_MODE,
                           notifications.SIG_RSSI,
                           notifications.SIG_SPEED,
                           notifications.SIG_RFSWITCH]

    cmd_dict = get_cmd_dict_copy()

    cmd_dict['get_card_model'] = dict(echo=None,
                    end=OK_REGEXP,
                    error=ERROR_REGEXP,
                    extract=re.compile('\s*(?P<model>\S*)\r\n'))

    cmd_dict['get_radio'] = dict(echo=None,
                    end=OK_REGEXP,
                    error=ERROR_REGEXP,
                    extract=re.compile('\s*\^RFSWITCH:(?P<switch>\S*)\r\n'))

    cmd_dict['get_contact_by_index'] = dict(echo=None,
                    end=re.compile('\r\nOK\r\n'),
                    error=ERROR_REGEXP,
                    extract=re.compile(r"""
                       \r\n
                       \^CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?\d+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)",
                       (?P<raw>\d+)
                       \r\n
                       """, re.VERBOSE))

    cmd_dict['get_contacts'] = dict(echo=None,
                 # one extra \r\n just in case
                 end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                       \r\n
                       \^CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?\d+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)",
                       (?P<raw>\d+)
                       """, re.VERBOSE))

    signal_translations = {
        '^MODE' : (notifications.SIG_NEW_CONN_MODE, huawei_new_conn_mode),
        '^RSSI' : (notifications.SIG_RSSI, lambda i: int(i)),
        '^DSFLOWRPT' : (notifications.SIG_SPEED, huawei_new_speed_link),
        '^RFSWITCH' : (notifications.SIG_RFSWITCH, huawei_radio_switch),
    }


class HuaweiEMXXAdapter(HuaweiAdapter):         # Modules have RFSWITCH
    """
    Adapter for all Huawei embedded modules
    """
    def __init__(self, device):
        super(HuaweiEMXXAdapter, self).__init__(device)

    def get_signal_level(self):
        """
        Returns the signal level
            @rtype: C{Deferred}
            Overloaded to poll the RFSWITCH status
        """

        cmd = ATCmd('AT^RFSWITCH?',name='get_radio')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda _: super(HuaweiEMXXAdapter, self).get_signal_level())
        return d


class HuaweiEMXXCustomizer(HuaweiCustomizer):
    """
    Customizer for all Huawei embedded modules
    """
    adapter = HuaweiEMXXAdapter

