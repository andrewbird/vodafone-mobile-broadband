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
Controllers for preferences
"""
__version__ = "$Rev: 1172 $"

from wader.common.config import config
from wader.vmc.translate import _
from wader.common.dialers import wvdial
#from wader.vmc.persistent import net_manager
from gtkmvc import Controller
import wader.vmc.dialogs as dialogs
from wader.vmc.models.preferences import VALIDITY_DICT, SMSCItem
from wader.vmc.tray import tray_available
from wader.vmc.contrib.ValidatedEntry import ValidatedEntry, v_phone

class PreferencesController(Controller):
    """Controller for preferences"""

    def __init__(self, model, parent_ctrl):
        Controller.__init__(self, model)
        self.parent_ctrl = parent_ctrl
        # handler id of self.view['gnomekeyring_checkbutton']::toggled
        self._hid1 = None
        # handler id of self.view['show_icon_checkbutton']::toggled
        self._hid2 = None

    def register_view(self, view):
        Controller.register_view(self, view)
        self.setup_signals()

    def setup_signals(self):
        # setting up the gnomekeyring checkbox
        def keyringtoggled_cb(checkbutton):
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
                    # block the handler so the set_active method doesnt executes
                    # this callback again
                    checkbutton.handler_block(self._hid1)
                    checkbutton.set_active(False)
                    # restore handler
                    checkbutton.handler_unblock(self._hid1)
                    message = _("Missing dependency")
                    details = _(
"""To use this feature you need the gnomekeyring module""")
                    dialogs.open_warning_dialog(message, details)
                    return True

        # keep a reference of the handler id
        self._hid1 = self.view['gnomekeyring_checkbutton'].connect('toggled',
                                                        keyringtoggled_cb)

        def show_icon_cb(checkbutton):
            if checkbutton.get_active():
                if not tray_available():
                    # block the handler so the set_active method doesnt
                    # executes this callback again
                    checkbutton.handler_block(self._hid2)
                    checkbutton.set_active(False)
                    # restore handler
                    checkbutton.handler_unblock(self._hid2)
                    message = _("Missing dependency")
                    details = _("""
