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

__version__ = "$Rev: 1172 $"

from zope.interface import implements
from twisted.internet.defer import Deferred
from twisted.python import log

from wader.common.interfaces import ICollaborator, ICollaboratorFactory
from wader.vmc.controllers.pin import AskPINController, AskPUKController
from wader.vmc.views.pin import AskPINView, AskPUKView
from wader.vmc.models.base import SerialConnectionModel

try:
    from wader.vmc.keyring import KeyringClient
except ImportError:
    KeyringClient = None

class GTKCollaborator(object):
    """
    GTKCollaborator implements the C{ICollaborator} interface on GTK
    """
    implements(ICollaborator)

    def __init__(self, device, view):
        self.keyring = None
        self.auth_token = None
        self.device = device
        self.pin = None
        self.puk = None
        self.puk2 = None
        self.view = view

    def get_pin(self):
        """Returns a C{Deferred} that will be callbacked with the PIN"""
        def get_pin_from_user():
            deferred = Deferred()

            model = SerialConnectionModel(self.device)
            ctrl = AskPINController(model, deferred)
            view = AskPINView(ctrl)
            view.set_parent_view(self.view)
            view.show()

            return deferred

        if self.keyring:
            import gnomekeyring
            d = self.keyring.get_pin(self.device)

            def callback(devinfo):
                if devinfo:
                    pin, auth_token = devinfo
                    self.auth_token = auth_token
                    return pin

                return get_pin_from_user()
            def errback(failure):
                failure.trap(gnomekeyring.DeniedError)
                log.err(failure)
                return get_pin_from_user()

            d.addCallback(callback)
            d.addErrback(errback)
            return d
        else:
            return get_pin_from_user()

    def get_puk(self):
        """
        Returns a C{Deferred} that will be cbcked with a (puk, sim) tuple
        """
        deferred = Deferred()

        model = SerialConnectionModel(self.device)
        ctrl = AskPUKController(model, deferred)
        view = AskPUKView(ctrl)
        view.set_parent_view(self.view)
        view.set_puk_view()
        view.show()

        return deferred

    def get_puk2(self):
        """
        Returns a C{Deferred} that will be cbcked with a (puk2, sim) tuple
        """
        deferred = Deferred()

        model = SerialConnectionModel(self.device)
        ctrl = AskPUKController(model, deferred)
        view = AskPUKView(ctrl)
        view.set_parent_view(self.view)
        view.set_puk2_view()
        view.show()

        return deferred

class GTKCollaboratorFactory(object):
    implements(ICollaboratorFactory)

    @classmethod
    def get_collaborator(cls, device, *args, **kwds):
        instance = GTKCollaborator(device, *args, **kwds)
        if KeyringClient:
            try:
                instance.keyring = KeyringClient()
            except:
                instance.keyring = None

        return instance

