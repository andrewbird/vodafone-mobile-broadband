# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano
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

from uuid import uuid1

import dbus
#from gtkmvc import Model
from wader.bcm.contrib.gtkmvc import Model

from wader.common.consts import (WADER_DIALUP_INTFACE,
                                 WADER_PROFILES_INTFACE, CRD_INTFACE,
                                 MM_ALLOWED_MODE_ANY, MM_NETWORK_BAND_ANY)
from wader.common.utils import get_allowed_modes
from wader.common.exceptions import ProfileNotFoundError
from wader.bcm.config import config
from wader.bcm.logger import logger
from wader.bcm.profiles import manager
from wader.bcm.translate import _

from wader.bcm.consts import (VM_NETWORK_AUTH_ANY,
                              VM_NETWORK_AUTH_PAP,
                              VM_NETWORK_AUTH_CHAP)

CONNECTED, DISCONNECTED = 0, 1


class ProfilesModel(Model):

    def __init__(self, device_callable=None, parent_model_callable=None):
        super(ProfilesModel, self).__init__()
        self.device_callable = device_callable
        self.parent_model_callable = parent_model_callable
        self.conf = config
        self.manager = manager

        uuid = self.conf.get('profile', 'uuid')
        self.active_profile = self.get_profile_by_uuid(uuid)
        self.activate_profile()

    def activate_profile(self):
        if self.active_profile:
            self.active_profile.activate()

    def has_active_profile(self):
        return self.active_profile is not None

    def get_active_profile(self):
        return self.active_profile

    def is_active_profile(self, profile):
        return self.active_profile == profile

    def remove_profile(self, profile):
        if self.is_active_profile(profile):
            self.active_profile = None
            self.conf.set('profile', 'uuid', '')

        profile.delete()

    def set_active_profile(self, profile, setconf=True):
        self.active_profile = profile
        if setconf:
            self.conf.set('profile', 'uuid', profile.uuid)

    def get_profile_by_uuid(self, uuid, setactive=False):
        if uuid is None:
            return None

        try:
            profile = self.manager.get_profile_by_uuid(uuid)
        except ProfileNotFoundError:
            logger.error("No profile found with uuid %s" % uuid)
            return None
        else:
            profile = ProfileModel(self, profile=profile,
                                   device_callable=self.device_callable,
                                   parent_model_callable=self.parent_model_callable)
            if setactive:
                self.active_profile = profile
            return profile

    def get_profiles(self):
        ret = {}
        for profile in self.manager.get_profiles():
            settings = profile.get_settings()
            # filter out wlan profiles
            if 'ppp' in settings:
                uuid = settings['connection']['uuid']
                ret[uuid] = ProfileModel(self, profile=profile,
                                         device_callable=self.device_callable,
                                         parent_model_callable=self.parent_model_callable)
        return ret


