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
"""Dialogs views"""

import os.path

from gtkmvc import View
from wader.vmc.consts import GLADE_DIR

def clear_s(s):
    return s.replace('\n', ' ')


class CheckBoxDialogView(View):
    """This is the base class for dialogs with a checkbox"""
    GLADE_FILE = os.path.join(GLADE_DIR, "dialogs.glade")

    def __init__(self, ctrl, top_widget):
        View.__init__(self, ctrl, self.GLADE_FILE, top_widget)

    def run(self):
        resp = self.get_top_widget().run()
        self.get_top_widget().destroy()
        return resp


class QuestionCheckboxOkCancel(CheckBoxDialogView):
    def __init__(self, ctrl, message, details):
        CheckBoxDialogView.__init__(self, ctrl,
                                    "dialog_question_checkbox_cancel_ok")
        self['title_label'].set_markup("<big><b>%s</b></big>" % message)
        self['message_label'].set_markup("<b>%s</b>" % clear_s(details))

#class DialogView(View):
#    """This is the base class for the dialogs"""
#
#    GLADE_FILE = os.path.join(consts.GLADE_DIR, "dialogs.glade")
#
#    def __init__(self, ctrl, top_widget):
#        View.__init__(self, ctrl, self.GLADE_FILE, top_widget, domain="VMC")
#
#    def run(self):
#        resp = self.get_top_widget().run()
#        self.get_top_widget().destroy()
#        return resp

#class DialogMessage(DialogView):
#    """Dialog message"""
#
#    def __init__(self, ctrl, message, details):
#        DialogView.__init__(self, ctrl, "dialog_message")
#        self['label_message'].set_markup("<big><b>%s</b></big>" % message)
#        self['label_details'].set_text(clear_s(details))

#class WarningMessage(DialogView):
#    """Warning dialog"""
#
#    def __init__(self, ctrl, message, details):
#        DialogView.__init__(self, ctrl, "warning_message")
#        self['label_message'].set_markup("<big><b>%s</b></big>" % message)
#        self['label_details'].set_text(clear_s(details))

#class WarningRequestOkCancel(DialogView):
#    """Warning dialog with two OK/Cancel buttons"""
#
#    def __init__(self, ctrl, message, details):
#        DialogView.__init__(self, ctrl, "dialog_confirm_cancel_ok")
#        self['label_message'].set_markup("<big><b>%s</b></big>" % message)
#        self['label_details'].set_text(clear_s(details))

#class QuestionConfirmAction(DialogView):
#    """Confirmation dialog for an action"""
#
#    def __init__(self, ctrl, action_name, message, details):
#        DialogView.__init__(self, ctrl, "dialog_confirm_action")
#        self['label_message'].set_markup("<big><b>%s</b></big>" % message)
#        self['label_details'].set_text(clear_s(details))
#        self['button_action'].set_label(action_name)
##        self.get_top_widget().set_title("")
#        filepath = os.path.join(consts.IMAGES_DIR, 'VF_logo.png')
#        self.get_top_widget().set_icon_from_file(filepath)
