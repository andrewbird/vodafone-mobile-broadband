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
#from gtkmvc import Controller
from gui.contrib.gtkmvc import Controller

from wader.common.provider import NetworkProvider

from gui.logger import logger
from gui.constx import (GUI_VIEW_DISABLED, GUI_VIEW_IDLE, GUI_VIEW_BUSY,
                              GUI_MODEM_STATE_REGISTERED)


class DiagnosticsController(Controller):
    """Controller for the diagnostics window"""

    def __init__(self, model, parent_ctrl):
        super(DiagnosticsController, self).__init__(model)
        self.parent_ctrl = parent_ctrl
        self.ussd_busy = False

    def register_view(self, view):
        """
        Fill the label fields of the diagnostics dialog

        This will be called once the view is registered
        """
        super(DiagnosticsController, self).register_view(view)

        self.set_device_info()

        self.view.set_appVersion_info(self.model.get_app_version())
        self.view.set_coreVersion_info(self.model.get_core_version())
        self.view['uptime_number_label'].set_text(self.model.get_uptime())
        self.view['os_name_label'].set_text(self.model.get_os_name())
        self.view['os_version_label'].set_text(self.model.get_os_version())

        # USSD
        self.ussd_busy = False
        self.property_status_value_change(
                self.model, None, self.model.status)

    def set_device_info(self):
        self.view.set_imei_info(self.model.imei)

        self.view.set_imsi_info(self.model.imsi)
        self.set_network_country_info(self.model.imsi)

        self.view.set_msisdn_info(self.model.msisdn)

        self.view.set_card_manufacturer_info(self.model.card_manufacturer)
        self.view.set_card_model_info(self.model.card_model)
        self.view.set_card_firmware_info(self.model.card_firmware)

    def set_network_country_info(self, imsi):
        try:
            provider = NetworkProvider()
            nets = provider.get_network_by_id(imsi)
            if not len(nets):
                raise ValueError
            self.view.set_network_info(nets[0].name)
            self.view.set_country_info(nets[0].country)
        except (TypeError, ValueError):
            self.view.set_network_info(None)
            self.view.set_country_info(None)
        finally:
            provider.close()

    # ------------------------------------------------------------ #
    #                       Signals Handling                       #
    # ------------------------------------------------------------ #

    def on_close_button_clicked(self, widget):
        self._hide_myself()

    def on_send_ussd_button_clicked(self, widget):
        self.ussd_busy = True
        self.property_status_value_change(
                self.model, None, self.model.status)

        ussd_message = self.view.get_ussd_request().strip()
#        self.view['ussd_entry'].set_text('')

        def reply_cb(reply):
            self.view.set_ussd_reply(reply)
            self.ussd_busy = False
            self.property_status_value_change(
                    self.model, None, self.model.status)

        device = self.model.get_device()
        device.Initiate(ussd_message,
                        reply_handler=reply_cb,
                        error_handler=logger.error)

    def _hide_myself(self):
        self.model.unregister_observer(self)
        self.view.hide()

    # ------------------------------------------------------------ #
    #                       Property Changes                       #
    # ------------------------------------------------------------ #

    def property_card_manufacturer_value_change(self, model, old, new):
        self.view.set_card_manufacturer_info(new)

    def property_card_model_value_change(self, model, old, new):
        self.view.set_card_model_info(new)

    def property_card_firmware_value_change(self, model, old, new):
        self.view.set_card_firmware_info(new)

    def property_imei_value_change(self, model, old, new):
        self.view.set_imei_info(new)

    def property_imsi_value_change(self, model, old, new):
        self.view.set_imsi_info(new)
        self.set_network_country_info(new)

    def property_msisdn_value_change(self, model, old, new):
        self.view.set_msisdn_info(new)

    def property_status_value_change(self, model, old, new):
        if new < GUI_MODEM_STATE_REGISTERED:
            self.view.set_ussd_state(GUI_VIEW_DISABLED)
        else:
            if not self.ussd_busy:
                self.view.set_ussd_state(GUI_VIEW_IDLE)
            else:
                self.view.set_ussd_state(GUI_VIEW_BUSY)
