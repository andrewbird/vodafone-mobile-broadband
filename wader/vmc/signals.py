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

from wader.common.signals import (NO_SIGNAL, GPRS_SIGNAL, EDGE_SIGNAL,
                                  UMTS_SIGNAL, TWOG_PREF_SIGNAL,
                                  THREEG_PREF_SIGNAL, TWOG_ONLY_SIGNAL,
                                  THREEG_ONLY_SIGNAL, HSDPA_SIGNAL,
                                  HSUPA_SIGNAL, HSPA_SIGNAL)
from wader.vmc.translate import _

NET_MODE_SIGNALS = {
    NO_SIGNAL : _('No signal'),
    GPRS_SIGNAL : _('GPRS'),
    EDGE_SIGNAL : _('EDGE'),
    UMTS_SIGNAL : _('UMTS'),
    TWOG_PREF_SIGNAL : _('2G preferred'),
    THREEG_PREF_SIGNAL : _('3G preferred'),
    TWOG_ONLY_SIGNAL : _('2G only'),
    THREEG_ONLY_SIGNAL : _('3G only'),
    HSDPA_SIGNAL : _('HSDPA'),
    HSUPA_SIGNAL : _('HSUPA'),
    HSPA_SIGNAL : _('HSPA'),
}
