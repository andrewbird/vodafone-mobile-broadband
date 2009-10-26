# -*- coding: utf-8 -*-
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

from os.path import join, expanduser

from wader.common.consts import (MM_NETWORK_MODE_ANY, MM_NETWORK_MODE_GPRS,
                                 MM_NETWORK_MODE_EDGE, MM_NETWORK_MODE_UMTS,
                                 MM_NETWORK_MODE_HSDPA, MM_NETWORK_MODE_HSUPA,
                                 MM_NETWORK_MODE_2G_PREFERRED,
                                 MM_NETWORK_MODE_3G_PREFERRED,
                                 MM_NETWORK_MODE_2G_ONLY, MM_NETWORK_MODE_HSPA,
                                 MM_NETWORK_MODE_3G_ONLY,
                                 MM_NETWORK_BAND_ANY, MM_NETWORK_BAND_EGSM,
                                 MM_NETWORK_BAND_DCS, MM_NETWORK_BAND_PCS,
                                 MM_NETWORK_BAND_G850, MM_NETWORK_BAND_U2100,
                                 MM_NETWORK_BAND_U1700, MM_NETWORK_BAND_17IV,
                                 MM_NETWORK_BAND_U800, MM_NETWORK_BAND_U850,
                                 MM_NETWORK_BAND_U900, MM_NETWORK_BAND_U17IX,
                                 MM_NETWORK_BAND_U1900)
from wader.common.utils import revert_dict
from wader.vmc.translate import _

APP_NAME = 'Vodafone Mobile Connect'
APP_SLUG_NAME = 'wader-vmc'
APP_LONG_NAME = 'Vodafone Mobile Connect'
APP_SHORT_NAME = APP_SLUG_NAME
APP_VERSION = '3.00.0'

# credits
APP_AUTHORS = ['Andrew Bird <ajb@spheresystems.co.uk>',
                'Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
               'Vicente Hernando <bizenton@gmail.com>',
                'Pablo Martí Gamboa <pmarti@warp.es>',
               'Jaime Soriano Pastor <jsoriano@warp.es>']
APP_DOCUMENTERS = ['Pablo Martí Gamboa <pmarti@warp.es>',
                   'Enrique Matias Sanchez <cronopios@gmail.com>',
                   'Jaime Soriano Pastor <jsoriano@warp.es>']
APP_ARTISTS = ['Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
                'Pablo Martí Gamboa <pmarti@warp.es>',
               'Jaime Soriano Pastor <jsoriano@warp.es>',
               'Daniel Baeyens <dbaeyens@warp.es>',
               'Splash by Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
          'Original glade by María Iglesias Barroso <miglesias@imssystem.net>'
          ]

#APP_URL = 'https://forge.betavine.net/projects/vodafonemobilec/'
APP_URL = 'http://www.betavine.net/bvportal/resources/datacards'

DATA_DIR = '/usr/share/%s' % APP_SLUG_NAME
RESOURCES_DIR = join(DATA_DIR, 'resources')

GLADE_DIR = join(RESOURCES_DIR, 'glade')
IMAGES_DIR = join(RESOURCES_DIR, 'glade')
THEMES_DIR = join(RESOURCES_DIR, 'themes')
GUIDE_DIR = join('/usr/share/doc', APP_SLUG_NAME)

GTK_LOCK = join('/tmp', '.wader-vmc-lock')

USER_HOME = expanduser('~')
# TODO: should we change WADER_HOME to wader-vmc?
WADER_HOME = join(USER_HOME, '.gnome2', 'wader')

# NETWORKS_DB is a deprecated path
DB_DIR = join(WADER_HOME, 'db')
NETWORKS_DB = join(DB_DIR, 'networks.db')

GCONF_BASE_DIR = '/apps/wader-vmc'

BAND_MAP = {
    MM_NETWORK_BAND_ANY   : _('Any band'),
    MM_NETWORK_BAND_EGSM  : _('EGSM 900'),
    MM_NETWORK_BAND_DCS   : _('GSM DCS'),
    MM_NETWORK_BAND_PCS   : _('GSM PCS'),
    MM_NETWORK_BAND_G850  : _('GSM 850'),
    MM_NETWORK_BAND_U2100 : _('WCDMA 2100'),
    MM_NETWORK_BAND_U1700 : _('WCDMA 1700'),
    MM_NETWORK_BAND_17IV  : _('WCDMA 17IV'),
    MM_NETWORK_BAND_U800  : _('WCDMA 800'),
    MM_NETWORK_BAND_U850  : _('WCDMA 850'),
    MM_NETWORK_BAND_U900  : _('WCDMA 900'),
    MM_NETWORK_BAND_U17IX : _('WCDMA 17IX'),
    MM_NETWORK_BAND_U1900 : _('WCDMA 1900'),
}

BAND_MAP_REV = revert_dict(BAND_MAP)

MODE_MAP = {
    MM_NETWORK_MODE_ANY   : _('Any'),
    MM_NETWORK_MODE_GPRS  : _('GPRS'),
    MM_NETWORK_MODE_EDGE  : _('EDGE'),
    MM_NETWORK_MODE_UMTS  : _('UMTS'),
    MM_NETWORK_MODE_HSDPA : _('HSDPA'),
    MM_NETWORK_MODE_HSUPA : _('HSUPA'),
    MM_NETWORK_MODE_HSPA  : _('HSPA'),
    MM_NETWORK_MODE_2G_PREFERRED : _('2G preferred'),
    MM_NETWORK_MODE_3G_PREFERRED : _('3G preferred'),
    MM_NETWORK_MODE_2G_ONLY : _('2G only'),
    MM_NETWORK_MODE_3G_ONLY : _('3G only'),
}

MODE_MAP_REV = revert_dict(MODE_MAP)

# We don't have any values for authentication methods
# in common.consts, so we'll have to invent them here
# for now
VM_NETWORK_AUTH_ANY      = 0xff
VM_NETWORK_AUTH_PAP      = 0x01
VM_NETWORK_AUTH_EAP      = 0x02
VM_NETWORK_AUTH_CHAP     = 0x04
VM_NETWORK_AUTH_MSCHAP   = 0x08
VM_NETWORK_AUTH_MSCHAPv2 = 0x10

AUTH_MAP = {
    VM_NETWORK_AUTH_ANY      : _('Default'),
    VM_NETWORK_AUTH_PAP      : _('PAP'),
    VM_NETWORK_AUTH_EAP      : _('EAP'),
    VM_NETWORK_AUTH_CHAP     : _('CHAP'),
    VM_NETWORK_AUTH_MSCHAP   : _('MSCHAP'),
    VM_NETWORK_AUTH_MSCHAPv2 : _('MSCHAPv2'),
}

AUTH_MAP_REV = revert_dict(AUTH_MAP)

CFG_PREFS_DEFAULT_BROWSER = 'xdg-open'
CFG_PREFS_DEFAULT_EMAIL   = 'xdg-email'
