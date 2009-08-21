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
"""Controllers for the main window and the about dialog"""

__version__ = "$Rev: 1172 $"

import os
from signal import SIGKILL

import gtk

from twisted.internet import reactor, defer
from twisted.internet.utils import getProcessOutput
from twisted.python import log
from twisted.application.internet import TimerService

from wader.common.config import config
from wader.common.csvutils import CSVUnicodeWriter, CSVContactsReader
import wader.common.consts as consts
from wader.common.encoding import _
from wader.common.messages import get_messages_obj
from wader.common.netspeed import get_signal_level_from_rssi
from wader.common.persistent import DBContact
from wader.common.profiles import get_profile_manager
import wader.common.notifications as N
from wader.common.phonebook import (get_phonebook,
                                  all_same_type, all_contacts_writable)
from wader.common.oal import osobj
from wader.common.shutdown import shutdown_core
from wader.common.daemon import NetworkSpeedDaemon
from wader.vmc import Model
from wader.vmc.notification import (show_error_notification,
                                 show_normal_notification)
from wader.vmc.tray import get_tray_icon
from wader.vmc.controllers.base import WidgetController, TV_DICT, TV_DICT_REV
from wader.vmc.controllers.contacts import (AddContactController,
                                          SearchContactController)
from wader.vmc.controllers.diagnostics import DiagnosticsController
from wader.vmc.controllers.initialconf import (NewProfileController,
                                             EditProfileController)
from wader.vmc.controllers.pin import (AskPINAndExecuteFuncController,
                                     PinModifyController)
from wader.vmc.controllers.preferences import (PreferencesController,
                                             SMSPreferencesController)
from wader.vmc.controllers.sms import ForwardSmsController, NewSmsController
from wader.vmc.models.initialconf import NewProfileModel
from wader.vmc.models.diagnostics import DiagnosticsModel
from wader.vmc.models.base import BaseWrapperModel
from wader.vmc.models.preferences import PreferencesModel
from wader.vmc.views.contacts import AddContactView, SearchContactView
from wader.vmc.views.diagnostics import DiagnosticsView
from wader.vmc.views.initialconf import NewProfileView, EditProfileView
from wader.vmc.views.pin import PinModifyView, AskPINView
from wader.vmc.views.preferences import PreferencesView, SMSPreferencesView
from wader.vmc.views.sms import ForwardSmsView, NewSmsView
from wader.vmc.views.application import units_to_bits, UNIT_MB
from wader.vmc import dialogs
from vmc.utils import utilities

from vmc.contrib import louie

DEVICE_PRESENT, NO_DEVICE_PRESENT, DEVICE_ADDED = range(3)

def get_fake_toggle_button():
    """Returns a toggled L{gtk.ToggleToolButton}"""
    button = gtk.ToggleToolButton()
    button.set_active(True)
    return button


