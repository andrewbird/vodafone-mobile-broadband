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
Wrapper around common.SIMCardConnection

It basically provides error control and more high-level operations. N-tier
folks can see this as a Business Logic class.
"""

__version__ = "$Rev: 1172 $"

from collections import deque

from wader.common.encoding import (from_ucs2, from_u, unpack_ucs2_bytes,
                                pack_ucs2_bytes, check_if_ucs2, _)
from wader.common.protocol import SIMCardConnection
import wader.common.exceptions as ex
from wader.common.sms import pdu_to_message

def process_contact_match(match):
    """I process a contact match and return a C{Contact} object out of it"""
    from wader.common.persistent import Contact

    _name = match.group('name')
    if check_if_ucs2(_name):
        name = from_ucs2(_name)
    else:
        name = _name.decode('utf8','ignore').rstrip('\x1f')

    number = from_ucs2(match.group('number'))
    index = int(match.group('id'))
    return Contact(name, number, index=index)

class SIMCardConnAdapter(SIMCardConnection):
    """
    Wrapper around common.SIMCardConnection

    Its main objective is to provide error control on some operations and
    a cleaner API and way to deal with results than directly with
    C{wader.common.protocol.SIMCardConnection}
    """

    def __init__(self, device):
        super(SIMCardConnAdapter, self).__init__(device)

    def add_contact(self, contact):
        """
        Adds C{contact} to the SIM and returns the index where was stored

        @rtype: C{defer.Deferred}
        """ 
        name = from_u(contact.get_name())

        if 'UCS2' in self.device.sim.charset:
            name = pack_ucs2_bytes(name)

        # common arguments for both operations (name and number)
        args = [name, from_u(contact.get_number())]

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

    def add_sms(self, sms):
        """
        Adds C{sms} to the SIM archive
        """
        pdu_len = sms.get_pdu_len()
        d = super(SIMCardConnAdapter, self).add_sms(pdu_len, sms.get_pdu())
        d.addCallback(lambda resp: int(resp[0].group('id')))
        return d

    def check_pin(self):
        """
        Returns the SIM's auth state

        @rtype: C{defer.Deferred}
        """
        def errback(failure):
            if failure.check(ex.ATTimeout):
                print "check_pin: timeout"
            return failure

        e = super(SIMCardConnAdapter, self).error_reporting(2)

        d = super(SIMCardConnAdapter, self).check_pin()
        d.addCallback(lambda result: result[0].group('resp'))
        d.addErrback(errback)
        return d

    def find_contacts(self, pattern):
        """Returns a list of C{Contact} whose name matches pattern"""
        if 'UCS2' in self.device.sim.charset:
            pattern = pack_ucs2_bytes(pattern)
        d = super(SIMCardConnAdapter, self).find_contacts(pattern)
        d.addCallback(lambda matches: [process_contact_match(m)
                                        for m in matches])
        return d

    def get_contacts(self):
        """Returns a list with all the contacts in the SIM"""
        d = super(SIMCardConnAdapter, self).get_contacts()
        def not_found_eb(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d.addCallback(lambda matches:
                      [process_contact_match(m) for m in matches])
        d.addErrback(not_found_eb)
        return d

    def get_contact_by_index(self, index):
        d = super(SIMCardConnAdapter, self).get_contact_by_index(index)
        d.addCallback(lambda match: process_contact_match(match[0]))
        return d

    def get_free_contact_ids(self):
        """Returns a deque with the contact ids not used"""
        def get_contacts_cb(used_ids):
            if not used_ids:
                # if there are no ids used, just return a list 1-sim size
                return deque(range(1, self.device.sim.size))

            # to compute the free ids, we just get XOR the set of 1 - sim size
            # with the set of busy_ids, that will leave a list with only the
            # ids not being used
            busy_ids = [contact.get_index() for contact in used_ids]
            free = set(range(1, self.device.sim.size)) ^ set(busy_ids)
            return deque(list(free))

        def get_contacts_eb(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            # some devices like to raise an exception when there are no
            # contacts
            return deque(range(1, self.device.sim.size))

        d = self.get_contacts()
        d.addCallbacks(get_contacts_cb, get_contacts_eb)
        return d

    def get_used_contact_ids(self):
        """Returns a list with the used contact ids"""
        def callback(contacts):
            if not contacts:
                return []

            return [contact.get_index() for contact in contacts]

        def errback(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d = self.get_contacts()
        d.addCallback(callback)
        d.addErrback(errback)
        return d

    def get_used_sms_ids(self):
        """Returns a list with used SMS ids in the SIM card"""
        d = self.get_sms()
        def process_all_sms(smslist):
            if not smslist:
                return []

            return [sms.get_index() for sms in smslist]

        def errback(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d.addCallback(process_all_sms)
        d.addErrback(errback)
        return d

    def get_sms(self):
        """
        Returns a list of ShortMessage objects with all the SMS in the SIM card
        """
        d = super(SIMCardConnAdapter, self).get_sms()
        def get_all_sms_cb(messages):
            sms_list = []
            for rawsms in messages:
                # ShortMessage obj
                try:
                    sms = pdu_to_message(rawsms.group('pdu'))
                except ValueError:
                    raise ex.MalformedSMSError(rawsms.group('pdu'))
                else:
                    sms.index = int(rawsms.group('id'))
                    sms.where = int(rawsms.group('storedat'))
                    sms_list.append(sms)

            return sms_list

        d.addCallback(get_all_sms_cb)
        return d

    def get_available_charset(self):
        """
        Returns a list with the available character sets

        @rtype: C{defer.Deferred}
        """
        def translate_from_ucs2(arg):
#            arg[0] = '00470053004D'
#            arg[1] = '004900520041'
#            arg[2] = '0038003800350039002D0031'
#            arg[3] = '005500540046002D0038'
#            arg[4] = '0055004300530032'

            if not check_if_ucs2(arg[0]):
                return arg

            cvt = []              # assume all strings are UCS2 and convert
            for p in arg:
                cvt.append(unpack_ucs2_bytes(p))
            return cvt

        d = super(SIMCardConnAdapter, self).get_available_charset()
        d.addCallback(lambda resp: [match.group('lang') for match in resp])
        d.addCallback(translate_from_ucs2)
        return d

    def get_card_model(self):
        """
        Returns the the card's model

        @rtype: C{defer.Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_card_model()
        d.addCallback(lambda response: response[0].group('model'))
        return d

    def get_card_version(self):
        """
        Returns a deferred that will be callbacked with the card's version
        """
        d = super(SIMCardConnAdapter, self).get_card_version()
        d.addCallback(lambda response: response[0].group('version'))
        return d

    def get_charset(self):
        """
        Returns the current charset
        """
        def translate_from_ucs2(arg):
            return (arg == '0055004300530032') and 'UCS2' or arg

        d = super(SIMCardConnAdapter, self).get_charset()
        d.addCallback(lambda response: response[0].group('lang'))
        d.addCallback(translate_from_ucs2)
        return d

    def get_imei(self):
        """
        Returns the card's IMEI number

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_imei()
        d.addCallback(lambda response: response[0].group('imei'))
        return d

    def get_imsi(self):
        """
        Returns the SIM's IMSI number

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_imsi()
        d.addCallback(lambda response: response[0].group('imsi'))
        return d

    def get_manufacturer_name(self):
        """
        Returns the Manufacturer name

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_manufacturer_name()
        d.addCallback(lambda response: response[0].group('name'))
        return d

    def get_phonebook_size(self):
        """
        Returns the phonebook size of the SIM card

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_phonebook_size()
        d.addCallback(lambda resp: int(resp[0].group('size')))
        return d

    def get_pin_status(self):
        """
        Returns 1 if PIN auth is active and 0 if its not

        @rtype: C{Deferred}
        """
        def pinreq_errback(failure):
            failure.trap(ex.CMEErrorSIMPINRequired)
            return 1

        def aterror_eb(failure):
            failure.trap(ex.ATError)
            # return the failure or wont work
            return failure

        d = super(SIMCardConnAdapter, self).get_pin_status()
        d.addCallback(lambda response: int(response[0].group('status')))
        d.addErrback(pinreq_errback)
        d.addErrback(aterror_eb)

        return d

    def get_signal_level(self):
        """
        Returns the signal level

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_signal_level()
        d.addCallback(lambda response: int(response[0].group('rssi')))
        return d

    def get_sms_by_index(self, index):
        """
        Returns a ShortMessage object representing the SMS at C{index}

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_sms_by_index(index)
        def get_sms_cb(rawsms):
            try:
                sms = pdu_to_message(rawsms[0].group('pdu'))
                sms.where = int(rawsms[0].group('storedat'))
                sms.index = index
            except IndexError:
                # handle bogus CMTI notifications, see #180
                return None

            return sms

        d.addCallback(get_sms_cb)
        return d

    def get_smsc(self):
        """
        Returns the SMSC number stored in the SIM

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_smsc()
        def get_smsc_cb(response):
            try:
                smsc = response[0].group('smsc')
                if not smsc.startswith('+'):
                    if check_if_ucs2(smsc):
                        # the smsc is in UCS2 format
                        smsc = from_u(unpack_ucs2_bytes(smsc))

                return smsc
            except KeyError, e:
                raise ex.CMEErrorNotFound()

        d.addCallback(get_smsc_cb)
        return d

    def get_netreg_status(self):
        """
        Returns a tuple with the network registration status

        +CREG: 0,0 - Not registered and not scanning for a GSM network
        +CREG: 0,1 - Registered on the "HOME" network of the SIM
        +CREG: 0,2 - Not registered but is scanning for a GSM network
        +CREG: 0,3 - Registration is denied (Manual attempt failed)
        +CREG: 0,5 - Registered on to another network (roaming).

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_netreg_status()
        def get_netreg_status(resp):
            # convert them to int
            mode = resp[0].group('mode')
            status = resp[0].group('status')
            return int(mode), int(status)

        d.addCallback(get_netreg_status)
        return d

    def get_network_info(self, process=True):
        """
        Returns the network info  (a.k.a AT+COPS?)

        The response will be a tuple as (OperatorName, ConnectionType) if
        it returns a (None, None) that means that some error occurred while
        obtaining the info. The class that requested the info should take
        care of insisting before this problem. This method will convert
        numeric network IDs to alphanumeric.

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_network_info()
        def get_net_info_cb(netinfo):
            """
            Returns a (Networname, ConnType) tuple

            It returns None if there's no info
            """
            if not netinfo:
                return None

            netinfo = netinfo[0]

            if netinfo.group('error'):
                # this means that we've received a response like
                # +COPS: 0 which means that we don't have network temporaly
                # we should raise an exception here
                raise ex.NetworkTemporalyUnavailableError

            try:
                status = int(netinfo.group('status'))
                conn_type = (status == 0) and 'GPRS' or '3G'
            except IndexError:
                conn_type = 'GPRS'

            netname = netinfo.group('netname')

            if netname in ['Limited Service',
                           pack_ucs2_bytes('Limited Service')]:
                return netname, conn_type

            # netname can be in UCS2, as a string, or as a network id (int)
            if check_if_ucs2(netname):
                return unpack_ucs2_bytes(netname), conn_type
            else:
                # now can be either a string or a network id (int)
                try:
                    netname = int(netname)
                except ValueError:
                    # we got a string ID
                    return netname, conn_type

                # if we have arrived here, that means that the network id
                # is a five digit integer
                if not process:
                    return netname, conn_type

                # we got a numeric id, lets convert it
                from wader.common.persistent import net_manager
                network = net_manager.get_network_by_id(netname)
                if network:
                    return network.get_name(), conn_type
# ajb: make consistent display between network returned via id or name
                #    return network.get_full_name(), conn_type

                return _('Unknown Network'), conn_type

        d.addCallback(get_net_info_cb)
        return d

    def get_network_names(self):
        """
        Returns a list of C{NetworkObject}s  (a.k.a AT+COPS=?)

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_network_names()
        d.addCallback(lambda resp: [NetworkOperator(*match.groups())
                                        for match in resp])
        return d

    def get_roaming_ids(self):
        """
        Returns the network ids stored in the SIM to roam (a.k.a AT+CPOL?)

        @rtype: C{Deferred}
        """
        d = super(SIMCardConnAdapter, self).get_roaming_ids()
        def get_roaming_ids_cb(raw):
            return [BasicNetworkOperator(obj.group('netid')) for obj in raw]

        d.addCallback(get_roaming_ids_cb)
        return d

    def send_sms(self, sms):
        """Sends C{sms} and returns the index"""
        pdu_len = sms.get_pdu_len()
        pdu = sms.get_pdu()
        d = super(SIMCardConnAdapter, self).send_sms(pdu, pdu_len)
        return d

    def set_charset(self, charset):
        d = super(SIMCardConnAdapter, self).set_charset(charset)
        d.addCallback(lambda ignored: self.device.sim.set_charset(charset))
        return d

    def set_smsc(self, smsc):
        """Sets the SIMS's SMSC number to C{smsc}"""
        if 'UCS2' in self.device.sim.charset:
            smsc = pack_ucs2_bytes(smsc)
        return super(SIMCardConnAdapter, self).set_smsc(smsc)


class BasicNetworkOperator(object):
    def __init__(self, netid=None):
        super(BasicNetworkOperator, self).__init__()
        self.netid = netid

    def __repr__(self):
        args = (id(self), str(self.netid))
        return '<BasicNetworkOperator at 0x%x %s>' % args

    def __eq__(self, o):
        return self.netid == o.netid

    def __ne__(self, o):
        return not self.__eq__(o)


class NetworkOperator(BasicNetworkOperator):
    """
    I represent a network operator in the mobile network
    """
    def __init__(self, stat, long_name, short_name, netid, rat):
        super(NetworkOperator, self).__init__(int(netid))
        self.stat = stat
        self.long_name = from_ucs2(long_name)
        self.short_name = from_ucs2(short_name)
        self.rat = rat

    def __repr__(self):
        args = (self.long_name, self.netid)
        return '<NetworkOperator "%s" netid: %d>' % args

