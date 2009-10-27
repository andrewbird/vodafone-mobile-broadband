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
Client for gnomekeyring
"""

import gnomekeyring

try:
    import gconf
except ImportError:
    import vmc.contrib.fakegconf as gconf

from wader.common.consts import APP_SLUG_NAME as slug, APP_LONG_NAME

class KeyringClient(object):
    """
    Client for gnome-keyring

    I associate the IMEI of a device with a PIN. Less stuff to remember for
    the user. The only drawback is what if the user changes the SIM of its
    device? Won't work :)
    """
    def __init__(self):
        self.keyring = gnomekeyring.get_default_keyring_sync()

    def delete(self, auth_token):
        """
        Deletes C{auth_token} from the keyring as its faulty
        """
        try:
            gnomekeyring.item_delete_sync(self.keyring, auth_token)
        except Exception, e:
            raise

    def register(self, device, pin):
        """
        Register C{pin} for C{device}
        """
        d = device.sconn.get_imei()
        def imei_cb(imei):
            gconf_key = "/apps/%s/%s/keyring_auth_token" % (slug, imei)
            auth_token = gnomekeyring.item_create_sync(
                self.keyring,
                gnomekeyring.ITEM_GENERIC_SECRET,
                "%s secrets!" % APP_LONG_NAME,
                dict(appname=APP_LONG_NAME),
                str(pin), True)
            gconf.client_get_default().set_int(gconf_key, auth_token)
            return auth_token

        d.addCallback(imei_cb)
        return d

    def get_pin(self, device):
        """
        Returns the PIN associated with C{device}
        """
        d = device.sconn.get_imei()
        def imei_cb(imei):
            gconf_key = "/apps/%s/%s/keyring_auth_token" % (slug, imei)
            auth_token = gconf.client_get_default().get_int(gconf_key)
            if auth_token > 0:
                try:
                    pin = gnomekeyring.item_get_info_sync(self.keyring,
                                                    auth_token).get_secret()
                except:
                    raise
                else:
                    return (pin, auth_token)

        d.addCallback(imei_cb)
        return d
