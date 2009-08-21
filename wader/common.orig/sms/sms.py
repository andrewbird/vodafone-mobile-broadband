# -*- coding: utf-8 -*-
# Authors:  Pablo Martí, Thomas Lotze and Vivesto Solutions
#
# This module is the result of a merge between code owned by Thomas Lotze
# and Vivesto Solutions plus some improvements of my own.
#
# This file should be licensed under the MPL and the ZPL. While former is
# GPL-compatible, the MPL isn't. The MPL allows you to modify files and add
# portions of them to files of your own as long as you keep the copyright,
# the license, and you gotta explain what you did. Both licenses allow you to
# do whatever you want with the code as long as you maintain licenses. I had
# them separated before, but adding stuff was just impossible. After the
# merge, I've added some stuff of my own, I guess that the copyright is
# shared. This should be probably better clarified with a lawyer
# but for now, I will just leave this header. I hope it explains the situation
# and gives credit to all the parties.
"""
SMS related classes and utilities
"""
__version__ = "$Rev: 1172 $"

import time
import datetime

from zope.interface import implements

from wader.common.encoding import (from_u, int2hexstr, swap, pack_7bit_bytes,
                                 unpack_7bit_bytes, pack_ucs2_bytes,
                                 ucs2_decoder, hex_decoder)
from wader.common.interfaces import IShortMessage

MAX_LENGTH_7BIT = 160
MAX_LENGTH_8BIT = 140
MAX_LENGTH_UCS2 = 70

UNKNOWN = 0
INTERNATIONAL = ISDNORTELEPHONE = 1
NATIONAL = 2
NETWORK_SPECIFIC = 3
SUBSCRIBER = 4
ALPHANUMERIC = 5 # (coded according to 3GPP TS 23.038 [9] GSM 7-bit default alphabet)
ABBREVIATED = 6
RESERVED = 7


class GSMAddress(object):

    def __init__(self, number, type=UNKNOWN):

        if type == ALPHANUMERIC:
            self.type_of_number = ALPHANUMERIC
            septets = unpack_7bit_bytes(number)
            self.number = gsm_decoder(septets)

            self.numbering_plan_id = UNKNOWN

        elif type == INTERNATIONAL:
            self.type_of_number = INTERNATIONAL
            if number.startswith('+'):
                self.number = number[1:]
            else:
                self.number = number

            self.numbering_plan_id = ISDNORTELEPHONE

        else:
            if number.startswith('+'):
                self.type_of_number = INTERNATIONAL
                self.number = number[1:]
            else:
                self.type_of_number = UNKNOWN
                self.number = number

            self.numbering_plan_id = ISDNORTELEPHONE

    def serialize(self):

        if self.type_of_number == ALPHANUMERIC:
            print "Don't know how to serialize an alphanumeric SMS yet"
            return ""

        result = []
        result.append(int2hexstr(len(self.number)))

        # GSM 03.40, section 9.1.2.5
        header = 0x80

        header = header | (self.type_of_number << 4)
        header = header | self.numbering_plan_id

        result.append(int2hexstr(header))
        result.append(swap(self.number))

        return "".join(result)

DEFAULT_ALPHABET = 0x00
EIGHT_BIT = 0x04
UCS2 = 0x08

def gsm_decoder(septets):
    text = u''.join(chr(c) for c in septets)
    return text.decode('sms-default')


