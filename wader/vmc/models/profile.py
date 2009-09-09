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
import gobject
from gtkmvc import Model, ListStoreModel

from wader.common.consts import (NM_PASSWD, WADER_DIALUP_INTFACE,
                                 WADER_PROFILES_INTFACE, NET_INTFACE,
                                 MM_NETWORK_MODE_ANY, MM_NETWORK_BAND_ANY)
from wader.common.utils import (convert_int_to_uint as convert,
                                patch_list_signature)
from wader.common.exceptions import ProfileNotFoundError
import wader.common.exceptions as ex
from wader.vmc.config import config
from wader.vmc.logger import logger
from wader.vmc.profiles import manager
from wader.vmc.translate import _

from wader.vmc.consts import (VM_NETWORK_AUTH_ANY,
                              VM_NETWORK_AUTH_PAP,
                              VM_NETWORK_AUTH_CHAP)

CONNECTED, DISCONNECTED = range(2)


class ProfilesModel(ListStoreModel):

    def __init__(self, device_callable=None):
        super(ProfilesModel, self).__init__(gobject.TYPE_BOOLEAN,
                                            gobject.TYPE_PYOBJECT)
        self.device_callable = device_callable
        self.active_iter = None
        self.conf = config
        self.manager = manager
        self.populate_profiles()

    def has_active_profile(self):
        return self.active_iter is not None

    def get_active_profile(self):
        if self.active_iter is None:
            raise RuntimeError(_("No active profile"))

        return self.get_value(self.active_iter, 1)

    def add_profile(self, profile, default=False):
        if not self.has_active_profile():
            default = True

        if not default:
            # just add it, do not make it default
            return self.append([default, profile])

        # set the profile as default and set active_iter
        self.conf.set('profile', 'uuid', profile.uuid)
        self.active_iter = self.append([True, profile])
        return self.active_iter

    def has_profile(self, profile=None, uuid=""):
        if profile:
            uuid = profile.uuid

        _iter = self.get_iter_first()
        while _iter:
            _profile = self.get_value(_iter, 1)

            if _profile.uuid == uuid:
                return _iter

            _iter = self.iter_next(_iter)

        return None

    def remove_profile(self, profile):
        _iter = self.has_profile(profile)
        if not _iter:
            uuid = profile.uuid
            raise ProfileNotFoundError("Profile %s not found" % uuid)

        if profile.uuid == self.get_value(self.active_iter, 1).uuid:
            self.set(self.active_iter, False, 0)
            self.active_iter = None

        self.conf.set('profile', 'uuid', '')

        self.remove(_iter)
        profile.delete()

    def set_default_profile(self, uuid):
        _iter = self.has_profile(uuid=uuid)
        assert _iter is not None, "Profile %s does not exist" % uuid
        if self.active_iter and self.iter_is_valid(self.active_iter):
            self.set(self.active_iter, 0, False)

        self.set(_iter, 0, True)
        self.active_iter = _iter
        self.conf.set('profile', 'uuid', self.get_value(_iter, 1).uuid)

    def populate_profiles(self):
        uuid = self.conf.get('profile', 'uuid')

        for _uuid, profile in self.get_profiles().iteritems():
            if not self.has_profile(uuid=_uuid):
                default = True if uuid and uuid == _uuid else False
                self.add_profile(profile, default)

    def get_profiles(self):
        ret = {}
        for profile in self.manager.get_profiles():
            settings = profile.get_settings()
            if 'ppp' in settings:
                uuid = settings['connection']['uuid']
                ret[uuid] = ProfileModel(self, profile=profile,
                                         device_callable=self.device_callable)
        return ret

    def profile_added(self, profile):
        self.add_profile(profile)

