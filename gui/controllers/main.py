# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano, Isaac Clerencia
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
Main controller for the application
"""

import os
import re
from subprocess import Popen

import gtk
from gettext import dgettext
from gobject import timeout_add_seconds

from wader.common.signals import SIG_SMS_COMP, SIG_SMS_DELV
from wader.common.keyring import KeyringInvalidPassword

from gui.controllers.base import WidgetController, TV_DICT, TV_DICT_REV
from gui.controllers.contacts import (AddContactController,
                                          SearchContactController)
from gui.views.contacts import AddContactView, SearchContactView
from gui.config import config
from gui.logger import logger
from gui.dialogs import (show_profile_window,
                               show_warning_dialog, ActivityProgressBar,
                               show_warning_request_cancel_ok,
                               show_about_dialog, show_error_dialog,
                               ask_password_dialog,
                               open_dialog_question_checkbox_cancel_ok,
                               save_csv_file, open_import_csv_dialog)
from gui.keyring_dialogs import NewKeyringDialog, KeyringPasswordDialog
from gui.utils import find_windows, get_error_msg, raise_window
from gui.translate import _
from gui.tray import get_tray_icon
from gui.consts import (GTK_LOCK, GUIDE_DIR, IMAGES_DIR, APP_URL,
                              APP_LONG_NAME, CFG_PREFS_DEFAULT_BROWSER,
                              CFG_PREFS_DEFAULT_EMAIL,
                              CFG_PREFS_DEFAULT_TRAY_ICON,
                              CFG_PREFS_DEFAULT_CLOSE_MINIMIZES,
                              CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION)
from gui.constx import (GUI_SIM_AUTH_NONE, GUI_SIM_AUTH_PIN,
                              GUI_SIM_AUTH_PUK, GUI_SIM_AUTH_PUK2,
                              GUI_MODEM_STATE_NODEVICE,
                              GUI_MODEM_STATE_HAVEDEVICE,
                              GUI_MODEM_STATE_ENABLED,
                              GUI_MODEM_STATE_REGISTERED,
                              GUI_MODEM_STATE_CONNECTED)

from gui.contacts import SIMContact
from gui.phonebook import (get_phonebook, Contact,
                                all_same_type, all_contacts_writable)
from gui.csvutils import CSVUnicodeWriter, CSVContactsReader
from gui.messages import get_messages_obj, is_sim_message

from gui.network_codes import get_customer_support_info

from gui.views.diagnostics import DiagnosticsView
from gui.controllers.diagnostics import DiagnosticsController

from gui.views.sms import NewSmsView, ForwardSmsView
from gui.controllers.sms import NewSmsController, ForwardSmsController

from gui.views.payt import PayAsYouTalkView
from gui.controllers.payt import PayAsYouTalkController

from gui.views.pin import PinModifyView, PinEnableView, AskPUKView, AskPINView
from gui.controllers.pin import (PinModifyController, PinEnableController,
                                        AskPUKController, AskPINController)

from gui.models.preferences import PreferencesModel
from gui.controllers.preferences import PreferencesController
from gui.views.preferences import PreferencesView

from gui.models.profile import ProfileModel
from gui.views.profile import APNSelectionView
from gui.controllers.profile import APNSelectionController


def get_fake_toggle_button():
    """Returns a toggled L{gtk.ToggleToolButton}"""
    button = gtk.ToggleToolButton()
    button.set_active(True)
    return button


class MainController(WidgetController):
    """
    I am the controller for the main window
    """

    def __init__(self, model):
        model.ctrl = self
        super(MainController, self).__init__(model)
        self.cid = None

        self.signal_matches = []

        self.apb = None  # activity progress bar
        self.tray = None
        # ignore cancelled connection attempts errors
        self._ignore_no_reply = False

    def register_view(self, view):
        super(MainController, self).register_view(view)
        self._setup_trayicon()
        self.connect_to_signals()
        self.start()

    def start(self):
        self.view.set_view_state(GUI_MODEM_STATE_NODEVICE)

        self.model.populate_last_month()
        self.model.populate_curr_month()

        # we're on SMS mode
        self.on_sms_button_toggled(get_fake_toggle_button())

    def connect_to_signals(self):
        self.view['main_window'].connect("delete_event",
                                         self._quit_or_minimize)

        self.cid = self.view['connect_button'].connect('toggled',
                                            self.on_connect_button_toggled)

        for treeview_name in list(set(TV_DICT.values())):
            treeview = self.view[treeview_name]
            treeview.connect('key_press_event', self.__on_treeview_key_press)
            if treeview.name != 'contacts_treeview':
                treeview.connect('row-activated', self._row_activated_tv)

    def _quit_or_minimize(self, *args):
        close_minimizes = config.get('preferences', 'close_minimizes',
                                        CFG_PREFS_DEFAULT_CLOSE_MINIMIZES)
        show_icon = config.get('preferences', 'show_icon',
                                  CFG_PREFS_DEFAULT_TRAY_ICON)
        if close_minimizes and show_icon:
            # pretend the delete_event didn't happen and hide the window
            window = self.view.get_top_widget()
            window.emit_stop_by_name("delete_event")
            window.hide()
            return True
        else:
            return self._quit_confirm_exit()

    def _quit_confirm_exit(self):
        exit_wo_conf = config.get('preferences', 'exit_without_confirmation',
                                  CFG_PREFS_DEFAULT_EXIT_WITHOUT_CONFIRMATION)
        if exit_wo_conf:
            return self._quit_check_connection()

        resp, checked = open_dialog_question_checkbox_cancel_ok(
                    self.view,
                    _("Quit %s") % APP_LONG_NAME,
                    _("Are you sure you want to exit?"))

        if checked:
            config.set('preferences', 'exit_without_confirmation', resp)

        if resp:
            return self._quit_check_connection()

        return True

    def _quit_check_connection(self, *args):
        if self.model.dial_path:
            show_warning_dialog(_("Can not close application"),
                               _("Can not close while a connection is active"))
            window = self.view.get_top_widget()
            try:
                window.emit_stop_by_name('delete_event')
            except IOError:
                pass

            return True
        else:
            self.view.start_throbber()
            # Quit is slow to happen, it can leave user wondering
            # if he pressed the button, so hide before actual close
            self.view.hide()
            self.model.quit(self._close_application_cb)
            return False

    def ask_for_pin(self):
        ctrl = AskPINController(self.model)
        view = AskPINView(ctrl)
        view.show()

    def ask_for_puk(self):
        ctrl = AskPUKController(self.model)
        view = AskPUKView(ctrl)
        view.set_puk_view()
        view.show()

    def ask_for_puk2(self):
        ctrl = AskPUKController(self.model)
        view = AskPUKView(ctrl)
        view.set_puk2_view()
        view.show()

    def ask_for_new_profile(self):

        def apn_callback(network):
            profile_model = ProfileModel(
                                self.model.profiles_model,  # parent
                                self.model,                 # main
                                network=network)
            show_profile_window(self.model.profiles_model,  # parent
                                self.model,                 # main
                                profile=profile_model)

        def imsi_callback(imsi):
            ctrl = APNSelectionController(self.model, imsi, apn_callback)
            view = APNSelectionView(ctrl)
            view.show()

        self.model.get_imsi(imsi_callback)

    def _close_application_cb(self, *args):
        message_mgr = get_messages_obj(self.model.device)
        message_mgr.close()

        try:
            os.unlink(GTK_LOCK)
        except OSError:
            pass

        self.view.stop_throbber()
        gtk.main_quit()

    def _setup_connection_signals(self):
        pass
        #self.model.bus.add_signal_receiver(
        #                        self._on_disconnect_cb,
        #                        "Disconnected",
        #                        dbus_interface=consts.WADER_DIALUP_INTFACE)

    def _generate_customer_support_text(self, imsi):
        utxt = '"' + _('Unknown') + '"'
        args = {'url': APP_URL, 'shortcode': utxt, 'international': utxt}

        nums = get_customer_support_info(imsi)
        if nums is not None:
            if nums[0] is not None:
                args['shortcode'] = nums[0]
            if nums[1] is not None:
                args['international'] = nums[1]

        return _("You can easily find answers to the most common"
            " questions in the help menu, in your company's support center and"
            " in the support area at:"
            "\n\n%(url)s."
            "\n\nIf you still have difficulties you can call to Vodafone's"
            " Customer Support Center, the numbers are:"
            "\n\n%(shortcode)s, if you are using Vodafone's network, or"
            "\n\n%(international)s if you are calling from other network."
            ) % args

    def update_connection_time(self):
        if not self.model.is_connected():
            return False  # don't want to be called again

        self.view.set_connection_time(self.model.get_connection_time())
        return True

    # properties
    def property_status_value_change(self, model, old, new):
        self.view.set_status_line(self.model.status,
                                     self.model.registration,
                                     self.model.tech,
                                     self.model.operator,
                                     self.model.rssi)

        self.view.set_view_state(new)

        if old < GUI_MODEM_STATE_ENABLED and new >= GUI_MODEM_STATE_ENABLED:
            self.refresh_treeviews()

            def imsi_cb(imsi):
                self.view.set_customer_support_text(
                    self._generate_customer_support_text(imsi))

            self.model.get_imsi(imsi_cb)

        if old < GUI_MODEM_STATE_CONNECTED and \
                new >= GUI_MODEM_STATE_CONNECTED:
            self.model.start_stats_tracking()
            self.view.set_connection_time("0:00:00")
            timeout_add_seconds(1, self.update_connection_time)

        if old > GUI_MODEM_STATE_REGISTERED and \
                new <= GUI_MODEM_STATE_REGISTERED:
            self.model.stop_stats_tracking()
            self.model.dial_path = None

    def property_registration_value_change(self, model, old, new):
        self.view.set_status_line(self.model.status,
                                     self.model.registration,
                                     self.model.tech,
                                     self.model.operator,
                                     self.model.rssi)

    def property_tech_value_change(self, model, old, new):
        self.view.set_status_line(self.model.status,
                                     self.model.registration,
                                     self.model.tech,
                                     self.model.operator,
                                     self.model.rssi)

    def property_operator_value_change(self, model, old, new):
        self.view.set_status_line(self.model.status,
                                     self.model.registration,
                                     self.model.tech,
                                     self.model.operator,
                                     self.model.rssi)

    def property_rssi_value_change(self, model, old, new):
        self.view.set_status_line(self.model.status,
                                     self.model.registration,
                                     self.model.tech,
                                     self.model.operator,
                                     self.model.rssi)

    def on_net_password_required(self, opath, tag):
        password = ask_password_dialog(self.view)

        if password:
            from gui.profiles import manager
            profile = manager.get_profile_by_object_path(opath)
            secrets = {'gsm': {'passwd': password}}
            profile.set_secrets(tag, secrets)

    def on_keyring_password_required(self, opath, callback=None):
        from gui.profiles import manager
        profile = manager.get_profile_by_object_path(opath)
        password = None

        if profile.secrets.manager.is_new():
            dialog = NewKeyringDialog(self.view.get_top_widget())
            response = dialog.run()
        elif not profile.secrets.manager.is_open():
            dialog = KeyringPasswordDialog(self.view.get_top_widget())
            response = dialog.run()
        else:
            if callback is not None:
                uuid = profile.get_settings()['connection']['uuid']
                callback(profile.secrets.manager.get_secrets(uuid))
            return

        if response == gtk.RESPONSE_OK:
            password = dialog.password_entry.get_text()

        dialog.destroy()

        if password is not None:
            try:
                profile.secrets.manager.open(password)
            except KeyringInvalidPassword:
                title = _("Invalid password")
                details = _("The supplied password is incorrect")
                show_error_dialog(title, details)
                # call ourselves again
                self.on_keyring_password_required(opath, callback=callback)
            else:
                if callback is not None:
                    uuid = profile.get_settings()['connection']['uuid']
                    callback(profile.secrets.manager.get_secrets(uuid))

    def property_device_value_change(self, model, old, new):
        if self.model.device is not None:
            sm = self.model.device.connect_to_signal("DeviceEnabled",
                                            self.on_device_enabled_cb)
            self.signal_matches.append(sm)

            # connect to SIG_SMS_COMP and display SMS
            sm = self.model.device.connect_to_signal(SIG_SMS_COMP,
                                                self.on_sms_received_cb)
            self.signal_matches.append(sm)

            # connect to SIG_SMS_DELV and notify user
            sm = self.model.device.connect_to_signal(SIG_SMS_DELV,
                                                self.on_sms_delivery_cb)
            self.signal_matches.append(sm)

            self.model.status = GUI_MODEM_STATE_HAVEDEVICE
        else:
            while self.signal_matches:
                sm = self.signal_matches.pop()
                sm.remove()
            self._hide_sim_contacts()
            self._hide_sim_messages()
            self.model.status = GUI_MODEM_STATE_NODEVICE

    def property_profile_value_change(self, model, old, new):
        logger.info("A profile has been set for current model %s" % new)

    def property_sim_error_value_change(self, model, old, new):
        if not new:
            return
        elif new == 'org.freedesktop.ModemManager.Gsm.SimNotInserted':
            title = _('SIM error')
            details = _('Perhaps your SIM is not inserted correctly?')
        else:
            title = _('Unknown error')
            details = new

        show_error_dialog(title, details)

    def property_net_error_value_change(self, model, old, new):
        title = _("Error while registering to home network")
        show_error_dialog(title, new)

    def property_sim_auth_required_value_change(self, model, old, new):
        if new == GUI_SIM_AUTH_NONE:
            # XXX: we should check for any of our existing popups and hide them
            pass
        elif new == GUI_SIM_AUTH_PIN:
            # Check for NM's desktop PIN popup
            app_name = dgettext('nm-applet', 'NetworkManager Applet')
            win_name = dgettext('nm-applet', 'SIM PIN unlock required')
            win_list = find_windows(app_name, win_name)
            if win_list is None or len(win_list) == 0:
                self.ask_for_pin()
            else:
                raise_window(win_list[0])
        elif new == GUI_SIM_AUTH_PUK:
            self.ask_for_puk()
        elif new == GUI_SIM_AUTH_PUK2:
            self.ask_for_puk2()

    def property_profile_required_value_change(self, model, old, new):
        if new:
            self.ask_for_new_profile()

    def property_current_month_name_value_change(self, model, old, new):
        self.view.set_usage_value('current_month_label', new)

    def property_current_summed_2g_value_change(self, model, old, new):
        self.view.set_usage_value('current_summed_2g_label', new)

    def property_current_summed_3g_value_change(self, model, old, new):
        self.view.set_usage_value('current_summed_3g_label', new)

    def property_current_summed_total_value_change(self, model, old, new):
        self.view.set_usage_value('current_summed_total_label', new)
        self.view.set_usage_bar_value('current-total', new)

    def property_current_session_2g_value_change(self, model, old, new):
        self.view.set_usage_value('current_session_2g_label', new)

    def property_current_session_3g_value_change(self, model, old, new):
        self.view.set_usage_value('current_session_3g_label', new)

    def property_current_session_total_value_change(self, model, old, new):
        self.view.set_usage_value('current_session_total_label', new)

    def property_last_month_name_value_change(self, model, old, new):
        self.view.set_usage_value('last_month_label', new)

    def property_last_month_2g_value_change(self, model, old, new):
        self.view.set_usage_value('last_summed_2g_label', new)

    def property_last_month_3g_value_change(self, model, old, new):
        self.view.set_usage_value('last_summed_3g_label', new)

    def property_last_month_total_value_change(self, model, old, new):
        self.view.set_usage_value('last_summed_total_label', new)
        self.view.set_usage_bar_value('last-total', new)

    def property_rx_rate_value_change(self, model, old, new):
        if old != new:
            self.view.set_transfer_rate(new, upload=False)
            logger.info("Rate rx: %d" % new)

    def property_tx_rate_value_change(self, model, old, new):
        if old != new:
            self.view.set_transfer_rate(new, upload=True)
            logger.info("Rate tx: %d" % new)

    def property_transfer_limit_exceeded_value_change(self, model, old, new):
        if not old and new:
            show_warning_dialog(_("Transfer limit exceeded"),
                                _("You have exceeded your transfer limit"))

    def on_sms_menu_item_activate(self, widget):
        self.on_sms_button_toggled(get_fake_toggle_button())

    def on_usage_menu_item_activate(self, widget):
        self.on_usage_button_clicked(get_fake_toggle_button())

    def on_support_menu_item_activate(self, widget):
        self.on_support_button_toggled(get_fake_toggle_button())

    def on_sms_button_toggled(self, widget):
        if widget.get_active():
            self.view['toolbar_frame_alignment'].show()
            self.view['usage_frame'].hide()
            self.view['support_notebook'].hide()
            self.view['sms_tool_button'].set_active(True)
            self.view['usage_tool_button'].set_active(False)
            self.view['support_tool_button'].set_active(False)

    def on_usage_button_clicked(self, widget):
        if widget.get_active():
            self.view['toolbar_frame_alignment'].hide()
            self.view['usage_frame'].show()
            self.view['support_notebook'].hide()
            self.view['sms_tool_button'].set_active(False)
            self.view['usage_tool_button'].set_active(True)
            self.view['support_tool_button'].set_active(False)

            self.update_usage_view()
            self.view.show_current_session(self.model.is_connected())

    def on_support_button_toggled(self, widget):
        if widget.get_active():
            self.view['toolbar_frame_alignment'].hide()
            self.view['usage_frame'].hide()
            self.view['support_notebook'].show()
            self.view['sms_tool_button'].set_active(False)
            self.view['usage_tool_button'].set_active(False)
            self.view['support_tool_button'].set_active(True)

    def on_topup_button_clicked(self, widget):
        logger.info("GUI Main: Topup button clicked")
        ctrl = PayAsYouTalkController(self.model)
        view = PayAsYouTalkView(ctrl, self.view)
        view.show()

    def on_mail_button_clicked(self, widget):
        if self._check_if_connected():
            binary = config.get('preferences', 'mail', CFG_PREFS_DEFAULT_EMAIL)
            if binary:
                Popen([binary, 'REPLACE@ME.COM'])

    def on_sms_delivery_cb(self, reference):
        """
        Executed whenever a SMS delivery receipt is received
        """
        # XXX: Will just notify user for now. If it's possible in the future,
        #      it would be good to set flag against those messages in the sent
        #      items to indicate delivery status, but that's probably going to
        #      require changes in the on disk DB format to give persistence
        sms = None

        # Find the original message
        treeview = self.view['sent_treeview']
        for message in treeview.get_model().get_messages():
            msgref = message.status_reference
            if msgref is not None and msgref == reference:
                sms = message
                break

        # Send notification - just display the first forty chars though
        if sms:
            number, text = sms.number, sms.text[:40]
        else:
            number, text = _('Unknown'), ''
        title = _("SMS receipt received for %s") % number
        self.tray.attach_notification(title, text, stock=gtk.STOCK_INFO)

    def on_sms_received_cb(self, index, complete):
        """
        Executed whenever a complete SMS is received, may be single or
        fully reassembled multipart message

        Will read, populate the treeview and notify the user
        """
        messages_obj = get_messages_obj(self.model.device)
        sms = messages_obj.get_message(index)

        # It will take care of looking up the number in the phonebook
        # to show the name if it's a known contact instead of its number
        contact = self._find_contact_by_number(sms.number)
        if contact:
            who = contact.get_name()
            contacts_list = [contact]
        else:
            who = sms.number
            contacts_list = None

        # Populate treeview
        treeview = self.view['inbox_treeview']
        model = treeview.get_model()
        model.add_message(sms, contacts_list)

        # Get the path of the new message and scroll to it
        paths = [str(i) for i, row in enumerate(model) if row[4] is sms]
        if len(paths):
            treeview.scroll_to_cell(paths[0])

        # Send notification
        title = _("SMS received from %s") % who
        self.tray.attach_notification(title, sms.text, stock=gtk.STOCK_INFO)

    def on_is_pin_enabled_cb(self, enabled):
        self.view['change_pin1'].set_sensitive(enabled)

        checkmenuitem = self.view['request_pin1']
        if checkmenuitem.get_active() != enabled:
            checkmenuitem.set_active(enabled)

    def on_device_enabled_cb(self, opath):
        self.model.pin_is_enabled(self.on_is_pin_enabled_cb,
                                  lambda * args: True)

    def _on_connect_cb(self, dev_path):
        logger.info("Connected")

        if self.apb:
            self.apb.close()
            self.apb = None

        self.model.dial_path = dev_path
        self.model.status = GUI_MODEM_STATE_CONNECTED
        self.model.set_our_dial_attempt(None)

    def _on_connect_eb(self, e):
        logger.error("_on_connect_eb: %s" % e)

        if self.apb:
            self.apb.close()
            self.apb = None

        if 'NoReply' in get_error_msg(e) and self._ignore_no_reply:
            # do not show NoReply exception as we were expecting it
            self._ignore_no_reply = False
        elif 'TypeError' in get_error_msg(e) and self._ignore_no_reply:
            # do not show TypeError exception as we were expecting it
            # as ActivateConnection returns None instead of an object
            # path.
            self._ignore_no_reply = False
        elif 'RuntimeError' in get_error_msg(e):
            title = _('Failed connection attempt')
            show_warning_dialog(title, _('Unable to connect'))
        else:
            title = _('Failed connection attempt')
            show_error_dialog(title, get_error_msg(e))

        self.model.set_our_dial_attempt(None)

    def _on_disconnect_cb(self, *args):
        logger.info("Disconnected")

        if self.apb:
            self.apb.close()
            self.apb = None

        if self.model.dial_path:
            # if dial_path is not None, it means that the connection was
            # deactivated externally to wader, either through nm-applet
            # or because pppd died or something.
            dialmanager = self.model.get_dialer_manager()
            dialmanager.DeactivateConnection(self.model.dial_path)
            self.model.dial_path = None

    def _on_disconnect_eb(self, e):
        logger.error("_on_disconnect_eb: %s" % e)

        if self.apb:
            self.apb.close()
            self.apb = None

    def get_trayicon_menu(self):
        button = self.view['connect_button']
        menu = gtk.Menu()

        if self.model.is_connected():
            item = gtk.ImageMenuItem(_("Disconnect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(IMAGES_DIR, 'stop16x16.png'))
            item.connect("activate", lambda w: button.set_active(False))
        else:
            item = gtk.ImageMenuItem(_("Connect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(IMAGES_DIR, 'connect-16x16.png'))
            item.connect("activate", lambda w: button.set_active(True))

        item.set_image(img)
        item.set_sensitive(self.model.device is not None)
        item.show()
        menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        item = gtk.ImageMenuItem(_("Send SMS"))
        img = gtk.Image()
        img.set_from_file(os.path.join(IMAGES_DIR, 'sms16x16.png'))
        item.set_image(img)
        item.connect("activate", self.on_new_sms_activate)
        item.set_sensitive(self.model.device is not None)
        item.show()
        menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        item = gtk.ImageMenuItem(_("Quit"))
        img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self.on_quit_menu_item_activate)
        item.show()
        menu.append(item)

        return menu

    def on_icon_popup_menu(self, icon, button, activate_time):
        menu = self.get_trayicon_menu()
        menu.popup(None, None, None, button, activate_time)

    def get_contacts_popup_menu(self, pathinfo, treeview):
        """Returns a popup menu for the contacts treeview"""
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        contacts = [model.get_value(_iter, 3) for _iter in iters]

        menu = gtk.Menu()

        item = gtk.ImageMenuItem(_("Send SMS"))
        item.connect("activate", self._send_sms_to_contact, treeview)
        img = gtk.Image()
        img.set_from_file(os.path.join(IMAGES_DIR, 'sms16x16.png'))
        item.set_image(img)
        item.show()
        menu.append(item)

        # Figure out whether we should show delete, edit,
        # or no extra menu items
        if all_contacts_writable(contacts):
            item = gtk.ImageMenuItem(_("_Delete"))
            img = gtk.image_new_from_stock(gtk.STOCK_DELETE,
                                           gtk.ICON_SIZE_MENU)
            item.set_image(img)
            item.connect("activate", self.delete_entries, pathinfo, treeview)
            item.show()
            menu.append(item)

        elif all_same_type(contacts):
            editor = contacts[0].external_editor()
            if editor:
                item = gtk.ImageMenuItem(_("Edit"))
                img = gtk.image_new_from_stock(gtk.STOCK_EDIT,
                                               gtk.ICON_SIZE_MENU)
                item.set_image(img)

                item.connect("activate", self._edit_external_contacts, editor)

                item.show()
                menu.append(item)

        return menu

    def on_import_contacts1_activate(self, widget):
        filepath = open_import_csv_dialog()
        if filepath:
            phonebook = get_phonebook(self.model.device)

            try:
                reader = CSVContactsReader(open(filepath))
            except ValueError:
                message = _('Invalid CSV format')
                details = _("""
