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
Base classes for Controllers
"""

__version__ = "$Rev: 1172 $"

from wader.vmc import Controller
from vmc.utils.utilities import dict_reverter

TV_DICT = {0 : 'inbox_treeview',
           1 : 'inbox_treeview',
           2 : 'drafts_treeview',
           3 : 'sent_treeview',
           4 : 'contacts_treeview'}

TV_DICT_REV = dict_reverter(TV_DICT)

class WidgetController(Controller):
    """I maintain a list of widgets"""
    def __init__(self, model):
        super(WidgetController, self).__init__(model)
        self._widgets = []

    def hide_widgets(self):
        """Hides all the widgets that we're weeping track of"""
        for widget in self._widgets:
            try:
                widget.close()
            except:
                pass

        self._widgets = []

    def append_widget(self, widget):
        """Appends a widget to C{self._widgets}"""
        self._widgets.append(widget)

