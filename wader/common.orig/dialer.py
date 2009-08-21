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
Dialer module abstracts the differences between dialers on different OSes
"""
__version__ = "$Rev: 1172 $"

from zope.interface import implements

from wader.common.interfaces import IDialer

class DialerConf(object):
    """
    I contain all the necessary information to connect to Internet
    """
    apn_host = None
    username = None
    password = None
    staticdns = None
    dialer_profile = None
    dns1 = None
    dns2 = None
    port = None

    def __init__(self):
        super(DialerConf, self).__init__()

    def __repr__(self):
        msg = '<DialerConf instance at 0x%x apn: %s, user: %s, passwd: %s>'
        args = (id(self), self.apn_host, self.username, self.password)
        return msg % args

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_profile(cls, profile):
        """
        Returns a new DialerConf instance from C{profile}

        @type profile: C{wader.common.configbase.VMCConfigBase} instance 
        """
        cls.apn_host = profile.get('connection', 'apn')
        cls.username = profile.get('connection', 'username')
        cls.password = profile.get('connection', 'password')
        cls.staticdns = profile.getboolean('connection', 'staticdns')
        cls.dialer_profile = profile.get('connection', 'dialer_profile')

        if cls.staticdns:
            cls.dns1 = profile.get('connection', 'dns1')
            cls.dns2 = profile.get('connection', 'dns2')

        return cls

    @classmethod
    def from_config_dict(cls, conf):
        """
        Returns a new DialerConf instance from the C{conf} dict
        """
        # used for cli-client
        cls.apn_host = conf['apn']
        cls.username = conf['username']
        cls.password = conf['password']
        cls.dialer_profile = conf['dialer_profile']
        cls.staticdns = conf['staticdns']
        cls.dns1 = conf['dns']
        cls.dns2 = conf['dns']
        return cls


class Dialer(object):
    """
    Base Dialer class

    Override me for new OSes
    """
    implements(IDialer)
    config = None
    protocol = None

    def __init__(self):
        super(Dialer, self).__init__()

    def configure(self, config, device):
        """
        Configures C{device} with C{config}

        This method should perform any necessary actions to connect to
        Internet like generating configuration files, modifying any necessary
        files, etc.
        """
        raise NotImplementedError()

    def connect(self):
        """
        Connects to Internet

        Returns a C{Deferred} that will be callbacked when connected

        @raise wader.common.exceptions.AlreadyConnected:
        @raise wader.common.exceptions.AlreadyConnecting:
        """
        raise NotImplementedError()

    def disconnect(self):
        """
        Disconnects from Internet

        Returns a C{Deferred} that will be callbacked when disconnected
        """
        raise NotImplementedError()

    def _generate_config(self):
        raise NotImplementedError()

