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
from subprocess import Popen

from wader.vmc.controllers.base import WidgetController, TV_DICT, TV_DICT_REV
from wader.vmc.controllers.contacts import (AddContactController,
                                          SearchContactController)
from wader.vmc.views.contacts import AddContactView, SearchContactView

import wader.common.consts as consts
from wader.common.signals import SIG_SMS_COMP
from wader.common.keyring import KeyringInvalidPassword
from wader.vmc.config import config
from wader.vmc.logger import logger
from wader.vmc.dialogs import (show_profile_window,
                               show_warning_dialog, ActivityProgressBar,
                               show_about_dialog, show_error_dialog,
                               ask_password_dialog,
                               save_csv_file, open_import_csv_dialog)
#from wader.vmc.keyring_dialogs import NewKeyringDialog, KeyringPasswordDialog
from wader.vmc.utils import bytes_repr, get_error_msg, UNIT_MB, units_to_bits
from wader.vmc.translate import _
from wader.vmc.notify import new_notification
from wader.vmc.consts import GTK_LOCK, GLADE_DIR, GUIDE_DIR, IMAGES_DIR, APP_URL

from wader.vmc.phonebook import (get_phonebook,
                                all_same_type, all_contacts_writable)
from wader.vmc.csvutils import CSVUnicodeWriter, CSVContactsReader
from wader.vmc.messages import get_messages_obj

from wader.vmc.models.diagnostics import DiagnosticsModel
from wader.vmc.views.diagnostics import DiagnosticsView
from wader.vmc.controllers.diagnostics import DiagnosticsController

from wader.vmc.models.sms import NewSmsModel
from wader.vmc.views.sms import NewSmsView, ForwardSmsView
from wader.vmc.controllers.sms import NewSmsController, ForwardSmsController

from wader.vmc.views.pin import (PinModifyView, PinEnableView,
                                 AskPUKView, AskPINView)
from wader.vmc.controllers.pin import (PinModifyController, PinEnableController,
                                       AskPUKController, AskPINController)

from wader.vmc.models.preferences import PreferencesModel
from wader.vmc.controllers.preferences import PreferencesController
from wader.vmc.views.preferences import PreferencesView

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
        self.start()

    def _setup_icon(self):
        filename = os.path.join(GLADE_DIR, 'VF_logo_medium.png')
        self.icon = gtk.status_icon_new_from_file(filename)

    def start(self):
        self.view.set_disconnected()

        # we're on SMS mode
        self.on_sms_button_toggled(get_fake_toggle_button())

        #self.usage_updater = TimerService(5, self.update_usage_view)
        #self.usage_updater.startService()

    def connect_to_signals(self):
        self._setup_menubar_hacks()

        self.view['main_window'].connect('delete_event', self.close_application)
# VMC        self.view.get_top_widget().connect("delete_event", self._quit_or_minimize)

        self.cid = self.view['connect_button'].connect('toggled',
                                            self.on_connect_button_toggled)

#        self.icon.connect('activate', self.on_icon_activated)

