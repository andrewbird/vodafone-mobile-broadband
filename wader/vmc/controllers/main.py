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

import gtk
from gtkmvc import Controller

import wader.common.consts as consts
from wader.common.signals import SIG_SMS
from wader.common.keyring import KeyringInvalidPassword
from wader.vmc.logger import logger
from wader.vmc.dialogs import (show_profile_window,
                               show_warning_dialog, ActivityProgressBar,
                               show_about_dialog, show_error_dialog,
                               ask_pin_dialog, ask_puk_dialog,
                               ask_puk2_dialog, ask_password_dialog)
#from wader.vmc.keyring_dialogs import NewKeyringDialog, KeyringPasswordDialog
from wader.vmc.utils import bytes_repr, get_error_msg
from wader.vmc.translate import _
from wader.vmc.notify import new_notification
from wader.vmc.consts import GTK_LOCK, GLADE_DIR


class MainController(Controller):
    """
    I am the controller for the main window
    """
    def __init__(self, model):
        super(MainController, self).__init__(model)
        model.ctrl = self
        self.cid = None

        self.signal_matches = []

        # activity progress bar
        self.apb = None
        self.icon = None

    def register_view(self, view):
        super(MainController, self).register_view(view)
        self._setup_icon()
        self.view.set_initialising(True)
        self.connect_to_signals()

    def _setup_icon(self):
        filename = os.path.join(GLADE_DIR, 'wader.png')
        self.icon = gtk.status_icon_new_from_file(filename)

    def connect_to_signals(self):
        self.view['main_window'].connect('delete_event', self.close_application)
        self.cid = self.view['connect_button'].connect('toggled',
                                            self.on_connect_button_toggled)
        self.icon.connect('activate', self.on_icon_activated)
        self.icon.connect('popup-menu', self.on_icon_popup_menu)

    def close_application(self, *args):
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
            self.model.quit(self._close_application_cb)

    def ask_for_new_profile(self):
        model = self.model.preferences_model
        if self.model.device:
            self.model.get_imsi(lambda imsi:
                show_profile_window(model, imsi=imsi))
        else:
            show_profile_window(model)

    def ask_for_pin(self):
        pin = ask_pin_dialog(self.view)
        if pin:
            self.model.send_pin(pin, self.model.enable_device)

    def _close_application_cb(self, *args):
        try:
            os.unlink(GTK_LOCK)
        except OSError:
            pass

        self.view.stop_throbber()
        gtk.main_quit()

    def _setup_connection_signals(self):
        self.model.bus.add_signal_receiver(
                                self._on_disconnect_cb,
                                "Disconnected",
                                dbus_interface=consts.WADER_DIALUP_INTFACE)
    # properties
    def property_rssi_value_change(self, model, old, new):
        self.view.rssi_changed(new)

    def on_net_password_required(self, opath, tag):
        password = ask_password_dialog(self.view)

        if password:
            from wader.vmc.profiles import manager
            profile = manager.get_profile_by_object_path(opath)
            # XXX: do not hardcode NM_PASSWD
            ret = {tag : {consts.NM_PASSWD :password}}
            profile.set_secrets(tag, ret)

    def on_keyring_password_required(self, opath):
        from wader.vmc.profiles import manager
        profile = manager.get_profile_by_object_path(opath)
        password = None