class ProfileModel(Model):

    __properties__ = {
        'name': "",
        'username': "",
        'password': "",
        'band': MM_NETWORK_BAND_ANY,
        'network_pref': MM_ALLOWED_MODE_ANY,
        'auth': VM_NETWORK_AUTH_ANY,
        'autoconnect': False,
        'apn': "",
        'uuid': "",
        'static_dns': False,
        'primary_dns': None,
        'secondary_dns': None,
    }

    def __init__(self, parent_model, profile=None, imsi=None, network=None,
                 device_callable=None, parent_model_callable=None):
        super(ProfileModel, self).__init__()

        self.bus = dbus.SystemBus()
        self.manager = manager
        self.profile = profile

        self.parent_model = parent_model
        self.device_callable = device_callable
        self.parent_model_callable = parent_model_callable

        if self.profile and hasattr(self.profile, '__dbus_object_path__'):
            self.profile_path = self.profile.__dbus_object_path__

        if profile:
            self._load_profile(profile=profile)
        elif imsi:
            self._load_profile_from_imsi(imsi)
            self.name = self.make_profilename_unique(self.name)
        elif network:
            self._load_profile_from_network(network)
            self.name = self.make_profilename_unique(self.name)
        else:
            self.uuid = str(uuid1()) # blank profile
            self.name = self.make_profilename_unique(_('Custom'))

        self.state = DISCONNECTED
        self.sm = [] # signal matches list
        self.connect_to_signals()

    def __eq__(self, other):
        if other is None:
            return False
        return self.uuid == other.uuid

    def __ne__(self, other):
        if other is None:
            return True
        return self.uuid != other.uuid

    def __repr__(self):
        return "<ProfileModel %s>" % self.uuid

    def connect_to_signals(self):
        self.sm.append(self.bus.add_signal_receiver(
                                            self._on_disconnected_cb,
                                            "Disconnected",
                                            WADER_DIALUP_INTFACE))
        self.sm.append(self.bus.add_signal_receiver(
                                            self._on_connected_cb,
                                            "Connected",
                                            WADER_DIALUP_INTFACE))

    def _on_disconnected_cb(self):
        self.state = DISCONNECTED

    def _on_connected_cb(self):
        self.state = CONNECTED

    def load_password(self, callback=None):
        if self.profile:
            if self.profile.secrets.is_open():
                secrets = self.profile.secrets.get(ask=True)
                self.password = secrets['gsm']['passwd']
            else:
                # keyring needs to be opened
                parent_model = self.parent_model_callable()
                parent_model.on_keyring_key_needed_cb(self.profile.opath,
                                                      callback=callback)

    def _load_profile(self, profile):
        self.profile = profile
        settings = self.profile.get_settings()
        if 'ipv4' in settings and 'ignore-auto-dns' not in settings['ipv4']:
            settings['ipv4']['ignore-auto-dns'] = False
        self._load_settings(settings)

    def _load_settings(self, settings):
        try:
            self.uuid = settings['connection']['uuid']
            self.name = settings['connection']['id']
            self.username = settings['gsm']['username']
            self.apn = settings['gsm']['apn']
            self.autoconnect = settings['connection'].get('autoconnect', False)
            self.static_dns = settings['ipv4'].get('ignore-auto-dns')
            if settings['ipv4'].get('dns', None):
                dns = settings['ipv4'].get('dns')
                self.primary_dns = dns[0]
                if len(dns) > 1:
                    self.secondary_dns = dns[1]

            self.network_pref = settings['gsm'].get('network-type')
            self.band = settings['gsm'].get('band')
            self.refuse_chap = settings['ppp'].get('refuse-chap')
            self.refuse_pap = settings['ppp'].get('refuse-pap')

            if not self.refuse_pap and self.refuse_chap:
                self.auth = VM_NETWORK_AUTH_PAP
            elif not self.refuse_chap and self.refuse_pap:
                self.auth = VM_NETWORK_AUTH_CHAP
            else:
                self.auth = VM_NETWORK_AUTH_ANY

            # the last one
            if settings['gsm'].get('password', None):
                self.password = settings['gsm']['password']

        except KeyError, e:
            logger.error("Missing required key '%s' in %s" % (e, settings))

    def _load_profile_from_imsi(self, imsi):
        logger.info("Loading profile for imsi %s" % str(imsi))
        try:
            props = self.manager.get_profile_options_from_imsi(imsi)
            self._load_settings(props)
        except ProfileNotFoundError:
            self.uuid = str(uuid1())

    def _load_profile_from_network(self, network):
        logger.info("Loading profile for network %s" % str(network))
        try:
            props = self.manager.get_profile_options_from_network(network)
            self._load_settings(props)
        except ProfileNotFoundError:
            self.uuid = str(uuid1())

    def make_profilename_unique(self, base):
        """Returns a unique name derived from base"""
        profs = self.manager.get_profiles()
        names = [prof.get_settings()['connection']['id'] for prof in profs]

        new, num = base, 1
        while new in names:
            new = '%s %02d' % (base, num)
            num += 1

        return new

    def save(self):
        props = {
            'connection': {
                'name': 'connection',
                'id': self.name,
                'type': 'gsm',
                'uuid': self.uuid,
                'autoconnect': self.autoconnect},
            'gsm': {
                'name': 'gsm',
                'band': self.band,
                'username': self.username,
                'number': '*99#',
                'network-type': self.network_pref,
                'apn': self.apn},
            'ppp': {
                'name': 'ppp',
                'refuse-pap': True,
                'refuse-chap': True,
                'refuse-eap': True,
                'refuse-mschap': True,
                'refuse-mschapv2': True},
            'serial': {
                'name': 'serial',
                'baud': 115200},
            'ipv4': {
                'name': 'ipv4',
                'addresses': [],
                'method': 'auto',
                'ignore-auto-dns': self.static_dns,
                'routes': []},
        }

        # Our GUI only cares about PAP/CHAP
        if self.auth == VM_NETWORK_AUTH_PAP:
            props['ppp']['refuse-pap'] = False
        elif self.auth == VM_NETWORK_AUTH_CHAP:
            props['ppp']['refuse-chap'] = False
        else:
            props['ppp']['refuse-pap'] = False
            props['ppp']['refuse-chap'] = False

        if not props['ipv4']['ignore-auto-dns']:
            props['ipv4']['dns'] = []
        else:
            props['ipv4']['dns'] = [i for i in [self.primary_dns,
                                                self.secondary_dns] if i]

        # clean up None values just in case
        if props['gsm']['band'] is None:
            del props['gsm']['band']
        if props['gsm']['network-type'] is None:
            del props['gsm']['network-type']

        if self.profile:
            self.manager.update_profile(self.profile, props)
            # store password associated to this connection
            secrets = {'gsm': {'passwd': self.password}}
            self.profile.secrets.update(secrets, ask=True)

            logger.debug("Profile modified: %s" % self.profile)
        else:
            uuid = props['connection']['uuid']
            sm = None # SignalMatch object

            def new_profile_cb(path):
                self.profile_path = path
                logger.debug("Profile added: %s" % self.profile_path)

                self.profile = self.manager.get_profile_by_uuid(uuid)
                secrets = {'gsm': {'passwd': self.password}}
                self.profile.secrets.update(secrets, ask=True)

                self.parent_model.set_active_profile(self)

                sm.remove() # remove SignalMatch handler

            sm = self.bus.add_signal_receiver(new_profile_cb,
                                              "NewConnection",
                                              WADER_PROFILES_INTFACE)
            self.manager.add_profile(props)

            self.activate()

    def activate(self):
        if self.state == DISCONNECTED and self.device_callable:
            # only perform this operations if we are disconnected and
            # a device is available
            device = self.device_callable()
            if not device:
                return

            if self.band is not None:
                device.SetBand(self.band,
                               reply_handler=lambda: True,
                               error_handler=logger.error)
            if self.network_pref is not None:
                device.SetAllowedMode(self.network_pref,
                                      reply_handler=lambda: True,
                                      error_handler=logger.error)

    def delete(self):
        if self.profile:
            logger.info("Removing profile %s" % self.profile)
            self.manager.remove_profile(self.profile)
            self.profile_path = None
            self.uuid = None
            self.name = ""

            while self.sm:
                sm = self.sm.pop()
                sm.remove()
        else:
            raise RuntimeError(_("Trying to remove an unsaved profile"))

    def get_supported_bands(self, callback):
        device = self.device_callable()

        device.Get(CRD_INTFACE, 'SupportedBands',
                   dbus_interface=dbus.PROPERTIES_IFACE,
                   reply_handler=callback,
                   error_handler=logger.warn)

    def get_supported_prefs(self, callback):
        device = self.device_callable()

        def convert_cb(modes):
            ret = get_allowed_modes(modes)
            callback(ret)

        device.Get(CRD_INTFACE, 'SupportedModes',
                   dbus_interface=dbus.PROPERTIES_IFACE,
                   reply_handler=convert_cb,
                   error_handler=logger.warn)
