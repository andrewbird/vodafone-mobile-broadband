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
Config related classes and methods

The object L{config} is a singleton instance of VMCConfig. The overhead of
opening the object, performing a get/set and closing it was too much.
That's why its a singleton. The instance is closed during
L{wader.common.shutdown.shutdown_core()}. You must be careful as importing it
too early during the first run of the program, could cause that the config
file is not created yet and you'd get a messy traceback. Delay its import as
much as possible in modules used at startup or that are imported at startup.
"""
__version__ = "$Rev: 1172 $"

from ConfigParser import ConfigParser
import os
import pickle
import shutil
import tempfile

from wader.common.consts import MOBILE_PROFILES, CACHED_DEVICES, PROFTEMPLATE

class VMCConfigBase(object):
    """I manage VMC's configuration"""

    def __init__(self, path):
        self.path = path
        self.fileobj = None
        self.conf = ConfigParser()
        self._read_settings()

    def _read_settings(self):
        self.fileobj = open(self.path)
        self.conf.readfp(self.fileobj)

    def get(self, section, option):
        return self.conf.get(section, option)

    def getboolean(self, section, option):
        return self.conf.getboolean(section, option)

    def getint(self, section, option):
        return self.conf.getint(section, option)

    def write(self):
        """
        Saves the current configuration to L{self.path}
        """
        return self.conf.write(open(self.path, 'w'))

    def set(self, section, option, value):
        return self.conf.set(section, option, value)

    def setboolean(self, section, option, val):
        if isinstance(val, str):
            if val not in ['yes', 'no']:
                raise AttributeError("Invalid boolean value %s" % val)

            value = val
        else:
            if not isinstance(val, bool):
                raise AttributeError("What I'm supposed to do with %?" % val)

            value = val and 'yes' or 'no'

        return self.conf.set(section, option, value)

    def serialize(self, path=None):
        """
        Returns the path where the profile has been serialized

        The caller is responsible of removing the file
        """
        if not path:
            path = tempfile.mkstemp('', 'VMCConfig', '/tmp', text=True)[1]
        fobj = open(path, 'w')
        pickle.dump(self, fobj, pickle.HIGHEST_PROTOCOL)
        fobj.close()
        return path

    def close(self):
        self.fileobj.close()
        self.conf = None


class MobileProfile(VMCConfigBase):
    """
    I am a mobile profile
    """

    def __init__(self, path):
        super(MobileProfile, self).__init__(path)
        self.name = os.path.basename(path)

    def __repr__(self):
        return '<MobileProfile %s at %s>' % (self.name, self.path)

    def __eq__(self, other):
        if not isinstance(other, MobileProfile):
            raise ValueError("Imposible to compare me with %s" % other)
        return self.name == other.name

    def __ne__(self, other):
        if not isinstance(other, MobileProfile):
            raise ValueError("Imposible to compare me with %s" % other)
        return not (self.name == other.name)

    @classmethod
    def from_name(cls, name, path=MOBILE_PROFILES):
        profpath = os.path.join(path, name)
        if not os.path.exists(profpath):
            shutil.copy(PROFTEMPLATE, profpath)

        return cls(profpath)

    @classmethod
    def from_dict(cls, name, opts, path=MOBILE_PROFILES):
        profile = MobileProfile.from_name(name, path)

        profile.set('connection', 'username', opts['username'])
        profile.set('connection', 'password', opts['password'])
        profile.set('connection', 'apn', opts['apn'])
        profile.set('connection', 'connection', opts['connection'])
        profile.set('connection', 'dialer_profile', opts['dialer_profile'])
        profile.setboolean('connection', 'staticdns', opts['staticdns'])
        profile.set('connection', 'dns1', opts['dns1'])
        profile.set('connection', 'dns2', opts['dns2'])

        profile.write()
        return profile
