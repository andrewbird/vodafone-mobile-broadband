# -*- coding: utf-8 -*-
# Copyright (C) 2006-2012  Vodafone España, S.A.
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

# Note: No wader.* imports are allowed in this file, if you need those then
#       please put your new consts in constx.py, else we get issues building
#       packages and with circular imports.

APP_NAME = 'V Mobile Broadband'
APP_SLUG_NAME = 'v-mobile-broadband'
APP_LONG_NAME = 'V Mobile Broadband'
APP_SHORT_NAME = 'vmb'
APP_VERSION = '3.00.01'

# credits
APP_AUTHORS = [
    'Andrew Bird <ajb@spheresystems.co.uk>',
    'Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
    'Vicente Hernando <bizenton@gmail.com>',
    'Pablo Martí Gamboa <pmarti@warp.es>',
    'Jaime Soriano Pastor <jsoriano@warp.es>']

APP_DOCUMENTERS = [
    'Pablo Martí Gamboa <pmarti@warp.es>',
    'Enrique Matias Sanchez <cronopios@gmail.com>',
    'Jaime Soriano Pastor <jsoriano@warp.es>']

APP_ARTISTS = [
    'Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
    'Pablo Martí Gamboa <pmarti@warp.es>',
    'Jaime Soriano Pastor <jsoriano@warp.es>',
    'Daniel Baeyens <dbaeyens@warp.es>',
    'Splash by Nicholas Herriot <Nicholas.Herriot@vodafone.com>',
    'Original glade by María Iglesias Barroso <miglesias@imssystem.net>']

APP_URL = 'http://www.betavine.net/bvportal/resources/datacards'

DATA_DIR = '/usr/share/%s' % APP_SLUG_NAME
RESOURCES_DIR = join(DATA_DIR, 'resources')

GLADE_DIR = join(RESOURCES_DIR, 'glade')
IMAGES_DIR = join(RESOURCES_DIR, 'glade')
ANIMATION_DIR = join(IMAGES_DIR, 'animation')
GUIDE_DIR = join('/usr/share/doc', APP_SLUG_NAME)

GTK_LOCK = join('/tmp', '.%s-lock' % APP_SLUG_NAME)

USER_HOME = expanduser('~')
GUI_HOME = join(USER_HOME, '.%s' % APP_SLUG_NAME)

LOG_FILE = join(GUI_HOME, 'log')

DB_DIR = join(GUI_HOME, 'db')
MESSAGES_DB = join(DB_DIR, 'messages.db')
USAGE_DB = join(DB_DIR, 'usage.db')

GCONF_BASE_DIR = '/apps/%s' % APP_SLUG_NAME

CFG_PREFS_DEFAULT_BROWSER = 'xdg-open'
CFG_PREFS_DEFAULT_EMAIL = 'xdg-email'
CFG_PREFS_DEFAULT_TRAY_ICON = True
CFG_PREFS_DEFAULT_CLOSE_MINIMIZES = False
CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION = False
CFG_PREFS_DEFAULT_USAGE_USER_LIMIT = 5
CFG_PREFS_DEFAULT_USAGE_MAX_VALUE = 20

CFG_SMS_VALIDITY_R1D = '1day'
CFG_SMS_VALIDITY_R3D = '3days'
CFG_SMS_VALIDITY_R1W = '1week'
CFG_SMS_VALIDITY_MAX = 'maximum'
CFG_PREFS_DEFAULT_SMS_VALIDITY = CFG_SMS_VALIDITY_R1W
CFG_PREFS_DEFAULT_SMS_CONFIRMATION = False

TV_CNT_TYPE, TV_CNT_NAME, TV_CNT_NUMBER, TV_CNT_EDITABLE, TV_CNT_OBJ = range(5)
TV_SMS_TYPE, TV_SMS_TEXT, TV_SMS_NUMBER, TV_SMS_DATE, TV_SMS_OBJ = range(5)
