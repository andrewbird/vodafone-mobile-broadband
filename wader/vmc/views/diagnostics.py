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

import os.path

import gtk

from gtkmvc import View
from wader.vmc.consts import GLADE_DIR

class DiagnosticsView(View):
    """View for the main diagnostics window"""
    GLADE_FILE = os.path.join(GLADE_DIR, "diagnostics.glade")

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE,
                      'diagnostics_window', register=False)
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self.get_top_widget().set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        
        
    def set_datacard__info(self, manufacturer,  model,  firmware):
        self['card_manufacturer_label'].set_text(manufacturer)
        self['card_model_label'].set_text(model)
        self['firmware_label'].set_text(firmware)
