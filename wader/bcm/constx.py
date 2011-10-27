# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

from wader.common.consts import (MM_ALLOWED_MODE_ANY,
                                 MM_ALLOWED_MODE_2G_PREFERRED,
                                 MM_ALLOWED_MODE_3G_PREFERRED,
                                 MM_ALLOWED_MODE_2G_ONLY,
                                 MM_ALLOWED_MODE_3G_ONLY,
                                 MM_MODEM_STATE_UNKNOWN,
                                 MM_MODEM_STATE_DISABLED,
                                 MM_MODEM_STATE_DISABLING,
                                 MM_MODEM_STATE_ENABLING,
                                 MM_MODEM_STATE_ENABLED,
                                 MM_MODEM_STATE_SEARCHING,
                                 MM_MODEM_STATE_REGISTERED,
                                 MM_MODEM_STATE_DISCONNECTING,
                                 MM_MODEM_STATE_CONNECTING,
                                 MM_MODEM_STATE_CONNECTED,
                                 MM_NETWORK_BAND_ANY, MM_NETWORK_BAND_EGSM,
                                 MM_NETWORK_BAND_DCS, MM_NETWORK_BAND_PCS,
                                 MM_NETWORK_BAND_G850, MM_NETWORK_BAND_U2100,
                                 MM_NETWORK_BAND_U1700, MM_NETWORK_BAND_17IV,
                                 MM_NETWORK_BAND_U800, MM_NETWORK_BAND_U850,
                                 MM_NETWORK_BAND_U900, MM_NETWORK_BAND_U17IX,
                                 MM_NETWORK_BAND_U1900)
from wader.common.utils import revert_dict
from wader.bcm.translate import _

BAND_MAP = {
    MM_NETWORK_BAND_ANY: _('Any'),
    MM_NETWORK_BAND_EGSM: _('EGSM 900'),
    MM_NETWORK_BAND_DCS: _('GSM DCS'),
    MM_NETWORK_BAND_PCS: _('GSM PCS'),
    MM_NETWORK_BAND_G850: _('GSM 850'),
    MM_NETWORK_BAND_U2100: _('WCDMA 2100'),
    MM_NETWORK_BAND_U1700: _('WCDMA 1700'),
    MM_NETWORK_BAND_17IV: _('WCDMA 17IV'),
    MM_NETWORK_BAND_U800: _('WCDMA 800'),
    MM_NETWORK_BAND_U850: _('WCDMA 850'),
    MM_NETWORK_BAND_U900: _('WCDMA 900'),
    MM_NETWORK_BAND_U17IX: _('WCDMA 17IX'),
    MM_NETWORK_BAND_U1900: _('WCDMA 1900'),
}

BAND_MAP_REV = revert_dict(BAND_MAP)

MODE_MAP = {
    MM_ALLOWED_MODE_ANY: _('Any'),
    MM_ALLOWED_MODE_2G_PREFERRED: _('2G preferred'),
    MM_ALLOWED_MODE_3G_PREFERRED: _('3G preferred'),
    MM_ALLOWED_MODE_2G_ONLY: _('2G only'),
    MM_ALLOWED_MODE_3G_ONLY: _('3G only'),
}
MODE_MAP_REV = revert_dict(MODE_MAP)

# We don't have any values for authentication methods
# in common.consts, so we'll have to invent them here
# for now
VM_NETWORK_AUTH_ANY = 0xff
VM_NETWORK_AUTH_PAP = 0x01
VM_NETWORK_AUTH_EAP = 0x02
VM_NETWORK_AUTH_CHAP = 0x04
VM_NETWORK_AUTH_MSCHAP = 0x08
VM_NETWORK_AUTH_MSCHAPv2 = 0x10

AUTH_MAP = {
    VM_NETWORK_AUTH_ANY: _('Any'),
    VM_NETWORK_AUTH_PAP: _('PAP'),
    VM_NETWORK_AUTH_EAP: _('EAP'),
    VM_NETWORK_AUTH_CHAP: _('CHAP'),
    VM_NETWORK_AUTH_MSCHAP: _('MSCHAP'),
    VM_NETWORK_AUTH_MSCHAPv2: _('MSCHAPv2'),
}
AUTH_MAP_REV = revert_dict(AUTH_MAP)

BCM_MODEM_STATE_UNKNOWN = MM_MODEM_STATE_UNKNOWN       #  0
BCM_MODEM_STATE_NODEVICE = MM_MODEM_STATE_UNKNOWN + 1
BCM_MODEM_STATE_HAVEDEVICE = MM_MODEM_STATE_UNKNOWN + 2
BCM_MODEM_STATE_DISABLED = MM_MODEM_STATE_DISABLED     # 10
BCM_MODEM_STATE_DISABLING = MM_MODEM_STATE_DISABLING   # 20
BCM_MODEM_STATE_LOCKED = MM_MODEM_STATE_DISABLING + 1
BCM_MODEM_STATE_UNLOCKING = MM_MODEM_STATE_DISABLING + 2
BCM_MODEM_STATE_UNLOCKED = MM_MODEM_STATE_DISABLING + 3
BCM_MODEM_STATE_ENABLING = MM_MODEM_STATE_ENABLING     # 30
BCM_MODEM_STATE_ENABLED = MM_MODEM_STATE_ENABLED
BCM_MODEM_STATE_SEARCHING = MM_MODEM_STATE_SEARCHING
BCM_MODEM_STATE_REGISTERED = MM_MODEM_STATE_REGISTERED
BCM_MODEM_STATE_DISCONNECTING = MM_MODEM_STATE_DISCONNECTING
BCM_MODEM_STATE_CONNECTING = MM_MODEM_STATE_CONNECTING
BCM_MODEM_STATE_CONNECTED = MM_MODEM_STATE_CONNECTED

BCM_SIM_AUTH_NONE, BCM_SIM_AUTH_PIN, \
BCM_SIM_AUTH_PUK, BCM_SIM_AUTH_PUK2 = range(4)

BCM_VIEW_DISABLED, BCM_VIEW_IDLE, BCM_VIEW_BUSY = range(3)
