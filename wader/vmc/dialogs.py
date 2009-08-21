# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Authors:  Jaime Soriano, Isaac Clerencia, Pablo Martí
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

import os
import re

import gtk
import gobject
import dbus

from wader.vmc.logger import logger
from wader.common.consts import WADER_DIALUP_INTFACE
from wader.vmc.translate import _
from wader.vmc.consts import (APP_ARTISTS, APP_AUTHORS, APP_DOCUMENTERS,
                             GLADE_DIR, APP_VERSION, APP_NAME, APP_URL)

def show_uri(uri):
    if not hasattr(gtk, 'show_uri'):
        from gnome import url_show
        return url_show(uri)

    return gtk.show_uri(gtk.gdk.Screen(), uri, 0L)

def show_about_dialog():
    abt = gtk.AboutDialog()
    icon = abt.render_icon(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU)
    abt.set_icon(icon)

    gtk.about_dialog_set_url_hook(lambda abt, url: show_uri(url))
    gtk.about_dialog_set_email_hook(lambda d, e: show_uri("mailto:%s" % e))

    icon = gtk.gdk.pixbuf_new_from_file(os.path.join(GLADE_DIR, 'wader.png'))
    abt.set_icon(icon)
    abt.set_program_name(APP_NAME)
    abt.set_version(APP_VERSION)
    abt.set_copyright("Copyright (C) 2008-2009 Wader contributors")
    abt.set_authors(APP_AUTHORS)
    abt.set_documenters(APP_DOCUMENTERS)
    abt.set_artists(APP_ARTISTS)
    abt.set_website(APP_URL)
    abt.set_translator_credits(_('translator-credits'))

    abt.set_website_label(APP_URL)
    _license = """
The Wader project
Copyright (C) 2008-2009  Warp Networks, S.L.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA"""
    abt.set_license(_license)
    return abt


def show_profile_window(main_model, profile=None, imsi=None):
    from wader.gtk.models.profile import ProfileModel
    from wader.gtk.controllers.profile import ProfileController
    from wader.gtk.views.profile import ProfileView

    if profile is not None:
        model = profile
    else:
        model = ProfileModel(main_model, imsi=imsi,
                             device_callable=main_model.device_callable)

    controller = ProfileController(model)
    view = ProfileView(controller)
    view.show()

def make_basic_dialog(title, buttons, stock_image):
    flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT | \
            gtk.DIALOG_NO_SEPARATOR
    dialog = gtk.Dialog(title, flags=flags, buttons=buttons)
    box = gtk.HBox()
    box.add(gtk.image_new_from_stock(stock_image, gtk.ICON_SIZE_DIALOG))
    vbox = gtk.VBox()
    box.add(vbox)

    box.set_spacing(12)
    vbox.set_spacing(6)

    alignment = gtk.Alignment()
    alignment.set_padding(6, 6, 6, 6)
    alignment.add(box)
    dialog.vbox.add(alignment)
    return dialog, vbox

def show_warning_dialog(title, message):
    logger.debug("Warning dialog: %s" % message)

    buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK)
    dialog, box = make_basic_dialog(title, buttons, gtk.STOCK_DIALOG_WARNING)
    box.add(gtk.Label(message))
    dialog.set_default_response(gtk.RESPONSE_OK)

    dialog.show_all()
    ret = dialog.run()
    dialog.destroy()
    return ret

def show_error_dialog(title, message):
    logger.debug("Error dialog: %s" % message)

    buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK)
    dialog, box = make_basic_dialog(title, buttons, gtk.STOCK_DIALOG_ERROR)
    label = gtk.Label(message)
    label.set_width_chars(80)
    label.set_line_wrap(True)
    label.set_justify(gtk.JUSTIFY_FILL)
    box.add(label)
    dialog.set_default_response(gtk.RESPONSE_OK)

    dialog.show_all()
    ret = dialog.run()
    dialog.destroy()
    return ret

def show_warning_request_cancel_ok(title, message):
    logger.debug("Warning request cancel/ok dialog: %s" % message)

    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
               gtk.STOCK_OK, gtk.RESPONSE_OK)
    dialog, box = make_basic_dialog(title, buttons, gtk.STOCK_DIALOG_WARNING)
    box.add(gtk.Label(message))
    dialog.set_default_response(gtk.RESPONSE_OK)

    dialog.show_all()
    ret = dialog.run()
    dialog.destroy()
    return ret == gtk.RESPONSE_OK

def generic_puk_dialog(title, message, parent, puk_regexp=None,
                       pin_regexp=None):
    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
               gtk.STOCK_OK, gtk.RESPONSE_OK)

    dialog, box = make_basic_dialog(title, buttons,
                                    gtk.STOCK_DIALOG_AUTHENTICATION)
    box.add(gtk.Label(message))
    puk_entry = gtk.Entry()
    pin_entry = gtk.Entry()

    pin_entry.set_activates_default(True)

    hbox = gtk.HBox(spacing=6)
    hbox.pack_start(puk_entry)
    hbox.pack_start(pin_entry)

    def enable_ok_button(enable):
        for child in dialog.action_area.get_children():
            if child.get_label() == 'gtk-ok':
                child.set_sensitive(enable)

    def on_puk_changed_cb(_entry, regexp):
        text = _entry.get_text()
        match = regexp.match(text)
        if match is not None:
            pin_entry.grab_focus()

    def on_pin_changed_cb(_entry, regexp):
        text = _entry.get_text()
        match = regexp.match(text)
        enable = True if match is not None else False

        enable_ok_button(enable)

    puk_entry.connect('changed', on_puk_changed_cb, puk_regexp)
    pin_entry.connect('changed', on_pin_changed_cb, pin_regexp)

    box.add(hbox)
    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_transient_for(parent.get_top_widget())
    dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    dialog.show_all()

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        puk = puk_entry.get_text()
        pin = pin_entry.get_text()
        ret = (puk, pin)
    else:
        ret = None

    dialog.destroy()
    dialog = None
    return ret

