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


import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import gobject
from gtkmvc import Model
import datetime

from wader.vmc.logger import logger
from wader.vmc.dialogs import show_error_dialog
from wader.vmc.models.profile import ProfilesModel, ProfileModel
from wader.vmc.models.preferences import PreferencesModel
from wader.vmc.translate import _
from wader.vmc.utils import dbus_error_is, get_error_msg
from wader.vmc.signals import NET_MODE_SIGNALS
from wader.vmc.config import config
from wader.common.consts import (WADER_SERVICE, WADER_OBJPATH, WADER_INTFACE,
                                 WADER_DIALUP_SERVICE, WADER_DIALUP_OBJECT,
                                 CRD_INTFACE, NET_INTFACE, MDM_INTFACE,
                                 NM_SYSTEM_SETTINGS_CONNECTION,
                                 WADER_DIALUP_INTFACE, WADER_KEYRING_INTFACE,
                                 MM_NETWORK_MODE_UMTS, MM_NETWORK_MODE_HSDPA,
                                 MM_NETWORK_MODE_HSUPA, MM_NETWORK_MODE_HSPA, MM_NETWORK_MODE_GPRS)

import wader.common.aterrors as E
import wader.common.signals as S
from wader.common.provider import UsageProvider

#from wader.vmc.persistent import usage_manager

THREEG_SIGNALS = [MM_NETWORK_MODE_UMTS, MM_NETWORK_MODE_HSDPA,
                  MM_NETWORK_MODE_HSUPA, MM_NETWORK_MODE_HSPA]


UPDATE_INTERVAL = CONFIG_INTERVAL = 2 * 1000 # 2ms
NETREG_INTERVAL = 5 * 1000 # 5ms

AUTH_TIMEOUT = 150        # 2.5m
ENABLE_TIMEOUT = 2 * 60   # 2m
REGISTER_TIMEOUT = 3 * 60 # 3m

ONE_MB = 2**20

if dbus.version >= (0, 83, 0):
    def get_dbus_error(e):
        return e.get_dbus_name()
else:
    def get_dbus_error(e):
        return e.message

