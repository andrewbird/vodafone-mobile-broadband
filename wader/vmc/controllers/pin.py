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
"""
Controllers for PIN screens
"""

from gtk import STATE_NORMAL
from gtk.gdk import color_parse
from gtkmvc import Controller

from wader.vmc.translate import _
from wader.vmc.dialogs import show_warning_dialog
from wader.vmc.controllers.base import WidgetController


def is_valid_puk(s):
    return (len(s) == 8) and s.isdigit()


def is_valid_pin(s):
    return (len(s) >= 4) and (len(s) <= 8) and s.isdigit()


def set_bg(widget, colour):
    if colour is 'red':
        col = '#E0B6AF'
    else:
        col = '#FFFFFF'
    widget.modify_base(STATE_NORMAL, color_parse(col))


class PinModifyController(WidgetController):
    """Controller for the PIN modify dialog"""

    def __init__(self, model):
        super(PinModifyController, self).__init__(model)

    def validate(self, widget=None):
        valid = True

        cur = self.view['pin_modify_current_pin_entry']
        new = self.view['pin_modify_new_pin_entry']
        cnf = self.view['pin_modify_confirm_pin_entry']

        s = cur.get_text()
        if is_valid_pin(s):
            set_bg(cur, 'white')
        else:
            valid = False
            set_bg(cur, 'red')

        s = new.get_text()
        if is_valid_pin(s):
            set_bg(new, 'white')
        else:
            valid = False
            set_bg(new, 'red')

        s = cnf.get_text()
        if is_valid_pin(s) and s == new.get_text():
            set_bg(cnf, 'white')
        else:
            valid = False
            set_bg(cnf, 'red')

        # We won't enable the OK button until we have a fully validated form
        self.view['pin_modify_ok_button'].set_sensitive(valid)

    def register_view(self, view):
        super(PinModifyController, self).register_view(view)

        self.view['pin_modify_current_pin_entry'].connect('changed', self.validate)
        self.view['pin_modify_new_pin_entry'].connect('changed', self.validate)
        self.view['pin_modify_confirm_pin_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def on_pin_modify_ok_button_clicked(self, widget):
        """
        Submits the change to the card

        We no longer have to check for any error other than bad passwd,
        since we are now validating the form before allowing submission
        """
        def pin_modify_cb():
            self.hide_widgets()
            self.model.unregister_observer(self)
            self.view.hide()

        def pin_modify_eb():
            title = _("Incorrect PIN")
            details = _("""
<small>The PIN you've just entered is
incorrect. Bear in mind that after
three failed PINs you'll be asked
for the PUK code</small>
""")
            show_warning_dialog(title, details)

            self.hide_widgets()
            self.model.unregister_observer(self)
            self.view.hide()

        oldpin = self.view['pin_modify_current_pin_entry'].get_text()
        newpin = self.view['pin_modify_new_pin_entry'].get_text()

        self.model.change_pin(oldpin, newpin, pin_modify_cb, pin_modify_eb)

    def on_pin_modify_quit_button_clicked(self, widget):
        self.model.unregister_observer(self)
        self.view.hide()


class PinEnableController(WidgetController):
    """Controller for the pin Enable dialog"""

    def __init__(self, model, enable, callback, errback):
        super(PinEnableController, self).__init__(model)
        self.enable = enable
        self.callback = callback
        self.errback = errback
        self.pin_activate_id = -1

    def register_view(self, view):
        super(PinEnableController, self).register_view(view)

        self.view['expander1'].set_sensitive(False) # disable advanced options

        self.view['pin_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

        # connect the buttons to the handlers
        self.view['ok_button'].connect('clicked',self.on_pin_enable_ok_button_clicked)
        self.view['cancel_button'].connect('clicked',self.on_pin_enable_cancel_button_clicked)

    def validate(self, widget=None):
        valid = True

        pin = self.view['pin_entry']

        s = pin.get_text()
        if is_valid_pin(s):
            set_bg(pin, 'white')
        else:
            valid = False
            set_bg(pin, 'red')

        # We won't enable the OK button until we have a fully validated form
        self.view['ok_button'].set_sensitive(valid)

        # A little fun {dis,en}abling the enter key
        if valid:
            if self.pin_activate_id == -1:
                self.pin_activate_id = pin.connect('activate', self.on_pin_enable_ok_button_clicked)
        else:
            if self.pin_activate_id >= 0:
                pin.disconnect(self.pin_activate_id)
                self.pin_activate_id = -1

    def on_pin_enable_ok_button_clicked(self, widget):

        def enable_pin_cb(args):
            self.callback(self.enable)
            self.hide_widgets()
            self.model.unregister_observer(self)
            self.view.hide()

        def enable_pin_eb(e):
            title = _("Incorrect PIN")
            details = _("""
<small>The PIN you've just entered is
incorrect. Bear in mind that after
three failed PINs you'll be asked
for the PUK code</small>
""")
            show_warning_dialog(title, details)
            self.errback(self.enable)
            self.hide_widgets()
            self.model.unregister_observer(self)
            self.view.hide()

        pin = self.view['pin_entry'].get_text()
        self.model.enable_pin(self.enable, pin, enable_pin_cb, enable_pin_eb)

    def on_pin_enable_cancel_button_clicked(self, widget):
        self.errback(self.enable)
        self.hide_widgets()
        self.model.unregister_observer(self)
        self.view.hide()


class AskPINController(Controller):
    """Asks PIN to user and returns it callbacking a deferred"""
    def __init__(self, model):
        super(AskPINController, self).__init__(model)
        # handler id of self.view['gnomekeyring_checkbutton']::toggled
        self._hid = None
        self.pin_activate_id = -1

    def validate(self, widget=None):
        valid = True

        pin = self.view['pin_entry']

        s = pin.get_text()
        if is_valid_pin(s):
            set_bg(pin, 'white')
        else:
            valid = False
            set_bg(pin, 'red')

        # We won't enable the OK button until we have a fully validated form
        self.view['ok_button'].set_sensitive(valid)

        # A little fun {dis,en}abling the enter key
        if valid:
            if self.pin_activate_id == -1:
                self.pin_activate_id = pin.connect('activate', self.on_ok_button_clicked)
        else:
            if self.pin_activate_id >= 0:
                pin.disconnect(self.pin_activate_id)
                self.pin_activate_id = -1

    def register_view(self, view):
        super(AskPINController, self).register_view(view)
#        self.view['ask_pin_window'].connect('delete-event',self.close_application)

        def toggled_cb(checkbutton):
            """
            Callback for the gnomekeyring_checkbutton::toggled signal

            we are gonna try to import gnomekeyring beforehand, if we
            get an ImportError we will inform the user about what she
            should do
            """
            if checkbutton.get_active():
                try:
                    import gnomekeyring
                except ImportError:
                    # block the handler so the set_active method doesnt
                    # executes this callback again
                    checkbutton.handler_block(self._hid)
                    checkbutton.set_active(False)
                    # restore handler
                    checkbutton.handler_unblock(self._hid)
                    message = _("Missing dependency")
                    details = _("""To use this feature you need the gnomekeyring module""")
                    show_warning_dialog(message, details)
                    return True

        self._hid = self.view['gnomekeyring_checkbutton'].connect('toggled',
                                                                 toggled_cb)
        self.view['pin_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        if pin:
            ## save keyring preferences
            #from wader.common.config import config
            #active = self.view['gnomekeyring_checkbutton'].get_active()
            #config.setboolean('preferences', 'manage_keyring', active)
            #config.write()

            self.model.send_pin(pin, self.model.enable_device)
            self.view.hide()
            self.model.unregister_observer(self)

    def on_cancel_button_clicked(self, widget):
        self.view.hide()
        self.model.unregister_observer(self)
#        self.close_application()


class AskPUKController(Controller):
    def __init__(self, model):
        super(AskPUKController, self).__init__(model)

    def validate(self, widget=None):
        valid = True

        puk = self.view['puk_entry']
        pin = self.view['pin_entry']
        cnf = self.view['cnf_entry']

        s = puk.get_text()
        if is_valid_puk(s):
            set_bg(puk, 'white')
        else:
            valid = False
            set_bg(puk, 'red')

        s = pin.get_text()
        if is_valid_pin(s):
            set_bg(pin, 'white')
        else:
            valid = False
            set_bg(pin, 'red')

        s = cnf.get_text()
        if is_valid_pin(s) and s == pin.get_text():
            set_bg(cnf, 'white')
        else:
            valid = False
            set_bg(cnf, 'red')

        # We won't enable the OK button until we have a fully validated form
        self.view['ok_button'].set_sensitive(valid)

    def register_view(self, view):
        super(AskPUKController, self).register_view(view)
#        self.view['ask_puk_window'].connect('delete-event',self.close_application)

        self.view['puk_entry'].connect('changed', self.validate)
        self.view['pin_entry'].connect('changed', self.validate)
        self.view['cnf_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        puk = self.view['puk_entry'].get_text()

        if pin and puk:
            self.model.send_puk(puk, pin, self.model.enable_device)
            self.view.hide()
            self.model.unregister_observer(self)

    def on_cancel_button_clicked(self, widget):
        self.view.hide()
        self.model.unregister_observer(self)
#        self.close_application()

