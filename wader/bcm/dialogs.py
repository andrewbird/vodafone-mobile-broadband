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

import gtk
import gobject
import dbus
#from gtkmvc import Controller, Model
from wader.bcm.contrib.gtkmvc import Controller, Model

from wader.bcm.logger import logger
from wader.common.consts import WADER_DIALUP_INTFACE
from wader.bcm.translate import _
from wader.bcm.consts import (APP_ARTISTS, APP_AUTHORS, APP_DOCUMENTERS,
                             GLADE_DIR, APP_VERSION, APP_NAME, APP_URL)
from wader.bcm.views.dialogs import QuestionCheckboxOkCancel


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

    icon = gtk.gdk.pixbuf_new_from_file(os.path.join(GLADE_DIR, 'VF_logo.png'))
    abt.set_icon(icon)
    if gtk.pygtk_version >= (2, 11, 0):
        abt.set_program_name(APP_NAME)
    else:
        abt.set_name(APP_NAME)
    abt.set_version(APP_VERSION)
    abt.set_copyright("Copyright (C) 2006-2010 Vodafone España S.A.\n" +
                      "Copyright (C) 2008-2009 Wader contributors")
    abt.set_authors(APP_AUTHORS)
    abt.set_documenters(APP_DOCUMENTERS)
    abt.set_artists(APP_ARTISTS)
    abt.set_website(APP_URL)
    abt.set_translator_credits(_('translator-credits'))

    abt.set_website_label(APP_URL)
    _license = """
Betavine Connection Manager
Copyright (C) 2006-2010 Vodafone España S.A.
Copyright (C) 2008-2010 Warp Networks, S.L.

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
    from wader.bcm.models.profile import ProfileModel
    from wader.bcm.controllers.profile import ProfileController
    from wader.bcm.views.profile import ProfileView

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


def ask_password_dialog(parent):
    logger.debug("Asking for password")
    return generic_auth_dialog(
            _("Password required"),
            _("Please, insert the password of your connection"),
            parent, regexp=None)


class CheckBoxPopupDialogCtrl(Controller):

    def __init__(self):
        super(CheckBoxPopupDialogCtrl, self).__init__(Model())
        self.checked = False

    def register_view(self, view):
        super(CheckBoxPopupDialogCtrl, self).register_view(view)
        view['checkbutton1'].connect('toggled', self._on_changed)

    def _on_changed(self, widget):
        self.checked = widget.get_active()


def open_dialog_question_checkbox_cancel_ok(parent_view, message, details):
    """
    Opens a dialog with a checkbox aka 'Never ask me this again'

    @return: tuple with two bools, the first is whether the user confirmed
    the action or not, the second is whether the checkbox is toggled
    """
    ctrl = CheckBoxPopupDialogCtrl()
    view = QuestionCheckboxOkCancel(ctrl, message, details)
    view.set_parent_view(parent_view)
    resp = view.run()
    return resp == gtk.RESPONSE_OK, ctrl.checked


def save_csv_file(path=None):
    """Opens a filechooser dialog to choose where to save a csv file"""
    title = _("Save as ...")
    chooser_dialog = gtk.FileChooserDialog(title,
                    action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_SAVE, gtk.RESPONSE_OK))

    chooser_dialog.set_default_response(gtk.RESPONSE_OK)
    filter_ = gtk.FileFilter()
    filter_.set_name(_("Csv files"))
    filter_.add_mime_type("text/xml")
    filter_.add_pattern("*csv")
    chooser_dialog.add_filter(filter_)

    filter_ = gtk.FileFilter()
    filter_.set_name(_("All files"))
    filter_.add_pattern("*")
    chooser_dialog.add_filter(filter_)

    if path:
        chooser_dialog.set_filename(os.path.abspath(path))
    if chooser_dialog.run() == gtk.RESPONSE_OK:
        resp = chooser_dialog.get_filename()
        if os.path.isfile(resp):
            # requests to confirm overwrite:
            overwrite = show_warning_request_cancel_ok(
                          _('Overwrite "%s"?') % os.path.basename(resp),
                          _("""A file with this name already exists.
If you choose to overwrite this file, the contents will be lost."""))
            if not overwrite:
                resp = None
    else:
        resp = None

    chooser_dialog.destroy()
    return resp


def open_import_csv_dialog(path=None):
    """Opens a filechooser dialog to import a csv file"""
    title = _("Import contacts from...")
    chooser_dialog = gtk.FileChooserDialog(title,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))

    chooser_dialog.set_default_response(gtk.RESPONSE_OK)

    filter_ = gtk.FileFilter()
    filter_.set_name(_("Csv files"))
    filter_.add_mime_type("text/xml")
    filter_.add_pattern("*csv")
    chooser_dialog.add_filter(filter_)
    filter_ = gtk.FileFilter()
    filter_.set_name(_("All files"))
    filter_.add_pattern("*")
    chooser_dialog.add_filter(filter_)

    if path:
        chooser_dialog.set_filename(os.path.abspath(path))
    if chooser_dialog.run() == gtk.RESPONSE_OK:
        resp = chooser_dialog.get_filename()
    else:
        resp = None

    chooser_dialog.destroy()
    return resp

#########################################################################

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
