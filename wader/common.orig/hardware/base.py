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
Base classes for the hardware module
"""
__version__ = "$Rev: 1172 $"

import serial

from twisted.internet.threads import deferToThread
from twisted.python import log

from wader.common.command import get_cmd_dict_copy
from wader.common.middleware import SIMCardConnAdapter
from wader.common.statem.auth import AuthStateMachine
from wader.common.statem.connection import ConnectStateMachine
from wader.common.statem.networkreg import NetworkRegStateMachine
import wader.common.exceptions as ex

class Customizer(object):
    """
    I contain all the custom classes and metadata that a device needs

    @cvar adapter: Adapter for the device
    @type adapter: L{SIMCardConnAdapter} child.
    @cvar async_regexp: regexp to parse asynchronous notifications emited
    by the device.
    @cvar conn_dict: Dictionary with the AT strings necessary to change
    between the different connection modes
    @cvar cmd_dict: Dictionary with commands info
    @cvar device_capabilities: List with the unsolicited notifications that
    this device supports
    @cvar authklass: Class that will handle the authentication for this device
    @cvar connklass: Class that will handle the connection for this device
    @cvar netrklass: Class that will handle the network registration for this
    device
    """
    adapter = SIMCardConnAdapter
    async_regexp = None
    ignore_regexp = None
    conn_dict = {}
    cmd_dict = get_cmd_dict_copy()
    device_capabilities = []
    signal_translations = {}
    authklass = AuthStateMachine
    connklass = ConnectStateMachine
    netrklass = NetworkRegStateMachine


def _identify_device(port):
    """
    Returns the model of the device present at C{port}
    """
    # as the readlines method blocks, this is executed in a parallel thread
    # with deferToThread
    ser = serial.Serial(port, timeout=1)
    ser.write('ATZ\r\n')    # Ericsson does not support ATZ, but we must echo off
    ser.readlines()         # at the very least or we won't match model name
    ser.write('ATE0 V1 X4 &C1\r\n')
    ser.readlines()

    ser.flushOutput()
    ser.flushInput()

    ser.write('AT+CGMM\r\n')
    # clean up unsolicited notifications and \r\n's
    response = [r.replace('\r\n', '') for r in ser.readlines()
                    if not r.startswith(('^', '_')) and r.replace('\r\n','')]
    log.msg("AT+CGMM response: %r" % response)
    ser.close()

    assert len(response), "Modem didn't reply anything meaningful"
    return response[0]

def identify_device(plugin):
    def identify_device_cb(model):
        # plugin to return
        _plugin = None

        if plugin.mapping:
            if model in plugin.mapping:
                _plugin = plugin.mapping[model]()

        # the plugin has no mapping, chances are that we already identified
        # it by its vendor & product id
        elif plugin.__remote_name__ != model:
            from wader.common.plugin import PluginManager
            # so we basically have a device identified by vendor & product id
            # but we know nuthin of this model
            try:
                _plugin = PluginManager.get_plugin_by_remote_name(model)
            except ex.UnknownPluginNameError:
                plugin.name = model

        if _plugin is not None:
            # we found another plugin during the process
            _plugin.patch(plugin)
            return _plugin
        else:
            return plugin

    port = plugin.has_two_ports() and plugin.cport or plugin.dport
    d = deferToThread(_identify_device, port)
    d.addCallback(identify_device_cb)
    return d

