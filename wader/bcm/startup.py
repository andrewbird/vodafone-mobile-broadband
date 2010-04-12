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
"""Startup helpers for GTK"""

import os

import wader.bcm.consts as consts


def create_skeleton_and_return():
    try:
        os.makedirs(consts.WADER_HOME, 0700)
    except OSError:
        pass

    try:
        os.mkdir(consts.DB_DIR, 0700)
    except OSError:
        pass

    if os.path.exists(consts.NETWORKS_DB):
        # remove old way of populating networks database
        os.unlink(consts.NETWORKS_DB)
