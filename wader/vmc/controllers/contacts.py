# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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
"""Controllers for both add_contact and search_contact dialogs"""

import gtk

from wader.vmc.models.contacts import ContactsStoreModel

from wader.vmc.phonebook import get_phonebook, Contact
from wader.vmc.translate import _

from gtkmvc import Controller
from wader.vmc import dialogs

from wader.vmc.contrib.ValidatedEntry import (ValidatedEntry, v_phone,
                                              v_ucs2_name)


class AddContactController(Controller):
    """Controller for the add contact dialog"""

    def __init__(self, model, parent_ctrl):
        super(AddContactController, self).__init__(model)
        self.parent_ctrl = parent_ctrl
        self.name_entry = ValidatedEntry(v_ucs2_name)
        self.number_entry = ValidatedEntry(v_phone)

    def register_view(self, view):
        super(AddContactController, self).register_view(view)
        if not self.model.device:
            self.view['mobile_radio_button'].set_sensitive(False)
            self.view['computer_radio_button'].set_active(True)

    def on_add_contact_ok_button_clicked(self, widget):
        if not self.name_entry.isvalid() or not self.number_entry.isvalid():
            return

        name = self.name_entry.get_text()
        number = self.number_entry.get_text()
        save_in_sim = self.view['mobile_radio_button'].get_active()

        phonebook = get_phonebook(self.parent_ctrl.model.device)
        contact = Contact(name, number)

        def add_callback(contact):
            # add it to the treeview model
            model = self.parent_ctrl.view['contacts_treeview'].get_model()
            model.add_contact(contact)
            self._hide_me()

        #d = phonebook.add_contact(contact, sim=save_in_sim)
        #d.addCallback(add_callback)
        new_contact = phonebook.add_contact(contact, sim=save_in_sim)
        add_callback(new_contact)

    def on_add_contact_cancel_button_clicked(self, widget):
        self._hide_me()

    def _hide_me(self):
        self.view.hide()
        self.model.unregister_observer(self)


class SearchContactController(Controller):
    """Controller for the search contact interface"""

    def __init__(self, model, parent_ctrl):
        super(SearchContactController, self).__init__(model)
        self.parent_ctrl = parent_ctrl

    def on_search_cancel_button_clicked(self, widget):
        pass

    def on_search_find_button_clicked(self, widget):
        pattern = self.view['search_entry'].get_text()
        phonebook = get_phonebook(self.parent_ctrl.model.device)

        def find_contact_cb(contacts):
            if not contacts:
                dialogs.show_warning_dialog(_('No contact found'),
                            _('No contact with the name %s found') % pattern)
                return

            treeview = self.parent_ctrl.view['contacts_treeview']
            model = treeview.get_model()
            # get the path
            path = [str(i) for i, row in enumerate(model)
                        if row[3] in contacts]
            # unselect
            sel = treeview.get_selection()
            sel.unselect_all()
            for elem in path:
                # and set the new selection
                sel.select_path(elem)

        #phonebook.find_contact(pattern).addCallback(find_contact_cb)
        clist = phonebook.find_contact(pattern)
        find_contact_cb(clist)


class ContactsListController(Controller):
    """Controller for the contacts list"""

    def __init__(self, model, parent_ctrl):
        super(ContactsListController, self).__init__(model)
        self.parent_ctrl = parent_ctrl

    def register_view(self, view):
        super(ContactsListController, self).register_view(view)
        self._position_and_show()
        self._setup_view()
        self._fill_treeview()

    def _position_and_show(self):
        window = self.view.get_top_widget()
        parent_window = self.parent_ctrl.view.get_top_widget()
        width, height = parent_window.get_size()
        x, y = parent_window.get_position()
        reqx = x + width + 10
        window.move(reqx, y)

        self.view.show()

    def _setup_view(self):
        treeview = self.view['treeview1']
        col_type, col_name, col_number, col_pyobj, col_editable = range(5)
        treeview.set_model(ContactsStoreModel())

        treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        treeview.connect('row-activated', self._row_activated_handler)

        cell = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(_("Type"))
        column.pack_start(cell)
        column.set_attributes(cell, pixbuf=col_type)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Name"), cell, text=col_name)
        column.set_resizable(True)
        column.set_sort_column_id(col_name)
        cell.set_property('editable', False)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Number"), cell, text=col_number)
        column.set_resizable(True)
        column.set_sort_column_id(col_number)
        cell.set_property('editable', False)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("IntId", cell, text=col_pyobj)
        column.set_visible(False)
        column.set_sort_column_id(col_pyobj)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Editable", cell, text=col_editable)
        column.set_visible(False)
        column.set_sort_column_id(col_editable)
        treeview.append_column(column)

        # make add contact insensitive until a row has been selected
        self.view['add_button'].set_sensitive(False)

    def _fill_treeview(self):
        _model = self.view['treeview1'].get_model()
        phonebook = get_phonebook(self.parent_ctrl.parent_ctrl.model.device)
        contacts = phonebook.get_contacts()
        _model.add_contacts(contacts)

    def _row_activated_handler(self, treeview, path, col):
        model, selected = treeview.get_selection().get_selected_rows()
        if not selected or len(selected) > 1:
            return

        _iter = model.get_iter(selected[0])
        number = model.get_value(_iter, 2)
        current_numbers = self.parent_ctrl.get_numbers_list()
        self.parent_ctrl.set_entry_text('')
        if not current_numbers:
            self.parent_ctrl.set_entry_text(number)
        else:
            current_numbers.append(number)
            self.parent_ctrl.set_entry_text(','.join(current_numbers))

        self.model.unregister_observer(self)
        self.view.hide()

    def on_add_button_clicked(self, widget):
        treeview = self.view['treeview1']
        # get selected rows
        selection = treeview.get_selection()
        model, selected = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in selected]
        numbers = []
        for _iter in iters:
            numbers.append(model.get_value(_iter, 2)) # 2 == number in model
        # set the text in the parent's text entry
        numberstext = ','.join(numbers)
        self.parent_ctrl.set_entry_text(numberstext)
        self.model.unregister_observer(self)
        self.view.hide()

    def on_cancel_button_clicked(self, widget):
        self.model.unregister_observer(self)
        self.view.hide()

    def on_treeview1_cursor_changed(self, treeview):
        model, selected = treeview.get_selection().get_selected_rows()
        if len(selected):
            self.view['add_button'].set_sensitive(True)
