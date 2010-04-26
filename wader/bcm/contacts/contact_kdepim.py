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

from wader.bcm.translate import _
from wader.bcm.consts import IMAGES_DIR
from wader.bcm.contacts.interface import IContact


class KDEContact(object):
    """
    I represent a contact in KDE
    """
    implements(IContact)

    def __init__(self, name, number, index=None):
        self.name = name
        self.number = number
        self.index = index
        self.writable = False

    def __repr__(self):
        return '<KDEContact name="%s" number="%s">' % (self.name, self.number)

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
        return ['kaddressbook', ]

    def image_16x16(self):
        return join(IMAGES_DIR, 'kdepim.png')

    def to_csv(self):
        """Returns a list with the name and number formatted for csv"""
        name = '"' + self.name + '"'
        number = '"' + self.number + '"'
        return [name, number]

    def set_name(self, name):
        return False

    def set_number(self, number):
        return False


class KDEContactsManager(object):
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

    def get_contacts(self):
        from os.path import expanduser

        # XXX: maybe we should try to read a system version of the
        #      vcard library provided with pycocuma
        from wader.bcm.contrib.pycocuma.vcard import vCardList

        vl = vCardList()

        ret = []
        if vl.LoadFromFile(expanduser('~') + '/.kde/share/apps/kabc/std.vcf'):
            for vc in vl.data.keys():

                fn = vl.data[vc].fn.get()

                if len(fn):
                    tel = vl.data[vc].tel
                    cell = ''
                    for num in tel:
                        if 'CELL' in num.params.get('type'):
                            cell = num.value.get()
                            break

                    email = vl.data[vc].email
                    if len(cell) or len(email):  # try to exclude distribution lists etc
                        ret.append(KDEContact(name=fn, number=cell))
        return ret

    def get_contact_by_id(self, index):
        print "KDEContactsManager::get_contact_by_id called"
        return None

    def is_writable(self):
        return False

    def name(self):
        return _('KDE PIM')
