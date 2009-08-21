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

from wader.common.utils import convert_int_to_ip, convert_ip_to_int
from wader.common.keyring import KeyringNoMatchError
from wader.vmc.consts import BAND_MAP_REV, MODE_MAP_REV
from wader.vmc.controllers import Controller
from wader.vmc.dialogs import show_error_dialog
from wader.vmc.logger import logger
from wader.vmc.utils import get_error_msg
from wader.vmc.translate import _

class ProfileController(Controller):

    def __init__(self, model):
        super(ProfileController, self).__init__(model)

    def register_view(self, view):
        super(ProfileController, self).register_view(view)

    def setup_view(self, view):
        self.view['profile_name_entry'].set_text(self.model.name)
        self.view['username_entry'].set_text(self.model.username)
        self.view.set_network_mode(self.model.network_type)
        self.view.set_band(self.model.band)
        self.view['apn_entry'].set_text(self.model.apn)
        self.view['static_dns_check'].set_active(self.model.static_dns)
        if self.model.primary_dns:
            dns1 = convert_int_to_ip(self.model.primary_dns)
            self.view['primary_dns_entry'].set_text(dns1)
        if self.model.secondary_dns:
            dns2 = convert_int_to_ip(self.model.secondary_dns)
            self.view['secondary_dns_entry'].set_text(dns2)

        if self.model.static_dns:
            self.view.enable_static_dns()

        if not self.model.password:
            try:
                self.model.load_password()
            except KeyringNoMatchError, e:
                logger.error("Error while loading connection password: %s" % e)
                title = _("Error while getting connection password")
                details = _("NoMatchError: No password was retrieved "
                            "from connection, please set one again")
                show_error_dialog(title, details)
                return

        self.view['password_entry'].set_text(self.model.password)

    def on_cancel_button_clicked(self, widget):
        self.close_controller()

    def on_ok_button_clicked(self, widget):
        self.model.name = self.view['profile_name_entry'].get_text()
        self.model.username = self.view['username_entry'].get_text()
        self.model.password = self.view['password_entry'].get_text()

        mode = self.view['connection_combobox'].get_active_text()
        band = self.view['band_combobox'].get_active_text()
        if mode:
            self.model.network_type = MODE_MAP_REV[mode]
        if band:
            self.model.band = BAND_MAP_REV[band]

        self.model.apn = self.view['apn_entry'].get_text()
        self.model.static_dns = self.view['static_dns_check'].get_active()
        if self.view['static_dns_check'].get_active():
            dns1 = self.view['primary_dns_entry'].get_text()
            dns2 = self.view['secondary_dns_entry'].get_text()
            if dns1:
                self.model.primary_dns = convert_ip_to_int(dns1)
            if dns2:
                self.model.secondary_dns = convert_ip_to_int(dns2)

        try:
            self.model.save()
        except RuntimeError, e:
            show_error_dialog(_("Error creating profile"), get_error_msg(e))
        else:
            self.close_controller()

    def property_name_value_change(self, model, old, new):
        self.view['profile_name_entry'].set_text(new)

    def property_username_value_change(self, model, old, new):
        self.view['username_entry'].set_text(new)

    def property_password_value_change(self, model, old, new):
        self.view['password_entry'].set_text(new)

    def property_network_type_value_change(self, model, old, new):
        self.view.set_network_mode(new)

    def property_band_value_change(self, model, old, new):
        self.view.set_band(new)

    def property_apn_value_change(self, model, old, new):
        self.view['apn_entry'].set_text(new)

    def property_primary_dns_value_change(self, model, old, new):
        if not old and new and old != new:
            self.view.enable_static_dns()

        self.view['primary_dns_entry'].set_text(convert_int_to_ip(new))

    def property_secondary_dns_value_change(self, model, old, new):
        if not old and new and old != new:
            self.view.enable_static_dns()

        self.view['secondary_dns_entry'].set_text(convert_int_to_ip(new))