#        if config.getboolean('preferences', 'show_icon'):
        if True:
            self.icon.connect('popup-menu', self.on_icon_popup_menu)

        for treeview_name in list(set(TV_DICT.values())):
            treeview = self.view[treeview_name]
            treeview.connect('key_press_event', self.__on_treeview_key_press)
            if treeview.name != 'contacts_treeview':
                treeview.connect('row-activated', self._row_activated_tv)

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
        model = self.model.profiles_model
        if self.model.device:
            self.model.get_imsi(lambda imsi:
                show_profile_window(model, imsi=imsi))
        else:
            show_profile_window(model)

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
            profiles_model = self.model.profiles_model
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
            # connect to SIG_SMS_COMP and display SMS
            sm = self.model.device.connect_to_signal(SIG_SMS_COMP,
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
            self.ask_for_puk()

    def property_puk2_required_value_change(self, model, old, new):
        if new:
            self.ask_for_puk2()

    def property_rx_bytes_value_change(self, model, old, new):
        pass
#        if old != new:
#            self.view['rx_bytes_label'].set_text(bytes_repr(new))
#            logger.info("Bytes rx: %d", new)

    def property_tx_bytes_value_change(self, model, old, new):
        pass
#        if old != new:
#            self.view['tx_bytes_label'].set_text(bytes_repr(new))
#            logger.info("Bytes tx: %d", new)

    def bits_to_human(self, bits):
        f = float(bits)
        for m in ['b/s', 'kb/s', 'mb/s', 'gb/s']:
            if f < 1000:
                return "%3.2f %s" % (f, m)
            f /= 1000
        return _("N/A")

    def property_rx_rate_value_change(self, model, old, new):
        if old != new:
            self.view['download_statusbar'].push(1,
                                                 self.bits_to_human(new*8))
            logger.info("Rate rx: %d", new)

    def property_tx_rate_value_change(self, model, old, new):
        if old != new:
            self.view['upload_statusbar'].push(1,
                                                 self.bits_to_human(new*8))
            logger.info("Rate tx: %d", new)

    def property_total_bytes_value_change(self, model, old, new):
        pass
#        if old != new and new != '':
#            self.view['total_bytes_label'].set_text(bytes_repr(new))
#            logger.info("Total bytes: %d", new)

    def property_transfer_limit_exceeded_value_change(self, model, old, new):
        if not old and new:
            show_warning_dialog(_("Transfer limit exceeded"),
                                _("You have exceeded your transfer limit"))

    # callbacks

    def on_sms_menu_item_activate(self, widget):
        self.on_sms_button_toggled(get_fake_toggle_button())

    def on_usage_menu_item_activate(self, widget):
        self.on_usage_button_clicked(get_fake_toggle_button())

    def on_support_menu_item_activate(self, widget):
        self.on_support_button_toggled(get_fake_toggle_button())

    def on_sms_button_toggled(self, widget):
        if widget.get_active():
            self.view['usage_frame'].hide()
            self.view['usage_tool_button'].set_active(False)
            self.view['support_tool_button'].set_active(False)
            self.view['support_notebook'].hide()
            self.view['sms_frame_alignment'].show()
            self.view['sms_tool_button'].set_active(True)

    def on_usage_button_clicked(self, widget):
        if widget.get_active():
            self.view['sms_frame_alignment'].hide()
            self.view['sms_tool_button'].set_active(False)
            self.view['support_notebook'].hide()
            self.view['support_tool_button'].set_active(False)
            self.view['usage_frame'].show()
            self.view['usage_tool_button'].set_active(True)

    def on_support_button_toggled(self, widget):
        if widget.get_active():
            self.view['usage_frame'].hide()
            self.view['usage_tool_button'].set_active(False)
            self.view['sms_frame_alignment'].hide()
            self.view['sms_tool_button'].set_active(False)
            self.view['support_notebook'].show()
            self.view['support_tool_button'].set_active(True)

    def on_internet_button_clicked(self, widget):
#        if self._check_if_connected():
        if True:
            binary = config.get('preferences', 'browser')
            if binary:
                Popen([ binary, APP_URL ])

    def on_mail_button_clicked(self, widget):
#        if self._check_if_connected():
        if True:
            binary = config.get('preferences', 'mail')
            if binary:
                Popen([ binary, 'REPLACE@ME.COM' ])

    def on_sms_received_cb(self, index, complete):
        """
        Executed whenever a complete SMS is received, may be single or
        fully reassembled multipart message

        Will read, populate the treeview and notify the user
        """
        
        print "main: controller - on_sms_received_cd"
        
        messages_obj = get_messages_obj(self.model.device)
        sms = messages_obj.get_message(index)
        print "main: controller - on_sms_received_cd: message is.... "  + repr(sms)
        print "main: controller - on_sms_received_cd: sms number is..." + repr(sms.number)
        
        # It will take care of looking up the number in the phonebook
        # to show the name if it's a known contact instead of its number
        contact = self._find_contact_by_number(sms.number)
        print "main: controller - on_sms_received_cd: contact is..." + repr(contact)
        
        if contact:
            contacts_value = contact.get_name()
            print "main: controller - on_sms_received_cd: contact name is..." + repr(contact.get_name())
        else:
            contacts_value = sms.number

        # Populate treeview
        treeview = self.view['inbox_treeview']
        #treeview.get_model().add_message(sms,[contact])
        treeview.get_model().add_message(sms,  contacts_value)

        # Send notification
        title = _("SMS received from %s") % id

        n = new_notification(self.icon, title, sms.text,
                             stock=gtk.STOCK_INFO)
        n.show()

    def on_is_pin_enabled_cb(self, enabled):
        self.view['change_pin1'].set_sensitive(enabled)

        checkmenuitem = self.view['request_pin1']
        if checkmenuitem.get_active() != enabled:
            checkmenuitem.set_active(enabled)

    def on_device_enabled_cb(self, udi):
        self._fill_treeviews()
        self.model.pin_is_enabled(self.on_is_pin_enabled_cb,
                                  lambda *args: True)
#        self.view['preferences_menu_item'].set_sensitive(True)

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

        connect_button = self.view['connect_button']

        def _disconnect_from_inet(widget):
            connect_button.set_active(False)

        def _connect_to_inet(widget):
            connect_button.set_active(True)

        menu = gtk.Menu()

#        if self.model.is_connected():
        if self.model.dial_path:
            item = gtk.ImageMenuItem(_("Disconnect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(IMAGES_DIR, 'stop16x16.png'))
            item.connect("activate", _disconnect_from_inet)
        else:
            item = gtk.ImageMenuItem(_("Connect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(IMAGES_DIR, 'connect-16x16.png'))
            item.connect("activate", _connect_to_inet)

        item.set_image(img)
        if self.model.device is None:
            item.set_sensitive(False)
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
        if self.model.device is None:
            item.set_sensitive(False)
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

    def get_contacts_popup_menu(self, pathinfo, treeview):
        """Returns a popup menu for the contacts treeview"""
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        contacts = [model.get_value(_iter, 3) for _iter in iters]

        menu = gtk.Menu()

        item = gtk.ImageMenuItem(_("_Send SMS"))
        item.connect("activate", self._send_sms_to_contact, treeview)
        img = gtk.Image()
        img.set_from_file(os.path.join(IMAGES_DIR, 'sms16x16.png'))
        item.set_image(img)
        item.show()
        menu.append(item)

        # Figure out whether we should show delete, edit, or no extra menu items
        if all_contacts_writable(contacts):
            item = gtk.ImageMenuItem(_("_Delete"))
            img = gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU)
            item.set_image(img)
            item.connect("activate", self.delete_entries, pathinfo, treeview)
            item.show()
            menu.append(item)

        elif all_same_type(contacts):
            editor = contacts[0].external_editor()
            if editor:
                item = gtk.ImageMenuItem(_("Edit"))
                img = gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU)
                item.set_image(img)

                item.connect("activate", self._edit_external_contacts, editor)

                item.show()
                menu.append(item)

        return menu

    def on_icon_popup_menu(self, icon, button, activate_time):
        menu = self.get_trayicon_menu()
        menu.popup(None, None, None, button, activate_time)

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
                contacts = list(reader)
                phonebook.add_contacts(contacts, True)
                # Flip the notebook to contacts
                self.view['main_notebook'].set_current_page(3)
                # Refresh contacts display
                self._empty_treeviews(['contacts_treeview'])
                self._fill_contacts()

    def on_export_contacts1_activate(self, widget):
        filepath = save_csv_file()
        if filepath:
            writer = CSVUnicodeWriter(open(filepath, 'w'))
            phonebook = get_phonebook(self.model.device)
            # Now we support different backends we need to be more
            # selective about what we write out?
            contacts = phonebook.get_contacts()
            writer.write_rows([c.to_csv() for c in contacts if c.is_writable()])

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

            profiles_model = self.model.profiles_model
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
        print "on_preferences_menu_item_activate -NEW menu"

        model = PreferencesModel(self.model.device)
        ctrl = PreferencesController(model, self)
        view = PreferencesView(ctrl)
        view.show()

#        from wader.vmc.views.preferences import PreferencesView
#        from wader.vmc.controllers.preferences import PreferencesController
#
#        controller = PreferencesController(self.model.preferences_model,
#                                           lambda: self.model.device)
#        view = PreferencesView(controller)
#
#        profiles_model = self.model.preferences_model.profiles_model
#        if not profiles_model.has_active_profile():
#            show_warning_dialog(
#                _("Profile needed"),
#                _("You need to create a profile to save preferences"))
#            self.ask_for_new_profile()
#            return
#        view.show()

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

    def on_exit_menu_item_activate(self, widget):
        self.close_application()

########################### copied in from application.py ##############################

    def on_new_contact_menu_item_activate(self, widget):
        self.view['main_notebook'].set_current_page(3) # contacts_tv
        ctrl = AddContactController(self.model, self)
        view = AddContactView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_search_contact_menu_item_activate(self, widget):
        self.view['main_notebook'].set_current_page(3) # contacts_tv
        ctrl = SearchContactController(self.model, self)
        view = SearchContactView(ctrl)
        view.set_parent_view(self.view)
        view.run()

    def on_new_sms_activate(self, widget):
        model = NewSmsModel(self.model.device)
        ctrl = NewSmsController(model, self)
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_quit_menu_item_activate(self, widget):
        #exit_without_conf = config.getboolean('preferences',
        #                                    'exit_without_confirmation')
        exit_without_conf = True
        if exit_without_conf:
            self.close_application()
            return

        #resp, checked = dialogs.open_dialog_question_checkbox_cancel_ok(
        #            self.view,
        #            _("Quit %s") % APP_LONG_NAME,
        #            _("Are you sure you want to exit?"))

        #config.setboolean('preferences', 'exit_without_confirmation', checked)
        #config.write()
#
#        if resp:
#            self.quit_application()

    def on_change_pin1_activate(self, widget):
        ctrl = PinModifyController(self.model)
        view = PinModifyView(ctrl)
        view.show()

    def on_request_pin1_activate(self, checkmenuitem):
        def is_pin_enabled_cb(curval):
            reqval = checkmenuitem.get_active()
            print "request = %d, current = %d" % (reqval, curval)
            if reqval == curval:
                return
            else:
                def pin_enable_cb(enable):
                    self.view['change_pin1'].set_sensitive(enable)

                def pin_enable_eb(enable):
                    self.view['change_pin1'].set_sensitive(not enable)
                    # Toggle checkmenuitem back, note this will cause it to
                    # activate again, but our is_pin_enabled check will
                    # prevent a loop
                    self.view['request_pin1'].set_active(not enable)

                ctrl = PinEnableController(self.model,
                           reqval,
                           pin_enable_cb,
                           pin_enable_eb)
                view = PinEnableView(ctrl)
                view.show()

        def is_pin_enabled_eb(e):
            pass

        self.model.pin_is_enabled(is_pin_enabled_cb,
                                  is_pin_enabled_eb)

    def on_new_profile_menuitem_activate(self, widget):
        self.ask_for_new_profile()
        # XXX: shouldn't we make it the active one

    def _build_profiles_menu(self):
        def load_profile(widget, profile):
            profiles_model = self.model.profiles_model
            profiles_model.set_default_profile(profile.uuid)

            # refresh menu
            self.on_tools_menu_item_activate(get_fake_toggle_button())

        def edit_profile(widget, profile):
            show_profile_window(self.model.profiles_model,
                                profile=profile)
            # XXX: check out whether editing a profile should make it active
            #      currently it doesn't
            # self.on_tools_menu_item_activate(get_fake_toggle_button())

        def delete_profile(widget, profile):
            profiles_model = self.model.profiles_model
            profiles_model.remove_profile(profile)

            # refresh menu
            self.on_tools_menu_item_activate(get_fake_toggle_button())

        def is_active_profile(profile):
            profiles_model = self.model.profiles_model

            if not profiles_model.has_active_profile():
                return False
            return profile.uuid == profiles_model.get_active_profile().uuid

        profiles = self.model.profiles_model.get_profiles()

        menu1 = gtk.Menu()
        for profile in profiles.values():
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", load_profile, profile)
            item.show()
            if is_active_profile(profile):
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
            if is_active_profile(profile):
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
        model = DiagnosticsModel(self.model.device)
        ctrl = DiagnosticsController(model, self)
        view = DiagnosticsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_help_topics_menu_item_activate(self, widget):
        binary = config.get('preferences', 'browser')
        if binary:
            index_path = os.path.join(GUIDE_DIR, 'index.html')
            Popen([ binary, index_path ])

    def on_about_menu_item_activate(self, widget):
        print "on_help_topics_about_menu_active"
        about = show_about_dialog()
        about.run()
        about.destroy()

######

    def _setup_menubar_hacks(self):
        def fake_delete_event(widget, event):
            if event.button == 1:
                self.on_delete_menu_item_activate(widget)
                return True

            return False

        def fake_forward_event(widget, event):
            if event.button == 1:
                self.on_forward_sms_menu_item_activate(widget)
                return True

            return False

        items = ['contact_delete_menu_item', 'sms_delete_menu_item',
                 'forward_sms_menu_item']

        for item in items:
            self.view[item].set_events(gtk.gdk.BUTTON_PRESS_MASK)

        # contacts_menubar delete item and messages_menubar delete item
        for item in ['contact_delete_menu_item', 'sms_delete_menu_item']:
            self.view[item].connect("button_press_event", fake_delete_event)

        # messages_menubar forward item
        self.view['forward_sms_menu_item'].connect("button_press_event",
                                                   fake_forward_event)
    def _empty_treeviews(self, treeviews):
        for treeview_name in treeviews:
            model = self.view[treeview_name].get_model()
            if model:
                model.clear()

    def _fill_contacts(self, ignored=None):
        """Fills the contacts treeview with contacts"""
        phonebook = get_phonebook(device=self.model.device)

        treeview = self.view['contacts_treeview']
        contacts = phonebook.get_contacts()
        model = treeview.get_model()
        model.add_contacts(contacts)
        return contacts

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

    def _fill_messages(self, contacts=None):
        """
        Fills the messages treeview with SIM & DB SMS

        We're receiving the contacts list produced by _fill_contacts because
        otherwise, adding dozens of SMS to the treeview would be very
        inefficient, as we would have to lookup the sender number of every
        SMS to find out whether is a known contact or not. The solution is
        to cache the previous result and pass the contacts list to the
        L{wader.vmc.models.sms.SMSStoreModel}
        """
        messages_obj = get_messages_obj(self.model.device)
        sms_list = messages_obj.get_messages()

        for sms in sms_list:
            if sms.where == 1:
                treeview = self.view['inbox_treeview']
                treeview.get_model().add_message(sms, contacts)

#            for sms in sms_list:
#                active_tv = TV_DICT[sms.where]         # get treeview name
#                treeview = self.view[active_tv]        # get treeview object
#                treeview.get_model().add_message(sms, contacts) # append to tv

    def _fill_treeviews(self):
        """
        Fills the treeviews with SMS and contacts
        """
        contacts = self._fill_contacts()
        self._fill_messages(contacts)

#########

    def _update_usage_panel(self, name, offset):
        m = self.model
        w = lambda label : label % name

        values = ['month', 'transferred_gprs', 'transferred_3g',
                  'transferred_total']
        for value_name in values:
            widget = (value_name + '_%s_label') % name
            value = getattr(m, 'get_%s' % value_name)(offset)
            self.view.set_usage_value(widget, value)

        self.view.set_usage_bar_value('%s-gprs' % name,
                                            m.get_transferred_gprs(offset))
        self.view.set_usage_bar_value('%s-3g' % name,
                                            m.get_transferred_3g(offset))

    def _update_usage_session(self):
        set_value = self.view.set_usage_value
        m = self.model
        set_value('transferred_3g_session_label', m.get_session_3g())
        set_value('transferred_gprs_session_label', m.get_session_gprs())
        set_value('transferred_total_session_label', m.get_session_total())

    def usage_notifier(self):
        #limit = int(config.get('preferences', 'traffic_threshold'))
        #notification = config.getboolean('preferences', 'usage_notification')
        limit = 10
        notification = 0
        limit = units_to_bits(limit, UNIT_MB)
        if (notification and limit > 0
                and self.model.get_transferred_total(0) > limit
                and not self.user_limit_notified):
            self.user_limit_notified = True
            message = _("User Limit")
            details = _("You have reached your limit of maximum usage")
            show_warning_dialog(message, details)

            #show_normal_notification(self.tray, message, details, expires=False)
            n = new_notification(self.icon, message, details, stock=gtk.STOCK_INFO)
            n.show()
        elif self.model.get_transferred_total(0) < limit :
            self.user_limit_notified = False

    def update_usage_view(self):
        self.model.clean_usage_cache()
        self._update_usage_panel('current', 0)
        self._update_usage_panel('last', -1)
        self._update_usage_session()
        self.view.update_bars_user_limit()
        self.usage_notifier()

    def on_reply_sms_no_quoting_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            model = NewSmsModel(self.model.device)
            ctrl = ForwardSmsController(model, self)
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.number)
            ctrl.set_textbuffer_focus()
            view.show()

    def on_reply_sms_quoting_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            model = NewSmsModel(self.model.device)
            ctrl = ForwardSmsController(model, self)
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.number)
            ctrl.set_textbuffer_text(message.text)
            ctrl.set_textbuffer_focus()
            view.show()

    def on_forward_sms_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            model = NewSmsModel(self.model.device)
            ctrl = ForwardSmsController(model, self)
            view = ForwardSmsView(ctrl)
            ctrl.numbers_entry.grab_focus()
            ctrl.set_textbuffer_text(message.text)
            view.set_parent_view(self.view)
            view.show()

#    XXX: check out if this is needed
#    def on_add_contact_menu_item_activate(self, widget):
#        self.on_new_contact_menu_item_activate(None)

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
                return True # selection is not lost

    def on_cursor_changed_treeview_event(self, treeview):
        col = treeview.get_cursor()[0]
        model = treeview.get_model()
        text = model[col][1]
        _buffer = self.view['smsbody_textview'].get_buffer()
        _buffer.set_text(text)
        self.view['sms_message_pane'].show()

    def on_main_notebook_switch_page(self, notebook, ptr, pagenum):
        """
        Callback for whenever VMC's main notebook is switched

        Basically takes care of showing and hiding the appropiate menubars
        depending on the page the user is viewing
        """
        if int(pagenum) == 3:
            self.view['contacts_menubar'].show()
            self.view['sms_menubar'].hide()
        else:
            self.view['contacts_menubar'].hide()
            self.view['sms_menubar'].show()

        self.view['sms_message_pane'].hide()

    #----------------------------------------------#
    # MISC FUNCTIONALITY                           #
    #----------------------------------------------#

    def _name_contact_cell_edited(self, widget, path, newname):
        """Handler for the cell-edited signal of the name column"""
        # first check that the edit is necessary
        model = self.view['contacts_treeview'].get_model()
        if newname != model[path][1] and newname != '':
            contact = model[path][3]
            if contact.set_name(unicode(newname, 'utf8')):
                model[path][1] = newname

    def _number_contact_cell_edited(self, widget, path, newnumber):
        """Handler for the cell-edited signal of the number column"""
        model = self.view['contacts_treeview'].get_model()
        number = newnumber.strip()
        # check that the edit is necessary

        def is_valid_number(number):
            import re
            pattern = re.compile('^\+?\d+$')
            return pattern.match(number) and True or False

        if number != model[path][2] and is_valid_number(number):
            contact = model[path][3]
            if contact.set_number(unicode(number, 'utf8')):
                model[path][2] = number

    def _row_activated_tv(self, treeview, path, col):
        # get selected row
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(Model(), self)
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

        if keyval_name(event.keyval) in 'F5':
            # get current treeview
            num = self.view['main_notebook'].get_current_page() + 1
            treeview_name = TV_DICT[num]
            # now do the refresh
            if treeview_name in 'contacts_treeview':
                self._empty_treeviews(['contacts_treeview'])
                self._fill_contacts()

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

        # if we are in contacts_treeview the gobject.TYPE_PYOBJECT that
        # contains the contact is at position 3, if we are on a sms treeview,
        # then it's at position 4
        if (treeview.name == 'contacts_treeview'): # filter out the read only items
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

        if not (len(objs) and iters): # maybe we filtered out everything
            return

        if treeview.name == 'contacts_treeview':
            manager = get_phonebook(self.model.device)
        else:
            manager = get_messages_obj(self.model.device)

        manager.delete_objs(objs)

# XXX: when multiple but mixed writable / readonly are in the selection for delete
#      invalidate the selection after delete or the selection is wrong
        _inxt = None
        for _iter in iters:
            _inxt=model.iter_next(_iter)
            model.remove(_iter) # delete from treeview
        if _inxt:
            treeview.get_selection().select_iter(_inxt) # select next item
        else:
            n_rows = len(model)                         # select last item
            if n_rows > 0:
                _inxt = model[n_rows-1].iter
                treeview.get_selection().select_iter(_inxt)

        # If we are in a sms treeview update displayed text
        if treeview.get_name() != 'contacts_treeview':
            _obj = self.get_obj_from_selected_row()
            if _obj:
                self.view['smsbody_textview'].get_buffer().set_text(_obj.text)
                self.view['sms_message_pane'].show()
            else:
                self.view['smsbody_textview'].get_buffer().set_text('')
                self.view['sms_message_pane'].hide()

    def _send_sms_to_contact(self, menuitem, treeview):
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        numbers = [model.get_value(_iter, 2) for _iter in iters]

        model = NewSmsModel(self.model.device)
        ctrl = NewSmsController(model, self)
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

        ctrl.set_entry_text(", ".join(numbers))

    def _edit_external_contacts(self, menuitem, editor=None):
        if editor:
            cmd = editor[0]
            args = len(editor) > 1 and editor[1:] or []
            getProcessOutput(cmd, args, os.environ)

    def get_generic_popup_menu(self, pathinfo, treeview):
        """Returns a popup menu for the rest of treeviews"""
        menu = gtk.Menu() # main menu

        item = gtk.ImageMenuItem(_("_Add to contacts"))
        img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        item.set_image(img)
        item.connect("activate", self._use_detail_add_contact)
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

    def _save_sms_to_draft(self, widget):
        """This will save the selected SMS to the drafts tv and the DB"""
        message = self.get_obj_from_selected_row()
        if message:
            messages = get_messages_obj(self.model.device)
            """
            def get_message_cb(sms):
                # Now save SMS to DB
                where = TV_DICT_REV['drafts_treeview']
                tv = self.view['drafts_treeview']
                d = messages.add_message(sms, where=where)
                d.addCallback(lambda smsback:
                                    tv.get_model().add_message(smsback))

            messages.get_message(message).addCallback(get_message_cb)
            """

    def _use_detail_add_contact(self, widget):
        """Handler for the use detail menu"""
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = AddContactController(self.model, self)
            view = AddContactView(ctrl)
            view.set_parent_view(self.view)
            ctrl.number_entry.set_text(message.number)
            view.show()

    def get_obj_from_selected_row(self):
        """Returns the data from the selected row"""
        page = self.view['main_notebook'].get_current_page() + 1

        treeview = self.view[TV_DICT[page]]
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        if not selected or len(selected) > 1:
            return None

        # in the contacts treeview, the contact object is at row[3]
        # while in the rest the SMS object is at row[4]
        row = (page == TV_DICT_REV['contacts_treeview']) and 3 or 4
        _iter = model.get_iter(selected[0])
        return model.get_value(_iter, row)


