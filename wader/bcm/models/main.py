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

import os
import datetime
import re

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

import gobject
#from gtkmvc import Model
from wader.bcm.contrib.gtkmvc import Model

from wader.bcm.logger import logger
from wader.bcm.dialogs import show_error_dialog
from wader.bcm.models.profile import ProfilesModel
from wader.bcm.models.preferences import PreferencesModel
from wader.bcm.translate import _
from wader.bcm.utils import dbus_error_is, get_error_msg
from wader.bcm.signals import NET_MODE_SIGNALS
from wader.bcm.consts import USAGE_DB, APP_VERSION
from wader.bcm.config import config
from wader.bcm.uptime import get_uptime
from wader.bcm.network_codes import get_msisdn_ussd_info

from wader.common.consts import (WADER_SERVICE, WADER_OBJPATH, WADER_INTFACE,
                                 WADER_DIALUP_SERVICE, WADER_DIALUP_OBJECT,
                                 CRD_INTFACE, NET_INTFACE, MDM_INTFACE,
                                 WADER_DIALUP_INTFACE, WADER_KEYRING_INTFACE,
                                 WADER_PROFILES_INTFACE,
                                 MM_NETWORK_MODE_GPRS, MM_NETWORK_MODE_EDGE,
                                 MM_NETWORK_MODE_2G_ONLY,
                                 MM_GSM_ACCESS_TECH_GSM,
                                 MM_GSM_ACCESS_TECH_GSM_COMPAT,
                                 MM_GSM_ACCESS_TECH_GPRS,
                                 MM_GSM_ACCESS_TECH_EDGE,
                                 MM_GSM_ACCESS_TECH_UMTS,
                                 MM_GSM_ACCESS_TECH_HSDPA,
                                 MM_GSM_ACCESS_TECH_HSUPA,
                                 MM_GSM_ACCESS_TECH_HSPA,
                                 APP_VERSION as CORE_VERSION)
import wader.common.aterrors as E
import wader.common.signals as S
from wader.common.provider import UsageProvider

TWOG_SIGNALS = [MM_NETWORK_MODE_GPRS, MM_NETWORK_MODE_EDGE,
                MM_NETWORK_MODE_2G_ONLY]

TWOG_TECH = [MM_GSM_ACCESS_TECH_GSM, MM_GSM_ACCESS_TECH_GSM_COMPAT,
             MM_GSM_ACCESS_TECH_GPRS, MM_GSM_ACCESS_TECH_EDGE]

UPDATE_INTERVAL = CONFIG_INTERVAL = 2 * 1000 # 2ms
NETREG_INTERVAL = 5 * 1000 # 5ms

AUTH_TIMEOUT = 150        # 2.5m
ENABLE_TIMEOUT = 2 * 60   # 2m
REGISTER_TIMEOUT = 3 * 60 # 3m

ONE_MB = 2 ** 20


