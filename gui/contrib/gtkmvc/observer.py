#  -------------------------------------------------------------------------
#  Author: Roberto Cavada <cavada@fbk.eu>
#
#  Copyright (C) 2006 by Roberto Cavada
#
#  pygtkmvc is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  pygtkmvc is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor,
#  Boston, MA 02110, USA.
#
#  For more information on pygtkmvc see <http://pygtkmvc.sourceforge.net>
#  or email to the author Roberto Cavada <cavada@fbk.eu>.
#  Please report bugs to <cavada@fbk.eu>.
#  -------------------------------------------------------------------------


class Observer (object):
    """Use this class as base class of all observers"""

    def __init__(self, model=None, spurious=False):
        """
        When parameter spurious is set to False
        (default value) the observer declares that it is not
        interested in receiving value-change notifications when
        property's value does not really change. This happens when a
        property got assigned to a value that is the same it had
        before being assigned.

        A notification was used to be sent to the observer even in
        this particular condition, because spurious (non-changing)
        assignments were used as signals when signals were not
        supported by early version of the framework. The observer
        was in charge of deciding what to do with spurious
        assignments, by checking if the old and new values were
        different at the beginning of the notification code. With
        latest version providing new notification types like
        signals, this requirement seems to be no longer needed, and
        delivering a notification is no longer a sensible
        behaviour.

        This is the reason for providing parameter
        spurious that changes the previous behaviour
        but keeps availability of a possible backward compatible
        feature.
        """

        self.model = None
        self.__accepts_spurious__ = spurious
        self.register_model(model)
        return

    def register_model(self, model):
        self.unregister_model()
        self.model = model
        if self.model: self.model.register_observer(self)
        return

    def accepts_spurious_change(self):
        """
        Returns True if this observer is interested in receiving
        spurious value changes. This is queried by the model when
        notifying a value change."""
        return self.__accepts_spurious__

    def unregister_model(self):
        if self.model:
            self.model.unregister_observer(self)
            self.model = None
            pass
        return

    def __del__(self):
        self.unregister_model()
        return

    def get_model(self): return self.model

    pass # end of class
