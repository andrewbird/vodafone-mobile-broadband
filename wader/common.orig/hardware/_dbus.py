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
"""dbus stuff"""

import dbus

if getattr(dbus, 'version', (0, 0, 0)) >= (0, 41, 0):
    # otherwise wont work
    import dbus.glib


class DbusComponent(object):
    """I provide a couple of useful methods to deal with DBus"""

    def __init__(self):
        self.bus = dbus.SystemBus()
        self.obj = self.bus.get_object('org.freedesktop.Hal',
                                  '/org/freedesktop/Hal/Manager')
        self.manager = dbus.Interface(self.obj, 'org.freedesktop.Hal.Manager')

    def get_properties_from_udi(self, udi):
        """Returns all the properties from C{udi}"""
        obj = self.bus.get_object('org.freedesktop.Hal', udi)
        dev = dbus.Interface(obj, 'org.freedesktop.Hal.Device')
        return dev.GetAllProperties()

    def get_devices_properties(self):
        """Returns all the properties from all devices registed in HAL"""
        props = {}
        for udi in self.manager.GetAllDevices():
            props[udi] = self.get_properties_from_udi(udi)

        return props

