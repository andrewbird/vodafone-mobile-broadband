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
View for the profile window
"""

from os.path import join

import gtk
import gobject
from gtkmvc import View

from wader.common.consts import MM_NETWORK_BAND_ANY, MM_NETWORK_MODE_ANY

from wader.vmc.consts import (GLADE_DIR, VM_NETWORK_AUTH_ANY,
                              BAND_MAP, MODE_MAP, AUTH_MAP)
from wader.vmc.translate import _


class ProfileView(View):

    GLADE_FILE = join(GLADE_DIR, "profiles.glade")
    IMAGE_FILE = join(GLADE_DIR, "proedt.png")

    def __init__(self, ctrl):
        super(ProfileView, self).__init__(ctrl, self.GLADE_FILE,
                                          'new_profile_window')

        self._init_combobox(BAND_MAP, 'band', MM_NETWORK_BAND_ANY, self.set_band)
        self._init_combobox(MODE_MAP, 'connection', MM_NETWORK_MODE_ANY, self.set_pref)
        self._init_combobox(AUTH_MAP, 'authentication', VM_NETWORK_AUTH_ANY, self.set_auth)

        ctrl.setup_view(self)
        self['PROimage'].set_from_file(self.IMAGE_FILE)
        self['static_dns_check'].connect('toggled', self.on_static_dns_toggled)
        icon = gtk.gdk.pixbuf_new_from_file(join(GLADE_DIR, 'VF_logo.png'))
        self.get_top_widget().set_icon(icon)

    def _init_combobox(self, _dict, name, default, method):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        for value, human_name in _dict.items():
            model.append([human_name, value])

        self['%s_combobox' % name].set_model(model)
        method(default)

    def set_band(self, band):
        if band:
            model = self['band_combobox'].get_model()
            for i, row in enumerate(model):
                if row[1] == band:
                    self['band_combobox'].set_active(i)
                    break

    def set_pref(self, pref):
        if pref:
            model = self['connection_combobox'].get_model()
            for i, row in enumerate(model):
                if row[1] == pref:
                    self['connection_combobox'].set_active(i)
                    break

    def set_auth(self, auth):
        if auth:
            model = self['authentication_combobox'].get_model()
            for i, row in enumerate(model):
                if row[1] == auth:
                    self['authentication_combobox'].set_active(i)
                    break

    def on_static_dns_toggled(self, widget):
        if widget.get_active():
            self.enable_static_dns()
        else:
            self.disable_static_dns()

    def disable_static_dns(self):
        self['primary_dns_entry'].set_sensitive(False)
        self['secondary_dns_entry'].set_sensitive(False)
        if self['static_dns_check'].get_active():
            self['static_dns_check'].set_active(False)

    def enable_static_dns(self):
        self['primary_dns_entry'].set_sensitive(True)
        self['secondary_dns_entry'].set_sensitive(True)
        if not self['static_dns_check'].get_active():
            self['static_dns_check'].set_active(True)


class APNSelectionView(View):
    GLADE_FILE = join(GLADE_DIR, "apnsel.glade")
    IMAGE_FILE = join(GLADE_DIR, "apnsel.png")

    def __init__(self, ctrl):
        super(APNSelectionView, self).__init__(ctrl, self.GLADE_FILE,
                                               'apn_selection_window',
                                               register=False)
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self._view = self['apn_list_treeview']
        self['APNimage'].set_from_file(self.IMAGE_FILE)

        # init columns
        render_text = gtk.CellRendererText()
        col0 = gtk.TreeViewColumn(_('Name'))
        col0.pack_start(render_text, expand=True)
        col0.add_attribute(render_text, 'text', 0)
        self._view.append_column(col0)

        col1 = gtk.TreeViewColumn(_('Country'))
        col1.pack_start(render_text, expand=True)
        col1.add_attribute(render_text, 'text', 1)
        self._view.append_column(col1)

        col2 = gtk.TreeViewColumn(_('Type'))
        col2.pack_start(render_text, expand=True)
        col2.add_attribute(render_text, 'text', 2)
        self._view.append_column(col2)

    def populate(self, profiles):
        # name, country, type, profile object
        self.store = gtk.TreeStore(gobject.TYPE_STRING,
                                   gobject.TYPE_STRING,
                                   gobject.TYPE_STRING,
                                   gobject.TYPE_PYOBJECT)
        self._view.set_model(self.store)

        # load data
        for profile in profiles:
            self.store.append(None,[profile.name,
                                    profile.country,
                                    profile.type,
                                    profile])

        # select the first row
        iter = self.store.get_iter(0)
        if iter:
            self._view.get_selection().select_iter(iter)

    def get_selected_apn(self):
        model, selected = self._view.get_selection().get_selected_rows()
        if model is None:
            return None
        if not selected:
            _iter = model.get_iter(0)    # 1st row if no selection
        else:
            _iter = model.get_iter(selected[0])
        return model.get_value(_iter, 3) # the object