class ShortMessage(object):
    """I represent a SMS in the system"""

    implements(IShortMessage)

    def __init__(self, number=None, text=None, _datetime=None,
                 where=None, index=None):
        super(ShortMessage, self).__init__()
        self.number = number
        self.text = text
        self.datetime = _datetime
        self.where = where
        self.index = index

    def __cmp__(self, m):
        return cmp(self.get_number(), m.get_number()) | \
                            cmp(self.get_text(), m.get_text())

    def __eq__(self, m):
        return self.get_number() == m.get_number() and \
                   self.get_text() == m.get_text()

    def __ne__(self, m):
        return not self.__eq__(m)

    def __str__(self):
        args = (self.__class__.__name__,
                self.datetime,
                self.index != None and self.index or 0,
                self.get_number(),
                self.text) 
        return "<%s instance (%s): index=%d, number = %s, text: '%s'>" % args

    def __repr__(self):
        return self.__str__()

    def get_localised_date(self):
        return self.datetime and time.strftime("%c",
                           self.datetime.timetuple()) or None
    def get_number(self):
        return self.number

    def get_text(self):
        return self.text

    def get_index(self):
        return self.index

    def user_data_from_octets(self, flags, octets, coding_scheme):
        user_data_len = octets.pop(0)

        if flags & 0x40: # user data header indicator
            header_len8 = octets[0] + 1
            self.header = octets[1:header_len8]
        else:
            header_len8 = 0

        compressed = (coding_scheme & 0xE0 == 0x20)
        if compressed:
            raise NotImplementedError()

        if (coding_scheme & 0xEC == 0x00 or     # general data coding
            coding_scheme & 0xE0 == 0xC0 or     # message waiting indication
            coding_scheme & 0xF4 == 0xF0):      # data coding/message class
            coding = DEFAULT_ALPHABET
        elif (coding_scheme & 0xEC == 0x04 or   # general data coding
              coding_scheme & 0xF4 == 0xF4):    # data coding/message class
            coding = EIGHT_BIT
        elif (coding_scheme & 0xEC == 0x08 or   # general data coding
              coding_scheme & 0xF0 == 0xE0):    # message waiting indication
            coding = UCS2
        else:
            raise ValueError("Unsupported coding scheme: %d" % coding_scheme)

        if coding == DEFAULT_ALPHABET:
            header_len7 = (header_len8 * 8 + 6) / 7 # ceil(int*8/7)
            septets = unpack_7bit_bytes(octets)[header_len7:user_data_len]
            self.text = gsm_decoder(septets)
        else:
            octets = octets[header_len8:user_data_len]
            user_data = "".join(chr(o) for o in octets)
            if coding == UCS2:
                self.text = ucs2_decoder(user_data)[0]
            else:
                self.text = user_data

class ShortMessageDeliver(ShortMessage):

    def protocol_data_from_octets(self, flags, octets):
        self.address = gsm_address_from_octets(octets)
        del octets[0] # protocol identifier
        coding_scheme = octets.pop(0)
        self.datetime = datetime_from_octets(octets)

        return coding_scheme

    def get_number(self):
        if self.address.type_of_number == INTERNATIONAL:
            return '+' + self.address.number
        else:
            return self.address.number

