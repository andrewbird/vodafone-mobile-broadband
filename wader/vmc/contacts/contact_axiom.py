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
from os.path import join, expanduser

from wader.vmc.consts import IMAGES_DIR
from wader.vmc.contacts.interface import IContact
from wader.vmc.contrib.axiom import item, attributes, store
from wader.vmc.contrib.axiom.attributes import AND

CONTACTS_DB = join(expanduser('~'),'.vmc2','contacts.db')


class ADBContact(item.Item):
    """
    I represent a contact on the Axiom DB
    """
    implements(IContact)
    # (id integer, category integer, name text, number text)
    typeName = 'DBContact'
    schemaVersion = 1

    name = attributes.text(allowNone=False)
    number = attributes.text(allowNone=False)
    writable = True

    def __repr__(self):
        return '<ADBContact name="%s" number="%s">' % (self.name, self.number)

    def __eq__(self, c):
        return self.name == c.name and self.number == c.number

    def __ne__(self, c):
        return not (self.name == c.name and self.number == c.number)

    def get_index(self):
        return self.storeID

    def get_name(self):
        return self.name

    def get_number(self):
        return self.number

    def is_writable(self):
        return self.writable

    def external_editor(self):
        return None

    def image_16x16(self):
        return join(IMAGES_DIR, 'computer.png')

    def to_csv(self):
        """Returns a list with the name and number formatted for csv"""
        name = '"' + self.name + '"'
        number = '"' + self.number + '"'
        return [name, number]

    def set_name(self, name):
        self.name = name     # XXX: how do we detect a failure to write to the DB?
        return True

    def set_number(self, number):
        self.number = number # XXX: how do we detect a failure to write to the DB?
        return True


class ADBContactsManager(object):
    """
    Axiom Contacts manager
    """
    def __init__(self, path=CONTACTS_DB):
        super(ADBContactsManager, self).__init__(path)
        self.store = store.Store(path)

    def device_reqd(self):
        return False

    def set_device(self, device):
        pass

    def add_contact(self, contact):
        return ADBContact(store=self.store, name=contact.get_name(),
                        number=contact.get_number())

    def delete_contact(self, contact):
        if not isinstance(contact, ADBContact):
            return False
        return self.store.query(ADBContact,
                                ADBContact == contact).deleteFromStore()

    def delete_contact_by_id(self, index):
        return self.store.getItemByID(index).deleteFromStore()

    def find_contacts(self, pattern):
        for contact in self.get_contacts():
            # XXX: O(N) here!
            # I can't find a way to do a LIKE comparison
            if pattern.lower() in contact.get_name().lower():
                yield contact

    def get_contacts(self):
        return list(self.store.query(ADBContact))

    def get_contact_by_id(self, index):
        return self.store.getItemByID(index)

    def close(self):
        self.store.close()
        self.store = None

