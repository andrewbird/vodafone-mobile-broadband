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
# 51 Franklin Street, Fi1fth Floor, Boston, MA 02110-1301 USA.
"""
Controllers for diagnostics
"""
__version__ = "$Rev: 1172 $"

from wader.vmc import Controller

class DiagnosticsController(Controller):
    """Controller for the diagnostics window"""

    def __init__(self, model, parent_ctrl):
        super(DiagnosticsController, self).__init__(model)
        self.parent_ctrl = parent_ctrl

    def register_view(self, view):
        """
        Fill the label fields of the diagnostics dialog

        This will be called once the view is registered
        """
        super(DiagnosticsController, self).register_view(view)

        if self.model.get_device():
            self.set_sim_info()

        self.model.get_uptime().addCallback(lambda uptime:
                self.view['uptime_number_label'].set_text(uptime))

        self.view['os_name_label'].set_text(self.model.get_os_name())
        self.view['os_version_label'].set_text(self.model.get_os_version())

    def set_sim_info(self):
        self.model.get_imei().addCallback(
                lambda imei: self.view['imei_number_label'].set_text(imei))
        self.model.get_imsi().addCallback(
                lambda imsi: self.view['imsi_number_label'].set_text(imsi))
        self.model.get_card_version().addCallback(
                lambda card_v: self.view['firmware_label'].set_text(card_v))
        self.model.get_card_model().addCallback(
                lambda card_m: self.view['card_model_label'].set_text(card_m))

    # ------------------------------------------------------------ #
    #                       Signals Handling                       #
    # ------------------------------------------------------------ #

    def on_close_button_clicked(self, widget):
        self._hide_myself()

    def _hide_myself(self):
        self.model.unregister_observer(self)
        self.view.hide()
