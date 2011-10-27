# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

from os.path import join

import gtk
#from gtkmvc import View
from wader.bcm.contrib.gtkmvc import View

from wader.bcm.consts import GLADE_DIR, IMAGES_DIR
from wader.bcm.constx import BCM_VIEW_DISABLED, BCM_VIEW_IDLE, BCM_VIEW_BUSY
from wader.bcm.translate import _


class DiagnosticsView(View):
    """View for the main diagnostics window"""

    GLADE_FILE = join(GLADE_DIR, "diagnostics.glade")
    Sim_Image = join(IMAGES_DIR, "simple_sim_35x20.png")
    Computer_Image = join(IMAGES_DIR, "netbookGraphic_50x25.png")
    Modem_Image = join(IMAGES_DIR, "blackDongle_65x18.png")
    Betavine_Image = join(IMAGES_DIR, "VF_logo_medium.png")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'diagnostics_window', register=False, domain='bcm')
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self.get_top_widget().set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self['SIMImage'].set_from_file(self.Sim_Image)
        self['ComputerImage'].set_from_file(self.Computer_Image)
        self['ModemImage'].set_from_file(self.Modem_Image)
        self['BetavineImage'].set_from_file(self.Betavine_Image)

        self['ussd_entry'].set_text('')
        self.set_ussd_reply('')
        self['ussd_textview'].set_editable(False)

    def set_datacard_info(self, manufacturer, model, firmware):
        self['card_manufacturer_label'].set_text(manufacturer)
        self['card_model_label'].set_text(model)
        self['firmware_label'].set_text(firmware)

    def get_ussd_request(self):
        return self['ussd_entry'].get_text()

    def set_ussd_reply(self, ussd_reply):
        _buffer = self['ussd_textview'].get_buffer()
        _buffer.set_text(ussd_reply)
        self['ussd_textview'].set_buffer(_buffer)

    def set_ussd_state(self, state):
        if state is BCM_VIEW_DISABLED:
            self['send_ussd_button'].set_sensitive(False)
            self['ussd_entry'].set_sensitive(False)
        elif state is BCM_VIEW_IDLE:
            self['send_ussd_button'].set_sensitive(True)
            self['ussd_entry'].set_sensitive(True)
        elif state is BCM_VIEW_BUSY:
            self['send_ussd_button'].set_sensitive(False)
            self['ussd_entry'].set_sensitive(False)
            self.set_ussd_reply('')

    def set_msisdn_info(self, msisdn):
        if msisdn is None:
            msisdn = _('Unknown')
        self['msisdn_name_label'].set_text(msisdn)

    def set_imsi_info(self, imsi):
        self['imsi_number_label'].set_text(imsi)

    def set_network_info(self, network=None, country=None):
        if network is None:
            network = _('Unknown')
        self['network_name_label'].set_text(network)

        if country is None:
            country = _('Unknown')
        self['country_name_label'].set_text(country)

    def set_imei_info(self, imei):
        self['imei_number_label'].set_text(imei)

    def set_appVersion_info(self, appVersion):
        self['bcm_version'].set_text(appVersion)

    def set_coreVersion_info(self, coreVersion):
        self['core_version'].set_text(coreVersion)
