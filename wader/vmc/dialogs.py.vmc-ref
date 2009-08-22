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
"""Some utilities for displaying dialogs"""
__version__ = "$Rev: 1172 $"

import os.path
from textwrap import fill

import gtk
from gnome import url_show

from twisted.internet import reactor, task

import vmc.common.consts as consts
from vmc.common.encoding import _
from vmc.gtk import Controller, Model
from vmc.gtk.views.initialconf import DeviceList
import vmc.gtk.views.dialogs as vdialogs

class PopupDialogCtrl(Controller):
    """Base controller class for popup dialogs"""
    
    def __init__(self):
        super(PopupDialogCtrl, self).__init__(Model())

class CheckBoxPopupDialogCtrl(Controller):
    def __init__(self):
        super(CheckBoxPopupDialogCtrl, self).__init__(Model())
        self.checked = False
    
    def register_view(self, view):
        super(CheckBoxPopupDialogCtrl, self).register_view(view)
        view['checkbutton1'].connect('toggled', self._on_changed)
    
    def _on_changed(self, widget):
        self.checked = widget.get_active()

def open_message_dialog(message, details):
    """Shows a standard message dialog"""
    ctrl = PopupDialogCtrl()
    view = vdialogs.DialogMessage(ctrl, message, details)
    view.run()

def open_warning_dialog(message, details):
    """Shows a warning message dialog"""
    ctrl = PopupDialogCtrl()
    view = vdialogs.WarningMessage(ctrl, message, details)
    view.run()
    
def open_warning_request_cancel_ok(message, details):
    """Returns True if the user confirmed the request, False otherwise"""
    ctrl = PopupDialogCtrl()
    view = vdialogs.WarningRequestOkCancel(ctrl, message, details)
    resp = view.run()
    return resp == gtk.RESPONSE_OK

def open_confirm_action_dialog(action_text, message, details):
    """Returns True if the user confirmed the action, False otherwise"""
    ctrl = PopupDialogCtrl()
    view = vdialogs.QuestionConfirmAction(ctrl, action_text, message, details)
    resp = view.run()
    return resp == gtk.RESPONSE_OK

def open_dialog_question_checkbox_cancel_ok(parent_view, message, details):
    """
    Opens a dialog with a checkbox aka 'Never ask me this again'
    
    @return: tuple with two bools, the first is whether the user confirmed
    the action or not, the second is whether the checkbox is toggled
    """
    ctrl = CheckBoxPopupDialogCtrl()
    view = vdialogs.QuestionCheckboxOkCancel(ctrl, message, details)
    view.set_parent_view(parent_view)
    resp = view.run()
    return resp == gtk.RESPONSE_OK, ctrl.checked

def open_import_csv_dialog(path=None):
    """Opens a filechooser dialog to import a csv file"""
    title = _("Import contacts from...")
    chooser_dialog = gtk.FileChooserDialog(title,
                    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
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

def save_standard_file(path=None):
    """Opens a filechooser dialog to choose where to save a file"""
    title = _("Save as ...")
    chooser_dialog = gtk.FileChooserDialog(title,
                    action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                               gtk.STOCK_SAVE, gtk.RESPONSE_OK))

    chooser_dialog.set_default_response(gtk.RESPONSE_OK)

    filter_ = gtk.FileFilter()
    filter_.set_name(_("All files"))
    filter_.add_pattern("*")
    chooser_dialog.add_filter(filter_)

    if path:
        chooser_dialog.set_filename(path)
    if chooser_dialog.run() == gtk.RESPONSE_OK:
        resp = chooser_dialog.get_filename()
        if os.path.isfile(resp):
            # requests to confirm overwrite:
            overwrite = open_confirm_action_dialog(_("Overwrite"),
                          _('Overwrite "%s"?') % os.path.basename(resp),
                          _("""A file with this name already exists.
If you choose to overwrite this file, the contents will be lost."""))
            if not overwrite:
                resp = None
    else:
        resp = None

    chooser_dialog.destroy()
    return resp

