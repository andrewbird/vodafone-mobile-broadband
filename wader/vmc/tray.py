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
"""Tray icon module"""

__version__ = "$Rev: 1172 $"

import os.path

import gtk

from twisted.internet import reactor

from wader.common import consts

IMG_PATH = os.path.join(consts.IMAGES_DIR, 'VF_logo.png')

try:
    import gtk.StatusIcon
    HAVE_STATUS_ICON = True
except ImportError:
    HAVE_STATUS_ICON = False

def tray_available():
    """Returns True if any kind of systray widget is present"""
    if HAVE_STATUS_ICON:
        return True

    try:
        import egg.trayicon
    except ImportError:
        return False

    return True

class TrayIcon(object):
    """
    I wrap either a gtk.StatusIcon or a egg.trayicon.TrayIcon instance

    I provide a uniform API for two heterogeneous components and perform
    some trickery to show notifications on a HIG-friendly way
    """
    def __init__(self, icon):
        self.icon = icon

    def show(self):
        """Shows the icon"""
        if HAVE_STATUS_ICON:
            self.icon.set_visible(True)
        else:
            self.icon.show_all()

    def hide(self):
        """Hides the icon"""
        if HAVE_STATUS_ICON:
            self.icon.set_visible(False)
        else:
            self.icon.hide_all()

    def visible(self):
        """Returns True if the icon is visible"""
        if HAVE_STATUS_ICON:
            return self.icon.get_visible()
        else:
            return self.icon.get_property('visible')

    def attach_notification(self, notification):
        """
        Attachs C{notification} to the icon

        If we're not visible, we will show ourselves for 5 seconds and will
        hide afterwards
        """
        if HAVE_STATUS_ICON:
            notification.set_property('status-icon', self.icon)
        else:
            notification.attach_to_widget(self.icon)

        if not self.visible():
            self.show()
            reactor.callLater(5, self.hide)

if HAVE_STATUS_ICON:
    def get_tray_icon(show_ide_cb, get_menu_func):
        icon = gtk.status_icon_new_from_file(IMG_PATH)
        icon.set_visible(True)
        def popup_menu_cb(widget, button, time, data = None):
            if button == 3:
                if data:
                    data.show_all()
                    data.popup(None, None, None, 3, time)

        icon.connect('activate', show_ide_cb)
        icon.connect('popup-menu', popup_menu_cb, get_menu_func())
        return TrayIcon(icon)

else:
    def get_tray_icon(show_ide_cb, get_menu_func=None):
        import egg.trayicon
        tray = egg.trayicon.TrayIcon(consts.APP_SHORT_NAME)
        # attach an image
        image = gtk.Image()
        image.set_from_file(IMG_PATH)
        # inside an eventbox
        event_box = gtk.EventBox()
        event_box.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        event_box.connect("button_press_event", show_ide_cb)
        event_box.add(image)
        # add the eventbox to the tray object
        tray.add(event_box)
        tray.show_all()
        return TrayIcon(tray)
