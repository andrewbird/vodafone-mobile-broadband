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
"""View for the splash screen"""
__version__ = "$Rev: 1172 $"

import os.path

from wader.vmc import View
import wader.common.consts as consts

PULSE_STEP = .2

class SplashView(View):
    """View for the splash screen"""

    GLADE_FILE = os.path.join(consts.GLADE_DIR, 'splash.glade')

    def __init__(self, ctrl):
        View.__init__(self, ctrl, self.GLADE_FILE, 'splash_window',
                      register=False, domain="VMC")
        ctrl.register_view(self)
        self.setup_view()

    def setup_view(self):
        self['splash_image'].set_from_file(
                   os.path.join(consts.IMAGES_DIR, "splash.png"))
        self.get_top_widget().set_title(consts.APP_LONG_NAME)
        self['splash_progress_bar'].set_pulse_step(PULSE_STEP)
