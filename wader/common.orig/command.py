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
AT Commands related classes and help functions
"""
__version__ = "$Rev: 1172 $"

import re

from twisted.internet import defer

from wader.common.aterrors import ERROR_REGEXP

def get_cmd_dict_copy():
    """
    Returns a copy of the CMD_DICT dictionary

    Use this instead of importing it directly as you may forget to copy() it
    """
    return CMD_DICT.copy()

OK_REGEXP = re.compile('\r\nOK\r\n')

CMD_DICT = {

    'add_contact' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=None),

    'add_sms' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\+CMGW:\s(?P<id>\d+)\r\n')),

    'change_pin' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'check_pin' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                     \r\n
                     \+CPIN:\s
                     (?P<resp>
                        READY      |
                        SIM\sPIN2? |
                        SIM\sPUK2?
                     )
                     \r\n""", re.VERBOSE)),

    'delete_contact' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'delete_sms' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'disable_echo' :
            dict(echo=re.compile('ATE0\r'),
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'disable_pin' :
            dict(echo=None,
                 end=re.compile('\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'enable_pin' :
            dict(echo=None,
                 end=re.compile('\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'error_reporting' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'find_contacts' :
            dict(echo=None,
                 end=re.compile('(\r\n)*OK\r\n', re.DOTALL),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                     \r\n
                     \+CPBF:\s
                     (?P<id>\d+),
                     "(?P<number>\+?\d+)",
                     (?P<category>\d+),
                     \"(?P<name>.*)\"
                     """, re.VERBOSE)),

    'get_available_charset':
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('"(?P<lang>.*?)",?')),

    'get_contact_by_index' :
            dict(echo=None,
                 end=re.compile('\r\nOK\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                       \r\n
                       \+CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?\d+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)"
                       \r\n
                       """, re.VERBOSE)),

    'get_contacts' :
            dict(echo=None,
                 # one extra \r\n just in case
                 end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                       \r\n
                       \+CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?\d+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)"
                       """, re.VERBOSE)),

    'get_card_version' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(
                        '\r\n(\+GMR:)?(?P<version>.*)\r\n\r\nOK\r\n')),

    'get_card_model' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n(?P<model>.*)\r\n')),

    'get_charset':
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\+CSCS:\s"(?P<lang>.*)"\r\n')),

    'get_manufacturer_name':
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n(?P<name>.*)\r\n\r\nOK\r\n')),

    'get_imei' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile("\r\n(?P<imei>\d+)\r\n")),

    'get_imsi' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n(?P<imsi>\d+)\r\n')),

    'get_netreg_status' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                        \r\n
                        \+CREG:\s
                        (?P<mode>\d),(?P<status>\d+)
                        \r\n
                        """, re.VERBOSE)),

    'get_network_info' :
            dict(echo=None,
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
                          \r\n
                          """, re.VERBOSE)),

    'get_network_names' :
            dict(echo=None,
                 end=re.compile('\r\nOK\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \(
                    (?P<id>\d+),
                    "(?P<lname>[\s\w+]*)",
                    "(?P<sname>[\s\w+]*)",
                    "(?P<netid>\d+)",
                    (?P<type>\d)
                    \),?
                    """, re.VERBOSE)),

    'get_signal_level' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \r\n
                    \+CSQ:\s(?P<rssi>\d+),(?P<ber>\d+)
                    \r\n
                    """, re.VERBOSE)),

    'get_phonebook_size' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \r\n
                    \+CPBR:\s
                    \(\d\-(?P<size>\d+)\),\d+,\d+
                    \r\n
                    """, re.VERBOSE)),

    'get_pin_status' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\+CLCK:\s(?P<status>\d)\r\n')),

    'get_roaming_ids' :
            dict(echo=None,
                 end=re.compile('(\r\n)*\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \r\n
                    \+CPOL:\s(?P<index>\d+),(?P<type>\d),"(?P<netid>\d+)"
                    """, re.VERBOSE)),

    'get_sms' :
            dict(echo=None,
                 end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \r\n
                    \+CMGL:\s
                    (?P<id>\d+),
                    (?P<storedat>\d),,\d+
                    \r\n(?P<pdu>\w+)
                    """, re.VERBOSE)),

    'get_sms_by_index' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile(r"""
                    \r\n
                    \+CMGR:\s
                    (?P<storedat>\d),,
                    \d+\r\n
                    (?P<pdu>\w+)
                    \r\n""", re.VERBOSE)),

    'get_smsc' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\+CSCA:\s"(?P<smsc>.*)",\d+\r\n')),

    'register_with_network' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\nOK\r\n')),

    'reset_settings' :
            dict(echo=re.compile('ATZ\r'),
                 end=re.compile('.*?\r\nOK\r\n', re.DOTALL),
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'send_at' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('[\s\S]*\r\nOK\r\n', re.DOTALL)),

    'send_sms' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\r\n\+CMGS:\s(\d+)\r\n')),

    'send_pin' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n(OK)\r\n')),
    'send_puk' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=re.compile('\r\n\+CPIN:\s[(OK|SIM\sPIN)]\r\n')),

    'set_charset' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'set_netreg_notification' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'set_network_info_format' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'set_sms_indication' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'set_sms_format' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),

    'set_smsc' :
            dict(echo=None,
                 end=OK_REGEXP,
                 error=ERROR_REGEXP,
                 extract=OK_REGEXP),
}

class ATCmd(object):
    """I encapsulate all data related an AT command"""
    def __init__(self, cmd, name=None, eol='\r\n'):
        self.cmd = cmd
        if eol:
            self.cmd += eol

        self.name = name
        # Some commands like sending a sms require an special handling this
        # is because we have to wait till we receive a prompt like '\r\n> '
        # if splitcmd is set, the second part will be send 0.1 seconds later
        self.splitcmd = None
        # command's deferred
        self.deferred = defer.Deferred()
        self.timeout = 15  # default timeout
        self.callID = None # DelayedCall reference

    def __repr__(self):
        args = (self.name, self.cmd, self.timeout)
        return "<ATCmd name: %s raw: %r timeout: %d>" % args

