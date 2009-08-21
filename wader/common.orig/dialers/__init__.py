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
Dialers for VMC
"""

__version__ = "$Rev: 1172 $"

import os

import wader.common.consts as consts
from wader.common.encoding import _
from vmc.utils.utilities import dict_reverter

AUTH_OPTS_LIST = [
    unicode(_('Default'), 'utf8'),
    unicode(_('PAP'), 'utf8'),
    unicode(_('CHAP'), 'utf8'),
]

AUTH_OPTS_DICT = {
   unicode(_('Default'), 'utf8') : 'default',
   unicode(_('PAP'), 'utf8') : 'PAP',
   unicode(_('CHAP'), 'utf8') : 'CHAP',
}

AUTH_OPTS_DICT_REV = dict_reverter(AUTH_OPTS_DICT)


def get_profiles_list():
    """
    Returns the names of the profiles at ~/.vmc2/dialer-profiles
    """
    return os.listdir(consts.DIALER_PROFILES)