class MainModel(Model):

    __properties__ = {
        'rssi' : 0,
        'profile' : None,
        'device' : None,
        'device_path' : None,
        'dial_path' : None,
        'operator' : _('Unknown'),
        'status' : _('Not registered'),
        'tech' : _('Unknown'),

        'pin_required': False,
        'puk_required': False,
        'puk2_required': False,
        'profile_required': False,
        'sim_error' : False,
        'net_error' : '',
        'key_needed' : False,

        'rx_bytes': 0,
        'tx_bytes': 0,
        'rx_rate' : 0,
        'tx_rate' : 0,
        'start_time':0, 
        'stop_time':0, 
        'total_bytes': 0,

        'transfer_limit_exceeded': False  
    }

    connected = False     # XXX: Should this come in properties?
    previous_bytes = 0    # This variable shows last session bytes stored in gprs or 3g.
    previous_tech = _('Unknown') # Last mobile technology used.
    session_3g = 0  # Stores current session 3g tx and rx bytes.
    session_gprs = 0 # Stores current session gprs tx and rx bytes.

    def __init__(self):
        super(MainModel, self).__init__()
        self.bus = dbus.SystemBus()
        self.obj = None
        self.conf = config
        # we have to break MVC here :P
        self.ctrl = None
        # DialStats SignalMatch
        self.stats_sm = None
        self.dialer_manager = None
        self.preferences_model = PreferencesModel(lambda: self.device)
        self.profiles_model = ProfilesModel(lambda: self.device)
        self._init_wader_object()

       # usage stuff from vmc
        self.session_stats = (0, 0)
        self.month_cache = {}
        self.origin_date = None
        self.clean_usage_cache()

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

        self.bus.add_signal_receiver(self._on_network_key_needed_cb,
                                     "KeyNeeded",
                                     NM_SYSTEM_SETTINGS_CONNECTION)
        self.bus.add_signal_receiver(self._on_keyring_key_needed_cb,
                                     "KeyNeeded",
                                     WADER_KEYRING_INTFACE)

    def _device_added_cb(self, udi):
        logger.info('Device with udi %s added' % udi)
        if not self.device:
            self._get_devices_cb([udi])

    def _device_removed_cb(self, udi):
        logger.info('Device with udi %s removed' % udi)

        if self.device_path:
            logger.info('Device path: %s' % self.device_path)

        if udi == self.device_path:
            self.device = None
            self.device_path = None
            self.dial_path = None
            self.operator = _('Unknown')
            self.status = _('No device')
            self.tech = '----'
            self.rssi = 0

    def _on_network_key_needed_cb(self, opath, tag):
        logger.info("KeyNeeded received, opath: %s tag: %s" % (opath, tag))
        self.ctrl.on_net_password_required(opath, tag)

    def _on_keyring_key_needed_cb(self, opath):
        logger.info("KeyNeeded received")
        self.ctrl.on_keyring_password_required(opath)

    def get_dialer_manager(self):
        if not self.dialer_manager:
            o = self.bus.get_object(WADER_DIALUP_SERVICE, WADER_DIALUP_OBJECT)
            self.dialer_manager = dbus.Interface(o, WADER_DIALUP_INTFACE)

        return self.dialer_manager

    def quit(self, quit_cb):
        def quit_eb(e):
            logger.error("Error while removing device: %s" % get_error_msg(e))
            quit_cb()

        if self.device_path and self.obj:
            logger.debug("Removing device %s before quit." % self.device_path)
            self.device.Enable(False,
                               dbus_interface=MDM_INTFACE,
                               reply_handler=quit_cb,
                               error_handler=quit_eb)
        else:
            quit_cb()

    def get_imsi(self, callback):
        def errback(failure):
            msg = "Error while getting IMSI for device %s"
            logger.error(msg % self.device_path)
            callback(None)

        self.device.GetImsi(dbus_interface=CRD_INTFACE,
                            reply_handler=lambda imsi: callback(imsi),
                            error_handler=errback)

    def _get_devices_eb(self, error):
        logger.error(error)
        # connecting to signals is safe now
        self._connect_to_signals()

    def _get_devices_cb(self, opaths):
        if len(opaths):
            if self.device_path:
                logger.warn("Device %s is already active" % self.device_path)
                return

            self.device_path = opaths[0]
            logger.info("Setting up device %s" % self.device_path)
            self.device = self.bus.get_object(WADER_SERVICE, self.device_path)

            self.pin_required = False
            self.puk_required = False
            self.puk2_required = False
            self.total_bytes = self.conf.get('statistics', 'total_bytes', 0)

            self.enable_device()
        else:
            logger.warn("No devices found")

        # connecting to signals is safe now
        self._connect_to_signals()

    def enable_device(self):
        # enabling the device is an expensive operation
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

        self.pin_required = False
        self.puk_required = False
        self.puk2_required = False

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
            return False

        def obtain_registration_info():
            self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE,
                                        reply_handler=self._get_regstatus_cb,
                                        error_handler=logger.warn)

        gobject.timeout_add_seconds(3, obtain_registration_info)
        return True

    def _network_mode_changed_cb(self, net_mode):
        logger.info("Network mode changed %s" % net_mode)
        self.tech = NET_MODE_SIGNALS[net_mode]
        self.add_3g_gprs_traffic()
        self.previous_tech = net_mode

    def _check_pin_status(self):
        def _check_pin_status_cb():
            pass
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
                          reply_handler=_check_pin_status_cb,
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

    def pin_is_enabled(self, cb=None, eb=None):
        logger.info("Checking if PIN request is enabled")

        def is_enabled_cb(result):
            if cb:
                cb(result)

        def is_enabled_eb(e):
            logger.warn(e)
            if eb:
                eb(e)

        self.device.Get(CRD_INTFACE, 'PinEnabled',
                        dbus_interface=dbus.PROPERTIES_IFACE,
                        reply_handler=is_enabled_cb,
                        error_handler=is_enabled_eb)

    def enable_pin(self, enable, pin, cb=None, eb=None):
        s = "Enabling" if enable else "Disabling"
        logger.info("%s PIN request" % s)

        def enable_pin_cb():
            if cb:
                cb(enable)

        def enable_pin_eb(e):
            logger.error("EnablePin failed %s" % get_error_msg(e))
            if eb:
                eb(enable)

            if 'SimPukRequired' in get_dbus_error(e):
                self.puk_required = True

            if 'SimPuk2Required' in get_dbus_error(e):
                self.puk2_required = True

        self.device.EnablePin(pin, enable, dbus_interface=CRD_INTFACE,
                                           reply_handler=enable_pin_cb,
                                           error_handler=enable_pin_eb)

    def change_pin(self, oldpin, newpin, cb=None, eb=None):
        logger.info("Change PIN request")

        def change_pin_cb():
            if cb:
                cb()

        def change_pin_eb(e):
            logger.error("ChangePin failed %s" % get_error_msg(e))
            if eb:
                eb()

            if 'SimPukRequired' in get_dbus_error(e):
                self.puk_required = True

            if 'SimPuk2Required' in get_dbus_error(e):
                self.puk2_required = True

        self.device.ChangePin(oldpin, newpin, dbus_interface=CRD_INTFACE,
                                              reply_handler=change_pin_cb,
                                              error_handler=change_pin_eb)

    def check_transfer_limit(self):
        warn_limit = self.conf.get('preferences', 'usage_notification', False)
        print "self.total_bytes: ", self.total_bytes
        if warn_limit:
            transfer_limit = self.conf.get('preferences', 'traffic_threshold', 0.0)
            transfer_limit = float(transfer_limit) * ONE_MB
            if transfer_limit > 0  and  self.total_bytes > transfer_limit:
                self.transfer_limit_exceeded = True
            else:
                self.transfer_limit_exceeded = False
        else:
            self.transfer_limit_exceeded = False

    def add_3g_gprs_traffic(self): # This does not need parameters because it uses global variables.
        total = self.rx_bytes + self.tx_bytes
        delta_bytes = total - self.previous_bytes
        self.previous_bytes = total

        if self.previous_tech in THREEG_SIGNALS :
            self.session_3g += delta_bytes
        elif self.previous_tech == MM_NETWORK_MODE_GPRS :
            self.session_gprs += delta_bytes
            
    def on_dial_stats(self, stats):
        try:
            total = int(self.conf.get('statistics', 'total_bytes', 0))
        except ValueError:
            total = 0

        self.rx_bytes, self.tx_bytes = stats[:2]
        self.rx_rate, self.tx_rate = stats[2:]
        self.total_bytes = total + self.rx_bytes + self.tx_bytes
        self.add_3g_gprs_traffic()

        # Check for transfer limit if it has not already been reached.
        if not self.transfer_limit_exceeded :
            self.check_transfer_limit()

    def start_stats_tracking(self):
        self.stats_sm = self.bus.add_signal_receiver(self.on_dial_stats,
                                                     S.SIG_DIAL_STATS,
                                                     MDM_INTFACE)

    def stop_stats_tracking(self):
        if self.stats_sm is not None:
            self.stats_sm.remove()
            self.stats_sm = None

        # before we set the counters to zero let's store this in the usage db.
        data_usage_entry = UsageProvider()
        #sim_network = NetworkProvider()
        #networks_attributes = sim_network.get_network_by_id("460009075714956")
        #usage_data = data_usage_entry.add_usage_item(self, True, start, end, bytes_recv, bytes_sent):
            
        usage_data = data_usage_entry.add_usage_item(True,  1253860338622714,  1253860341703897, 1984,  1560)

        self.rx_bytes = 0
        self.tx_bytes = 0
        self.rx_rate = self.tx_rate = 0
        self.previous_bytes = 0

        self.conf.set('statistics', 'total_bytes', self.total_bytes)

        current_month_3g = self.conf.get('statistics', 'current_month_3g', 0)
        current_month_3g += self.session_3g
        self.conf.set('statistics', 'current_month_3g', current_month_3g)
        self.session_3g = 0

        current_month_gprs = self.conf.get('statistics', 'current_month_gprs', 0)
        current_month_gprs += self.session_gprs
        self.conf.set('statistics', 'current_month_gprs', current_month_gprs)
        self.session_gprs = 0
        
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

