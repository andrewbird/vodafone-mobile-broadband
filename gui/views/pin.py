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
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""View for the PIN window"""

import os.path

#from gtkmvc import View
from gui.contrib.gtkmvc import View

from gui.consts import GLADE_DIR, IMAGES_DIR
from gui.translate import _


class PinModifyView(View):
    """View for the PIN modify window"""

    GLADE_FILE = os.path.join(GLADE_DIR, "pin.glade")

    def __init__(self, ctrl):
        super(PinModifyView, self).__init__(ctrl, self.GLADE_FILE,
                'pin_modify_window', register=True, domain='vodafone-mobile-broadband')


class PinEnableView(View):
    """View for the ask PIN dialog"""

    GLADE_FILE = os.path.join(GLADE_DIR, "pin.glade")

    def __init__(self, ctrl):
        super(PinEnableView, self).__init__(ctrl, self.GLADE_FILE,
            'ask_pin_window', register=False, domain='vodafone-mobile-broadband')
        self.setup_view()
        ctrl.register_view(self)

    def setup_view(self):
        self['gnomekeyring_checkbutton'].set_active(False)


class AskPINView(View):
    """View for the ask PIN dialog"""

    GLADE_FILE = os.path.join(GLADE_DIR, "pin.glade")

    def __init__(self, ctrl):
        super(AskPINView, self).__init__(ctrl, self.GLADE_FILE,
            'ask_pin_window', register=False, domain='vodafone-mobile-broadband')
        ctrl.register_view(self)

    def get_keyring_checkbox_active(self):
        return self['gnomekeyring_checkbutton'].get_active()

    def set_keyring_checkbox_active(self, active):
        self['gnomekeyring_checkbutton'].set_active(active)

    def set_keyring_checkbox_sensitive(self, sensitive):
        self['gnomekeyring_checkbutton'].set_sensitive(sensitive)
        if not sensitive:
            details = _("To use this feature you need the gnomekeyring module")
            self['gnomekeyring_checkbutton'].set_tooltip_text(details)


class AskPUKView(View):
    """View for the ask PUK/PUK2 dialog"""

    GLADE_FILE = os.path.join(GLADE_DIR, "pin.glade")
    IMAGE_FILE = os.path.join(IMAGES_DIR, "sim-puk-lock.png")

    def __init__(self, ctrl):
        super(AskPUKView, self).__init__(ctrl, self.GLADE_FILE,
            'ask_puk_window', register=True, domain='vodafone-mobile-broadband')

    def set_puk_view(self):
        msg = _("""
In order to unlock your SIM, we need your
PIN and PUK codes""")
        self['message_label'].set_text(msg)
        self['puk_dialog_image'].set_from_file(self.IMAGE_FILE)

    def set_puk2_view(self):
        msg = _("""
In order to unlock your SIM, we need your
PIN and PUK2 codes""")
        self['message_label'].set_text(msg)
        self['puk_label'].set_text('PUK2')