class MainModel(Model):

    __properties__ = {
        'rssi': None,
        'profile': None,
        'device': None,
        'device_opath': None,
        'dial_path': None,
        'connected': False,
        'operator': None,
        'status': _('No device'),
        'tech': None,
        'msisdn': _('Unknown'),
        'pin_required': False,
        'puk_required': False,
        'puk2_required': False,
        'profile_required': False,
        'sim_error': False,
        'net_error': '',
        'key_needed': False,
        # usage properties
        'current_session_3g': -1,
        'current_session_2g': -1,
        'current_session_total': -1,
        'current_session_time': 0,
        'last_month_3g': -1,
        'last_month_2g': -1,
        'last_month_total': -1,
        'last_month_name': '',
        'current_summed_3g': -1,
        'current_summed_2g': -1,
        'current_summed_total': -1,
        'current_month_name': '',
        'rx_rate': -1,
        'tx_rate': -1,
        'transfer_limit_exceeded': False,
        # payt properties
        'payt_available': None,
        'payt_credit_balance': _('Not available'),
        'payt_credit_date': None,
        'payt_credit_busy': False,
        'payt_submit_busy': False,
    }

    def __init__(self):
        logger.info("BCM %s starting, using %s core" % (
            self.get_app_version(), self.get_core_version()))

        super(MainModel, self).__init__()
        self.bus = dbus.SystemBus()
        self.obj = None
        self.conf = config
        # we have to break MVC here :P
        self.ctrl = None
        # stats stuff
        self.is_3g_bearer = True # we assume 3G
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
        # Per SIM stuff
        self.imsi = None
        self.msisdn = None
        # PIN in keyring stuff
        self.manage_pin = False
        self.keyring_available = self.is_keyring_available()

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

        # catch profiles removed just in case it's our active one
        self.bus.add_signal_receiver(self._on_delete_profile,
                                     "Removed",
                                     WADER_PROFILES_INTFACE)

    def _on_delete_profile(self):
        # check if the active one still exists
        # popup dialog if not
        if self.profiles_model.active_profile_just_deleted():
            logger.info("Active Profile removed")
            self.profile_required = False # toggle to tell controller
            self.profile_required = True
        else:
            logger.info("Profile removed")

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
            self.status = _('No device')
            self.operator = None
            self.tech = None
            self.rssi = None
            self.imsi = None
            self.msisdn = None

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

    def get_imsi(self, cb):
        logger.info("main.py: model - get_imsi called")
        if self.imsi:
            logger.info("main.py: model - get_imsi imsi is: " + self.imsi)
            cb(self.imsi)
            return

        def get_imsi_cb(imsi):
            self.imsi = imsi
            cb(self.imsi)

        def get_imsi_eb(failure):
            msg = "Error while getting IMSI for device %s"
            logger.error(msg % self.device_opath)
            cb(None)

        self.device.GetImsi(dbus_interface=CRD_INTFACE,
                            reply_handler=get_imsi_cb,
                            error_handler=get_imsi_eb)

    def get_sim_conf(self, item, default=None):
        if self.imsi is None:

            def imsi_cb(imsi):
                logger.info("get_sim_conf - fetched IMSI %s" % imsi)

            self.get_imsi(imsi_cb)

        return self.conf.get("sim/%s" % self.imsi, item, default)

    def set_sim_conf(self, item, value):
        if self.imsi is None:

            def imsi_cb(imsi):
                logger.info("set_sim_conf - fetched IMSI %s" % imsi)

            self.get_imsi(imsi_cb)
        self.conf.set("sim/%s" % self.imsi, item, value)

    def _get_msisdn_by_ussd(self, ussd, cb):
        mccmnc, request, regex = ussd

        def get_msisdn_cb(response):
            match = re.search(regex, response)
            if match:
                msisdn = match.group('number')
                self.msisdn = msisdn
                logger.info("MSISDN from network: %s" % msisdn)
                self.set_sim_conf('msisdn', self.msisdn)
                cb(self.msisdn)
            else:
                logger.info("MSISDN from network: '%s' didn't match regex" %
                            response)
                cb(None)

        def get_msisdn_eb(failure):
            msg = "MSISDN Error fetching via USSD"
            logger.error(msg)
            cb(None)

        self.device.Initiate(request,
                             reply_handler=get_msisdn_cb,
                             error_handler=get_msisdn_eb)

    def get_msisdn(self, cb):
        if self.msisdn:
            logger.info("MSISDN from model cache: %s" % self.msisdn)
            cb(self.msisdn)
            return

        def get_imsi_cb(imsi):
            if imsi:
                msisdn = self.conf.get("sim/%s" % imsi, 'msisdn')
                if msisdn:
                    logger.info("MSISDN from gconf: %s" % msisdn)
                    self.msisdn = msisdn
                    cb(self.msisdn)
                    return

            ussd = get_msisdn_ussd_info(imsi)
            if ussd:
                self._get_msisdn_by_ussd(ussd, cb)
            else:
                cb(_("Unknown"))

        self.get_imsi(get_imsi_cb)

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
            logger.info("main.py: model - Setting up device %s" % self.device_opath)
            self.device = self.bus.get_object(WADER_SERVICE, self.device_opath)

            self.pin_required = self.puk_required = self.puk2_required = False
            self.sim_error = False
            self.status = _('Device found')
            self.enable_device()
        else:
            logger.warn("No devices found")

        # connecting to signals is safe now
        self._connect_to_signals()

    def enable_device(self):
        # Enable is a potentially long operation
        self.device.Enable(True,
                           dbus_interface=MDM_INTFACE,
                           timeout=ENABLE_TIMEOUT,
                           reply_handler=self._enable_device_cb,
                           error_handler=self._enable_device_eb)

        # -1 == special value for Initialising
        self._get_regstatus_cb((-1, None, None))

    def _enable_device_cb(self):
        logger.info("main.py: model - Device enabled")

        self.pin_required = self.puk_required = self.puk2_required = False

        self.init_dial_stats()

        self.device.connect_to_signal(S.SIG_RSSI, self._rssi_changed_cb)
        self.device.connect_to_signal(S.SIG_NETWORK_MODE,
                                      self._network_mode_changed_cb)

        # react to any modem manager property changes
        self.device.connect_to_signal("MmPropertiesChanged",
                                      self.on_mm_props_change_cb)

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
                logger.warn("main.py: model - No profile, creating one")
                self.profile_required = True # tell controller
                logger.warn("main.py: model - profile_required being set to 'True' ")
        else:
            self.profile.activate()

    def _network_register_cb(self, ignored=None):
        self._get_regstatus(first_time=True)
        self.get_msisdn(lambda x: True)

        self.device.GetSignalQuality(dbus_interface=NET_INTFACE,
                                     reply_handler=self._rssi_changed_cb,
                                     error_handler=lambda m:
                                     logger.warn("Cannot get RSSI %s" % m))

    def _network_register_eb(self, error):
        logger.error("Error while registering to home network %s" % error)
        try:
            self.net_error = E.error_to_human(error)
        except KeyError:
            self.net_error = error

        # fake a +CREG: 0,3
        self._get_regstatus_cb((3, None, None))

    def _rssi_changed_cb(self, rssi):
        logger.info("RSSI changed %d" % rssi)
        self.rssi = rssi

    def _get_regstatus_cb(self, (status, operator_code, operator_name)):
        if status == -1:
            # Don't set status here, as it stamps on 'Device found' and others
            # that aren't included in registration values
            # self.status = _('No device')
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

    def on_mm_props_change_cb(self, ifname, ifprops):
        mapped = {
            MM_GSM_ACCESS_TECH_GPRS: _('GPRS'),
            MM_GSM_ACCESS_TECH_EDGE: _('EDGE'),
            MM_GSM_ACCESS_TECH_UMTS: _('UMTS'),
            MM_GSM_ACCESS_TECH_HSDPA: _('HSDPA'),
            MM_GSM_ACCESS_TECH_HSUPA: _('HSUPA'),
            MM_GSM_ACCESS_TECH_HSPA: _('HSPA'),
        }

        if ifname == NET_INTFACE and 'AccessTechnology' in ifprops:
            self.tech = mapped.get(ifprops['AccessTechnology'], _('N/A'))
            logger.info("AccessTechnology changed %s", self.tech)

            is_3g_bearer = ifprops['AccessTechnology'] not in TWOG_TECH

            # maybe write a Usage DB segment
            if self.connected:
                self.write_dial_stats(is_3g_bearer)

            self.is_3g_bearer = is_3g_bearer

    def _network_mode_changed_cb(self, net_mode):
        self.tech = NET_MODE_SIGNALS[net_mode]
        logger.info("Network mode changed %s" % self.tech)

        is_3g_bearer = net_mode not in TWOG_SIGNALS

        # maybe write a Usage DB segment
        if self.connected:
            self.write_dial_stats(is_3g_bearer)

        self.is_3g_bearer = is_3g_bearer

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

    def send_pin(self, pin, cb):
        logger.info("Trying authentication with PIN %s" % pin)

        def _send_pin_cb(*args):
            logger.info("Authentication success")
            if self.manage_pin:
                self.store_pin_in_keyring(pin)
            cb()

        def _send_pin_eb(e):
            logger.error("SendPin failed %s" % get_error_msg(e))
            if self.manage_pin:
                self.delete_pin_from_keyring()
            self._check_pin_status()

        self.device.SendPin(pin,
                            timeout=AUTH_TIMEOUT,
                            dbus_interface=CRD_INTFACE,
                            reply_handler=_send_pin_cb,
                            error_handler=_send_pin_eb)

    def is_keyring_available(self):
        # XXX: this needs to work with keyring backend abstraction
        try:
            # XXX: until we get the keyring working
            #import gnomekeyring
            raise ImportError
        except ImportError:
            return False

        return True

    def store_pin_in_keyring(self, pin):
        # XXX: In the future is would be good enhance this to fetch/store in
        #      different keyring paths according to the following preference:
        #      1/ ICC-ID identifies the SIM uniquely and is available before
        #         PIN auth, but only the latest datacards support its
        #         retrieval.
        #      2/ IMEI identifies the datacard uniquely, but if the user swaps
        #         SIM to another device it won't be found, or worse it finds
        #         the PIN associated with another SIM
        #      3/ Store in application specific location, this is effectively a
        #         single PIN for all SIMs used within BCM
        if not self.keyring_available:
            return
        logger.info("Storing PIN in keyring")

    def fetch_pin_from_keyring(self):
        # XXX: until we get the keyring working
        return None

    def delete_pin_from_keyring(self):
        if not self.keyring_available:
            return
        logger.info("Deleting PIN from keyring")

    def _send_puk_eb(self, e):
        logger.error("SendPuk failed: %s" % get_error_msg(e))
        self._check_pin_status()

    def send_puk(self, puk, pin, cb):
        logger.info("Trying authentication with PUK %s, PIN %s" % (puk, pin))
        self.device.SendPuk(puk, pin,
                            dbus_interface=CRD_INTFACE,
                            reply_handler=lambda * args: cb(),
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
            self.transfer_limit_exceeded = (
                                self.current_summed_total > transfer_limit > 0)
        else:
            self.transfer_limit_exceeded = False

    def calc_month(self, offset):
        v_3g = v_2g = 0

        for item in self._get_month(offset):
            if item.is_3g():
                v_3g += item.total()
            else:
                v_2g += item.total()

        return (v_3g, v_2g)

    def calc_current_summed(self):
        self.current_summed_3g = self._month_to_date_3g + self.current_session_3g
        self.current_summed_2g = self._month_to_date_2g + self.current_session_2g
        self.current_summed_total = self.current_summed_3g + self.current_summed_2g

    def zero_current_session(self):
        self.current_session_3g = 0
        self.current_session_2g = 0
        self.current_session_total = 0

    def populate_last_month(self):
        self.last_month_name = self.get_month(-1)
        self.last_month_3g, self.last_month_2g = self.calc_month(-1)
        self.last_month_total = self.last_month_3g + self.last_month_2g

    def populate_curr_month(self):
        self.current_month_name = self.get_month(0)
        self._month_to_date_3g, self._month_to_date_2g = self.calc_month(0)
        self.zero_current_session()
        self.calc_current_summed()

    def init_dial_stats(self):
        self.rx_bytes = self.tx_bytes = self.rx_rate = self.tx_rate = 0

        # to calc the delta
        self.previous_bytes = 0

        # the last values written to DB
        self._last_time = self.start_time
        self._last_rx = self.rx_bytes
        self._last_tx = self.tx_bytes

    def write_dial_stats(self, is_3g_bearer=None):
        # Save data to the DB. Called on bearer change, connection tear down,
        # or possibly day transition(future)

        # nothing to write
        if ((self._last_rx == self.rx_bytes) and
            (self._last_tx == self.tx_bytes)):
            return

        # coalesce writes
        if self.is_3g_bearer == is_3g_bearer:
            return

        # before resetting the counters, we'll store the stats
        now = datetime.datetime.utcnow()
        self.provider.add_usage_item(self._last_time, now,
                                     self.rx_bytes - self._last_rx,
                                     self.tx_bytes - self._last_tx,
                                     self.is_3g_bearer)
        self._last_time = now
        self._last_rx = self.rx_bytes
        self._last_tx = self.tx_bytes

    def on_dial_stats(self, stats):
        self.rx_bytes, self.tx_bytes = stats[:2]
        self.rx_rate, self.tx_rate = stats[2:]

        # calc the delta and update for next time
        total_bytes = self.rx_bytes + self.tx_bytes
        dx_bytes = total_bytes - self.previous_bytes
        self.previous_bytes = total_bytes

        # calc current session
        if self.is_3g_bearer:
            self.current_session_3g += dx_bytes
        else:
            self.current_session_2g += dx_bytes
        self.current_session_total = self.current_session_3g + self.current_session_2g

        # calc transferred to date
        self.calc_current_summed()

        # Check for transfer limit if it has not already been reached.
        if not self.transfer_limit_exceeded:
            self.check_transfer_limit()

    def start_stats_tracking(self):
        # ok make sure we get the current epoch start time in UTC format.
        # store it in the models properites for start_time
        self.start_time = datetime.datetime.utcnow()
        # create a callback for getting data send/received via dbus.
        self.stats_sm = self.bus.add_signal_receiver(self.on_dial_stats,
                                                     S.SIG_DIAL_STATS,
                                                     MDM_INTFACE)
        self.init_dial_stats()

    def stop_stats_tracking(self):
        if self.stats_sm is not None:
            self.stats_sm.remove()
            self.stats_sm = None

        self.write_dial_stats()

        self.zero_current_session()

    def get_connection_time(self):
        return datetime.datetime.utcnow() - self.start_time

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

    def get_uptime(self):
        """Returns the uptime with uptime(1)'s format"""
        return get_uptime()

    def get_os_name(self):
        return os.uname()[0]

    def get_os_version(self):
        return os.uname()[2]

    def get_app_version(self):
        return APP_VERSION

    def get_core_version(self):
        return CORE_VERSION
