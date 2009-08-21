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
OS Abstraction Layer

OS provides an abstraction layer so path differences between OSes/distros
won't affect VMCCdfL
"""
__version__ = "$Rev: 1172 $"

from wader.common.exceptions import OSNotRegisteredError

def get_os_object():
    """
    Returns a C{BaseDistribution} object corresponding to current OS used

    @raise OSNotRegisteredError: If the OS is not supported.
    """
    from wader.common.plugin import PluginManager
    from wader.common.interfaces import IOSPlugin

    for osplugin in PluginManager.get_plugins(IOSPlugin):
        if osplugin.is_valid():
            osplugin.initialize()
            return osplugin

    raise OSNotRegisteredError

osobj = get_os_object()
