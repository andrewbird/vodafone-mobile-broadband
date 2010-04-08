# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone Global
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
# 51 Franklin Street, Fi1fth Floor, Boston, MA 02110-1301 USA.
"""
Controllers for Pay As You Talk 
"""
#from gtkmvc import Controller
import datetime
from wader.vmc.contrib.gtkmvc import Controller

from wader.common.consts import CRD_INTFACE, MDM_INTFACE
from wader.common.provider import NetworkProvider
from wader.vmc.logger import logger


class PayAsYouTalkController(Controller):
    """Controller for the pay as you talk window"""

    def __init__(self, model, parent_ctrl):
        super(PayAsYouTalkController, self).__init__(model)
        self.parent_ctrl = parent_ctrl

    def register_view(self, view):
        """
        Fill the label fields of the pay as you talk dialog

        This will be called once the view is registered
        """
        super(PayAsYouTalkController, self).register_view(view)

        self.set_device_info()

        #self.view.set_appVersion_info(self.model.get_app_version())
        #self.view['uptime_number_label'].set_text(self.model.get_uptime())
        #self.view['os_name_label'].set_text(self.model.get_os_name())
        #self.view['os_version_label'].set_text(self.model.get_os_version())

    def set_device_info(self):
         
         
        device = self.model.get_device()
        
        ussd_msisdn = "*#100#"
        ussd_check_account = "*#135#"
        ussd_send_voucher = "*#999#"
        ussd_check_credit = "*#134#"
        
        if not device:
            return

        def sim_imei(sim_data):
          # ok we don't have a model the data is coming from dbus
          # from wader core lets tell the view to set the imsi value
          # in the correct place
          logger.info("payt-controller sim_imei - IMEI number is: " +  sim_data)
          # FIXME - Removed not needed at the minute.
          #self.view.set_imei_info(sim_data)

        device.GetImei(dbus_interface=CRD_INTFACE,
                       error_handler=logger.error, reply_handler=sim_imei)


        def sim_msisdn(msisdn_data):
          # same as above, no model so lets get the msisdn value from the network
          # using ussd messages
          logger.info("payt-controller sim_msisdn - MSISDN number is: " + msisdn_data)
          self.view.set_msisdn_value(msisdn_data)
          
             
        device.Initiate(ussd_msisdn,
                         reply_handler= sim_msisdn,
                         error_handler= logger.error)             
          
        def sim_credit(sim_credit):
          # same as above, no model so lets get the sim credit value from the network
          # using ussd messages
          logger.info("payt-controller sim_credit - SIM Credit is: " + sim_credit)
          self.view.set_credit_view(sim_credit)
          credit_time = datetime.datetime.utcnow()
          logger.info("payt-controller sim_credit - Date of querry is: " + credit_time.strftime("%A, %d. %B %Y %I:%M%p"))
          self.view.set_credit_date(credit_time.strftime("%A, %d. %B %Y %I:%M%p"))

        device.Initiate(ussd_check_account,
          reply_handler= sim_credit,
          error_handler= logger.error)             


        def sim_network(sim_data):
            # let's look up what we think this SIM's network is.
            # so we want to display the country and network operator

            sim_network = NetworkProvider()
            networks_attributes = sim_network.get_network_by_id(sim_data)
            if networks_attributes:
               net_attrib = networks_attributes[0]
               logger.info("payt-controller sim_network - country: " +  net_attrib.country)
               logger.info("payt-controller sim_network - network operator: " +  net_attrib.name)
               logger.info("payt-controller sim_network - smsc value: " +  net_attrib.smsc)
               logger.info("payt-controller sim_network - password value: " +  net_attrib.password)
               # FIXME - Removed not needed yet.
               #self.view.set_network_info(net_attrib.name, net_attrib.country)

        device.GetImsi(dbus_interface=CRD_INTFACE,
                       error_handler=logger.error, reply_handler=sim_network)

        def sim_imsi(sim_data):
            # ok we don't have a model the data is coming from dbus from the
            # core lets tell the view to set the imei in the correct place
            logger.info("payt-controller sim_imsi - IMSI number is: %s" % sim_data)
            # FIXME - Removed not needed yet
            #self.view.set_imsi_info(sim_data)

        device.GetImsi(dbus_interface=CRD_INTFACE,
                       error_handler=logger.error, reply_handler=sim_imsi)

    # ------------------------------------------------------------ #
    #                Common Functions                #
    # ------------------------------------------------------------ #

    def reset_credit_and_date(self,  ussd_reply):
         # a call back must have called us, my job is to reset the credit date and value.
         # I take care of reseting both as a credit amount is only valid at the time you check, so make sure when you update
         # the credit you also update the time you did the check.
         # ok lets reset the date and credit of the view

         logger.info("payt-controller set_credit_and_date - USSD reply is: " + ussd_reply)
         self.view.set_credit_view(ussd_reply)
         credit_time = datetime.datetime.utcnow()
         logger.info("payt-controller reset_credit_and_date - Date of querry is: " + credit_time.strftime("%A, %d. %B %Y %I:%M%p"))
         self.view.set_credit_date(credit_time.strftime("%A, %d. %B %Y %I:%M%p"))

    def check_voucher_update_response(self,  ussd_voucher_update_response):
         device = self.model.get_device()         
         # ok my job is to work out what happened after a credit voucher update message was sent.
         # we can have three possibilities, it was succesfull, the voucher code was wrong, or you tried with
         # an illegal number too many times. For now I only do something when it works, the other two
         # possibilities I just report the error provided by the network.
         
         if (ussd_voucher_update_response.find('TopUp successful') == -1):
              # ok we got a -1 from our 'find' so it failed just log for now as we report the message to the view no matter what happens.
               logger.info("payt-controoler check_voucher_update_response - topup failed: "  + ussd_voucher_update_response)

         else:
              # ok we established his voucher code is good - lets cause the system to update the UI with his new credit
              # to do that we need to fire off another ussd to cause a credit request to happen
              logger.info("payt-controler check_voucher_update_response - topup was succesful: "  + ussd_voucher_update_response)
              self.view.set_waiting_credit_view()
              # lets now do a credit check via USSD
              device.Initiate(ussd_message,
                    reply_handler= self.reset_credit_and_date,
                    error_handler= logger.error)  

          # ok no matter we have, we need to update our view to show good or bad!
         logger.info("payt-controoler check_voucher_update_response - topup follows normal path: "  + ussd_voucher_update_response)
         set_voucher_entry_view(ussd_voucher_update_response)
              
         
     

    # ------------------------------------------------------------ #
    #                       Signals Handling             #
    # ------------------------------------------------------------ #

    def on_close_button_clicked(self, widget):
        self._hide_myself()
             
        
    def on_credit_button_clicked(self,  widget):
         device = self.model.get_device()
         ussd_message = "*#135#"
         logger.info("payt-controller on_credit_button_clicked- USSD Message is:" + ussd_message)
         
         # ok we need to tell the view to wipe current data and prepare for the new!
         # So lets remove our current credit and date first.
         self.view.set_waiting_credit_view()
         
         # lets now do a credit check via USSD
         device.Initiate(ussd_message,
               reply_handler= self.reset_credit_and_date,
               error_handler= logger.error)  
         
         
    def on_send_voucher_button_clicked(self, widget):
          device = self.model.get_device()

          # ok when the send voucher button is clicked grab the value from the view entry box and send 
          # to the network. 

          ussd_voucher_init = "*#1345*"
          ussd_voucher_end = "#"
          voucher_code = self.view['voucher_code'].get_text().strip()
          self.view.set_voucher_entry_view('')
          # make sure we construct the string to enable PAYT Topup vouchers to be used e.g. *#1345*<voucher number>#
          ussd_voucher_message = ussd_voucher_init + voucher_code + ussd_voucher_end
          logger.info("payt-controller on_send_voucher_button_clicked - USSD Message: " + ussd_voucher_message)
          
          device.Initiate(ussd_voucher_message,
                         reply_handler=self.check_voucher_update_response,
                         error_handler=logger.error)



    def _hide_myself(self):
        self.model.unregister_observer(self)
        self.view.hide()