#    def _update_session_stats(self, stats):
#        self.session_stats = stats

    def _get_usage_for_month(self, dateobj):
        # We check if current month is finished.
        current_month = self.conf.get('statistics', 'current_month', self.origin_date.month)
        if self.origin_date.month != current_month :
            current_month_3g = self.conf.get('statistics', 'current_month_3g', 0)
            current_month_gprs = self.conf.get('statistics', 'current_month_gprs', 0)
            self.conf.set('statistics', 'previous_month_3g', current_month_3g)
            self.conf.set('statistics', 'previous_month_gprs', current_month_gprs)
            self.conf.set('statistics', 'current_month_3g', 0)
            self.conf.set('statistics', 'current_month_gprs', 0)
            self.conf.set('statistics', 'current_month', self.origin_date.month)
            self.transfer_limit_exceeded = False
            self.conf.set('statistics', 'total_bytes', 0)

        key = (dateobj.year, dateobj.month)
        if not self.month_cache.has_key(key):
            # Current session information
            if self.is_connected() and self.origin_date.month == dateobj.month:
#                tracker = self.connsm.tracker
#                tracker.get_current_usage().addCallback(
#                                                    self._update_session_stats)

#                stats = self.session_stats
#                umts = tracker.conn_mode in THREEG_SIGNALS
#                transferred = stats[0] + stats[1]
#                transferred_3g = umts and transferred or 0
#                transferred_gprs = not umts and transferred or 0
#                transferred_3g = self.rx_bytes + self.tx_bytes
#                transferred_gprs = 0
#                transferred_3g
                transferred_3g = self.session_3g
                transferred_gprs = self.session_gprs
            else:
                transferred_3g = 0
                transferred_gprs = 0

         # XXX: WARNING - IMPORTANT - RIGHT NOW ALL TRAFFIC IS CONSIDERED AS UMTS TRAFFIC.

            if self.origin_date.month == dateobj.month :    
                # Get current month data.
                transferred_3g += self.conf.get('statistics', 'current_month_3g', 0)
                transferred_gprs += self.conf.get('statistics', 'current_month_gprs', 0)
