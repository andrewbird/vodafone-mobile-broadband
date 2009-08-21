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

__version__ = "$Rev: 1172 $"

import os

import codecs
import gettext

gettext.bindtextdomain('VMC', os.getenv('TEXTDOMAINDIR', '/usr/share/locale'))
gettext.textdomain('VMC')
_ = gettext.gettext

ucs2_encoder = codecs.getencoder("utf_16be")
ucs2_decoder = codecs.getdecoder("utf_16be")
hex_decoder = codecs.getdecoder("hex_codec")

def int2hexstr(i):
    """
    Returns the hex representation of C{i}

    @rtype: str
    """
    return '%02X' % i

def swap(source):
    """
    Convert a string of numbers into the semi-octet representation
    described in GSM 03.40, 9.1.2.3
    """
    out = ''
    if len(source) % 2:
        source += 'F'

    for i in range(0, len(source), 2):
        out += source[i + 1]
        out += source[i]

    return out

def pack_7bit_bytes(s):
    """
    pack_7bit_bytes("hellohello") => "E8329BFD4697D9EC37"

    Packs a series of 7-bit bytes into 8-bit bytes and then to
    ASCII strings as hexidecimal. See GSM 03.40, 9.1.2.1
    """
    out = ''
    for i in range(0, len(s)):
        if i % 8 == 7:
            continue

        end = ord(s[i]) >> (i % 8)

        if i + 1 < len(s):
            start = ord(s[i + 1]) << (7 - (i % 8))
            start = start & 0xFF
            out += int2hexstr(start | end)
        else:
            out += int2hexstr(end)

    return out

def unpack_7bit_bytes(octets):
    """Decode 7 bit character strings packed into 8 bit byte strings"""
    septets = []
    overflow = overflow_len = 0

    for value in octets:
        septets.append(value << overflow_len & 127 | overflow)
        overflow = value >> (7 - overflow_len)
        overflow_len += 1
        if overflow_len == 7:
            septets.append(overflow)
            overflow = overflow_len = 0

    return septets

def pack_8bit_bytes(s):
    return "".join([int2hexstr(ord(c)) for c in s])

def pack_ucs2_bytes(s):
    return "".join([int2hexstr(ord(c)) for c in ucs2_encoder(s)[0]])

#def unpack_ucs2_bytes(s):
#    octets = [ord(c) for c in hex_decoder(s)[0]]
#    user_data = "".join(chr(o) for o in octets)
#    return ucs2_decoder(user_data)[0]

def unpack_ucs2_bytes(s):
    return codecs.utf_16_be_decode(s.decode('hex'))[0]

def unpack_ucs2_bytes_in_ts31101_80(s):
    """
    Returns a string from C{s} which is a string encoded in the format
    described in TS 31.101 (Annex A) type 80. Below is the detail from there,
    but we expect the first two hex chars(80) to have been removed already.

    If the first byte in the alpha string is '80', then the remaining bytes are 16 bit UCS2 characters, with the more
    significant byte (MSB) of the UCS2 character coded in the lower numbered byte of the alpha field, and the less
    significant byte (LSB) of the UCS2 character is coded in the higher numbered alpha field byte, i.e. byte 2 of the
    alpha field contains the more significant byte (MSB) of the first UCS2 character, and byte 3 of the alpha field
    contains the less significant byte (LSB) of the first UCS2 character (as shown below). Unused bytes shall be set
    to 'FF', and if the alpha field is an even number of bytes in length, then the last (unusable) byte shall be set to 'FF'.
    """

    # example string '058300440586FF'

    vl = len(s) - len(s) % 4
    vs = s[:vl]
    try:
        t = unpack_ucs2_bytes(vs)
    except:
        t = vs # show the invalid unicode

    return t

def unpack_ucs2_bytes_in_ts31101_81(s):
    """
    Returns a string from C{s} which is a string encoded in the format
    described in TS 31.101 (Annex A) type 81. Below is the detail from there,
    but we expect the first two hex chars(81) to have been removed already.

    If the first byte of the alpha string is set to '81', then the second byte contains a value indicating the number of
    characters in the string, and the third byte contains an 8 bit number which defines bits 15 to 8 of a 16 bit base
    pointer, where bit 16 is set to zero, and bits 7 to 1 are also set to zero. These sixteen bits constitute a base pointer
    to a "half-page" in the UCS2 code space, to be used with some or all of the remaining bytes in the string. The
    fourth and subsequent bytes in the string contain codings as follows; if bit 8 of the byte is set to zero, the
    remaining 7 bits of the byte contain a GSM Default Alphabet character, whereas if bit 8 of the byte is set to one,
    then the remaining seven bits are an offset value added to the 16 bit base pointer defined earlier, and the resultant
    16 bit value is a UCS2 code point, and completely defines a UCS2 character.
    """

    # example string '0602A46563746F72FF'

    num = ord(s[:2].decode('hex'))
    base = (ord(s[2:4].decode('hex')) & 0x7f) << 7 # bits 15..8
    chars = s[4:4+num*2]

    t = ''
    for i in range(num):
        j = i*2
        c_hex = chars[j:j+2]
        c_chr = c_hex.decode('hex')
        c_ord = ord(c_chr)

        if c_ord & 0x80 == 0:
            t += c_chr
        else:
            t += unichr(base + (c_ord & 0x7f))
    return t

def unpack_ucs2_bytes_in_ts31101_82(s):
    """
    Returns a string from C{s} which is a string encoded in the format
    described in TS 31.101 (Annex A) type 82. Below is the detail from there,
    but we expect the first two hex chars(82) to have been removed already.

    If the first byte of the alpha string is set to '82', then the second byte contains a value indicating the number of
    characters in the string, and the third and fourth bytes contain a 16 bit number which defines the complete 16 bit
    base pointer to a "half-page" in the UCS2 code space, for use with some or all of the remaining bytes in the
    string. The fifth and subsequent bytes in the string contain codings as follows; if bit 8 of the byte is set to zero,
    the remaining 7 bits of the byte contain a GSM Default Alphabet character, whereas if bit 8 of the byte is set to
    one, the remaining seven bits are an offset value added to the base pointer defined in bytes three and four, and
    the resultant 16 bit value is a UCS2 code point, and defines a UCS2 character.
    """

    # example string '0505302D82D32D31'

    num = ord(s[:2].decode('hex'))
    base = ord(s[2:4].decode('hex')) << 8 # bits 16..9
    base += ord(s[4:6].decode('hex'))     # bits  8..1
    chars = s[6:6+num*2]

    t = ''
    for i in range(num):
        j = i*2
        c_hex = chars[j:j+2]
        c_chr = c_hex.decode('hex')
        c_ord = ord(c_chr)

        if c_ord & 0x80 == 0:
            t += c_chr
        else:
            t += unichr(base + (c_ord & 0x7f))
    return t

def check_if_ucs2(text):
    """Returns True if C{text} is a string encoded in UCS2"""
    if isinstance(text, str) and (len(text) % 4 == 0):
        try:
            unpack_ucs2_bytes(text)
        except (UnicodeDecodeError, TypeError):
            return False
        else:
            return True

    return False

def from_u(s):
    return isinstance(s, unicode) and s.encode('utf8') or s

def from_ucs2(s):
    return check_if_ucs2(s) and unpack_ucs2_bytes(s) or s

def to_u(s):
    """Returns a unicode object from C{s} if C{s} is not unicode already"""
    return isinstance(s, unicode) and s or unicode(s, 'utf8')
