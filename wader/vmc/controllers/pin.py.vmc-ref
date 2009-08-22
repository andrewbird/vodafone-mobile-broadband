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
"""
Controllers for PIN screens
"""
__version__ = "$Rev: 1172 $"

import wader.common.exceptions as ex
from wader.common.encoding import _
from wader.common.shutdown import shutdown_core
from wader.vmc import Controller
import wader.vmc.dialogs as dialogs
from wader.vmc.controllers.base import WidgetController
from wader.vmc.notification import show_error_notification

from gtk.gdk import color_parse
from gtk import STATE_NORMAL

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
        oldpin = self.view['pin_modify_current_pin_entry'].get_text()
        newpin = self.view['pin_modify_new_pin_entry'].get_text()

        def success_cb(resp):
            self.hide_widgets()
            self.model.unregister_observer(self)
            self.view.hide()

        def pin_req_eb(failure):
            failure.trap(ex.CMEErrorIncorrectPassword, ex.ATError)
            title = _("Incorrect PIN")
            details = _("""
<small>The PIN you've just entered is
incorrect. Bear in mind that after
three failed PINs you'll be asked
for the PUK code</small>
""")
            dialogs.open_warning_dialog(title, details)
            self.view['pin_modify_current_pin_entry'].grab_focus()
            self.view['pin_modify_current_pin_entry'].select_region(0, -1)

        def puk_req_eb(failure):
            failure.trap(ex.CMEErrorSIMPUKRequired)
            self.model.unregister_observer(self)
            self.view.hide()

            # need to arrange for AskPUK form to be called
            shutdown_core() # just for now when user restarts he'll need PUK

        d = self.model.change_pin(oldpin, newpin)
        d.addCallback(success_cb)
        d.addErrback(pin_req_eb)
        d.addErrback(puk_req_eb)

    def on_pin_modify_quit_button_clicked(self, widget):
        self.model.unregister_observer(self)
        self.view.hide()


class ExecuteFuncController(WidgetController):
    """Base class for the ExecuteFuncControllers

    You can register a callback that will be executed when the authentication
    succeeds and an errback that will be executed when the user presses the
    cancel button. It also takes care of hiding any notification shown to the
    user as long as its in the _notifications list.
    """
    def __init__(self, model):
        super(ExecuteFuncController, self).__init__(model)
        self._cbfunc = None
        self._cbargs = None
        self._cbkwds = None
        self._ebfunc = None
        self._ebargs = None
        self._ebkwds = None
        self.mode = None

    def set_callback(self, func, *args, **kwds):
        assert callable(func), "Func is not callable"
        self._cbfunc = func
        self._cbargs = args
        self._cbkwds = kwds

    def set_errback(self, func, *args, **kwds):
        assert callable(func), "Func is not callable"
        self._ebfunc = func
        self._ebargs = args
        self._ebkwds = kwds

    def set_mode(self, mode):
        """Sets the mode of the controller"""
        self.mode = mode

    def on_ok_button_clicked(self, widget):
        raise NotImplementedError()

    def on_pin_entry_activate(self, widget):
        self.view['ok_button'].clicked()

    def _execute_func(self):
        # hide any active notification
        self.hide_widgets()
        # hide ourselves and start it up
        self._cbfunc(*self._cbargs, **self._cbkwds)
        self.view.hide()
        self.model.unregister_observer(self)

    def on_cancel_button_clicked(self, widget):
        # hide any active notification
        self.hide_widgets()
        # execute errback
        try:
            self._ebfunc(*self._ebargs, **self._ebkwds)
        except:
            pass

        self.view.hide()
        self.model.unregister_observer(self)


class AskPUKAndExecuteFuncController(ExecuteFuncController):
    """Controller for the ask puk/puk2 dialog"""

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        puk = self.view['puk_entry'].get_text()
        if not puk or not pin:
            return

        method = getattr(self.model, self.mode)
        d = method(puk, pin)

        def send_puk_cb(resp):
            self._execute_func()

        def send_puk_eb(failure):
            failure.trap(ex.CMEErrorIncorrectPassword)
            title = _("Incorrect PUK")
            details = _("""
<small>The PUK you've just entered is
incorrect. Bear in mind that after
three failed PUKs you'll be asked
for the PUK2 code. Your PIN code
should be your last PIN.</small>
""")
            n = show_error_notification(self.view['pin_entry'], title, details)
            self.append_widget(n)
            self.view['pin_entry'].grab_focus()
            self.view['pin_entry'].select_region(0, -1)
            self.view['puk_entry'].grab_focus()
            self.view['puk_entry'].select_region(0, -1)

        d.addCallback(send_puk_cb)
        d.addErrback(send_puk_eb)


