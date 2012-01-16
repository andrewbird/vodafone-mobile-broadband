# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone
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
"""View for the preferences window"""

import os.path

import gobject
import gtk
#from gtkmvc import View
from gui.contrib.gtkmvc import View

from gui.consts import APP_SLUG_NAME, GLADE_DIR
from gui.models.preferences import SMSCListStoreModel


class PreferencesView(View):
    """View for the preferences window"""

    GLADE_FILE = os.path.join(GLADE_DIR, "preferences.glade")

    def __init__(self, ctrl):
        super(PreferencesView, self).__init__(ctrl, self.GLADE_FILE,
                                                'preferences_window',
                                                register=False,
                                                domain=APP_SLUG_NAME)
        self.ctrl = ctrl
        ctrl.register_view(self)

    def setup_alternate_smsc_address_checkbox(self, val):
        self['smsc_profile_checkbutton'].set_active(val)

    def setup_smsc_profile(self, profile_val, active_set,
                           show_sms_preferences):
        self['sms_profiles_combobox'].set_model(profile_val)
        self['sms_profiles_combobox'].set_active_iter(active_set)
        self['vbox14'].set_sensitive(show_sms_preferences)

    def setup_smsc_number(self, smsc_number):
        self['smsc_number'].set_text(smsc_number)

    def setup_sms_message_validity(self, val, active_set):
        self['validity_combobox'].set_model(val)
        if active_set:
            self['validity_combobox'].set_active_iter(active_set)

    def setup_sms_confirmation_checkbox(self, val):
        self['sms_confirmation'].set_active(val)

    def get_sms_combobox_model(self):
        print "get_sms_combobox_model"
        model = gtk.ListStore(gobject.TYPE_STRING)
        return model

    # second notebook page
    # methods are called by the controller to setup the view for user
    # preferences tab in properties. methods are called on initialisation

    def setup_user_exit_without_confirmation(self, val):
        self['exit_without_confirmation_checkbutton'].set_active(val)

    def setup_user_show_icon_on_tray(self, val):
        self['show_icon_checkbutton'].set_active(val)

    def setup_user_close_window_minimize(self, val):
        self['close_window_checkbutton'].set_active(val)

    def setup_user_close_window_minimize_enable(self, sensitive):
        self['close_window_checkbutton'].set_sensitive(sensitive)

    def setup_manage_my_pin(self, val):
        self['gnomekeyring_checkbutton'].set_active(val)

    # third page
    # methods are called by the controller to setup the view for
    # applications tab in properties. methods are called on initialisation

    def setup_application_browser_text_box(self, val):
        self['browser_entry'].set_text(val)

    def setup_application_mail_text_box(self, val):
        self['mail_entry'].set_text(val)

    def setup_application_mail_combo_box(self, val, active_set):
        self['mail_combobox'].set_model(val)
        self['mail_combobox'].set_active_iter(active_set)

    def setup_application_browser_combo_box(self, val, active_set):
        self['browser_combobox'].set_model(val)
        self['browser_combobox'].set_active_iter(active_set)

    # fourth page
    # methods are called by the controller to setup the view
    # for usage options tab. methods are called on initialisation

    def setup_usage_max_traffic_value(self, val):
        print "view: setup_usage_max_traffic_value - :", val
        self['maximum_traffic_entry'].set_value(val)

    def setup_usage_threshold_value(self, val):
        self['threshold_entry'].set_value(val)

    def setup_usage_notification_check(self, val):
        self['usage_notification_check'].set_active(val)


class SMSPreferencesView(View):
    """View for the SMS preferences window"""
    GLADE_FILE = os.path.join(GLADE_DIR, "sms-preferences.glade")

    def __init__(self, ctrl, parent_ctrl):
        super(SMSPreferencesView, self).__init__(ctrl, self.GLADE_FILE,
                                                    'sms_preferences',
                                                    register=False,
                                                    domain=APP_SLUG_NAME)
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
