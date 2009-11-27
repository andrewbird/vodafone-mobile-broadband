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
"""Controllers for the sms dialogs"""

from datetime import datetime
from gtkmvc import Controller, Model
from twisted.internet.defer import succeed

#from wader.vmc.config import config as config
#import wader.common.exceptions as ex
#from wader.common.sms import (MAX_LENGTH_7BIT, MAX_LENGTH_UCS2)
from messaging import (PDU,
                       SEVENBIT_SIZE, UCS2_SIZE,
                       SEVENBIT_MP_SIZE, UCS2_MP_SIZE,
                       is_valid_gsm_text)

from wader.common.consts import SMS_INTFACE
from wader.common.oal import osobj
from wader.common.sms import Message

from wader.vmc import dialogs
from wader.vmc.translate import _
from wader.vmc.messages import get_messages_obj
from wader.vmc.utils import get_error_msg
from wader.vmc.config import config

from wader.vmc.controllers.base import TV_DICT, TV_DICT_REV

from wader.vmc.views.contacts import ContactsListView
from wader.vmc.controllers.contacts import ContactsListController

from wader.vmc.contrib.ValidatedEntry import ValidatedEntry, v_phone


SMS_TOOLTIP = \
    _("You can send the SMS to several recipients separating them by commas")

IDLE, SENDING = range(2)

class NewSmsController(Controller):
    """Controller for the new sms dialog"""

    def __init__(self, model, parent_ctrl = None):
        super(NewSmsController, self).__init__(model)
        self.pdu = PDU()
        self.state = IDLE
        self.parent_ctrl = parent_ctrl
        self.max_length = SEVENBIT_SIZE
        self.numbers_entry = ValidatedEntry(v_phone)
        self.sms = None

        try:
            self.numbers_entry.set_tooltip_text(SMS_TOOLTIP)
        except AttributeError, e:
            # This fails on Ubuntu Feisty, we can live without it
            pass

        self.tz = None
        try:
            self.tz = osobj.get_tzinfo()
        except:
            pass

    def register_view(self, view):
        super(NewSmsController, self).register_view(view)
        # set initial text
        msg = _('Text message: 0/%d chars') % self.max_length
        self.view.get_top_widget().set_title(msg)
        # signals stuff
        textbuffer = self.view['sms_edit_text_view'].get_buffer()
        textbuffer.connect('changed', self._textbuffer_changed)
        # show up
        self.numbers_entry.grab_focus()

    def close_controller(self):
        self.model.unregister_observer(self)
        self.view.get_top_widget().destroy()
        self.view = None
        self.model = None

    def on_delete_event_cb(self, *args):
        self.close_controller()

    def on_send_button_clicked(self, widget):
        # check that is a valid number
        if not self.numbers_entry.isvalid():
            self.numbers_entry.grab_focus()
            return

        # protect ourselves against multiple presses
        self.view.set_busy_view()

        text = self.get_message_text()
        if not text:
            resp = dialogs.show_warning_request_cancel_ok(
                    _("Send empty message"),
                    _("Are you sure you want to send an empty message?"))
            if not resp: # user said no
                self.view.set_idle_view()
                return

        def on_sms_sent_cb(msg):
            where = TV_DICT_REV['sent_treeview']
            self.save_messages_to_db([msg], where)

            # if original message is a draft, remove it
            if self.sms:
                self.delete_messages_from_db_and_tv([self.sms])
                self.sms = None

            # hide ourselves if we are not sending more SMS...
            if self.state == IDLE:
                if self.view:
                    self.view.set_idle_view()
                self.on_delete_event_cb(None)

        def on_sms_sent_eb(error):
            title = _('Error while sending SMS')
            dialogs.show_error_dialog(title, get_error_msg(error))

        self.state = SENDING

        numbers = self.get_numbers_list()
        for number in numbers:
            msg = Message(number, text, _datetime=datetime.now(self.tz))
            self.model.device.Send(dict(number=number, text=text),
                                   dbus_interface=SMS_INTFACE,
                                   reply_handler=lambda indexes: on_sms_sent_cb(msg),
                                   error_handler=on_sms_sent_eb)
        self.state = IDLE

    def on_save_button_clicked(self, widget):
        """This will save the selected SMS to the drafts tv and the DB"""

        numl = self.get_numbers_list()
        nums = ','.join(numl) if numl else ''

        text = self.get_message_text()
        if text:
            msg = Message(nums, text, _datetime=datetime.now(self.tz))
            where = TV_DICT_REV['drafts_treeview']
            self.save_messages_to_db([msg], where)

        self.model.unregister_observer(self)
        self.view.hide()

    def on_cancel_button_clicked(self, widget):
        self.model.unregister_observer(self)
        self.view.hide()

    def on_contacts_button_clicked(self, widget):
        ctrl = ContactsListController(Model(), self)
        view = ContactsListView(ctrl)
        view.run()

    def _textbuffer_changed(self, textbuffer):
        """Handler for the textbuffer changed signal"""
        text = textbuffer.get_text(textbuffer.get_start_iter(),
                                   textbuffer.get_end_iter())
        if not len(text):
            msg = _('Text message: 0/%d chars') % SEVENBIT_SIZE
        else:
            # get the number of messages
            # we use a default number for encoding purposes
            num_sms = len(self.pdu.encode_pdu('+342453435', text))
            if num_sms == 1:
                max_length = SEVENBIT_SIZE if is_valid_gsm_text(text) else UCS2_SIZE
                msg = _('Text message: %d/%d chars') % (len(text), max_length)
            else:
                max_length = SEVENBIT_MP_SIZE if is_valid_gsm_text(text) else UCS2_MP_SIZE
                used = len(text) - (max_length * (num_sms - 1))
                msg = _('Text message: %d/%d chars (%d SMS)') % (used, max_length, num_sms)

        self.view.get_top_widget().set_title(msg)

    def get_message_text(self):
        """Returns the text written by the user in the textview"""
        textbuffer = self.view['sms_edit_text_view'].get_buffer()
        bounds = textbuffer.get_bounds()
        return textbuffer.get_text(bounds[0], bounds[1])

    def get_numbers_list(self):
        """Returns a list with all the numbers in the recipients_entry"""
        numbers_text = self.numbers_entry.get_text()
        numbers = numbers_text.split(',')
        if numbers[0] == '':
            return []
        return numbers

    def get_messages_list(self):
        """Returns a list with all the messages to send/sav"""
        # get number list and text
        numbers = self.get_numbers_list()
        if not numbers:
            return succeed([])

        message_text = self.get_message_text()
        message_text = unicode(message_text, 'utf8')

        validity = config.get('sms', 'validity')
        #validity = transform_validity[validity]

