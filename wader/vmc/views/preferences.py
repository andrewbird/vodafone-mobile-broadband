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
View for the preferences window
"""

from os.path import join

import gtk
import gobject
from gtkmvc import View

from wader.vmc.translate import _
from wader.vmc.consts import GLADE_DIR

PROFILES_FRAME, STATISTICS_FRAME = range(2)
PREFERENCES_FRAMES = (PROFILES_FRAME, STATISTICS_FRAME)
PREFERENCES_LABEL = {
    PROFILES_FRAME : _("Profiles"),
    STATISTICS_FRAME : _("Statistics"),
}

class PreferencesList(gtk.TreeView):
    def __init__(self, activate_callback):
        store = gtk.ListStore(gobject.TYPE_STRING)
        super(PreferencesList, self).__init__(store)
        self.set_headers_visible(False)

        self.activate_callback = activate_callback
        self._init_model()
        self._init_view_columns()

    def _init_model(self):
        store = self.get_model()
        for frame in PREFERENCES_FRAMES:
            store.append((PREFERENCES_LABEL[frame],))

    def _init_view_columns(self):
        col = gtk.TreeViewColumn()

        render_text = gtk.CellRendererText()
        col.pack_start(render_text, expand=True)
        col.add_attribute(render_text, 'text', 0)

        self.append_column(col)

        self.connect('cursor-changed', self._cursor_changed)
        self.get_selection().set_mode(gtk.SELECTION_SINGLE)

    def _cursor_changed(self, treeview):
        model, selected = self.get_selection().get_selected_rows()
        if len(selected) == 1:
            self.activate_callback(selected[0][0])


class ProfilesList(gtk.TreeView):
    def __init__(self, model):
        super(ProfilesList, self).__init__(model)
        self.set_headers_visible(False)

        self._init_view_columns()
        self.default_profile_iter = None

    def _init_view_columns(self):
        col = gtk.TreeViewColumn()
        render_toggle = gtk.CellRendererToggle()
        render_toggle.set_radio(True)
        render_toggle.set_data('column', 0)
        col.pack_start(render_toggle, expand=False)
        col.add_attribute(render_toggle, 'active', 0)
        render_toggle.connect("toggled", self.on_item_toggled)
        self.append_column(col)

        def render_profile(cellview, cell, model, _iter):
            profile = model.get_value(_iter, 1)
            cell.set_property('text', str(profile.name))

        col = gtk.TreeViewColumn()
        cell = gtk.CellRendererText()
        col.pack_start(cell, expand=True)
        col.set_cell_data_func(cell, render_profile)
        self.append_column(col)

        self.get_selection().set_mode(gtk.SELECTION_SINGLE)

    def on_item_toggled(self, cell, path):
        model = self.get_model()
        _iter = model.get_iter(path)
        profile = model.get_value(_iter, 1)
        model.set_default_profile(profile.uuid)


class PreferencesView(View):

    GLADE_FILE = join(GLADE_DIR, "preferences.glade")

    def __init__(self, ctrl):
        super(PreferencesView, self).__init__(ctrl, self.GLADE_FILE,
                                              'preferences_window')
        self.profiles_treeview = None
        self.preferences_treeview = None

        self['preferences_notebook'].set_show_tabs(False)
        self._init_preferences_treeview()
        self._init_profiles_treeview(ctrl)

        ctrl.model.load()

        # I think this should be done in anotyher way, for now this works.
        self['transfer_limit_entry'].set_value(ctrl.model.transfer_limit)
        self['warn_limit_check'].set_active(ctrl.model.warn_limit)

        self.change_panel(PROFILES_FRAME)
        icon = gtk.gdk.pixbuf_new_from_file(join(GLADE_DIR, 'wader.png'))
        self.get_top_widget().set_icon(icon)

    def _init_preferences_treeview(self):
        self.preferences_treeview = PreferencesList(self.change_panel)
        self['preferences_view'].add(self.preferences_treeview)

    def _init_profiles_treeview(self, ctrl):
        model = ctrl.model.get_profiles_model(ctrl.device_callable)
        self.profiles_treeview = ProfilesList(model)
        self['profiles_view'].add(self.profiles_treeview)

    def change_panel(self, panel):
        self['preferences_notebook'].set_current_page(panel)