class ShortMessageSubmit(ShortMessage):

    def __init__(self, number, text, smsc=None, validity=None, **kwds):
        super(ShortMessageSubmit, self).__init__(number, text, **kwds)
        self.address = GSMAddress(from_u(number))
        self.smsc = smsc
        self.encoding = None
        self.user_data = None
        self.__set_text(text)
        self.validity = None
        self._set_validity(validity)

    def __set_text(self, text):
        try:
            sms_text = text.encode('sms-default')
            self.user_data_length = len(sms_text)
            self.user_data = pack_7bit_bytes(sms_text)
            self.encoding = DEFAULT_ALPHABET
        except UnicodeError, e:
            self.user_data = pack_ucs2_bytes(text)
            self.user_data_length = len(self.user_data) / 2
            self.encoding = UCS2

    def _set_validity(self, validity):
        """
        Sets the SMS's validity

        @type validity: datetime.timedelta
        """
        # Validity format
        # VP Value
        # 0 - 143    (VP + 1) x 5 minutes
        # 144-167    12 hours + ((VP-143) x 30 minutes)
        # 168-196    (VP-166) x 1 day
        # 197-255    (VP-192) x 1 week

        if not validity:
            self.validity = 170 # 4 days by default

        elif validity.days <= 1:
            self.validity = 167 # at least 1 day of validity

        elif validity.days <= 30:
            self.validity = validity.days + 166

        elif validity.days <= 63:
            self.validity = validity.days + 192

        else:
            self.validity = 255  # thats the maximum baby

    def protocol_data_from_octets(self, flags, octets):
        del octets[0] # TP message reference
        self.address = gsm_address_from_octets(octets)
        del octets[0] # protocol identifier
        coding_scheme = octets.pop(0)

        # TP validity period
        if flags & 0x08: # enhanced or absolute format
            del octets[:7]
        elif flags & 0x10: # relative format
            del octets[0]

        return coding_scheme

    def get_number(self):
        if self.address.type_of_number == INTERNATIONAL:
            return '+' + self.address.number
        else:
            return self.address.number

    def get_text(self):
        return self.text

    def get_pdu_len(self):
        lenpdu = len(self.get_pdu())
        return (lenpdu / 2) - self.get_smsc_len() - 1

    def get_smsc_len(self):
        swapped_smsc = swap(self.smsc[1:])
        swapped_smsc = '91' + swapped_smsc
        return len(swapped_smsc) / 2

    def get_pdu(self):
        """Returns the PDU of the message"""
        pdu = []
        assert self.smsc.startswith('+')
        swapped_smsc = swap(self.smsc[1:])
        swapped_smsc = '91' + swapped_smsc

        pdu.append(int2hexstr(self.get_smsc_len()))
        pdu.append(swapped_smsc)

        # TP-Message-Type-Indicator = 01
        # header = header | 0x01

        # TP-Reject-Duplicates = 0

        # TP-Validity-Period-Format = 00 (TP-VP field not present)

        # TP-Status-Report-Request = 0

        # TP-User-Data-Header-Indicator

        # TP-Reply-Path = 0
        #pdu.append(int2hexstr(header))
        pdu.append(int2hexstr(17))
        # TP-Message-Reference = 0
        pdu.append(int2hexstr(0))

        # TP-Destination-Address
        pdu.append(self.address.serialize())

        # TP-Protocol-Identifier
        pdu.append(int2hexstr(0))

        # TP-Data-Coding-Scheme
        dcs = 0
        if self.encoding == DEFAULT_ALPHABET:
            dcs = dcs | 0x00
        else:
            dcs = dcs | 0x08

        pdu.append(int2hexstr(dcs))

        # TP-Validity-Period
        pdu.append(int2hexstr(self.validity))

        # TP-User-Data-Length
        pdu.append(int2hexstr(self.user_data_length))

        # TP-User-Data
        pdu.append(self.user_data)

        return "".join(pdu)

# RECV PART

def gsm_address_from_octets(octets):
    """Read a gsm address from octets.

    Consumes those octets holding the address field.

    returns GSMAddress
    """
    address_len = octets.pop(0) # seems to be the number of significant nybbles
    address_type = (octets.pop(0) >> 4 ) & 0x07 # bits 654

    if address_type == ALPHANUMERIC:
        address = []
        num_octets = address_len / 2 + address_len % 2 # if odd gather the last one up too.
        while len(address) < num_octets:
            o = octets.pop(0)
            address.append(o)
    else:
        address = ""
        while len(address) < address_len:
            o = octets.pop(0)
            address += str(o & 15) + str(o >> 4)
        address = address[:address_len]

    return GSMAddress(address, address_type)

def datetime_from_octets(octets):
    """
    Returns a datetime object from octets

    Consumes those octets holding the timestamp.

    returns naive datetime.datetime instance relative to UTC
    """
    values = [(o & 15) * 10 + (o >> 4) for o in octets[:7]]
    del octets[:7]
    year = values[0]
    if year < 68:
        year = year + 2000 # YK2 Bug here

    try:
        result = datetime.datetime(year, *values[1:6])
    except ValueError, e:
        raise ValueError("Invalid datetime values: %s\n%s" % (values[1:6], e))

    zone = values[-1]
    delta = datetime.timedelta(minutes=(zone & 127) * 15)
    if zone & 128:
        result -= delta
    else:
        result += delta

    return result

def pdu_to_message(pdu):
    octets = [ord(c) for c in hex_decoder(pdu)[0]]

    smsc_len = octets.pop(0)
    del octets[0] # delete smsc address type
    del octets[:smsc_len - 1] # delete smsc address

    flags = octets.pop(0)
    sms = (flags & 3) and ShortMessageSubmit() or ShortMessageDeliver()
    coding_scheme = sms.protocol_data_from_octets(flags, octets)
    sms.user_data_from_octets(flags, octets, coding_scheme)

    return sms
