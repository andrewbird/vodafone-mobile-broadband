# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
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
"""Model for the diagnostics window"""

import os

from wader.vmc.uptime import get_uptime
from wader.vmc.models.base import BaseWrapperModel

class DiagnosticsModel(BaseWrapperModel):
    """Model for diagnostics window"""

    __properties__ = {}

    def __init__(self, wrapper):
        super(DiagnosticsModel, self).__init__(wrapper)

    def get_uptime(self):
        """Returns the uptime with uptime(1)'s format"""
        return get_uptime()

    def get_os_name(self):
        return os.uname()[0]

    def get_os_version(self):
        return os.uname()[2]

