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
phonebook presents a uniform layer to deal with contacts from all sources
"""

from wader.vmc.contacts import supported_types
# just for now, we'll interrogate later
from wader.vmc.contacts.contact_sim import SIMContactsManager


def all_same_type(l):
    """Returns True if all items in C{l} are the same type"""
    type_0 = type(l[0])

    for item in l[1:]:
        if type(item) != type_0:
            return False
    return True


def all_contacts_writable(l):
    """Returns True if all contacts in C{l} are writable"""
    for contact in l:
        if not contact.is_writable():
            return False
    return True


class Contact(object):
    """
    Generic object capable only of being initialised and returning
    name and number
    """

    def __init__(self, name, number):
        self.name = unicode(name)
        self.number = unicode(number)

    def get_name(self):
        return self.name

    def get_number(self):
        return self.number


class PhoneBook(object):
    """
    I manage all your contacts

    PhoneBook presents a single interface to access contacts from
    all sources
    """

    def __init__(self, device=None):
        self.device = device

    def close(self):
        self.device = None

    def add_contact(self, contact, sim=False):
        if sim:
            manager = SIMContactsManager()
            manager.set_device(self.device)
            return manager.add_contact(contact)
        else:
            # XXX: Fix DB contacts handling
            raise RuntimeError("Cannot handle DB contacts right now")

    def add_contacts(self, contacts, sim=False):
        for contact in contacts:
            self.add_contact(contact, sim)

    def find_contact(self, name=None, number=None):
        ret = []

        if (not name and not number) or (name and number):
            return ret

        if name:
            for cclass, mclass in supported_types:
                manager = mclass()
                if manager.device_reqd():
                    manager.set_device(self.device)
                ret.extend(manager.find_contacts(name))

        elif number:
            # searching by name is pretty easy as the SIM allows to lookup
            # contacts by name. However searching by number is more difficult
            # as the SIM doesn't provides any facility for it. Thus we need
            # to get *all* contacts and iterate through them looking for
            # a number that matches the pattern
            ret = [c for c in self.get_contacts()
                         if c.get_number() == number]

        return ret

    def get_writable_types(self):
        ret = []
        for cclass, mclass in supported_types:
            manager = mclass()
            if manager.is_writable():
                ret.append(mclass)
        return ret

    def get_contacts(self):
        ret = []
        for cclass, mclass in supported_types:
            manager = mclass()
            if manager.device_reqd():
                manager.set_device(self.device)
            ret.extend(manager.get_contacts())
        return ret

    def delete_objs(self, objs):
        return self.delete_contacts(objs)

    def delete_contacts(self, clist):
        for contact in clist:
            self.delete_contact(contact)

    def delete_contact(self, contact):
        for cclass, mclass in supported_types:
            if isinstance(contact, cclass):
                manager = mclass()
                if manager.device_reqd():
                    manager.set_device(self.device)
                manager.delete_contact(contact)
                break

#    def edit_contact(self, contact):
#        if is_sim_contact(contact):
#            def add_contact_cb(index):
#                contact.index = index
#                return contact
#
#            d = self.sconn.add_contact(contact)
#            d.addCallback(add_contact_cb)
#            return d
#        else:
#            raise NotImplementedError()

_phonebook = PhoneBook()


def get_phonebook(device):
    _phonebook.device = device
    return _phonebook