#                transferred_3g = self.current_month_3g
#                transferred_gprs = self.current_month_gprs
            elif self.origin_date.month == (dateobj.month + 1) or (self.origin_date.month == 1 and dateobj.month == 12) :
                # Get previous month data.
                transferred_3g = self.conf.get('statistics', 'previous_month_3g', 0)
                transferred_gprs = self.conf.get('statistics', 'previous_month_gprs', 0)
            else :
                # Data not available.
                transferred_3g = 0
                transferred_gprs = 0
        
                
            # Historical usage data
#            usage = usage_manager.get_usage_for_month(dateobj)
#            for item in usage:
#                if item.umts:
#                    transferred_3g += item.bits_recv + item.bits_sent
#                else:
#                    transferred_gprs += item.bits_recv + item.bits_sent

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
#        tracker = self.connsm.tracker
#        umts = tracker.conn_mode in THREEG_SIGNALS
#        total = self.session_stats[0] + self.session_stats[1]
#        return umts and total or 0
        return self.session_3g

    def get_session_gprs(self):
        if not self.is_connected():
            return 0
#        tracker = self.connsm.tracker
#        umts = tracker.conn_mode in THREEG_SIGNALS
#        total = self.session_stats[0] + self.session_stats[1]
#        return not umts and total or 0
        return self.session_gprs

    def get_session_total(self):
        return self.get_session_3g() + self.get_session_gprs()

