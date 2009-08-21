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
Network registration state machine

I am a relatively complex (not complicated) network registration agent that
will always (try) to do TheRightThing(tm).
"""

__version__ = "$Rev: 1172 $"

from twisted.python import log
from twisted.internet import defer, reactor
from time import time

import wader.common.exceptions as ex
import wader.common.notifications as N
from wader.common.statem.base import StateMachineMixin
from vmc.contrib.epsilon.modal import mode, Modal

REGISTER_TIMEOUT = 60
REGISTER_INTERVAL = 8
MAX_FAILURES = 3

class NetworkRegStateMachine(StateMachineMixin, Modal):
    """
    I register with the network
    """
    modeAttribute = 'mode'
    initialMode = 'check_registered'

    def __init__(self, device):
        log.msg("Instantiating %s ...." % self.__class__.__name__)
        # reference to the device
        self.device = device
        # we cache our imsi prefix
        self.prefix = None
        # this is the netobj that we must register with
        self.netobj = None
        # used to cache network ids on a foreign country
        self.cached_roaming_ids = None
        # Absolute timeout for registration
        self.register_timeout = 0
        # wait_for_register IDelayedCall
        self.cID = None
        # response's deferred
        self.deferred = defer.Deferred()
        # num failures
        self.num_failures = 0

    def __repr__(self):
        return self.__class__.__name__

    def cancel_poll(self):
        if self.cID:
            self.cID.cancel()
            self.cID = None

    def on_notification_received(self, notification):
        super(NetworkRegStateMachine,
              self).on_notification_received(notification)

        if (self.mode == 'wait_to_register'
                and isinstance(notification, N.NetworkRegNotification)):
            # we are only interested on NetworkRegNotifications and we
            # must be on the wait_to_register state

            # XXX: We could also detect whether we've been unregistered from
            # the network if, say, the local MSC is down or whatever
            status = notification.args 
            if status == 1:
                # we are finally registered
                self.cancel_poll()
                #self.transitionTo('obtain_netinfo')
                self.transitionTo('registration_finished')
                self.do_next()

            elif status == 2:
                # still searching for a network, give it some time
                pass

            elif status == 3:
                # registration rejected
                self.cancel_poll()
                self.transitionTo('registration_failed')
                # send exception back to behaviour
                errmsg = 'Registration rejected +CREG: 3'
                self.do_next(ex.NetworkRegistrationError(errmsg))

            elif status == 4:
                # registration rejected
                self.cancel_poll()
                self.transitionTo('registration_failed')
                # send exception back to behaviour
                errmsg = 'Registration rejected by unknown reasons, +CREG: 4'
                self.do_next(ex.NetworkRegistrationError(errmsg))

            elif status == 5:
                # registered on foreign network (roaming)
                # our SIM is smart enough to discover itself which network
                # should register with
                self.cancel_poll()
                self.transitionTo('registration_finished')
                self.do_next()

    def check_if_i_registered_with_any_net(self):
        """
        Executed when poll interval has expired while on wait_to_register

        some cards do not like to notify you that they're registered
        """
        # Like NovatelWireless' Ovation MC950D
        def get_netreg_status_cb(netregstatus):
            mode, status = netregstatus

            if status in [1, 5]: # registered in our home network or roaming
                # we are already registered
                self.transitionTo('registration_finished')
                self.do_next()
            elif status in [2, 4] and (time() < self.register_timeout):
                # keep polling for now
                self.transitionTo('wait_to_register')
                self.do_next()
            else:
                self.transitionTo('registration_failed')
                msg = 'Timeout while waiting for registering with the network'
                self.do_next(ex.NetworkRegistrationError(msg))

        self.cID = None # invalidate since we were called

        d = self.device.sconn.get_netreg_status()
        d.addCallback(get_netreg_status_cb)

    def _process_netreg_status(self, netregstatus):
        """
        Process get_netreg_status response from "check_registered" mode
        """
        # +CREG: 0,0 - Not registered and not scanning for a GSM network
        # +CREG: 0,1 - Registered on the "HOME" network of the SIM
        # +CREG: 0,2 - Not registered but is scanning for a GSM network
        # +CREG: 0,3 - Registration is denied (Manual attempt failed)
        # +CREG: 0,4 - Offically Unknown, but seen with Ericsson modules during radio power up
        # +CREG: 0,5 - Registered on to another network (roaming).

        mode, status = netregstatus
        if status == 0:
            # Not registered and not scanning for a GSM network. That means
            # that either there's a major problem with the local network or
            # that we're abroad and we have and old SIM with no CPOL list or
            # our SIM is new and doesn't have a clue which network should
            # register with
            self.device.sconn.set_netreg_notification(1)
            self.transitionTo('wait_to_register')
            self.do_next()

        elif status == 1:
            # we are already registered
            self.transitionTo('registration_finished')
            self.do_next()

        elif status == 2:
            # ask again in a while
            if mode == 0:
                self.device.sconn.set_netreg_notification(1)
            self.transitionTo('wait_to_register')
            self.do_next()

        elif status == 3:
            self.transitionTo('registration_failed')
            # send exception back to behaviour
            errmsg = 'Registration failed CREG=0,3'
            self.do_next(ex.NetworkRegistrationError(errmsg))

        elif status == 4:
            # ask again in a while
            if mode == 0:
                self.device.sconn.set_netreg_notification(1)
            self.transitionTo('wait_to_register')
            self.do_next()

        elif status == 5:
            # we are registered and roaming is enabled
            self.transitionTo('registration_finished')
            self.do_next()

    def _process_imsi_cb(self, imsi_prefix):
        self.prefix = imsi_prefix
        self.device.sconn.set_network_info_format()
        # is it really necessary to register with the network?
        def network_info_cb(netinfo):
            netname, conn_type = netinfo
            if isinstance(netname, int):
                if netname == imsi_prefix:
                    # we are already registered with our network
                    self.transitionTo('registration_finished')
                else:
                    self.transitionTo('search_operators')
            else:
                assert isinstance(netname, str)
                # we already setup AT+COPS=0,2 but the device insists in
                # replying in alphanumeric format, we'll accept it for now
                # this happens with Option's Nozomi at least
                self.transitionTo('registration_finished')

            # transition to registration_finished or search_operators
            self.do_next()

        def network_info_eb(failure):
            failure.trap(ex.NetworkTemporalyUnavailableError)
            self.num_failures += 1
            if self.num_failures >= MAX_FAILURES:
                self.transitionTo('registration_failed')
                self.do_next(ex.NetworkTemporalyUnavailableError)
            else:
                # repeat till we succeed
                self.do_next()

        d = self.device.sconn.get_network_info(process=False)
        d.addCallback(network_info_cb)
        d.addErrback(network_info_eb)

    def get_net_names_cb(self, net_objs):
        names = [obj for obj in net_objs if obj.netid == self.prefix]
        try:
            self.netobj = names[0]
            self.transitionTo('register_with_operator')
        except IndexError:
            # we couldn't find a netid to register with, it seems that we're
            # on a foreign country
            self.cached_roaming_ids = net_objs
            self.transitionTo('international_roaming')

        self.do_next()

    def process_roaming_ids(self, net_objs):
        for obj in net_objs:
            if obj in self.cached_roaming_ids:
                self.netobj = obj
                break

        if self.netobj:
            self.transitionTo('register_with_operator')
        else:
            # XXX: Automatic configuration system here would lookup the netid
            self.deferred.errback(True)

        self.do_next()

    def start_netreg(self):
        """
        Starts the network registration process

        @rtype: C{defer.Deferred}

        @raise ex.NetworkTemporalyUnavailableError: If AT+COPS keeps replying
        +COPS: 0 (No network)
        @raise ex.NetworkRegistrationError: Raised when we can't register with
        the network we want to register to
        """
        self.do_next()
        return self.deferred

    # states
    class check_registered(mode):
        """
        Check if we are currently registered with the network
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: check_registered" % self)
            # calc the absolute timeout for the operation
            self.register_timeout = time() + REGISTER_TIMEOUT
            # Set encoding to IRA as some devices return less information
            # while in UCS2
            self.device.sconn.set_charset("IRA")
            d = self.device.sconn.get_netreg_status()
            d.addCallback(self._process_netreg_status)
            d.addErrback(log.err)

    class wait_to_register(mode):
        """
        Wait till we are registered with the network, if after 
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: wait_to_register" % self)
            if not self.cID:
                # we setup a timer to poll for registration status in case
                # we don't receive the unsolicited notification
                self.cID = reactor.callLater(REGISTER_INTERVAL,
                                    self.check_if_i_registered_with_any_net)

    class obtain_netinfo(mode):
        """
        Find out what network are we registered with
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: obtain_netinfo" % self)
            d = self.device.sconn.get_imsi()
            d.addCallback(lambda response: int(response[:5])) # FIXME IMSI 5 digit restriction
            d.addCallback(self._process_imsi_cb)

    class search_operators(mode):
        """
        Find out what operators are around
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: search_operators" % self)
            d = self.device.sconn.get_network_names()
            d.addCallback(self.get_net_names_cb)

    class international_roaming(mode):
        """
        We couldn't find an operator to connect with, we're abroad. Check
        my CPOL list and if I can't find there an ID to register with, use
        the configuration system.
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: international_roaming" % self)
            d = self.device.sconn.get_roaming_ids()
            d.addCallback(self.process_roaming_ids)

    class register_with_operator(mode):
        """
        We've found the operator that we must register with
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: register_with_operator" % self)
            d = self.device.sconn.register_with_network(self.netobj.netid)
            def register_callback(ignored):
                self.transitionTo('registration_finished')
                self.do_next()

            def register_errback(failure):
                self.transitionTo('registration_failed')
                self.do_next(failure)

            d.addCallback(register_callback)

    class registration_finished(mode):
        """
        Find out what network are we registered with
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: NEW MODE: registration_finished" % self)
            # set encoding back to UCS2
            self.device.sconn.set_charset("UCS2")
            d = self.device.sconn.get_network_info()
            d.addCallback(lambda netinfo: self.deferred.callback(netinfo))

    class registration_failed(mode):
        """
        Registration failed, send
        """
        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self, _exception=None):
            log.msg("%s: NEW MODE: registration_failed" % self)
            # set encoding back to UCS2
            self.device.sconn.set_charset("UCS2")
            if not _exception:
                self.deferred.errback(ex.NetworkRegistrationError())
            else:
                self.deferred.errback(_exception)

