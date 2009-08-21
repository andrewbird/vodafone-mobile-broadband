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
"""View for the initial config dialog"""
__version__ = "$Rev: 1172 $"

import os.path

import gobject
import gtk

from twisted.internet import defer

from wader.common.dialers import AUTH_OPTS_LIST
from wader.common.encoding import _
import wader.common.consts as consts

from wader.vmc import View
from wader.vmc.models.initialconf import BluetoothDeviceStoreModel
from wader.vmc.images import get_pixbuf_for_device

class BaseProfileView(View):
    GLADE_FILE = os.path.join(consts.GLADE_DIR, "config2.glade")
    IMAGE_FILE = os.path.join(consts.GLADE_DIR, "proedt.png")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'new_profile_window', register=False, domain="VMC")
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        window = self.get_top_widget()
        window.set_position(gtk.WIN_POS_CENTER)
        self['PROimage'].set_from_file(self.IMAGE_FILE)

        # setup connection combobox
        model = gtk.ListStore(gobject.TYPE_STRING)
        self['connection_combobox'].set_model(model)

        # setup auth combobox
        model = gtk.ListStore(gobject.TYPE_STRING)
        for opt in AUTH_OPTS_LIST:
            model.append([opt])

        self['auth_combobox'].set_model(model)


class NewProfileView(BaseProfileView):
    def __init__(self, ctrl):
        super(NewProfileView, self).__init__(ctrl)

    def setup_view(self):
        super(NewProfileView, self).setup_view()
        self['auth_combobox'].set_active(0)        # Default auth profile


class EditProfileView(BaseProfileView):
    def __init__(self, ctrl):
        super(EditProfileView, self).__init__(ctrl)

    def setup_view(self):
        super(EditProfileView, self).setup_view()


class APNSelectionView(View):
    GLADE_FILE = os.path.join(consts.GLADE_DIR, "apnsel.glade")
    IMAGE_FILE = os.path.join(consts.GLADE_DIR, "apnsel.png")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'apn_selection_window', domain="VMC")
        self.ctrl = ctrl
        self.setup_view()
        self.init_model(self.ctrl.apn_list)
        self.init_view_columns()

    def setup_view(self):
        self._view = self['apn_list_treeview']
        self['APNimage'].set_from_file(self.IMAGE_FILE)

    def init_view_columns(self):
        render_text = gtk.CellRendererText()
        col0=gtk.TreeViewColumn(_('Name'))
        col0.pack_start(render_text, expand=True)
        col0.add_attribute(render_text, 'text', 0)
        col1=gtk.TreeViewColumn(_('Country'))
        col1.pack_start(render_text, expand=True)
        col1.add_attribute(render_text, 'text', 1)
        col2=gtk.TreeViewColumn(_('Type'))
        col2.pack_start(render_text, expand=True)
        col2.add_attribute(render_text, 'text', 2)
        self._view.append_column(col0)
        self._view.append_column(col1)
        self._view.append_column(col2)

    def init_model(self, profiles):
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
        self._view.get_selection().select_iter(iter)

    def get_selected_apn(self):
        def get_selected_apn_cb(self):
            model, selected = self._view.get_selection().get_selected_rows()
            if not selected:
                _iter = model.get_iter(0)    # 1st row if no selection
            else:
                _iter = model.get_iter(selected[0])
            return model.get_value(_iter, 3) # the object
        return defer.maybeDeferred(get_selected_apn_cb,self)


class DeviceList(gtk.TreeView):
    def __init__(self, device_list, callback, _window):
        super(gtk.TreeView, self).__init__()
        self.set_headers_visible(False)
        self.callback = callback
        self._window = _window
        self.device_iters = {}
        self.init_model(device_list)
        self.init_view_columns()

    def init_model(self, device_list):
        store = gtk.ListStore(gtk.gdk.Pixbuf,
                              gobject.TYPE_STRING,
                              gobject.TYPE_PYOBJECT)
        self.set_model(store)

        for device in device_list:
            self.show_device(device)

        # select the first row if there
        if len(device_list) > 0:
            iter = self.get_model().get_iter_first()
            if iter:
                self.get_selection().select_iter(iter)

    def hide_device(self, device):
        store = self.get_model()
        store.remove(self.device_iters[device])
        del(self.device_iters[device])

    def show_device(self, device):
        store = self.get_model()
        item = (get_pixbuf_for_device(device), device.name, device)
        self.device_iters[device] = store.append(item)

    def __len__(self):
        return len(self.device_iters)

    def init_view_columns(self):
        col = gtk.TreeViewColumn()
        render_pixbuf = gtk.CellRendererPixbuf()
        col.pack_start(render_pixbuf, expand=False)
        col.add_attribute(render_pixbuf, 'pixbuf', 0)
        render_text = gtk.CellRendererText()
        col.pack_start(render_text, expand=True)
        col.add_attribute(render_text, 'text', 1)
        self.append_column(col)

        self.connect('row-activated', self._row_activated_handler)
        self.get_selection().set_mode(gtk.SELECTION_SINGLE)

    def _row_activated_handler(self, treeview, path, col):
        device = self.get_selected_device()
        self.callback(device)
        self._window.destroy()

    def get_selected_device(self):
        model, selected = self.get_selection().get_selected_rows()
        if not selected or len(selected) > 1:
            return self.device_iters.keys()[0]
        _iter = model.get_iter(selected[0])
        device = model.get_value(_iter, 2)
        return device


