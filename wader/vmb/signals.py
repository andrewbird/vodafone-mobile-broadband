# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

from wader.common import consts
from wader.vmb.translate import _

NET_MODE_SIGNALS = {
    consts.MM_NETWORK_MODE_UNKNOWN: _('No signal'),
    consts.MM_NETWORK_MODE_GPRS: _('GPRS'),
    consts.MM_NETWORK_MODE_EDGE: _('EDGE'),
    consts.MM_NETWORK_MODE_UMTS: _('UMTS'),
    consts.MM_NETWORK_MODE_2G_PREFERRED: _('2G preferred'),
    consts.MM_NETWORK_MODE_3G_PREFERRED: _('3G preferred'),
    consts.MM_NETWORK_MODE_2G_ONLY: _('2G only'),
    consts.MM_NETWORK_MODE_3G_ONLY: _('3G only'),
    consts.MM_NETWORK_MODE_HSDPA: _('HSDPA'),
    consts.MM_NETWORK_MODE_HSUPA: _('HSUPA'),
    consts.MM_NETWORK_MODE_HSPA: _('HSPA'),
}
