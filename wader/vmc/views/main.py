# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano
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
Views for the main interface
"""

import os

import gtk
from gtkmvc import View

from wader.vmc.translate import _
from wader.vmc.consts import GLADE_DIR, THEMES_DIR, APP_LONG_NAME

THROBBER = gtk.gdk.PixbufAnimation(os.path.join(GLADE_DIR, 'throbber.gif'))

class MainView(View):

    GLADE_FILE = os.path.join(GLADE_DIR, "VMC-reduced.glade")

    def __init__(self, ctrl):
        super(MainView, self).__init__(ctrl, self.GLADE_FILE, 'main_window',
                                       register=True)
        self.throbber = None
        self.theme_ui()

    def theme_ui(self):
        self.get_top_widget().set_title(APP_LONG_NAME)
        theme = os.path.join(THEMES_DIR, "default.gtkrc")
        gtk.rc_parse(theme)

    def _get_signal_icon(self, rssi):
        if rssi < 10 or rssi > 100:
            return 0

        elif rssi < 25:
            return 1

        elif rssi < 50:
            return 2

        elif rssi < 75:
            return 3

        elif rssi <= 100:
            return 4

    def rssi_changed(self, new_rssi):
        icon = self._get_signal_icon(new_rssi)
        path = os.path.join(GLADE_DIR, '%d.png' % icon)
        self['signal_image'].set_from_file(path)

    def operator_changed(self, new_operator):
        self['operator_label'].set_text(new_operator)

    def tech_changed(self, new_tech):
        self['tech_label'].set_text(new_tech)

    def set_status(self, status):
        self['status_label'].set_text(status)

    def set_initialising(self, enable):
        self['connect_button'].set_sensitive(not enable)
#        self['sms_menuitem'].set_sensitive(not enable)
#        self['preferences_menu_item'].set_sensitive(not enable)

    def set_connected(self):
        self['connect_button'].set_label(_("Disconnect"))

    def set_disconnected(self, device_present=True):
        self['connect_button'].set_label(_("Connect"))
        self['connect_button'].set_active(False)
        self.stop_throbber()
        if not device_present:
            self.set_initialising(True)

    def start_throbber(self):
        if self.throbber is None:
            self.throbber = gtk.Image()
            self['hbox2'].pack_start(self.throbber, expand=False)
            self.throbber.set_from_animation(THROBBER)
            self.throbber.show()

    def stop_throbber(self):
        if self.throbber is not None:
            self.throbber.hide()
            try:
                self['hbox2'].remove(self.throbber)
            except AttributeError:
                pass

            self.throbber = None

