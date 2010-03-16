# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone Group
# Author:  Nicholas Herriot
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
from wader.vmc.contrib.gtkmvc import View

from wader.vmc.consts import GLADE_DIR, IMAGES_DIR


class PayAsYouTalkView(View):
    """View for the main Pay As You Talk window"""

    GLADE_FILE = join(GLADE_DIR, "payt.glade")
    sim_image = join(IMAGES_DIR, "simple_sim_35x20.png")
    payt_image = join(IMAGES_DIR,  "payt_graphic.png")
    creditcard_Image = join(IMAGES_DIR,  "credit_card_50x25.png")
    voucher_image = join(IMAGES_DIR,  "voucher_image_50x25.png")
    
    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'payt_window', register=False)
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self.get_top_widget().set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self['sim_image'].set_from_file(self.sim_image)
        self['payt_image'].set_from_file(self.Computer_Image)
        self['credit_card_image'].set_from_file(self.Modem_Image)
        self['voucher_image'].set_from_file(self.Betavine_Image)

    def set_ussd_reply(self, ussd_reply):
         buffer = self['ussd_textview'].get_buffer()
         buffer.set_text(ussd_reply)
         self['ussd_textview'].set_buffer(buffer)

    def set_msisdn_info(self,  MSISDNvalue):
         self['msisdn'].set_text(MSISDNvalue)