The csv file that you have tried to import has an invalid format.""")
                show_warning_dialog(message, details)
            else:
                phonebook.add_contacts(list(reader), True)

                # Flip the notebook to contacts
                self.view['main_notebook'].set_current_page(3)
                self.refresh_treeviews()

    def on_export_contacts1_activate(self, widget):
        filepath = save_csv_file()
        if filepath:
            writer = CSVUnicodeWriter(open(filepath, 'w'))
            # Now we support different backends we need to be more
            # selective about what we write out?
            contacts = [c.to_csv() for c in self._get_treeview_contacts()
                                if c.is_writable()]
            writer.write_rows(contacts)

    def on_connect_button_toggled(self, widget):
        dialmanager = self.model.get_dialer_manager()

        # Note: Only do something if status REGISTERED or CONNECTED

        if self.model.status == GUI_MODEM_STATE_REGISTERED:
            # user wants to connect
            if not self.model.device:
                show_warning_dialog(
                    _("No device found"),
                    _("No device has been found. Insert one and try again."))
                return

            profiles_model = self.model.profiles_model
            if not profiles_model.has_active_profile():
                show_warning_dialog(
                    _("Profile needed"),
                    _("You need to create a profile for connecting."))
                self.ask_for_new_profile()
                return

            active_profile = profiles_model.get_active_profile()
            if not active_profile.password:
                active_profile.load_password()

            logger.info("Connecting...")

            self.model.set_our_dial_attempt(True)

            dialmanager.ActivateConnection(active_profile.profile_path,
                                           self.model.device_opath,
                                           timeout=40,
                                           reply_handler=self._on_connect_cb,
                                           error_handler=self._on_connect_eb)

            self._setup_connection_signals()

            def cancel_cb():
                # XXX: should not need this
                # self.model.status = _('Not connected')
                self.model.dial_path = None

            def stop_connection_attempt():
                self._ignore_no_reply = True
                dialmanager.StopConnection(self.model.device_opath,
                                           reply_handler=cancel_cb,
                                           error_handler=logger.error)

            self.apb = ActivityProgressBar(_("Connecting"), self)
            self.apb.set_cancel_cb(stop_connection_attempt)
            self.apb.init()

        elif self.model.status == GUI_MODEM_STATE_CONNECTED:
            # user wants to disconnect
            logger.info("Disconnecting...")

            if self.model.dial_path:  # created by us
                dialmanager.DeactivateConnection(self.model.dial_path,
                                        reply_handler=self._on_disconnect_cb,
                                        error_handler=self._on_disconnect_eb)
                self.model.dial_path = None
            else:
                title = _("Invalid Connection")
                details = _("It's likely that this connection was made by the "
                            "Network Manager Applet, please use that to "
                            "deactivate")
                show_error_dialog(title, details)
                logger.warn("Can't deactivate a connection we didn't create")
                # XXX: This brute force approach doesn't work with NM for some
                #      reason, ideally we'd need a new way of asking the wader
                #      dialup service to remove a connection for which we have
                #      no dial_path
                # self.model.device.Disconnect(dbus_interface=MDM_INTFACE,
                #                        reply_handler=self._on_disconnect_cb,
                #                        error_handler=self._on_disconnect_eb)

    def on_preferences_menu_item_activate(self, widget):
        model = PreferencesModel(self.model.device)
        ctrl = PreferencesController(model, self)
        view = PreferencesView(ctrl)
        view.show()

    def on_new_contact_menu_item_activate(self, widget):
        self.view['main_notebook'].set_current_page(3)  # contacts_tv
        ctrl = AddContactController(self.model, self._add_new_contact_cb)
        view = AddContactView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_search_contact_menu_item_activate(self, widget):
        self.view['main_notebook'].set_current_page(3)  # contacts_tv
        ctrl = SearchContactController(self.model, self)
        view = SearchContactView(ctrl)
        view.set_parent_view(self.view)
        view.run()

    def on_quit_menu_item_activate(self, widget):
        self._quit_confirm_exit()

    def on_enable_modem_activate(self, checkmenuitem):
        curval = self.model.is_enabled()
        reqval = checkmenuitem.get_active()

        if reqval != curval:
            self.model.enable_device(reqval)

    def on_change_pin1_activate(self, widget):
        ctrl = PinModifyController(self.model)
        view = PinModifyView(ctrl)
        view.show()

    def on_request_pin1_activate(self, checkmenuitem):

        def is_pin_enabled_cb(curval):
            reqval = checkmenuitem.get_active()
            if reqval != curval:

                def pin_enable_cb(enable):
                    self.view['change_pin1'].set_sensitive(enable)

                def pin_enable_eb(enable):
                    self.view['change_pin1'].set_sensitive(not enable)
                    # Toggle checkmenuitem back, note this will cause it to
                    # activate again, but our is_pin_enabled check will
                    # prevent a loop
                    self.view['request_pin1'].set_active(not enable)

                ctrl = PinEnableController(self.model, reqval,
                                           pin_enable_cb,
                                           pin_enable_eb)
                view = PinEnableView(ctrl)
                view.show()

        self.model.pin_is_enabled(is_pin_enabled_cb,
                                  logger.error)

    def on_new_profile_menuitem_activate(self, widget):
        self.ask_for_new_profile()

    def _build_profiles_menu(self):

        def load_profile(widget, profile):
            profiles_model = self.model.profiles_model
            profiles_model.set_active_profile(profile)
            profiles_model.activate_profile()

            # refresh menu
            self.on_tools_menu_item_activate(get_fake_toggle_button())

        def edit_profile(widget, profile):
            show_profile_window(self.model.profiles_model,  # parent model
                                self.model,                 # main model
                                profile=profile)
            # XXX: check out whether editing a profile should make it active
            # currently it doesn't
            self.on_tools_menu_item_activate(get_fake_toggle_button())

        def delete_profile(widget, profile):
            profiles_model = self.model.profiles_model
            profiles_model.remove_profile(profile)

            # refresh menu
            self.on_tools_menu_item_activate(get_fake_toggle_button())

        profiles = self.model.profiles_model.get_profiles()

        menu1 = gtk.Menu()
        for profile in profiles.values():
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", load_profile, profile)
            item.show()
            if self.model.profiles_model.is_active_profile(profile):
                item.set_sensitive(False)
            menu1.append(item)

        menu2 = gtk.Menu()
        for profile in profiles.values():
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", edit_profile, profile)
            item.show()
            menu2.append(item)

        menu3 = gtk.Menu()
        for profile in profiles.values():
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", delete_profile, profile)
            item.show()
            if self.model.profiles_model.is_active_profile(profile):
                item.set_sensitive(False)
            menu3.append(item)

        return menu1, menu2, menu3

    def on_tools_menu_item_activate(self, widget):
        # build dynamically the menu with the profiles
        parent = self.view['profiles_menu_item']
        menu = gtk.Menu()

        item = gtk.ImageMenuItem(_("_New Profile"))
        img = gtk.image_new_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self.on_new_profile_menuitem_activate)
        menu.append(item)
        item.show()

        load, edit, delete = self._build_profiles_menu()

        item = gtk.MenuItem(_("Load Profile"))
        item.set_submenu(load)
        menu.append(item)
        item.show()

        item = gtk.MenuItem(_("Edit Profile"))
        item.set_submenu(edit)
        menu.append(item)
        item.show()

        item = gtk.MenuItem(_("Delete Profile"))
        item.set_submenu(delete)
        menu.append(item)
        item.show()

        parent.set_submenu(menu)

    def on_diagnostics_item_activate(self, widget):
        ctrl = DiagnosticsController(self.model, self)
        view = DiagnosticsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_help_topics_menu_item_activate(self, widget):
        binary = config.get('preferences', 'browser',
                            CFG_PREFS_DEFAULT_BROWSER)
        if binary:
            index_path = os.path.join(GUIDE_DIR, 'index.html')
            Popen([binary, index_path])

    def on_about_menu_item_activate(self, widget):
        about = show_about_dialog()
        about.run()
        about.destroy()

    def _check_if_connected(self):
        """
        Returns True if connected or if the user does not care if not connected
        """
        if self.model.is_connected():
            return True
        else:
            message = _("Not connected")
            details = _("No mobile connection. Do you want to continue?")
            return show_warning_request_cancel_ok(message, details)

    def _empty_treeviews(self, treeviews):
        for treeview_name in treeviews:
            model = self.view[treeview_name].get_model()
            if model:
                model.clear()

    def _hide_sim_contacts(self):
        """
        Called when the device holding the SIM is removed
        """
        treeview = self.view['contacts_treeview']
        model = treeview.get_model()

        iter = model.get_iter_first()
        while iter:
            obj = model.get_value(iter, 3)
            _iter = model.iter_next(iter)
            if isinstance(obj, SIMContact):
                model.remove(iter)
            iter = _iter

    def _hide_sim_messages(self):
        """
        Called when the device holding the SIM is removed
        """
        treeview = self.view['inbox_treeview']
        model = treeview.get_model()

        iter = model.get_iter_first()
        while iter:
            obj = model.get_value(iter, 4)
            _iter = model.iter_next(iter)
            if is_sim_message(obj):
                model.remove(iter)
            iter = _iter

        # Maybe the current message was removed
        page = self.view['main_notebook'].get_current_page() + 1
        if page == TV_DICT_REV['inbox_treeview']:
            text = self._get_current_message_text(treeview)
            self.view.set_message_preview(text)

    def _find_contact_by_number(self, number):
        treeview = self.view['contacts_treeview']
        model = treeview.get_model()

        contacts = model.find_contacts_by_number(number)
        if not len(contacts):
            return None
        if len(contacts) > 1:
            print "more than one contact matched number %s" % number
            for contact in contacts:
                print contact.get_name()
        return contacts[0]

    def _fill_contacts(self, contacts):
        """Fills the contacts treeview with contacts"""
        treeview = self.view['contacts_treeview']

        model = treeview.get_model()
        model.add_contacts(contacts)

    def _fill_messages(self, messages):
        """
        Fills the messages treeview with SIM & DB SMS

        We're using the contacts list installed in the contacts treeview
        because otherwise, adding dozens of SMS to the treeview would be very
        inefficient, as we would have to lookup the sender number of every SMS
        to find out whether is a known contact or not.
        """
        contacts = self._get_treeview_contacts()

        for sms in messages:
            active_tv = TV_DICT[sms.where]         # get treeview name
            treeview = self.view[active_tv]        # get treeview object
            treeview.get_model().add_message(sms, contacts)  # append to tv

    def update_message_contact_info(self):
        """
        Iterates through each SMS treeview, updating contact info
        """

        contacts = self._get_treeview_contacts()

        for tv in ['inbox_treeview', 'drafts_treeview', 'sent_treeview']:
            treeview = self.view[tv]
            treeview.get_model().update_contacts(contacts)

    def refresh_treeviews(self):
        """
        Fills the treeviews with SMS and contacts
        """

        def messages_cb(contacts, messages):
            # refresh display
            self._empty_treeviews(list(set(TV_DICT.values())))
            self._fill_contacts(contacts)
            self._fill_messages(messages)

        def contacts_cb(contacts):
            # get messages from all backends(inc SIM)
            messages_obj = get_messages_obj(self.model.device)
            messages_obj.get_messages_async(
                            lambda messages: messages_cb(contacts, messages),
                            logger.error)

        # get contacts from all backends(inc SIM)
        phonebook = get_phonebook(device=self.model.device)
        phonebook.get_contacts_async(contacts_cb, logger.error)

    def _get_treeview_contacts(self):
        treeview = self.view['contacts_treeview']
        return treeview.get_model().get_contacts()

    def update_usage_view(self):
        self.view.update_bars_user_limit()

    def on_new_sms_activate(self, widget):
        if hasattr(widget, 'get_active'):  # called by a menu item
            if widget.get_active() == True:
                widget.set_active(False)
            else:
                return

        ctrl = NewSmsController(self.model, self,
                                self._get_treeview_contacts())
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_reply_sms_no_quoting_menu_item_activate(self, widget):
        if hasattr(widget, 'get_active'):  # called by a menu item
            if widget.get_active() == True:
                widget.set_active(False)
            else:
                return

        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(self.model, self,
                                        self._get_treeview_contacts())
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.number)
            ctrl.set_textbuffer_focus()
            view.show()

    def on_reply_sms_quoting_menu_item_activate(self, widget):
        if hasattr(widget, 'get_active'):  # called by a menu item
            if widget.get_active() == True:
                widget.set_active(False)
            else:
                return

        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(self.model, self,
                                        self._get_treeview_contacts())
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.number)
            ctrl.set_textbuffer_text(message.text)
            ctrl.set_textbuffer_focus()
            view.show()

    def on_forward_sms_menu_item_activate(self, widget):
        if hasattr(widget, 'get_active'):  # called by a menu item
            if widget.get_active() == True:
                widget.set_active(False)
            else:
                return

        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(self.model, self,
                                        self._get_treeview_contacts())
            view = ForwardSmsView(ctrl)
            ctrl.numbers_entry.grab_focus()
            ctrl.set_textbuffer_text(message.text)
            view.set_parent_view(self.view)
            view.show()

    def on_delete_menu_item_activate(self, widget):
        page = self.view['main_notebook'].get_current_page() + 1
        treeview = self.view[TV_DICT[page]]
        self.delete_entries(widget, None, treeview)
        treeview.grab_focus()

    def on_generic_treeview_row_button_press_event(self, treeview, event):
        if event.button == 3 and event.type == gtk.gdk.BUTTON_PRESS:
            selection = treeview.get_selection()
            model, pathlist = selection.get_selected_rows()
            if pathlist:
                if treeview.name in ['contacts_treeview']:
                    get_contacts = self.get_contacts_popup_menu
                else:
                    get_contacts = self.get_generic_popup_menu
                menu = get_contacts(pathlist, treeview)
                menu.popup(None, None, None, event.button, event.time)
                return True  # selection is not lost

    def _get_current_message_text(self, treeview):
        path = treeview.get_cursor()[0]
        if path is None:
            return None
        model = treeview.get_model()
        return model[path][4].text

    def on_cursor_changed_treeview_event(self, treeview):
        text = self._get_current_message_text(treeview)
        self.view.set_message_preview(text)

    def on_main_notebook_switch_page(self, notebook, ptr, pagenum):
        """
        Callback for whenever GUI's main notebook is switched

        Basically takes care of showing and hiding the appropiate menubars
        depending on the page the user is viewing
        """
        page = int(pagenum)
        if page == 3:
            self.view['contacts_toolbar'].show()
            self.view['sms_toolbar'].hide()
            self.view.set_message_preview(None)
        else:
            self.view['contacts_toolbar'].hide()
            self.view['sms_toolbar'].show()
            text = self._get_current_message_text(self.view[TV_DICT[page + 1]])
            self.view.set_message_preview(text)

    #----------------------------------------------#
    # MISC FUNCTIONALITY                           #
    #----------------------------------------------#

    def _name_contact_cell_edited(self, widget, path, newname):
        """Handler for the cell-edited signal of the name column"""
        # first check that the edit is necessary
        model = self.view['contacts_treeview'].get_model()
        if newname != model[path][1] and newname:
            contact = model[path][3]
            if contact.set_name(unicode(newname, 'utf8')):
                model[path][1] = newname
                self.update_message_contact_info()

    def _number_contact_cell_edited(self, widget, path, newnumber):
        """Handler for the cell-edited signal of the number column"""
        model = self.view['contacts_treeview'].get_model()
        number = newnumber.strip()
        # check that the edit is necessary

        def is_valid_number(number):
            pattern = re.compile('^\+?\d+$')
            return pattern.match(number) and True or False

        if number != model[path][2] and is_valid_number(number):
            contact = model[path][3]
            if contact.set_number(unicode(number, 'utf8')):
                model[path][2] = number
                self.update_message_contact_info()

    def _setup_trayicon(self, ignoreconf=False):
        """Attaches GUI's trayicon to the systray"""
        showit = config.get('preferences', 'show_icon',
                            CFG_PREFS_DEFAULT_TRAY_ICON)
        if ignoreconf:
            showit = True

        if not self.tray:
            self.tray = get_tray_icon(self._show_hide_window,
                                      self.on_icon_popup_menu)
        self.tray.show()
        if not showit:
            self.tray.hide()

    def _detach_trayicon(self):
        """Detachs GUI's trayicon from the systray"""
        if self.tray:
            self.tray.hide()

    def _show_hide_window(self, *args):
        win = self.view.get_top_widget()
        if len(args) == 1:
            # we ask the for the number of args because we use this
            # function for both egg.tray.TrayIcon and gtk.StatusIcon
            # the formers callback only has one arg
            if win.get_property('visible'):
                win.hide()
            else:
                win.present()
        else:
            eventbox, event = args
            if event.button == 1:  # left click
                if win.get_property('visible'):
                    win.hide()
                else:
                    win.present()
            elif event.button == 3:  # right click
                self.on_icon_popup_menu(None, event.button, event.time)

    def _row_activated_tv(self, treeview, path, col):
        # get selected row
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(self.model, self,
                                        self._get_treeview_contacts())
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_textbuffer_text(message.text)
            ctrl.set_recipient_numbers(message.number)
            if treeview.name in 'drafts_treeview':
                # if the SMS is a draft, delete it after sending it
                ctrl.set_processed_sms(message)
            view.show()

    def __on_treeview_key_press(self, widget, event):
        """Handler for key_press_button in treeviews"""
        from gtk.gdk import keyval_name