class BaseApplicationController(WidgetController):
    """Controller for the main window"""

    def __init__(self, model, splash):
        super(BaseApplicationController, self).__init__(model)
        self.tray = None
        self.mode = None
        self.splash = splash
        self.usage_updater = None
        self.user_limit_notified = False
        self._setup_trayicon()
        self.bearer = 'gprs'    # 'gprs' or 'umts'
        self.signal = 0         # -1, 0, 25, 50, 75, 100

    def _quit_or_minimize(self, *args):
        if config.getboolean('preferences', 'close_minimizes'):
            # pretend the delete_event didn't happen and hide the window
            window = self.view.get_top_widget()
            window.emit_stop_by_name("delete_event")
            window.hide()
            return True
        else:
            self.quit_application()
            return False

    def quit_application(self, *args):
        """Closes open connections and exits the application"""
        def disconnect_cb(ignored):
            self.hide_widgets()
            title = _('Shutting down')
            apb = dialogs.ActivityProgressBar(title, self)
            self.append_widget(apb)

            def default_eb():
                pass

            apb.set_default_cb(2, lambda: shutdown_core(delay=.3))
            apb.set_cancel_cb(default_eb)
            apb.init()

        if self.usage_updater:
            self.usage_updater.stopService()

        # hide notifications just in case
        if not self.model.is_connected():
            disconnect_cb(True)
        else:
            message = _('Connected to Internet')
            details = _("""
You need to disconnect from Internet before shutting
down %s,
if you want to do so, press the OK button.
""") % consts.APP_LONG_NAME

            if dialogs.open_warning_request_cancel_ok(message, details):
                # user said yes
                self.stop_network_stats_timer()
                d = self.model.disconnect_internet()
                d.addCallback(disconnect_cb)

    def start(self):
        """Overrides the register_view method and starts the whole thing up"""
        self.view.set_disconnected()

        # we're on SMS mode
        self.on_sms_button_toggled(get_fake_toggle_button())

        self._setup_signals()

        self.usage_updater = TimerService(5, self.update_usage_view)
        self.usage_updater.startService()

        if self.model.get_device():
            self.mode = DEVICE_PRESENT
        else:
            self.mode = NO_DEVICE_PRESENT
            self.view.set_no_device_present()

        self.setup()

    def _setup_signals(self):
        self._setup_menubar_hacks()

        for treeview_name in list(set(TV_DICT.values())):
            treeview = self.view[treeview_name]
            treeview.connect('key_press_event', self.__on_treeview_key_press)
            if treeview.name != 'contacts_treeview':
                treeview.connect('row-activated', self._row_activated_tv)

        self.view.get_top_widget().connect("delete_event",
                                           self._quit_or_minimize)

    def start_device_activities(self, widget=None, hotplug=False):
        if self.mode == NO_DEVICE_PRESENT:
            return

        if hotplug:
            #XXX:
            pass

        # not hotplug, regular startup
        self.model.daemons = self.model.wrapper.rmanager.daemons
        self.model.notimanager = self.model.wrapper.rmanager.notimanager

        def enable_disable_pin(ignored):
            def pin_status_cb(active):
                """
                Actives or disactivates change_pin_menuitem

                If C{active} is True set change_pin_menuitem active
                """
                if not active:
                    self.view['change_pin1'].set_sensitive(False)
                    self.view['request_pin1'].set_active(False)

                if widget:
                    widget.close()

                self._hide_splash_and_show_ourselves()
                self.paint_initial_values()
                return True

            d = self.model.get_pin_status()
            d.addCallback(pin_status_cb)
            return d

        d = defer.succeed(True)
        d.addCallback(enable_disable_pin)
        # get the pin status and toggle change_pin1 accordingly

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

        items = ['imagemenuitem8', 'sms_delete_menu_item',
                 'forward_sms_menu_item']

        for item in items:
            self.view[item].set_events(gtk.gdk.BUTTON_PRESS_MASK)

        # contacts_menubar delete item and messages_menubar delete item
        for item in ['imagemenuitem8', 'sms_delete_menu_item']:
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
        """Fills the contacts treeview with SIM & DB contacts"""
        self.splash.set_text(_('Reading contacts...'))
        phonebook = get_phonebook(self.model.get_sconn())

        def process_contacts(contacts):
            treeview = self.view['contacts_treeview']
            model = treeview.get_model()
            model.add_contacts(contacts)

            return contacts

        d = phonebook.get_contacts()
        d.addCallback(process_contacts)
        d.addErrback(log.err)
        return d

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
        messages_obj = get_messages_obj(self.model.get_sconn())
        self.splash.set_text(_('Reading messages...'))
        def process_sms(sms_list):
            for sms in sms_list:
                active_tv = TV_DICT[sms.where]         # get treeview name
                treeview = self.view[active_tv]        # get treeview object
                treeview.get_model().add_message(sms, contacts) # append to tv

            self.splash.pulse()
            return True

        d = messages_obj.get_messages()
        d.addCallback(process_sms)
        return d

    def _fill_treeviews(self):
        """
        Fills the treeviews with SMS and contacts from the SIM and DB
        """
        d = self._fill_contacts()
        d.addCallback(self._fill_messages)
        d.addErrback(log.err)
        return d

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
        limit = int(config.get('preferences', 'traffic_threshold'))
        notification = config.getboolean('preferences', 'usage_notification')
        limit = units_to_bits(limit, UNIT_MB)
        if (notification and limit > 0
                and self.model.get_transferred_total(0) > limit
                and not self.user_limit_notified):
            self.user_limit_notified = True
            message = _("User Limit")
            details = _("You have reached your limit of maximum usage")
            #dialogs.open_warning_dialog(message, details)
            show_normal_notification(self.tray, message, details, expires=False)
        elif self.model.get_transferred_total(0) < limit :
            self.user_limit_notified = False

    def update_usage_view(self):
        self.model.clean_usage_cache()
        self._update_usage_panel('current', 0)
        self._update_usage_panel('last', -1)
        self._update_usage_session()
        self.view.update_bars_user_limit()
        self.usage_notifier()

    def setup(self, ignored=None):
        """
        Presents the main screen and configures profiles and devices
        """
        prof_manager = get_profile_manager(self.model.get_device())

        def check_update_profile_cb(profile):
            if profile:
                message = _('New mobile profile available')
                details = _("""
New profile available, do you want to load it?""")
                resp = dialogs.open_confirm_action_dialog(_('Load'),
                                                          message, details)
                if resp:
                    # User said yes
                    prof_manager.add_profile(profile)
                    prof_manager.load_profile(profile)

            if self.model.get_device():
                self.start_device_activities()
                self.view.set_device_present()

        d = self.model.check_profile_updates()
        d.addCallback(check_update_profile_cb)

    def paint_initial_values(self):
        """
        Sets the signal level and network name in the GUI
        """
        def paint_initial_values_eb(failure):
            """Need to handle the exception if get_network_info gets +COPS: 0"""
            return
        self.model.get_signal_level().addCallback(self._change_signal_level)
        d = self.model.get_network_info()
        d.addCallback(self._network_reg_cb)
        d.addErrback(paint_initial_values_eb)

    def _network_reg_cb(self, netinfo):
        if netinfo:
            netname, conn_type = netinfo
            self.view['network_name_label'].set_text(netname)
            self.update_signal_bearer(newmode=_(conn_type))

    def _change_radio_state(self, mode):
        if mode == N.RADIO_OFF:
            self.update_signal_bearer(newsignal=-1,
                                      newmode=_('Radio Disabled'))
        elif mode == N.RADIO_ON:
            # always set rssi 0, it's fine after radio switch on to show zero
            self.update_signal_bearer(newsignal=0)

    def _change_signal_level(self, rssi):
        self.update_signal_bearer(newsignal=get_signal_level_from_rssi(int(rssi)))

    def _hide_splash_and_show_ourselves(self):
        self.splash.set_fraction(1.0)
        # now we are done, hide the splash screen and show ourselves
        self.splash.close()
        #self.splash = None
        self.view.get_top_widget().show()

    #----------------------------------------------#
    # Signals Handling                             #
    #----------------------------------------------#

    def on_quit_menu_item_activate(self, widget):
        exit_without_conf = config.getboolean('preferences',
                                            'exit_without_confirmation')
        if exit_without_conf:
            self.quit_application()
            return

        resp, checked = dialogs.open_dialog_question_checkbox_cancel_ok(
                    self.view,
                    _("Quit %s") % consts.APP_LONG_NAME,
                    _("Are you sure you want to exit?"))

        config.setboolean('preferences', 'exit_without_confirmation', checked)
        config.write()

        if resp:
            self.quit_application()

    def _build_profiles_menu(self):
        prof_manager = get_profile_manager(self.model.get_device())
        profiles = prof_manager.get_profile_list()

        def load_profile(widget, profile):
            prof_manager.load_profile(profile)

        def delete_profile(widget, profile):
            prof_manager.delete_profile(profile)

        def edit_profile(widget, profile):
            model = NewProfileModel(self.model.get_device())
            ctrl = EditProfileController(model, profile)
            view = EditProfileView(ctrl)
            view.set_parent_view(self.view)
            view.show()

        menu1 = gtk.Menu()
        for profile in profiles:
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", load_profile, profile)
            item.show()
            if config.current_profile == profile:
                item.set_sensitive(False)
            menu1.append(item)

        menu2 = gtk.Menu()
        for profile in profiles:
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", edit_profile, profile)
            item.show()
            menu2.append(item)

        menu3 = gtk.Menu()
        for profile in profiles:
            item = gtk.ImageMenuItem(profile.name)
            item.connect("activate", delete_profile, profile)
            item.show()
            if config.current_profile == profile:
                item.set_sensitive(False)
            menu3.append(item)

        return menu1, menu2, menu3

    def on_tools_menu_item_activate(self, widget):
        # we're gonna build dinamically the menu with the profiles
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
        model = DiagnosticsModel(self.model.wrapper)
        ctrl = DiagnosticsController(model, self)
        view = DiagnosticsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_help_topics_menuitem_activate(self, widget):
        binary = config.get('preferences', 'browser')
        index_path = os.path.join(consts.GUIDE_DIR, 'index.html')
        getProcessOutput(binary, [index_path], os.environ)

    def on_about_menu_item_activate(self, widget):
        about = dialogs.get_about_dialog()
        about.run()
        about.destroy()

    def on_change_pin1_activate(self, widget):
        ctrl = PinModifyController(self.model)
        view = PinModifyView(ctrl)
        view.show()

    def on_request_pin1_activate(self, checkmenuitem):
        model = BaseWrapperModel(self.model.wrapper)
        ctrl = AskPINAndExecuteFuncController(model)

        def func_callback(parent_ctrl, enable):
            parent_ctrl.view['change_pin1'].set_sensitive(enable)
            parent_ctrl.view['request_pin1'].set_active(enable)

        def func_errback(parent_ctrl, enable):
            parent_ctrl.view['request_pin1'].set_active(enable)

        def enable_pin_auth(active):
            if not active:
                ctrl.set_callback(func_callback, self, True)
                ctrl.set_errback(func_errback, self, False)
                view = AskPINView(ctrl)
                ctrl.set_mode('enable_pin')
                view.show()
            else:
                self.view['change_pin1'].set_sensitive(True)
                self.view['request_pin1'].set_active(True)

        def disable_pin_auth(active):
            if active:
                ctrl.set_callback(func_callback, self, False)
                ctrl.set_errback(func_errback, self, True)
                view = AskPINView(ctrl)
                ctrl.set_mode('disable_pin')
                view.show()
            else:
                self.view['change_pin1'].set_sensitive(False)
                self.view['request_pin1'].set_active(False)

        d = self.model.get_pin_status()
        if checkmenuitem.get_active():
            # The user wants the pin to be asked at startup
            # first we check if its already set
            d.addCallback(enable_pin_auth)
        else:
            # The user doesn't wants the pin to be asked
            d.addCallback(disable_pin_auth)

    def on_new_profile_menuitem_activate(self, widget):
        model = NewProfileModel(self.model.get_device())
        ctrl = NewProfileController(model)
        view = NewProfileView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_inspect_menu_item_activate(self, widget):
        try:
            import vte
        except ImportError:
            message = _("Missing dependency")
            details = _("To use this widget you need python-vte installed")
            dialogs.open_warning_dialog(message, details)
            return

        window = gtk.Window()
        window.resize(400, 400)
        window.set_transient_for(self.view.get_top_widget())
        window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        window.show()

        term = vte.Terminal()
        args = ['ssh', 'admin@localhost', '-p', '2222']
        ssh_pid = term.fork_command(args[0], args, [])
        term.set_emulation('xterm')
        term.connect("child-exited", lambda _: window.destroy())
        term.show()

        def delete_event_cb(_window, event):
            # make sure that the ssh connection is lost
            _window.emit_stop_by_name('delete_event')
            os.kill(ssh_pid, SIGKILL)
            return True

        window.add(term)
        window.connect("delete_event", delete_event_cb)
        window.show_all()

    def on_preferences_menu_item_activate(self, widget):
        model = PreferencesModel(self.model.wrapper)
        ctrl = PreferencesController(model, self)
        view = PreferencesView(ctrl, self.model.get_device())
        view.show()

    def on_mobile1_activate(self, widget):
        # This emits the toggled signal
        self.view['connect_button'].set_active(True)

    def on_import_contacts1_activate(self, widget):
        filepath = dialogs.open_import_csv_dialog()
        if filepath:
            model = self.view['contacts_treeview'].get_model()

            phonebook = get_phonebook(self.model.get_sconn())
            def get_free_ids_cb(free):
                try:
                    reader = CSVContactsReader(open(filepath), free)
                except ValueError:
                    message = _('Invalid CSV format')
                    details = _("""
The csv file that you have tried to import has an invalid format.""")
                    dialogs.open_warning_dialog(message, details)
                else:
                    contacts = list(reader)
                    d2 = phonebook.add_contacts(contacts, True)
                    d2.addCallback(lambda reply: model.add_contacts(reply))
                    d2.addErrback(log.err)

            self.model.get_free_contact_ids().addCallback(get_free_ids_cb)

    def on_export_contacts1_activate(self, widget):
        filepath = dialogs.save_csv_file()
        if filepath:
            writer = CSVUnicodeWriter(open(filepath, 'w'))
            phonebook = get_phonebook(self.model.get_sconn())
            d = phonebook.get_contacts()
            d.addCallback(lambda contacts: writer.write_rows([c.to_csv()
                                                        for c in contacts]))

    def on_connect_button_toggled(self, button):
        if button.get_active():
            # check if dialer assumptions are met
            problems = osobj.check_dialer_assumptions()
            if problems:
                message, details = problems
                dialogs.open_warning_dialog(message, details)
                self.view['connect_button'].set_active(False)
                return

            # here we go...
            title = _('Connecting...')
            # show a modal progress bar to the user, one day we could include
            # realtime information about the connection progress...
            apb = dialogs.ActivityProgressBar(title, self)
            self.append_widget(apb)

            d = self.model.connect_internet()
            def connect_internet_cb(resp):
                apb.close()
                self.start_network_stats_timer()
                self.view.set_connected()
                # if device has only one port, we need to manually set
                # net_statusbar contents manually, as
                # NetworkRegistrationService would handle it
                if self.model.get_device().has_two_ports():
                    self.model.get_network_info(process=False).addCallback(
                        lambda netinfo: self.view['net_statusbar'].push(1,
                                _('Connected to %s') % netinfo[1]))
                else:
                    self.view['net_statusbar'].push(1, _('Connected'))

            d.addCallbacks(connect_internet_cb, lambda fail: log.err(fail))
            self.view['net_statusbar'].push(1, _('Connecting...'))

            def default_eb():
                self.model.disconnect_internet()
                self.view.set_disconnected()

            apb.set_cancel_cb(default_eb)
            apb.init()
        else:
            # the button was active and now it isn't
            self.model.disconnect_internet()
            self.stop_network_stats_timer()

            self.view['mobile1'].set_sensitive(True)
            self.view['preferences_menu_item'].set_sensitive(True)
            self.view.set_disconnected()

    def on_sms_menu_item_activate(self, widget):
        self.on_sms_button_toggled(get_fake_toggle_button())

    def on_usage_menu_item_activate(self, widget):
        self.on_usage_button_clicked(get_fake_toggle_button())

    def on_support_menu_item_activate(self, widget):
        self.on_support_button_toggled(get_fake_toggle_button())

    def on_minimize_menu_item_activate(self, widget):
        pass

    def on_sms_preferences_activate(self, widget):
        model = PreferencesModel(self.model.wrapper)
        ctrl = SMSPreferencesController(model)
        view = SMSPreferencesView(ctrl, self)
        view.set_parent_view(self.view)
        view.show()

    def on_mail_button_clicked(self, widget):
        if self._check_if_connected():
            binary = config.get('preferences', 'mail')
            getProcessOutput(binary, ['REPLACE@ME.COM'], os.environ)

    def on_sms_button_toggled(self, widget):
        if widget.get_active():
            self.view['usage_frame'].hide()
            self.view['usage_tool_button'].set_active(False)
            self.view['support_tool_button'].set_active(False)
            self.view['support_notebook'].hide()
            self.view['sms_frame_alignment'].show()
            self.view['sms_tool_button'].set_active(True)

    def on_internet_button_clicked(self, widget):
        if self._check_if_connected():
            binary = config.get('preferences', 'browser')
            getProcessOutput(binary, [consts.APP_URL], os.environ)

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
        ctrl = NewSmsController(Model(), self)
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

    def on_reply_sms_no_quoting_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(Model(), self)
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.get_number())
            ctrl.set_textbuffer_focus()
            view.show()

    def on_reply_sms_quoting_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(Model(), self)
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_recipient_numbers(message.get_number())
            ctrl.set_textbuffer_text(message.get_text())
            ctrl.set_textbuffer_focus()
            view.show()

    def on_forward_sms_menu_item_activate(self, widget):
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(Model(), self)
            view = ForwardSmsView(ctrl)
            ctrl.numbers_entry.grab_focus()
            ctrl.set_textbuffer_text(message.get_text())
            view.set_parent_view(self.view)
            view.show()

    def on_add_contact_menu_item_activate(self, widget):
        self.on_new_contact_menu_item_activate(None)

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
        self.view['vbox17'].show()

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

        self.view['vbox17'].hide()

    #----------------------------------------------#
    # MISC FUNCTIONALITY                           #
    #----------------------------------------------#

    def _name_contact_cell_edited(self, widget, path, newname):
        """Handler for the cell-edited signal of the name column"""
        # first check that the edit is necessary
        model = self.view['contacts_treeview'].get_model()
        if newname != model[path][1] and newname != '':
            model[path][1] = newname
            contact = model[path][3]
            contact.name = unicode(newname, 'utf8')
            if not isinstance(contact, DBContact):
                model[path][3] = contact
                phonebook = get_phonebook(self.model.get_sconn())
                d = phonebook.edit_contact(contact)

    def _number_contact_cell_edited(self, widget, path, newnumber):
        """Handler for the cell-edited signal of the number column"""
        model = self.view['contacts_treeview'].get_model()
        number = newnumber.strip()
        # check that the edit is necessary
        if number != model[path][2] and utilities.is_valid_number(number):
            contact = model[path][3]
            contact.number = unicode(newnumber, 'utf8')
            if not isinstance(contact, DBContact):
                model[path][2] = number
                model[path][3] = contact

                phonebook = get_phonebook(self.model.get_sconn())
                d = phonebook.edit_contact(contact)

    def _setup_trayicon(self, ignoreconf=False):
        """Attaches VMC's trayicon to the systray"""
        if ignoreconf:
            # ignoreconf is set to True when invoked from the preferences
            # controller
            if self.tray:
                self.tray.show()
            else:
                self.tray = get_tray_icon(self._show_hide_window,
                                          self.get_trayicon_popup_menu)
            return

        self.tray = get_tray_icon(self._show_hide_window,
                                  self.get_trayicon_popup_menu)
        self.tray.hide()
        if config.getboolean('preferences', 'show_icon'):
            self.tray.show()

    def _detach_trayicon(self):
        """Detachs VMC's trayicon from the systray"""
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
            if event.button == 1: # left click
                if win.get_property('visible'):
                    win.hide()
                else:
                    win.present()
            elif event.button == 3: # right click
                menu = self.get_trayicon_popup_menu()
                menu.popup(None, None, None, event.button, event.time)

    def _row_activated_tv(self, treeview, path, col):
        # get selected row
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = ForwardSmsController(Model(), self)
            view = ForwardSmsView(ctrl)
            view.set_parent_view(self.view)
            ctrl.set_textbuffer_text(message.get_text())
            ctrl.set_recipient_numbers(message.get_number())
            if treeview.name in 'drafts_treeview':
                # if the SMS is a draft, delete it after sending it
                ctrl.set_processed_sms(message)
            view.show()

    def _check_if_connected(self):
        """
        Returns True if connected or the user doesn't cares is not connected
        """
        if self.model.is_connected():
            return True
        else:
            message = _("Not connected")
            details = _("No mobile connection. Do you want to continue?")
            return dialogs.open_warning_request_cancel_ok(message, details)

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

        if treeview.name == 'contacts_treeview':
            manager = get_phonebook(self.model.get_sconn())
        else:
            manager = get_messages_obj(self.model.get_sconn())

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

        manager.delete_objs(objs)

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
                self.view['smsbody_textview'].get_buffer().set_text(_obj.get_text())
                self.view['vbox17'].show()
            else:
                self.view['smsbody_textview'].get_buffer().set_text('')
                self.view['vbox17'].hide()

    def _send_sms_to_contact(self, menuitem, treeview):
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        numbers = [model.get_value(_iter, 2) for _iter in iters]

        ctrl = NewSmsController(Model(), self)
        view = NewSmsView(ctrl)
        view.set_parent_view(self.view)
        view.show()

        ctrl.set_entry_text(", ".join(numbers))

    def _edit_external_contacts(self, menuitem, editor=None):
        if editor:
            cmd = editor[0]
            args = len(editor) > 1 and editor[1:] or []
            getProcessOutput(cmd, args, os.environ)

    def get_trayicon_popup_menu(self, *args):
        """Returns a popup menu when you right click on the trayicon"""

        connect_button = self.view['connect_button']

        def _disconnect_from_inet(widget):
            connect_button.set_active(False)

        def _connect_to_inet(widget):
            connect_button.set_active(True)

        menu = gtk.Menu()

        if self.model.is_connected():
            item = gtk.ImageMenuItem(_("Disconnect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(consts.IMAGES_DIR,
                              'stop16x16.png'))
            item.connect("activate", _disconnect_from_inet)
        else:
            item = gtk.ImageMenuItem(_("Connect"))
            img = gtk.Image()
            img.set_from_file(os.path.join(consts.IMAGES_DIR,
                              'connect-16x16.png'))
            item.connect("activate", _connect_to_inet)

        item.set_image(img)
        if not self.model.get_device():
            item.set_sensitive(False)
        item.show()
        menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        item = gtk.ImageMenuItem(_("Send SMS"))
        img = gtk.Image()
        img.set_from_file(os.path.join(consts.IMAGES_DIR, 'sms16x16.png'))
        item.set_image(img)
        item.connect("activate", self.on_new_sms_activate)
        if not self.model.get_device():
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
        img.set_from_file(os.path.join(consts.IMAGES_DIR, 'sms16x16.png'))
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
            messages = get_messages_obj(self.model.get_sconn())
            def get_message_cb(sms):
                # Now save SMS to DB
                where = TV_DICT_REV['drafts_treeview']
                tv = self.view['drafts_treeview']
                d = messages.add_message(sms, where=where)
                d.addCallback(lambda smsback:
                                    tv.get_model().add_message(smsback))

            messages.get_message(message).addCallback(get_message_cb)

    def _use_detail_add_contact(self, widget):
        """Handler for the use detail menu"""
        message = self.get_obj_from_selected_row()
        if message:
            ctrl = AddContactController(self.model, self)
            view = AddContactView(ctrl)
            view.set_parent_view(self.view)
            ctrl.number_entry.set_text(message.get_number())
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

    def start_network_stats_timer(self):
        raise NotImplementedError()

    def stop_network_stats_timer(self):
        raise NotImplementedError()

