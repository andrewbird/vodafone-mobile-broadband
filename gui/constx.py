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
                                 MM_NETWORK_BAND_U1800, MM_NETWORK_BAND_U17IV,
                                 MM_NETWORK_BAND_U800, MM_NETWORK_BAND_U850,
                                 MM_NETWORK_BAND_U900, MM_NETWORK_BAND_U17IX,
                                 MM_NETWORK_BAND_U1900)
from wader.common.utils import revert_dict

from gui.translate import _

BAND_MAP = {
    MM_NETWORK_BAND_ANY: _('Any'),
    MM_NETWORK_BAND_EGSM: _('EGSM 900'),
    MM_NETWORK_BAND_DCS: _('GSM DCS'),
    MM_NETWORK_BAND_PCS: _('GSM PCS'),
    MM_NETWORK_BAND_G850: _('GSM 850'),
    MM_NETWORK_BAND_U2100: _('WCDMA 2100'),
    MM_NETWORK_BAND_U1800: _('WCDMA 1800'),
    MM_NETWORK_BAND_U17IV: _('WCDMA 17IV'),
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
GUI_NETWORK_AUTH_ANY = 0xff
GUI_NETWORK_AUTH_PAP = 0x01
GUI_NETWORK_AUTH_EAP = 0x02
GUI_NETWORK_AUTH_CHAP = 0x04
GUI_NETWORK_AUTH_MSCHAP = 0x08
GUI_NETWORK_AUTH_MSCHAPv2 = 0x10

AUTH_MAP = {
    GUI_NETWORK_AUTH_ANY: _('Any'),
    GUI_NETWORK_AUTH_PAP: _('PAP'),
    GUI_NETWORK_AUTH_EAP: _('EAP'),
    GUI_NETWORK_AUTH_CHAP: _('CHAP'),
    GUI_NETWORK_AUTH_MSCHAP: _('MSCHAP'),
    GUI_NETWORK_AUTH_MSCHAPv2: _('MSCHAPv2'),
}
AUTH_MAP_REV = revert_dict(AUTH_MAP)

GUI_MODEM_STATE_UNKNOWN = MM_MODEM_STATE_UNKNOWN       #  0
GUI_MODEM_STATE_NODEVICE = MM_MODEM_STATE_UNKNOWN + 1
GUI_MODEM_STATE_HAVEDEVICE = MM_MODEM_STATE_UNKNOWN + 2
GUI_MODEM_STATE_DISABLED = MM_MODEM_STATE_DISABLED     # 10
GUI_MODEM_STATE_DISABLING = MM_MODEM_STATE_DISABLING   # 20
GUI_MODEM_STATE_LOCKED = MM_MODEM_STATE_DISABLING + 1
GUI_MODEM_STATE_UNLOCKING = MM_MODEM_STATE_DISABLING + 2
GUI_MODEM_STATE_UNLOCKED = MM_MODEM_STATE_DISABLING + 3
GUI_MODEM_STATE_ENABLING = MM_MODEM_STATE_ENABLING     # 30
GUI_MODEM_STATE_ENABLED = MM_MODEM_STATE_ENABLED
GUI_MODEM_STATE_SEARCHING = MM_MODEM_STATE_SEARCHING
GUI_MODEM_STATE_REGISTERED = MM_MODEM_STATE_REGISTERED
GUI_MODEM_STATE_DISCONNECTING = MM_MODEM_STATE_DISCONNECTING
GUI_MODEM_STATE_CONNECTING = MM_MODEM_STATE_CONNECTING
GUI_MODEM_STATE_CONNECTED = MM_MODEM_STATE_CONNECTED

GUI_SIM_AUTH_NONE, GUI_SIM_AUTH_PIN, \
GUI_SIM_AUTH_PUK, GUI_SIM_AUTH_PUK2 = range(4)

GUI_VIEW_DISABLED, GUI_VIEW_IDLE, GUI_VIEW_BUSY = range(3)
