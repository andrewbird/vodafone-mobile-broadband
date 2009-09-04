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

import dbus
import gobject
from gtkmvc import Model, ListStoreModel

from wader.vmc.models.profile import ProfileModel
from wader.vmc.logger import logger
from wader.vmc.translate import _
from wader.vmc.profiles import manager
from wader.vmc.config import config
import wader.common.exceptions as ex

PREF_TABS = ["PROFILES"]

class ProfilesModel(ListStoreModel):

    def __init__(self):
        super(ProfilesModel, self).__init__(gobject.TYPE_BOOLEAN,
                                            gobject.TYPE_PYOBJECT)
        self.active_iter = None
        self.conf = config

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
            raise ex.ProfileNotFoundError("Profile %s not found" % uuid)

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


class PreferencesModel(Model):

    __properties__ = {
        'current_tab': PREF_TABS[0],
        'default_profile': None,
        'warn_limit' : False,
        'transfer_limit' : -1
    }

    def __init__(self, parent, device_callable):
        super(PreferencesModel, self).__init__()
        self.bus = dbus.SystemBus()
        self.manager = manager
        self.conf = config
        self.parent = parent
        self.device_callable = device_callable
        self.profiles_model = ProfilesModel()

    def get_profiles_model(self, device_callable):
        uuid = self.conf.get('profile', 'uuid')

        for _uuid, profile in self.get_profiles(device_callable).iteritems():
            if not self.profiles_model.has_profile(uuid=_uuid):
                default = True if uuid and uuid == _uuid else False
                self.profiles_model.add_profile(profile, default)

        return self.profiles_model

    def get_profiles(self, device_callable):
        ret = {}
        for profile in self.manager.get_profiles():
            settings = profile.get_settings()
            if 'ppp' in settings:
                uuid = settings['connection']['uuid']
                ret[uuid] = ProfileModel(self, profile=profile,
                                         device_callable=device_callable)
        return ret

    def load(self):
        self.warn_limit = self.conf.get('statistics', 'warn_limit', True)
        self.transfer_limit = self.conf.get('statistics',
                                            'transfer_limit', 50.0)

    def save(self):
        self.conf.set('statistics', 'warn_limit', self.warn_limit)
        self.conf.set('statistics', 'transfer_limit', self.transfer_limit)

    def reset_statistics(self):
        logger.info('Resetting total bytes')
        self.parent.total_bytes = 0
        self.conf.set('statistics', 'total_bytes', 0)

    def profile_added(self, profile):
        self.profiles_model.add_profile(profile)