def save_csv_file(path=None):
    """Opens a filechooser dialog to choose where to save a csv file"""
    title = _("Save as ...")
    chooser_dialog = gtk.FileChooserDialog(title,
                    action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
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
            overwrite = open_confirm_action_dialog(_("Overwrite"),
                          _('Overwrite "%s"?') % os.path.basename(resp),
                          _("""A file with this name already exists.
If you choose to overwrite this file, the contents will be lost."""))
            if not overwrite:
                resp = None
    else:
        resp = None

    chooser_dialog.destroy()
    return resp

def get_device_treeview(device_list, callback, parent_view):
    window = gtk.Window()
    window.set_transient_for(parent_view.get_top_widget())
    window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    window.set_title(_('Device List'))
    window.set_size_request(width=400, height=300)
    sw = gtk.ScrolledWindow()
    sw.add(DeviceList(device_list, callback, window))
    window.add(sw)
    window.show_all()

def get_about_dialog():
    """Returns an AboutDialog with all the necessary info"""
    
    _MAX_WIDTH = 20
    wrapped_name = fill(consts.APP_LONG_NAME, _MAX_WIDTH)
    
    abt = gtk.AboutDialog()
    
    # attach an icon
    icon = abt.render_icon(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU)
    abt.set_icon(icon)
    
    filepath = os.path.join(consts.IMAGES_DIR, 'VF_logo.png')
    logo = gtk.gdk.pixbuf_new_from_file(filepath)
    
    
    abt.set_logo(logo)
    gtk.about_dialog_set_url_hook(lambda abt, url: url_show(url))
    gtk.about_dialog_set_email_hook(lambda d, e: url_show("mailto:%s" % e))
    
    if gtk.pygtk_version >= (2, 11, 0):
        abt.set_program_name(wrapped_name)
    else:
        abt.set_name(wrapped_name)
    
    abt.set_version(consts.APP_VERSION)
    abt.set_copyright(_('Vodafone Spain S.A.'))
    abt.set_authors(consts.APP_AUTHORS)
    abt.set_documenters(consts.APP_DOCUMENTERS)
    abt.set_artists(consts.APP_ARTISTS)
    abt.set_website(consts.APP_URL)
    abt.set_website_label('/'.join(consts.APP_URL.split('/')[0:3] + ['...']))
    
    trans_credits = _('translated to $LANG by $translater')
    # only enable them when necessary
    if trans_credits != 'translated to $LANG by $translater':
        abt.set_translator_credits(trans_credits)
    
    _license = """
Vodafone Mobile Connect Card driver for Linux
Copyright (C) 2006-2007 Vodafone España S.A.

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

PULSE_STEP = .2
MAX_WIDTH = 260
MIN_WIDTH = 150
SIZE_PER_CHAR = 15

class ActivityProgressBar(object):
    """
    I am an activity progress bar
    
    useful for situation where we don't beforehand how long will take an IO
    operation to complete
    """
    def __init__(self, title, parent, initnow=False, disable_cancel=False):
        self.window = None
        self.vbox = None
        self.bbox = None
        self.progress_bar = None
        self.cancel_button = None
        self.loop = None
        self.default_func = None
        self.default_args = None
        self.default_call = None
        self.cancel_func = None
        self.cancel_args = None
        
        self._build_gui(title, parent, disable_cancel)
        if initnow:
            self.init()
    
    def _build_gui(self, title, parent, disable_cancel):
        self.window = gtk.Window()
        self.window.set_transient_for(parent.view.get_top_widget())
        self.window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.window.set_resizable(False)
        self.window.set_modal(True)
        
        width = max(MIN_WIDTH, min(len(title) * SIZE_PER_CHAR, MAX_WIDTH))
        self.window.set_size_request(width, -1)
        self.window.set_title(title)
        self.window.set_border_width(0)
        
        self.vbox = gtk.VBox()
        
        self.progress_bar = gtk.ProgressBar()
        self.progress_bar.set_pulse_step(PULSE_STEP)
        
        self.vbox.pack_start(self.progress_bar)
        
        self.bbox = gtk.HButtonBox()
        self.bbox.set_layout(gtk.BUTTONBOX_END)
        self.cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
        if disable_cancel:
            self.cancel_button.set_sensitive(False)
        
        self.bbox.add(self.cancel_button)
        
        self.vbox.pack_end(self.bbox, False, False)
        self.window.add(self.vbox)
        
        self.loop = None
    
        self.cancel_button.connect('clicked', self.on_cancel_button_clicked)
        
    def init(self):
        self.progress_bar.show_all()
        self.bbox.show_all()
        self.loop = task.LoopingCall(self.progress_bar.pulse)
        self.loop.start(0.2, True)
        self.window.show_all()
    
    def close(self):
        try:
            self.loop.stop()
        except:
            pass
        self.window.destroy()
    
    def on_cancel_button_clicked(self, widget):
        if self.default_call:
            if self.default_call.active:
                self.default_call.cancel()
        
        if self.cancel_func:
            self.cancel_func(*self.cancel_args)
        
        self.close()
    
    def set_default_cb(self, delay, func, *args):
        self.default_func = func
        self.default_args = args
        def execute_and_close():
            self.default_func(*self.default_args)
            self.close()
        
        self.default_call = reactor.callLater(delay, execute_and_close)
    
    def set_cancel_cb(self, func, *args):
        self.cancel_func = func
        self.cancel_args = args
