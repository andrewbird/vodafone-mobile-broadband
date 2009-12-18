# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
# Author:  Andrew Bird
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

from wader.vmc.translate import _
from wader.vmc.consts import IMAGES_DIR
from wader.vmc.contacts.interface import IContact


class EVContact(object):
    """
    I represent a contact in Evolution
    """
    implements(IContact)
    typeName = 'EVContact'

    def __init__(self, name, number, index=None):
        self.name = name
        self.number = number
        self.index = index
        self.writable = False

    def __repr__(self):
        return '<EVContact name="%s" number="%s">' % (self.name, self.number)

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
        return ['evolution', '-c', 'contacts']

    def image_16x16(self):
        return join(IMAGES_DIR, 'evolution.png')

    def to_csv(self):
        """Returns a list with the name and number formatted for csv"""
        name = '"' + self.name + '"'
        number = '"' + self.number + '"'
        return [name, number]

    def set_name(self, name):
        return False

    def set_number(self, number):
        return False


class EVContactsManager(object):
    """
    Contacts manager
    """

    def device_reqd(self):
        return False

    def set_device(self, device):
        pass

    def delete_contact(self, contact):
        return False

    def delete_contact_by_id(self, index):
        return False

    def find_contacts(self, pattern):
        for contact in self.get_contacts():
            # XXX: O(N) here!
            # I can't find a way to do a LIKE comparison
            if (pattern.lower() in contact.get_name().lower()) and contact.get_number():
                yield contact

    def get_contacts(self):
        try:
            import evolution
        except:
            return []

        addressbooks = evolution.ebook.list_addressbooks()
        if not addressbooks:
            return []

        ret = []
        for i in addressbooks:
            name, id = i # ('Personal', 'default')

            addressbook = evolution.ebook.open_addressbook(id)
            if not addressbook:
                continue

            for c in addressbook.get_all_contacts():

                item = EVContact(name=c.get_name(),
                                 number=c.get_property('mobile-phone'),
                                 index=c.get_property('id'))

                # Ubuntu one mirrors personal address books, so avoid
                # duplicate entry - might be slow with many contacts
                if not item in ret:
                    ret.append(item)

        return ret

    def get_contact_by_id(self, index):
        print "EVContactsManager::get_contact_by_id called"
        return None

    def is_writable(self):
        return False

    def name(self):
        return _('Evolution')