class AskPINAndExecuteFuncController(ExecuteFuncController):
    """Controller for the ask pin dialog"""

    def __init__(self, model):
        super(AskPINAndExecuteFuncController, self).__init__(model)
        self.pin_activate_id = -1

    def register_view(self, view):
        super(AskPINAndExecuteFuncController, self).register_view(view)

        self.view['expander1'].set_sensitive(False) # disable advanced options

        self.view['pin_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def _ask_for_puk_and_hide_me(self):
        # hide any notification around
        self.hide_widgets()
        from wader.vmc.views.pin import AskPUKView
        ctrl = AskPUKAndExecuteFuncController(self.model)
        ctrl.set_callback(self._cbfunc, *self._cbargs, **self._cbkwds)
        ctrl.set_errback(self._ebfunc, *self._ebargs, **self._ebkwds)
        ctrl.set_mode('send_puk')
        view = AskPUKView(ctrl)
        view.show()
        self.model.unregister_observer(self)
        self.view.hide()

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

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        if not pin:
            return

        method = getattr(self.model, self.mode)
        d = method(pin)

        def send_pin_cb(resp):
            self._execute_func()

        def send_pin_incorrect_passwd_eb(failure):
            failure.trap(ex.CMEErrorIncorrectPassword, ex.ATError)
            title = _("Incorrect PIN")
            details = _("""
The PIN you've just entered is
incorrect. Bear in mind that after
three failed PINs you'll be asked
for the PUK code
""")
            notification = \
                show_error_notification(self.view['pin_entry'], title, details)
            self.append_widget(notification)
            self.view['pin_entry'].grab_focus()
            self.view['pin_entry'].select_region(0, -1)

        def send_pin_error_eb(failure):
            failure.trap(ex.CMEErrorOperationNotAllowed)
            d = self.model.check_pin()
            def callback(result):
                resp = result[0].group('resp')
                if resp in '+CPIN: READY':
                    self._execute_func()
                elif resp in '+CPIN: SIM PUK':
                    self._ask_for_puk_and_hide_me()

            def sim_puk_req_eb(failure):
                failure.trap(ex.CMEErrorSIMPUKRequired)
                self._ask_for_puk_and_hide_me()

            def sim_busy_eb(failure):
                failure.trap(ex.CMEErrorSIMBusy)
                d = self.model.check_pin()
                d.addCallback(callback)
                d.addErrback(sim_puk_req_eb)
                d.addErrback(sim_busy_eb)

            d.addCallback(callback)
            d.addErrback(sim_busy_eb)
            d.addErrback(sim_puk_req_eb)

        def send_pin_puk_required_eb(failure):
            failure.trap(ex.CMEErrorSIMPUKRequired)
            self._ask_for_puk_and_hide_me()

        d.addCallback(send_pin_cb)
        d.addErrback(send_pin_incorrect_passwd_eb)
        d.addErrback(send_pin_error_eb)
        d.addErrback(send_pin_puk_required_eb)


class AskPINController(Controller):
    """Asks PIN to user and returns it callbacking a deferred"""
    def __init__(self, model, deferred):
        super(AskPINController, self).__init__(model)
        self.deferred = deferred
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
        self.view['ask_pin_window'].connect('delete-event',shutdown_core)

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
                    details = _(
    """To use this feature you need the gnomekeyring module""")
                    dialogs.open_warning_dialog(message, details)
                    return True

        self._hid = self.view['gnomekeyring_checkbutton'].connect('toggled',
                                                                 toggled_cb)
        self.view['pin_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        if pin:
            # save keyring preferences
            from wader.common.config import config
            active = self.view['gnomekeyring_checkbutton'].get_active()
            config.setboolean('preferences', 'manage_keyring', active)
            config.write()

            # callback the PIN to the state machine
            self.deferred.callback(pin)

            self.view.hide()
            self.model.unregister_observer(self)

    def on_cancel_button_clicked(self, widget):
        self.view.hide()
        self.model.unregister_observer(self)
        shutdown_core()


class AskPUKController(Controller):
    def __init__(self, model, deferred):
        super(AskPUKController, self).__init__(model)
        self.deferred = deferred

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
        self.view['ask_puk_window'].connect('delete-event',shutdown_core)

        self.view['puk_entry'].connect('changed', self.validate)
        self.view['pin_entry'].connect('changed', self.validate)
        self.view['cnf_entry'].connect('changed', self.validate)
        self.validate() # Initial validation

    def on_ok_button_clicked(self, widget):
        pin = self.view['pin_entry'].get_text()
        puk = self.view['puk_entry'].get_text()

        if pin and puk:
            self.deferred.callback((puk, pin))
            self.view.hide()
            self.model.unregister_observer(self)

    def on_cancel_button_clicked(self, widget):
        self.view.hide()
        self.model.unregister_observer(self)
        shutdown_core()

