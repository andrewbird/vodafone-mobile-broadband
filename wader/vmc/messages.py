# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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
messages presents a uniform layer to deal with messages from both SIM and DB
"""

#from twisted.internet import defer

#from wader.vmc.persistent import SMSManager, DBShortMessage
from wader.common.oal import osobj
from wader.common.consts import SMS_INTFACE
from wader.common.sms import Message

def is_sim_message(sms):
    """Returns True if C{sms} is a SIM sms"""
#    return not isinstance(sms, DBShortMessage)
    return True

class Messages(object):
    """
    I provide a uniform API to deal with all SMS in the system (SIM, DB, etc.)
    """
    def __init__(self, device=None):
        self.device = device
#        self.smanager = SMSManager()

        self.tz = None
        try:
            self.tz = osobj.get_tzinfo()
        except:
            pass

    def close(self):
#        self.smanager.close()
        self.device = None

#    def add_messages(self, smslist, where=None):
#        if where:
#            # where is only set when we store a draft or when a copy of
#            # a sms is kept on the sent treeview
#            return self.smanager.add_messages(smslist, where)
#
#        responses = [self.add_message(sms) for sms in smslist]
#        return defer.gatherResults(responses)

#    def add_message(self, sms, where=None):
#        if where:
#            # where is only set when is a DB SMS
#            return defer.maybeDeferred(self.smanager.add_message, sms, where)
#
#        if is_sim_message(sms):
#            raise NotImplementedError()

    def get_messages(self):
        lst = self.device.List(dbus_interface=SMS_INTFACE)
        ret = []
        for dct in lst:
            sms = Message.from_dict(dct, self.tz)
            ret.append(sms)

        # should return messages in db storage too
        return ret

    def get_message(self, index):
        dct = self.device.Get(index, dbus_interface=SMS_INTFACE)
        sms = Message.from_dict(dct, self.tz)
        return sms

    def delete_messages(self, smslist):
        for sms in smslist:
            if is_sim_message(sms):
                self.device.Delete(sms.index, dbus_interface=SMS_INTFACE)

    def delete_objs(self, objs):
        return self.delete_messages(objs)

_messages = Messages()

def get_messages_obj(device):
    _messages.device = device
    return _messages

