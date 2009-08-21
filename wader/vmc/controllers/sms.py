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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""Controllers for the sms dialogs"""

__version__ = "$Rev: 1172 $"

import datetime

from twisted.internet.defer import DeferredList, succeed

from wader.common.config import config as config
import wader.common.consts as consts
from wader.common.encoding import _
import wader.common.exceptions as ex
from wader.common.messages import get_messages_obj
from wader.common.sms import (ShortMessageSubmit, MAX_LENGTH_7BIT,
                            MAX_LENGTH_UCS2)

from wader.vmc import Controller, Model
from wader.vmc.controllers.contacts import ContactsListController
from wader.vmc.controllers.base import TV_DICT, TV_DICT_REV
from wader.vmc.controllers.preferences import SMSPreferencesController
from wader.vmc.models.preferences import PreferencesModel, transform_validity
from wader.vmc.views.contacts import ContactsListView
from wader.vmc.views.preferences import SMSPreferencesView
from vmc.contrib.ValidatedEntry import ValidatedEntry, v_phone
from wader.vmc import dialogs

SMS_TOOLTIP = \
    _("You can send the SMS to several recipients separating them by commas")

class NewSmsController(Controller):
    """Controller for the new sms dialog"""

    def __init__(self, model, parent_ctrl = None):
        super(NewSmsController, self).__init__(model)
        self.parent_ctrl = parent_ctrl
        self.max_length = MAX_LENGTH_7BIT
        self.numbers_entry = ValidatedEntry(v_phone)
        self.sms = None
        try:
            self.numbers_entry.set_tooltip_text(SMS_TOOLTIP)
        except AttributeError, e:
            # This fails on Ubuntu Feisty, we can live without it
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

    def on_send_button_clicked(self, widget):
        # check that is a valid number
        if not self.numbers_entry.isvalid():
            self.numbers_entry.grab_focus()
            return

        # protect ourselves against multiple presses
        self.view.set_busy_view()
        def get_sms_list_cb(messages):
            if not messages:
                return

            message_text = self.get_message_text()
            if not message_text:
                resp = dialogs.open_warning_request_cancel_ok(
                        _("Send empty message"),
                        _("Are you sure you want to send an empty message?"))
                if not resp: # user said no
                    self.view.set_idle_view()
                    return

            # send the sms
            sms_cb_list = []            
            sent_list = []
            err_list = []
            def list_cb(resp):
                if self.sms:
                    self.delete_messages_from_db_and_tv([self.sms])

                if sent_list:
                    self.save_messages_to_db(sent_list, 
                                             TV_DICT_REV['sent_treeview'])
                if err_list:
                    dialogs.open_warning_dialog(
                        _("Unknown Error"),
                        _("Your message cannot be sent to some of its recipients. Unsent messages have been saved in drafts. Please, check that you have typed the number correctly."))
                    self.save_messages_to_db(err_list,
                                             TV_DICT_REV['drafts_treeview'])
                self.model.unregister_observer(self)
                self.view.hide()

            def try_to_send(sms):
                def ok(ign):
                    sent_list.append(sms)
                def error(failure):
                    failure.trap(ex.CMSError500, ex.CMSError304)
                    err_list.append(sms)
                d = self.parent_ctrl.model.send_sms(sms)
                d.addCallback(ok)
                d.addErrback(error)      
                return d         

            for sms in messages:
                d = try_to_send(sms)
                sms_cb_list.append(d)

            dlist = DeferredList(sms_cb_list)
            dlist.addCallback(list_cb)

        d = self.get_messages_list()
        d.addCallback(get_sms_list_cb)

    def on_save_button_clicked(self, widget):
        # get number list and text
        def get_sms_list_cb(messages):
            if messages:
                where = TV_DICT_REV['drafts_treeview']
                self.save_messages_to_db(messages, where)
                self.model.unregister_observer(self)
                self.view.hide()

        self.get_messages_list().addCallback(get_sms_list_cb)

    def on_cancel_button_clicked(self, widget):
        self.model.unregister_observer(self)
        self.view.hide()

    def on_contacts_button_clicked(self, widget):
        ctrl = ContactsListController(Model(), self)
        view = ContactsListView(ctrl)
        resp = view.run()

    def _textbuffer_changed(self, textbuffer):
        """Handler for the textbuffer changed signal"""
        text = self.get_message_text()

        try:
            text.encode('sms-default')
        except UnicodeError, e:
            self.max_length = MAX_LENGTH_UCS2
        else:
            self.max_length = MAX_LENGTH_7BIT

        charcount = textbuffer.get_char_count()
        if charcount > self.max_length:
            start, end = textbuffer.get_bounds()
            message_text = textbuffer.get_text(start, end)
            textbuffer.set_text(message_text[:self.max_length])
            charcount = self.max_length

        info = dict(chrcnt=charcount, maxchr=self.max_length)
        msg = _('Text message: %(chrcnt)d/%(maxchr)d chars') % info
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
        validity = transform_validity[validity]

        d = self.parent_ctrl.model.get_smsc()
        def get_smsc_cb(smsc):
            if not smsc or smsc == '':
                raise ex.CMEErrorNotFound()

            return [ShortMessageSubmit(number, message_text,
                    _datetime=datetime.datetime.now(), smsc=smsc,
                    validity=validity) for number in numbers]

        def get_smsc_eb(failure):
            failure.trap(ex.CMEErrorNotFound)
            # handle #179
            message = _('No SMSC number')
            details = _(
"""
In order to send a SMS, %s needs to know the number of your provider's SMSC.
If you do not know the SMSC number, contact your customer service.
""") % consts.APP_LONG_NAME
            dialogs.open_warning_dialog(message, details)

            # prepare the dialog
            model = PreferencesModel(self.parent_ctrl.model.wrapper)
            ctrl = SMSPreferencesController(model)
            view = SMSPreferencesView(ctrl, self)
            view.set_parent_view(self.view)

            # hide ourselves
            self.model.unregister_observer(self)
            self.view.hide()
            # show the dialog
            view.show()

        d.addCallback(get_smsc_cb)
        d.addErrback(get_smsc_eb)
        return d

    def set_entry_text(self, text):
        self.numbers_entry.set_text(text)

    def save_messages_to_db(self, smslist, where):
        messages = get_messages_obj(self.parent_ctrl.model.get_sconn())
        smslistback = messages.add_messages(smslist, where)
        tv_name = TV_DICT[where]
        model = self.parent_ctrl.view[tv_name].get_model()
        model.add_messages(smslistback)

    def delete_messages_from_db_and_tv(self, smslist):
        messages = get_messages_obj(self.parent_ctrl.model.get_sconn())
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
