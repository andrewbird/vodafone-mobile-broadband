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
Daemons for VMC
"""

__version__ = "$Rev: 1172 $"

from twisted.internet.task import LoopingCall
from twisted.python import log

from wader.common.netspeed import bps_to_human, NetworkSpeed
import wader.common.exceptions as ex
import wader.common.notifications as N

class VMCDaemon(object):
    """
    I represent a Daemon in VMC

    A Daemon is an entity that performs a repetitive action, like polling
    signal quality from the datacard. A Daemon will notify the notification
    manager with fake notifications built out of the action's response.
    """
    def __init__(self, frequency, device, notification_manager):
        super(VMCDaemon, self).__init__()
        self.frequency = frequency
        self.device = device
        self.loop = None
        self.manager = notification_manager

    def start(self):
        """Starts the Daemon"""
        log.msg("DAEMONS: DAEMON %s started..." % self.__class__.__name__)
        if not self.loop or not self.loop.running:
            self.loop = LoopingCall(self.function)
            self.loop.start(self.frequency)

            args = (self.function, self.frequency)
            log.msg("DAEMONS: executing %s every %d seconds" % args)

    def stop(self):
        """Stops the Daemon"""
        if self.loop.running:
            cname = self.__class__.__name__
            log.msg("DAEMONS: DAEMON %s stopped..." % cname)
            self.loop.stop()

    def function(self):
        """Function that will be called periodically"""
        raise NotImplementedError()


class SignalQualityDaemon(VMCDaemon):
    """
    I enque fake SIG_RSSI UnsolicitedNotifications
    """
    def function(self):
        def get_signal_level_cb(rssi):
            noti = N.UnsolicitedNotification(N.SIG_RSSI, rssi)
            self.manager.on_notification_received(noti)

        self.device.sconn.get_signal_level().addCallback(get_signal_level_cb)


class CellTypeDaemon(VMCDaemon):
    """
    I enque fake SIG_NEW_CONN_MODE UnsolicitedNotifications
    """
    def function(self):

        def get_network_name_cb(netinfo): # Network name
            noti = N.UnsolicitedNotification(N.SIG_NEW_NETWORK, netinfo[0])
            self.manager.on_notification_received(noti)
            return netinfo

        def get_network_bear_cb(netinfo): # Bearer
            if netinfo[1] in 'GPRS':
                sig = N.GPRS_SIGNAL
            else:
                sig = N.UMTS_SIGNAL
            noti = N.UnsolicitedNotification(N.SIG_NEW_CONN_MODE, sig)
            self.manager.on_notification_received(noti)

        def get_network_info_eb(failure):
            failure.trap(ex.NetworkTemporalyUnavailableError)
            log.err(failure, "CellTypeDaemon: FAILURE RECEIVED")

        d = self.device.sconn.get_network_info()
        d.addCallback(get_network_name_cb)
        d.addCallback(get_network_bear_cb)
        d.addErrback(get_network_info_eb)


class NetworkSpeedDaemon(VMCDaemon):
    """
    I enque fake SIG_SPEED UnsolicitedNotifications
    """
    def __init__(self, frequency, device, notification_manager):
        super(NetworkSpeedDaemon, self).__init__(frequency, device,
                                                  notification_manager)
        self.netspeed = NetworkSpeed()

    def start(self):
        log.msg("DAEMONS: DAEMON %s started..." % self.__class__.__name__)
        self.netspeed.start()
        self.loop = LoopingCall(self.function)
        self.loop.start(self.frequency)

    def stop(self):
        log.msg("DAEMONS: DAEMON %s stopped..." % self.__class__.__name__)

        self.loop.stop()
        self.netspeed.stop()

    def function(self):
        up, down = self.netspeed['up'], self.netspeed['down']
        n = N.UnsolicitedNotification(N.SIG_SPEED, bps_to_human(up, down))
        self.manager.on_notification_received(n)


class VMCDaemonCollection(object):
    """
    I am a collection of Daemons

    I provide some methods to manage the collection.
    """
    def __init__(self):
        self.daemons = {}

    def append_daemon(self, name, daemon):
        """Adds C{daemon} to the collection with C{name}"""
        self.daemons[name] = daemon

    def has_daemon(self, name):
        """Returns True if C{name} exists"""
        return name in self.daemons

    def remove_daemon(self, name):
        """Removes daemon with C{name}"""
        try:
            del self.daemons[name]
        except KeyError:
            raise 

    def start_daemon(self, name):
        """Starts daemon with C{name}"""
        try:
            self.daemons[name].start()
        except KeyError:
            raise

    def start_daemons(self):
        """Starts all daemons"""
        for daemon in self.daemons.values():
            daemon.start()

    def stop_daemon(self, name):
        """Stops daemon with C{name}"""
        try:
            self.daemons[name].stop()
        except KeyError:
            raise

    def stop_daemons(self):
        """Stops all daemons"""
        for daemon in self.daemons.values():
            daemon.stop()


class VMCDaemonFactory(object):
    """Daemon Factory for VMC"""

    @classmethod
    def build_daemon_collection(cls, device, notification_manager):
        """
        Returns a C{VMCServiceCollection} customized for C{device}
        """
        col = VMCDaemonCollection()

        if device.has_two_ports():
            # check capabilities
            if N.SIG_RSSI in device.custom.device_capabilities:
                # the device says that can report RSSI changes, nonetheless
                # we will poll every minute the signal
                freq = 60
            else:
                # device doesn't sends unsolicited notifications about RSSI
                # changes, we will have to monitor it ourselves every 15s
                freq = 15

            daemon = SignalQualityDaemon(freq, device, notification_manager)
            col.append_daemon('signal', daemon)

            if N.SIG_NEW_CONN_MODE in device.custom.device_capabilities:
                # the device says that it can report bearer change, nonetheless
                # we will poll every 4 minutes
                freq = 240
            else:
                # device doesn't send unsolicited notifications about bearer
                # changes, we will have to monitor it ourselves every minute
                freq = 60

            daemon = CellTypeDaemon(freq, device, notification_manager)
            col.append_daemon('conn_mode', daemon)

        else:
            # device with just one port
            daemon = SignalQualityDaemon(15, device, notification_manager)
            col.append_daemon('signal', daemon)

            daemon = CellTypeDaemon(60, device, notification_manager)
            col.append_daemon('conn_mode', daemon)

        return col


