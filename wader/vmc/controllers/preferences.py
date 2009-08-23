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

from wader.common.consts import CRD_INTFACE
from wader.common.exceptions import ProfileNotFoundError
from wader.vmc.controllers import Controller
from wader.vmc.logger import logger
from wader.vmc.dialogs import show_profile_window, show_error_dialog
from wader.vmc.translate import _
from wader.vmc.utils import get_error_msg


class PreferencesController(Controller):

    def __init__(self, model, device_callable):
        super(PreferencesController, self).__init__(model)
        self.device_callable = device_callable

    def register_view(self, view):
        super(PreferencesController, self).register_view(view)

    def on_cancel_button_clicked(self, event):
        self.close_controller()

    def on_ok_button_clicked(self, event):
        self.model.save()
        self.close_controller()

    def on_warn_limit_check_toggled(self, toggle):
        self.model.warn_limit = toggle.get_active()

    def on_transfer_limit_entry_value_changed(self, entry):
        self.model.transfer_limit = entry.get_value()

    def on_reset_statistics_button_clicked(self, button):
        self.model.reset_statistics()

    def on_add_profile_button_clicked(self, event):
        device = self.device_callable()
        if not device:
            return show_profile_window(self.model)

        device.GetImsi(dbus_interface=CRD_INTFACE,
                       reply_handler=lambda imsi:
                           show_profile_window(self.model, imsi=imsi),
                       error_handler=logger.error)

    def on_modify_profile_button_clicked(self, event):
        _iter = self.view.profiles_treeview.get_selection().get_selected()[1]
        if _iter:
            profile = self.model.profiles_model.get_value(_iter, 1)
            if profile:
                show_profile_window(self.model, profile=profile)

    def on_delete_profile_button_clicked(self, event):
        _iter = self.view.profiles_treeview.get_selection().get_selected()[1]
        profile = self.model.profiles_model.get_value(_iter, 1)
        if profile:
            try:
                self.model.profiles_model.remove_profile(profile)
            except ProfileNotFoundError, e:
                show_error_dialog(_("Error while removing profile"),
                                  get_error_msg(e))

    def property_warn_limit_value_change(self, model, old, new):
        if new != self.view['warn_limit_check'].get_active():
            self.view['warn_limit_check'].set_active(new)

    def property_transfer_limit_value_change(self, model, old, new):
        if new != self.view['transfer_limit_entry'].get_value():
            self.view['transfer_limit_entry'].set_value(new)

