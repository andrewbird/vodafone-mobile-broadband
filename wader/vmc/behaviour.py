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
GTK Behaviour

I synchronize the different state machines and set the appropiated callbacks
to the listeners
"""

from wader.common.behaviour import Behaviour
from wader.vmc.collaborator import GTKCollaboratorFactory
from vmc.contrib.epsilon.modal import mode

class GTKBehaviour(Behaviour):
    """
    Behaviour for GTK
    """
    collaborator = GTKCollaboratorFactory

    Init = Behaviour.Init
    NetReg = Behaviour.NetReg
    ImDone = Behaviour.ImDone

    def __init__(self, device, dialer, sm_callbacks, sm_errbacks, ctrl):
        super(GTKBehaviour, self).__init__(device, dialer,
                                           sm_callbacks, sm_errbacks)
        self.ctrl = ctrl

    class Auth(mode):
        """
        We override Behaviour.Auth because we want a reference of the view
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            authklass = self.device.custom.authklass
            authsm = authklass(self.device, self.collaborator, self.ctrl.view)
            d = authsm.start_auth()
            d.addCallback(lambda ignored: self._transition_to('Init'))
            d.addErrback(self.error_handler)
            self.current_sm = authsm
