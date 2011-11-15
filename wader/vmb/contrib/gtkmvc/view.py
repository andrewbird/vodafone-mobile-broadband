#  Author: Roberto Cavada <cavada@fbk.eu>
#  Modified by: Guillaume Libersat <glibersat AT linux62.org>
#
#  Copyright (c) 2005 by Roberto Cavada
#  Copyright (c) 2007 by Guillaume Libersat
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

import gtk.glade
from controller import Controller
import types


class View (object):

    #
    # modified for VMB to use translation domain
    #

    def __init__(self, controller, glade_filename=None,
                 glade_top_widget_name=None, parent_view=None,
                 register=True, domain=None):
        """If register is False you *must* call 'controller.register_view(self)'
        from the derived class constructor (i.e. registration is delayed)
        If filename is not given (or None) all following parameters must be
        not given (or None). In that case widgets must be connected manually.
        glade_top_widget_name can be either a string name or list of names."""
        self.manualWidgets = {}
        self.autoWidgets = None

        self.xmlWidgets = []

        # Sets a callback for custom widgets
        gtk.glade.set_custom_handler(self._custom_widget_create)

        if (( type(glade_top_widget_name) == types.StringType)
            or (glade_top_widget_name is None) ):
            wids = (glade_top_widget_name,)
        else: wids = glade_top_widget_name  # Already a list or tuple

        # retrieves XML objects from glade
        if (glade_filename is not None):
            if domain is not None:
                for i in range(0,len(wids)):
                    self.xmlWidgets.append(gtk.glade.XML(glade_filename,
                                                         wids[i], domain))
            else:
                for i in range(0,len(wids)):
                    self.xmlWidgets.append(gtk.glade.XML(glade_filename,
                                                         wids[i]))

        # top widget list or singleton:
        if (glade_top_widget_name is not None):
            if len(wids) > 1:
                self.m_topWidget = []
                for i in range(0, len(wids)):
                    self.m_topWidget.append(self[wids[i]])
                    pass
            else: self.m_topWidget = self[wids[0]]
        else:  self.m_topWidget = None

        if (glade_filename is not None): self.__autoconnect_signals(controller)
        if (register):                   controller.register_view(self)
        if (not parent_view is None):    self.set_parent_view(parent_view)
        return

    # Gives us the ability to do: view['widget_name'].action()
    # Returns None if no widget name has been found.
    def __getitem__(self, key):
        wid = None

        if self.autoWidgets:
            if self.autoWidgets.has_key(key): wid = self.autoWidgets[key]
            pass
        else:
            for xml in self.xmlWidgets:
                wid = xml.get_widget(key)
                if wid is not None: break
                pass
            pass

        if wid is None:
            # try with manually-added widgets:
            if self.manualWidgets.has_key(key):
                wid = self.manualWidgets[key]
                pass
            pass
        return wid

    # You can also add a single widget:
    def __setitem__(self, key, wid):
        self.manualWidgets[key] = wid
        if (self.m_topWidget is None): self.m_topWidget = wid
        return

    def show(self):
        ret = True
        top = self.get_top_widget()
        if type(top) in (types.ListType, types.TupleType):
            for t in top:
                if t is not None: ret = ret and t.show()
                pass
        elif (top is not None): ret = top.show_all()
        else:                   ret = False
        return ret


    def hide(self):
        top = self.get_top_widget()
        if type(top) in (types.ListType, types.TupleType):
            for t in top:
                if t is not None: t.hide_all()
                pass
        elif top is not None: top.hide_all()
        return

    # Returns the top-level widget, or a list of top widgets
    def get_top_widget(self):
        return self.m_topWidget


    # Set parent view:
    def set_parent_view(self, parent_view):
        top = self.get_top_widget()
        if type(top) in (types.ListType, types.TupleType):
            for t in top:
                if t is not None:
                    t.set_transient_for(parent_view.get_top_widget())
                    pass
                pass
        elif (top is not None):
            top.set_transient_for(parent_view.get_top_widget())
            pass

        return

    # Set the transient for the view:
    def set_transient(self, transient_view):
        top = self.get_top_widget()
        if type(top) in (types.ListType, types.TupleType):
            for t in top:
                if t is not None:
                    transient_view.get_top_widget().set_transient_for(t)
                    pass
                pass
        elif (top is not None):
            transient_view.get_top_widget().set_transient_for(top)
            pass
        return

    # Finds the right callback for custom widget creation and calls it
    # Returns None if an undefined or invalid  handler is found
    def _custom_widget_create(self, glade, function_name, widget_name,
                              str1, str2, int1, int2):
        # This code was kindly provided by Allan Douglas <zalguod at
        # users.sourceforge.net>
        if function_name is not None:
            handler = getattr(self, function_name, None)
            if handler is not None: return handler(str1, str2, int1, int2)
            pass
        return None

    # implements the iteration protocol
    def __iter__(self):
        # pre-calculates the auto widgets if needed:
        if self.autoWidgets is None:
            self.autoWidgets = {}

            for xml in self.xmlWidgets:
                for wid in xml.get_widget_prefix(""):
                    wname = gtk.glade.get_widget_name(wid)
                    assert not self.autoWidgets.has_key(wname)
                    self.autoWidgets[wname] = wid
                    pass
                pass
            pass

        self.__idx = 0
        self.__max1 = len(self.autoWidgets)
        self.__max2 = self.__max1 + len(self.manualWidgets)
        return self

    # implements the iteration protocol
    def next(self):
        if self.__idx >= self.__max2: raise StopIteration()
        if self.__idx >= self.__max1: m = self.manualWidgets
        else: m = self.autoWidgets
        self.__idx += 1
        return m.keys()[self.__idx-1]


    # performs Controller's signals auto-connection:
    def __autoconnect_signals(self, controller):
        dic = {}
        for name in dir(controller):
            method = getattr(controller, name)
            if (not callable(method)): continue
            assert(not dic.has_key(name)) # not already connected!
            dic[name] = method
            pass

        for xml in self.xmlWidgets: xml.signal_autoconnect(dic)
        return



    pass # end of class View
