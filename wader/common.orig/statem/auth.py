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
Authentication state machine
"""

__version__ = "$Rev: 1172 $"

from twisted.internet import reactor, defer
from twisted.python import log

from vmc.contrib.epsilon.modal import mode, Modal
import wader.common.exceptions as ex
from wader.common.statem.base import StateMachineMixin

DELAY = 15
SIM_FAIL_DELAY = 15
MAX_NUM_SIM_ERRORS = 3
MAX_NUM_SIM_BUSY = 5


class AuthStateMachine(StateMachineMixin, Modal):
    """
    I authenticate against a device
    """
    modeAttribute = 'mode'
    initialMode = 'get_pin_status'

    def __init__(self, device, factory, *args, **kwds):
        self.device = device
        self.collaborator = factory.get_collaborator(device, *args, **kwds)
        self.deferred = defer.Deferred()
        # it will be set to True if AT+CPIN? == +CPIN: READY
        self.auth_was_ready = False
        self.num_sim_errors = 0
        self.num_sim_busy = 0
        self.delay = DELAY
        log.msg("Instantiating %s ..." % self.__class__.__name__)

    def __repr__(self):
        return self.__class__.__name__

    def _notify_auth_ok(self):
        """
        Wrapper to notify success, subclass me
        """
        if self.auth_was_ready:
            # If authentication was ready
            self.deferred.callback(True)
        else:
            args = (self.__class__.__name__, self.delay)
            log.msg("%s: Giving %d seconds to settle the SIM card..." % args)
            reactor.callLater(self.delay, self.deferred.callback, True)

    # keyring stuff
    def notify_auth_ok(self):
        """Called when authentication was successful"""
        if not self.auth_was_ready:
            # we can only register a keyring if we authenticated beforehand
            from wader.common.config import config
            manage_kring = config.getboolean('preferences', 'manage_keyring')
            if manage_kring and self.collaborator.keyring:
                register = self.collaborator.keyring.register
                d = register(self.device, self.collaborator.pin)
                d.addCallback(lambda _: self._notify_auth_ok())
                return

        # if auth was ready or there's no keyring then notify auth ok directly
        self._notify_auth_ok()

    def notify_auth_failure(self, failure):
        """Called when we faced a failure"""
        self.deferred.errback(failure)

    # collaborator callbacks
    def _get_pin_cb(self, pin):
        """collaborator.get_pin() callback"""
        self.collaborator.pin = pin
        self.transitionTo('pin_needed_status')
        self.do_next()

    def _get_puk_cb(self, auth):
        """collaborator.get_puk() callback"""
        self.collaborator.puk, self.collaborator.pin = auth
        self.transitionTo('puk_needed_status')
        self.do_next()

    def _get_puk2_cb(self, auth):
        """collaborator.get_puk2() callback"""
        self.collaborator.puk2, self.collaborator.pin = auth
        self.transitionTo('puk2_needed_status')
        self.do_next()

    # states callbacks
    def check_pin_cb(self, resp):
        """Callbacked with check_pin's result"""
        if resp == 'READY':
            self.auth_was_ready = True
            self.notify_auth_ok()

        elif resp == 'SIM PIN':
            d = self.collaborator.get_pin()
            d.addCallback(self._get_pin_cb)

        elif resp == 'SIM PUK':
            d = self.collaborator.get_puk()
            d.addCallback(self._get_puk_cb)

        elif resp == 'SIM PUK2':
            d = self.collaborator.get_puk2()
            d.addCallback(self._get_puk2_cb)

    def get_pin_status_cb(self, enabled):
        if int(enabled):
            d = self.collaborator.get_pin()
            d.addCallback(self._get_pin_cb)
            d.addErrback(log.err)
        else:
            self.notify_auth_ok()

    def incorrect_pin_eb(self, failure):
        """Executed when PIN is incorrect"""
        failure.trap(ex.CMEErrorIncorrectPassword, ex.ATError)
        if self.collaborator.auth_token:
            auth_token = self.collaborator.auth_token
            log.err("DELETING BAD TOKEN %d" % auth_token)
            self.collaborator.keyring.delete(auth_token)
            self.collaborator.auth_token = None

        self.collaborator.get_pin().addCallback(self._get_pin_cb)

    def incorrect_puk_eb(self, failure):
        """Executed when the PUK is incorrect"""
        failure.trap(ex.CMEErrorIncorrectPassword, ex.ATError)
        self.collaborator.get_puk().addCallback(self._get_puk_cb)

    def incorrect_puk2_eb(self, failure):
        """Executed when the PUK2 is incorrect"""
        failure.trap(ex.CMEErrorIncorrectPassword, ex.ATError)
        self.collaborator.get_puk2().addCallback(self._get_puk2_cb)

    def puk_required_eb(self, failure):
        """Executed when PUK is required"""
        failure.trap(ex.CMEErrorSIMPUKRequired)
        self.collaborator.get_puk().addCallback(self._get_puk_cb)

    def puk2_required_eb(self, failure):
        """Executed when PUK2 is required"""
        failure.trap(ex.CMEErrorSIMPUK2Required)
        self.collaborator.get_puk2().addCallback(self._get_puk2_cb)

    def sim_failure_eb(self, failure):
        """Executed when there's a SIM failure, try again in a while"""
        failure.trap(ex.CMEErrorSIMFailure)
        self.num_sim_errors += 1
        if self.num_sim_errors >= MAX_NUM_SIM_ERRORS:
            # we can now consider that there's something wrong with the
            # device, probably there's no SIM
            self.notify_auth_failure(ex.CMEErrorSIMNotInserted)
            return

        reactor.callLater(SIM_FAIL_DELAY, self.do_next)

    def sim_busy_eb(self, failure):
        """Executed when SIM is busy, try again in a while"""
        failure.trap(ex.CMEErrorSIMBusy, ex.CMEErrorSIMNotStarted, ex.ATError, ex.ATTimeout)
        self.num_sim_busy += 1
        if self.num_sim_busy >= MAX_NUM_SIM_BUSY:
            # we can now consider that there's something wrong with the
            # device, probably a firmwarebug
            self.notify_auth_failure(ex.CMEErrorSIMFailure)
            return

        reactor.callLater(SIM_FAIL_DELAY, self.do_next)

    def sim_no_present_eb(self, failure):
        """Executed when there's no SIM, errback it"""
        failure.trap(ex.CMEErrorSIMNotInserted)
        self.notify_auth_failure(failure)

    # entry point
    def start_auth(self):
        """
        Starts the authentication

        Returns a deferred that will be callbacked if everything goes alright

        @raise wader.common.exceptions.AuthCancelled: User cancelled the auth
        @raise wader.common.exceptions.CMEErrorSIMFailure: SIM unknown error
        @raise wader.common.exceptions.CMEErrorSIMNotInserted: SIM not inserted
        @raise wader.common.exceptions.DeviceLocked: Device is locked
        """
        self.do_next()
        return self.deferred

    # states
    class get_pin_status(mode):
        """
        Ask the PIN what's the PIN status

        The SIM can be in one of the following states:
         - SIM is ready (already authenticated, or PIN disabled)
         - PIN is needed
         - PIN2 is needed (not handled)
         - PUK is needed
         - PUK2 is needed
         - SIM is not inserted
         - SIM's firmware error
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: Instantiating get_pin_status mode...." % self)
            d = self.device.sconn.check_pin()
            d.addCallback(self.check_pin_cb)
            d.addErrback(self.sim_failure_eb)
            d.addErrback(self.sim_busy_eb)
            d.addErrback(self.sim_no_present_eb)

    class pin_needed_status(mode):
        """
        PIN is needed, get it from the collaborator and try to authenticate.

        Three things can happen:
         - Auth went OK
         - PIN is incorrect
         - After three failed PIN auths, PUK is needed
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            # PIN is needed, get it from the collaborator and try to
            # authenticate.  Three things can happen:
            # - Auth went OK
            # - PIN is incorrect
            # - After three failed PIN auths, PUK is needed
            log.msg("%s: Instantiating pin_needed_status mode...." % self)
            pin = self.collaborator.pin
            d = self.device.sconn.send_pin(pin)
            d.addCallback(lambda _: self.notify_auth_ok())
            d.addErrback(self.incorrect_pin_eb)
            d.addErrback(self.puk_required_eb)

    class puk_needed_status(mode):
        """
        PUK and PIN are needed, get 'em from the collaborator and pray

        Three things can happen:
         - Auth went OK
         - PUK/PIN is incorrect
         - After five failed attempts, PUK2 is needed
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: Instantiating puk_needed_status mode...." % self)
            d = self.device.sconn.send_puk(self.collaborator.puk, 
                                           self.collaborator.pin)
            d.addCallback(lambda _: self.notify_auth_ok())
            d.addErrback(self.incorrect_puk_eb)
            d.addErrback(self.puk2_required_eb)


    class puk2_needed_status(mode):
        """
        PUK2 and PIN are needed, get 'em from the collaborator and pray

        Three things can happen:
         - Auth went OK
         - PUK/PIN is incorrect
         - After ten failed attempts, device is locked
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: Instantiating puk2_needed_status mode...." % self)
            d = self.device.sconn.send_puk(self.collaborator.puk2,
                                           self.collaborator.pin)
            d.addCallback(lambda _: self.notify_auth_ok())
            d.addErrback(self.incorrect_puk2_eb)
            d.addErrback(self.puk2_required_eb)

