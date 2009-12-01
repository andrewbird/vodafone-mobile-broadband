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

from wader.common.consts import MM_NETWORK_BANDS, MM_NETWORK_BAND_ANY

from wader.vmc.consts import (GLADE_DIR, VM_NETWORK_AUTH_ANY,
                              VM_NETWORK_AUTH_PAP, VM_NETWORK_AUTH_CHAP,
                              BAND_MAP, MODE_MAP, AUTH_MAP)
from wader.vmc.translate import _


class ProfileView(View):

    GLADE_FILE = join(GLADE_DIR, "profiles.glade")
    IMAGE_FILE = join(GLADE_DIR, "proedt.png")

    def __init__(self, ctrl):
        super(ProfileView, self).__init__(ctrl, self.GLADE_FILE,
                                          'new_profile_window')

        ctrl.setup_view(self)
        self['PROimage'].set_from_file(self.IMAGE_FILE)
        self['static_dns_check'].connect('toggled', self.on_static_dns_toggled)
        icon = gtk.gdk.pixbuf_new_from_file(join(GLADE_DIR, 'VF_logo.png'))
        self.get_top_widget().set_icon(icon)

    def _set_combo(self, combo, model, current):
        self[combo].set_model(model)
        if current:
            for i, row in enumerate(model):
                if row[1] == current:
                    self[combo].set_active(i)
                    break

    def set_bands(self, bands, current):

        def get_bands(bitwised_band):
            """Returns all the bitwised bands in ``bitwised_band``"""
            return [band for band in MM_NETWORK_BANDS if band & bitwised_band]

        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        for value in [MM_NETWORK_BAND_ANY] + get_bands(bands):
            human_name = BAND_MAP[value]
            model.append([human_name, value])

        self._set_combo('band_combobox', model, current)

    def set_prefs(self, prefs, current):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        for value in prefs:
            human_name = MODE_MAP[value]
            model.append([human_name, value])

        self._set_combo('connection_combobox', model, current)

    def set_auths(self, current):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        for value in [VM_NETWORK_AUTH_ANY,
                      VM_NETWORK_AUTH_PAP,
                      VM_NETWORK_AUTH_CHAP]:
            human_name = AUTH_MAP[value]
            model.append([human_name, value])

        self._set_combo('authentication_combobox', model, current)

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
            self.store.append(None, [profile.name,
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
