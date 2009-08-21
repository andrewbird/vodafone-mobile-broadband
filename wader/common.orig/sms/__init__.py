# -*- coding: utf-8 -*-
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and
# limitations under the License.

# The Original Code is Vivesto Solutions code.

# The Initial Developer of the Original Code is Viveto Solutions.
# Portions created by the Initial Developer are Copyright (C) 2003 the
# Initial Developer. All Rights Reserved.

# Modified by Pablo Marti at Warp Networks S.L. 11 Jan 2007
# Added a __version__ field, added more comments and organised code

__version__ = "$Rev: 1172 $"

import codecs

### Decoding Map

decoding_map = codecs.make_identity_dict(range(128))
decoding_map.update({
        0x0000: 0x0040, # @ COMMERCIAL AT
        0x0001: 0x00a3, # £ POUND SIGN
        0x0002: 0x0024, # $ DOLLAR SIGN
        0x0003: 0x00a5, # ¥ YEN SIGN
        0x0004: 0x00e8, # è LATIN SMALL LETTER E WITH GRAVE
        0x0005: 0x00e9, # é LATIN SMALL LETTER E WITH ACUTE
        0x0006: 0x00f9, # ù LATIN SMALL LETTER U WITH ACUTE
        0x0007: 0x00ec, # ì LATIN SMALL LETTER I WITH GRAVE
        0x0008: 0x00f2, # ò LATIN SMALL LETTER O WITH GRAVE
        0x0009: 0x00c7, # Ç LATIN CAPITAL LETTER C WITH CEDILLA

        0x000b: 0x00d8, # Ø LATIN CAPITAL LETTER O WITH STROKE
        0x000c: 0x00f8, # ø LATIN SMALL LETTER O WITH STROKE

        0x000e: 0x00c5, # Å LATIN CAPITAL LETTER A WITH RING ABOVE
        0x000f: 0x00e5, # å LATIN SMALL LETTER A WITH RING ABOVE
        0x0010: 0x0394, # GREEK CAPITAL LETTER DELTA
        0x0011: 0x005f, # LOW LINE
        0x0012: 0x03a6, # GREEK CAPITAL LETTER PHI
        0x0013: 0x0393, # GREEK CAPITAL LETTER GAMMA
        0x0014: 0x039b, # GREEK CAPITAL LETTER LAMBDA
        0x0015: 0x03a9, # GREEK CAPITAL LETTER OMEGA
        0x0016: 0x03a0, # GREEK CAPITAL LETTER PI
        0x0017: 0x03a8, # GREEK CAPITAL LETTER PSI
        0x0018: 0x03a3, # GREEK CAPITAL LETTER SIGMA
        0x0019: 0x0398, # GREEK CAPITAL LETTER THETA
        0x001a: 0x039e, # GREEK PITAL LETTER XI
        0x001b: None,   # XXX: ESCAPE TO EXTENSION TABLE
        0x001c: 0x00c6, # Æ LATIN CAPITAL LETTER AE
        0x001d: 0x00e6, # æ LATIN SMALL LETTER AE
        0x001e: 0x00df, # ß LATIN SMALL LETTER SHARP S
        0x001f: 0x00c9, # É LATIN CAPITAL LETTER E WITH ACUTE

        0x0024: 0x00a4, # € EURO CURRENCY SIGN

        0x0040: 0x00a1, # ¡ INVERTED EXCLAMATION MARK

        0x005b: 0x00c4, # Ä LATIN CAPITAL LETTER A WITH DIAERESIS
        0x005c: 0x00d6, # Ö LATIN CAPITAL LETTER O WITH DIAERESIS
        0x005d: 0x00d1, # Ñ LATIN CAPITAL LETTER N WITH TILDE
        0x005e: 0x00dc, # Ü LATIN CAPITAL LETTER U WITH DIAERESIS
        0x005f: 0x00a7, # § SECTION SIGN
        0x0060: 0x00bf, # ¿ INVERTED QUESTION MARK

        0x007b: 0x00e4, # ä LATIN SMALL LETTER A WITH DIAERESIS
        0x007c: 0x00f6, # ö LATIN SMALL LETTER O WITH DIAERESIS
        0x007d: 0x00f1, # ñ LATIN SMALL LETTER N WITH TILDE
        0x007e: 0x00fc, # ü LATIN SMALL LETTER U WITH DIAERESIS
        0x007f: 0x00e0, # à LATIN SMALL LETTER A WITH GRAVE
})

### Encoding Map

encoding_map = codecs.make_encoding_map(decoding_map)

### Codec APIs

class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):

        return codecs.charmap_encode(input, errors, encoding_map)

    def decode(self, input, errors='strict'):

        return codecs.charmap_decode(input, errors, decoding_map)

class StreamWriter(Codec, codecs.StreamWriter):
    pass

class StreamReader(Codec, codecs.StreamReader):
    pass

### encodings module API

def getregentry():

    return (Codec().encode, Codec().decode, StreamReader, StreamWriter)

### register codec

def sms_search_function(name):
    if name == 'sms-default':
        codec = Codec()
        return (codec.encode, codec.decode, StreamReader, StreamWriter)

codecs.register(sms_search_function)

from wader.common.sms.sms import (ShortMessageSubmit, MAX_LENGTH_7BIT,
                                MAX_LENGTH_UCS2, pdu_to_message, ShortMessage)
