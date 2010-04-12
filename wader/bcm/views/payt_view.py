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
from wader.bcm.contrib.gtkmvc import View
from wader.bcm.logger import logger

from wader.bcm.consts import GLADE_DIR, IMAGES_DIR


class PayAsYouTalkView(View):
    """View for the main Pay As You Talk window"""

    GLADE_FILE = join(GLADE_DIR, "payt.glade")
    sim_image = join(IMAGES_DIR, "simple_sim_35x20.png")
    payt_image = join(IMAGES_DIR,  "topup-banner.png")
    creditcard_image = join(IMAGES_DIR,  "credit_card_green.png")
    voucher_image = join(IMAGES_DIR,  "voucher.png")
    
    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'payt_window', register=False)
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self.get_top_widget().set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self['sim_image'].set_from_file(self.sim_image)
        self['paytbanner'].set_from_file(self.payt_image)
        self['credit_card_image'].set_from_file(self.creditcard_image)
        self['voucher_image'].set_from_file(self.voucher_image)

    def set_msisdn_value(self,  MSISDNvalue):
         self['msisdn_view'].set_text(MSISDNvalue)
         
    def set_credit_view(self,  credit_value):
          self['credit_view'].set_text(credit_value.replace('#',' £'))
    
    def set_credit_date(self,  credit_date_value):
         self['date_view'].set_text(credit_date_value)


    def set_waiting_credit_view(self):
         self['date_view'].set_text("Fetching ......")
         self['credit_view'].set_text("Fetching current credit from network.....")
         

    def set_voucher_entry_view(self,  voucher_value):
         
         #ok if the view has been asked to reset with a null string, make sure we reset any previous messages too.
         if voucher_value=='':
              self['voucher_code'].set_text('')
              self['voucher_response_message'].set_text('')
              logger.info("payt-view set_voucher_entry_view (value-null) - USSD Message: " + voucher_value)
         else:
              self['voucher_response_message'].set_text(voucher_value.replace('#',' £'))
              logger.info("payt-view set_voucher_entry_view - USSD Message: " + voucher_value)
         
         

