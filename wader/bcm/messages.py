# -*- coding: utf-8 -*-
# Copyright (C) 2006-2010  Vodafone España, S.A.
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

from os.path import exists

from wader.common.oal import get_os_object
from wader.common.consts import SMS_INTFACE
from wader.common.sms import Message as SMMessage
from wader.common.provider import Message as DBMessage
from wader.common.provider import (SmsProvider,
                                   inbox_folder, outbox_folder, drafts_folder)

from wader.bcm.consts import MESSAGES_DB
from wader.bcm.logger import logger

KNOWN_FOLDERS = [inbox_folder, drafts_folder, outbox_folder]


def is_sim_message(sms):
    """Returns True if C{sms} is a SIM sms"""
    return not isinstance(sms, DBMessage)


class DBSMSManager(object):
    """
    SMS manager for DB stored messages
    """

    def __init__(self, path=MESSAGES_DB):
        super(DBSMSManager, self).__init__()

        if not exists(path):
            self.provider = SmsProvider(path)
            for f in KNOWN_FOLDERS:
                self.provider.add_folder(f)
        else:
            self.provider = SmsProvider(path)

    def close(self):
        self.provider.close()

    def add_message(self, sms, where=None):
        if not where:
            folder = KNOWN_FOLDERS[0]
        else:
            folder = KNOWN_FOLDERS[where-1]

        msg = DBMessage(sms.number, sms.text, _datetime=sms.datetime)
        self.provider.add_sms(msg, folder=folder)
        return msg

    def add_messages(self, sms_list, where=None):
        return [self.add_message(sms, where) for sms in sms_list]

    def delete_message(self, sms):
        # we should delete the containing thread if it's empty
        self.provider.delete_sms(sms)

    def get_messages(self):
        ret = []
        for i in range(3):
            folder = KNOWN_FOLDERS[i]
            tab = i + 1
            for thread in self.provider.list_from_folder(folder):
                msgs = list(self.provider.list_from_thread(thread))
                for msg in msgs:
                    msg.where = tab
                ret.extend(msgs)
        return ret


class Messages(object):
    """
    I provide a uniform API to deal with all SMS in the system (SIM, DB, etc.)
    """

    def __init__(self, device=None):
        self.device = device
        self.smanager = DBSMSManager()

        self.tz = None
        try:
            self.tz = get_os_object().get_tzinfo()
        except:
            pass

    def close(self):
        self.smanager.close()
        self.device = None

    def add_messages(self, smslist, where=None):
        return self.smanager.add_messages(smslist, where)

    def add_message(self, sms, where=None):
        if where:
            # where is only set when is a DB SMS
            return self.smanager.add_message(sms, where)

    def get_messages(self):
        ret = []

        # from sim storage
        lst = self.device.List(dbus_interface=SMS_INTFACE)
        for dct in lst:
            sms = SMMessage.from_dict(dct, self.tz)
            ret.append(sms)

        # return messages in db storage too
        lst = self.smanager.get_messages()
        for msg in lst:
            msg.datetime = msg.datetime.astimezone(self.tz)
            ret.append(msg)

        return ret

    def get_messages_async(self, cb, eb):

        def _cb(slist):
            ret = []

            # from sim storage
            for dct in slist:
                sms = SMMessage.from_dict(dct, self.tz)
                ret.append(sms)

            # return messages in db storage too
            lst = self.smanager.get_messages()
            for msg in lst:
                msg.datetime = msg.datetime.astimezone(self.tz)
                ret.append(msg)

            cb(ret)

        self.device.List(dbus_interface=SMS_INTFACE,
                         reply_handler=_cb,
                         error_handler=eb)

    def get_message(self, index):
        dct = self.device.Get(index, dbus_interface=SMS_INTFACE)
        sms = SMMessage.from_dict(dct, self.tz)
        return sms

    def delete_messages(self, smslist):
        for sms in smslist:
            if is_sim_message(sms):
                self.device.Delete(sms.index, dbus_interface=SMS_INTFACE,
                                   reply_handler=lambda: True,
                                   error_handler=logger.error)
            else:
                self.smanager.delete_message(sms)

    def delete_objs(self, objs):
        return self.delete_messages(objs)


def get_messages_obj(device):
    _messages = Messages()
    _messages.device = device
    return _messages