class ApplicationController(BaseApplicationController):
    """
    I extend BaseApplicationController with some signal handlers
    """
    def __init__(self, model, splash):
        super(ApplicationController, self).__init__(model, splash)
        self._setup_louie_signals()
        self.signal_loop = None
        self.net_loop = None
        self.time_loop = None
        self.start_time = 0

    def _setup_louie_signals(self):
        # louie notifications
        louie.connect(self.invalid_dns_handler, N.SIG_INVALID_DNS)
        louie.connect(self.disconnected_handler, N.SIG_DISCONNECTED)
        louie.connect(self.device_removed_handler, N.SIG_DEVICE_REMOVED)
        louie.connect(self.device_added_handler, N.SIG_DEVICE_ADDED)

    def start_network_stats_timer(self):
        """Starts the timer that updates the speed stats on screen"""
        capabilities = self.model.get_device().custom.device_capabilities
        if N.SIG_SPEED not in capabilities:
            # device cannot report the speed to us
            daemon = NetworkSpeedDaemon(2, self.model.get_device(),
                                        self.model.notimanager)
            self.model.daemons.append_daemon('speed', daemon)
            daemon.start()

    def stop_network_stats_timer(self):
        """Stops the network stats timer"""
        if self.model.daemons.has_daemon('speed'):
            self.model.daemons.stop_daemon('speed')

    def _change_net_stats_cb(self, (upmsg, downmsg)):
        self.view['upload_statusbar'].push(1, upmsg)
        self.view['download_statusbar'].push(1, downmsg)

    def start_polling_stats(self):
        if self.model.daemons.has_daemon('signal'):
            self.model.daemons.start_daemon('signal')
        if self.model.daemons.has_daemon('conn_mode'):
            self.model.daemons.start_daemon('conn_mode')

    def stop_polling_stats(self):
        if self.model.daemons.has_daemon('conn_mode'):
            self.model.daemons.stop_daemon('conn_mode')
        if self.model.daemons.has_daemon('signal'):
            self.model.daemons.stop_daemon('signal')

    def close_serial_connection(self):
        device = self.model.get_device()
        if device.sconn:
            device.sconn = None

    def update_signal_bearer(self, newsignal = None, newmode = None):
        if newsignal:
            self.signal = newsignal

        if newmode:
            if newmode in [_('N/A'), _('Radio Disabled')]:
                pass
            elif newmode in [_('GPRS'), _('EDGE')]:
                self.bearer = 'gprs'
            else:
                self.bearer = 'umts'

            self.view['cell_type_label'].set_text(newmode)
            if self.model.is_connected():
                msg = _('Connected to %s') % newmode
                self.view['net_statusbar'].push(1, msg)

        if self.signal == -1:
            image = 'radio-off.png'
        else:
            image = 'signal-%s-%d.png' % (self.bearer, self.signal)

        self.view['signal_image'].set_from_file(
                os.path.join(consts.IMAGES_DIR, image))

    #################################################################
    # SIGNAL HANDLERS                                               #
    #################################################################

    def on_illegal_operation(self, failure):
        message = _('Illegal Operation!')
        details = _("""
Your device only has one port and you are currently connected
to Internet, you cannot perform any operation while connected""")
        dialogs.open_warning_dialog(message, details)

    def _conn_mode_changed(self, mode):
        """Handler for the NEW_CONN_MODE signal"""
        if mode == N.NO_SIGNAL:
            self.update_signal_bearer(newmode=_('N/A'))
        elif mode == N.GPRS_SIGNAL:
            self.update_signal_bearer(newmode=_('GPRS'))
        else: # UMTS & HSDPÂ
            self.update_signal_bearer(newmode=_('3G'))

    def _network_changed(self, network):
        """Handler for the NEW_NETWORK signal"""
        self.view['network_name_label'].set_text(network)

    def _on_sms_received(self, (index, where)):
        def get_sms_cb(sms):
            if not sms:
                # Handle bogus CMTI notification, see #180
                return

            self.view['inbox_treeview'].get_model().add_message(sms)

            phonebook = get_phonebook(self.model.get_sconn())
            def lookup_number_cb(contacts):
                who = contacts and contacts[0].name or sms.get_number()
                message = _("<small>SMS received from %s</small>") % who
                dat = dict(date=sms.get_localised_date(), text=sms.get_text())
                details = _(
                "<small>Received at %(date)s</small>\n<b>%(text)s</b>") % dat

                noti = show_normal_notification(self.tray, message, details)
                self.append_widget(noti)

            d = phonebook.find_contact(number=sms.get_number())
            d.addCallback(lookup_number_cb)

        self.model.get_sms_by_index(index).addCallback(get_sms_cb)

    def invalid_dns_handler(self, dnslist):
        """Handler called when wvdial receives invalid DNS"""
        title = _("Invalid DNS received from Network")
        message = _(
"""
<small>The DNS settings received from the mobile network are invalid. You will
probably want to restart the connection, or if the problem persists, you
can specify a static DNS entry in the connection preferences</small>
""")
        notification = show_error_notification(self.tray, title, message)
        self.append_widget(notification)

    def disconnected_handler(self, *args):
        """Handler called when wvdial dies before connecting"""
        if self.model.is_connected():
            log.err("disconnected_handler this shouldn't happen")
            return

        self.hide_widgets()
        title = _("Disconnected from Internet")
        message = _("""
<small>%s has given
up after trying to connect three times to Internet. This might
be provoked by a problem in the configuration or just the fact
that there's no carrier.</small>""") % consts.APP_LONG_NAME

        notification = show_error_notification(self.tray, title, message)
        self.append_widget(notification)
        self.view['connect_button'].set_active(False)

    def device_removed_handler(self):
        """Handler called when the mobile device is unplugged whilst in use"""
        message = _("Device in use removed")
        details = _(
"""
The 3G device in use has been removed. Now
%s
is going to shutdown. In order to continue,
plug in the 3G device and start again.""") % consts.APP_LONG_NAME

        notification = show_error_notification(self.tray, message, details)

        self.hide_widgets()
        self.append_widget(notification)

        self.view.set_no_device_present()
        self.mode = NO_DEVICE_PRESENT
        if self.model.is_connected():
            self.view.set_disconnected()
            self.stop_network_stats_timer()
            self.model.disconnect_internet(hotplug=True)

        self.stop_polling_stats()
        self.close_serial_connection()

        # clean treeviews
        self._empty_treeviews(['inbox_treeview', 'contacts_treeview'])

    def device_added_handler(self, device):
        """
        Handler for the device_added signal
        """
        if self.mode != DEVICE_ADDED:
            self.mode = DEVICE_ADDED

