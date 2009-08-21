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
Base classes for Models
"""
__version__ = "$Rev: 1172 $"

from twisted.internet import defer
from twisted.python.failure import Failure

from wader.common.exceptions import IllegalOperationError
from wader.vmc import Model

class FakeFailedDeferred(object):
    """I impersonate a Deferred that will fail"""
    def __init__(self, value):
        self.value = value

    def __call__(self, *args, **kwds):
        return defer.fail(self.value)

class BaseWrapperModel(Model):
    """
    I provide all DevicePlugin's methods to my controller
    """
    def __init__(self, wrapper=None):
        super(BaseWrapperModel, self).__init__()
        self.wrapper = wrapper

    def get_device(self):
        if self.wrapper and self.wrapper.device:
            return self.wrapper.device

        return None

    def _dispatch(self, name):
        if hasattr(self.wrapper.device.sconn, name):
            return getattr(self.wrapper.device.sconn, name)
        else:
            raise AttributeError, name

    def __getattr__(self, name):
        """This acts a dispatcher around self.wrapper.device.sconn"""
        has_two_ports = self.get_device().has_two_ports()
        if has_two_ports or self.wrapper.behaviour.initting:
            # we have two ports, so its ok, or we are in the middle of the
            # startup with a single port device which is also ok
            return self._dispatch(name)
        else:
            # we have just one port and we are not starting up, check whether
            # we are connected or not
            if self.wrapper.behaviour.current_sm.mode == 'disconnected':
                # we just have one port but we are not connected, so its ok
                return self._dispatch(name)

            failure = Failure(IllegalOperationError(name))
            self.wrapper.behaviour.error_handler(failure)
            # we return a FakeDeferred that will automatically raise
            # IllegalOperationError
            return FakeFailedDeferred(failure)

    def get_sconn(self):
        """Returns a SerialConnection reference"""
        return self.wrapper.device.sconn

class SerialConnectionModel(Model):
    """
    I provide all DevicePlugin's methods to my controller
    """
    def __init__(self, device):
        super(SerialConnectionModel, self).__init__()
        self.device = device

    def __getattr__(self, name):
        if hasattr(self.wrapper.device.sconn, name):
            return getattr(self.device.sconn, name)
        else:
            raise AttributeError, name

