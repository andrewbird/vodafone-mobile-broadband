# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone
# Author:  Pablo Martí and Nicholas Herriot
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

import dbus
import gobject
from gtkmvc import Model, ListStoreModel

from wader.common.utils import revert_dict
from wader.vmc.logger import logger
from wader.vmc.translate import _
from wader.vmc.config import config
from wader.vmc.consts import (CFG_PREFS_DEFAULT_BROWSER,
                              CFG_PREFS_DEFAULT_EMAIL,
                              CFG_PREFS_DEFAULT_TRAY_ICON,
                              CFG_PREFS_DEFAULT_CLOSE_MINIMIZES,
                              CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION)

PREF_TABS = ["PROFILES"]

VALIDITY_DICT = {
     _('Maximum time').encode('utf8'): 'maximum',
     _('1 week').encode('utf8'): '1week',
     _('3 days').encode('utf8'): '3days',
     _('1 day').encode('utf8'): '1day',
}

VALIDITY_DICT_REV = revert_dict(VALIDITY_DICT)


class PreferencesModel(Model):

    __properties__ = {
        'current_tab': PREF_TABS[0],
        'default_profile': None,
        'warn_limit': False,
        'transfer_limit': -1,
        'use_alternate_smsc': False,
        'validities': VALIDITY_DICT,
        'smsc_profile': "default",
        'smsc_number': "+447785016005",
        'smsc_validity': "maximum",
        'exit_without_confirmation': CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION,
        'show_icon': CFG_PREFS_DEFAULT_TRAY_ICON,
        'close_minimizes': CFG_PREFS_DEFAULT_CLOSE_MINIMIZES,
        'manage_my_keyring': False,
        'max_traffic': 10,
        'traffic_threshold': 100,
        'usage_notification': False,
        'browser': CFG_PREFS_DEFAULT_BROWSER,
        'mail': CFG_PREFS_DEFAULT_EMAIL,
    }

    def __init__(self, device_callable):
        super(PreferencesModel, self).__init__()
        self.bus = dbus.SystemBus()
        self.conf = config
        self.device_callable = device_callable
        self.load()

    def load(self):
        self.warn_limit = self.conf.get('statistics', 'warn_limit', True)
        self.transfer_limit = self.conf.get('statistics', 'transfer_limit', 50.0)

        # ok lets load the SMS preferences from the configuration file.
        # but take care! If the config file is absent set to default values.
        self.use_alternate_smsc = self.conf.get('preferences',
                                                'use_alternate_smsc', False)

        self.smsc_profile = self.conf.get('preferences', 'smsc_profile',
                                          'Vodafone UK United Kingdon')

        self.smsc_number = self.conf.get('preferences', 'smsc_number',
                                         '+447785016005')

        self.smsc_validity = self.conf.get('preferences', 'smsc_validity',
                                           'maximum')

        # ok lets load the user preferences from configuration file into the
        # model but take care! If the config file is absent set to false!
        self.exit_without_confirmation = config.get('preferences',
                                                  'exit_without_confirmation',
                                   CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION)

        self.show_icon = config.get('preferences', 'show_icon',
                                    CFG_PREFS_DEFAULT_TRAY_ICON)

        self.close_minimizes = config.get('preferences', 'close_minimizes',
                                    CFG_PREFS_DEFAULT_CLOSE_MINIMIZES)

        self.manage_my_keyring = config.get('preferences', 'manage_my_keyring')
        if (self.manage_my_keyring==''):
            print "model: Warning! self.manage_my_keyring is NULL"
            self.manage_my_keyring = False

        # ok lets load the application values from configuration file
        self.browser = config.get('preferences', 'browser',
                                  CFG_PREFS_DEFAULT_BROWSER)
        self.mail = config.get('preferences', 'mail', CFG_PREFS_DEFAULT_EMAIL)

        # ok lets load the usage values from configuration file
        self.max_traffic = config.get('preferences', 'max_traffic', 100)

        self.traffic_threshold = config.get('preferences',
                                            'traffic_threshold', 10)

        self.usage_notification = config.get('preferences',
                                             'usage_notification', False)

    def save(self):
        #self.conf.set('statistics', 'warn_limit', self.warn_limit)
        #self.conf.set('statistics', 'transfer_limit', self.transfer_limit)

        # Save all the attributes on the SMS tab
        config.set('preferences', 'use_alternate_smsc',
                   self.use_alternate_smsc)
        config.set('preferences', 'smsc_profile', self.smsc_profile)
        config.set('preferences', 'smsc_number', self.smsc_number)
        config.set('preferences', 'smsc_validity', self.smsc_validity)

        # Save all the attributes on the user preferences tab
        config.set('preferences', 'exit_without_confirmation',
                   self.exit_without_confirmation)
        config.set('preferences', 'show_icon', self.show_icon)
        config.set('preferences', 'close_minimizes', self.close_minimizes)
        config.set('preferences', 'manage_my_keyring', self.manage_my_keyring)

        # Save all the attributes on the applications tab
        config.set('preferences', 'browser', self.browser)
        config.set('preferences', 'mail', self.mail)

        # Save all the attributes on the usage tab
        config.set('preferences', 'max_traffic', int(self.max_traffic))
        config.set('preferences', 'traffic_threshold', int(self.traffic_threshold))
        config.set('preferences', 'usage_notification', self.usage_notification)

    def reset_statistics(self):
        logger.info('Resetting total bytes')
        # self.parent.total_bytes = 0
        self.conf.set('statistics', 'total_bytes', 0)


class SMSCListStoreModel(ListStoreModel):
    """Store Model for smsc list combobox"""

    def __init__(self):
        super(SMSCListStoreModel, self).__init__(gobject.TYPE_PYOBJECT)
        self.active = None

    def add_smscs(self, smsc_list):
        return map(self.add_smsc, smsc_list)

    def add_smsc(self, smscobj):
        if smscobj.active:
            self.active = self.append([smscobj])
            return self.active

        return self.append([smscobj])


class SMSCItem(object):

    def __init__(self, message, number=None, active=True):
        self.message = message
        self.number = number
        self.active = active