#        d = self.parent_ctrl.model.get_smsc()
#        def get_smsc_cb(smsc):
#            if not smsc or smsc == '':
#                raise ex.CMEErrorNotFound()
#
#            return [ShortMessageSubmit(number, message_text,
#                    _datetime=datetime.now(), smsc=smsc,
#                    validity=validity) for number in numbers]
#
#        def get_smsc_eb(failure):
#            failure.trap(ex.CMEErrorNotFound)
#            # handle #179
#            message = _('No SMSC number')
#            details = _(
#"""
#In order to send a SMS, %s needs to know the number of your provider's SMSC.
#If you do not know the SMSC number, contact your customer service.
#""") % APP_LONG_NAME
#            dialogs.open_warning_dialog(message, details)
#
#            # prepare the dialog
#            model = PreferencesModel(self.parent_ctrl.model.wrapper)
#            ctrl = SMSPreferencesController(model)
#            view = SMSPreferencesView(ctrl, self)
#            view.set_parent_view(self.view)
#
#            # hide ourselves
#            self.model.unregister_observer(self)
#            self.view.hide()
#            # show the dialog
#            view.show()
#
#        d.addCallback(get_smsc_cb)
#        d.addErrback(get_smsc_eb)
#        return d

    def set_entry_text(self, text):
        self.numbers_entry.set_text(text)

    def save_messages_to_db(self, smslist, where):
        messages = get_messages_obj(self.parent_ctrl.model.get_device())
        smslistback = messages.add_messages(smslist, where)
        tv_name = TV_DICT[where]
        model = self.parent_ctrl.view[tv_name].get_model()
        model.add_messages(smslistback)

    def delete_messages_from_db_and_tv(self, smslist):
        messages = get_messages_obj(self.parent_ctrl.model.get_device())
        messages.delete_messages(smslist)
        model = self.parent_ctrl.view['drafts_treeview'].get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 4) in smslist:
                model.remove(iter)
            iter = model.iter_next(iter)


class ForwardSmsController(NewSmsController):
    """Controller for ForwardSms"""

    def __init__(self, model, parent_ctrl):
        super(ForwardSmsController, self).__init__(model, parent_ctrl)

    def set_recipient_numbers(self, text):
        self.numbers_entry.set_text(text)

    def set_textbuffer_text(self, text):
        textbuffer = self.view['sms_edit_text_view'].get_buffer()
        textbuffer.set_text(text)

    def set_textbuffer_focus(self):
        textwindow = self.view['sms_edit_text_view']
        textwindow.grab_focus()

    def set_processed_sms(self, sms):
        self.sms = sms
