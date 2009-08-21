# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author: Pablo Marti
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

import gtk
import pynotify

from wader.vmc.consts import APP_NAME

def new_notification(status_icon, title, text="", stock=None,
                     actions=None, category=None):

    if not pynotify.init(APP_NAME):
        raise RuntimeError("Can not initialize pynotify")

    n = pynotify.Notification(title, text)

    if category:
        n.set_category(category)

    if actions:
        for _type, action_text, callback in actions:
            n.add_action(_type, action_text, callback)

    if stock:
        icon = gtk.Button().render_icon(stock, gtk.ICON_SIZE_DIALOG)
        n.set_icon_from_pixbuf(icon)

    n.set_property('status-icon', status_icon)
    return n