#        print keyval_name(event.keyval)

        if keyval_name(event.keyval) in 'F5' and \
                self.model.status >= GUI_MODEM_STATE_ENABLED:
            self.refresh_treeviews()
            self.view.set_message_preview(None)

        if keyval_name(event.keyval) in 'Delete':
            # get current treeview
            num = self.view['main_notebook'].get_current_page() + 1
            treeview_name = TV_DICT[num]
            treeview = self.view[treeview_name]
            # now delete the entries
            self.delete_entries(None, None, treeview)

    def delete_entries(self, menuitem, pathlist, treeview):
        """
        Deletes the entries selected in the treeview

        This entries are deleted in SIM/DB and the treeview
        """
        model, selected = treeview.get_selection().get_selected_rows()
        iters = [model.get_iter(path) for path in selected]

        # filter out the read only items
        if treeview.name == 'contacts_treeview':
            # if we are in contacts_treeview the gobject.TYPE_PYOBJECT that
            # contains the contact is at position 3, if we are on a sms
            # treeview, then it's at position 4
            pos = 3
            objs = []
            _iters = []
            for _iter in iters:
                obj = model.get_value(_iter, pos)
                if obj.is_writable():
                    objs.append(obj)
                    _iters.append(_iter)
            iters = _iters
        else:
            pos = 4
            objs = [model.get_value(_iter, pos) for _iter in iters]

        if not (len(objs) and iters):  # maybe we filtered out everything
            return

        if treeview.name == 'contacts_treeview':
            manager = get_phonebook(self.model.device)
        else:
            manager = get_messages_obj(self.model.device)

        manager.delete_objs(objs)

        # XXX: when multiple but mixed writable / readonly are in the
        # selection for delete invalidate the selection after delete or
        # the selection is wrong
        _inxt = None
        for _iter in iters:
            _inxt = model.iter_next(_iter)
            model.remove(_iter)  # delete from treeview
        if _inxt:
            treeview.get_selection().select_iter(_inxt)  # select next item
        else:
            n_rows = len(model)                          # select last item
            if n_rows:
                _inxt = model[n_rows - 1].iter
                treeview.get_selection().select_iter(_inxt)

        # If we are in a sms treeview update displayed text
        if treeview.get_name() != 'contacts_treeview':
            _obj = self.get_obj_from_selected_row()
            if _obj:
                self.view.set_message_preview(_obj.text)
            else:
                self.view.set_message_preview(None)
        # if we deleted a contact then we need to update all message views
        else:
            self.update_message_contact_info()

    def _send_sms_to_contact(self, menuitem, treeview):
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        numbers = [model.get_value(_iter, 2) for _iter in iters]

        ctrl = NewSmsController(self.model, self,
                                self._get_treeview_contacts())
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

        ctrl.set_entry_text(", ".join(numbers))

    def _edit_external_contacts(self, menuitem, editor=None):
        if editor:
            try:
                Popen(editor)
            except OSError:
                name = editor[0]
                show_warning_dialog(
                    _("Editor not available"),
                    _('Can not start external contact editor "%s"' % name))

    def get_generic_popup_menu(self, pathinfo, treeview):
        """Returns a popup menu for the rest of treeviews"""
        menu = gtk.Menu()  # main menu

        item = gtk.ImageMenuItem(_("_Add to contacts"))
        img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self._use_detail_add_contact)
        item.show()

        menu.append(item)

        if treeview.get_name() == 'inbox_treeview':
            msg = self.get_obj_from_selected_row()
            if msg and is_sim_message(msg):
                item = gtk.ImageMenuItem(_("Migrate to DB"))
                img = gtk.image_new_from_stock(gtk.STOCK_CONVERT,
                                               gtk.ICON_SIZE_MENU)
                item.set_image(img)
                item.connect("activate", self._migrate_sms_to_db)
                item.show()
                menu.append(item)

        if treeview.get_name() != 'drafts_treeview':
            item = gtk.ImageMenuItem(_("Save to draft"))
            img = gtk.image_new_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_MENU)
            item.set_image(img)
            item.connect("activate", self._save_sms_to_draft)
            item.show()
            menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        item = gtk.ImageMenuItem(_("Delete"))
        img = gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self.delete_entries, pathinfo, treeview)
        item.show()
        menu.append(item)

        return menu

    def _migrate_sms_to_db(self, widget):
        """This will save the selected SMS to the drafts tv and the DB"""
        # XXX: this needs reworking to allow multiple selections
        row = self.get_model_iter_obj_from_selected_row()
        if row:
            model, _iter, old = row
            if is_sim_message(old):
                message_mgr = get_messages_obj(self.model.device)

                # Save SMS to DB
                where = TV_DICT_REV['inbox_treeview']
                new = message_mgr.add_message(old, where=where)

                # Remove SMS from the SIM
                message_mgr.delete_objs([old])

                # Update the treeview
                model.update_message(_iter, new, self._get_treeview_contacts())

    def _save_sms_to_draft(self, widget):
        """This will save the selected SMS to the drafts tv and the DB"""
        # XXX: this needs reworking to allow multiple selections
        old = self.get_obj_from_selected_row()
        if old:
            message_mgr = get_messages_obj(self.model.device)
            # Now save SMS to DB
            where = TV_DICT_REV['drafts_treeview']
            new = message_mgr.add_message(old, where=where)
            # Add to the view
            tv = self.view['drafts_treeview']
            tv.get_model().add_message(new)

    def _add_new_contact_cb(self, contact):
        if contact is None:
            return

        name, number, save_in_sim = contact

        if not save_in_sim:
            show_warning_dialog(_("Can not handle DB contacts"),
                                _("Only SIM based contacts supported"))
        else:
            phonebook = get_phonebook(self.model.device)
            phonebook.add_contact(Contact(name, number), sim=save_in_sim)
            self.refresh_treeviews()

    def _use_detail_add_contact(self, widget):
        """Handler for the use detail menu"""
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = AddContactController(self.model, self._add_new_contact_cb,
                                        defnumber=message.number)
            view = AddContactView(ctrl)
            view.set_parent_view(self.view)
            view.show()

    def get_obj_from_selected_row(self):
        """Returns just the object from the selected row"""
        ret = self.get_model_iter_obj_from_selected_row()
        return ret[2] if ret else None

    def get_model_iter_obj_from_selected_row(self):
        """Returns the model, iter and object from the selected row"""
        page = self.view['main_notebook'].get_current_page() + 1

        treeview = self.view[TV_DICT[page]]
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        if not selected or len(selected) > 1:
            return None

        # in the contacts treeview, the contact object is at row[3]
        # while in the rest the SMS object is at row[4]
        row = 3 if page == TV_DICT_REV['contacts_treeview'] else 4
        _iter = model.get_iter(selected[0])
        return model, _iter, model.get_value(_iter, row)
