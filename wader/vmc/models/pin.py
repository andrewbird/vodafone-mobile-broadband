# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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
"""Model for the PIN windows"""

import os

from wader.vmc.models.base import BaseWrapperModel
from wader.common.consts import CRD_INTFACE, NET_INTFACE, MDM_INTFACE


class PinModel(BaseWrapperModel):
    """Model for PIN window"""

    def __init__(self, device):
        super(PinModel, self).__init__(device)

    def change_pin(self, oldpin, newpin):
        try:
            self.device.ChangePin(oldpin, newpin, dbus_interface=CRD_INTFACE)
        except:
            return False
        else:
            return True

    def enable_pin(self, enable, pin):
        try:
            self.device.EnablePin(pin, enable, dbus_interface=CRD_INTFACE)
        except:
            return False
        else:
            return True

    def pin_is_enabled(self):
        return True
