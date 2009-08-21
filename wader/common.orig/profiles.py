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
Profile manager

I manage mobile profiles in the system
"""

__version__ = "$Rev: 1172 $"

import os

from twisted.python import log

import wader.common.exceptions as ex
from wader.common.consts import MOBILE_PROFILES
from wader.common.configbase import MobileProfile
from vmc.utils.utilities import touch

class ProfileUpdater:

    def update_profile(self):
        return self.do_update_profile()

class HTTPUpdater:
    def do_update_profile(self):
        from twisted.web.client import getPage
        url = "http://localhost/profile"
        return getPage(url)


class ProfileManager(object):
    """
    I manage mobile profiles
    """

    def __init__(self, path=MOBILE_PROFILES):
        super(ProfileManager, self).__init__()
        self.path = path
        self.device = None
        self.config = None

    def _configure_connection(self, profile):
        if not self.device or not self.device.sconn:
            log.err("%s: device not configured" % self.__class__.__name__)
            return

        log.msg("Configuring connection preferences for %s" % profile.name)

        preferred = profile.get('connection', 'connection')
        if not self.device.custom.conn_dict:
            log.msg("No conn_dict registered for device %s" % self.device)
            return
        try:
            conn_str = self.device.custom.conn_dict[preferred]
        except KeyError:
            args = (self.device, preferred)
            log.err("Device %s doesn't have key %s in its conn_dict" % args)
            return

        d = self.device.sconn.send_at(conn_str)
        d.addCallbacks(lambda _: _, lambda failure: log.err(failure))
        return d

    def _configure_profile(self, name, opts):
        if self.config.current_profile:
            # save current settings if a profile is active
            self.config.current_profile.write()

        profile = MobileProfile.from_dict(name, opts)
        self.load_profile(profile)

    def add_profile(self, profile):
        """
        Called when a new profile is added remotely (with an updater)
        """
        # where should be stored
        where = os.path.join(self.path, profile.name)
        if not os.path.exists(where):
            touch(where)

        profile.path = where
        profile._read_settings()
        profile.write()

    def create_profile(self, name, opts):
        """
        Creates a new mobile profile with C{name} from the C{opts} dict
        """
        return MobileProfile.from_dict(name, opts, path=self.path)

    def delete_profile(self, profile):
        """
        Deletes C{profile}

        @raise wader.common.exceptions.ProfileInUseError: If the profile to
        delete is the active profile
        @raise OSError: Raised if we don't have permissions to delete profile
        @raise IOError: Raised if profile doesn't exists or any other IO error
        """
        if self.config.current_profile == profile:
            raise ex.ProfileInUseError(profile)

        try:
            os.unlink(profile.path)
            profile = None
        except (IOError, OSError):
            raise

    def edit_profile(self, profile, opts):
        """
        Edits C{profile} from the C{opts} dict
        """
        self._configure_profile(profile.name, opts)

        if profile == self.config.current_profile:
            self._configure_connection(profile)

    def get_profile_list(self):
        """
        Returns all the stored profiles as a list of C{MobileProfile} objects
        """
        return [MobileProfile.from_name(name, self.path)
                            for name in os.listdir(self.path)]

    def load_profile(self, profile):
        """
        Loads C{profile}

        This just swaps the profiles in the config singleton and sets the
        new connection preferences
        """
        self.config.set_current_profile(profile)
        # send the at conn str
        self._configure_connection(profile)


_profile_manager = ProfileManager()

def get_profile_manager(device=None):
    """
    returns the ProfileManager singleton
    """
    # why not importing the singleton directly you might ask. All this hassle
    # is because we're living in a hotpluggin world where devices do not
    # longer exist
    from wader.common.config import config
    _profile_manager.config = config # XXX: Is this worthy?
    _profile_manager.device = device
    return _profile_manager
