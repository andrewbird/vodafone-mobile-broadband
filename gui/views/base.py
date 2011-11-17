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
"""Controllers for the main window and the about dialog"""

from gui import View


class BaseDialogView(View):
    """View from which all dialogs should inherit from"""

    GLADE_FILE = None

    def __init__(self, ctrl, *args, **kwds):
        super(BaseDialogView, self).__init__(ctrl,
                                             self.GLADE_FILE, *args, **kwds)

    def run(self):
        widget = self.get_top_widget()
        res = widget.run()
        widget.destroy()
        return res
