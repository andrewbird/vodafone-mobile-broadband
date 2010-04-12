# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano and Nicholas Herriot
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

import os
import logging

from wader.vmc.consts import APP_SLUG_NAME
try:
    import pwd
    log_str = '/tmp/%s-%s.log' % (APP_SLUG_NAME, pwd.getpwuid(os.getuid())[0])
except ImportError:
    log_str = '/tmp/%s.log' % APP_SLUG_NAME

logger = logging.getLogger(APP_SLUG_NAME)

hdlr = logging.FileHandler(log_str)
FORMAT = '%(asctime)s %(levelname)s %(message)s'
formatter = logging.Formatter(FORMAT)

# OK lets just send all this to stdout if Mr User has been using CLI to start us off!
logging.basicConfig(format=FORMAT) # log sur console

# as usual we set our proper logger handler which should go to /tmp/bcm-<username>.log
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)
