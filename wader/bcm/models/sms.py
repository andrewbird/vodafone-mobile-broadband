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
"""Model for SMS-related controllers"""

import gtk
from gobject import TYPE_PYOBJECT, TYPE_STRING
#from gtkmvc import Model, ListStoreModel
from wader.bcm.contrib.gtkmvc import Model, ListStoreModel

from wader.bcm.images import MOBILE_IMG, COMPUTER_IMG
from wader.bcm.messages import is_sim_message


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
        self.device = None

    def add_messages(self, messages, contacts=None):
        """
        Adds a list of messages

        See L{add_message} docs
        """
        for sms in messages:
            self.add_message(sms, contacts)

    def _make_entry(self, message, contacts):
        if is_sim_message(message):
            entry = [MOBILE_IMG, message.text]
        else:
            entry = [COMPUTER_IMG, message.text]

        if contacts or contacts == []:
            # this is only used at startup received as the return value
            # of sconn.get_all_contacts(), an unmodified fresh copy of all
            # the contacts, we use it instead of doing a lookup for each
            # contact
            match = [contact.name for contact in contacts
                            if message.number == contact.get_number()]
            if match:
                entry.append(match[0])
            else:
                entry.append(message.number)

        else: # no contacts received
            entry.append(message.number)

        entry.append(message.datetime)
        entry.append(message)

        return entry

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

        entry = self._make_entry(message, contacts)
        self.append(entry)

    def update_message(self, _iter, message, contacts=None):
        """
        Updates the existing row specified by C{_iter} with the C{message}
        """

        entry = self._make_entry(message, contacts)
        for column in range(len(entry)):
            self.set_value(_iter, column, entry[column])


class NewSmsModel(Model):
    """
    Model for the send SMS controller
    """

    def __init__(self, device):
        super(NewSmsModel, self).__init__()

        self.device = device
