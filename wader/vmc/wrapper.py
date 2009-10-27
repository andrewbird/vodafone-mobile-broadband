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
GTK Wrapper
"""

from wader.common.wrapper import BaseWrapper
from wader.vmc.behaviour import GTKBehaviour

class GTKWrapper(BaseWrapper):
    """
    Wrapper for GTK+
    """
    BEHAVIOUR_KLASS = GTKBehaviour

    def __init__(self, device, noti_callbacks,
                 sm_callbacks, sm_errbacks, ctrl):
        self.ctrl = ctrl
        super(GTKWrapper, self).__init__(device, noti_callbacks, sm_callbacks,
                                         sm_errbacks)

    def setup(self):
        self.ctrl.model.wrapper = self

        if self.device:
            self.device = self.rmanager.setup_device(self.device)
            args = [self, self.device, self.noti_callbacks]
            self.ctrl.model.notimanager, self.ctrl.model.daemons = \
                    self.rmanager.setup_notifications_and_daemons(*args)
