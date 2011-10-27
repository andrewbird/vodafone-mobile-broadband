# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano
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
Views for the main interface
"""

import os

import gtk
from pango import ELLIPSIZE_END

from wader.bcm.contrib.gtkmvc import View
from wader.bcm.config import config
from wader.bcm.translate import _
from wader.bcm.consts import (GLADE_DIR, IMAGES_DIR, THEMES_DIR,
                              APP_LONG_NAME, APP_URL)
from wader.bcm.constx import (BCM_MODEM_STATE_NODEVICE,
                              BCM_MODEM_STATE_HAVEDEVICE,
                              BCM_MODEM_STATE_DISABLED,
                              BCM_MODEM_STATE_LOCKED,
                              BCM_MODEM_STATE_UNLOCKING,
                              BCM_MODEM_STATE_UNLOCKED,
                              BCM_MODEM_STATE_ENABLING,
                              BCM_MODEM_STATE_DISABLING,
                              BCM_MODEM_STATE_ENABLED,
                              BCM_MODEM_STATE_SEARCHING,
                              BCM_MODEM_STATE_REGISTERED,
                              BCM_MODEM_STATE_DISCONNECTING,
                              BCM_MODEM_STATE_CONNECTING,
                              BCM_MODEM_STATE_CONNECTED)

from wader.bcm.utils import UNIT_KB, UNIT_MB, units_to_bytes
from wader.bcm.views.stats import StatsBar
from wader.bcm.controllers.base import TV_DICT
from wader.bcm.models.sms import SMSStoreModel
from wader.bcm.models.contacts import ContactsStoreModel

from wader.bcm.consts import (CFG_PREFS_DEFAULT_USAGE_USER_LIMIT,
                              CFG_PREFS_DEFAULT_USAGE_MAX_VALUE)

from wader.common.consts import (MM_GSM_ACCESS_TECH_UNKNOWN,
                                 MM_GSM_ACCESS_TECH_GSM,
                                 MM_GSM_ACCESS_TECH_GSM_COMPAT,
                                 MM_GSM_ACCESS_TECH_GPRS,
                                 MM_GSM_ACCESS_TECH_EDGE,
                                 MM_GSM_ACCESS_TECH_UMTS,
                                 MM_GSM_ACCESS_TECH_HSDPA,
                                 MM_GSM_ACCESS_TECH_HSUPA,
                                 MM_GSM_ACCESS_TECH_HSPA,
                                 MM_GSM_ACCESS_TECH_HSPA_PLUS,
                                 MM_GSM_ACCESS_TECH_LTE)

WIDGETS_TO_SHOW = ['change_pin1', 'request_pin1',
                   'import_contacts1', 'export_contacts1', 'new_menu_item',
                   'new_sms_menu_item', 'contact1', 'reply_sms_menu_item',
                   'reply_sms_menu', 'forward_sms_menu_item',
                   'imagemenuitem3', 'preferences_menu_item']
WIDGETS_TO_HIDE = WIDGETS_TO_SHOW + ['connect_button']

WIN_WIDTH = 625
WIN_HEIGHT = 500

SMS_TEXT_TV_WIDTH = 220


class MainView(View):
    """View for the main window"""

    def __init__(self, ctrl):

        height = 450        # define the max height of the main window
        GLADE_FILE = os.path.join(GLADE_DIR, "bcm.glade")

        super(MainView, self).__init__(ctrl, GLADE_FILE, 'main_window',
                                       register=False, domain='bcm')

        # Usage statistics
        self.usage_user_limit = int(config.get('preferences',
                                               'traffic_threshold',
                                         CFG_PREFS_DEFAULT_USAGE_USER_LIMIT))
        self.usage_max_value = int(config.get('preferences',
                                              'max_traffic',
                                         CFG_PREFS_DEFAULT_USAGE_MAX_VALUE))
        self.usage_units = UNIT_KB
        self.usage_bars = None

        self.bearer = 'gprs'    # 'gprs' or 'umts'
        self.signal = 0         # -1, 0, 25, 50, 75, 100

        self.setup_view(height)
        ctrl.register_view(self)
        self.throbber = None
        ctrl.update_usage_view()
        self.setup_treeview(ctrl)

        self.theme_ui()

    def show(self):
        ret = super(MainView, self).show()

        # XXX: AJB - for some reason these items hidden before
        # in ctrl.register_view() are reshown by parent.show()
        self['usage_frame'].hide()
        self['support_notebook'].hide()
        self['contacts_menubar'].hide()
        self['sms_message_pane'].hide()
        self['time_alignment'].hide()
        self['upload_alignment'].hide()
        self['download_alignment'].hide()
        self['roaming_image'].hide()

        return ret

    def setup_view(self, height):
        self.set_name()
        window = self.get_top_widget()
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_size_request(width=WIN_WIDTH, height=height)
        self._setup_support_tabs()
        self._setup_usage_view()
        self.set_status_line(BCM_MODEM_STATE_NODEVICE, None, None, None, None)
        self.set_view_state(BCM_MODEM_STATE_NODEVICE)

    def theme_ui(self):
        theme = os.path.join(THEMES_DIR, "default.gtkrc")
        gtk.rc_parse(theme)

    def _setup_support_tabs(self):
        # populate Help tab
        tbuf = gtk.TextBuffer()
        tbuf.set_text(_("In most cases you can find the answer to your"
            " questions about the program in the help menu. This menu can be"
            " accessed if you click on the \"Help\" label on the menu bar"
            " located in the top side of the window, and selecting the"
            " \"Help topics\" option."
            "\n\nYou can also find help, updates and tips in %(name)s's web:"
            "\n\n%(url)s."
            "\n\nIf you use the mail and browser buttons to access other"
            " programs in your system, you might need to ask your Systems"
            " Administrator any doubt that you might have.")
            % {'name': APP_LONG_NAME, 'url': APP_URL})
        self['support_notebook_help_text'].set_buffer(tbuf)

        # populate Support center tab
        tbuf = gtk.TextBuffer()
        tbuf.set_text(_("If you are using this program in a corporate"
            " environment, your company probably has a support center to"
            " solve the questions that you might have about the program."
            "\n\nIf your company does not have a support center, you will have"
            " to contact your company's System Administrator."))
        self['support_notebook_support_text'].set_buffer(tbuf)

    def set_customer_support_text(self, text):
        # populate Customer support tab
        tbuf = gtk.TextBuffer()
        tbuf.set_text(text)
        self['support_notebook_customer_text'].set_buffer(tbuf)

    def _setup_usage_view(self):
        args = {'user_limit': self.usage_user_limit}
#       labels = ('GPRS', '3G') * 2
        labels = ('TOTAL TRAFFIC') * 2  # XXX: Not sure about this.
        self.usage_bars = dict(zip(
                ('current-total', 'last-total'),
                    StatsBar.init_array(labels, **args)))

        self['stats_bar_last_box'].add(self.usage_bars['last-total'])
        self['stats_bar_current_box'].add(self.usage_bars['current-total'])
        # XXX: Malign hack we couldn't find out a better way to build up the
        # usage widgets without messing up the initial view
        self.get_top_widget().show_all()
        self.get_top_widget().hide()
        self['sms_message_pane'].hide()
        self['contacts_menubar'].hide()

    def show_current_session(self, show):
        items = ['usage_label7', 'current_session_2g_label',
                 'usage_label8', 'current_session_3g_label',
                 'usage_label9', 'current_session_total_label', 'label8']
        if show:
            for item in items:
                self[item].show()
        else:
            for item in items:
                self[item].hide()

    def set_connection_time(self, td):
        # XXX: timedelta string representation does not respect localization,
        #      but this will only become a problem if the connection is up for
        #      more than one day as the day field will be displayed in English
        self['time_statusbar'].push(1, str(td).split('.')[0])

    def set_transfer_rate(self, rate, upload=False):

        def bps_to_human(bps):
            f = float(bps)
            for m in ['b/s ', 'kb/s', 'mb/s', 'gb/s']:
                if f < 1000:
                    return "%3.2f %s" % (f, m)
                f /= 1000
            return _("N/A")

        if upload:
            self['upload_statusbar'].push(1, bps_to_human(rate * 8))
        else:
            self['download_statusbar'].push(1, bps_to_human(rate * 8))

    def set_usage_value(self, widget, value):

        def bytes_to_human(_bytes):
            f = float(_bytes)
            for m in ['B', 'KiB', 'MiB', 'GiB']:
                if f < 1000:
                    if _bytes < 1000:  # don't show fraction of bytes
                        return "%3.0f %s" % (f, m)
                    else:
                        return "%3.2f %s" % (f, m)
                f /= 1024
            return _("N/A")

        if isinstance(value, (int, long)):
            self[widget].set_text(bytes_to_human(value))
        else:
            self[widget].set_text(str(value))

    def set_usage_bar_value(self, bar, value):
        self.usage_bars[bar].set_value(value)

    def update_bars_user_limit(self):
        self.usage_user_limit = int(config.get('preferences',
                                               'traffic_threshold',
                                        CFG_PREFS_DEFAULT_USAGE_USER_LIMIT))
        self.usage_max_value = int(config.get('preferences',
                                              'max_traffic',
                                        CFG_PREFS_DEFAULT_USAGE_MAX_VALUE))

        for bar in self.usage_bars.values():
            bar.set_user_limit(units_to_bytes(self.usage_user_limit, UNIT_MB))
            bar.set_max_value(units_to_bytes(self.usage_max_value, UNIT_MB))

    def show_statistics(self, visible):
        if not visible:
            self['time_alignment'].hide()
            self['upload_alignment'].hide()
            self['download_alignment'].hide()
        else:
            self['time_alignment'].show()
            self['upload_alignment'].show()
            self['download_alignment'].show()

    def set_name(self, name=APP_LONG_NAME):
        self.get_top_widget().set_title(name)

    def set_status_line(self, state, registration, tech, operator, rssi):

        def set_image(filename):
            try:
                self['signal_image'].set_from_file(
                                        os.path.join(IMAGES_DIR, filename))
            except AttributeError:
                pass  # Probably we are being destroyed

        def set_cell_type(name=None):
            try:
                if name:
                    self['cell_type_label'].set_text(name)
                    self['cell_type_label'].show()
                else:
                    self['cell_type_label'].hide()
            except AttributeError:
                pass

        def set_network_name(name=None):
            try:
                if name:
                    self['network_name_label'].set_text(name)
                    self['network_name_label'].show()
                else:
                    self['network_name_label'].hide()
            except AttributeError:
                pass

        def set_roaming_indicator(show=False):
            try:
                if show:
                    self['roaming_image'].show()
                else:
                    self['roaming_image'].hide()
            except AttributeError:
                pass

        def get_signal_image_name(_type, rssi):
            if rssi < 10 or rssi > 100:
                value = 0
            elif rssi < 25:
                value = 25
            elif rssi < 50:
                value = 50
            elif rssi < 75:
                value = 75
            elif rssi <= 100:
                value = 100
            return 'signal-%s-%d.png' % (_type, value)

        if state >= BCM_MODEM_STATE_REGISTERED:
            # construct the signal image, bearer, network, roaming state

            # Image
            if tech == MM_GSM_ACCESS_TECH_UNKNOWN:
                set_image('radio-off.png')
            elif tech <= MM_GSM_ACCESS_TECH_EDGE:
                set_image(get_signal_image_name('gprs', rssi))
            elif tech <= MM_GSM_ACCESS_TECH_HSPA_PLUS:
                set_image(get_signal_image_name('umts', rssi))
            else:
                set_image(get_signal_image_name('lte', rssi))

            # Bearer
            tech_names = {
                MM_GSM_ACCESS_TECH_GSM: _('GSM'),
                MM_GSM_ACCESS_TECH_GSM_COMPAT: _('GSM_COMPAT'),
                MM_GSM_ACCESS_TECH_GPRS: _('GPRS'),
                MM_GSM_ACCESS_TECH_EDGE: _('EDGE'),
                MM_GSM_ACCESS_TECH_UMTS: _('UMTS'),
                MM_GSM_ACCESS_TECH_HSDPA: _('HSDPA'),
                MM_GSM_ACCESS_TECH_HSUPA: _('HSUPA'),
                MM_GSM_ACCESS_TECH_HSPA: _('HSPA'),
                MM_GSM_ACCESS_TECH_HSPA_PLUS: _('HSPA+'),
                MM_GSM_ACCESS_TECH_LTE: _('LTE'),
            }
            set_cell_type(tech_names.get(tech, _('Unknown')))

            # Operator
            set_network_name(operator)

            # Roaming
            set_roaming_indicator(registration == 5)
        else:
            # Image
            if state <= BCM_MODEM_STATE_NODEVICE:
                set_image('nodevice.png')
            elif state in [BCM_MODEM_STATE_HAVEDEVICE,
                           BCM_MODEM_STATE_DISABLED,
                           BCM_MODEM_STATE_UNLOCKED,
                           BCM_MODEM_STATE_ENABLED]:
                set_image('device.png')
            elif state == BCM_MODEM_STATE_LOCKED:
                set_image('simlocked.png')
            elif state in [BCM_MODEM_STATE_UNLOCKING,
                           BCM_MODEM_STATE_ENABLING,
                           BCM_MODEM_STATE_DISABLING,
                           BCM_MODEM_STATE_SEARCHING]:
                set_image('throbber.gif')

            # Bearer
            set_cell_type(None)

            # Operator
            set_network_name(None)

            # Roaming
            set_roaming_indicator(False)

    def set_view_state(self, state):

        def set_button():
            if state < BCM_MODEM_STATE_REGISTERED:
                ifile = 'connect.png'
                label = _("Connect")
                enabled = False
            elif state == BCM_MODEM_STATE_REGISTERED:
                ifile = 'connect.png'
                label = _("Connect")
                enabled = True
            elif state == BCM_MODEM_STATE_DISCONNECTING:
                ifile = 'disconnect.png'
                label = _("Disconnecting")
                enabled = False
            elif state == BCM_MODEM_STATE_CONNECTING:
                ifile = 'connect.png'
                label = _("Connecting")
                enabled = False
            elif state == BCM_MODEM_STATE_CONNECTED:
                ifile = 'disconnect.png'
                label = _("Disconnect")
                enabled = True

            obj = self['connect_button']
            if obj:
                image = gtk.Image()
                image.set_from_file(os.path.join(IMAGES_DIR, ifile))
                image.show()
                obj.set_icon_widget(image)
                obj.set_label(label)
                obj.set_sensitive(enabled)

        def set_status_bar():
            state_names = {
                BCM_MODEM_STATE_HAVEDEVICE: _('Device found'),
                BCM_MODEM_STATE_DISABLED: _('Disabled'),
                BCM_MODEM_STATE_LOCKED: _('SIM locked'),
                BCM_MODEM_STATE_UNLOCKING: _('Authenticating'),
                BCM_MODEM_STATE_UNLOCKED: _('Authenticated'),
                BCM_MODEM_STATE_ENABLING: _('Enabling'),
                BCM_MODEM_STATE_DISABLING: _('Disabling'),
                BCM_MODEM_STATE_ENABLED: _('Enabled'),
                BCM_MODEM_STATE_SEARCHING: _('Searching'),
                BCM_MODEM_STATE_REGISTERED: _('Not connected'),
                BCM_MODEM_STATE_CONNECTING: _('Connecting'),
                BCM_MODEM_STATE_DISCONNECTING: _('Disconnecting'),
                BCM_MODEM_STATE_CONNECTED: _('Connected'),
            }
            self['net_statusbar'].push(1,
                                    state_names.get(state, _('No device')))

        try:
            # Enable checkitem
            if state < BCM_MODEM_STATE_HAVEDEVICE:
                self['enable_modem'].set_active(False)
                self['enable_modem'].set_sensitive(False)
            elif state < BCM_MODEM_STATE_ENABLED:
                self['enable_modem'].set_active(False)
                self['enable_modem'].set_sensitive(True)
            else:
                self['enable_modem'].set_active(True)
                self['enable_modem'].set_sensitive(True)

            # Most items that need to switch on once device is enabled
            if state < BCM_MODEM_STATE_ENABLED:
                self['change_pin1'].set_sensitive(False)
                self['request_pin1'].set_sensitive(False)
                self['import_contacts1'].set_sensitive(False)
                self['topup_tool_button'].set_sensitive(False)
            else:
                self['change_pin1'].set_sensitive(True)
                self['request_pin1'].set_sensitive(True)
                self['import_contacts1'].set_sensitive(True)
                self['topup_tool_button'].set_sensitive(True)

            # But we also don't want to tempt the user to try changing
            # profile whilst connected
            if state < BCM_MODEM_STATE_ENABLED or \
                    state > BCM_MODEM_STATE_REGISTERED:
                self['profiles_menu_item'].set_sensitive(False)
            else:
                self['profiles_menu_item'].set_sensitive(True)

            set_button()

            set_status_bar()

            self.show_statistics(state == BCM_MODEM_STATE_CONNECTED)
            self.show_current_session(state == BCM_MODEM_STATE_CONNECTED)

        except AttributeError:
            pass  # Probably we are being destroyed

    def setup_treeview(self, ctrl):
        """Sets up the treeviews"""
        for name in list(set(TV_DICT.values())):
            treeview = self[name]
            col_smstype, col_smstext, col_smsnumber, \
                    col_smsdate, col_smsid = range(5)
            col_usertype, col_username, col_usernumber,\
                    col_userid, col_editable = range(5)
            if name in 'contacts_treeview':
                model = ContactsStoreModel()
            else:
                model = SMSStoreModel(ctrl.model.device)

            treeview.set_model(model)
            treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

            if name in 'contacts_treeview':
                cell = gtk.CellRendererPixbuf()
                column = gtk.TreeViewColumn(_("Type"))
                column.pack_start(cell)
                column.set_attributes(cell, pixbuf=col_usertype)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                column = gtk.TreeViewColumn(_("Name"), cell,
                                            text=col_username,
                                            editable=col_editable)
                column.set_resizable(True)
                column.set_sort_column_id(col_username)
                cell.connect('edited', ctrl._name_contact_cell_edited)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                column = gtk.TreeViewColumn(_("Number"), cell,
                                            text=col_usernumber,
                                            editable=col_editable)
                column.set_resizable(True)
                column.set_sort_column_id(col_usernumber)
                cell.connect('edited', ctrl._number_contact_cell_edited)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                column = gtk.TreeViewColumn("IntId", cell, text=col_userid)
                column.set_visible(False)
                column.set_sort_column_id(col_userid)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                column = gtk.TreeViewColumn("Editable", cell,
                                            text=col_editable)
                column.set_visible(False)
                column.set_sort_column_id(col_editable)
                treeview.append_column(column)

            else:  # inbox_tv sent_tv drafts_tv sent_tv
                cell = gtk.CellRendererPixbuf()
                column = gtk.TreeViewColumn(_("Type"))
                column.pack_start(cell)
                column.set_attributes(cell, pixbuf=col_smstype)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                cell.set_fixed_height_from_font(1)
                cell.set_property('editable', False)
                cell.set_property('ellipsize', ELLIPSIZE_END)
                cell.set_property('ellipsize-set', True)
                cell.set_property('wrap-width', -1)
                column = gtk.TreeViewColumn(_("Text"), cell,
                                        text=col_smstext)
                column.set_resizable(True)
                column.set_sort_column_id(col_smstext)
                column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                column.set_fixed_width(SMS_TEXT_TV_WIDTH)
                treeview.append_column(column)

                cell = gtk.CellRendererText()

                thename = name in ['sent_treeview', 'drafts_treeview'] \
                             and _("Recipient") or _("Sender")
                column = gtk.TreeViewColumn(thename, cell, text=col_smsnumber)
                column.set_resizable(True)
                column.set_sort_column_id(col_smsnumber)
                cell.set_property('editable', False)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                cell.set_property('xalign', 1.0)
                column = gtk.TreeViewColumn(_("Date"), cell, text=col_smsdate)
                column.set_resizable(True)
                column.set_sort_column_id(col_smsdate)

                def render_date(cellview, cell, model, _iter):
                    datetime = model.get_value(_iter, 3)
                    if datetime:
                        cell.set_property('text', datetime.strftime("%c"))
                    return

                def sort_func(model, iter1, iter2, data):
                    date1 = model.get_value(iter1, 3)
                    date2 = model.get_value(iter2, 3)
                    if date1 and not date2:
                        return 1
                    if date2 and not date1:
                        return -1
                    if date1 == date2:
                        return 0
                    if date1 < date2:
                        return -1
                    else:
                        return 1

                model.set_sort_column_id(col_smsdate, gtk.SORT_DESCENDING)
                model.set_sort_func(col_smsdate, sort_func, None)
                column.set_cell_data_func(cell, render_date)
                cell.set_property('editable', False)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                column = gtk.TreeViewColumn("intId", cell, text=col_smsid)
                column.set_visible(False)
                column.set_sort_column_id(col_smsid)
                treeview.append_column(column)

    def set_message_preview(self, content):
        if content is None:
            self['smsbody_textview'].get_buffer().set_text('')
            self['sms_message_pane'].hide()
        else:
            self['smsbody_textview'].get_buffer().set_text(content)
            self['sms_message_pane'].show()

    def start_throbber(self):
        pass

    def stop_throbber(self):
        pass
