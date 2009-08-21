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
"""
Models for the initial configuration screens
"""
__version__ = "$Rev: 1172 $"

import gobject
import dbus
if getattr(dbus, 'version', (0, 0, 0)) >= (0, 41, 0):
    # otherwise wont work
    import dbus.glib

from twisted.internet import defer
from twisted.python import log

import wader.common.exceptions as ex
from wader.common.hardware.bt import get_bluetooth_adapter
from wader.vmc import ListStoreModel, Model

INTERFACE = 'org.bluez.Adapter'
SERVICE = 'org.bluez'
DEV = '/org/bluez/hci0'
SPORT = 'org.bluez.serial.Port'

class BluetoothDeviceStoreModel(ListStoreModel):
    """Store Model for Contacts treeviews"""
    def __init__(self):
        ListStoreModel.__init__(self, gobject.TYPE_STRING,
                                gobject.TYPE_STRING)

    def add_device(self, entry):
        self.append(entry)


class DeviceConfModel(Model):
    """Model used in the initial conf screens"""

    def __init__(self, device):
        Model.__init__(self)
        self.device = device

class NewProfileModel(Model):
    def __init__(self, device):
        super(NewProfileModel, self).__init__()
        self.device = device

    def get_device(self):
        return self.device

    def get_profiles_from_imsi_prefix(self):
        from wader.common.persistent import net_manager
        from wader.common.startup import attach_serial_protocol
        # we just need the IMSI, but the device is not setup yet. We'll setup
        # its sconn temporarily
        device = self.get_device()
        if not device.sconn:
            device = attach_serial_protocol(device)

        def get_imsi_eb(failure):
            failure.trap(ex.ATError,
                         ex.CMEErrorSIMPINRequired, ex.CMEErrorSIMFailure)
            # this card doesn't likes to be asked for its IMSI if its not
            # authenticated, we will just return None, as we don't have any
            # way to get the IMSI
            return failure

        d = device.sconn.get_imsi()
        d.addCallback(lambda imsi: net_manager.get_all_networks_by_id(imsi))
        d.addErrback(get_imsi_eb)

        return d


class BluetoothConfModel(Model):
    """Model used in the bluetooth conf screens"""

    def __init__(self):
        Model.__init__(self)
        self.adapter = get_bluetooth_adapter()
        self.queue = None

    def bonding_created_signal(self, address):
        log.msg('Signal: BondingCreated(%s)' % address)

    def bonding_removed_signal(self, address):
        log.msg('Signal: BondingRemoved(%s)' % address)

    def create_bonding(self, address):
        #self.adapter.RemoveBonding(address)
        if self.adapter.HasBonding(address):
            return defer.succeed(address)

        bus = dbus.SystemBus()
        for method, signal in [
                 (self.bonding_created_signal, 'BondingCreated'),
                 (self.bonding_removed_signal, 'BondingRemoved')]:
            bus.add_signal_receiver(method, signal, INTERFACE, SERVICE, DEV)

        deferred = defer.Deferred()

        def create_bonding_cb():
            print "CREATE BONDING CB"
            deferred.callback(address)

        def create_bonding_eb(response):
            print "CREATE BONDING EB", response
            deferred.errback(response)

        self.adapter.CreateBonding(address,
                                   reply_handler=create_bonding_cb,
                                   error_handler=create_bonding_eb)

        return deferred

    def get_sports(self, address):
        bus = dbus.SystemBus()
        obj = bus.get_object('org.bluez', '/org/bluez')
        bmgr = dbus.Interface(obj, 'org.bluez.Manager')
        try:
            bus_id = bmgr.ActivateService('serial')
            obj2 = bus.get_object(bus_id, '/org/bluez/serial')
            serial = dbus.Interface(obj2, 'org.bluez.serial.Manager')
        except dbus.exceptions.DBusException, e:
            log.err(e)
            return (None, None)

        def get_port(service_name):
            path = serial.CreatePort(address, service_name)
            return dbus.Interface(bus.get_object(bus_id, path), SPORT)

        dport = cport = None

        try:
            # all devices should implement dun
            dport = get_port('dun')
            cport = get_port('spp')
        except dbus.exceptions.DBusException, e:
            log.err(e)

        return (dport, cport)

    def _rem_dev_name_cb(self, address, name):
        log.msg('RemoteNameUpdated(%s, %s)' % (address, name))
        if address != self.adapter.GetAddress():
            self.queue.put([str(name), str(address)])

    def _disc_completed_cb(self):
        self.queue.put(None)

    def get_bluetooth_discv_queue(self):
        bus = dbus.SystemBus()

        items = [(self._rem_dev_name_cb, 'RemoteNameUpdated'),
                 (self._disc_completed_cb, 'DiscoveryCompleted')]

        for method, signal in items:
            bus.add_signal_receiver(method, signal, INTERFACE, SERVICE, DEV)

        self.queue = defer.DeferredQueue()
        self.adapter.DiscoverDevices()
        return self.queue


