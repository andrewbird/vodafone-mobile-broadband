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

from zope.interface import implements
from os.path import join

from wader.common.consts import CTS_INTFACE

from wader.vmc.translate import _
from wader.vmc.consts import IMAGES_DIR
from wader.vmc.contacts.interface import IContact


class SIMContact(object):
    implements(IContact)

    def __init__(self, name, number, index=None, device=None):
        self.name = name
        self.number = number
        self.index = index
        self.device = device
        self.writable = True

    def __repr__(self):
        if self.index:
            args = (self.index, self.name, self.number)
            return '<SIMContact index="%d" name="%s" number="%s">' % args

        return '<SIMContact name="%s" number="%s">' % (self.name, self.number)

    __str__ = __repr__

    def __eq__(self, c):
        return self.name == c.name and self.number == c.number

    def __ne__(self, c):
        return not (self.name == c.name and self.number == c.number)

    def get_index(self):
        return self.index

    def get_name(self):
        return self.name

    def get_number(self):
        return self.number

    def is_writable(self):
        return self.writable

    def external_editor(self):
        return None

    def image_16x16(self):
        return join(IMAGES_DIR, 'mobile.png')

    def to_csv(self):
        """Returns a list with the name and number formatted for csv"""
        name = '"' + self.name + '"'
        number = '"' + self.number + '"'
        return [name, number]

    def set_name(self, name):
        ret = self._edit(name, self.number)
        if ret:
            self.name = name
        return ret

    def set_number(self, number):
        ret = self._edit(self.name, number)
        if ret:
            self.number = number
        return ret

    def _edit(self, name, number):
        if not self.device:
            return False

        index = self.device.Edit(self.index, name, number)
        if index <= 0:
            return False

        return True


class SIMContactsManager(object):
    """
    SIM Contacts manager
    """

    def device_reqd(self):
        return True

    def set_device(self, device):
        self.device = device

    def add_contact(self, contact):
        name = contact.get_name()
        number = contact.get_number()
        index = self.device.Add(name, number,
                                dbus_interface=CTS_INTFACE)
        if index > 0:
            return SIMContact(name, number, index, self.device)
        else:
            return None

    def delete_contact(self, contact):
        if not isinstance(contact, SIMContact):
            return False
        return self.delete_contact_by_id(contact.get_index())

    def delete_contact_by_id(self, index):
        self.device.Delete(index, dbus_interface=CTS_INTFACE)
        return True

    def find_contacts(self, pattern):
        for contact in self.get_contacts():
            # XXX: O(N) here!
            # I can't find a way to do a LIKE comparison
            if pattern.lower() in contact.get_name().lower():
                yield contact

    def get_contacts(self):
        ret = []
        clist = self.device.List(dbus_interface=CTS_INTFACE)
        for c in clist:
            (index, name, number) = c
            ret.append(SIMContact(name, number, index, self.device))

        return ret

    def get_contact_by_id(self, index):
        c = self.device.Get(index, dbus_interface=CTS_INTFACE)
        if c:
            (index, name, number) = c
            return SIMContact(name, number, index, self.device)
        else:
            return None

    def is_writable(self):
        return True

    def name(self):
        return _('Mobile')

