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
Stuff used at startup
"""
__version__ = "$Rev: 1172 $"

import os
import shutil
import sys

from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
from twisted.python import log

import wader.common.consts as consts
from vmc.utils.utilities import save_file, touch

DELAY = 10

LOCK = os.path.join(consts.VMC_HOME, '.setup-done')

def attach_serial_protocol(device, test=False):
    """
    Returns C{device} with a reference to the protocol's instance
    """
    from wader.common.protocol import SIMCardConnection
    from wader.common.middleware import SIMCardConnAdapter

    if not test:
        # Use the adapter that device specifies
        if device.custom.adapter:
            adapter_klass = device.custom.adapter
        else:
            adapter_klass = SIMCardConnAdapter

        log.msg("ADAPTING %s to %s" % (device, adapter_klass))
        sconn = adapter_klass(device)
    else:
        # We can only test SIMCardConnection as SIMCardConnAdapter uses
        # delayed calls
        sconn = SIMCardConnection(device)

    port = device.has_two_ports() and device.cport or device.dport
    # keep a reference to the SerialPort, in case we need to stop it or
    # something
    device.sport = SerialPort(sconn, port, reactor, baudrate=device.baudrate)
    device.sconn = sconn
    return device

def ensure_have_config(force_create=False):
    if os.path.exists(consts.VMC_CFG) and not force_create:
        return

    from wader.common.oal import osobj

    join = os.path.join
    cfg_path = join(consts.TEMPLATES_DIR, osobj.abstraction['CFG_TEMPLATE'])
    shutil.copy(cfg_path, consts.VMC_CFG)

    os.chmod(consts.VMC_CFG, 0600)

def create_skeleton_and_do_initial_setup():
    """I perform the operations needed for the initial user setup"""
    if os.path.exists(LOCK):
        return

    try:
        shutil.rmtree(consts.VMC_HOME, True)
        os.mkdir(consts.VMC_HOME)
        os.mkdir(consts.MOBILE_PROFILES)
        os.mkdir(consts.DIALER_PROFILES)
        os.mkdir(consts.CACHED_DEVICES)
    except OSError, e:
        pass

    # copy plugins to plugins dir
    shutil.copytree(consts.PLUGINS_DIR, consts.PLUGINS_HOME)

    # Create the initial config
    ensure_have_config(force_create=True)

    touch(consts.CHAP_PROFILE)
    touch(consts.DEFAULT_PROFILE)
    touch(consts.PAP_PROFILE)

    from wader.common import plugin
    save_file(LOCK, str(plugin.VERSION))

def populate_dbs():
    """
    Populates the different databases
    """
    try:
        # only will succeed on development 
        vf_networks = __import__('resources/extra/vf_networks')
        xx_networks = __import__('resources/extra/xx_networks')
    except ImportError:
        try:
            # this fails on feisty but not on gutsy
            vf_networks = __import__(os.path.join(consts.EXTRA_DIR, 'vf_networks'))
            xx_networks = __import__(os.path.join(consts.EXTRA_DIR, 'xx_networks'))
        except ImportError:
            sys.path.insert(0, consts.EXTRA_DIR)
            import vf_networks
            import xx_networks

    vf_instances = [getattr(vf_networks, item)() for item in dir(vf_networks)
                    if (not item.startswith('__') and item != 'NetworkOperator')]
    xx_instances = [getattr(xx_networks, item)() for item in dir(xx_networks)
                    if (not item.startswith('__') and item != 'NetworkOperator')]

    from wader.common.persistent import net_manager
    net_manager.populate_networks(vf_instances + xx_instances)

