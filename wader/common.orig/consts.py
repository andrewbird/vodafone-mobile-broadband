# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
# Author:  Pablo Martí, Nicholas Herriot, Andrew Bird
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
VMC's global variables
"""
__version__ = "$Rev: 788 $"

from os.path import join, expanduser
from consts_prefix import TOP_DIR

# app name
APP_SHORT_NAME = 'VMCCdfL'
APP_LONG_NAME = 'Vodafone Mobile Connect'
APP_VERSION = '2.15.01'
APP_SLUG_NAME = 'vodafone-mobile-connect'
APP_URL = 'https://forge.betavine.net/projects/vodafonemobilec/'

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

DATA_DIR = join(TOP_DIR, 'usr', 'share', '%s' % APP_SLUG_NAME)
GUIDE_DIR = join(TOP_DIR, 'usr', 'share', 'doc', '%s' % APP_SLUG_NAME, 'guide')

# paths
RESOURCES_DIR = join(DATA_DIR, 'resources')
GLADE_DIR = join(RESOURCES_DIR, 'glade')
IMAGES_DIR = join(RESOURCES_DIR, 'glade')
TEMPLATES_DIR = join(RESOURCES_DIR, 'templates')
HELP_DIR = join(RESOURCES_DIR, 'help')
EXTRA_DIR = join(RESOURCES_DIR, 'extra')

NETWORKS_CSV = join(EXTRA_DIR, 'networks.csv')
SMSCLIST_CSV = join(EXTRA_DIR, 'smsc-list.csv')

# TEMPLATES
WVTEMPLATE = join(TEMPLATES_DIR, 'wvdial.conf.tpl')
REPTEMPLATE = join(TEMPLATES_DIR, 'support_report.tpl')
PROFTEMPLATE = join(TEMPLATES_DIR, 'new_profile.tpl')

USER_HOME = expanduser('~')
VMC_HOME = join(USER_HOME, '.vmc2')
VMC_CFG = join(VMC_HOME, 'vmc.cfg')
VMC_DOC = join(TOP_DIR, 'usr', 'share', 'doc', '%s' % APP_SLUG_NAME, 'guide')

FAKE_GCONF = join(VMC_HOME, 'fake-gconf.dat')

# profiles stuff
MOBILE_PROFILES = join(VMC_HOME, 'mobile-profiles')
CACHED_DEVICES = join(VMC_HOME, 'cached-devices')

# plugins stuff
PLUGINS_DIR = join(DATA_DIR, 'plugins')
PLUGINS_HOME = join(VMC_HOME, 'plugins')
USER_PLUGINS = [PLUGINS_HOME,
                join(PLUGINS_HOME, 'devices'),
                join(PLUGINS_HOME, 'os'),
                join(PLUGINS_HOME, 'notifications')]

# Dialers & Wvdial stuff
DIALER_PROFILES = join(VMC_HOME, 'dialer-profiles')
WVDIAL_AUTH_CONF = join(TOP_DIR, 'etc', 'ppp', 'peers', 'wvdial')

DEFAULT_PROFILE = join(DIALER_PROFILES, 'default')
PAP_PROFILE = join(DIALER_PROFILES, 'PAP')
CHAP_PROFILE = join(DIALER_PROFILES, 'CHAP')

# databases, they should be merged in the future
CONTACTS_DB = join(VMC_HOME, 'contacts.db')
MESSAGES_DB = join(VMC_HOME, 'messages.db')
SMSC_DB = join(VMC_HOME, 'smsc.db')
USAGE_DB = join(VMC_HOME, 'usage.db')

# static dns stuff
VMC_DNS_LOCK = join('/tmp', 'vmc-conn.lock')

# intronspection
SSH_PORT = "2222"