To use this feature you need either pygtk >= 2.10 or the egg.trayicon module
""")
                    dialogs.open_warning_dialog(message, details)
                    return True
                else:
                    # attach and show systray icon
#                    self.parent_ctrl._setup_trayicon(ignoreconf=True)
                    # if there's an available tray, enable this chkbtn
                    close_win_chkbtn = self.view['close_window_checkbutton']
                    close_win_chkbtn.set_sensitive(True)

            else:
                # detach icon from systray
#                self.parent_ctrl._detach_trayicon()
                # close_window_checkbutton depends on this checkbutton
                # being active, thats why we set insensitive the chkbtn
                self.view['close_window_checkbutton'].set_sensitive(False)
                self.view['close_window_checkbutton'].set_active(False)

        # keep a reference of the handler id
        self._hid2 = self.view['show_icon_checkbutton'].connect('toggled',
                                                                show_icon_cb)

    def get_selected_sms_profile(self):
        model = self.view['sms_profiles_combobox'].get_model()


    def get_selected_dialer_profile(self):
        model = self.view['dialer_profiles_combobox'].get_model()
        index = self.view['dialer_profiles_combobox'].get_active()
        if index < 0:
            return None
        else:
            name = model[index][0]
            return wvdial.get_profile_from_name(name)

    # ------------------------------------------------------------ #
    #                       Signals Handling                       #
    # ------------------------------------------------------------ #
    def _on_traffic_entry_value_changed(self):
        max_traffic = self.view['maximum_traffic_entry'].get_value()
        threshold = self.view['threshold_entry'].get_value()
        if threshold > max_traffic:
            self.view['threshold_entry'].set_value(max_traffic)

    def on_maximum_traffic_entry_value_changed(self, widget):
        self._on_traffic_entry_value_changed()

    def on_threshold_entry_value_changed(self, widget):
        self._on_traffic_entry_value_changed()

    def on_usage_notification_check_toggled(self, widget):
        self.view['threshold_entry'].set_sensitive(widget.get_active())

    def on_preferences_ok_button_clicked(self, widget):
        # first page
        if self.view['custom_profile_checkbutton'].get_active():
            # get combobox option
            profile = self.get_selected_dialer_profile()
            config.current_profile.set('connection',
                                       'dialer_profile', profile.name)
        else:
            # use default profile
            config.current_profile.set('connection',
                                       'dialer_profile', 'default')

        config.current_profile.write()

        # second page
        exit_without_confirmation = \
            self.view['exit_without_confirmation_checkbutton'].get_active()
        minimize_to_tray = self.view['close_window_checkbutton'].get_active()
        show_icon = self.view['show_icon_checkbutton'].get_active()
        manage_keyring = self.view['gnomekeyring_checkbutton'].get_active()

        config.setboolean('preferences', 'exit_without_confirmation',
                        exit_without_confirmation)
        config.setboolean('preferences', 'show_icon', show_icon)
        config.setboolean('preferences', 'close_minimizes', minimize_to_tray)
        config.setboolean('preferences', 'manage_keyring', manage_keyring)

        # third page
        model = self.view['browser_combobox'].get_model()
        iter = self.view['browser_combobox'].get_active_iter()
        browser_opt = model.get_value(iter, 0)

        if browser_opt == 'xdg-open':
            config.set('preferences', 'browser', browser_opt)
        else:
            browser_binary = self.view['browser_entry'].get_text()
            if not browser_binary:
                return

            config.set('preferences', 'browser', browser_binary)

        model = self.view['mail_combobox'].get_model()
        iter = self.view['mail_combobox'].get_active_iter()
        mail_opt = model.get_value(iter, 0)

        if mail_opt == 'xdg-email':
            config.set('preferences', 'mail', mail_opt)
        else:
            mail_binary = self.view['mail_entry'].get_text()
            if not mail_binary:
                return

            config.set('preferences', 'mail', mail_binary)

        # fourth page
        #XXX: To Current Profile if any?
        max_traffic = self.view['maximum_traffic_entry'].get_value()
        threshold = self.view['threshold_entry'].get_value()
        usage_notification = self.view['usage_notification_check'].get_active()
        config.set('preferences', 'max_traffic', str(int(max_traffic)))
        config.set('preferences', 'traffic_threshold', str(int(threshold)))
        config.setboolean('preferences', 'usage_notification', usage_notification)

        config.write()

        self._hide_ourselves()

    def on_preferences_cancel_button_clicked(self, widget):
        self._hide_ourselves()

    def _hide_ourselves(self):
        self.model.unregister_observer(self)
        self.view.hide()

    # second notebook page stuff
    def on_custom_profile_checkbutton_toggled(self, button):
        if button.get_active():
            self.view['vbox14'].set_sensitive(True)
        else:
            # commenting out to get basic functionality working.
#            config.current_profile.set('connection',
#                                       'dialer_profile', 'default')
#            config.current_profile.write()
            self.view['vbox14'].set_sensitive(False)

        self.view.setup_sms_combobox()

    def on_browser_combobox_changed(self, combobox):
        model = combobox.get_model()
        iter = combobox.get_active_iter()
        if model.get_value(iter, 0) == 'xdg-open':
            self.view['hbox6'].set_sensitive(False)
        else:
            self.view['hbox6'].set_sensitive(True)

    def on_mail_combobox_changed(self, combobox):
        model = combobox.get_model()
        iter = combobox.get_active_iter()
        if model.get_value(iter, 0) == 'xdg-email':
            self.view['hbox7'].set_sensitive(False)
        else:
            self.view['hbox7'].set_sensitive(True)


class SMSPreferencesController(Controller):
    """
    Controller for the SMS preferences window
    """
    def __init__(self, model):
        Controller.__init__(self, model)
        self.initial_smsc = None
        self.smsc_entry = ValidatedEntry(v_phone)

    def register_view(self, view):
        Controller.register_view(self, view)
        self._setup()

    def _setup(self):
        d = self.model.get_smsc()
        def get_smsc_cb(smsc):
            if not smsc:
                # XXX:
                return

            self.smsc_entry.set_text(smsc)
            self.initial_smsc = smsc
            self._check_smsc(smsc)

        d.addCallback(get_smsc_cb)
        self._setup_message_options()

    def _check_smsc(self, smsc):
        d = self.model.get_imsi()
        def get_imsi_cb(imsi):
            # we will setup the combobox options here
            items = []

            network = net_manager.get_network_by_id(imsi)
            if not network:
                # we dont know anything about this network operator, we will
                # just show 'Unknown' in the combobox, giving no options to
                # the user
                items.append(SMSCItem(_("Unknown")))
            else:
                if network.smsc:
                    # we know the network and we have its SMSC
                    if smsc != network.smsc:
                        # as the SMSC is different that the stored one,
                        # we are gonna append "Custom" too
                        items.append(SMSCItem(_("Custom")))
                        items.append(SMSCItem(network.get_full_name(),
                                          network.smsc, active=False))
                    else:
                        items.append(SMSCItem(network.get_full_name(),
                                          network.smsc))
                else:
                    # we dont know the SMSC of this network
                    items.append(SMSCItem(_("Unknown")))

            self.view.populate_smsc_combobox(items)

        d.addCallback(get_imsi_cb)

    def _setup_message_options(self):
        validity = config.get('sms', 'validity')
        if not validity:
            config.set('sms', 'validity', 'maximum')
            config.write()
            validity = 'maximum'

        combobox = self.view['validity_combobox']
        model = combobox.get_model()

        for i, row in enumerate(model):
            option = row[0]
            if validity == VALIDITY_DICT[option]:
                combobox.set_active(i)
                break

    def _hide_myself(self):
        self.view.hide()
        self.model.unregister_observer(self)

    def on_combobox1_changed(self, combobox):
        smscobj = self._get_active_combobox_item('combobox1')
        if smscobj and smscobj.number:
            self.smsc_entry.set_text(smscobj.number)

    def _get_active_combobox_item(self, comboname):
        combobox = self.view[comboname]
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None

        return model[active][0]

    def on_ok_button_clicked(self, widget):
        # save message options
        validity = self._get_active_combobox_item('validity_combobox')
        if validity:
            validity_key = VALIDITY_DICT[validity]
            config.set('sms', 'validity', validity_key)
            config.write()

        # check that we have changed the SMSC info
        if self.smsc_entry.isvalid():
            smscnumber = self.smsc_entry.get_text()
            if self.initial_smsc != smscnumber:
                d = self.model.set_smsc(smscnumber)
                d.addCallback(lambda x: self._hide_myself())
            else:
                self._hide_myself()

    def on_cancel_button_clicked(self, widget):
        self._hide_myself()

