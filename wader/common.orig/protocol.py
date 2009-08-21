#o -*- coding: utf-8 -*-
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
Twisted's protocols for the serial and data (wvdial) connections
"""
__version__ = "$Rev: 1172 $"

import re
from collections import deque

from twisted.internet import protocol, defer, reactor
from twisted.python.failure import Failure
from twisted.python import log

from wader.common.aterrors import extract_error
from wader.common.command import ATCmd
import wader.common.exceptions as ex
import wader.common.notifications as N

def clean_data(s):
    """Returns a clean copy of C{s} (without \r\n)"""
    return "[%s]" % s.replace('\r', '').replace('\n', '')

# Standard unsolicited notifications
CALL_RECV = re.compile('\r\nRING\r\n')
STK_DEBUG = re.compile('\r\n\+STC:\s\d+\r\n')
# Standard solicited notifications
NEW_SMS = re.compile('\r\n\+CMTI:\s"(?P<where>\w{2,})",(?P<id>\d+)\r\n')
SPLIT_PROMPT = re.compile('^\r\n>\s$')
CREG_REGEXP = re.compile('\r\n\+CREG:\s*(?P<status>\d)\r\n')


class BufferingStateMachine(object, protocol.Protocol):
    """
    A simple SM that handles low level communication with the device
    """
    def __init__(self, device):
        super(BufferingStateMachine, self).__init__()
        self.device = device
        self.custom = device.custom
        self.cmd = None
        self.state = 'idle'
        # since Python 2.5+ using a string as buffer is efficient m'kay?
        self.idlebuf = ""
        self.waitbuf = ""
        self.notifications = defer.DeferredQueue()

    def _timeout_eb(self):
        self.notify_failure(ex.ATTimeout(self.cmd))

    def cancel_current_delayed_call(self):
        """Cancels current C{ATCmd} dellayed call if active"""
        if self.cmd.callID and self.cmd.callID.active():
            self.cmd.callID.cancel()

    def notify_success(self, foo):
        """Notify success to current C{ATCmd} callbacks"""
        self.cancel_current_delayed_call()
        self.cmd.deferred.callback(foo)

    def notify_failure(self, failure):
        """Notify failure to current C{ATCmd} errbacks"""
        self.cancel_current_delayed_call()
        self.cmd.deferred.errback(failure)

    def set_cmd(self, cmd):
        """Sets self.cmd to C{cmd}"""
        assert self.state == 'idle', "Not in idle!"
        self.cmd = cmd
        # set the timeout for this command
        self.cmd.callID = reactor.callLater(cmd.timeout, self._timeout_eb)
        self.set_state('waiting')

    def set_state(self, state):
        """Sets and logs the new state"""
        log.msg("%s: NEW STATE: %s" % (self, state))
        self.state = state

    def transition_to_idle(self):
        """
        Transitions to idle state and
        """
        self.cmd = None
        self.set_state('idle')
        # XXX: If we set idlebuf to "" we can miss some unsolicited responses
        # OTOH, the idlebuf might end up full of STK garbage, ATZ, etc.
        self.idlebuf = ""
        self.waitbuf = ""
#        log.msg("AFTER TRANSITIONING IDLE=%r" % self.idlebuf)

    def send_splitcmd(self):
        """
        Used to send the second part of a split command after prompt appears
        """
        raise NotImplementedError()

    def enque_notification(self, klass, *args, **kwds):
        """
        Enqueues a notification

        @param klass: The class of the notification to enqueue
        @param args: The arguments to instantiate C{klass}
        @param kwds: The keywords to instantiate C{klass}
        """
        n = klass(*args, **kwds)
        self.notifications.put(n)
        log.msg("%s: QUEING %s args=%s kwds=%s" % (self, klass, args, kwds))

    def dataReceived(self, data):
        """See L{twisted.internet.protocol.Protocol.dataReceived}"""
        args = (self, self.state.upper(), data)
        log.msg("%s::%s DATA_RCV: %r" % args)
        state = 'handle_' + self.state
        getattr(self, state)(data)

    def process_notifications(self, buffer):
        """
        Processes unsolicited notifications in C{buffer}

        @type buffer: str
        @param buffer: Buffer to scan
        """
        if not self.device.custom:
            return buffer

        custom = self.device.custom

        # ignore and consume these strings from the buffer
        if custom.ignore_regexp:
            for ignore in custom.ignore_regexp:
                for match in re.finditer(ignore, buffer):
                    if match:
                        stuff = (self, match.group())
                        log.msg("%s::IGNORE: %r" % stuff)
                        buffer = buffer.replace(match.group(), '', 1)

        if custom.async_regexp:
            # we have to use re.finditer as some cards like to pipeline
            # several asynchronous notifications in one
            for match in re.finditer(custom.async_regexp, buffer):
                stuff = (self, match.group())
                log.msg("%s::NOTIFICATION: %r" % stuff)
                name, value = match.groups()
                if name in custom.signal_translations:
                    # we obtain the signal name and the associated function
                    # that will translate the device unsolicited message to
                    # the signal used in VMC internally
                    signal, func = custom.signal_translations[name]

                    # if we have a transform function defined, then use it
                    # otherwise use value as args
                    try:
                        args = func and func(value) or value
                    except Exception, e:
                        log.err(e, """
