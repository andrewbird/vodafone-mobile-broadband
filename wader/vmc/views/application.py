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
Views for the main window and the about window
"""
__version__ = "$Rev: 1172 $"

import time
import os.path

import gtk
import cairo

import wader.common.consts as consts
from wader.common.encoding import _
from wader.common.config import config

from wader.vmc import View
from wader.vmc.images import THROBBER
from wader.vmc.controllers.base import TV_DICT
from wader.vmc.models.sms import SMSStoreModel
from wader.vmc.models.contacts import ContactsStoreModel

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


UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB = xrange(4)
UNIT_REPR = {
    UNIT_B:  _("B"),
    UNIT_KB: _("KB"),
    UNIT_MB: _("MB"),
    UNIT_GB: _("GB"),
}

def units_to_bits(value, units):
    return value * 8 * (2 ** (units * 10))

def bits_to_units(bits, units):
    bytes = (bits / 8)
    return float(bytes) / (2 ** (units * 10))

def repr_usage(bits, units=None, round=lambda x: int(x)):
    if not units:
        if bits == 0:
            units = UNIT_B
        else:
            units = UNIT_GB
            for u in [UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB]:
                btu =  bits_to_units(bits, u)
                if btu >= 1 and btu < 10:
                    units = u -1
                    break
                elif btu >= 10 and btu < 1024:
                    units = u
                    break
    while bits > 0 and bits_to_units(bits, units) < 1:
        units -= 1
    return "%d%s" % (round(bits_to_units(bits, units)), UNIT_REPR[units])


class StatsBar(gtk.DrawingArea):

    def __init__(self, label="", value=0, min_value=0,
                    max_value=10, units=UNIT_MB, user_limit=0):
        super(StatsBar, self).__init__()
        self.supports_alpha = False

        #value in bits
        self.value = value
        self.units = units
        #min and max values in self.units
        self.min_value = units_to_bits(min_value, units)
        self.max_value = units_to_bits(max_value, units)
        self.user_limit = units_to_bits(user_limit, units)

        self.connect('expose-event', self.on_expose)
        self.connect('screen-changed', self.on_screen_changed)

    @classmethod
    def init_array(cls, labels, *args, **kwargs):
        """
        This method makes an array of n identical StatsBars
        """
        bars = []
        for label in labels:
            bar = cls(*((label,) + args), **kwargs)
            bars.append(bar)
        return bars

    def on_screen_changed(self, widget, old_screen=None):
        # To check if the display supports alpha channels, get the colormap
        screen = widget.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            self.supports_alpha = False
        else:
            self.supports_alpha = True

        # Now we have a colormap appropriate for the screen, use it
        widget.set_colormap(colormap)

        return False

    def on_expose(self, widget, event):
        if not widget.window:
            return
        cr = widget.window.cairo_create()

        if self.supports_alpha:
        #if 0:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.0) # Transparent
        else:
            cr.set_source_rgb(1.0, 1.0, 1.0) # Opaque white

        # Draw the background
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        x, y, width, height = widget.get_allocation()
        cr.set_source_rgba(.8, 0.8, 0.8, 0.4)

        cr.rectangle(1.0, 1.0, width - 1.0, height - 1.0)
        # Draw a rectangle (and fill background)
        cr.fill()
        #cr.stroke()

        inner_width = width * .75
        self.draw_limits(cr, inner_width, height)
        self.draw_usage(cr, inner_width, height)
        # Draw inner rectangle
        cr.set_line_width(.8)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.rectangle(0, 0, inner_width, height)
        cr.stroke()
        # Draw outer rectangle
        cr.set_line_width(1.0)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

        return False

    def draw_limits(self, cr, inner_width, height):
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.set_line_width(.1)
        step = float(height) / bits_to_units(self.max_value, self.units)
        frange = lambda a, b, step : [
                                x * step for x in xrange(a,int(b*(1/step)))]
        for i in frange(0, height + step, step):
            cr.move_to(inner_width - 5, height - i)
            cr.line_to(inner_width - 15, height - i)
            cr.stroke()

        # Draw limits
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.select_font_face("Verdana",
                            cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

        #font_size = height * .022
        #cr.set_font_size(font_size)

        # upper limit
        cr.move_to(inner_width + 4, height * .03)
        cr.show_text(repr_usage(self.max_value, self.units))
        # upper mid limit
        cr.move_to(inner_width + 4, height * .25)
        cr.show_text(repr_usage(self.max_value * .75, self.units))
        # mid limit
        cr.move_to(inner_width + 4, height * .5)
        cr.show_text(repr_usage(self.max_value * .5, self.units))
        # down mid limit
        cr.move_to(inner_width + 4, height * .75)
        cr.show_text(repr_usage(self.max_value * .25, self.units))
        # down limit (0)
        cr.move_to(inner_width + 4, height * .99)
        cr.show_text(repr_usage(0, self.units))

    def draw_usage(self, cr, inner_width, height):
        threshold = self._fraction()
        usage_height = height - (threshold * height)
        #linear = cairo.LinearGradient(0.85, 0.85, 0.85, 0.65)
        #linear.add_color_stop_rgba(.9,  0.9, 0.9, 0.9, 0.5)
        cr.set_source_rgba(0.7, 0.7, 0.7, 0.9)
        cr.rectangle(5, usage_height, inner_width-10, height)
        cr.fill()

        if self.user_limit and self.value > self.user_limit:
            limit = self._fraction(self.value - self.user_limit)
            limit = limit * height
            cr.set_source_rgba(5.0, 0, 0, 0.5)
            cr.rectangle(5, usage_height, inner_width-10, limit)
            cr.fill()

    def _fraction(self, value=None):
        if not value:
            value = self.value
        value = float(value - self.min_value)
        max_value = self.max_value - self.min_value
        return value / max_value

    def update(self):
        assert self.max_value > self.value
        self.emit('expose-event', gtk.gdk.Event(gtk.gdk.EXPOSE))
        self.queue_draw()

    def set_value(self, value):
        if value == self.value: return
        if value >= self.max_value:
            self.max_value = 1.25 * value
        self.value = value
        self.update()

    def set_max_value(self, max_value):
        if max_value == self.max_value: return
        self.max_value = max_value
        if self.value >= self.max_value:
            self.max_value = 1.25 * self.value
        self.update()

    def set_user_limit(self, user_limit):
        if user_limit == self.user_limit: return
        self.user_limit = user_limit
        self.update()


class ApplicationView(View):
    """Main view for application"""

    def __init__(self, ctrl):
        if gtk.gdk.screen_height() < 600:
            height = 420
            GLADE_FILE = os.path.join(consts.GLADE_DIR, "VMC-reduced.glade")
        else:
            height = WIN_HEIGHT
            GLADE_FILE = os.path.join(consts.GLADE_DIR, "VMC.glade")

        super(ApplicationView, self).__init__(ctrl, GLADE_FILE,
            'main_window', register=False, domain="VMC")

        #Usage statistics
        self.usage_user_limit = int(config.get('preferences', 'traffic_threshold'))
        self.usage_max_value = int(config.get('preferences', 'max_traffic'))
        self.usage_units = UNIT_KB
        self.usage_bars = None

        self.setup_view(height)
        ctrl.register_view(self)
        self.throbber = None
        ctrl.update_usage_view()
        self.setup_treeview(ctrl)

    def setup_view(self,height):
        self.set_name()
        window = self.get_top_widget()
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_size_request(width=WIN_WIDTH, height=height)
        self._setup_usage_view()

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
        self['vbox17'].hide()
        self['contacts_menubar'].hide()

    def set_usage_value(self, widget, value):
        if isinstance(value, int):
            self[widget].set_text(repr_usage(value))
        else:
            self[widget].set_text(str(value))

    def set_usage_bar_value(self, bar, value):
        bar = self.usage_bars[bar]
        bar.set_value(value)

    def update_bars_user_limit(self):
        self.usage_user_limit = int(config.get('preferences', 'traffic_threshold'))
        self.usage_max_value = int(config.get('preferences', 'max_traffic'))
        for bar in self.usage_bars.values():
            bar.set_user_limit(units_to_bits(self.usage_user_limit, UNIT_MB))
            bar.set_max_value(units_to_bits(self.usage_max_value, UNIT_MB))

    def set_name(self, name=consts.APP_LONG_NAME):
        self.get_top_widget().set_title(name)

    def set_disconnected(self):
        image = gtk.Image()
        image.set_from_file(os.path.join(consts.IMAGES_DIR, 'connect.png'))
        image.show()
        self['connect_button'].set_icon_widget(image)
        self['connect_button'].set_label(_("Connect"))
        self['connect_button'].set_active(False)

        self['upload_alignment'].hide()
        self['download_alignment'].hide()

        self['net_statusbar'].push(1, _('Not connected'))

    def set_connected(self):
        image = gtk.Image()
        image.set_from_file(os.path.join(consts.IMAGES_DIR, 'disconnect.png'))
        image.show()

        self['connect_button'].set_icon_widget(image)
        self['connect_button'].set_label(_("Disconnect"))
        self['connect_button'].set_active(True)

        self['mobile1'].set_sensitive(False)

        self['upload_alignment'].show()
        self['download_alignment'].show()

    def set_no_device_present(self):
        for widget in WIDGETS_TO_HIDE:
            self[widget].set_sensitive(False)

        self.set_name(consts.APP_LONG_NAME + ' / ' + _('No device present'))

        self['cell_type_label'].set_text(_('N/A'))
        self['network_name_label'].set_text(_('N/A'))

    def set_device_present(self, ignored=None):
        for widget in WIDGETS_TO_SHOW:
            self[widget].set_sensitive(True)

        self.set_name()

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
                model = SMSStoreModel(ctrl.model.get_sconn)

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
                        cell.set_property('text',
                                    time.strftime("%c", datetime.timetuple()))
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

    def start_throbber(self):
        if self.throbber:
            return

        self.throbber = gtk.Image()
        self['throbber_hbox'].pack_start(self.throbber, expand=False)
        self.throbber.set_from_animation(THROBBER)
        self.throbber.show()

    def stop_throbber(self):
        self.throbber.hide()
        self.throbber = None

