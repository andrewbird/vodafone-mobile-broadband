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
Common stuff for all SonyEricsson's cards
"""

__version__ = "$Rev: 1172 $"

from wader.common.hardware.base import Customizer

SONYERICSSON_DICT = {
   'GPRSONLY' : 'AT$NWRAT=1,2',
   '3GONLY'   : 'AT$NWRAT=2,2',
   'GPRSPREF' : 'AT$NWRAT=0,2', # XXX
   '3GPREF'   : 'AT$NWRAT=0,2', # XXX
}

class SonyEricssonCustomizer(Customizer):
    async_regexp = None
    conn_dict = SONYERICSSON_DICT
