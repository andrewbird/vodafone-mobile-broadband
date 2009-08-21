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
"""Model for SMS-related controllers"""

__version__ = "$Rev: 1189 $"

import gtk
from gobject import TYPE_PYOBJECT, TYPE_STRING

from wader.common.oal import osobj
from wader.common.notifications import SIG_DEVICE_REMOVED
from wader.common.phonebook import get_phonebook
from wader.common.persistent import DBShortMessage
from wader.vmc import ListStoreModel
from wader.vmc.images import MOBILE_IMG, COMPUTER_IMG
from vmc.contrib import louie

class SMSStoreModel(ListStoreModel):
    """
    SMS ListStoreModel with some convenience methods

    Accepts a callable because as we live in a hotplugging world we need a
    way to obtain a reference to the new plugged device.
    """
    def __init__(self, _callable):
        super(SMSStoreModel, self).__init__(gtk.gdk.Pixbuf,
            TYPE_STRING, TYPE_STRING, TYPE_PYOBJECT, TYPE_PYOBJECT)
        self._callable = _callable
        self.sconn = None
        louie.connect(self.device_removed_handler, SIG_DEVICE_REMOVED)

    def device_removed_handler(self):
        """
        I take care of {self.sconn} and will update it as necessary
        """
        self.sconn = None

    def add_messages(self, messages, contacts=None):
        """
        Adds a list of messages

        See L{add_message} docs
        """
        for sms in messages:
            self.add_message(sms, contacts)

    def _add_sim_message(self, message, contacts=None):
        entry = [MOBILE_IMG, message.get_text()]
        if contacts or contacts == []:
            # this is only used at startup received as the return value
            # of sconn.get_all_contacts(), an unmodified fresh copy of all
            # the contacts, we use it instead of doing a lookup for each
            # contact
            match = [contact.name for contact in contacts
                            if message.get_number() == contact.get_number()]
            if match:
                entry.append(match[0])
            else:
                entry.append(message.get_number())

            entry.append(message.datetime)
            entry.append(message)
            self.append(entry)

        else: # no contacts received
            phonebook = get_phonebook(self.sconn)
            def lookup_number_cb(clist):
                """
                Add the contact to the model

                If the SMS's number exists in the phonebook, display the
                contact's name instead of the number
                """
                if clist:
                    entry.append(clist[0].name)
                else:
                    entry.append(message.get_number())

                entry.append(message.datetime)
                entry.append(message)
                self.append(entry)

            d = phonebook.find_contact(number=message.get_number())
            d.addCallback(lookup_number_cb)


    def _add_db_message(self, message, contacts=None):
        tzinfo = osobj.get_tzinfo()
        entry = [COMPUTER_IMG, message.get_text()]
        if contacts or contacts == []:
            # this is only used at startup received as the return value
            # of sconn.get_all_contacts(), an unmodified fresh copy of all
            # the contacts, we use it instead of doing a lookup for each
            # contact
            match = [contact.name for contact in contacts
                            if message.get_number() == contact.get_number()]
            if match:
                entry.append(match[0])
            else:
                entry.append(message.get_number())

            entry.append(message.date.asDatetime(tzinfo=tzinfo))
            entry.append(message)
            self.append(entry)
        else:
            phonebook = get_phonebook(self.sconn)
            def lookup_number_cb(clist):
                """
                Add the contact to the model

                If the SMS's number exists in the phonebook, display the
                contact's name instead of the number
                """
                if clist:
                    entry.append(clist[0].name)
                else:
                    entry.append(message.get_number())

                entry.append(message.date.asDatetime(tzinfo=tzinfo))
                entry.append(message)
                self.append(entry)

            d = phonebook.find_contact(number=message.get_number())
            d.addCallback(lookup_number_cb)

    def add_message(self, message, contacts=None):
        """
        Adds C{message} to the ListStoreModel

        Whenever a new message is inserted, I lookup the number on the
        phonebook and will show the name instead of the number if its a
        contact. As this can be really expensive for mass insertions, such as
        during startup, it also accepts a list of contacts to save the lookup.

        @type message: L{wader.common.sms.ShortMessage}
        @type contacts: list
        """
        if not self.sconn:
            self.sconn = self._callable()

        if isinstance(message, DBShortMessage):
            self._add_db_message(message, contacts)
        else:
            self._add_sim_message(message, contacts)

