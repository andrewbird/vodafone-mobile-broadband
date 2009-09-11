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
from gtkmvc import View

from wader.vmc.translate import _
from wader.vmc.consts import GLADE_DIR, IMAGES_DIR, THEMES_DIR, APP_LONG_NAME
from wader.vmc.utils import repr_usage, UNIT_KB, UNIT_MB, units_to_bits
from wader.vmc.views.stats import StatsBar
from wader.vmc.controllers.base import TV_DICT
from wader.vmc.models.sms import SMSStoreModel
from wader.vmc.models.contacts import ContactsStoreModel

THROBBER = gtk.gdk.PixbufAnimation(os.path.join(GLADE_DIR, 'throbber.gif'))

WIDGETS_TO_SHOW = ['connect1',
                   'change_pin1', 'request_pin1',
                   'import_contacts1', 'export_contacts1', 'new_menu_item',
                   'new_sms_menu_item', 'contact1', 'reply_sms_menu_item',
                   'reply_sms_menu', 'forward_sms_menu_item',
                   'imagemenuitem3', 'preferences_menu_item']
WIDGETS_TO_HIDE = WIDGETS_TO_SHOW + ['connect_button']

WIN_WIDTH = 600
WIN_HEIGHT = 500

SMS_TEXT_TV_WIDTH = 220

class MainView(View):

    def __init__(self, ctrl):

#        if gtk.gdk.screen_height() < 600:
        if True:
            height = 420
            GLADE_FILE = os.path.join(GLADE_DIR, "VMC-reduced.glade")
        else:
            height = WIN_HEIGHT
            GLADE_FILE = os.path.join(GLADE_DIR, "VMC.glade")

        super(MainView, self).__init__(ctrl, GLADE_FILE,
            'main_window', register=False)

        #Usage statistics
