# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
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
Dialogs for the keyring functionality
"""

import os
import re
import string

import gtk

from gui.translate import _
from gui.consts import GLADE_DIR, APP_NAME

GLADE_FILE = os.path.join(GLADE_DIR, 'keyring.glade')
UI_FILE = os.path.join(GLADE_DIR, 'keyring.ui')

GLADE_AVAILABLE = not hasattr(gtk, 'Builder')
FILE_TO_LOAD = GLADE_FILE if GLADE_AVAILABLE else UI_FILE

if GLADE_AVAILABLE:

    def get_tree(path):
        return gtk.glade.XML(path)

    def get_object(tree, name):
        return tree.get_widget(name)
else:

    def get_tree(path):
        tree = gtk.Builder()
        tree.add_from_file(path)
        return tree

    def get_object(tree, name):
        return tree.get_object(name)


def add_regexp_validation(editable_widget, regexp, notify_parent_cb):
    editable_widget.last_valid_text = editable_widget.get_text()
    validation_re = re.compile(regexp)

    def on_changed_cb(widget):
        text = widget.get_text()
        if validation_re.match(text):
            widget.last_valid_text = text
        else:
            widget.set_text(widget.last_valid_text)

        if notify_parent_cb:
            notify_parent_cb()

    editable_widget.connect('changed', on_changed_cb)


def add_password_validation(editable_widget, notify_parent_cb=None):
    valid_chars = string.printable[:95]
    add_regexp_validation(editable_widget, "^[%s]*$" % valid_chars,
                          notify_parent_cb)


class _KeyringDialog(gtk.Dialog):

    def __init__(self, parent, title, msg):
        flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
        super(_KeyringDialog, self).__init__(title, parent, flags)
        self.cancel_button = self.add_button(gtk.STOCK_CANCEL,
                                             gtk.RESPONSE_REJECT)
        self.ok_button = self.add_button(gtk.STOCK_OK,
                                         gtk.RESPONSE_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.ok_button.grab_default()
        self.ok_button.set_sensitive(False)

        self.tree = get_tree(FILE_TO_LOAD)
        self.text_label = get_object(self.tree, self.widget_name)
        self.text_label.set_text(msg)


class NewKeyringDialog(_KeyringDialog):
    """Dialog for a new keyring"""

    widget_name = 'message_label'

    def __init__(self, parent):
        super(NewKeyringDialog, self).__init__(parent,
                _("Create default keyring"),
                _("The application '%s' wants to store a password, but "
                  "there is no default keyring. To create one, you need "
                  "to choose a password you wish to use for it." % APP_NAME))
        self.cancel_button.destroy()

        pin_panel = get_object(self.tree, 'new_keyring_panel')
        get_object(self.tree, 'new_keyring_window').remove(pin_panel)
        self.vbox.add(pin_panel)

        self.password_entry = get_object(self.tree, 'new_keyring_password')
        #self.password_entry.get_settings().set_long_property(
        #    "gtk-entry-password-hint-timeout", 600, "")
        add_password_validation(self.password_entry, self.check_ok_conditions)

        self.confirm_password_entry = get_object(self.tree,
                                                'new_keyring_password_confirm')
        #self.confirm_password_entry.get_settings().set_long_property(
        #    "gtk-entry-password-hint-timeout", 600, "")
        add_password_validation(self.confirm_password_entry,
                                self.check_ok_conditions)

    def check_ok_conditions(self):
        password = self.password_entry.get_text()
        confirm_password = self.confirm_password_entry.get_text()
        self.ok_button.set_sensitive(password == confirm_password)


class KeyringPasswordDialog(_KeyringDialog):
    """Keyring 'insert password' dialog"""

    widget_name = 'message_label1'

    def __init__(self, parent):
        super(KeyringPasswordDialog, self).__init__(parent,
                _("Unlock keyring"),
                _("The application '%s' wants access to the default "
                  "keyring, but is locked." % APP_NAME))

        pin_panel = get_object(self.tree, 'ask_keyring_password_panel')
        get_object(self.tree, 'ask_keyring_password_window').remove(pin_panel)
        self.vbox.add(pin_panel)

        self.password_entry = get_object(self.tree, 'keyring_password_entry')
        #self.password_entry.get_settings().set_long_property(
        #    "gtk-entry-password-hint-timeout", 600, "")
        add_password_validation(self.password_entry, self.check_ok_conditions)

    def check_ok_conditions(self):
        password = self.password_entry.get_text()
        self.ok_button.set_sensitive(len(password) > 0)
