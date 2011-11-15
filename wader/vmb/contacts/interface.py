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

from zope.interface import Interface


class IContact(Interface):
    """
    Interface that all contact backends must implement
    """

    def get_index():
        """Returns the contact's index"""

    def get_name():
        """Returns the contact's name"""

    def get_number():
        """Returns the contact's number"""

    def is_writable():
        """Returns the contact's writable status"""

    def external_editor():
        """Returns a list of cmd + args to edit the external contact or Null"""

    def image_16x16():
        """Returns the pathname of the 16x16 icon to represent this contact"""

    def to_csv():
        """Returns a csv string with the contact info"""

    def set_name(self, name):
        """Sets the contact's name - return True if successful"""

    def set_number(self, number):
        """Sets the contact's number - return True if successful"""