#        self.usage_user_limit = int(config.get('preferences', 'traffic_threshold'))
#        self.usage_max_value = int(config.get('preferences', 'max_traffic'))
        self.usage_user_limit = 0
        self.usage_max_value = 10
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

        self['usage_frame'].hide()       # XXX: AJB - for some reason these items hidden before
        self['support_notebook'].hide()  # in ctrl.register_view() are reshown by parent.show()
        self['contacts_menubar'].hide()
        self['sms_message_pane'].hide()

        return ret

    def setup_view(self,height):
        self.set_name()
        window = self.get_top_widget()
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_size_request(width=WIN_WIDTH, height=height)
        self._setup_usage_view()

    def theme_ui(self):
        theme = os.path.join(THEMES_DIR, "default.gtkrc")
        gtk.rc_parse(theme)

    def _setup_usage_view(self):
        args = {'user_limit': self.usage_user_limit}
        labels = ('GPRS', '3G') * 2
        self.usage_bars = dict(zip(
                    ('current-gprs', 'current-3g', 'last-gprs', 'last-3g'),
                    StatsBar.init_array(labels, **args)))

        self['stats_bar_last_box'].add(self.usage_bars['last-gprs'])
        self['stats_bar_last_box'].add(self.usage_bars['last-3g'])
        self['stats_bar_current_box'].add(self.usage_bars['current-gprs'])
        self['stats_bar_current_box'].add(self.usage_bars['current-3g'])
        # XXX: Malign hack we couldn't find out a better way to build up the
        # usage widgets without messing up the initial view
        self.get_top_widget().show_all()
        self.get_top_widget().hide()
        self['sms_message_pane'].hide()
        self['contacts_menubar'].hide()

    def set_usage_value(self, widget, value):
        if isinstance(value, (int, long)):
            self[widget].set_text(repr_usage(value))
        else:
            self[widget].set_text(str(value))

    def set_usage_bar_value(self, bar, value):
        bar = self.usage_bars[bar]
        bar.set_value(value)

    def update_bars_user_limit(self):
        #self.usage_user_limit = int(config.get('preferences', 'traffic_threshold'))
        #self.usage_max_value = int(config.get('preferences', 'max_traffic'))
        self.usage_user_limit = 0
        self.usage_max_value = 10
        for bar in self.usage_bars.values():
            bar.set_user_limit(units_to_bits(self.usage_user_limit, UNIT_MB))
            bar.set_max_value(units_to_bits(self.usage_max_value, UNIT_MB))

    def set_name(self, name=APP_LONG_NAME):
        self.get_top_widget().set_title(name)

    def set_disconnected(self):
        obj = self['connect_button']
        if obj:
            image = gtk.Image()
            image.set_from_file(os.path.join(IMAGES_DIR, 'connect.png'))
            image.show()
            obj.set_icon_widget(image)
            obj.set_label(_("Connect"))
            obj.set_active(False)

        self['upload_alignment'].hide()
        self['download_alignment'].hide()

        self['net_statusbar'].push(1, _('Not connected'))

    def set_connected(self):
        obj = self['connect_button']
        if obj:
            image = gtk.Image()
            image.set_from_file(os.path.join(IMAGES_DIR, 'disconnect.png'))
            image.show()
            obj.set_icon_widget(image)
            obj.set_label(_("Disconnect"))
            obj.set_active(True)

        self['mobile1'].set_sensitive(False)

        self['upload_alignment'].show()
        self['download_alignment'].show()

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
                column.set_attributes(cell, pixbuf = col_usertype)
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
                column = gtk.TreeViewColumn("Editable", cell, text=col_editable)
                column.set_visible(False)
                column.set_sort_column_id(col_editable)
                treeview.append_column(column)

            else: # inbox_tv sent_tv drafts_tv sent_tv
                cell = gtk.CellRendererPixbuf()
                column = gtk.TreeViewColumn(_("Type"))
                column.pack_start(cell)
                column.set_attributes(cell, pixbuf = col_smstype)
                treeview.append_column(column)

                cell = gtk.CellRendererText()
                cell.set_property('editable', False)
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

    def _get_signal_icon(self, rssi):
        if rssi < 10 or rssi > 100:
            return 0

        elif rssi < 25:
            return 25

        elif rssi < 50:
            return 50

        elif rssi < 75:
            return 75

        elif rssi <= 100:
            return 100

    def update_signal_bearer(self, newsignal = None, newmode = None):
        if newsignal:
            self.signal = self._get_signal_icon(newsignal)

        if newmode:
            if newmode in [_('N/A'), _('Radio Disabled')]:
                pass
            elif newmode in [_('GPRS'), _('EDGE')]:
                self.bearer = 'gprs'
            else:
                self.bearer = 'umts'

            obj = self['cell_type_label']
            if obj:
                obj.set_text(newmode)

#            if self.model.is_connected():
#                msg = _('Connected to %s') % newmode
#                self['net_statusbar'].push(1, msg)

        if self.signal == -1:
            image = 'radio-off.png'
        else:
            image = 'signal-%s-%d.png' % (self.bearer, self.signal)

        obj = self['signal_image']
        if obj:
            obj.set_from_file(os.path.join(IMAGES_DIR, image))

    def rssi_changed(self, new_rssi):
        print "rssi_changed: %s" % new_rssi
        self.update_signal_bearer(newsignal = new_rssi)

    def tech_changed(self, new_tech):
        print "tech_changed: %s" % new_tech
        self.update_signal_bearer(newmode = new_tech)

    def operator_changed(self, new_operator):
        print "operator_changed: %s" % new_operator
        obj = self['network_name_label']
        if obj:
            if new_operator in '0':
                obj.set_text('')
            else:
                obj.set_text(new_operator)

    def set_status(self, status):
        print "set_status: %s" % status
#        self['status_label'].set_text(status)

    def set_initialising(self, enable):
        self['connect_button'].set_sensitive(not enable)
#        self['sms_menuitem'].set_sensitive(not enable)
#        self['preferences_menu_item'].set_sensitive(not enable)

    def start_throbber(self):
        pass
#        if self.throbber is None:
#            self.throbber = gtk.Image()
#            self['hbox2'].pack_start(self.throbber, expand=False)
#            self.throbber.set_from_animation(THROBBER)
#            self.throbber.show()

    def stop_throbber(self):
        pass
#        if self.throbber is not None:
#            self.throbber.hide()
#            try:
#                self['hbox2'].remove(self.throbber)
#            except AttributeError:
#                pass
#
#            self.throbber = None

