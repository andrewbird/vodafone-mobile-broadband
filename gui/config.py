# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
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
"""Configuration singleton for GTK"""

import gconf

from wader.common._gconf import GConfHelper
from wader.common.config import WaderConfig

from gui.consts import GCONF_BASE_DIR

DEFAULT_KEYS = ['profile', 'preferences', 'sms']


class CheckOldConfig(GConfHelper):

    def __init__(self):
        self.old = '/apps/bcm'
        self.new = GCONF_BASE_DIR
        super(CheckOldConfig, self).__init__()

    def check(self):
        if self.client.dir_exists(self.new):
            return

        if not self.client.dir_exists(self.old):
            return

        # We are going to move old into new data.
        dir_list = [self.old]
        for d in dir_list:
            dir_list.extend(self.client.all_dirs(d))

        for d in dir_list:
            entries = self.client.all_entries(d)

            for en in entries:
                key = en.get_key()
                new_key = self.new + key[len(self.old):]
                value = en.get_value()
                if value:
                    self.client.set(new_key, value)

        # We remove old directory.
        self.client.recursive_unset(self.old,
                                    gconf.UNSET_INCLUDING_SCHEMA_NAMES)


config = WaderConfig(keys=DEFAULT_KEYS, base_path=GCONF_BASE_DIR)
