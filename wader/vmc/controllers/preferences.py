# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone
# Author:  Pablo Martí & Nicholas Herriot
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

import gobject
import gtk
from gtkmvc import Controller


from wader.vmc.config import config
from wader.vmc.translate import _
from wader.vmc.dialogs import show_warning_dialog
from wader.vmc.models.preferences import VALIDITY_DICT, SMSCItem
from wader.vmc.tray import tray_available
from wader.vmc.contrib.ValidatedEntry import ValidatedEntry, v_phone
from wader.vmc.consts import CFG_PREFS_DEFAULT_BROWSER, CFG_PREFS_DEFAULT_EMAIL


class PreferencesController(Controller):
    """Controller for preferences"""

    def __init__(self, model, parent_ctrl):
        Controller.__init__(self, model)
        self.parent_ctrl = parent_ctrl
        # handler id of self.view['gnomekeyring_checkbutton']::toggled
        self._hid1 = None
        # handler id of self.view['show_icon_checkbutton']::toggled
        self._hid2 = None

    # setup on initialisation of the view. Make sure you call the setup methods
    # for all the tabs windows in the view.
    def register_view(self, view):
        Controller.register_view(self, view)
        self.setup_sms_tab()
        self.setup_user_prefs_tab()
        self.setup_mail_browser_tab()
        self.setup_usage_tab()
        # set up signals after init
        self.setup_signals()

    def setup_sms_tab(self):
        # setup the sms preferences to reflect what's in our model on startup
        # remember that if 'use an alternative SMSC service centre is set ' is False we have to grey out 'SMSC preferences' so
        # tell the view that he has to do that by checking the show_smsc_preferences flag.

        alternate_smsc_flag = self.model.use_alternate_smsc
        smsc_number = self.model.smsc_number
        smsc_profile = self.model.smsc_profile
        smsc_validity = self.model.smsc_validity

        # setup the smsc number
        self.view.setup_smsc_number(smsc_number)

        # setup the alternate checkbox
        self.view.setup_alternate_smsc_address_checkbox(alternate_smsc_flag)

        # ok lets populate the view of the sms profile box
        smsc_profile_box = gtk.ListStore(gobject.TYPE_STRING)
        iterator = smsc_profile_box.append([self.model.smsc_profile])
        self.view.setup_smsc_profile(smsc_profile_box, iterator, alternate_smsc_flag)

        # finally the validity period
        smsc_validity_box = gtk.ListStore(gobject.TYPE_STRING)

        for key, value in self.model.validities.items():
            if key == self.model.smsc_validity:
                iterator = smsc_validity_box.append([key])
            else:
                smsc_validity_box.append([key])
        self.view.setup_sms_message_validity(smsc_validity_box, iterator)

    def setup_user_prefs_tab(self):
        # setup the user preferences to reflect what's in our model on startup
        # remember that if 'show_icon_on_tray' is False we have to grey out 'Close_window_app_to_tray' so
        # tell the view that he has to do that by checking the show_icon flag and passing this with sensitive flag.
        sensitive = self.model.show_icon

        self.view.setup_user_exit_without_confirmation(self.model.exit_without_confirmation)
        self.view.setup_user_show_icon_on_tray(self.model.show_icon)
        self.view.setup_user_close_window_minimize(self.model.close_minimizes)
        self.view.setup_user_close_window_minimize_enable(sensitive)
        self.view.setup_manage_my_pin(self.model.manage_my_keyring)

    def setup_usage_tab(self):
        # setup the usage tab to reflect what's in our model on startup
        self.view.setup_usage_max_traffic_value(self.model.max_traffic)
        self.view.setup_usage_threshold_value(self.model.traffic_threshold)
        self.view.setup_usage_notification_check(self.model.usage_notification)
        return

    def setup_mail_browser_tab(self):
        # setup the mail and browser tab to reflect what's in our model on startup

        # ok lets populate the view of the mail combo box and text box first
        mail_combo_box = gtk.ListStore(gobject.TYPE_STRING)
        iterator = mail_combo_box.append([CFG_PREFS_DEFAULT_EMAIL])
        custom_iter = mail_combo_box.append([_('Custom')])

        # ok lets get the value for the mail text box from the model if it exists
        mail_text_box = self.model.mail
        active_set = iterator if ( mail_text_box == CFG_PREFS_DEFAULT_EMAIL) else custom_iter
        # set the combo box in the view to show the values
        self.view.setup_application_mail_combo_box(mail_combo_box, active_set)
        # we have to set the text box if it's a custom value otherwise leave blank and show the default.
        if mail_text_box != CFG_PREFS_DEFAULT_EMAIL:
            self.view.setup_application_mail_text_box(mail_text_box)


        # ok lets populate the view of the browser combo box and text box
        browser_combo_box = gtk.ListStore(gobject.TYPE_STRING)
        iterator = browser_combo_box.append([CFG_PREFS_DEFAULT_BROWSER])
        custom_iter = browser_combo_box.append([_('Custom')])

        # ok lets get the value for the browser text box from the model if it exists
        browser_text_box = self.model.browser
        active_set = iterator if ( browser_text_box == CFG_PREFS_DEFAULT_BROWSER) else custom_iter
        # set the combo box in the view to show values
        self.view.setup_application_browser_combo_box(browser_combo_box, active_set)
        # we have to set the browser box if it's a custom value otherwise leave blang and show the default
        if browser_text_box != CFG_PREFS_DEFAULT_BROWSER:
            self.view.setup_application_browser_text_box(browser_text_box)

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
                    show_warning_dialog(message, details)
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
                    show_warning_dialog(message, details)
                    return True
                else:
                    self.view.setup_user_close_window_minimize_enable(True)
            else:
                self.view.setup_user_close_window_minimize_enable(False)

        # keep a reference of the handler id
        self._hid2 = self.view['show_icon_checkbutton'].connect('toggled',
                                                                show_icon_cb)

    def get_selected_sms_profile(self):
        model = self.view['sms_profiles_combobox'].get_model()

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
        # ----- first tab -----
        # lets fetch all the values stored in the view for the first tab and place them in the model.

        # get the sms validity virst
        #sms_validity_view = gtk.ListStore(gobject.TYPE_STRING)
        sms_validity_view = self.view['validity_combobox'].get_model()
        iteration = self.view['validity_combobox'].get_active_iter()
        if iteration is not None:
            validity_option = sms_validity_view.get_value(iteration, 0)
            self.model.smsc_validity = validity_option

        # get the 'use an alternative smsc address' and save to config.
        # If this is set 'true' then we should not bother saving details for profile or smsc number, so first get the value from the view.
        alternate_sms_checkbox = self.view['smsc_profile_checkbutton'].get_active()
        # Now set the model to that value.
        self.model.use_alternate_smsc = alternate_sms_checkbox

        # OK only set the SMSC values if the alternate_sms_checkbox is true.
        if alternate_sms_checkbox==True:
            smsc_profile_view = self.view['sms_profiles_combobox'].get_model()
            iteration = self.view['sms_profiles_combobox'].get_active_iter()
            smsc_profile_option = smsc_profile_view.get_value(iteration, 0)

            # ok lets set the model to the value in the view
            self.model.smsc_profile = smsc_profile_option

            # now get the smsc number from the view and set the model.browser
            smsc_number = self.view['smsc_number'].get_text()
            self.model.smsc_number = smsc_number

        # ----- second tab -----
        # lets fetch all the vaules stored in the view for the second tab.
        exit_without_confirmation = self.view['exit_without_confirmation_checkbutton'].get_active()
        close_minimizes = self.view['close_window_checkbutton'].get_active()
        show_icon = self.view['show_icon_checkbutton'].get_active()
        manage_keyring = self.view['gnomekeyring_checkbutton'].get_active()

        # ok lets set the model with those values. The model can deal with saving them to disk! :-)
        self.model.exit_without_confirmation = exit_without_confirmation
        self.model.close_minimizes = close_minimizes
        self.model.show_icon = show_icon
        self.model.manage_my_keyring = manage_keyring

        # make the change in the parent
        if self.model.show_icon:
            self.parent_ctrl._setup_trayicon(ignoreconf=True)
        else:
            self.parent_ctrl._detach_trayicon()

        # ------third tab -----
        # fetch the browser combo box data and the browser custom drop down list
        browser_combo_view = self.view['browser_combobox'].get_model()
        iteration = self.view['browser_combobox'].get_active_iter()
        browser_options = browser_combo_view.get_value(iteration, 0)

        # ok if the guy selects the xdg-open just save that name value pair in the model
        # otherwise save the entry in the command box
        browser_command = self.view['browser_entry'].get_text()
        if browser_options != CFG_PREFS_DEFAULT_BROWSER and browser_command:
            self.model.browser = browser_command
        else:
            self.model.browser = CFG_PREFS_DEFAULT_BROWSER

        # fetch the mail combo box data and the mail custom drop down list
        mail_combo_view = self.view['mail_combobox'].get_model()
        iteration = self.view['mail_combobox'].get_active_iter()
        mail_options = mail_combo_view.get_value(iteration, 0)

        # ok if the guy selects the xdg-email just save that name value pair in the model
        # otherwise save the entry in the comand box
        mail_command = self.view['mail_entry'].get_text()
        if mail_options != CFG_PREFS_DEFAULT_EMAIL and mail_command:
            self.model.mail = mail_command
        else:
            self.model.mail = CFG_PREFS_DEFAULT_EMAIL

        # ----- fourth tab -----
        # get the value from the view and set the model
        max_traffic = self.view['maximum_traffic_entry'].get_value()
        self.model.max_traffic = max_traffic

        # get the value from the view and set the model
        threshold = self.view['threshold_entry'].get_value()
        self.model.traffic_threshold = threshold

        # get the value from the view and set the model
        usage_notification = self.view['usage_notification_check'].get_active()
        self.model.usage_notification = usage_notification

        # ok lets ask the model to save those items
        self.model.save()
        self._hide_ourselves()

    def on_preferences_cancel_button_clicked(self, widget):
        self._hide_ourselves()

    def _hide_ourselves(self):
        self.model.unregister_observer(self)
        self.view.hide()

    # second notebook page stuff
    def on_custom_smsc_profile_checkbutton_toggled(self, button):
        if button.get_active():
            self.view['vbox14'].set_sensitive(True)
        else:
            self.view['vbox14'].set_sensitive(False)

        #self.view.setup_sms_combobox()

    def on_browser_combobox_changed(self, combobox):
        model = combobox.get_model()
        iter = combobox.get_active_iter()
        if model.get_value(iter, 0) == CFG_PREFS_DEFAULT_BROWSER:
            self.view['hbox6'].set_sensitive(False)
        else:
            self.view['hbox6'].set_sensitive(True)

    def on_mail_combobox_changed(self, combobox):
        model = combobox.get_model()
        iter = combobox.get_active_iter()
        if model.get_value(iter, 0) == CFG_PREFS_DEFAULT_EMAIL:
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

