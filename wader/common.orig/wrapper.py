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
Base Wrapper
"""
__version__ = "$Rev: 1172 $"

from wader.common.resource_manager import ResourceManager
from wader.common.exceptions import StateMachineNotReadyError

class BaseWrapper(object):
    """
    I wrap the access to resources in runtime

    I'm the entry point to interact with the bottom half of the app for third
    party developers
    """
    BEHAVIOUR_KLASS = None

    def __init__(self, device, noti_callbacks, sm_callbacks, sm_errbacks):
        super(BaseWrapper, self).__init__()
        self.device = device
        self.noti_callbacks = noti_callbacks
        self.sm_callbacks = sm_callbacks
        self.sm_errbacks = sm_errbacks
        self.behaviour = None
        self.rmanager = ResourceManager()
        self.setup()

    def setup(self):
        if self.device:
            self.device = self.rmanager.setup_device(self.device)
            args = [self, self.device, self.noti_callbacks]
            self.rmanager.setup_notifications_and_daemons(*args)

    def start_behaviour(self, *args):
        """
        Starts the Behaviour meta state machine.
        """
        dialer = self.rmanager.get_dialer()
        self.behaviour = self.BEHAVIOUR_KLASS(self.device, dialer,
                                              self.sm_callbacks,
                                              self.sm_errbacks, *args)
        self.rmanager.notimanager.add_listener(self.behaviour)
        self.behaviour.notification_manager = self.rmanager.notimanager
        self.behaviour.start()

    def get_current_sm(self):
        """
        Returns the current state machine in use

        @raise StateMachineNotReadyError: When the state machine is not ready.
        This is to prevent third-party plugin developers to perform operations
        when they shouldn't
        """
        if self.behaviour.initting:
            raise StateMachineNotReadyError

        return self.behaviour.current_sm