SIGNAL TRANSLATION ERROR:
function %s can not handle notification %s""" % (func, value))
                        args = value

                    self.enque_notification(N.UnsolicitedNotification,
                                            signal, args)

                # remove from the idlebuf the match (but only once please)
                buffer = buffer.replace(match.group(), '', 1)

        return buffer

    def handle_idle(self, data):
        """See the method comments"""
        # being in idle state, there are six possible events that must be
        # handled:
        # - STK init garbage
        # - Call received (we're not handling it in waiting)
        # - A SMS arrived
        # - SMS notification (Not handled yet)
        # - Device's own unsolicited notifications
        # - Default: i.e. this device originated a notification that we don't
        #   understand yet, the point is to log it and make it visible so the
        #   user can report it to us
        self.idlebuf += data

        # most possible event:
        # device's own unsolicited notifications
        # signal translations stuff
        self.idlebuf = self.process_notifications(self.idlebuf)
        if not self.idlebuf:
            return

        # second most possible event:
        # new SMS arrived
        match = NEW_SMS.match(self.idlebuf)
        if match:
            index = int(match.group('id'))
            where = match.group('where')

            self.enque_notification(N.NewSMSArrived, index, where)

            self.idlebuf = self.idlebuf.replace(match.group(), '', 1)
            if not self.idlebuf:
                return

        # third most possible event
        match = STK_DEBUG.match(self.idlebuf)
        if match:
            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        # fourth most possible event
        match = CREG_REGEXP.match(self.idlebuf)
        if match:
            status = int(match.group('status'))
            self.enque_notification(N.NetworkRegNotification, status)
            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        # fifth most possible event:
        match = CALL_RECV.match(self.idlebuf)
        if match:
            self.enque_notification(N.CallNotification)

            # XXX: Should we place a limit here? Wait till we have one of
            # this gadgets
            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        stuff = (self, self.idlebuf)
        log.msg("%s::IDLE: %r doesn't matchs my regexp" % stuff)

    def handle_waiting(self, data):
        self.waitbuf += data

        self.waitbuf = self.process_notifications(self.waitbuf)
        if not self.waitbuf:
            return

        cmdinfo = self.custom.cmd_dict[self.cmd.name]
        match = cmdinfo['end'].search(self.waitbuf)
        if match: # end of response
            log.msg("%s::WAITING: EOR detected, firing deferred" % self)
            if 'echo' in cmdinfo and cmdinfo['echo']:
                m = cmdinfo['echo'].match(self.waitbuf)
                if m:
                    self.waitbuf = self.waitbuf.replace(m.group(), '', 1)

            if cmdinfo['extract']:
                # There's an regex to extract info from data
                response = list(re.finditer(cmdinfo['extract'], self.waitbuf))
                resp_repr = str([m.groups() for m in response])
                log.msg("%s::WAITING: CBK = %s" % (self, resp_repr))
                self.notify_success(response)

                # now clean self.waitbuf
                for _m in response:
                    self.waitbuf = self.waitbuf.replace(_m.group(), '', 1)
                # now clean end of command
                endmatch = cmdinfo['end'].search(self.waitbuf)
                if endmatch:
                    self.waitbuf = self.waitbuf.replace(endmatch.group(),
                                                        '', 1)
            else:
                # there's no regex in cmdinfo to extract info
                cdata = clean_data(self.waitbuf)
                log.msg("%s::WAITING: NO CBK REG, CBK= %s" % (self, cdata))
                self.notify_success(cdata)
                self.waitbuf = self.waitbuf.replace(match.group(), '', 1)

            self.transition_to_idle()
        else:
            match = extract_error(self.waitbuf)
            if match:
                excep, error, m = match
                log.err("%s::WAITING: ERROR received %r" % (self, m.group()))
                # send the failure back
                self.notify_failure(Failure(excep(error)))
                self.waitbuf = self.waitbuf.replace(m.group(), '', 1)
                self.transition_to_idle()
            else:
                match = SPLIT_PROMPT.match(data)
                if match:
                    log.msg("%s::WAITING: Split CMD detected" % self)
                    self.send_splitcmd()
                    self.waitbuf = self.waitbuf.replace(match.group(), '', 1)
                else:
                    msg  = "%s::WAITING: Data %s didn't match my regexp"
                    log.err(msg % (self, data))


class SIMProtocol(BufferingStateMachine):
    """
    SIMProtocol defines the protocol used to communicate with the SIM card

    SIMProtocol communicates with the SIM synchronously, only one command
    at a time. However, SIMProtocol offers an asynchronous interface
    L{queue_at_cmd} which accepts and queues an L{wader.common.command.ATCmd}
    and returns a L{Deferred} that will be callbacked with the commands
    response, or errback if an exception is raised.

    SIMProtocol actually is an specially tailored Finite State Machine. After
    several redesigns and simplifications, this FSM has just two states:
     - idle: sitting idle for user input or an unsolicited response, when
     a command is received we send the command and transition to the waiting
     state
     - waiting: the FSM is buffering and parsing all the SIM's response to
     the command till it matches the regexp that signals the end of the
     command. If the command has an associated regexp to extract information,
     the buffered response will be parsed and the command's deferred will be
     callbacked with the regexp as argument. There are commands that don't
     have an associated regexp to extract information as we are not interested
     in the "all went ok" response, only if an exception occurred (e.g. when
     deleting a contact we are only interested if something went wront, not
     if all went ok)

     The transition to each state is driven by regular expressions, each
     command has associated a set of regular expressions that make the FSM
     change states. This regexps are defined in L{wader.common.command.CMD_DICT}
     although the plugin mechanism offers the possibility of customizing the
     CMD_DICT through L{wader.common.hardware.Customizer} if a card uses a
     different AT string than the rest for that particular command.
    """
    def __init__(self, device):
        super(SIMProtocol, self).__init__(device)
        self.queue = defer.DeferredQueue()
        self.mutex = defer.DeferredLock()
        self._check_queue()

    def __repr__(self):
        return self.__class__.__name__

    def transition_to_idle(self):
        """Transitions to idle and processes next queued C{ATCmd}"""
        super(SIMProtocol, self).transition_to_idle()
        try:
            self.mutex.release()
        except AssertionError:
            pass

        self._check_queue()

    def send_splitcmd(self):
        """
        Used to send the second part of a split command after prompt appears
        """
        self.transport.write(self.cmd.splitcmd)

    def _process_at_cmd(self, cmd):
        def transition_n_send(_):
            assert self.state == 'idle', "NOT IN IDLE: %s" % self.state

            log.msg("%s: SENDING ATCMD %r" % (self, cmd.cmd))
            self.set_cmd(cmd)
            self.transport.write(cmd.cmd)

        self.mutex.acquire().addCallback(transition_n_send)

    def _check_queue(self):
        # when the next element of the queue is put, _process_at_cmd will be
        # callbacked with it
        self.queue.get().addCallback(self._process_at_cmd)

    def queue_at_cmd(self, cmd):
        """
        Queues an C{ATCmd} and returns a deferred

        This deferred will be callbacked with the command's response
        """
        self.queue.put(cmd)
        return cmd.deferred

    def fake_queue_at_cmd(self, cmd):
        """
        Returns a Deferred timeout failure
        """
        return defer.fail(ex.ATTimeout(cmd))


class SIMCardConnection(SIMProtocol):
    """
    SIMCardConnection provides several methods to interact with the SIM card
    """

    def __init__(self, device):
        super(SIMCardConnection, self).__init__(device)

    #####################################################################
    # USER COMMANDS
    #####################################################################

    def add_contact(self, name, number, index):
        """
        Adds a contact to the SIM card
        """
        category = (number.startswith('+') or number.startswith('002B')) and 145 or 129
        args = (index, number, category, name)
        cmd = ATCmd('AT+CPBW=%d,"%s",%d,"%s"' % args, name='add_contact')
        return self.queue_at_cmd(cmd)

    def add_sms(self, pdu_len, pdu):
        """Adds C{sms} to the SIM and returns the index"""
        atstr = 'AT+CMGW=%d' % pdu_len
        cmd = ATCmd(atstr, name='add_sms', eol='\r')
        cmd.splitcmd = '%s\x1a' % pdu
        return self.queue_at_cmd(cmd)

    def change_pin(self, oldpin, newpin):
        """
        Changes C{oldpin} to C{newpin} in the SIM card

        @type oldpin: C{str}
        @type newpin: C{str}

        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the password is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        password is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        atstr = 'AT+CPWD="SC","%s","%s"' % (str(oldpin), str(newpin))
        cmd = ATCmd(atstr, name='change_pin')
        return self.queue_at_cmd(cmd)

    def check_pin(self):
        """
        Checks what's necessary to authenticate against the SIM card

        @return: If everything goes well, it will return one of the following
          1. +CPIN: READY
          2. +CPIN: SIM PIN
          3. +CPIN: SIM PUK
          4. +CPIN: SIM PUK2

        @raise common.exceptions.CMEErrorSIMBusy: When the SIM is not ready
        @raise common.exceptions.CMEErrorSIMNotStarted: When the SIM is not
        ready
        @raise common.exceptions.CMEErrorSIMFailure: This exception is
        raised by GlobeTrotter's 3G cards (without HSDPA) when PIN
        authentication is disabled
        """
        cmd = ATCmd('AT+CPIN?', name='check_pin')
        cmd.timeout=5
        return self.queue_at_cmd(cmd)
        #return self.fake_queue_at_cmd(cmd)

    def delete_all_contacts(self):
        """Deletes all the contacts in SIM card, function useful for tests"""
        d = self.get_used_contact_ids()
        def get_contacts_ids_cb(used):
            if not used:
                return True

            return defer.gatherResults([self.delete_contact(i) for i in used])

        d.addCallback(get_contacts_ids_cb)
        return d

    def delete_all_sms(self):
        """Deletes all the messages in SIM card, function useful for tests"""
        d = self.get_used_sms_ids()
        def delete_all_sms_cb(used):
            if not used:
                return True

            return defer.gatherResults([self.delete_sms(i) for i in used])

        d.addCallback(delete_all_sms_cb)
        return d

    def delete_contact(self, index):
        """Deletes the contact specified by index"""
        cmd = ATCmd('AT+CPBW=%d' % index, name='delete_contact')
        return self.queue_at_cmd(cmd)

    def delete_sms(self, index):
        """Deletes the message specified by index"""
        cmd = ATCmd('AT+CMGD=%d' % index, name='delete_sms')
        return self.queue_at_cmd(cmd)

    def disable_echo(self):
        """Disables echo of AT cmds"""
        cmd = ATCmd('ATE0', name='disable_echo')
        return self.queue_at_cmd(cmd)

    def disable_pin(self, pin):
        """
        Disables pin authentication at startup

        @type pin: C{int}
        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the PIN is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        PIN is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        cmd = ATCmd('AT+CLCK="SC",0,"%s"' % str(pin), name='disable_pin')
        return self.queue_at_cmd(cmd)

    def enable_pin(self, pin):
        """
        Enables pin authentication at startup

        @type pin: C{int}
        @return: If everything goes well, it will return an 'OK' through the
        callback, otherwise it will raise an exception.

        @raise common.exceptions.ATError: When the PIN is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: When the
        PIN is incorrect.
        @raise common.exceptions.InputValueError: When the PIN != \d{4}
        """
        cmd = ATCmd('AT+CLCK="SC",1,"%s"' % str(pin), name='enable_pin')
        return self.queue_at_cmd(cmd)

    def error_reporting(self, type=1):
        """
        Error reporting method

        0 disable +CME ERROR: <err> result code and use ERROR instead
        1 enable +CME ERROR: <err> result code and use numeric <err> values
        2 enable +CME ERROR: <err> result code and use verbose <err> values
        """
        cmd = ATCmd('AT+CMEE=%d' % type, name='error_reporting')
        return self.queue_at_cmd(cmd)

    def find_contacts(self, pattern):
        """Returns a list of contacts that match the given pattern"""
        cmd = ATCmd('AT+CPBF="%s"' % pattern, name='find_contacts')
        return self.queue_at_cmd(cmd)

    def get_contact_by_index(self, index):
        cmd = ATCmd('AT+CPBR=%d' % index, name='get_contact_by_index')
        return self.queue_at_cmd(cmd)

    def get_contacts(self):
        """
        Returns a list with all the contacts stored in the SIM card

        @return: Returns a list of C{re.MatchObject} with the contacts.

        @raise common.exceptions.ATError: When no contacts are found.
        @raise common.exceptions.CMEErrorNotFound: When no contacts are
        found.
        @raise common.exceptions.CMEErrorSIMBusy: When the SIM is not
        ready.
        @raise common.exceptions.CMEErrorSIMNotStarted: When the SIM is not
        ready.
        """
        cmd = ATCmd('AT+CPBR=1,%d' % self.device.sim.size,
                    name='get_contacts')
        return self.queue_at_cmd(cmd)

    def get_available_charset(self):
        """Returns the available character sets"""
        cmd = ATCmd('AT+CSCS=?', name='get_available_charset')
        return self.queue_at_cmd(cmd)

    def get_card_version(self):
        """Returns the SIM card version"""
        cmd = ATCmd('AT+GMR', name='get_card_version')
        return self.queue_at_cmd(cmd)

    def get_card_model(self):
        """Returns the SIM card model"""
        cmd = ATCmd('AT+CGMM', name='get_card_model')
        return self.queue_at_cmd(cmd)

    def get_charset(self):
        """Returns the current character set name"""
        cmd = ATCmd('AT+CSCS?', name='get_charset')
        return self.queue_at_cmd(cmd)

    def get_imei(self):
        """Returns the IMEI number of the SIM card"""
        cmd = ATCmd('AT+CGSN', name='get_imei')
        return self.queue_at_cmd(cmd)

    def get_imsi(self):
        """Returns the IMSI number of the SIM card"""
        cmd = ATCmd('AT+CIMI', name='get_imsi')
        return self.queue_at_cmd(cmd)

    def get_manufacturer_name(self):
        """Returns the manufacturer name of the SIM card"""
        cmd = ATCmd('AT+CGMI', name='get_manufacturer_name')
        return self.queue_at_cmd(cmd)

    def get_netreg_status(self):
        """Returns the network registration status"""
        cmd = ATCmd('AT+CREG?', name='get_netreg_status')
        return self.queue_at_cmd(cmd)

    def get_network_info(self):
        """Returns a tuple with the network info"""
        cmd = ATCmd('AT+COPS?', name='get_network_info')
        return self.queue_at_cmd(cmd)

    def get_network_names(self):
        """Returns a tuple with the network info"""
        cmd = ATCmd('AT+COPS=?', name='get_network_names')
        cmd.timeout = 40
        return self.queue_at_cmd(cmd)

    def get_roaming_ids(self):
        """Returns a list with the networks we can register with"""
        cmd = ATCmd('AT+CPOL?', name='get_roaming_ids')
        return self.queue_at_cmd(cmd)

    def get_free_contact_ids(self):
        """Returns a deque with the not used contact ids"""
        def callback(contacts):
            if not contacts:
                return deque(range(1, self.device.sim.size))

            busy_ids = [int(contact.group('id')) for contact in contacts]

            free = set(range(1, self.device.sim.size)) ^ set(busy_ids)
            return deque(list(free))

        def errback(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return deque(range(1, self.device.sim.size))

        d = self.get_contacts()
        d.addCallbacks(callback, errback)
        return d

    def get_next_contact_id(self):
        """Returns the next free contact id"""
        d = self.get_free_contact_ids()
        d.addCallback(lambda free: free.popleft()) # equivalent to list.pop(0)
        return d

    def get_signal_level(self):
        """Returns a tuple with the RSSI and BER of the connection"""
        cmd = ATCmd('AT+CSQ', name='get_signal_level')
        return self.queue_at_cmd(cmd)

    def get_sms(self):
        """
        Returns a list with all the messages stored in the SIM card

        @return: Returns a list of C{re.MatchObject} with the messages.

        @raise common.exceptions.ATError: When no messages are found.
        @raise common.exceptions.CMEErrorNotFound: When no messages are
        found.
        @raise common.exceptions.CMEErrorSIMBusy: When the SIM is not
        ready.
        @raise common.exceptions.CMEErrorSIMNotStarted: When the SIM is not
        ready.
        @raise common.exceptions.CMSError500: When the SIM is not
        ready.
        """
        cmd = ATCmd('AT+CMGL=4', name='get_sms')
        return self.queue_at_cmd(cmd)

    def get_sms_by_index(self, index):
        """Returns the message stored at index"""
        cmd = ATCmd('AT+CMGR=%d' % index, name='get_sms_by_index')
        return self.queue_at_cmd(cmd)

    def get_smsc(self):
        cmd = ATCmd('AT+CSCA?', name='get_smsc')
        return self.queue_at_cmd(cmd)

    def get_phonebook_size(self):
        """
        Returns the phonebook size of the SIM card

        @return: A C{re.MatchObject} with the size of the phonebook

        @raise common.exceptions.CMEErrorSIMBusy: When the SIM is not
        ready.
        @raise common.exceptions.CMSError500: When the SIM is not ready.
        @raise common.exceptions.ATError: When the SIM is not ready.
        """
        cmd = ATCmd('AT+CPBR=?', name='get_phonebook_size')
        cmd.timeout = 30
        return self.queue_at_cmd(cmd)

    def get_pin_status(self):
        """Checks wether the pin is enabled or disabled"""
        cmd = ATCmd('AT+CLCK="SC",2', name='get_pin_status')
        return self.queue_at_cmd(cmd)

    def get_used_contact_ids(self):
        """Returns a list with the used contact ids"""
        def errback(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d = self.get_contacts()
        d.addCallback(lambda contacts: [int(c.group('id')) for c in contacts])
        d.addErrback(errback)
        return d

    def get_used_sms_ids(self):
        """Returns a list with used SMS ids in the SIM card"""
        d = self.get_sms()
        def errback(failure):
            failure.trap(ex.CMEErrorNotFound, ex.ATError)
            return []

        d.addCallback(lambda smslist: [int(s.group('id')) for s in smslist])
        d.addErrback(errback)
        return d

    def register_with_network(self, netid, mode=1, format=2):
        """Registers with the given netid"""
        atstr = 'AT+COPS=%d,%d,"%d"' % (mode, format, netid)
        cmd = ATCmd(atstr, name='register_with_network')
        return self.queue_at_cmd(cmd)

    def reset_settings(self):
        """Resets the settings to factory settings"""
        cmd = ATCmd('ATZ', name='reset_settings')
        return self.queue_at_cmd(cmd)

    def send_at(self, at_str):
        """Send an arbitrary AT string to the SIM card"""
        cmd = ATCmd(at_str, name='send_at')
        return self.queue_at_cmd(cmd)

    def send_pin(self, pin):
        """Sends the PIN to the SIM card"""
        cmd = ATCmd('AT+CPIN="%s"' % str(pin), name='send_pin')
        return self.queue_at_cmd(cmd)

    def send_puk(self, puk, pin):
        """
        Sends PUK and PIN to the SIM card

        @return: C{True} if everything went ok

        @raise common.exceptions.ATError: Exception raised by Nozomi when
        the PUK is incorrect.
        @raise common.exceptions.CMEErrorIncorrectPassword: Exception raised
        when the PUK is incorrect.
        """
        atstr = 'AT+CPIN="%s","%s"' % (str(puk), str(pin))
        cmd = ATCmd(atstr, name='send_puk')
        return self.queue_at_cmd(cmd)

    def send_sms(self, pdu, pdu_len):
        """Sends the given pdu and returns the index"""
        cmd = ATCmd('AT+CMGS=%d' % pdu_len, name='send_sms', eol='\r')
        cmd.splitcmd = '%s\x1a' % pdu
        return self.queue_at_cmd(cmd)

    def set_charset(self, charset):
        """Sets the character set used on the SIM"""
        cmd = ATCmd('AT+CSCS="%s"' % charset, name='set_charset')
        return self.queue_at_cmd(cmd)

    def set_netreg_notification(self, val=1):
        """Sets CREG unsolicited notification"""
        cmd = ATCmd('AT+CREG=%d' % val, name='set_netreg_notification')
        return self.queue_at_cmd(cmd)

    def set_network_info_format(self, mode=0, format=2):
        cmd = ATCmd('AT+COPS=%d,%d' % (mode, format),
                    name='set_network_info_format')
        return self.queue_at_cmd(cmd)

    def set_sms_format(self, format=1):
        """Sets the format of the SMS"""
        cmd = ATCmd('AT+CMGF=%d' % format, name='set_sms_format')
        return self.queue_at_cmd(cmd)

    def set_sms_indication(self, mode=2, mt=1, bm=0, ds=0, bfr=0):
        """Sets the SMS indication mode"""
        args = 'AT+CNMI=' + ','.join(map(str, [mode, mt, bm, ds, bfr]))
        cmd = ATCmd(args, name='set_sms_indication')
        return self.queue_at_cmd(cmd)

    def set_smsc(self, number):
        """Sets the SMSC"""
        cmd = ATCmd('AT+CSCA="%s"' % number, name='set_smsc')
        return self.queue_at_cmd(cmd)