# ajb - Maybe the network registration has occurred, and hence connect_button
#       has been enabled already. Hiding all widgets disables it again.
#            self.hide_widgets()

            info = dict(device_name=device.name, app_name=consts.APP_LONG_NAME)
            message = _("3G Device added")
            details = _("""
A new 3G device (%(device_name)s)
has been added, in around 15 seconds
(%(app_name)s) will resume its functioning""") % info

            notification = show_normal_notification(self.tray, message, details)
            self.append_widget(notification)

            title = _("Setting up device...")
            self.apb = dialogs.ActivityProgressBar(title, self, initnow=True,
                                                   disable_cancel=True)
            self.append_widget(self.apb)
            # we're gonna wait for 15 seconds till the device has settled
            # before starting the device activities
            # the last parameter means hotplug=True

            self.added_devices = set()
            def configure_added_devices():
                self.apb.close()
                if self.added_devices:
                    added_device = self.added_devices.pop()
                    self.try_to_configure_device(added_device,
                                                 configure_added_devices)
                else:
                    self.mode = NO_DEVICE_PRESENT

            # 15 seconds to accept devices when a device is plugged in
            reactor.callLater(15, configure_added_devices)

        self.added_devices.add(device)

    def on_netreg_exit(self):
        self.start_polling_stats()
        self.view['connect_button'].set_sensitive(True)

        self._empty_treeviews(['inbox_treeview', 'drafts_treeview',
                                'sent_treeview', 'contacts_treeview'])
        self._fill_treeviews()

    def try_to_configure_device(self, device, failure_cb):
        log.err("Trying to configure %s" % device.name)

        unsolicited_notifications_callbacks = {
            N.SIG_RSSI : self._change_signal_level,
            N.SIG_RFSWITCH : self._change_radio_state,
            N.SIG_SPEED : self._change_net_stats_cb,
            N.SIG_NEW_CONN_MODE : self._conn_mode_changed,
            N.SIG_NEW_NETWORK : self._network_changed,
            N.SIG_SMS : self._on_sms_received,
            N.SIG_CALL : None,
            N.SIG_CREG : None,
            N.SIG_CONNECTED : None,
            N.SIG_CONN : None, # Why are there two notifications for 'Connect'?
            N.SIG_DISCONNECTED : None,
        }

        if not config.current_profile:
            def configure_device():
                _model = NewProfileModel(device)
                _ctrl = NewProfileController(_model, hotplug=True,
                                             aux_ctrl=self)
                _view = NewProfileView(_ctrl)
                _view.set_parent_view(self.view) # center on main screen
                _view.show()

            statemachine_callbacks = {
                'InitExit' : configure_device,
                'NetRegExit' : self.on_netreg_exit,
            }
        else:
            statemachine_callbacks = {
                'InitExit' : self.start,
                'NetRegExit' : self.on_netreg_exit,
            }

        statemachine_errbacks = {
            'AlreadyConnecting' : None,
            'AlreadyConnected' : None,
            'IllegalOperationError' : self.on_illegal_operation,
        }

        try:
            from wader.vmc.wrapper import GTKWrapper
            self.model.wrapper = GTKWrapper(device,
                                        unsolicited_notifications_callbacks,
                                        statemachine_callbacks,
                                        statemachine_errbacks, self)
            self.model.wrapper.start_behaviour(self)
        except:
            failure_cb()
