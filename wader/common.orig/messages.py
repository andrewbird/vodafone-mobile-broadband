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
messages presents a uniform layer to deal with messages from both SIM and DB
"""

__version__ = "$Rev: 1172 $"

from twisted.internet import defer

from wader.common.persistent import SMSManager, DBShortMessage

def is_sim_message(sms):
    """Returns True if C{sms} is a SIM sms"""
    return not isinstance(sms, DBShortMessage)

class Messages(object):
    """
    I provide a uniform API to deal with all SMS in the system (SIM, DB, etc.)
    """
    def __init__(self, sconn=None):
        self.sconn = sconn
        self.smanager = SMSManager()

    def close(self):
        self.smanager.close()
        self.sconn = None

    def add_messages(self, smslist, where=None):
        if where:
            # where is only set when we store a draft or when a copy of
            # a sms is kept on the sent treeview
            return self.smanager.add_messages(smslist, where)

        responses = [self.add_message(sms) for sms in smslist]
        return defer.gatherResults(responses)

    def add_message(self, sms, where=None):
        if where:
            # where is only set when is a DB SMS
            return defer.maybeDeferred(self.smanager.add_message, sms, where)

        if is_sim_message(sms):
            raise NotImplementedError()

    def get_messages(self):
        d = self.sconn.get_sms()
        d.addCallback(lambda sim_sms: self.smanager.get_messages() + sim_sms)
        return d

    def get_message(self, sms):
        if is_sim_message(sms):
            return self.sconn.get_sms_by_index(sms.index)
        else:
            raise NotImplementedError()

    def delete_messages(self, smslist):
        resp = []
        for sms in smslist:
            if is_sim_message(sms):
                resp.append(self.sconn.delete_sms(sms.get_index()))
            else:
                d = defer.maybeDeferred(self.smanager.delete_message_by_id,
                                        sms.get_index())
                resp.append(d)

        return defer.gatherResults(resp)

    def delete_objs(self, objs):
        return self.delete_messages(objs)

_messages = Messages()

def get_messages_obj(sconn):
    _messages.sconn = sconn
    return _messages

