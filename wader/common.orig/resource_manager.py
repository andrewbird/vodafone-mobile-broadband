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
I manage the resources
"""
__version__ = "$Rev: 1172 $"

from wader.common.oal import osobj
from wader.common.daemon import VMCDaemonFactory
from wader.common.notifications import NotificationsManager
from wader.common.startup import attach_serial_protocol

from twisted.python import log

class ResourceManager(object):
    """
    I'm the entry point to access system resources at runtime
    """
    def __init__(self):
        super(ResourceManager, self).__init__()
        self.notimanager = None
        self.daemons = None

    def setup_device(self, device):
        if device.sconn:
            log.msg("%s: device.sconn already setup" % self)
            # device might be already configured by configuration dialog
            return device

        return attach_serial_protocol(device)

    def setup_notifications_and_daemons(self, wrapper, device, noti_cbs):
        self.notimanager = NotificationsManager(wrapper, device, noti_cbs)
        # get the daemon collection for this device
        args = [device, self.notimanager]
        self.daemons = VMCDaemonFactory.build_daemon_collection(*args)
        # start daemons only after exit from auth stage
        # self.daemons.start_daemons()
        return self.notimanager, self.daemons

    def start_daemons(self):
        self.daemons.start_daemons()

    def get_dialer(self):
        return osobj.dialer
