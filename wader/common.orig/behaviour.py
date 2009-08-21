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
Behaviour module

I synchronize the different state machines and set the appropiated callbacks
to the listeners
"""

__version__ = "$Rev: 1172 $"

from zope.interface import implements
from twisted.python import log

from wader.common.interfaces import INotificationListener
from vmc.contrib.epsilon.modal import Modal, mode

class Behaviour(Modal):
    """
    I am a meta-statemachine that synchronizes different state machines

    I will make sure that each state machine is called in order and will
    notify any registered errback about any possible error that might occur
    during the process. Basically this process can succeed, or fail because
    one of the following reasons:

     - AlreadyConnected: Raised when we are connected to Internet and user
     tries to connect to Internet
     - AlreadyConnecting: Raised when we are already connecting and user
     tries to connect to Internet again
     - CMEErrorSIMFailure: Raised when there is an error with the SIM, this
     could be just the case that the SIM is not inserted or that there is an
     error with the device's firmware.
     - CMEErrorSIMNotInserted: Raised when the SIM is not inserted
     - IllegalOperationError: Raised on single-port devices already connected
     to Internet (and thus its only port is already busy) and tries to issue
     an ATCmd.
     - NetworkRegistrationError: Raised when we couldn't find a network to
     register with during NetReg

    In adittion, you can connect to several signals that I will emit when I
    transition from one state machine to another:

     - AuthEnter: Executed when we enter into Auth state
     - AuthExit: Executed when we exit from Auth state
     - InitEnter: Executed when we enter into Init state
     - InitExit: Executed when we exit from Init state
     - NetRegEnter: Executed when we enter into NetReg state
     - NetRegExit: Executed when we exit from NetReg state
     - ImDoneEnter: Executed when we enter into ImDone state
     - ImDoneExit: Executed when we exit from ImDone state

    For example, GTKBehaviour connects to InitExit and shows the main
    UI, this is done because NetReg can be a potentially expensive (time)
    operation and its better to show the UI asap. GTKBehaviour also connects
    to NetRegExit to stop the throbber and show the result.
    """
    implements(INotificationListener)

    modeAttribute = 'mode'
    initialMode = 'Auth'
    # collaborator for AuthStateMachine
    collaborator = None

    def __init__(self, device, dialer, sm_callbacks, sm_errbacks):
        self.device = device
        self.dialer = dialer
        self.sm_callbacks = sm_callbacks
        self.sm_errbacks = sm_errbacks
        self.notification_manager = None
        self.current_sm = None
        self.initting = True

    def __repr__(self):
        return self.__class__.__name__

    def _try_execute_callback(self, cb_name, *args, **kwds):
        if cb_name in self.sm_callbacks:
            handler = self.sm_callbacks[cb_name]
            if handler: # could be None
                try:
                    handler(*args, **kwds)
                except:
                    log.err()

    def register_callback_for_signal(self, signal, callback):
        """Register C{callback} for C{signal}"""
        self.sm_callbacks[signal] = callback

    def register_errback_for_signal(self, signal, errback):
        """Register C{errback} for C{signal}"""
        self.sm_errbacks[signal] = errback

    def on_notification_received(self, notification):
        """
        Called whenever a notification is received

        I will notify the current SM about it
        """
        if self.current_sm:
            # notify the current SM about the notification
            self.current_sm.on_notification_received(notification)

    def _transition_to(self, _mode, *args, **kwds):
        """
        Transitions to state C{mode}

        I will try to execute my registered exit and enter callbacks with
        *args and **kwds
        """
        self._try_execute_callback(self.mode + 'Exit', *args, **kwds)
        stuff = (self, self.mode, _mode)
        log.msg("%s: LEAVING %s AND ENTERING INTO %s" % stuff)
        self.transitionTo(_mode)
        self._try_execute_callback(self.mode + 'Enter', *args, **kwds)
        self.do_next()

    def error_handler(self, failure):
        """
        Executed whenever an error occurs on one of my sub-state machines

        If I receive a FooError, I will try to execute the registered errback
        for FooError.
        """
        # we get the exception class name
        exception_name = failure.type.__name__
        # do we have an errback registered for this exception?
        if exception_name in self.sm_errbacks:
            handler = self.sm_errbacks[exception_name]
            if handler:
                # if defined execute it
                try:
                    handler(failure)
                except:
                    log.err()

    def start(self):
        self.do_next()

    class Auth(mode):
        """
        Auth is the first state, here we will authenticate against the device
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            authklass = self.device.custom.authklass
            authsm = authklass(self.device, self.collaborator)
            d = authsm.start_auth()
            def on_auth_ok_cb(ignored):
                self._transition_to('Init')
                self.do_next()

            d.addCallback(on_auth_ok_cb)
            d.addErrback(self.error_handler)
            self.current_sm = authsm

    class Init(mode):
        """
        Init is the second state, after successfully authenticating with
        the device, we will set up the rest of parameters that needed an
        authentication beforehand (encoding, SMS notifications, SIM size, ...)
        """

        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            d = self.device.initialize()
            d.addCallback(lambda ign: self._transition_to('NetReg'))
            d.addErrback(log.err)
            d.addErrback(self.error_handler)

    class NetReg(mode):
        """
        NetReg tries to register with the network and do the right thing.
        """

        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            netregklass = self.device.custom.netrklass
            netregsm = netregklass(self.device)
            d = netregsm.start_netreg()
            d.addCallback(lambda ninfo: self._transition_to('ImDone'))
            d.addErrback(self.error_handler)
            self.current_sm = netregsm
            self.notification_manager.start()

    class ImDone(mode):
        """
        final state
        """

        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            # configure device according to profile settings
            # set current_sm to the connection state machine
            connklass = self.device.custom.connklass
            connsm = connklass(self.dialer)
            self.current_sm = connsm
            self.current_sm.add_listener(self.notification_manager)

            from wader.common.config import config
            if config.current_profile:
                # this can be None if we just created a profile
                preferred = config.current_profile.get('connection',
                                                       'connection')
                if not self.device.custom.conn_dict:
                    msg = "No conn_dict registered for device %s"
                    log.msg(msg % self.device)
                    return
                try:
                    conn_str = self.device.custom.conn_dict[preferred]
                except KeyError:
                    msg = "Device %s doesn't have key %s in its conn_dict"
                    log.err(msg % (self.device, preferred))
                    return

                d = self.device.sconn.send_at(conn_str)
                d.addCallback(lambda _: _)
                d.addErrback(self.error_handler)

            self.initting = False
