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
"""Model for main application"""
__version__ = "$Rev: 1183 $"

import os
import pickle
import datetime
from cStringIO import StringIO

from twisted.internet import defer, reactor
from twisted.python.modules import PythonPath

import wader.common.consts as consts
import wader.common.exceptions as ex
from wader.common.notifications import THREEG_SIGNALS

from wader.common.config import config
from wader.common.persistent import usage_manager
from wader.common.profiles import ProfileUpdater
from wader.common.encoding import _
from wader.vmc.models.base import BaseWrapperModel

class ApplicationModel(BaseWrapperModel):
    """Model for the main application"""

    def __init__(self, wrapper=None):
        super(ApplicationModel, self).__init__(wrapper)
        self.ctrl = None
        # reference to wader.common.daemon.DaemonCollection
        self.daemons = None
        # reference to wader.common.notification.NotificationsManager
        self.notimanager = None
        self.connsm = None
        # usage stuff
        self.session_stats = (0, 0)
        self.month_cache = {}
        self.origin_date = None
        self.clean_usage_cache()

    def is_connected(self):
        try:
            return self.wrapper.behaviour.current_sm.mode == 'connected'
        except:
            return False

    def is_connecting(self):
        if self.wrapper and self.wrapper.behaviour:
            return self.wrapper.behaviour.current_sm.mode == 'connecting'
        return False

    #----------------------------------------------#
    # CONNECTION/DISCONNECTION SERIAL/INTERNET     #
    #----------------------------------------------#

    def connect_internet(self):
        """Starts wvdial in case it wasn't already started"""
        assert self.wrapper.behaviour.current_sm != None

        if self.is_connecting():
            return defer.fail(ex.AlreadyConnecting())

        if self.is_connected():
            return defer.fail(ex.AlreadyConnected())

        self.connsm = self.wrapper.behaviour.current_sm

        # cleanup stale lock file just in case
        try:
            os.unlink(consts.VMC_DNS_LOCK)
        except (OSError, IOError):
            pass

        # get the connection type for the last time
        def connect_internet_eb(failure):
            """Need to handle the exception if get_network_info gets +COPS: 0"""
            return
        d = self.wrapper.device.sconn.get_network_info()
        d.addCallback(lambda netinfo:
                      self.connsm.tracker.set_conn_mode(netinfo[1]))
        d.addErrback(connect_internet_eb)

        # What if the device has just one serial port? We must stop whatever
        # daemons we've got running and lose the transport connection in
        # self.wrapper.device.sport

        if not self.wrapper.device.has_two_ports():
            self.daemons.stop_daemons()
            # close serial connection
            self.wrapper.device.sport.loseConnection("Connecting...")
            self.wrapper.device.sconn = None
            self.wrapper.device.sport = None

        # configure dialer
        self.connsm.dialer.configure_from_profile(config.current_profile,
                                                  self.wrapper.device)

        return self.connsm.connect()

    def disconnect_internet(self, hotplug=False):
        """Disconnects from the Internet and kills all related processes"""

        def disconnect_cb(usageitem):
            self.connsm = None

            if not self.wrapper.device.has_two_ports():
                # if the device has only one port, we need to reinit the
                # device and start again whatever daemons this device had
                # running
                def reinit_device():
                    self.wrapper.setup()
                    reactor.callLater(1, self.daemons.start_daemons)
                    # XXX: Register with the network again

                # give ten seconds to pppd to free resources
                reactor.callLater(10, reinit_device)

        d = self.connsm.close(hotplug)
        d.addCallback(disconnect_cb)
        return d

    #----------------------------------------------#
    # UPDATE PROFILES STUFF                        #
    #----------------------------------------------#

    def build_updater_mixin(self, name):
        pypath = PythonPath()
        try:
            mixin = pypath.moduleLoader(name)
        except AttributeError:
            return None

        ProfileUpdater.__bases__ += (mixin,)
        return ProfileUpdater()

    def _update_profile_cb(self, profile_data):
        if profile_data:
            buffer = StringIO(profile_data)
            try:
                try:
                    return pickle.load(buffer)
                except pickle.UnpicklingError:
                    raise
            finally:
                buffer.close()

        return None

    def check_profile_updates(self):
        updater = config.get('profile', 'updater')
        if not updater:
            return defer.succeed(None)

        updater_mixin = self.build_updater_mixin(updater)
        if not updater_mixin:
            return defer.succeed(None)

        d = updater_mixin.update_profile()
        d.addCallback(self._update_profile_cb)
        return d

    #----------------------------------------------#
    # USAGE STATS MODEL                            #
    #----------------------------------------------#

    # IMPORTANT: All the usage values are measured as bits, only the View
    # should represent it with other units.

    def clean_usage_cache(self):
        self.month_cache = {}
        self.origin_date = datetime.datetime.now()

    def _date_from_month_offset(self, offset):
        d = self.origin_date
        new_month = (d.month + offset) % 12 or 12
        new_year = d.year + (d.month + offset - 1) / 12
        try:
            ret = d.replace(month=new_month, year=new_year)
        except ValueError:
            #It's a last day greater than the last day of the new month
            next_month = d.replace(day=1, 
                                  month=(new_month + 1) % 12 or 12,
                                  year=new_year)
            ret = next_month - datetime.timedelta(days=1)
        return ret

    def _update_session_stats(self, stats):
        self.session_stats = stats

    def _get_usage_for_month(self, dateobj):
        key = (dateobj.year, dateobj.month)
        if not self.month_cache.has_key(key):
            # Current session information
            if self.is_connected() and self.origin_date.month == dateobj.month:
                tracker = self.connsm.tracker
                tracker.get_current_usage().addCallback(
                                                    self._update_session_stats)

                stats = self.session_stats
                umts = tracker.conn_mode in THREEG_SIGNALS
                transferred = stats[0] + stats[1]
                transferred_3g = umts and transferred or 0
                transferred_gprs = not umts and transferred or 0
            else:
                transferred_3g = 0
                transferred_gprs = 0

            # Historical usage data
            usage = usage_manager.get_usage_for_month(dateobj)
            for item in usage:
                if item.umts:
                    transferred_3g += item.bits_recv + item.bits_sent
                else:
                    transferred_gprs += item.bits_recv + item.bits_sent

            self.month_cache[key] = {
                'month': dateobj.strftime(_("%B, %Y")),
                'transferred_gprs': transferred_gprs,
                'transferred_3g': transferred_3g,
                'transferred_total': transferred_gprs + transferred_3g
            }
        return self.month_cache[key]

    def get_month(self, offset):
        date = self._date_from_month_offset(offset)
        return self._get_usage_for_month(date)['month']

    def get_transferred_3g(self, offset):
        date = self._date_from_month_offset(offset)
        return self._get_usage_for_month(date)['transferred_3g']

    def get_transferred_gprs(self, offset):
        date = self._date_from_month_offset(offset)
        return self._get_usage_for_month(date)['transferred_gprs']

    def get_transferred_total(self, offset):
        date = self._date_from_month_offset(offset)
        return self._get_usage_for_month(date)['transferred_total']

    def get_session_3g(self):
        if not self.is_connected():
            return 0
        tracker = self.connsm.tracker
        umts = tracker.conn_mode in THREEG_SIGNALS
        total = self.session_stats[0] + self.session_stats[1]
        return umts and total or 0

    def get_session_gprs(self):
        if not self.is_connected():
            return 0
        tracker = self.connsm.tracker
        umts = tracker.conn_mode in THREEG_SIGNALS
        total = self.session_stats[0] + self.session_stats[1]
        return not umts and total or 0

    def get_session_total(self):
        return self.get_session_3g() + self.get_session_gprs()

