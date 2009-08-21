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
Pynotify-related utilities and methods
"""
__version__ = "$Rev: 1172 $"

import os
from textwrap import fill

import gtk
try:
    import pynotify
except ImportError:
    pass

import wader.common.consts as consts

MAX_WIDTH = 30

def check_if_initted():
    """Initializes pynotify in case it wasn't initted"""
    if not pynotify.is_initted():
        pynotify.init(consts.APP_SHORT_NAME)

def show_normal_notification_posix(widget, title, message, error=False,
                                   expires=True):
    """
    Attach a notification to C{widget}

    Notification with C{title} as title and C{message} as message, if
    error is True, show an error notification
    """
    print "check this out, there's a new notification mechanism in wader"

    check_if_initted()

    wrapped_text = fill(message, MAX_WIDTH)
    notification = pynotify.Notification(title, wrapped_text)
    notification.set_urgency(pynotify.URGENCY_NORMAL)

    if error:
        helper = gtk.Button()
        icon = helper.render_icon(gtk.STOCK_DIALOG_ERROR,
                                  gtk.ICON_SIZE_DIALOG)
        notification.set_icon_from_pixbuf(icon)

    if not expires:
        notification.set_timeout(pynotify.EXPIRES_NEVER)

    widget.attach_notification(notification)
    notification.show()
    return notification

def show_error_notification_posix(widget, title, message, expires=True):
    """
    Attach an error notification to C{widget}

    See L{show_normal_notification}
    """
    return show_normal_notification(widget, title, message, error=True,
                                    expires=True)

def show_normal_notification_win(widget, title, message, error=False):
    pass

def show_error_notification_win(widget, title, message):
    pass

if os.name == 'posix':
    show_normal_notification = show_normal_notification_posix
    show_error_notification = show_error_notification_posix
elif os.name == 'nt':
    show_normal_notification = show_normal_notification_win
    show_error_notification = show_error_notification_win
