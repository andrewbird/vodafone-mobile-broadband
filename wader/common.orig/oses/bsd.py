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
BSD-based OS plugins
"""

__version__ = "$Rev: 1172 $"

from wader.common.oses.unix import UnixPlugin

class FreeBSDPlugin(UnixPlugin):
    """Plugin for FreeBSD"""
    os_name = None
    os_version = None

    def __init__(self):
        super(FreeBSDPlugin, self).__init__()

    def is_valid(self):
        try:
            import freebsd
        except ImportError:
            return False

        return freebsd.getosreldate() >= self.os_version

    def check_permissions(self):
        return []

class OpenBSDPlugin(UnixPlugin):
    """Plugin for OpenBSD"""
    os_name = None
    os_version = None

    def __init__(self):
        super(OpenBSDPlugin, self).__init__()

    def is_valid(self):
        try:
            import openbsd
        except ImportError:
            return False

        return openbsd.getosreldate() >= self.os_version

    def check_permissions(self):
        return []

