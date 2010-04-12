# -*- coding: utf-8 -*-
# Copyright (C) 2008 Warp Networks S.L.
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

import datetime

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

import gobject
#from gtkmvc import Model
from wader.vmc.contrib.gtkmvc import Model

from wader.vmc.logger import logger
from wader.vmc.dialogs import show_error_dialog
from wader.vmc.models.profile import ProfilesModel
from wader.vmc.models.preferences import PreferencesModel
from wader.vmc.translate import _
from wader.vmc.utils import dbus_error_is, get_error_msg
from wader.vmc.signals import NET_MODE_SIGNALS
from wader.vmc.consts import USAGE_DB
from wader.vmc.config import config
from wader.common.consts import (WADER_SERVICE, WADER_OBJPATH, WADER_INTFACE,
                                 WADER_DIALUP_SERVICE, WADER_DIALUP_OBJECT,
                                 CRD_INTFACE, NET_INTFACE, MDM_INTFACE,
                                 WADER_DIALUP_INTFACE, WADER_KEYRING_INTFACE,
                                 MM_NETWORK_MODE_GPRS, MM_NETWORK_MODE_EDGE,
                                 MM_NETWORK_MODE_2G_ONLY)
import wader.common.aterrors as E
import wader.common.signals as S
from wader.common.provider import UsageProvider


TWOG_SIGNALS = [MM_NETWORK_MODE_GPRS, MM_NETWORK_MODE_EDGE,
                MM_NETWORK_MODE_2G_ONLY]


UPDATE_INTERVAL = CONFIG_INTERVAL = 2 * 1000 # 2ms
NETREG_INTERVAL = 5 * 1000 # 5ms

AUTH_TIMEOUT = 150        # 2.5m
ENABLE_TIMEOUT = 2 * 60   # 2m
REGISTER_TIMEOUT = 3 * 60 # 3m

ONE_MB = 2**20


