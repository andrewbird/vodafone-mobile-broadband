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
"""Controller for the splash screen"""

import gtk

from wader.common.shutdown import shutdown_core
from wader.vmc import Controller

class SplashController(Controller):
    """Controller for splash screen"""

    def __init__(self, model):
        super(SplashController, self).__init__(model)

    def register_view(self, view):
        super(SplashController, self).register_view(view)
        view.get_top_widget().set_position(gtk.WIN_POS_CENTER)

    def on_cancel_button_clicked(self, widget):
        shutdown_core()
