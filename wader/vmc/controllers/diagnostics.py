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
from gtkmvc import Controller

from wader.common.consts import CRD_INTFACE, MDM_INTFACE

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

        self.set_device_info()

        self.view['uptime_number_label'].set_text(self.model.get_uptime())
        self.view['os_name_label'].set_text(self.model.get_os_name())
        self.view['os_version_label'].set_text(self.model.get_os_version())

    def set_device_info(self):

        device = self.model.get_device()
        if not device:
            return

        def error(e):
            print e

        device.GetImsi(dbus_interface=CRD_INTFACE, error_handler=error,
                       reply_handler=lambda imsi: self.view['imsi_number_label'].set_text(imsi))

# XXX: why isn't GetImei under MDM_INTFACE, it's a modem attribute not SIM?
        device.GetImei(dbus_interface=CRD_INTFACE, error_handler=error,
                       reply_handler=lambda imei: self.view['imei_number_label'].set_text(imei))

        def mdm_info(datacard_info):
            # ok we don't have a model the data is coming straight from our core via dbus
            manufacturer = datacard_info[0]
            model = datacard_info[1]
            firmware = datacard_info[2]
            print "controller: diagnostics mdm_info - manufacturer " + manufacturer
            print "controller: diagnostics mdm_info - model " + model
            print "controller: diagnostics mdm_info - firmware " + firmware
            self.view.set_datacard__info(manufacturer,  model,  firmware)
            
            #self.view['card_manufacturer_label'].set_text(t[0])
            #self.view['card_model_label'].set_text(t[1])
            #self.view['firmware_label'].set_text(t[2])
        device.GetInfo(dbus_interface=MDM_INTFACE, error_handler=error, reply_handler=mdm_info)

    # ------------------------------------------------------------ #
    #                       Signals Handling                       #
    # ------------------------------------------------------------ #

    def on_close_button_clicked(self, widget):
        self._hide_myself()

    def _hide_myself(self):
        self.model.unregister_observer(self)
        self.view.hide()