class MainModel(Model):

    __properties__ = {
        'rssi': 0,
        'profile': None,
        'device': None,
        'device_opath': None,
        'dial_path': None,
        'connected': False,
        'operator': _('Unknown'),
        'status': _('Not registered'),
        'tech': _('Unknown'),
        'pin_required': False,
        'puk_required': False,
        'puk2_required': False,
        'profile_required': False,
        'sim_error': False,
        'net_error': '',
        'key_needed': False,
        # usage properties
        'threeg_transferred': 0,
        'twog_transferred': 0,
        'threeg_session': 0,
        'twog_session': 0,
        'total_session': 0,
        'total_transferred': 0,
        'total_month': 0,

        'rx_rate': 0,
        'tx_rate': 0,

        'transfer_limit_exceeded': False,
    }

    def __init__(self):
        super(MainModel, self).__init__()
        self.bus = dbus.SystemBus()
        self.obj = None
        self.conf = config
        # we have to break MVC here :P
        self.ctrl = None
        # stats stuff
        self.bearer_type = True # we assume 3G
        self.previous_bytes = 0
        self.start_time = None
        self.stop_time = None
        self.rx_bytes = self.tx_bytes = 0
        # DialStats SignalMatch
        self.stats_sm = None
        self.dialer_manager = None
        self.preferences_model = PreferencesModel(lambda: self.device)
        self.profiles_model = ProfilesModel(lambda: self.device, lambda: self)
        self.provider = UsageProvider(USAGE_DB)
        self._init_wader_object()

       # usage stuff from vmc

    def get_device(self):
        return self.device

    def is_connected(self):
        return self.connected

    def _init_wader_object(self):
        try:
            self.obj = self.bus.get_object(WADER_SERVICE, WADER_OBJPATH)
        except dbus.DBusException, e:
            title = _("Error while starting wader")
            details = _("Check that your installation is correct and your "
                        " OS/distro is supported: %s" % e)
            show_error_dialog(title, details)
            raise SystemExit()
        else:
            # get the active device
            self.obj.EnumerateDevices(dbus_interface=WADER_INTFACE,
                                      reply_handler=self._get_devices_cb,
                                      error_handler=self._get_devices_eb)

    def _connect_to_signals(self):
        self.obj.connect_to_signal("DeviceAdded", self._device_added_cb)
        self.obj.connect_to_signal("DeviceRemoved", self._device_removed_cb)
        self.bus.add_signal_receiver(self.on_keyring_key_needed_cb,
                                     "KeyNeeded",
                                     WADER_KEYRING_INTFACE)

    def _device_added_cb(self, opath):
        logger.info('Device with opath %s added' % opath)
        if not self.device:
            self._get_devices_cb([opath])

    def _device_removed_cb(self, opath):
        logger.info('Device with opath %s removed' % opath)

        if self.device_opath:
            logger.info('Device path: %s' % self.device_opath)

        if opath == self.device_opath:
            self.device = None
            self.device_opath = None
            self.dial_path = None
            self.operator = _('Unknown')
            self.status = _('No device')
            self.tech = '----'
            self.rssi = 0

    def _on_network_key_needed_cb(self, opath, tag):
        logger.info("KeyNeeded received, opath: %s tag: %s" % (opath, tag))
        self.ctrl.on_net_password_required(opath, tag)

    def on_keyring_key_needed_cb(self, opath, callback=None):
        logger.info("KeyNeeded received")
        self.ctrl.on_keyring_password_required(opath, callback=callback)

    def get_dialer_manager(self):
        if not self.dialer_manager:
            o = self.bus.get_object(WADER_DIALUP_SERVICE, WADER_DIALUP_OBJECT)
            self.dialer_manager = dbus.Interface(o, WADER_DIALUP_INTFACE)

        return self.dialer_manager

    def quit(self, quit_cb):
        # close UsageProvider on exit
        self.provider.close()

        def quit_eb(e):
            logger.error("Error while removing device: %s" % get_error_msg(e))
            quit_cb()

        if self.device_opath and self.obj:
            logger.debug("Removing device %s before quit." % self.device_opath)
            self.device.Enable(False,
                               dbus_interface=MDM_INTFACE,
                               reply_handler=quit_cb,
                               error_handler=quit_eb)
        else:
            quit_cb()

    def get_imsi(self, get_imsi_cb):

        def get_imsi_eb(failure):
            msg = "Error while getting IMSI for device %s"
            logger.error(msg % self.device_opath)
            get_imsi_cb(None)

        self.device.GetImsi(dbus_interface=CRD_INTFACE,
                            reply_handler=get_imsi_cb,
                            error_handler=get_imsi_eb)

    def _get_devices_eb(self, error):
        logger.error(error)
        # connecting to signals is safe now
        self._connect_to_signals()

    def _get_devices_cb(self, opaths):
        if len(opaths):
            if self.device_opath:
                logger.warn("Device %s is already active" % self.device_opath)
                return

            self.device_opath = opaths[0]
            logger.info("Setting up device %s" % self.device_opath)
            self.device = self.bus.get_object(WADER_SERVICE, self.device_opath)

            self.pin_required = self.puk_required = self.puk2_required = False
            self._initialize_usage_values()
            self.enable_device()
        else:
            logger.warn("No devices found")

        # connecting to signals is safe now
        self._connect_to_signals()

    def _initialize_usage_values(self):
        self.total_month = self.get_month(0)
        self.threeg_transferred = self.get_transferred_3g(0)
        self.twog_transferred = self.get_transferred_gprs(0)
        self.total_transferred = self.get_transferred_total(0)

    def enable_device(self):
        # Enable is a potentially long operation
        self.ctrl.view.start_throbber()

        self.device.Enable(True,
                           dbus_interface=MDM_INTFACE,
                           timeout=ENABLE_TIMEOUT,
                           reply_handler=self._enable_device_cb,
                           error_handler=self._enable_device_eb)

        # -1 == special value for Initialising
        self._get_regstatus_cb((-1, None, None))

    def _enable_device_cb(self):
        logger.info("Device enabled")

        self.pin_required = self.puk_required = self.puk2_required = False

        self.device.connect_to_signal(S.SIG_RSSI, self._rssi_changed_cb)
        self.device.connect_to_signal(S.SIG_NETWORK_MODE,
                                      self._network_mode_changed_cb)

        self.device.GetSignalQuality(dbus_interface=NET_INTFACE,
                                     reply_handler=self._rssi_changed_cb,
                                     error_handler=lambda m:
                                        logger.warn("Cannot get RSSI %s" % m))

        self._start_network_registration()
        # delay the profile creation till the device is completely enabled
        self.profile_required = False
        self._get_config()

    def _enable_device_eb(self, e):
        if dbus_error_is(e, E.SimPinRequired):
            self.pin_required = True
        elif dbus_error_is(e, E.SimPukRequired):
            self.puk_required = True
        elif dbus_error_is(e, E.SimPuk2Required):
            self.puk2_required = True
        else:
            self.sim_error = get_error_msg(e)

        logger.debug("Error enabling device:\n%s" % get_error_msg(e))

    def _start_network_registration(self):
        self._get_regstatus_cb((2, None, None))
        self.device.Register("",
                             dbus_interface=NET_INTFACE,
                             timeout=REGISTER_TIMEOUT,
                             reply_handler=self._network_register_cb,
                             error_handler=self._network_register_eb)

    def _get_regstatus(self, first_time=False):
        self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE,
                            reply_handler=self._get_regstatus_cb,
                            error_handler=lambda e:
                                logger.warn("Error getting registration "
                                            "status: %s " % get_error_msg(e)))

        if not first_time and self.status != "Scanning":
            return False

    # Get Configuration
    def _get_config(self):
        if not self.profile:
            self.profile = self.profiles_model.get_active_profile()
            if self.profile:
                self.profile.activate()
                self.profile_required = False # tell controller
            else:
                logger.warn("No profile, creating one")
                self.profile_required = True # tell controller

    def _network_register_cb(self, ignored=None):
        self._get_regstatus(first_time=True)
        # once we are registered stop the throbber
        self.ctrl.view.stop_throbber()

    def _network_register_eb(self, error):
        logger.error("Error while registering to home network %s" % error)
        try:
            self.net_error = E.error_to_human(error)
        except KeyError:
            self.net_error = error

        # fake a +CREG: 0,3
        self._get_regstatus_cb((3, None, None))
        # registration failed, stop the throbber
        self.ctrl.view.stop_throbber()

    def _rssi_changed_cb(self, rssi):
        logger.info("RSSI changed %d" % rssi)
        self.rssi = rssi

    def _get_regstatus_cb(self, (status, operator_code, operator_name)):
        if status == -1:
            self.status = _('Initialising')
            return
        if status == 1:
            self.status = _("Registered")
        elif status == 2:
            self.status = _("Scanning")
        elif status == 3:
            self.status = _("Reg. rejected")
        elif status == 4:
            self.status = _("Unknown Error")
        elif status == 5:
            self.status = _("Roaming")

        if operator_name is not None:
            self.operator = operator_name

        if status in [1, 5]:
            # only stop asking for reg status when we are in our home
            # network or roaming
            return False

        def obtain_registration_info():
            self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE,
                                        reply_handler=self._get_regstatus_cb,
                                        error_handler=logger.warn)
        # ask in three seconds for more registration info
        gobject.timeout_add_seconds(3, obtain_registration_info)
        return True

    def _network_mode_changed_cb(self, net_mode):
        logger.info("Network mode changed %s" % net_mode)
        self.tech = NET_MODE_SIGNALS[net_mode]
        # account existing traffic to previous tech mode
        self.add_traffic_to_stats()

        # True if 3G bearer, False otherwise
        old_bearer_type = self.bearer_type
        self.bearer_type = net_mode not in TWOG_SIGNALS
        if old_bearer_type != self.bearer_type:
            self.reset_session_data()

    def _check_pin_status(self):

        def _check_pin_status_eb(e):
            if dbus_error_is(e, E.SimPinRequired):
                self.pin_required = False
                self.pin_required = True
            elif dbus_error_is(e, E.SimPukRequired):
                self.puk_required = False
                self.puk_required = True
            elif dbus_error_is(e, E.SimPuk2Required):
                self.puk2_required = False
                self.puk2_required = True
            else:
                self.sim_error = get_error_msg(e)

        self.device.Check(dbus_interface=CRD_INTFACE,
                          reply_handler=lambda: True,
                          error_handler=_check_pin_status_eb)

    def _send_pin_eb(self, e):
        logger.error("SendPin failed %s" % get_error_msg(e))
        self._check_pin_status()

    def _send_puk_eb(self, e):
        logger.error("SendPuk failed: %s" % get_error_msg(e))
        self._check_pin_status()

    def send_pin(self, pin, cb):
        logger.info("Trying authentication with PIN %s" % pin)
        self.device.SendPin(pin,
                            timeout=AUTH_TIMEOUT,
                            dbus_interface=CRD_INTFACE,
                            reply_handler=lambda *args: cb(),
                            error_handler=self._send_pin_eb)

    def send_puk(self, puk, pin, cb):
        logger.info("Trying authentication with PUK %s, PIN %s" % (puk, pin))
        self.device.SendPuk(puk, pin,
                            dbus_interface=CRD_INTFACE,
                            reply_handler=lambda *args: cb(),
                            error_handler=self._send_puk_eb)

    def pin_is_enabled(self, is_enabled_cb, is_enabled_eb):
        logger.info("Checking if PIN request is enabled")
        self.device.Get(CRD_INTFACE, 'PinEnabled',
                        dbus_interface=dbus.PROPERTIES_IFACE,
                        reply_handler=is_enabled_cb,
                        error_handler=is_enabled_eb)

    def enable_pin(self, enable, pin, enable_pin_cb, eb):
        s = "Enabling" if enable else "Disabling"
        logger.info("%s PIN request" % s)

        def enable_pin_eb(e):
            logger.error("EnablePin failed %s" % get_error_msg(e))
            eb(enable)

            if 'SimPukRequired' in get_error_msg(e):
                self.puk_required = True

            if 'SimPuk2Required' in get_error_msg(e):
                self.puk2_required = True

        self.device.EnablePin(pin, enable, dbus_interface=CRD_INTFACE,
                              reply_handler=enable_pin_cb,
                              error_handler=enable_pin_eb)

    def change_pin(self, oldpin, newpin, change_pin_cb, eb):
        logger.info("Change PIN request")

        def change_pin_eb(e):
            logger.error("ChangePin failed %s" % get_error_msg(e))
            eb()

            if 'SimPukRequired' in get_error_msg(e):
                self.puk_required = True

            if 'SimPuk2Required' in get_error_msg(e):
                self.puk2_required = True

        self.device.ChangePin(oldpin, newpin, dbus_interface=CRD_INTFACE,
                              reply_handler=change_pin_cb,
                              error_handler=change_pin_eb)

    def check_transfer_limit(self):
        warn_limit = self.conf.get('preferences', 'usage_notification', False)
        if warn_limit:
            transfer_limit = float(self.conf.get('preferences',
                                                 'traffic_threshold', 0.0))
            transfer_limit = transfer_limit * ONE_MB
            # the session total should be taken into account too
            total_traffic = self.total_transferred + self.total_session
            self.transfer_limit_exceeded = total_traffic > transfer_limit > 0
        else:
            self.transfer_limit_exceeded = False

    def add_traffic_to_stats(self):
        # This does not need parameters because it uses global variables.
        total = self.rx_bytes + self.tx_bytes
        delta_bytes = total - self.previous_bytes
        self.previous_bytes = total

        # 3G traffic
        if self.bearer_type:
            self.threeg_session += delta_bytes
        # GPRS traffic
        else:
            self.twog_session += delta_bytes

        self.total_session += delta_bytes

    def reset_session_data(self):
        # This function stores current tx and rx data in usage data base and
        # reset session counters.
        # if start_time is None it means that the connection attempt failed
        if self.start_time is not None:
            # before resetting the counters, we'll store the stats
            self.end_time = datetime.datetime.utcnow()
            self.provider.add_usage_item(self.start_time,
                                         self.end_time, self.rx_bytes,
                                         self.tx_bytes, self.bearer_type)
            # add session to transferred
            self.threeg_transferred += self.threeg_session
            self.twog_transferred += self.twog_session
            self.total_transferred += self.total_session

            # reset counters
            self.threeg_session = self.twog_session = self.total_session = 0
            self.rx_bytes = self.tx_bytes = self.rx_rate = self.tx_rate = 0
            self.previous_bytes = 0
            self.total_month = self.get_month(0)
            # reset stats tracking
            self.start_time = self.end_time

    def on_dial_stats(self, stats):
        self.rx_bytes, self.tx_bytes = stats[:2]
        self.rx_rate, self.tx_rate = stats[2:]
        self.add_traffic_to_stats()

        # Check for transfer limit if it has not already been reached.
        if not self.transfer_limit_exceeded:
            self.check_transfer_limit()

    def start_stats_tracking(self):
        # ok make sure we get the current epoch start time in UTC format.
        # store it in the models properites for start_time
        self.start_time = datetime.datetime.utcnow()
        # create a callback  for getting data send/received via dbus.
        self.stats_sm = self.bus.add_signal_receiver(self.on_dial_stats,
                                                     S.SIG_DIAL_STATS,
                                                     MDM_INTFACE)

    def stop_stats_tracking(self):
        if self.stats_sm is not None:
            self.stats_sm.remove()
            self.stats_sm = None

        self.reset_session_data()
        self.start_time = self.end_time = None

    def _get_month_date(self, offset):
        today = datetime.date.today()
        if offset:
            new_month = (today.month + offset) % 12 or 12
            new_year = today.year + (today.month + offset - 1) / 12
            try:
                month = today.replace(year=new_year, month=new_month)
            except ValueError:
                next_month = today.replace(day=1,
                                           month=(new_month + 1) % 12 or 12,
                                           year=new_year)
                month = next_month - datetime.timedelta(days=1)
        else:
            month = today
        return month

    def _get_month(self, offset):
        month = self._get_month_date(offset)
        return self.provider.get_usage_for_month(month)

    def get_month(self, offset):
        # returns a string like "Dec 2009" showing month and year.
        month = self._get_month_date(offset)
        return month.strftime("%b %Y")

    def get_session_3g(self):
        return self.threeg_session

    def get_session_gprs(self):
        return self.twog_session

    def get_session_total(self):
        return self.total_session

    def get_transferred_3g(self, offset):
        # filter out all the items that respond True to "is_3g"
        threeg_items = [item for item in self._get_month(offset) if item.is_3g()]
        # get a list with the total transferred for every item and sum them up
        result = sum((item.total() for item in threeg_items))
        if offset == 0:
            result += self.threeg_session
        return result
    

    def get_transferred_gprs(self, offset):
        # filter out all the items that respond True to "is_gprs"
        gprs_items = [item for item in self._get_month(offset) if item.is_gprs()]
        # get a list with the total transferred for every item and sum them up
        result = sum((item.total() for item in gprs_items))
        if offset == 0:
            result += self.twog_session
        return result

    def get_transferred_total(self, offset):
        # XXX: Needs review
        # if current month return the total transferred for this month
#         if not offset:
#             return self.total_transferred

#         # else return the usage of the given month
#         return self.get_month(offset)
        # XXX: Probably this should be more efficient for offset 0 using self.total_transferred.
        result = sum((item.total() for item in self._get_month(offset)))
        if offset == 0:
            result += self.total_session
        return result