def generic_auth_dialog(title, message, parent, regexp=None):
    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
               gtk.STOCK_OK, gtk.RESPONSE_OK)

    dialog, box = make_basic_dialog(title, buttons,
                                    gtk.STOCK_DIALOG_AUTHENTICATION)
    box.add(gtk.Label(message))
    entry = gtk.Entry()
    entry.set_activates_default(True)

    def enable_ok_button(enable):
        for child in dialog.action_area.get_children():
            if child.get_label() == 'gtk-ok':
                child.set_sensitive(enable)

    enable_ok_button(False)

    def on_changed_cb(_entry):
        text = _entry.get_text()
        enable = True
        if regexp:
            match = regexp.match(text)
            enable = True if match is not None else False

        enable_ok_button(enable)

    entry.connect('changed', on_changed_cb)
    box.add(entry)
    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_transient_for(parent.get_top_widget())
    dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    dialog.show_all()
    dialog.realize()

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        ret = entry.get_text()
    else:
        ret = None

    dialog.destroy()
    dialog = None
    return ret

def ask_pin_dialog(parent):
    logger.debug("Asking for PIN")
    return generic_auth_dialog(
            _("PIN required"),
            _("Please, insert the PIN of your SIM card"),
            parent, regexp=re.compile('^\d{4,8}$'))

def ask_password_dialog(parent):
    logger.debug("Asking for password")
    return generic_auth_dialog(
            _("Password required"),
            _("Please, insert the password of your connection"),
            parent, regexp=None)

def ask_puk_dialog(parent):
    logger.debug("Asking for PUK")
    return generic_puk_dialog(
            _("PUK required"),
            _("Please, insert the PUK and PIN of your SIM card"),
           parent, puk_regexp=re.compile('^\d{8}$'),
           pin_regexp=re.compile('^\d{4,8}$'))

def ask_puk2_dialog(parent):
    logger.debug("Asking for PUK2")
    return generic_puk_dialog(
            _("PUK2 required"),
            _("Please, insert the PUK2 and PIN of your SIM card"),
            parent, puk_regexp=re.compile('^\d{8}$'),
            pin_regexp=re.compile('^\d{4,8}$'))


PULSE_STEP = .2
MAX_WIDTH = 260
MIN_WIDTH = 150
SIZE_PER_CHAR = 15

class ActivityProgressBar(object):
    """
    I am an activity progress bar

    useful for situation where we don't know how long will
    take an IO operation to complete
    """
    def __init__(self, title, parent, initnow=False, disable_cancel=False):
        self.tree = None
        self.window = None
        self.parent = parent
        self.progress_bar = None
        self.cancel_button = None
        self.loop = None
        self.cancel_func = None
        self.cancel_args = None
        self.cancel_kwds = None

        self.disconnect_sm = None
        self.exit = None

        self._build_gui(title, parent, disable_cancel)
        if initnow:
            self.init()

    def _build_gui(self, title, parent, disable_cancel):
        glade_file = os.path.join(GLADE_DIR, 'misc.glade')
        self.tree = gtk.glade.XML(glade_file)
        self.window = self.tree.get_widget('progress_window')
        self.cancel_button = self.tree.get_widget('cancel_button')
        self.progress_bar = self.tree.get_widget('progressbar')

        self.window.set_transient_for(parent.view.get_top_widget())
        self.window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.window.set_resizable(False)
        self.window.set_deletable(False)
        self.window.set_modal(True)

        width = max(MIN_WIDTH, min(len(title) * SIZE_PER_CHAR, MAX_WIDTH))
        self.window.set_size_request(width, -1)
        self.window.set_title(title)
        self.window.connect('delete_event', self.on_delete_event)
        self.cancel_button.connect('clicked', self.on_cancel_button_clicked)

        self.exit = None

    def init(self):
        self.window.show_all()
        gobject.timeout_add(200, self.pulse_update)
        self.connect_to_signals()

    def connect_to_signals(self):
        bus = dbus.SystemBus()
        self.disconnect_sm = bus.add_signal_receiver(
                                self.disconnected_cb,
                                "Disconnected",
                                WADER_DIALUP_INTFACE)

    def disconnected_cb(self):
        """
        org.freedesktop.ModemManager.Dial.Disconnect signal callback
        """
        logger.info("Disconnected received")
        button = self.parent.view['connect_button']
        # block and unblock handler while toggling connect button
        button.handler_block(self.parent.cid)
        button.set_active(False)
        button.handler_unblock(self.parent.cid)

        self.close()

    def pulse_update(self):
        if self.exit:
            return False
        else:
            self.progress_bar.pulse()
            return True

    def close(self):
        self.window.destroy()
        self.exit = True
        if self.disconnect_sm:
            # do not listen for o.fd.ModemManager.Dialer.Disconnect signals
            self.disconnect_sm.remove()

    def on_delete_event(self, *args):
        return True

    def on_cancel_button_clicked(self, widget):
        if self.cancel_func:
            self.cancel_func(*self.cancel_args, **self.cancel_kwds)

        self.close()

    def set_cancel_cb(self, func, *args, **kwds):
        self.cancel_func = func
        self.cancel_args = args
        self.cancel_kwds = kwds