class DeviceSelectionView(View):
    """
    View for the device selection dialog
    """
    GLADE_FILE = os.path.join(consts.GLADE_DIR, "config2.glade")
    IMAGE_FILE = os.path.join(consts.GLADE_DIR, "devsel-dongle.png")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'device_selection_window', domain="VMC")
        self.ctrl = ctrl
        self.device_list = None
        self.without_device_label = None
        self.setup_view()

    def setup_view(self):
        self['DEVimage'].set_from_file(self.IMAGE_FILE)
        self.device_list = DeviceList(self.ctrl.device_list,
                                          self.ctrl.device_callback,
                                          self.get_top_widget())
        self.without_device_label = gtk.Label(_("No known devices found"))

        if self.ctrl.device_list:
            self._with_devices()
            self['known_device_radio'].set_active(True)
        else:
            self._without_devices()

    def _change_viewport(self, widget_to_hide, widget_to_show):
        container = self['device_list_container']
        viewport = widget_to_hide.get_parent()
        if viewport and container is viewport.get_parent():
            container.remove(viewport)
        container.add_with_viewport(widget_to_show)
        widget_to_show.show()

    def _with_devices(self):
        self._change_viewport(self.without_device_label, self.device_list)
        self['known_devices_frame'].set_sensitive(True)

    def _without_devices(self):
        self._change_viewport(self.device_list, self.without_device_label)
        self.disable_known_device_controls()
        self['known_devices_frame'].set_sensitive(False)
        self['custom_device_radio'].set_active(True)
        self.enable_custom_device_controls()

    def enable_known_device_controls(self):
        self['device_list_container'].set_sensitive(True)

    def disable_known_device_controls(self):
        self['device_list_container'].set_sensitive(False)

    def enable_custom_device_controls(self):
        self['custom_device_controls'].set_sensitive(True)

    def disable_custom_device_controls(self):
        self['custom_device_controls'].set_sensitive(False)

    def get_selected_device(self):
        if self['known_device_radio'].get_active():
            return defer.maybeDeferred(self.device_list.get_selected_device)
        else:
            dataport = self['data_port_entry'].get_text()
            controlport = self['control_port_entry'].get_text() or None
            baudrate = int(self['speed_entry'].get_text()) or 115200

            from wader.common.plugin import get_unknown_device_plugin
            d = get_unknown_device_plugin(dataport, controlport, baudrate)
            return d

    def device_removed(self, device):
        self.device_list.hide_device(device)
        if len(self.device_list) == 0:
            self._without_devices()

    def device_added(self, device):
        if not self.device_list or (len(self.device_list) == 0):
            self._with_devices()
        self.device_list.show_device(device)

class BluetoothConfView2(View):
    """View for the bluetooth config dialog"""

    GLADE_FILE = os.path.join(consts.GLADE_DIR, "config.glade")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE, 'bluetooth_window',
                            register=False, domain="VMC")
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self._setup_device_treeview()
        self._setup_datap_combobox()
        self._setup_controlp_combobox()
        self._setup_speed_combobox()

    def _setup_device_treeview(self):
        treeview = self['device_treeview']

        treeview.set_model(BluetoothDeviceStoreModel())
        treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)

        col_name, col_address = range(2)
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Name"), cell, text=col_name)
        column.set_resizable(True)
        column.set_sort_column_id(col_name)
        cell.set_property('editable', False)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Address"), cell, text=col_address)
        column.set_resizable(True)
        column.set_sort_column_id(col_address)
        cell.set_property('editable', False)
        treeview.append_column(column)

    def _setup_datap_combobox(self):
        store = gtk.ListStore(gobject.TYPE_STRING)
        #store.append(["/dev/rfcomm0"])

        combo = self['data_comboboxentry']
        combo.set_model(store)
        combo.set_active(0)

    def _setup_controlp_combobox(self):
        store = gtk.ListStore(gobject.TYPE_STRING)
        #store.append(["/dev/rfcomm1"])

        combo = self['control_comboboxentry']
        combo.set_model(store)
        combo.set_active(0)

    def _setup_speed_combobox(self):
        store = gtk.ListStore(gobject.TYPE_STRING)
        store.append(["115200"])
        store.append(["57600"])
        store.append(["38400"])
        store.append(["19200"])

        combo = self['speed_comboboxentry']
        combo.set_model(store)
        combo.set_active(0)
