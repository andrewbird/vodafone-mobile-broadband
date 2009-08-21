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
"""Bluetooth stuff"""

import dbus

if getattr(dbus, 'version', (0, 0, 0)) >= (0, 41, 0):
    # otherwise wont work
    import dbus.glib

def get_bluetooth_adapter():
    """Returns the default Bluetooth adapter"""
    bus = dbus.SystemBus()
    obj = bus.get_object('org.bluez', '/org/bluez')
    manager = dbus.Interface(obj,'org.bluez.Manager')
    obj = bus.get_object('org.bluez', manager.DefaultAdapter())
    return dbus.Interface(obj, 'org.bluez.Adapter')