class ProfileModel(Model):

    __properties__ = {
        'name' : "",
        'username' : "",
        'password' : "",
        'band' : MM_NETWORK_BAND_ANY,
        'network_type' : MM_NETWORK_MODE_ANY,
        'auth' : VM_NETWORK_AUTH_ANY,
        'autoconnect' : False,
        'apn' : "",
        'uuid' : "",
        'static_dns': False,
        'primary_dns' : None,
        'secondary_dns' : None,
    }

    def __init__(self, parent_model, profile=None, imsi=None,
                 device_callable=None):
        super(ProfileModel, self).__init__()

        self.bus = dbus.SystemBus()
        self.manager = manager
        self.profile = profile

        self.device_callable = device_callable
        self.parent_model = parent_model

        if self.profile and hasattr(self.profile, '__dbus_object_path__'):
            self.profile_path = self.profile.__dbus_object_path__

        if profile:
            self._load_profile(profile=profile)
        elif imsi:
            self._load_profile_from_imsi(imsi)
        else:
            raise ValueError("Bad arguments for ProfileModel.__init__")

        self.state = DISCONNECTED
        self.sm = [] # signal matches list
        self.connect_to_signals()

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

    def load_password(self):
        if self.profile:
            secrets = self.profile.secrets.get(ask=False)

            if secrets and 'gsm' in secrets and NM_PASSWD in secrets['gsm']:
                self.password = secrets['gsm'][NM_PASSWD]

    def _load_profile(self, profile):
        self.profile = profile
        settings = self.profile.get_settings()

        if 'ignore-auto-dns' not in settings['ipv4']:
            settings['ipv4']['ignore-auto-dns'] = False

        self._load_settings(settings)

    def _load_settings(self, settings):
        try:
            self.uuid = settings['connection']['uuid']
            self.name = settings['connection']['id']
            if 'username' in settings['gsm']:
                self.username = settings['gsm']['username']
            if 'password' in settings['gsm']:
                self.password = settings['gsm']['password']

            self.apn = settings['gsm']['apn']
            self.autoconnect = settings['connection']['autoconnect']
            # DNS
            self.static_dns = bool(settings['ipv4']['ignore-auto-dns'])
            if 'dns' in settings['ipv4']:
                dns = settings['ipv4']['dns']
                self.primary_dns = dns[0] if len(dns) else None
                self.secondary_dns = dns[1] if len(dns) > 1 else None

            if 'network-type' in settings['gsm']:
                self.network_type = settings['gsm']['network-type']

            if 'band' in settings['gsm']:
                self.band = settings['gsm']['band']

            if 'refuse-pap' in settings['ppp']:
                refuse_pap = settings['ppp']['refuse-pap']
            else:
                refuse_pap = False

            if 'refuse-chap' in settings['ppp']:
                refuse_chap = settings['ppp']['refuse-chap']
            else:
                refuse_chap = False

            if not refuse_pap and refuse_chap:
                self.auth = VM_NETWORK_AUTH_PAP
            elif not refuse_chap and refuse_pap:
                self.auth = VM_NETWORK_AUTH_CHAP
            else:
                self.auth = VM_NETWORK_AUTH_ANY

        except KeyError, e:
            logger.error("Missing required key '%s' in %s" % (settings, e))

    def _load_profile_from_imsi(self, imsi):
        logger.info("Loading profile for imsi %s" % str(imsi))
        try:
            props = self.manager.get_profile_options_from_imsi(imsi[:5])
            self._load_settings(props)
        except ProfileNotFoundError:
            self.uuid = str(uuid1())

    def save(self):
        props = {
            'connection' : { 'id' : self.name, 'type' : 'gsm',
                             'name' : 'connection', 'uuid' : self.uuid,
                             'autoconnect' : self.autoconnect },
            'gsm' : { 'band' : self.band, 'username' : self.username,
                      'number' : '*99#', 'network-type' : self.network_type,
                      'apn' : self.apn, 'name' : 'gsm' },
            'ppp' : { 'name' : 'ppp' },
            'serial' : { 'baud' : 115200, 'name' : 'serial' },
            'ipv4' : { 'addresses' : [], 'method': 'auto',
                       'ignore-auto-dns' : self.static_dns,
                       'name' : 'ipv4', 'routes' : [] }
        }

        if self.auth == VM_NETWORK_AUTH_PAP:     # Our GUI only cares about PAP/CHAP
            props['ppp']['refuse-pap'] = False
            props['ppp']['refuse-chap'] = True
        elif self.auth == VM_NETWORK_AUTH_CHAP:
            props['ppp']['refuse-pap'] = True
            props['ppp']['refuse-chap'] = False
        else:
            props['ppp']['refuse-pap'] = False   # just unset in case NM has set others
            props['ppp']['refuse-chap'] = False

        if not props['ipv4']['ignore-auto-dns']:
            props['ipv4']['dns'] = []
        else:
            dns = [i for i in [self.primary_dns, self.secondary_dns] if i]
            props['ipv4']['dns'] = map(convert, dns)

        props = patch_list_signature(props)

        if self.profile:
            self.manager.update_profile(self.profile, props)
            # store password associated to this connection
            secrets = {'gsm' : { NM_PASSWD : self.password}}
            self.profile.secrets.update(secrets, ask=True)

            logger.debug("Profile modified: %s" % self.profile)
        else:
            uuid = props['connection']['uuid']
            if self.parent_model.has_profile(uuid=uuid):
                msg = _('A profile with udi "%s" exists') % uuid
                raise RuntimeError(msg)

            sm = None # SignalMatch object
            def new_profile_cb(path):
                self.profile_path = path
                logger.debug("Profile added: %s" % self.profile_path)

                self.profile = self.manager.get_profile_by_uuid(uuid)
                secrets = {'gsm' : { NM_PASSWD : self.password}}
                self.profile.secrets.update(secrets, ask=True)

                self.parent_model.profile_added(self)

                sm.remove() # remove SignalMatch handler

            sm = self.bus.add_signal_receiver(new_profile_cb,
                                              "NewConnection",
                                              WADER_PROFILES_INTFACE)
            self.manager.add_profile(props)

        if self.state == DISCONNECTED and self.device_callable:
            # only perform this operations if we are disconnected and
            # a device is available
            device = self.device_callable()
            if not device:
                return

            if self.band is not None:
                device.SetBand(self.band, dbus_interface=NET_INTFACE,
                               reply_handler=lambda: True,
                               error_handler=logger.error)
            if self.network_type is not None:
                device.SetNetworkMode(self.network_type,
                                      dbus_interface=NET_INTFACE,
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


