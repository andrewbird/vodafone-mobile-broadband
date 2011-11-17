# -*- coding: utf-8 -*-
# Copyright (C) 2009-2010  Vodafone España, S.A.
# Author:  Andrew Bird
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

import gobject
import gtk
from gtk.gdk import WINDOW_TYPE_HINT_SPLASHSCREEN
import os
from gui.consts import GLADE_DIR


class SplashScreen(gtk.Window):

    def __init__(self, parent_view):
        super(SplashScreen, self).__init__(gtk.WINDOW_POPUP)
        self.parent_view = parent_view

        def done(win):
            self.hide()
            self.parent_view.show()

        self.connect('destroy', done)
        self.set_resizable(False)
        self.set_modal(1)
        self.set_position(1)
        self.set_type_hint(WINDOW_TYPE_HINT_SPLASHSCREEN)

        img = gtk.Image()
        img.set_from_file(os.path.join(GLADE_DIR, "splash.png"))
        self.add(img)

    def show_it(self, displaytime):
        gobject.timeout_add(displaytime * 1000,
                            lambda splash: splash.destroy(), self)

        self.show_all()
        self.show_now()

        while gtk.events_pending():
            gtk.main_iteration()
