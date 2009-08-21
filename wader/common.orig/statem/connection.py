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
Connection state machine
"""

__version__ = "$Rev: 1172 $"

import datetime

from twisted.internet import defer
from twisted.python import log

from wader.common.statem.base import StateMachineMixin
import wader.common.exceptions as ex
from wader.common.persistent import usage_manager
from wader.common.notifications import (SIG_NEW_CONN_MODE, NO_SIGNAL,
                                      GPRS_SIGNAL, THREEG_SIGNALS,
                                      ConnectionNotification, SIG_CONNECTED,
                                      SIG_DISCONNECTED)

from vmc.contrib.epsilon.modal import Modal, mode
from vmc.contrib.epsilon.extime import Time


NO_TRACKING, TRACKING = range(2)

class ConnectionTracker(object):
    """
    I keep track of a connection for accounting purposes

    I detect connection changes and will add usage items whenever a new
    connection mode change happens
    """

    def __init__(self):
        super(ConnectionTracker, self).__init__()
        self.mode = NO_TRACKING
        self.conn_mode = None
        self.session_start = None
        self.start = None
        self.end = None
        self.start_recv = 0
        self.start_sent = 0

    def set_conn_mode(self, mode):
        if mode in '3G':
            self.conn_mode = THREEG_SIGNALS[0]
        else:
            self.conn_mode = GPRS_SIGNAL

    def connection_started(self):
        """
        Call it to start tracking the connection stats
        """
        if self.mode != NO_TRACKING:
            raise ex.AlreadyTracking()
        log.msg("ConnectionTracker started........")

        from wader.common.oal import osobj
        tzinfo = osobj.get_tzinfo()
        self.mode = TRACKING
        d = osobj.get_iface_stats()
        def get_iface_stats_cb(stats):
            self.start_recv, self.start_sent = stats
            self.start = Time.fromDatetime(datetime.datetime.now(tzinfo))
            self.session_start = self.start

        d.addCallback(get_iface_stats_cb)

    def add_current_usage(self, restart=True):
        """
        Adds the current usage statistics to the database
        """
        from wader.common.oal import osobj
        tzinfo = osobj.get_tzinfo()
        end = Time.fromDatetime(datetime.datetime.now(tzinfo))
        umts = self.conn_mode in THREEG_SIGNALS
        def get_iface_stats_cb(usage):
            # append usage item
            usage_manager.add_usage_item(umts, self.start, end, *usage)
            if restart:
                # reset start time
                self.start = end
                # reset usage stats
                self.start_recv = usage[0]
                self.start_sent = usage[1]

        d = osobj.get_iface_stats()
        d.addCallback(get_iface_stats_cb)

    def get_current_usage(self):
        from wader.common.oal import osobj

        if self.mode != TRACKING:
            raise ex.NotTrackingError()
        def get_iface_stats_cb(usage):
            recv = usage[0] - self.start_recv
            sent = usage[1] - self.start_sent
            return recv, sent

        d = osobj.get_iface_stats()
        d.addCallback(get_iface_stats_cb)
        return d

    def on_notification_received(self, notification):
        """
        ConnectStateMachine will notify us of SIG_NEW_CONN_MODE notifications
        """
        if self.mode == TRACKING:
            assert notification.args != NO_SIGNAL, "This shouldn't happen"

            if (self.conn_mode == GPRS_SIGNAL and
                    notification.args in THREEG_SIGNALS):
                # we were in GPRS and now in 3G
                self.add_current_usage(restart=True)
            elif (self.conn_mode in THREEG_SIGNALS and
                    notification.args == GPRS_SIGNAL):
                # we were in 3G and now in GPRS
                self.add_current_usage(restart=True)
            else:
                # No connection change? This a bug?
                # we're probably using a device that can't notify us conn
                # mode changes, we're receiving this notification because of
                # the daemon infrastructure, no change in connection, return
                return

            self.conn_mode = notification.args
        else:
            # we're not tracking, we'll record the last known connection mode
            # for accounting purposes
            self.conn_mode = notification.args


class ConnectStateMachine(StateMachineMixin, Modal):
    """
    I handle the connection
    """
    modeAttribute = 'mode'
    initialMode = 'disconnected'

    def __init__(self, dialer):
        self.dialer = dialer
        self.tracker = ConnectionTracker()
        self.listeners = []

    def __repr__(self):
        return self.__class__.__name__

    def add_listener(self, listener):
        self.listeners.append(listener)

    def on_notification_received(self, notification):
        if notification.type == SIG_NEW_CONN_MODE:
            # notify the tracker about a possible connection mode change
            self.tracker.on_notification_received(notification)

    def notify_listeners(self, notification):
        for listener in self.listeners:
            listener.on_notification_received(notification)

    def connect(self):
        """
        Returns a Deferred that will be callbacked when connected

        @raise wader.common.exceptions.AlreadyConnecting: raised when the
        state machine is already connecting
        @raise wader.common.exceptions.AlreadyConnected: raised when the
        state machine is already connected
        """
        # sanity check
        if self.mode == 'connecting':
            return defer.fail(ex.AlreadyConnecting())

        elif self.mode == 'connected':
            return defer.fail(ex.AlreadyConnected())

        # we are connecting now
        self.transitionTo('connecting')
        return self.do_next()

    def close(self, hotplug=False):
        """
        Returns a Deferred that will be callbacked when all resources are free

        @raise wader.common.exceptions.NotConnectedError: raised when we are
        not connected
        """
        if self.mode == 'disconnected':
            return defer.fail(ex.NotConnectedError())

        self.transitionTo('disconnected')
        return self.do_next(hotplug)

    # states
    class disconnected(mode):
        """
        I'm disconnected from Internet
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self, hotplug=False):
            self.tracker.add_current_usage(restart=False)
            self.tracker.mode = NO_TRACKING

            self.notify_listeners(ConnectionNotification(SIG_DISCONNECTED))
            if hotplug:
                return defer.succeed(True)

            return self.dialer.disconnect()

    class connecting(mode):
        """
        We're connecting to Internet now
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            def connect_cb(ignored):
                self.transitionTo('connected')
                self.do_next()

            d = self.dialer.connect()
            d.addCallback(connect_cb)
            return d

    class connected(mode):
        """
        We are connected to Internet now
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            # start tracker
            self.notify_listeners(ConnectionNotification(SIG_CONNECTED))
            self.tracker.connection_started()
