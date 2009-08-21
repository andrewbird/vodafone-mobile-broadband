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
The hardware module manages device discovery via dbus/hal on Unix/Linux
"""
__version__ = "$Rev: 1172 $"

from time import time

import serial
from twisted.internet import defer, reactor
from twisted.python import log

from vmc.contrib import louie
from wader.common.hardware._dbus import DbusComponent
from wader.common.hardware.base import identify_device, Customizer
from vmc.utils.utilities import extract_lsb_info, natsort
from wader.common import notifications


IDLE, BUSY = range(2)
ADD_THRESHOLD = 10.

def probe_port(port):
    """
    Returns C{True} if C{port} works, otherwise returns C{False}
    """
    try:
        ser = None
        ser = serial.Serial(port, timeout=1)
        ser.write('AT+CGMR\r\n')
        if not ser.readline():
            # Huawei E620 with driver option registers three serial
            # ports and the middle one wont raise any exception while
            # opening it even thou its a dummy port.
            return False

        return True
    except serial.SerialException:
        if ser is None:
            raise RuntimeError('Port %s not available: check permissions' % port)
        else:
            return False
    finally:
        if ser is not None:
            ser.close()

def probe_ports(ports):
    """
    Returns a tuple of (data port, control port) out of C{ports}
    """
    dport = cport = None
    while ports:
        port = ports.pop(0)
        if probe_port(port):
            if not dport:
                # data port tends to the be the first one
                dport = port
            elif not cport:
                # control port the next one
                cport = port
                break

    return dport, cport

def extract_info(props):
    info = {}
    if 'usb.vendor_id' in props:
        info['usb_device.vendor_id'] = props['usb.vendor_id']
        info['usb_device.product_id'] = props['usb.product_id']
    elif 'usb_device.vendor_id' in props:
        info['usb_device.vendor_id'] = props['usb_device.vendor_id']
        info['usb_device.product_id'] = props['usb_device.product_id']
    elif 'pcmcia.manf_id' in props:
        info['pcmcia.manf_id'] = props['pcmcia.manf_id']
        info['pcmcia.card_id'] = props['pcmcia.card_id']
    elif 'pci.vendor_id' in props:
        info['pci.vendor_id'] = props['pci.vendor_id']
        info['pci.product_id'] = props['pci.product_id']
    else:
        raise RuntimeError("Unknown bus for device %s" % props['info.udi'])

    return info


class HardwareRegistry(DbusComponent):
    """
    I find and configure devices on Linux

    I am resilient to ports assigned in unusual locations
    and devices sharing ids.
    """

    def __init__(self):
        super(HardwareRegistry, self).__init__()
        self.call_id = None
        self.os_info = extract_lsb_info()

        self.mode = IDLE
        self.get_devices_deferred = None
        self.devices = {}
        self.added_udis = []
        self.call_id = None

        self.connect_to_dbus_signals()
        # prepopulate device list
        d = self.get_devices()
        d.addCallback(self._register_devices, to_idle=True)

    def connect_to_dbus_signals(self):
        self.manager.connect_to_signal('DeviceAdded', self._dev_added_cb)
        self.manager.connect_to_signal('DeviceRemoved', self._dev_removed_cb)

    def get_devices(self):
        """
        Returns a list with all the devices present in the system

        List of deferreds of course
        """
        if self.mode == BUSY:
            # we are populating the initial device list and we've received
            # another request in the middle, will finish the current one
            # and will callback with the result in the _register_devices cb
            assert self.get_devices_deferred is None
            self.get_devices_deferred = defer.Deferred()
            return self.get_devices_deferred

        if self.mode == IDLE and self.devices:
            # we are IDLE and we've prepopulated our devices dict, return
            # the current values of the dict.
            return self.devices.values()

        # we are IDLE and self.devices is empty, lets populate it
        self.mode = BUSY
        parent_udis = self._get_parent_udis()
        d = self._get_devices_from_udis(parent_udis)
        d.addCallback(self._register_devices, to_idle=True)
        return d

    def _register_devices(self, devices, to_idle=False):
        for device in devices:
            udi = device.udi
            if device.udi not in self.devices:
                self.devices[udi] = device
                louie.send(notifications.SIG_DEVICE_ADDED, None, device)

        if to_idle:
            self.mode = IDLE

        if self.get_devices_deferred is not None:
            self.get_devices_deferred.callback(self.devices.values())
            self.get_devices_deferred = None

        return self.devices.values()

    def _get_device_from_udi(self, udi):
        """
        Returns a device built out of the info extracted from C{udi}
        """
        info = self._get_info_from_udi(udi)
        ports = self._get_ports_from_udi(udi)
        device = self._get_device_from_info_and_ports(info, udi, ports)
        return device

    def _get_devices_from_udis(self, udis):
        """
        Returns a list of devices built out of the info extracted from C{udis}
        """
        unknown_devs = map(self._get_device_from_udi, udis)
        deferreds = map(identify_device, unknown_devs)
        return defer.gatherResults(deferreds)

    def _same_pcmcia_slot(self, u1, u2):
        """
        Returns true if the devices are present on the same PCMCIA card
        """
        p1 = self.get_properties_from_udi(u1)
        if not 'pcmcia.socket_number' in p1:
            return False

        p2 = self.get_properties_from_udi(u2)
        if not 'pcmcia.socket_number' in p2:
            return False

        if not p1['pcmcia.socket_number'] == p2['pcmcia.socket_number']:
            return False

        if not 'info.parent' in p1:
            return False

        if not 'info.parent' in p2:
            return False

        if not p1['info.parent'] == p2['info.parent']:
            return False

        return True

    def _get_parent_udis(self):
        """
        Returns the root udi of all the devices with modem capabilities
        """

        devs = map(self._get_parent_udi,
                       self.manager.FindDeviceByCapability("modem"))

        # if device is pcmcia based, then separate device ports on a
        # multifunction device might be seen as distinct devices
        def is_unique(i, l):
            for j in l:
                if i == j:  # duplicate item
                    return False
                if self._same_pcmcia_slot(i, j):
                    return False
            return True

        def get_unique(old):
            new = []
            for udi in old:
                if is_unique(udi, new):
                    new.append(udi)
            return new

        return set(get_unique(devs))

    def _get_parent_udi(self, udi):
        """
        Returns the absolute parent udi of C{udi}
        """
        ORIG = 'serial.originating_device'
        def get_parent(props):
            if ORIG in props:
                return props[ORIG]
            return props['info.parent']

        current_udi = udi
        while True:
            props = self.get_properties_from_udi(current_udi)
            try:
                info = extract_info(props)
                break
            except RuntimeError:
                current_udi = get_parent(props)

        # now that we have an id to lookup for, lets repeat the process till we
        # get another RuntimeError
        def is_contained(_info, props):
            """
            Returns C{True} if C{_info} values are contained in C{props}

            As hal likes to swap between usb.vendor_id and usb_device.vendor_id
            I have got a special case where I will retry
            """
            def container_is_valid(d1, d2):
                for key in d1:
                    try:
                        if d1[key] == d2[key]:                       # Vendor_id match
                            if 'usb.device_class' in d2:
                                if d2['usb.device_class'] == 9:      # Hubs aren't valid containers
                                    return False
                            if 'usb_device.device_class' in d2:
                                if d2['usb_device.device_class'] == 9:
                                    return False
                            return True
                        else:
                            return False
                    except KeyError:
                        return False

            if container_is_valid(_info, props):
                # we got a straight map
                return True
            # hal likes to swap between usb_device.vendor_id and usb.vendor_id
            if 'usb_device.vendor_id' in _info:
                # our last chance, perhaps its swapped
                newinfo = {'usb.vendor_id' : _info['usb_device.vendor_id'],
                           'usb.product_id' : _info['usb_device.product_id']}
                return container_is_valid(newinfo, props)

            # the original container_is_valid failed, so return False
            return False

        last_udi = current_udi
        while True:
            props = self.get_properties_from_udi(current_udi)
            if not is_contained(info, props):
                break
            last_udi, current_udi = current_udi, get_parent(props)

        return last_udi

    def _get_info_from_udi(self, udi):
        return extract_info(self.get_properties_from_udi(udi))

    def _get_child_udis_from_udi(self, udi):
        """
        Returns the paths of C{udi} childs and the properties used
        """
        device_props = self.get_devices_properties()
        dev_udis = sorted(device_props.keys(), key=len)

        # Given the matched udi, we search through the device tree
        # for any pcmcia siblings. This is necessary for seemingly
        # unconnected serial ports that are part of a multifunction
        # device such as the Novatel U630
        udi_list=[udi]
        for i in dev_udis:
            if udi == i:
                continue
            if self._same_pcmcia_slot(udi,i):
                udi_list.append(i)

        # We now search all udis looking for any decendants of our
        # matched udi, or maybe its pcmcia sibling
        childs = []
        for cur_udi in udi_list:             # maybe pcmcia siblings
            for i in range(2):               # look for children & grandchilren
                dev_udis2 = dev_udis[:]
                while dev_udis2:
                    _udi = dev_udis2.pop()
                    if _udi != cur_udi and 'info.parent' in device_props[_udi]:
                        par_udi = device_props[_udi]['info.parent']

                        if par_udi == cur_udi or (par_udi in childs and
                                                    _udi not in childs):
                            childs.append(_udi)

        childs = list(set(childs)) # make unique 

        return childs, device_props

    def _get_ports_from_udi(self, udi):
        """
        Returns all the ports that C{udi} has registered
        """
        childs, dp = self._get_child_udis_from_udi(udi)
        if not childs:
            raise RuntimeError("Couldn't find any child of device %s" % udi)

        ports = map(str, [dp[_udi]['serial.device']
                        for _udi in childs if 'serial.device' in dp[_udi]])
        natsort(ports)
        return ports

    def _get_device_from_info_and_ports(self, info, udi, ports):
        """
        Returns a C{DevicePlugin} out of C{info} and C{dport} and {cport}
        """
        from wader.common.plugin import PluginManager
        plugin = PluginManager.get_plugin_by_vendor_product_id(*info.values())

        if plugin:
            # set its udi
            plugin.udi = udi

            if hasattr(plugin, 'preprobe_init'):
                # this plugin requires special initialisation before probing
                plugin.preprobe_init(ports, extract_info(info))

            if hasattr(plugin, 'hardcoded_ports'):
                # this plugin registers its ports in a funky way and thus
                # the probe algorithm wont work for it. hardcoded_ports is
                # a tuple of size two that contains the indexes of the ports
                # that should be used for dport and cport.
                dport_index, cport_index = plugin.hardcoded_ports
                dport = ports[dport_index]
                try:
                    if type(cport_index) == type(None):
                        cport = None
                    else:
                        cport = ports[cport_index]
                except Exception, e:
                    log.err()
                    cport = None
            else:
                # probe ports
                dport, cport = probe_ports(ports)

            if not dport and not cport:
                # this shouldn't happen
                raise RuntimeError("No data port and no control port")

            print "data port is %s" % dport
            if cport:
                print "ctrl port is %s" % cport

            plugin.cport, plugin.dport = cport, dport
            return plugin

        raise RuntimeError("Couldn't find a plugin with info %s" % info)

    def get_plugin_for_remote_dev(self, speed, dport, cport):
        from wader.common.plugin import UnknownDevicePlugin
        dev = UnknownDevicePlugin()
        dev.custom = Customizer()
        dev.dport, dev.cport, dev.baudrate = dport, cport, speed
        port = cport and cport or dport
        return identify_device(port)

    # hotplugging methods

    def _dev_added_cb(self, udi):
        self.mode = BUSY
        self.last_action = time()

        assert udi not in self.added_udis
        self.added_udis.append(udi)

        try:
            if not self.call_id:
                self.call_id = reactor.callLater(ADD_THRESHOLD,
                                             self._process_added_udis)
            else:
                self.call_id.reset(ADD_THRESHOLD)
        except:
            log.err()
            # call has already been fired
            self.added_udis = []
            self.call_id = None
            self.mode = IDLE

    def _dev_removed_cb(self, udi):
        if self.mode == BUSY:
            # we're in the middle of a hotpluggin event and the udis that
            # we just added to self.added_udis are disappearing!
            # whats going on? Some devices such as the Huawei E870 will
            # add some child udis, and will remove them once libusual kicks
            # in, so we need to wait for at most ADD_THRESHOLD seconds
            # since the last removal/add to find out what really got added
            if udi in self.added_udis:
                self.added_udis.remove(udi)
                return

        if udi in self.devices:
            louie.send(notifications.SIG_DEVICE_REMOVED, None)
            del self.devices[udi]

    def _process_added_udis(self):
        assert self.mode == BUSY
        # obtain the parent udis of all the devices with modem capabilities
        parent_udis = self._get_parent_udis()
        # we're only interested on devices not being handled and just added
        not_handled_udis = set(self.devices.keys()) ^ parent_udis
        just_added_udis = not_handled_udis & set(self.added_udis)
        # get devices out of UDIs and register them emitting DeviceAdded
        d = self._get_devices_from_udis(just_added_udis)
        d.addCallback(self._register_devices)

        # cleanup
        self.mode = IDLE
        self.added_udis = []
        try:
            self.call_id.cancel()
        except:
            pass

        self.call_id = None

hw_reg = HardwareRegistry()

