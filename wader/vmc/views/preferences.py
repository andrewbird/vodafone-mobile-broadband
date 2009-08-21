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
"""View for the preferences window"""
__version__ = "$Rev: 1172 $"

import os.path

import gobject
import gtk

from wader.vmc import View
import wader.common.consts as consts
from wader.common.config import config
from wader.common.dialers import AUTH_OPTS_DICT_REV
from wader.common.dialers import get_profiles_list
from wader.common.encoding import _
from wader.vmc.models.preferences import SMSCListStoreModel

class PreferencesView(View):
    """View for the preferences window"""

    GLADE_FILE = os.path.join(consts.GLADE_DIR, "preferences.glade")

    def __init__(self, ctrl, device):
        super(PreferencesView, self).__init__(ctrl, self.GLADE_FILE,
            'preferences_window', register=False, domain="VMC")
        self.device = device
        self.ctrl = ctrl
        ctrl.register_view(self)
        self.setup_view()

    def setup_view(self):
        # first page of the notebook
        profile = config.current_profile.get('connection', 'dialer_profile')

        if profile == 'default':
            self['vbox2'].set_sensitive(False)
        else:
            self['custom_profile_checkbutton'].set_active(True)

        # third page of the notebook
        exit_without_confirmation = config.getboolean('preferences',
                                                'exit_without_confirmation')
        chkbt = self['exit_without_confirmation_checkbutton']
        chkbt.set_active(exit_without_confirmation)

        show_icon = config.getboolean('preferences', 'close_minimizes')
        self['show_icon_checkbutton'].set_active(show_icon)

        minimize_to_tray = config.getboolean('preferences', 'close_minimizes')
        if show_icon:
            self['close_window_checkbutton'].set_active(minimize_to_tray)
        else:
            self['close_window_checkbutton'].set_sensitive(False)

        manage_keyring = config.getboolean('preferences', 'manage_keyring')
        self['gnomekeyring_checkbutton'].set_active(manage_keyring)

        #setup dialer_combobox
        self.setup_dialer_combobox()

        self.setup_browser_combobox()
        self.setup_mail_combobox()

        self.setup_usage_options()

    # second notebook page
    def setup_dialer_combobox(self):
        model = self.get_dialer_combobox_model()
        self['dialer_profiles_combobox'].set_model(model)

        profile = config.current_profile.get('connection', 'dialer_profile')
        self.select_dialer_combobox_option(model, profile)

    def get_dialer_combobox_model(self):
        model = gtk.ListStore(gobject.TYPE_STRING)
        for profile in get_profiles_list():
            model.append([profile])

        return model

    def select_dialer_combobox_option(self, model, profile):
        for i, row in enumerate(model):
            if row[0].lower() == AUTH_OPTS_DICT_REV[profile].lower():
                self['dialer_profiles_combobox'].set_active(i)
                break

    # third page
    def setup_browser_combobox(self):
        model = gtk.ListStore(gobject.TYPE_STRING)
        xdg_iter = model.append(['xdg-open'])
        custom_iter = model.append([_('Custom')])
        self['browser_combobox'].set_model(model)

        binary = config.get('preferences', 'browser')
        _iter = (binary == 'xdg-open') and xdg_iter or custom_iter
        self['browser_combobox'].set_active_iter(_iter)

        if binary != 'xdg-open':
            self['browser_entry'].set_text(binary)

    def setup_mail_combobox(self):
        model = gtk.ListStore(gobject.TYPE_STRING)
        xdg_iter = model.append(['xdg-email'])
        custom_iter = model.append([_('Custom')])
        self['mail_combobox'].set_model(model)

        binary = config.get('preferences', 'mail')
        _iter = (binary == 'xdg-email') and xdg_iter or custom_iter
        self['mail_combobox'].set_active_iter(_iter)

        if binary != 'xdg-email':
            self['mail_entry'].set_text(binary)

    # fourth page
    def setup_usage_options(self):
        #XXX: From Current Profile if any?
        max_traffic = config.getint('preferences', 'max_traffic')
        threshold = config.getint('preferences', 'traffic_threshold')
        usage_notification = \
                    config.getboolean('preferences', 'usage_notification')
        self['maximum_traffic_entry'].set_value(max_traffic)
        self['threshold_entry'].set_value(threshold)
        self['usage_notification_check'].set_active(usage_notification)
        self['threshold_entry'].set_sensitive(usage_notification)


class SMSPreferencesView(View):
    """View for the SMS preferences window"""
    GLADE_FILE = os.path.join(consts.GLADE_DIR,
                              "sms-preferences.glade")

    def __init__(self, ctrl, parent_ctrl):
        super(SMSPreferencesView, self).__init__(ctrl, self.GLADE_FILE,
            'sms_preferences', register=False, domain="VMC")
        self.parent_ctrl = parent_ctrl
        self.setup_view(ctrl)
        ctrl.register_view(self)

    def setup_view(self, ctrl):
        self.get_top_widget().set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self['alignment5'].add(ctrl.smsc_entry)

    def populate_smsc_combobox(self, smsc_list):
        model = SMSCListStoreModel()
        model.add_smscs(smsc_list)
        combobox = self['combobox1']

        cell = gtk.CellRendererText()
        combobox.pack_end(cell, False)
        def render_pyobj(cellview, cell, model, iter):
            pyobj = model.get_value(iter, 0)
            if pyobj:
                cell.set_property('text', pyobj.message)

        combobox.set_cell_data_func(cell, render_pyobj)
        combobox.set_model(model)
        if model.active:
            combobox.set_active_iter(model.active)

