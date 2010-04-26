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
"""Contacts-related models"""

import gtk

#from gtkmvc import ListStoreModel
from wader.bcm.contrib.gtkmvc import ListStoreModel
from gobject import TYPE_STRING, TYPE_PYOBJECT, TYPE_BOOLEAN


class ContactsStoreModel(ListStoreModel):
    """Store Model for Contacts treeviews"""

    def __init__(self):
        super(ContactsStoreModel, self).__init__(gtk.gdk.Pixbuf,
                TYPE_STRING, TYPE_STRING, TYPE_PYOBJECT, TYPE_BOOLEAN)

    def add_contacts(self, contacts):
        """Adds C{contacts} to the store"""
        for contact in contacts:
            self.add_contact(contact)

    def add_contact(self, contact):
        """Adds C{contact} to the store"""
        img = gtk.gdk.pixbuf_new_from_file(contact.image_16x16())
        self.append([img, contact.name, contact.number, contact,
                     contact.writable])

    def find_contacts_by_number(self, number):
        ret = []
        _iter = self.get_iter_first()
        while _iter:
            _number = self.get_value(_iter, 2)
            if _number == number:
                ret.append(self.get_value(_iter, 3))

            _iter = self.iter_next(_iter)

        return ret

    def find_contacts(self, pattern):
        ret = []
        _iter = self.get_iter_first()
        while _iter:
            _name = self.get_value(_iter, 1)
            _number = self.get_value(_iter, 2)

            if (pattern.lower() in _name.lower()) and _number:
                ret.append(self.get_value(_iter, 3))

            _iter = self.iter_next(_iter)

        return ret

    def get_contacts(self):
        ret = []
        _iter = self.get_iter_first()
        while _iter:
            ret.append(self.get_value(_iter, 3))

            _iter = self.iter_next(_iter)

        return ret