#        if profile.secrets.manager.is_new:
#            dialog = NewKeyringDialog(self.view.get_top_widget())
#            response = dialog.run()
#        else:
#            # profile.secrets.manager.is_open == True
#            dialog = KeyringPasswordDialog(self.view.get_top_widget())
#            response = dialog.run()
#
#        if response == gtk.RESPONSE_OK:
#            password = dialog.password_entry.get_text()
#
#        dialog.destroy()

        if password is not None:
            try:
                profile.secrets.manager.open(password)
            except KeyringInvalidPassword:
                title = _("Invalid password")
                details = _("The supplied password is incorrect")
                show_error_dialog(title, details)
                # call ourselves again
                self.on_keyring_password_required(opath)

    def property_operator_value_change(self, model, old, new):
        if new == _('Unknown Network'):
            logger.error("Unknown operator received, using profile name...")
            profiles_model = self.model.preferences_model.profiles_model
            try:
                profile = profiles_model.get_active_profile()
            except RuntimeError:
                self.view.operator_changed(new)
            else:
                self.view.operator_changed(profile.name)
        else:
            self.view.operator_changed(new)

    def property_tech_value_change(self, model, old, new):
        self.view.tech_changed(new)

    def property_device_value_change(self, model, old, new):
        if self.model.device is not None:
            sm = self.model.device.connect_to_signal("DeviceEnabled",
                                            self.on_device_enabled_cb)
            self.signal_matches.append(sm)
            # connect to SIG_SMS and display SMS
            sm = self.model.device.connect_to_signal(SIG_SMS,
                                                self.on_sms_received_cb)
            self.signal_matches.append(sm)
        else:
            while self.signal_matches:
                sm = self.signal_matches.pop()
                sm.remove()

    def property_profile_value_change(self, model, old, new):
        logger.info("A profile has been set for current model %s" % new)

    def property_status_value_change(self, model, old, new):
        self.view.set_status(new)
        if new == _('Initialising'):
            self.view.set_initialising(True)
        elif new == _('No device'):
            self.view.set_disconnected(device_present=False)
        elif new in [_('Registered'), _('Roaming')]:
            self.view.set_initialising(False)

    def property_sim_error_value_change(self, model, old, details):
        title = _('Unknown error while initting device')
        show_error_dialog(title, details)

    def property_net_error_value_change(self, model, old, new):
        title = _("Error while registering to home network")
        show_error_dialog(title, new)

    def property_pin_required_value_change(self, model, old, new):
        if new:
            self.ask_for_pin()

    def property_puk_required_value_change(self, model, old, new):
        if new:
            pukinfo = ask_puk_dialog(parent=self.view)
            if pukinfo:
                puk, pin = pukinfo
                model.send_puk(puk, pin, model.enable_device)

    def property_puk2_required_value_change(self, model, old, new):
        if new:
            pukinfo = ask_puk2_dialog(parent=self.view)
            if pukinfo:
                puk2, pin = pukinfo
                model.send_puk(puk2, pin, model.enable_device)

    def property_rx_bytes_value_change(self, model, old, new):
        if old != new:
            self.view['rx_bytes_label'].set_text(bytes_repr(new))
            logger.info("Bytes rx: %d", new)

    def property_tx_bytes_value_change(self, model, old, new):
        if old != new:
            self.view['tx_bytes_label'].set_text(bytes_repr(new))
            logger.info("Bytes tx: %d", new)

    def property_total_bytes_value_change(self, model, old, new):
        if old != new and new != '':
            self.view['total_bytes_label'].set_text(bytes_repr(new))
            logger.info("Total bytes: %d", new)

    def property_transfer_limit_exceeded_value_change(self, model, old, new):
        if not old and new:
            show_warning_dialog(_("Transfer limit exceeded"),
                                _("You have exceeded your transfer limit"))

    # callbacks
    def on_sms_received_cb(self, index):
        """
        Executed whenever a new SMS is received

        Will read and show the SMS to the user
        """
        def process_sms_eb(error):
            title = _("Error reading SMS %d") % index
            show_error_dialog(title, get_error_msg(error))

         # read the SMS and show it to the user
        self.model.device.Get(index,
                              dbus_interface=consts.SMS_INTFACE,
                              reply_handler=self.show_sms_notification,
                              error_handler=process_sms_eb)

    def show_sms_notification(self, sms):
        """
        Shows a notification when a SMS is received

        It will take care of looking up the number in the phonebook
        to show the name if its a known contact instead of its number
        """
        def find_by_number_cb(contacts):
            if not contacts:
                title = _("SMS received from %s") % sms['number']
            else:
                assert len(contacts) == 1, "More than one match for a number!"
                title = _("SMS received from %s") % contacts[0][1]

            n = new_notification(self.icon, title, sms['text'],
                                 stock=gtk.STOCK_INFO)
            n.show()

        self.model.device.FindByNumber(sms['number'],
                                       dbus_interface=consts.CTS_INTFACE,
                                       reply_handler=find_by_number_cb,
                                       error_handler=logger.error)

    def on_device_enabled_cb(self, udi):
        self.view['sms_menuitem'].set_sensitive(True)
        self.view['preferences_menu_item'].set_sensitive(True)

    def _on_connect_cb(self, dev_path):
        self.view.set_connected()
        self.model.start_stats_tracking()
        if self.apb:
            self.apb.close()
            self.apb = None

        self.model.dial_path = dev_path

    def _on_connect_eb(self, e):
        logger.error(e)
        self.view.set_disconnected()
        if self.apb:
            self.apb.close()
            self.apb = None

        title = _('Failed connection attempt')
        show_error_dialog(title, get_error_msg(e))

    def _on_disconnect_cb(self, *args):
        logger.info("Disconnected")
        self.model.stop_stats_tracking()
        self.view.set_disconnected()

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

    def _on_disconnect_eb(self, args):
        logger.error(args)
        self.model.stop_stats_tracking()
        if self.apb:
            self.apb.close()
            self.apb = None

    def on_icon_activated(self, icon):
        window = self.view.get_top_widget()
        if window.get_property('visible'):
            window.hide()
        else:
            window.present()

    def get_trayicon_menu(self):
        menu = gtk.Menu()

        item = gtk.ImageMenuItem(_("About"))
        img = gtk.image_new_from_stock(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self.on_about_menuitem_activate)
        item.show()
        menu.append(item)

        item = gtk.ImageMenuItem(_("Preferences"))
        item.set_image(gtk.image_new_from_stock(gtk.STOCK_PREFERENCES,
                                                gtk.ICON_SIZE_MENU))
        item.connect("activate", self.on_preferences_menu_item_activate)
        if self.model.device is None:
            item.set_sensitive(False)
        else:
            item.set_sensitive(True)
        item.show()
        menu.append(item)

        item = gtk.ImageMenuItem(_("Quit"))
        img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self.close_application)
        item.show()
        menu.append(item)

        return menu

    def on_icon_popup_menu(self, icon, button, activate_time):
        menu = self.get_trayicon_menu()
        menu.popup(None, None, None, button, activate_time)

    def on_connect_button_toggled(self, widget):
        dialmanager = self.model.get_dialer_manager()

        if widget.get_active():
            # user wants to connect
            if not self.model.device:
                widget.set_active(False)
                show_warning_dialog(
                    _("No device found"),
                    _("No device has been found. Insert one and try again."))
                return


            profiles_model = self.model.preferences_model.profiles_model
            if not profiles_model.has_active_profile():
                widget.set_active(False)
                show_warning_dialog(
                    _("Profile needed"),
                    _("You need to create a profile for connecting."))
                self.ask_for_new_profile()
                return

            active_profile = profiles_model.get_active_profile()

            dialmanager.ActivateConnection(active_profile.profile_path,
                                           self.model.device_path,
                                           timeout=40,
                                           reply_handler=self._on_connect_cb,
                                           error_handler=self._on_connect_eb)

            self._setup_connection_signals()

            def cancel_cb():
                self.view.set_disconnected()
                self.model.dial_path = None

            self.apb = ActivityProgressBar(_("Connecting"), self)
            self.apb.set_cancel_cb(dialmanager.StopConnection,
                                   self.model.device_path,
                                   reply_handler=cancel_cb,
                                   error_handler=logger.error)

            self.apb.init()
            logger.info("Connecting...")
        else:
            # user wants to disconnect
            if not self.model.dial_path:
                return

            self.apb = ActivityProgressBar(_("Disconnecting"), self,
                                           disable_cancel=True)
            dialmanager.DeactivateConnection(self.model.dial_path,
                                        reply_handler=self._on_disconnect_cb,
                                        error_handler=self._on_disconnect_eb)

            self.apb.init()
            self.model.dial_path = None

    def on_preferences_menu_item_activate(self, widget):
        from wader.vmc.views.preferences import PreferencesView
        from wader.vmc.controllers.preferences import PreferencesController

        controller = PreferencesController(self.model.preferences_model,
                                           lambda: self.model.device)
        view = PreferencesView(controller)

        profiles_model = self.model.preferences_model.profiles_model
        if not profiles_model.has_active_profile():
            show_warning_dialog(
                _("Profile needed"),
                _("You need to create a profile to save preferences"))
            self.ask_for_new_profile()
            return
        view.show()

    def on_sms_menuitem_activate(self, widget):
        from wader.vmc.models.sms import SMSContactsModel
        from wader.vmc.controllers.sms import SMSContactsController
        from wader.vmc.views.sms import SMSContactsView

        model = SMSContactsModel(self.model.device)
        ctrl = SMSContactsController(model, self)
        view = SMSContactsView(ctrl, parent_view=self.view)

        view.show()

    def on_log_menuitem_activate(self, widget):
        from wader.vmc.controllers.log import LogController
        from wader.vmc.views.log import LogView
        from wader.vmc.models.log import LogModel

        model = LogModel()
        ctrl = LogController(model)
        view = LogView(ctrl)

        view.show()

    def on_about_menuitem_activate(self, widget):
        dlg = show_about_dialog()
        dlg.run()
        dlg.destroy()

    def on_exit_menu_item_activate(self, widget):
        self.close_application()

